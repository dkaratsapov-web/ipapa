import { LayoutGroup, motion } from "framer-motion";
import { useMemo, useState } from "react";
import { DEVICES, Store } from "../data";
import { plural } from "../format";
import type { DeviceKey, Product } from "../types";
import { Chip } from "./CategoryScreen";
import { IconBox } from "./Icons";
import { ProductCard } from "./ProductCard";
import { ScreenHeader } from "./ScreenHeader";

type Sort = "default" | "cheap" | "expensive";
const SORTS: { id: Sort; label: string }[] = [
  { id: "default", label: "Сначала новые" },
  { id: "cheap", label: "Сначала дешёвые" },
  { id: "expensive", label: "Сначала дорогие" },
];
const PAGE = 24;

/** Тип устройства с разбивкой по ОС и переключателем «Новые / Б/У». */
export function DeviceScreen({ store, deviceKey, onProduct, onBack }: { store: Store; deviceKey: DeviceKey; onProduct: (p: Product) => void; onBack?: () => void }) {
  const def = DEVICES.find((d) => d.key === deviceKey)!;
  const hasUsed = store.inDevice(deviceKey, { used: true }).length > 0;
  const [used, setUsed] = useState(false);
  const [os, setOs] = useState<"all" | "apple" | "other">("all");
  const [sort, setSort] = useState<Sort>("default");
  const [onlyStock, setOnlyStock] = useState(false);
  const [limit, setLimit] = useState(PAGE);

  const base = store.inDevice(deviceKey, { used });
  const osCounts = { apple: base.filter((p) => p.apple).length, other: base.filter((p) => !p.apple).length };
  const showOs = !!def.os && osCounts.apple > 0 && osCounts.other > 0;

  const items = useMemo(() => {
    let list = store.inDevice(deviceKey, { used, apple: os === "all" ? undefined : os === "apple" });
    if (onlyStock) list = list.filter((p) => p.inStock);
    const price = (p: Product) => p.minPrice || Number.MAX_SAFE_INTEGER;
    if (sort === "cheap") return [...list].sort((a, b) => price(a) - price(b));
    if (sort === "expensive") return [...list].sort((a, b) => (b.minPrice || 0) - (a.minPrice || 0));
    return [...list].sort(Store.byNewest);
  }, [store, deviceKey, used, os, sort, onlyStock]);

  const reset = () => setLimit(PAGE);
  return (
    <>
      <ScreenHeader title={def.label} onBack={onBack}>
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
      </ScreenHeader>

      {hasUsed && (
        <div className="segmented" role="group" aria-label="Состояние">
          {[
            [false, "Новые"],
            [true, "Б/У"],
          ].map(([value, label]) => (
            <button key={String(value)} className={`seg ${used === value ? "is-active" : ""}`} aria-pressed={used === value}
              onClick={() => { setUsed(value as boolean); setOs("all"); reset(); }}>
              {used === value && <motion.span className="seg-bg" layoutId={`seg-${deviceKey}`} transition={{ type: "spring", stiffness: 500, damping: 38 }} />}
              <span>{label as string}</span>
            </button>
          ))}
        </div>
      )}

      {showOs && (
        <div className="chips" role="group" aria-label="Операционная система">
          <Chip active={os === "all"} group={`os-${deviceKey}`} onClick={() => { setOs("all"); reset(); }}>Все</Chip>
          <Chip active={os === "apple"} group={`os-${deviceKey}`} onClick={() => { setOs("apple"); reset(); }}>
            {def.os![0]} · {osCounts.apple}
          </Chip>
          <Chip active={os === "other"} group={`os-${deviceKey}`} onClick={() => { setOs("other"); reset(); }}>
            {def.os![1]} · {osCounts.other}
          </Chip>
        </div>
      )}
      <div className="chips" role="group" aria-label="Сортировка">
        {SORTS.map((s) => (
          <Chip key={s.id} active={sort === s.id} group={`dsort-${deviceKey}`} onClick={() => setSort(s.id)}>
            {s.label}
          </Chip>
        ))}
      </div>

      {items.length ? (
        <LayoutGroup id={`dgrid-${deviceKey}`}>
          <div className="grid">
            {items.slice(0, limit).map((p, i) => (
              <ProductCard key={p.id} product={p} index={i % PAGE} onOpen={onProduct} />
            ))}
          </div>
        </LayoutGroup>
      ) : (
        <div className="empty">
          <div className="empty-icon">
            <IconBox />
          </div>
          <h2>{onlyStock ? "Сейчас нет в наличии" : "Пока пусто"}</h2>
          <p>{onlyStock ? "Выключите «Только в наличии», чтобы увидеть товары под заказ." : "Загляните позже — каталог обновляется каждый час."}</p>
        </div>
      )}
      {items.length > limit && (
        <motion.button className="load-more" whileTap={{ scale: 0.96 }} onClick={() => setLimit(limit + PAGE)}>
          Показать ещё {Math.min(PAGE, items.length - limit)}
        </motion.button>
      )}
    </>
  );
}
