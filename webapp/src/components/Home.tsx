import { motion } from "framer-motion";
import type { Store } from "../data";
import { plural, rub, updatedLabel } from "../format";
import type { Product } from "../types";
import { IconChevronRight, IconSearch, IconSwap, IconWrench } from "./Icons";
import { Img } from "./Img";
import { ProductCard } from "./ProductCard";

function Header({ updated, onSearch }: { updated: string; onSearch?: () => void }) {
  return (
    <header className="topbar">
      <div className="logo">
        <h1 className="logo-text">
          <img className="logo-img" src={`${import.meta.env.BASE_URL}brand/logo.png`} alt="айпапа.рф" width={126} height={44} />
        </h1>
        <span className="logo-sub">
          Тверь
          <br />
          {updated}
        </span>
      </div>
      <motion.button className="search-pill" onClick={onSearch} whileTap={{ scale: 0.98 }} aria-label="Поиск по каталогу">
        <IconSearch />
        <span>Айфон 17 Про, AirPods, MacBook…</span>
      </motion.button>
    </header>
  );
}

/** Каркас главной, пока нет каталога. */
export function HomeSkeleton() {
  return (
    <>
      <Header updated="загружаем цены…" />
      <div className="rail" style={{ marginTop: 12 }} aria-hidden="true">
        <div className="skeleton skeleton-hero" />
        <div className="skeleton skeleton-hero" />
      </div>
      <div className="section-head section">
        <div className="skeleton" style={{ width: 120, height: 26, borderRadius: 8 }} />
      </div>
      <div className="cat-grid" aria-hidden="true">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="skeleton skeleton-tile" />
        ))}
      </div>
    </>
  );
}

export function Home({
  store,
  onCategory,
  onProduct,
  onSearch,
  onScreen,
}: {
  store: Store;
  onCategory: (id: number) => void;
  onProduct: (p: Product) => void;
  onSearch: () => void;
  onScreen: (name: "tradein" | "service") => void;
}) {
  const featured = store.featured(8);
  const deals = store.deals(6);
  const cats = store.topCategories();
  return (
    <>
      <Header updated={updatedLabel(store.updatedAt)} onSearch={onSearch} />

      {featured.length > 0 && (
        <section className="section" style={{ marginTop: 12 }} aria-label="Витрина">
          <div className="rail">
            {featured.map((p, i) => {
              const kicker = p.maxDiscount
                ? `Выгода до ${rub(p.maxDiscount)}`
                : store.isNew(p)
                  ? "Новинка"
                  : "В наличии";
              return (
                <motion.button
                  key={p.id}
                  className="hero-card"
                  onClick={() => onProduct(p)}
                  initial={{ opacity: 0, x: 40 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: Math.min(i, 3) * 0.06, type: "spring", stiffness: 260, damping: 28 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <span className="hero-kicker">{kicker}</span>
                  <span className="hero-name">{p.name}</span>
                  <span className="hero-price">
                    {p.variations.length > 1 ? "от " : ""}
                    {rub(p.minPrice)}
                  </span>
                  {p.img && (
                    <>
                      <span className="hero-glow" aria-hidden="true" />
                      <img className="hero-img" src={p.img} alt="" loading={i < 2 ? "eager" : "lazy"} decoding="async" />
                    </>
                  )}
                </motion.button>
              );
            })}
          </div>
        </section>
      )}

      <div className="promo-grid" style={{ marginTop: 20 }}>
        <motion.button className="promo promo-dark" onClick={() => onScreen("tradein")} whileTap={{ scale: 0.97 }} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <IconSwap size={26} />
          <b>Трейд-ин</b>
          <span>Сколько стоит ваш iPhone</span>
          <IconChevronRight />
        </motion.button>
        <motion.button className="promo" onClick={() => onScreen("service")} whileTap={{ scale: 0.97 }} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <IconWrench size={26} />
          <b>Ремонт</b>
          <span>При вас за 25 минут</span>
          <IconChevronRight />
        </motion.button>
      </div>

      <section className="section" aria-labelledby="cat-title">
        <div className="section-head">
          <h2 className="section-title" id="cat-title">
            Каталог
          </h2>
        </div>
        <div className="cat-grid">
          {cats.map((c, i) => {
            const n = store.inCategory(c.id).length;
            return (
              <motion.button
                key={c.id}
                className="cat-tile"
                onClick={() => onCategory(c.id)}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.08 + Math.min(i, 12) * 0.025, type: "spring", stiffness: 400, damping: 30 }}
                whileTap={{ scale: 0.94 }}
                aria-label={`${c.name}, ${n} ${plural(n, "товар", "товара", "товаров")}`}
              >
                <Img src={store.cover(c.id)} alt="" frameClass="cat-img" />
                <span className="cat-tile-name">{c.name}</span>
                <span className="cat-tile-count">{n}</span>
              </motion.button>
            );
          })}
        </div>
      </section>

      {deals.length > 0 && (
        <section className="section" aria-labelledby="deals-title">
          <div className="section-head">
            <h2 className="section-title" id="deals-title">
              Скидки
            </h2>
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
