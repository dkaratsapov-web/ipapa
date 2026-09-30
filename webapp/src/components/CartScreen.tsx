import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import type { Store } from "../data";
import { plural, rub } from "../format";
import { lists, useLists } from "../state";
import { haptic, openExternal, sendLead } from "../telegram";
import type { Product } from "../types";
import { IconBag, IconClose, IconExternal } from "./Icons";
import { Img } from "./Img";
import { LeadForm, type Contact } from "./LeadForm";
import { ScreenHeader } from "./ScreenHeader";

export function CartScreen({
  store,
  onProduct,
  onCatalog,
  toast,
}: {
  store: Store;
  onProduct: (p: Product, vid?: number) => void;
  onCatalog: () => void;
  toast: (m: string) => void;
}) {
  const { cart } = useLists();
  const [contact, setContact] = useState<Contact>({ name: "", phone: "", comment: "" });
  const rows = cart
    .map((item) => ({ item, found: store.resolve(item.id) }))
    .filter((r): r is typeof r & { found: NonNullable<typeof r.found> } => !!r.found);
  const priceOf = (r: (typeof rows)[number]) => (r.found.variation ? r.found.variation.price : r.found.product.minPrice);
  const total = rows.reduce((s, r) => s + priceOf(r) * r.item.qty, 0);
  const onRequest = rows.some((r) => !priceOf(r));
  const count = rows.reduce((s, r) => s + r.item.qty, 0);

  const checkout = () => {
    const result = sendLead(
      { kind: "order", items: rows.map((r) => [r.item.id, r.item.qty]), ...contact },
      {},
    );
    if (result === "sent") {
      haptic.success();
      toast("Переходим в бот — там подтвердим заказ");
      lists.clearCart();
    } else if (result === "long") {
      toast("Слишком много позиций для одной ссылки — откройте магазин кнопкой в чате бота");
    } else {
      toast("Откройте приложение из бота, чтобы оформить заказ");
    }
  };

  return (
    <>
      <ScreenHeader title="Корзина" subtitle={count ? `${count} ${plural(count, "товар", "товара", "товаров")}` : undefined} />
      {rows.length === 0 ? (
        <motion.div className="empty" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="empty-icon">
            <IconBag size={32} />
          </div>
          <h2>Корзина пуста</h2>
          <p>Добавляйте товары из каталога — оформим заказ через менеджера магазина.</p>
          <motion.button className="btn btn-dark" style={{ margin: "22px auto 0", padding: "0 26px" }} whileTap={{ scale: 0.96 }} onClick={onCatalog}>
            Перейти в каталог
          </motion.button>
        </motion.div>
      ) : (
        <>
          <ul className="plain-list">
            <AnimatePresence initial={false}>
              {rows.map((r) => {
                const { product, variation } = r.found;
                const price = priceOf(r);
                return (
                  <motion.li key={r.item.id} layout className="cart-row" exit={{ opacity: 0, x: -80, height: 0 }}>
                    <button className="cart-open" onClick={() => onProduct(product, variation?.id)}>
                      <Img src={variation?.thumb || product.thumb} alt="" frameClass="row-img" />
                      <span className="row-main">
                        <span className="row-title">{product.name}</span>
                        {variation && <span className="row-sub">{Object.values(variation.attrs).join(" · ")}</span>}
                        <span className="row-price">{price ? rub(price * r.item.qty) : "Цена по запросу"}</span>
                      </span>
                    </button>
                    <div className="cart-side">
                      <button className="icon-btn" style={{ width: 32, height: 32 }} onClick={() => lists.setQty(r.item.id, 0)} aria-label={`Удалить: ${product.name}`}>
                        <IconClose size={16} />
                      </button>
                      <div className="stepper" role="group" aria-label="Количество">
                        <button onClick={() => lists.setQty(r.item.id, r.item.qty - 1)} aria-label="Меньше">−</button>
                        <motion.span key={r.item.qty} initial={{ y: -6, opacity: 0 }} animate={{ y: 0, opacity: 1 }} aria-live="polite">
                          {r.item.qty}
                        </motion.span>
                        <button onClick={() => lists.setQty(r.item.id, r.item.qty + 1)} aria-label="Больше">+</button>
                      </div>
                    </div>
                  </motion.li>
                );
              })}
            </AnimatePresence>
          </ul>

          <div className="pad">
            <div className="total-row">
              <span>Итого</span>
              <motion.b key={total} initial={{ scale: 0.9, opacity: 0.4 }} animate={{ scale: 1, opacity: 1 }}>
                {total ? rub(total) : "по запросу"}
                {onRequest && total ? " + по запросу" : ""}
              </motion.b>
            </div>
            <LeadForm value={contact} onChange={setContact} />
            <motion.button className="btn btn-primary" style={{ width: "100%", marginTop: 14 }} whileTap={{ scale: 0.97 }} onClick={checkout}>
              Оформить заказ
            </motion.button>
            <p className="form-note">Менеджер подтвердит наличие и цену, договоритесь о самовывозе или доставке. Оплата — в магазине.</p>
            {rows.length === 1 && (
              <button className="follow-all" onClick={() => openExternal(rows[0].found.product.url)}>
                Или купить на сайте <IconExternal />
              </button>
            )}
            <button className="follow-all muted" onClick={() => lists.clearCart()}>
              Очистить корзину
            </button>
          </div>
        </>
      )}
    </>
  );
}
