import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState, type KeyboardEvent } from "react";
import { isColorAttr, swatch } from "../colors";
import type { Store } from "../data";
import { rub, updatedLabel } from "../format";
import { lists, useLists } from "../state";
import { botName, haptic, openExternal, shareProduct } from "../telegram";
import type { Product, Variation } from "../types";
import { AnimatedPrice } from "./AnimatedPrice";
import { IconBack, IconBag, IconBell, IconCheck, IconChevron, IconCompare, IconExternal, IconHeart, IconShare } from "./Icons";

/** Вариант по умолчанию: в наличии и самый дешёвый. */
function defaultVariation(p: Product, vid?: number): Variation | undefined {
  if (vid) {
    const v = p.variations.find((x) => x.id === vid);
    if (v) return v;
  }
  const score = (v: Variation) => (v.inStock ? 0 : 2) + (v.price > 0 ? 0 : 1);
  return [...p.variations].sort((a, b) => score(a) - score(b) || a.price - b.price)[0];
}

/** Значения атрибута: цвета — как пришли, остальное (память) — по возрастанию цены. */
function optionValues(p: Product, attr: string): string[] {
  const seen = new Map<string, number>();
  for (const v of p.variations) {
    const val = v.attrs[attr];
    if (!val) continue;
    const price = v.price || Number.MAX_SAFE_INTEGER;
    seen.set(val, Math.min(seen.get(val) ?? Number.MAX_SAFE_INTEGER, price));
  }
  const values = [...seen.keys()];
  return isColorAttr(attr)
    ? values
    : values.sort((a, b) => seen.get(a)! - seen.get(b)! || a.localeCompare(b, "ru", { numeric: true }));
}

const configOf = (v: Variation) => Object.values(v.attrs).join(" · ");

export function ProductScreen({
  store,
  id,
  vid,
  subs,
  onToggleSub,
  onBack,
  toast,
  onCart,
  onCompare,
}: {
  store: Store;
  id: number;
  vid?: number;
  subs: Set<number>;
  onToggleSub: (id: number) => void;
  onBack?: () => void;
  toast: (m: string) => void;
  onCart: () => void;
  onCompare: () => void;
}) {
  const saved = useLists();
  const product = store.byId.get(id)!;
  const [current, setCurrent] = useState<Variation | undefined>(() => defaultVariation(product, vid));
  const sorted = useMemo(
    () => [...product.variations].sort((a, b) => Number(!a.price) - Number(!b.price) || a.price - b.price),
    [product],
  );
  const [tableOpen, setTableOpen] = useState(sorted.length > 1 && sorted.length <= 6);
  const options = useMemo(
    () => product.attrNames.map((a) => ({ attr: a, values: optionValues(product, a) })).filter((o) => o.values.length > 1),
    [product],
  );

  const choose = (attr: string, value: string) => {
    haptic.select();
    const wanted = { ...(current?.attrs ?? {}), [attr]: value };
    const exact = product.variations.find((v) => Object.entries(wanted).every(([k, val]) => v.attrs[k] === val));
    if (exact) return setCurrent(exact);
    // Такой комбинации нет — берём лучший вариант с выбранным значением
    const overlap = (v: Variation) => Object.entries(wanted).filter(([k, val]) => v.attrs[k] === val).length;
    const candidates = product.variations
      .filter((v) => v.attrs[attr] === value)
      .sort((a, b) => overlap(b) - overlap(a) || Number(b.inStock) - Number(a.inStock) || a.price - b.price);
    if (candidates[0]) setCurrent(candidates[0]);
  };

  const isAvailable = (attr: string, value: string) =>
    product.variations.some(
      (v) => v.attrs[attr] === value && Object.entries(current?.attrs ?? {}).every(([k, val]) => k === attr || v.attrs[k] === val),
    );

  // Стрелки внутри группы — по паттерну WAI-ARIA radio
  const onOptionKey = (e: KeyboardEvent, attr: string, values: string[]) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const i = values.indexOf(current?.attrs[attr] ?? values[0]);
    const next = values[(i + step + values.length) % values.length];
    choose(attr, next);
    requestAnimationFrame(() =>
      (e.currentTarget as HTMLElement).querySelector<HTMLElement>(`[data-value="${CSS.escape(next)}"]`)?.focus(),
    );
  };

  const price = current ? current.price : product.minPrice;
  const regular = current ? current.regular : 0;
  const inStock = current ? current.inStock : product.inStock;
  const image = current?.img || product.img;
  const configLine = current ? configOf(current) : "";
  const hasVariants = product.variations.length > 1;
  const followId = current && hasVariants ? current.id : product.id;
  const following = subs.has(followId) || subs.has(product.id);
  const followAll = subs.has(product.id);
  const isFavorite = saved.favorites.includes(product.id);
  const inCompare = saved.compare.includes(product.id);
  const cartId = current && hasVariants ? current.id : current?.id ?? product.id;
  const inCart = saved.cart.some((i) => i.id === cartId);

  return (
    <div className="pd-page">
      <div className="pd-media">
        <div className="pd-top-actions">
          {onBack ? (
            <button className="icon-btn is-glass" onClick={onBack} aria-label="Назад">
              <IconBack />
            </button>
          ) : (
            <span />
          )}
          <span className="pd-top-right">
            {botName && (
              <motion.button
                className="icon-btn is-glass"
                whileTap={{ scale: 0.9 }}
                onClick={() => shareProduct(product.id, product.name) && toast("Выберите чат, чтобы поделиться")}
                aria-label="Поделиться"
              >
                <IconShare />
              </motion.button>
            )}
            <motion.button
              className={`icon-btn is-glass ${isFavorite ? "is-fav" : ""}`}
              whileTap={{ scale: 0.8 }}
              onClick={() => {
                haptic.tap();
                const on = lists.toggleFavorite(product.id);
                toast(on ? "Добавлено в избранное" : "Убрано из избранного");
              }}
              aria-pressed={isFavorite}
              aria-label="В избранное"
            >
              <motion.span key={String(isFavorite)} initial={{ scale: 0.4 }} animate={{ scale: [1.35, 1] }} transition={{ duration: 0.35 }}>
                <IconHeart filled={isFavorite} />
              </motion.span>
            </motion.button>
          </span>
        </div>
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
        transition={{ delay: 0.06, type: "spring", stiffness: 300, damping: 30 }}
      >
        <h1 className="pd-name">{product.name}</h1>
        <div className="pd-config">{configLine}</div>

        <div className="pd-price-row">
          <AnimatedPrice value={price} className="pd-price" />
          <AnimatePresence>
            {price > 0 && regular > price && (
              <motion.span key="old" className="pd-old" initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
                <span className="sr-only">Старая цена </span>
                {rub(regular)}
              </motion.span>
            )}
            {price > 0 && regular > price && (
              <motion.span key="save" className="pd-save" initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ opacity: 0 }}>
                −{rub(regular - price)}
              </motion.span>
            )}
          </AnimatePresence>
          <motion.span key={String(inStock)} className={`stock ${inStock ? "" : "is-out"}`} initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>
            <i /> {inStock ? "В наличии" : "Нет в наличии"}
          </motion.span>
        </div>

        {options.map(({ attr, values }) => {
          const labelId = `opt-${product.id}-${attr.replace(/\s+/g, "-")}`;
          return (
            <div className="opt-group" key={attr}>
              <div className="opt-label" id={labelId}>
                {attr}
                <span>{current?.attrs[attr]}</span>
              </div>
              <div className="opts" role="radiogroup" aria-labelledby={labelId} onKeyDown={(e) => onOptionKey(e, attr, values)}>
                {values.map((val) => {
                  const selected = current?.attrs[attr] === val;
                  const available = isAvailable(attr, val);
                  return (
                    <motion.button
                      key={val}
                      data-value={val}
                      className={`opt ${available ? "" : "is-dim"}`}
                      onClick={() => choose(attr, val)}
                      whileTap={{ scale: 0.95 }}
                      role="radio"
                      aria-checked={selected}
                      tabIndex={selected ? 0 : -1}
                    >
                      {selected && (
                        <motion.span className="opt-ring" layoutId={`ring-${product.id}-${attr}`} transition={{ type: "spring", stiffness: 500, damping: 35 }} />
                      )}
                      {isColorAttr(attr) && <span className="dot" style={{ background: swatch(val) }} aria-hidden="true" />}
                      {val}
                      {!available && <span className="sr-only"> (в другой комбинации)</span>}
                    </motion.button>
                  );
                })}
              </div>
            </div>
          );
        })}

        <div className="pd-links">
          <motion.button
            className={`chip ${inCompare ? "is-active" : ""}`}
            whileTap={{ scale: 0.94 }}
            aria-pressed={inCompare}
            onClick={() => {
              if (!lists.toggleCompare(product.id)) toast("В сравнении уже 4 товара — уберите один");
              else if (!inCompare) toast("Добавлено к сравнению");
            }}
          >
            {inCompare && <motion.span className="chip-bg" layoutId={`cmp-${product.id}`} />}
            <span>
              <IconCompare size={16} /> {inCompare ? "В сравнении" : "Сравнить"}
            </span>
          </motion.button>
          {saved.compare.length > (inCompare ? 1 : 0) && (
            <button className="chip" onClick={onCompare}>
              <span>Открыть сравнение · {saved.compare.length}</span>
            </button>
          )}
        </div>

        {product.specs.length > 0 && (
          <section className="specs" aria-labelledby={`specs-${product.id}`}>
            <h2 id={`specs-${product.id}`}>Характеристики</h2>
            <dl>
              {product.specs.map(([label, value], i) => (
                <motion.div key={label} className="spec" initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: Math.min(i, 6) * 0.03 }}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </motion.div>
              ))}
            </dl>
            {product.specsSrc && (
              <button className="spec-src" onClick={() => openExternal(product.specsSrc)}>
                По данным Википедии <IconExternal size={14} />
              </button>
            )}
          </section>
        )}

        {hasVariants && (
          <button className="follow-all" onClick={() => onToggleSub(product.id)} aria-pressed={followAll}>
            {followAll ? "✓ Вы следите за всеми вариантами" : "Следить за всеми вариантами"}
          </button>
        )}
        <p className="follow-hint">Напишем в Telegram, если цена снизится или товар появится в наличии</p>

        {sorted.length > 1 && (
          <div className="table">
            <button className="table-head" onClick={() => setTableOpen(!tableOpen)} aria-expanded={tableOpen}>
              Все варианты · {sorted.length}
              <IconChevron open={tableOpen} />
            </button>
            <AnimatePresence initial={false}>
              {tableOpen && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: "auto" }}
                  exit={{ height: 0 }}
                  style={{ overflow: "hidden" }}
                  transition={{ type: "spring", stiffness: 300, damping: 34 }}
                >
                  {sorted.map((v) => (
                    <button
                      key={v.id}
                      className={`table-row ${v.id === current?.id ? "is-current" : ""}`}
                      aria-current={v.id === current?.id ? "true" : undefined}
                      onClick={() => {
                        haptic.select();
                        setCurrent(v);
                      }}
                    >
                      <i className={`stock-dot ${v.inStock ? "" : "is-out"}`} aria-hidden="true" />
                      <span className="t-label">
                        {configOf(v)}
                        <span className="sr-only">, {v.inStock ? "в наличии" : "нет в наличии"}</span>
                      </span>
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

        <button className="follow-all" onClick={() => openExternal(product.url)}>
          Купить на сайте айпапа.рф <IconExternal size={16} />
        </button>
        <p className="updated">Цены с сайта айпапа.рф · {updatedLabel(store.updatedAt)}</p>
      </motion.div>

      <motion.div
        className="buybar"
        initial={{ y: 90 }}
        animate={{ y: 0 }}
        transition={{ delay: 0.12, type: "spring", stiffness: 380, damping: 34 }}
      >
        <motion.button
          className={`bell ${following ? "is-on" : ""}`}
          whileTap={{ scale: 0.9 }}
          onClick={() => onToggleSub(following && !subs.has(followId) ? product.id : followId)}
          aria-pressed={following}
          aria-label={following ? "Вы следите за ценой — отписаться" : "Следить за ценой"}
        >
          <motion.span key={String(following)} initial={{ rotate: -25, scale: 0.7 }} animate={{ rotate: 0, scale: 1 }} transition={{ type: "spring", stiffness: 500, damping: 12 }}>
            <IconBell filled={following} />
          </motion.span>
        </motion.button>
        {inCart ? (
          <motion.button className="btn btn-dark" whileTap={{ scale: 0.97 }} onClick={onCart} initial={{ scale: 0.96 }} animate={{ scale: 1 }}>
            <IconCheck /> В корзине — оформить
          </motion.button>
        ) : (
          <motion.button
            className="btn btn-primary"
            whileTap={{ scale: 0.97 }}
            onClick={() => {
              haptic.success();
              lists.addToCart(cartId);
              toast("Добавлено в корзину");
            }}
          >
            <IconBag size={20} />
            {price > 0 ? `В корзину · ${rub(price)}` : "В корзину"}
          </motion.button>
        )}
      </motion.div>
    </div>
  );
}
