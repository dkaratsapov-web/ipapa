import { AnimatePresence, motion } from "framer-motion";
import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import type { Store } from "../data";
import { plural, rub } from "../format";
import type { Product } from "../types";
import { IconClose, IconSearch } from "./Icons";
import { Img } from "./Img";

const SUGGESTIONS = ["iPhone 17 Pro", "iPhone 17", "AirPods Pro", "MacBook Air", "Apple Watch", "iPad", "Samsung", "Xiaomi", "Dyson", "PlayStation"];
const LIMIT = 60;

export function SearchScreen({
  store,
  onProduct,
  onCatalog,
  autoFocus,
}: {
  store: Store;
  onProduct: (p: Product) => void;
  onCatalog: () => void;
  autoFocus: boolean;
}) {
  const [query, setQuery] = useState("");
  const deferred = useDeferredValue(query);
  const input = useRef<HTMLInputElement>(null);
  const found = useMemo(() => store.search(deferred, LIMIT + 1), [store, deferred]);
  const results = found.slice(0, LIMIT);
  // Подсказки, по которым в каталоге что-то есть
  const suggestions = useMemo(() => SUGGESTIONS.filter((s) => store.search(s, 1).length), [store]);

  useEffect(() => {
    if (autoFocus) setTimeout(() => input.current?.focus(), 250);
  }, [autoFocus]);

  const chips = (
    <div className="suggest">
      {suggestions.map((s, i) => (
        <motion.button
          key={s}
          className="chip"
          onClick={() => setQuery(s)}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.03 }}
          whileTap={{ scale: 0.94 }}
        >
          <span>{s}</span>
        </motion.button>
      ))}
    </div>
  );

  return (
    <>
      <header className="topbar">
        <h1 className="page-title">Поиск</h1>
        <div className="search-pill">
          <IconSearch />
          <input
            ref={input}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Например, айфон 17 про 256"
            enterKeyHint="search"
            aria-label="Поиск по каталогу"
            onKeyDown={(e) => e.key === "Enter" && input.current?.blur()}
          />
          <AnimatePresence>
            {query && (
              <motion.button
                className="icon-btn"
                style={{ width: 36, height: 36, background: "transparent", marginRight: -8 }}
                onClick={() => {
                  setQuery("");
                  input.current?.focus();
                }}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                aria-label="Очистить"
              >
                <IconClose />
              </motion.button>
            )}
          </AnimatePresence>
        </div>
      </header>

      <div className="sr-only" role="status">
        {deferred.trim() ? (results.length ? `Найдено: ${found.length > LIMIT ? `больше ${LIMIT}` : results.length}` : "Ничего не нашли") : ""}
      </div>

      {!deferred.trim() ? (
        <section className="section" style={{ marginTop: 16 }} aria-labelledby="often">
          <div className="section-head">
            <h2 className="section-title" id="often" style={{ fontSize: 17 }}>
              Часто ищут
            </h2>
          </div>
          {chips}
        </section>
      ) : results.length === 0 ? (
        <motion.div className="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="empty-icon">
            <IconSearch size={30} />
          </div>
          <h2>Ничего не нашли по «{deferred.trim()}»</h2>
          <p>Проверьте написание или посмотрите похожее:</p>
          <div style={{ marginTop: 16 }}>{chips}</div>
          <motion.button className="btn btn-dark" style={{ margin: "20px auto 0", padding: "0 24px" }} whileTap={{ scale: 0.96 }} onClick={onCatalog}>
            Открыть каталог
          </motion.button>
        </motion.div>
      ) : (
        <motion.div key={deferred} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.12 }} style={{ marginTop: 4 }}>
          <div className="pad muted" style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }} aria-hidden="true">
            Найдено: {found.length > LIMIT ? `${LIMIT}+` : results.length}
          </div>
          {results.map((p, i) => (
            <motion.button
              key={p.id}
              className="row"
              onClick={() => onProduct(p)}
              initial={i < 8 ? { opacity: 0, x: 16 } : false}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(i, 8) * 0.025, type: "spring", stiffness: 420, damping: 34 }}
              whileTap={{ scale: 0.98 }}
            >
              <Img src={p.thumb} alt="" frameClass="row-img" />
              <span className="row-main">
                <span className="row-title" style={{ display: "block" }}>
                  {p.name}
                </span>
                <span className="row-sub" style={{ display: "block" }}>
                  {p.inStock ? "В наличии" : "Нет в наличии"}
                  {p.variations.length > 1 ? ` · ${p.variations.length} ${plural(p.variations.length, "вариант", "варианта", "вариантов")}` : ""}
                </span>
              </span>
              <span className="row-price">{p.minPrice ? `${p.variations.length > 1 ? "от " : ""}${rub(p.minPrice)}` : "По запросу"}</span>
            </motion.button>
          ))}
        </motion.div>
      )}
    </>
  );
}
