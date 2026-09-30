import { AnimatePresence, motion } from "framer-motion";
import type { Store } from "../data";
import { rub } from "../format";
import { botName, inTelegram } from "../telegram";
import type { Product } from "../types";
import { IconClose } from "./Icons";
import { Img } from "./Img";

export function SubsScreen({
  store,
  subs,
  onProduct,
  onToggleSub,
  onCatalog,
}: {
  store: Store;
  subs: Set<number>;
  onProduct: (p: Product, vid?: number) => void;
  onToggleSub: (id: number, title: string) => void;
  onCatalog: () => void;
}) {
  const items = [...subs].map((id) => ({ id, found: store.resolve(id) }));
  return (
    <>
      <header className="topbar">
        <h1 className="page-title">Слежу за ценой</h1>
        <div className="muted" style={{ fontWeight: 600, marginTop: 2 }}>
          Бот напишет, когда цена изменится или товар появится в наличии
        </div>
      </header>

      {items.length === 0 ? (
        <motion.div className="empty" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <motion.div className="empty-emoji" animate={{ rotate: [0, -12, 12, -6, 0] }} transition={{ duration: 1.2, repeat: Infinity, repeatDelay: 2 }}>
            🔔
          </motion.div>
          <h3>Пока ни одной подписки</h3>
          <p>Откройте товар и нажмите «Следить за ценой».</p>
          {!inTelegram && !botName && <p style={{ marginTop: 8 }}>Подписки работают, когда приложение открыто из бота.</p>}
          <motion.button className="btn btn-dark" style={{ margin: "22px auto 0", padding: "0 26px" }} whileTap={{ scale: 0.96 }} onClick={onCatalog}>
            В каталог
          </motion.button>
        </motion.div>
      ) : (
        <AnimatePresence initial={false}>
          {items.map(({ id, found }, i) => {
            const title = found ? found.product.name : `Товар #${id}`;
            const sub = found?.variation ? Object.values(found.variation.attrs).join(" · ") : found ? "Все варианты" : "Снят с продажи";
            const price = found ? (found.variation ? found.variation.price : found.product.minPrice) : 0;
            return (
              <motion.div
                key={id}
                layout
                className="row"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0, transition: { delay: i * 0.04 } }}
                exit={{ opacity: 0, x: -60, height: 0, paddingTop: 0, paddingBottom: 0 }}
              >
                <button
                  className="row"
                  style={{ padding: 0 }}
                  disabled={!found}
                  onClick={() => found && onProduct(found.product, found.variation?.id)}
                >
                  <span className="row-img">
                    <Img src={found?.variation?.thumb || found?.product.thumb || ""} alt="" />
                  </span>
                  <span className="row-main">
                    <span className="row-title" style={{ display: "block" }}>{title}</span>
                    <span className="row-sub" style={{ display: "block" }}>{sub}</span>
                    {price > 0 && <span className="row-price" style={{ display: "block", marginTop: 2 }}>{found?.variation ? "" : "от "}{rub(price)}</span>}
                  </span>
                </button>
                <motion.button className="icon-btn" whileTap={{ scale: 0.9 }} onClick={() => onToggleSub(id, title)} aria-label={`Отписаться: ${title}`}>
                  <IconClose />
                </motion.button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      )}
    </>
  );
}
