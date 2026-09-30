import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";
import type { Store } from "../data";
import { plural } from "../format";
import type { Product } from "../types";
import { ProductCard } from "./ProductCard";

type Sort = "popular" | "cheap" | "expensive";
const SORTS: { id: Sort; label: string }[] = [
  { id: "popular", label: "Популярные" },
  { id: "cheap", label: "Дешевле" },
  { id: "expensive", label: "Дороже" },
];
const PAGE = 24;

export function CategoryScreen({ store, id, onProduct }: { store: Store; id: number; onProduct: (p: Product) => void }) {
  const category = store.category(id);
  const children = store.children(id);
  const [sub, setSub] = useState<number>(0);
  const [sort, setSort] = useState<Sort>("popular");
  const [onlyStock, setOnlyStock] = useState(false);
  const [limit, setLimit] = useState(PAGE);

  const items = useMemo(() => {
    let list = store.inCategory(sub || id);
    if (onlyStock) list = list.filter((p) => p.inStock);
    const price = (p: Product) => p.minPrice || Number.MAX_SAFE_INTEGER;
    if (sort === "cheap") list = [...list].sort((a, b) => price(a) - price(b));
    else if (sort === "expensive") list = [...list].sort((a, b) => (b.minPrice || 0) - (a.minPrice || 0));
    else list = [...list].sort((a, b) => Number(b.inStock) - Number(a.inStock) || Number(!a.minPrice) - Number(!b.minPrice));
    return list;
  }, [store, id, sub, sort, onlyStock]);

  const listKey = `${sub}-${sort}-${onlyStock}`;
  return (
    <>
      <header className="topbar">
        <h1 className="page-title">{category?.name ?? "Каталог"}</h1>
        <div className="title-row">
          <span className="muted" style={{ fontWeight: 600 }}>
            {items.length} {plural(items.length, "товар", "товара", "товаров")}
          </span>
          <button className="toggle" role="switch" aria-checked={onlyStock} onClick={() => setOnlyStock(!onlyStock)}>
            <span className={`toggle-track ${onlyStock ? "is-on" : ""}`}>
              <motion.span className="toggle-knob" layout transition={{ type: "spring", stiffness: 600, damping: 35 }} />
            </span>
            В наличии
          </button>
        </div>
      </header>

      {children.length > 0 && (
        <div className="chips" role="tablist" aria-label="Подкатегории">
          {[{ id: 0, name: "Все" }, ...children].map((c) => (
            <Chip key={c.id} active={sub === c.id} group={`sub-${id}`} onClick={() => { setSub(c.id); setLimit(PAGE); }}>
              {c.name}
            </Chip>
          ))}
        </div>
      )}
      <div className="chips" role="tablist" aria-label="Сортировка">
        {SORTS.map((s) => (
          <Chip key={s.id} active={sort === s.id} group={`sort-${id}`} onClick={() => setSort(s.id)}>
            {s.label}
          </Chip>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={listKey} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
          {items.length ? (
            <div className="grid">
              {items.slice(0, limit).map((p, i) => (
                <ProductCard key={p.id} product={p} index={i % PAGE} onOpen={onProduct} />
              ))}
            </div>
          ) : (
            <div className="empty">
              <div className="empty-emoji">🫙</div>
              <h3>Пусто</h3>
              <p>Попробуйте убрать фильтр «В наличии».</p>
            </div>
          )}
          {items.length > limit && (
            <motion.button className="load-more" whileTap={{ scale: 0.96 }} onClick={() => setLimit(limit + PAGE)}>
              Показать ещё {Math.min(PAGE, items.length - limit)}
            </motion.button>
          )}
        </motion.div>
      </AnimatePresence>
    </>
  );
}

export function Chip({
  active,
  group,
  onClick,
  children,
}: {
  active: boolean;
  group: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <motion.button
      className={`chip ${active ? "is-active" : ""}`}
      onClick={onClick}
      whileTap={{ scale: 0.94 }}
      role="tab"
      aria-selected={active}
    >
      {active && <motion.span className="chip-bg" layoutId={`chip-${group}`} transition={{ type: "spring", stiffness: 500, damping: 38 }} />}
      <span>{children}</span>
    </motion.button>
  );
}
