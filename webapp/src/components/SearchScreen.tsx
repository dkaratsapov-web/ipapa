import { AnimatePresence, motion } from "framer-motion";
import { useDeferredValue, useEffect, useRef, useState } from "react";
import type { Store } from "../data";
import { rub } from "../format";
import type { Product } from "../types";
import { IconClose, IconSearch } from "./Icons";
import { Img } from "./Img";

const SUGGESTIONS = ["iPhone 17 Pro", "iPhone 17", "AirPods Pro", "MacBook Air", "Apple Watch", "Samsung S25", "Dyson", "PlayStation"];

export function SearchScreen({ store, onProduct, autoFocus }: { store: Store; onProduct: (p: Product) => void; autoFocus: boolean }) {
  const [query, setQuery] = useState("");
  const deferred = useDeferredValue(query);
  const input = useRef<HTMLInputElement>(null);
  const results = store.search(deferred);

  useEffect(() => {
    if (autoFocus) setTimeout(() => input.current?.focus(), 250);
  }, [autoFocus]);

  return (
    <>
      <header className="topbar">
        <h1 className="page-title">Поиск</h1>
        <label className="search-pill">
          <IconSearch />
          <input
            ref={input}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Например, iphone 17 pro 256"
            enterKeyHint="search"
            aria-label="Поиск по каталогу"
            onKeyDown={(e) => e.key === "Enter" && input.current?.blur()}
          />
          <AnimatePresence>
            {query && (
              <motion.button
                className="icon-btn"
                style={{ width: 28, height: 28, background: "transparent" }}
                onClick={() => setQuery("")}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                aria-label="Очистить"
              >
                <IconClose />
              </motion.button>
            )}
          </AnimatePresence>
        </label>
      </header>

      {!deferred.trim() ? (
        <section className="section" style={{ marginTop: 16 }}>
          <div className="section-head">
            <h2 className="section-title" style={{ fontSize: 17 }}>Часто ищут</h2>
          </div>
          <div className="suggest">
            {SUGGESTIONS.map((s, i) => (
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
        </section>
      ) : results.length === 0 ? (
        <motion.div className="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="empty-emoji">🔍</div>
          <h3>Ничего не нашлось</h3>
          <p>Попробуйте написать короче, например «iphone 17».</p>
        </motion.div>
      ) : (
        <div style={{ marginTop: 4 }}>
          <div className="pad muted" style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
            Найдено: {results.length}
          </div>
          <AnimatePresence initial={false}>
            {results.map((p) => (
              <motion.button
                key={p.id}
                layout="position"
                className="row"
                onClick={() => onProduct(p)}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
                whileTap={{ scale: 0.98 }}
              >
                <span className="row-img">
                  <Img src={p.thumb} alt="" />
                </span>
                <span className="row-main">
                  <span className="row-title">{p.name}</span>
                  <span className="row-sub" style={{ display: "block" }}>
                    {p.inStock ? "В наличии" : "Нет в наличии"}
                    {p.variations.length > 1 ? ` · ${p.variations.length} вариантов` : ""}
                  </span>
                </span>
                <span className="row-price">{p.minPrice ? `${p.variations.length > 1 ? "от " : ""}${rub(p.minPrice)}` : "—"}</span>
              </motion.button>
            ))}
          </AnimatePresence>
        </div>
      )}
    </>
  );
}
