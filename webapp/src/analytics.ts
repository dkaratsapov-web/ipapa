/**
 * Статистика мини-аппа. Своего сервера нет, поэтому события копятся на устройстве и уходят
 * в бота вместе с ближайшей отправкой данных (заявка, подписки). Если задан VITE_METRIKA_ID —
 * дополнительно отправляются в Яндекс Метрику (полная картина без заявок).
 */
interface Batch {
  v: Record<string, number>; // просмотры карточек
  f: number[]; // добавили в избранное
  c: number[]; // добавили в корзину
  k: number[]; // добавили к сравнению
  q: string[]; // поисковые запросы
}

const KEY = "ipapa-events-v1";
const METRIKA = Number(import.meta.env.VITE_METRIKA_ID) || 0;

declare global {
  interface Window {
    ym?: (id: number, method: string, ...args: unknown[]) => void;
  }
}

function load(): Batch {
  try {
    const b = JSON.parse(localStorage.getItem(KEY) || "null");
    if (b && typeof b === "object") return { v: b.v || {}, f: b.f || [], c: b.c || [], k: b.k || [], q: b.q || [] };
  } catch {
    /* пусто */
  }
  return { v: {}, f: [], c: [], k: [], q: [] };
}

let batch = load();

function save(): void {
  // не больше ~2,5 КБ: sendData ограничен 4096 байтами вместе с заявкой
  while (JSON.stringify(batch).length > 2500) {
    if (batch.q.length) batch.q.shift();
    else if (Object.keys(batch.v).length) delete batch.v[Object.keys(batch.v)[0]];
    else break;
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(batch));
  } catch {
    /* не критично */
  }
}

function goal(name: string, params?: Record<string, unknown>): void {
  if (METRIKA && window.ym) window.ym(METRIKA, "reachGoal", name, params);
}

const push = (list: number[], id: number) => {
  if (!list.includes(id)) list.push(id);
};

export const track = {
  view(id: number, name: string): void {
    batch.v[id] = (batch.v[id] || 0) + 1;
    save();
    goal("product_view", { id, name });
  },
  favorite(id: number): void {
    push(batch.f, id);
    save();
    goal("favorite_add", { id });
  },
  cart(id: number): void {
    push(batch.c, id);
    save();
    goal("cart_add", { id });
  },
  compare(id: number): void {
    push(batch.k, id);
    save();
    goal("compare_add", { id });
  },
  search(query: string): void {
    const q = query.trim().slice(0, 60);
    if (q.length < 2 || batch.q[batch.q.length - 1] === q) return;
    batch.q.push(q);
    save();
    goal("search", { q });
  },
  screen(name: string): void {
    if (METRIKA && window.ym) window.ym(METRIKA, "hit", `#/${name}`);
  },
};

/** Накопленные события для отправки в бота; после вызова очередь пуста. */
export function takeBatch(): Batch | null {
  const b = batch;
  const empty = !Object.keys(b.v).length && !b.f.length && !b.c.length && !b.k.length && !b.q.length;
  if (empty) return null;
  batch = { v: {}, f: [], c: [], k: [], q: [] };
  save();
  return b;
}

/** Подключение Яндекс Метрики (если задан номер счётчика при сборке). */
export function initMetrika(): void {
  if (!METRIKA) return;
  const w = window as unknown as { ym: { (...a: unknown[]): void; a?: unknown[]; l?: number } };
  w.ym = Object.assign(function (...args: unknown[]) {
    (w.ym.a = w.ym.a || []).push(args);
  }, { l: Date.now() });
  const s = document.createElement("script");
  s.async = true;
  s.src = "https://mc.yandex.ru/metrika/tag.js";
  document.head.appendChild(s);
  window.ym!(METRIKA, "init", { clickmap: true, trackLinks: true, accurateTrackBounce: true });
}
