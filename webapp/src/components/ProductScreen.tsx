import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";
import { isColorAttr, swatch } from "../colors";
import type { Store } from "../data";
import { rub, updatedLabel } from "../format";
import { haptic, openExternal } from "../telegram";
import type { Product, Variation } from "../types";
import { AnimatedPrice } from "./AnimatedPrice";
import { IconBell, IconCheck, IconChevron, IconExternal } from "./Icons";

/** Вариант по умолчанию: в наличии и самый дешёвый. */
function defaultVariation(p: Product, vid?: number): Variation | undefined {
  if (vid) {
    const v = p.variations.find((x) => x.id === vid);
    if (v) return v;
  }
  const score = (v: Variation) => (v.inStock ? 0 : 2) + (v.price > 0 ? 0 : 1);
  return [...p.variations].sort((a, b) => score(a) - score(b) || a.price - b.price)[0];
}

/** Значения атрибута в осмысленном порядке: память — по возрастанию цены. */
function optionValues(p: Product, attr: string): string[] {
  const seen = new Map<string, number>();
  for (const v of p.variations) {
    const val = v.attrs[attr];
    if (!val) continue;
    const price = v.price || Number.MAX_SAFE_INTEGER;
    seen.set(val, Math.min(seen.get(val) ?? Number.MAX_SAFE_INTEGER, price));
  }
  const values = [...seen.keys()];
  return isColorAttr(attr) ? values : values.sort((a, b) => (seen.get(a)! - seen.get(b)!) || a.localeCompare(b, "ru", { numeric: true }));
}

export function ProductScreen({
  store,
  id,
  vid,
  subs,
  onToggleSub,
}: {
  store: Store;
  id: number;
  vid?: number;
  subs: Set<number>;
  onToggleSub: (id: number, title: string) => void;
}) {
  const product = store.byId.get(id)!;
  const [current, setCurrent] = useState<Variation | undefined>(() => defaultVariation(product, vid));
  const [tableOpen, setTableOpen] = useState(false);

  const options = useMemo(
    () => product.attrNames.map((a) => ({ attr: a, values: optionValues(product, a) })),
    [product],
  );

  const choose = (attr: string, value: string) => {
    haptic.select();
    const wanted = { ...(current?.attrs ?? {}), [attr]: value };
    const exact = product.variations.find((v) => Object.entries(wanted).every(([k, val]) => v.attrs[k] === val));
    if (exact) return setCurrent(exact);
    // Такой комбинации нет — берём лучший вариант с выбранным значением
    const candidates = product.variations.filter((v) => v.attrs[attr] === value);
    const overlap = (v: Variation) => Object.entries(wanted).filter(([k, val]) => v.attrs[k] === val).length;
    candidates.sort((a, b) => overlap(b) - overlap(a) || Number(b.inStock) - Number(a.inStock) || a.price - b.price);
    if (candidates[0]) setCurrent(candidates[0]);
  };

  const isAvailable = (attr: string, value: string) =>
    product.variations.some(
      (v) => v.attrs[attr] === value && Object.entries(current?.attrs ?? {}).every(([k, val]) => k === attr || v.attrs[k] === val),
    );

  const price = current ? current.price : product.minPrice;
  const regular = current ? current.regular : 0;
  const inStock = current ? current.inStock : product.inStock;
  const image = current?.img || product.img;
  const configLine = current ? Object.values(current.attrs).join(" · ") : "";
  const sorted = useMemo(
    () => [...product.variations].sort((a, b) => Number(!a.price) - Number(!b.price) || a.price - b.price),
    [product],
  );

  const followAll = subs.has(product.id);
  const followCurrent = current ? subs.has(current.id) : false;
  const title = current && configLine ? `${product.name} ${configLine}` : product.name;

  return (
    <>
      <div className="pd-media">
        <AnimatePresence initial={false} mode="popLayout">
          <motion.img
            key={image}
            src={image}
            alt={product.name}
            initial={{ opacity: 0, scale: 0.9, x: 30 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            exit={{ opacity: 0, scale: 0.95, x: -30 }}
            transition={{ type: "spring", stiffness: 260, damping: 26 }}
          />
        </AnimatePresence>
      </div>

      <motion.div
        className="pd-body"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08, type: "spring", stiffness: 300, damping: 30 }}
      >
        <h1 className="pd-name">{product.name}</h1>
        <div className="pd-config">{configLine}</div>

        <div className="pd-price-row">
          <AnimatedPrice value={price} className="pd-price" />
          <AnimatePresence>
            {price > 0 && regular > price && (
              <motion.span key="old" className="pd-old" initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
                {rub(regular)}
              </motion.span>
            )}
            {price > 0 && regular > price && (
              <motion.span key="save" className="pd-save" initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ opacity: 0 }}>
                −{rub(regular - price)}
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        <motion.div key={String(inStock)} className={`stock ${inStock ? "" : "is-out"}`} initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>
          <i /> {inStock ? "В наличии" : "Нет в наличии"}
        </motion.div>

        {options.map(({ attr, values }) =>
          values.length > 0 ? (
            <div className="opt-group" key={attr} role="radiogroup" aria-label={attr}>
              <div className="opt-label">
                {attr}
                <span>{current?.attrs[attr]}</span>
              </div>
              <div className="opts">
                {values.map((val) => {
                  const selected = current?.attrs[attr] === val;
                  return (
                    <motion.button
                      key={val}
                      className={`opt ${isAvailable(attr, val) ? "" : "is-dim"}`}
                      onClick={() => choose(attr, val)}
                      whileTap={{ scale: 0.95 }}
                      role="radio"
                      aria-checked={selected}
                    >
                      {selected && <motion.span className="opt-ring" layoutId={`ring-${product.id}-${attr}`} transition={{ type: "spring", stiffness: 500, damping: 35 }} />}
                      {isColorAttr(attr) && <span className="dot" style={{ background: swatch(val) }} aria-hidden="true" />}
                      {val}
                    </motion.button>
                  );
                })}
              </div>
            </div>
          ) : null,
        )}

        <div className="pd-actions">
          {current && product.variations.length > 1 && (
            <motion.button
              className={`btn btn-primary ${followCurrent ? "is-on" : ""}`}
              whileTap={{ scale: 0.97 }}
              onClick={() => onToggleSub(current.id, title)}
            >
              {followCurrent ? <IconCheck /> : <IconBell size={20} />}
              {followCurrent ? "Слежу за этой конфигурацией" : "Следить за ценой"}
            </motion.button>
          )}
          <motion.button
            className={`btn ${product.variations.length > 1 ? "btn-dark" : "btn-primary"} ${followAll ? "is-on" : ""}`}
            whileTap={{ scale: 0.97 }}
            onClick={() => onToggleSub(product.id, product.name)}
          >
            {followAll ? <IconCheck /> : <IconBell size={20} />}
            {followAll ? "Слежу за всеми вариантами" : product.variations.length > 1 ? "Следить за всеми вариантами" : "Следить за ценой"}
          </motion.button>
          <motion.button className="btn btn-soft" whileTap={{ scale: 0.97 }} onClick={() => openExternal(product.url)}>
            Купить на сайте <IconExternal />
          </motion.button>
        </div>

        {sorted.length > 1 && (
          <div className="table">
            <button className="table-head" onClick={() => setTableOpen(!tableOpen)} aria-expanded={tableOpen}>
              Все конфигурации · {sorted.length}
              <IconChevron open={tableOpen} />
            </button>
            <AnimatePresence initial={false}>
              {tableOpen && (
                <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} style={{ overflow: "hidden" }} transition={{ type: "spring", stiffness: 300, damping: 34 }}>
                  {sorted.map((v) => (
                    <button key={v.id} className={`table-row ${v.id === current?.id ? "is-current" : ""}`} onClick={() => { haptic.select(); setCurrent(v); }}>
                      <span aria-hidden="true">{v.inStock ? "✅" : "❌"}</span>
                      <span className="t-label">{Object.values(v.attrs).join(" · ")}</span>
                      <span className="t-price">
                        {v.price > 0 && v.regular > v.price && <s>{rub(v.regular)}</s>}
                        {rub(v.price)}
                      </span>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        <p className="updated">Цены с сайта айпапа.рф · {updatedLabel(store.updatedAt)}</p>
      </motion.div>
    </>
  );
}
