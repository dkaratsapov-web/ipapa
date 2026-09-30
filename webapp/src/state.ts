/**
 * Избранное, корзина и сравнение. Хранятся в localStorage и в Telegram CloudStorage —
 * так списки общие для всех устройств пользователя.
 */
import { useSyncExternalStore } from "react";
import { cloudGet, cloudSet } from "./telegram";

export interface CartItem {
  /** ID варианта или простого товара */
  id: number;
  qty: number;
}

export interface Lists {
  favorites: number[]; // ID товаров
  cart: CartItem[];
  compare: number[]; // ID товаров, не больше MAX_COMPARE
}

export const MAX_COMPARE = 4;
const KEY = "ipapa-lists-v1";
const EMPTY: Lists = { favorites: [], cart: [], compare: [] };

function sanitize(raw: unknown): Lists {
  const r = (raw ?? {}) as Partial<Lists>;
  const ids = (a: unknown) => (Array.isArray(a) ? a.map(Number).filter((n) => n > 0) : []);
  return {
    favorites: ids(r.favorites),
    compare: ids(r.compare).slice(0, MAX_COMPARE),
    cart: Array.isArray(r.cart)
      ? r.cart
          .map((i) => ({ id: Number(i?.id), qty: Math.max(1, Math.min(99, Number(i?.qty) || 1)) }))
          .filter((i) => i.id > 0)
      : [],
  };
}

function readLocal(): Lists {
  try {
    return sanitize(JSON.parse(localStorage.getItem(KEY) || "null"));
  } catch {
    return EMPTY;
  }
}

let state: Lists = readLocal();
const listeners = new Set<() => void>();

function set(next: Lists): void {
  state = next;
  const json = JSON.stringify(next);
  try {
    localStorage.setItem(KEY, json);
  } catch {
    /* не критично */
  }
  cloudSet(KEY, json);
  listeners.forEach((l) => l());
}

// Подтягиваем списки из облака Telegram (например, с другого устройства)
cloudGet(KEY).then((json) => {
  if (!json) return;
  try {
    const cloud = sanitize(JSON.parse(json));
    const merged: Lists = {
      favorites: [...new Set([...cloud.favorites, ...state.favorites])],
      compare: [...new Set([...cloud.compare, ...state.compare])].slice(0, MAX_COMPARE),
      cart: [...cloud.cart, ...state.cart.filter((i) => !cloud.cart.some((c) => c.id === i.id))],
    };
    set(merged);
  } catch {
    /* повреждённые данные — игнорируем */
  }
});

export function useLists(): Lists {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
  );
}

const toggle = (list: number[], id: number) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

export const lists = {
  toggleFavorite(id: number): boolean {
    set({ ...state, favorites: toggle(state.favorites, id) });
    return state.favorites.includes(id);
  },
  /** false — список сравнения полон */
  toggleCompare(id: number): boolean {
    if (!state.compare.includes(id) && state.compare.length >= MAX_COMPARE) return false;
    set({ ...state, compare: toggle(state.compare, id) });
    return true;
  },
  clearCompare(): void {
    set({ ...state, compare: [] });
  },
  addToCart(id: number): void {
    const has = state.cart.find((i) => i.id === id);
    set({
      ...state,
      cart: has ? state.cart.map((i) => (i.id === id ? { ...i, qty: Math.min(99, i.qty + 1) } : i)) : [...state.cart, { id, qty: 1 }],
    });
  },
  setQty(id: number, qty: number): void {
    set({ ...state, cart: qty <= 0 ? state.cart.filter((i) => i.id !== id) : state.cart.map((i) => (i.id === id ? { ...i, qty: Math.min(99, qty) } : i)) });
  },
  clearCart(): void {
    set({ ...state, cart: [] });
  },
};
