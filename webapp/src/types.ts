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
  /** характеристики из Википедии: [название, значение] */
  specs?: [string, string][];
  specs_src?: string;
  /** все фото по порядку (первое — главное), если их больше одного */
  gal?: string[];
}

export interface TradeInVariant {
  id: string;
  label: string;
  prices: Record<string, number>; // рубли по id состояния
}

export interface TradeIn {
  conditions: { id: string; label: string }[];
  devices: { slug: string; label: string; models: { id: string; name: string; variants: TradeInVariant[] }[] }[];
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
  tradein?: TradeIn;
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
  specs: [string, string][];
  specsSrc: string;
  gallery: string[];
  device: DeviceKey;
  /** «Apple» или «другие» внутри типа устройства — по ОС */
  apple: boolean;
  used: boolean;
  /** «новизна» модели: больше — новее (см. rankNewness в data.ts) */
  newness: number;
}

export type DeviceKey = "phone" | "tablet" | "laptop" | "watch" | "audio" | "console" | "tv" | "home" | "acc" | "other";

export type Screen =
  | { name: "home" }
  | { name: "category"; id: number }
  | { name: "product"; id: number; vid?: number }
  | { name: "search" }
  | { name: "subs" }
  | { name: "favorites" }
  | { name: "cart" }
  | { name: "compare" }
  | { name: "more" }
  | { name: "service" }
  | { name: "tradein" }
  | { name: "device"; key: DeviceKey };
