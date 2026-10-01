import { LayoutGroup, motion } from "framer-motion";
import { useMemo, useState, type ReactNode } from "react";
import { Store } from "../data";
import { plural } from "../format";
import type { Product } from "../types";
import { IconBack, IconBox } from "./Icons";
import { ProductCard } from "./ProductCard";

type Sort = "default" | "cheap" | "expensive";
const SORTS: { id: Sort; label: string }[] = [
  { id: "default", label: "Сначала новые" },
  { id: "cheap", label: "Сначала дешёвые" },
  { id: "expensive", label: "Сначала дорогие" },
];
const PAGE = 24;

export function CategoryScreen({
  store,
  id,
  onProduct,
  onBack,
}: {
  store: Store;
  id: number;
  onProduct: (p: Product) => void;
  onBack?: () => void;
}) {
  const category = store.category(id);
  const children = store.children(id);
  const [sub, setSub] = useState<number>(0);
  const [sort, setSort] = useState<Sort>("default");
  const [onlyStock, setOnlyStock] = useState(false);
  const [limit, setLimit] = useState(PAGE);

  const items = useMemo(() => {
    let list = store.inCategory(sub || id);
    if (onlyStock) list = list.filter((p) => p.inStock);
    const price = (p: Product) => p.minPrice || Number.MAX_SAFE_INTEGER;
    if (sort === "cheap") return [...list].sort((a, b) => price(a) - price(b));
    if (sort === "expensive") return [...list].sort((a, b) => (b.minPrice || 0) - (a.minPrice || 0));
    return [...list].sort(Store.byNewest);
  }, [store, id, sub, sort, onlyStock]);

  return (
    <>
      <header className="topbar">
        <div className="topbar-row">
          {onBack && (
            <button className="icon-btn back-btn" onClick={onBack} aria-label="Назад">
              <IconBack />
            </button>
          )}
          <h1 className="page-title">{category?.name ?? "Каталог"}</h1>
        </div>
        <div className="title-row">
          <span className="muted" style={{ fontWeight: 600 }} role="status">
            {items.length} {plural(items.length, "товар", "товара", "товаров")}
          </span>
          <button className="toggle" role="switch" aria-checked={onlyStock} onClick={() => setOnlyStock(!onlyStock)}>
            <span className={`toggle-track ${onlyStock ? "is-on" : ""}`}>
              <motion.span className="toggle-knob" layout transition={{ type: "spring", stiffness: 600, damping: 35 }} />
            </span>
            Только в наличии
          </button>
        </div>
      </header>

      {children.length > 0 && (
        <div className="chips" role="group" aria-label="Подкатегории">
          {[{ id: 0, name: "Все" }, ...children].map((c) => (
            <Chip
              key={c.id}
              active={sub === c.id}
              group={`sub-${id}`}
              onClick={() => {
                setSub(c.id);
                setLimit(PAGE);
              }}
            >
              {c.name}
            </Chip>
          ))}
        </div>
      )}
      <div className="chips" role="group" aria-label="Сортировка">
        {SORTS.map((s) => (
          <Chip key={s.id} active={sort === s.id} group={`sort-${id}`} onClick={() => setSort(s.id)}>
            {s.label}
          </Chip>
        ))}
      </div>

      {items.length ? (
        <LayoutGroup id={`grid-${id}`}>
          <div className="grid">
            {items.slice(0, limit).map((p, i) => (
              <ProductCard key={p.id} product={p} index={i % PAGE} onOpen={onProduct} />
            ))}
          </div>
        </LayoutGroup>
      ) : (
        <motion.div className="empty" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="empty-icon">
            <IconBox />
          </div>
          {onlyStock ? (
            <>
              <h2>Сейчас нет в наличии</h2>
              <p>Выключите «Только в наличии» — товары под заказ тоже можно купить или подписаться на поступление.</p>
              <motion.button className="btn btn-dark" style={{ margin: "20px auto 0", padding: "0 24px" }} whileTap={{ scale: 0.96 }} onClick={() => setOnlyStock(false)}>
                Показать все товары
              </motion.button>
            </>
          ) : (
            <>
              <h2>В этом разделе пока пусто</h2>
              <p>Загляните позже — каталог обновляется каждый час.</p>
            </>
          )}
        </motion.div>
      )}
      {items.length > limit && (
        <motion.button className="load-more" whileTap={{ scale: 0.96 }} onClick={() => setLimit(limit + PAGE)}>
          Показать ещё {Math.min(PAGE, items.length - limit)}
        </motion.button>
      )}
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
  children: ReactNode;
}) {
  return (
    <motion.button className={`chip ${active ? "is-active" : ""}`} onClick={onClick} whileTap={{ scale: 0.94 }} aria-pressed={active}>
      {active && <motion.span className="chip-bg" layoutId={`chip-${group}`} transition={{ type: "spring", stiffness: 500, damping: 38 }} />}
      <span>{children}</span>
    </motion.button>
  );
}
