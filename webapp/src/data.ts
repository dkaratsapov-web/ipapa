import type { Catalog, Category, Product, RawProduct, Variation } from "./types";

const DEFAULT_DATA_URL =
  "https://raw.githubusercontent.com/dkaratsapov-web/ipapa/webapp-data/catalog.json";

/** Источник данных: ?data=..., переменная сборки VITE_DATA_URL или ветка webapp-data. */
export function dataUrl(): string {
  const params = new URLSearchParams(location.search);
  if (params.get("demo") === "1") return "./demo-catalog.json";
  return params.get("data") || import.meta.env.VITE_DATA_URL || DEFAULT_DATA_URL;
}

export async function loadCatalog(): Promise<Catalog> {
  const url = dataUrl();
  // Каталог обновляется раз в час — добавляем метку, чтобы обойти кэш CDN
  const bust = `${url.includes("?") ? "&" : "?"}t=${Math.floor(Date.now() / 300_000)}`;
  const resp = await fetch(url + bust, { cache: "no-cache" });
  if (!resp.ok) throw new Error(`Каталог недоступен (HTTP ${resp.status})`);
  return resp.json();
}

export function normalize(text: string): string {
  return text.toLowerCase().replace(/ё/g, "е").replace(/\s+/g, " ").trim();
}

export function terms(query: string): string[] {
  return normalize(query).split(/[\s,;]+/).filter(Boolean);
}

/** «Цвет: Silver, Память: 256 ГБ» -> { Цвет: "Silver", Память: "256 ГБ" } */
export function parseAttrs(label: string): Record<string, string> {
  const attrs: Record<string, string> = {};
  for (const part of label.split(",")) {
    const i = part.indexOf(":");
    if (i > 0) attrs[part.slice(0, i).trim()] = part.slice(i + 1).trim();
    else if (part.trim()) attrs[`Вариант`] = part.trim();
  }
  return attrs;
}

/** Память и цвет — в привычном порядке, остальное — как пришло. */
const ATTR_ORDER = ["Цвет", "Память", "Объём памяти", "Конфигурация", "Размер", "Количество сим-карт"];

function sortAttrNames(names: string[]): string[] {
  const rank = (n: string) => {
    const i = ATTR_ORDER.findIndex((a) => n.toLowerCase().startsWith(a.toLowerCase()));
    return i === -1 ? 50 : i;
  };
  return [...names].sort((a, b) => rank(a) - rank(b));
}

function buildProduct(raw: RawProduct): Product {
  const variations: Variation[] = (raw.v ?? []).map(([id, label, price, regular, stock, img, thumb]) => ({
    id,
    parentId: raw.id,
    label,
    attrs: parseAttrs(label),
    price,
    regular,
    inStock: !!stock,
    img: img || raw.img,
    thumb: thumb || img || raw.thumb,
  }));
  const priced = variations.length ? variations.map((v) => v.price).filter((p) => p > 0) : [raw.price].filter((p) => p > 0);
  const discounts = variations.length
    ? variations.map((v) => (v.price > 0 && v.regular > v.price ? v.regular - v.price : 0))
    : [raw.price > 0 && raw.reg > raw.price ? raw.reg - raw.price : 0];
  const names = new Set<string>();
  variations.forEach((v) => Object.keys(v.attrs).forEach((k) => names.add(k)));
  return {
    id: raw.id,
    name: raw.name,
    url: raw.url,
    img: raw.img,
    thumb: raw.thumb || raw.img,
    cats: raw.cats,
    minPrice: priced.length ? Math.min(...priced) : 0,
    maxDiscount: Math.max(0, ...discounts),
    inStock: variations.length ? variations.some((v) => v.inStock) : !!raw.stock,
    variations,
    attrNames: sortAttrNames([...names]),
    search: normalize([raw.name, raw.sku ?? "", ...variations.map((v) => v.label)].join(" ")),
  };
}

export class Store {
  readonly products: Product[];
  readonly byId = new Map<number, Product>();
  readonly variationById = new Map<number, Variation>();
  readonly categories: Category[];
  readonly updatedAt: Date | null;

  constructor(catalog: Catalog) {
    this.products = catalog.products.map(buildProduct);
    for (const p of this.products) {
      this.byId.set(p.id, p);
      p.variations.forEach((v) => this.variationById.set(v.id, v));
    }
    this.categories = catalog.categories;
    this.updatedAt = catalog.updated_at ? new Date(catalog.updated_at) : null;
  }

  topCategories(): Category[] {
    return this.categories
      .filter((c) => c.parent === 0 && this.inCategory(c.id).length > 0)
      .sort((a, b) => CATEGORY_ORDER(a.name) - CATEGORY_ORDER(b.name) || a.name.localeCompare(b.name));
  }

  children(id: number): Category[] {
    return this.categories.filter((c) => c.parent === id && this.inCategory(c.id).length > 0);
  }

  category(id: number): Category | undefined {
    return this.categories.find((c) => c.id === id);
  }

  inCategory(id: number): Product[] {
    const ids = new Set([id, ...this.categories.filter((c) => c.parent === id).map((c) => c.id)]);
    return this.products.filter((p) => p.cats.some((c) => ids.has(c)));
  }

  /** Обложка категории — картинка самого дорогого товара в наличии. */
  cover(id: number): string {
    const items = this.inCategory(id).filter((p) => p.thumb);
    const best = [...items].sort((a, b) => Number(b.inStock) - Number(a.inStock) || b.minPrice - a.minPrice)[0];
    return best?.thumb ?? "";
  }

  search(query: string, limit = 60): Product[] {
    const words = terms(query);
    if (!words.length) return [];
    return this.products
      .filter((p) => words.every((w) => p.search.includes(w)))
      .sort((a, b) => Number(b.inStock) - Number(a.inStock) || a.name.length - b.name.length)
      .slice(0, limit);
  }

  /** Товар и (если есть) вариант по ID подписки. */
  resolve(id: number): { product: Product; variation?: Variation } | null {
    const product = this.byId.get(id);
    if (product) return { product };
    const variation = this.variationById.get(id);
    if (!variation) return null;
    const parent = this.byId.get(variation.parentId);
    return parent ? { product: parent, variation } : null;
  }

  /** Новинки и скидки для главной. */
  featured(limit = 10): Product[] {
    const news = this.categories.find((c) => c.name.toLowerCase().includes("новинки"));
    const good = (list: Product[]) => list.filter((p) => p.inStock && p.minPrice > 0);
    const fromNews = news ? good(this.inCategory(news.id)) : [];
    const pool = fromNews.length ? fromNews : good(this.products).sort((a, b) => b.minPrice - a.minPrice);
    return pool.slice(0, limit);
  }

  deals(limit = 10): Product[] {
    return this.products
      .filter((p) => p.maxDiscount > 0 && p.inStock)
      .sort((a, b) => b.maxDiscount - a.maxDiscount)
      .slice(0, limit);
  }
}

const PRIORITY = ["iphone", "новинки", "macbook", "ipad", "apple watch", "airpods", "samsung", "android"];
function CATEGORY_ORDER(name: string): number {
  const i = PRIORITY.findIndex((p) => name.toLowerCase().startsWith(p));
  return i === -1 ? 100 : i;
}
