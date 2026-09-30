import { motion } from "framer-motion";
import { rub, updatedLabel } from "../format";
import type { Product } from "../types";
import type { Store } from "../data";
import { IconSearch } from "./Icons";
import { Img } from "./Img";
import { ProductCard } from "./ProductCard";

export function Home({
  store,
  onCategory,
  onProduct,
  onSearch,
}: {
  store: Store;
  onCategory: (id: number) => void;
  onProduct: (p: Product) => void;
  onSearch: () => void;
}) {
  const featured = store.featured(8);
  const deals = store.deals(6);
  const cats = store.topCategories();
  return (
    <>
      <header className="topbar">
        <div className="logo">
          <span className="logo-mark" aria-hidden="true">i</span>
          <span>
            iPapa<span className="logo-dot">.</span>
          </span>
          <span className="logo-sub">
            Тверь
            <br />
            {updatedLabel(store.updatedAt)}
          </span>
        </div>
        <motion.button className="search-pill" onClick={onSearch} whileTap={{ scale: 0.98 }}>
          <IconSearch />
          <span>iPhone 17 Pro, AirPods, MacBook…</span>
        </motion.button>
      </header>

      {featured.length > 0 && (
        <section className="section" style={{ marginTop: 12 }}>
          <div className="rail">
            {featured.map((p, i) => (
              <motion.button
                key={p.id}
                className="hero-card"
                onClick={() => onProduct(p)}
                initial={{ opacity: 0, x: 40 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06, type: "spring", stiffness: 260, damping: 28 }}
                whileTap={{ scale: 0.98 }}
              >
                <span className="hero-kicker">{p.maxDiscount ? "Выгодно" : "Новинка"}</span>
                <span className="hero-name">{p.name}</span>
                <span className="hero-price">от {rub(p.minPrice)}</span>
                {p.img && (
                  <motion.img
                    className="hero-img"
                    src={p.img}
                    alt=""
                    loading={i < 2 ? "eager" : "lazy"}
                    animate={{ y: [0, -6, 0] }}
                    transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: i * 0.3 }}
                  />
                )}
              </motion.button>
            ))}
          </div>
        </section>
      )}

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">Каталог</h2>
        </div>
        <div className="cat-grid">
          {cats.map((c, i) => (
            <motion.button
              key={c.id}
              className="cat-tile"
              onClick={() => onCategory(c.id)}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 + i * 0.03, type: "spring", stiffness: 400, damping: 30 }}
              whileTap={{ scale: 0.94 }}
            >
              <Img src={store.cover(c.id)} alt="" />
              <span className="cat-tile-name">{c.name}</span>
              <span className="cat-tile-count">{store.inCategory(c.id).length}</span>
            </motion.button>
          ))}
        </div>
      </section>

      {deals.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2 className="section-title">Скидки</h2>
          </div>
          <div className="grid">
            {deals.map((p, i) => (
              <ProductCard key={p.id} product={p} index={i} onOpen={onProduct} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
