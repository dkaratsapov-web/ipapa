import { AnimatePresence, motion } from "framer-motion";
import type { Store } from "../data";
import { rub } from "../format";
import type { Product } from "../types";
import { IconBell, IconClose } from "./Icons";
import { Img } from "./Img";
import { ScreenHeader } from "./ScreenHeader";

export function SubsScreen({
  store,
  subs,
  onProduct,
  onToggleSub,
  onCatalog,
  onBack,
}: {
  store: Store;
  subs: Set<number>;
  onProduct: (p: Product, vid?: number) => void;
  onToggleSub: (id: number) => void;
  onCatalog: () => void;
  onBack?: () => void;
}) {
  const items = [...subs].map((id) => ({ id, found: store.resolve(id) }));
  return (
    <>
      <ScreenHeader title="Мои подписки" subtitle="Напишем в Telegram, когда цена изменится или товар появится в наличии" onBack={onBack} />

      {items.length === 0 ? (
        <motion.div className="empty" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <motion.div
            className="empty-icon"
            animate={{ rotate: [0, -14, 14, -8, 0] }}
            transition={{ duration: 1.1, repeat: 2, repeatDelay: 1.5 }}
          >
            <IconBell size={32} />
          </motion.div>
          <h2>Пока ни одной подписки</h2>
          <p>Откройте товар и нажмите на колокольчик — сообщим, когда цена снизится.</p>
          <motion.button className="btn btn-dark" style={{ margin: "22px auto 0", padding: "0 26px" }} whileTap={{ scale: 0.96 }} onClick={onCatalog}>
            Перейти в каталог
          </motion.button>
        </motion.div>
      ) : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
          <AnimatePresence initial={false}>
            {items.map(({ id, found }, i) => {
              const title = found ? found.product.name : "Товар больше не продаётся";
              const sub = found?.variation
                ? Object.values(found.variation.attrs).join(" · ")
                : found
                  ? "Все варианты"
                  : "Можно убрать из подписок";
              const v = found?.variation;
              const price = found ? (v ? v.price : found.product.minPrice) : 0;
              return (
                <motion.li
                  key={id}
                  layout
                  className="row"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0, transition: { delay: Math.min(i, 8) * 0.04 } }}
                  exit={{ opacity: 0, x: -60, height: 0, paddingTop: 0, paddingBottom: 0 }}
                >
                  <button
                    className="row"
                    style={{ padding: 0 }}
                    disabled={!found}
                    onClick={() => found && onProduct(found.product, v?.id)}
                  >
                    <Img src={v?.thumb || found?.product.thumb || ""} alt="" frameClass="row-img" />
                    <span className="row-main">
                      <span className="row-title" style={{ display: "block" }}>
                        {title}
                      </span>
                      <span className="row-sub" style={{ display: "block" }}>
                        {sub}
                      </span>
                      {price > 0 && (
                        <span className="row-price" style={{ display: "block", marginTop: 2 }}>
                          {v ? "" : "от "}
                          {rub(price)}
                          {v && v.regular > v.price && (
                            <s className="muted" style={{ fontWeight: 600, marginLeft: 6 }}>
                              {rub(v.regular)}
                            </s>
                          )}
                        </span>
                      )}
                    </span>
                  </button>
                  <motion.button className="icon-btn" whileTap={{ scale: 0.9 }} onClick={() => onToggleSub(id)} aria-label={`Отписаться: ${title}`}>
                    <IconClose />
                  </motion.button>
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ul>
      )}
    </>
  );
}
