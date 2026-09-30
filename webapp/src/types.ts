/** Формат catalog.json (см. services/export.py). Цены — в копейках. */
export type RawVariation = [
  id: number,
  label: string,
  price: number,
  regular: number,
  inStock: number,
  img: string,
  thumb: string,
];

export interface RawProduct {
  id: number;
  name: string;
  url: string;
  img: string;
  thumb: string;
  cats: number[];
  price: number;
  reg: number;
  stock: number;
  sku?: string;
  v?: RawVariation[];
}

export interface Category {
  id: number;
  name: string;
  parent: number;
  count: number;
}

export interface Catalog {
  updated_at: string | null;
  categories: Category[];
  products: RawProduct[];
}

export interface Variation {
  id: number;
  parentId: number;
  label: string;
  attrs: Record<string, string>;
  price: number;
  regular: number;
  inStock: boolean;
  img: string;
  thumb: string;
}

export interface Product {
  id: number;
  name: string;
  url: string;
  img: string;
  thumb: string;
  cats: number[];
  /** минимальная цена > 0 среди вариантов (0 — «по запросу») */
  minPrice: number;
  /** максимальная скидка среди вариантов, копейки */
  maxDiscount: number;
  inStock: boolean;
  variations: Variation[];
  /** порядок атрибутов, например ["Память", "Цвет"] */
  attrNames: string[];
  search: string;
}

export type Screen =
  | { name: "home" }
  | { name: "category"; id: number }
  | { name: "product"; id: number; vid?: number }
  | { name: "search" }
  | { name: "subs" };
