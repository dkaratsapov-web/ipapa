import type { Catalog, Category, DeviceKey, Product, RawProduct, TradeIn, Variation } from "./types";

/** Типы устройств и разбивка по ОС: [ОС Apple, ОС остальных] */
export const DEVICES: { key: DeviceKey; label: string; os?: [string, string] }[] = [
  { key: "phone", label: "Смартфоны", os: ["iOS", "Android"] },
  { key: "tablet", label: "Планшеты", os: ["iPadOS", "Android"] },
  { key: "laptop", label: "Ноутбуки", os: ["macOS", "Windows"] },
  { key: "watch", label: "Часы", os: ["watchOS", "Другие"] },
  { key: "audio", label: "Наушники", os: ["AirPods", "Другие"] },
  { key: "console", label: "Игровые приставки" },
  { key: "tv", label: "ТВ-приставки" },
  { key: "home", label: "Dyson" },
  { key: "acc", label: "Аксессуары" },
];

const APPLE_CATS = ["iphone", "ipad", "macbook", "apple watch", "airpods", "новинки apple", "apple tv"];
const PHONE_CATS = ["iphone", "android-смартфоны", "samsung", "xiaomi", "honor", "huawei", "google", "oneplus", "realme",
  "nothing", "vivo", "tecno", "sony", "redmagic"];

/** Тип устройства по категориям сайта (с родителями) и названию. */
function classify(name: string, cats: string[]): { device: DeviceKey; apple: boolean; used: boolean } {
  const n = name.toLowerCase();
  const has = (c: string) => cats.includes(c);
  const used = cats.some((c) => c.startsWith("б/у"));
  const apple = APPLE_CATS.some(has) || /\b(apple|iphone|ipad|macbook|imac|airpods)\b/.test(n);
  let device: DeviceKey;
  if (has("тв-приставки") || /apple tv/.test(n)) device = "tv";
  else if (has("аксессуары") || /^(адаптер|защитное|стекло|чехол|силиконовый чехол|кабель|переходник|airtag)/.test(n)) device = "acc";
  else if (has("airpods") || /airpods|buds|наушник|earbuds|headphone|freebuds/.test(n)) device = "audio";
  else if (has("apple watch") || /watch|\bband\b|часы/.test(n)) device = "watch";
  else if (has("ipad") || /ipad|\bpad\b|\btab\b|планшет|matepad/.test(n)) device = "tablet";
  else if (has("macbook") || /macbook|ноутбук|laptop|matebook|magicbook|imac|mac mini/.test(n)) device = "laptop";
  else if (has("игровые приставки") || /playstation|xbox|nintendo|steam deck|dualsense/.test(n)) device = "console";
  else if (has("dyson") || /dyson/.test(n)) device = "home";
  else if (PHONE_CATS.some(has) || /iphone|galaxy|redmi|xiaomi|honor|huawei|pixel|oneplus|realme|nothing|vivo|tecno|poco|redmagic|xperia|смартфон/.test(n))
    device = "phone";
  else device = "other";
  return { device, apple: !!apple, used };
}

const DEFAULT_DATA_URL =
  "https://raw.githubusercontent.com/dkaratsapov-web/ipapa/webapp-data/catalog.json";

/** Источник данных: ?data=..., переменная сборки VITE_DATA_URL или ветка webapp-data. */
export function dataUrl(): string {
  const params = new URLSearchParams(location.search);
  if (params.get("demo") === "1") return "./demo-catalog.json";
  return params.get("data") || import.meta.env.VITE_DATA_URL || DEFAULT_DATA_URL;
}

const CACHE_KEY = "ipapa-catalog-v1";

/** Каталог из прошлого запуска — показываем сразу, пока грузится свежий. */
export function cachedCatalog(): Catalog | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as Catalog) : null;
  } catch {
    return null;
  }
}

function saveCache(catalog: Catalog): void {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(catalog));
  } catch {
    /* переполнение или запрет хранилища — не критично */
  }
}

export async function loadCatalog(): Promise<Catalog> {
  const url = dataUrl();
  // Каталог обновляется раз в час — добавляем метку, чтобы обойти кэш CDN
  const bust = `${url.includes("?") ? "&" : "?"}t=${Math.floor(Date.now() / 300_000)}`;
  const resp = await fetch(url + bust, { cache: "no-cache" });
  if (!resp.ok) {
    console.error("catalog.json: HTTP", resp.status);
    throw new Error("Проверьте интернет и попробуйте ещё раз.");
  }
  const catalog = (await resp.json()) as Catalog;
  saveCache(catalog);
  return catalog;
}

export function normalize(text: string): string {
  return text.toLowerCase().replace(/ё/g, "е").replace(/\s+/g, " ").trim();
}

/** Русские и транслитерированные названия -> как в каталоге. */
const SYNONYMS: [RegExp, string][] = [
  [/айфон\S*/g, "iphone"],
  [/айпад\S*/g, "ipad"],
  [/макбук\S*/g, "macbook"],
  [/(эйр|аир|эир)подс\S*/g, "airpods"],
  [/(эпл|эппл|apple)\s*(вотч|воч|watch)\S*/g, "apple watch"],
  [/(вотч|часы)\b/g, "watch"],
  [/самсунг\S*|галакси\S*/g, "samsung"],
  [/сяоми|ксиаоми/g, "xiaomi"],
  [/редми/g, "redmi"],
  [/дайсон\S*/g, "dyson"],
  [/плейстейшн\S*|плойк\S*|пс5/g, "playstation"],
  [/\bпро\b/g, "pro"],
  [/\bмакс\b/g, "max"],
  [/\bмини\b/g, "mini"],
  [/\bплюс\b/g, "plus"],
  [/\bэйр\b|\bаир\b/g, "air"],
  [/(\d+)\s*(гб|gb)\b/g, "$1"],
  [/(\d+)\s*(тб|tb)\b/g, "$1"],
];

export function terms(query: string): string[] {
  let q = normalize(query);
  for (const [re, to] of SYNONYMS) q = q.replace(re, to);
  return q.split(/[\s,;]+/).filter(Boolean);
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

function buildProduct(raw: RawProduct, catNames: (ids: number[]) => string[]): Product {
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
  // На сайте бывают дубли вариантов с одинаковым описанием — оставляем лучший (в наличии, дешевле)
  const best = new Map<string, Variation>();
  for (const v of variations) {
    const prev = best.get(v.label);
    const better = !prev || (v.inStock && !prev.inStock) || (v.inStock === prev.inStock && v.price > 0 && (prev.price === 0 || v.price < prev.price));
    if (better) best.set(v.label, v);
  }
  if (best.size < variations.length) variations.splice(0, variations.length, ...best.values());
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
    specs: raw.specs ?? [],
    specsSrc: raw.specs_src ?? "",
    gallery: raw.gal?.length ? raw.gal : raw.img ? [raw.img] : [],
    ...classify(raw.name, catNames(raw.cats)),
    newness: raw.id,
  };
}

export class Store {
  readonly products: Product[];
  readonly byId = new Map<number, Product>();
  readonly variationById = new Map<number, Variation>();
  readonly categories: Category[];
  readonly updatedAt: Date | null;
  readonly tradein: TradeIn | null;

  constructor(catalog: Catalog) {
    const byId = new Map(catalog.categories.map((c) => [c.id, c]));
    // названия категорий товара вместе с родителями, в нижнем регистре
    const catNames = (ids: number[]) => {
      const out: string[] = [];
      for (let id of ids) {
        for (let guard = 0; byId.has(id) && guard < 5; guard++) {
          const c = byId.get(id)!;
          out.push(c.name.toLowerCase());
          id = c.parent;
        }
      }
      return out;
    };
    this.products = catalog.products.map((p) => buildProduct(p, catNames));
    rankNewness(this.products);
    for (const p of this.products) {
      this.byId.set(p.id, p);
      p.variations.forEach((v) => this.variationById.set(v.id, v));
    }
    this.categories = catalog.categories;
    this.updatedAt = catalog.updated_at ? new Date(catalog.updated_at) : null;
    this.tradein = catalog.tradein ?? null;
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

  /** Обложка категории — фото дорогого товара в наличии, без баннеров и коллажей. */
  cover(id: number): string {
    return coverOf(this.inCategory(id));
  }

  /** Новые (или Б/У) товары типа устройства; apple: true/false — разбивка по ОС. */
  inDevice(key: DeviceKey, opts: { used?: boolean; apple?: boolean } = {}): Product[] {
    return this.products.filter(
      (p) => p.device === key && p.used === !!opts.used && (opts.apple === undefined || p.apple === opts.apple),
    );
  }

  devices(): { key: DeviceKey; label: string; os?: [string, string]; count: number; cover: string }[] {
    return DEVICES.map((d) => {
      const items = this.inDevice(d.key);
      return { ...d, count: items.length, cover: coverOf(items) };
    }).filter((d) => d.count > 0);
  }

  /** Новые модели — первыми; при равенстве — в наличии и с ценой. */
  static byNewest = (a: Product, b: Product) =>
    b.newness - a.newness || Number(b.inStock) - Number(a.inStock) || Number(!a.minPrice) - Number(!b.minPrice);

  search(query: string, limit = 60): Product[] {
    // limit + 1, чтобы понять, что результатов больше лимита
    const words = terms(query);
    if (!words.length) return [];
    return this.products
      .filter((p) => words.every((w) => p.search.includes(w)))
      .sort((a, b) => Number(a.used) - Number(b.used) || Store.byNewest(a, b))
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

  private newsId(): number | undefined {
    return this.categories.find((c) => c.name.toLowerCase().includes("новинки"))?.id;
  }

  isNew(p: Product): boolean {
    const id = this.newsId();
    return id !== undefined && p.cats.includes(id);
  }

  /** Новинки (или самые дорогие товары в наличии) для карусели на главной. */
  featured(limit = 10): Product[] {
    const id = this.newsId();
    const good = (list: Product[]) => list.filter((p) => p.inStock && p.minPrice > 0);
    const fromNews = id !== undefined ? good(this.inCategory(id)) : [];
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

/** Пропорции фото по имени файла WordPress (…-600x935.jpg). */
function ratio(url: string): number | null {
  const m = url.match(/-(\d+)x(\d+)\.\w+(\?|$)/);
  return m ? Number(m[1]) / Number(m[2]) : null;
}

function coverOf(items: Product[]): string {
  const score = (p: Product) => {
    const r = ratio(p.thumb);
    const shape = r === null ? 0.3 : Math.abs(Math.log(r)); // ближе к квадрату — лучше
    return (p.inStock ? 0 : 2) + shape * 2 - Math.log10(1 + p.minPrice / 100) / 10;
  };
  const best = items.filter((p) => p.thumb).sort((a, b) => score(a) - score(b))[0];
  return best?.thumb ?? "";
}

/**
 * Линейка и поколение модели по названию: «Redmi Note 17 Pro» -> [«redmi note», 17],
 * «Galaxy S26» -> [«galaxy s», 26], «MacBook Air 15 (2023) M2» -> [«macbook air», 2023].
 * Год и чип (M4, A16) важнее первого числа: у ноутбуков первое число — диагональ.
 */
export function modelGeneration(name: string): { line: string; gen: number | null } {
  const n = name.toLowerCase().split(",")[0].replace(/[″"()]/g, " ");
  const year = n.match(/\b(20[12]\d)\b/);
  const chip = n.match(/\b(?:m([1-9])|a(1[0-9]|[2-9]\d))\b/);
  const tokens = n.split(/\s+/).filter(Boolean);
  const line: string[] = [];
  let first: number | null = null;
  for (const t of tokens) {
    const m = t.match(/^([a-zа-я]*)(\d+)/);
    if (m) {
      if (m[1]) line.push(m[1]);
      first = Number(m[2]);
      break;
    }
    line.push(t);
  }
  const gen = year ? Number(year[1]) : chip ? (chip[1] ? 100 + Number(chip[1]) : Number(chip[2])) : first;
  return { line: line.slice(0, 3).join(" "), gen };
}

/**
 * Новизна: ID товара растёт по мере добавления в магазин, но внутри одной линейки
 * порядок поправляем по поколению (Redmi Note 17 новее Note 14, даже если 14 добавили позже).
 */
function rankNewness(products: Product[]): void {
  const lines = new Map<string, { p: Product; gen: number }[]>();
  for (const p of products) {
    const { line, gen } = modelGeneration(p.name);
    if (gen === null || !line) continue;
    const key = `${p.used ? "u" : "n"}:${line}`;
    if (!lines.has(key)) lines.set(key, []);
    lines.get(key)!.push({ p, gen });
  }
  for (const group of lines.values()) {
    if (group.length < 2) continue;
    const ids = group.map((g) => g.p.newness).sort((a, b) => b - a);
    group.sort((a, b) => b.gen - a.gen || b.p.newness - a.p.newness);
    group.forEach((g, i) => (g.p.newness = ids[i]));
  }
}
