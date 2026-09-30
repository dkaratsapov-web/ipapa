import { motion } from "framer-motion";
import type { Store } from "../data";
import { plural } from "../format";
import { useLists } from "../state";
import type { Product } from "../types";
import { IconHeart } from "./Icons";
import { ProductCard } from "./ProductCard";
import { ScreenHeader } from "./ScreenHeader";

export function FavoritesScreen({ store, onProduct, onCatalog }: { store: Store; onProduct: (p: Product) => void; onCatalog: () => void }) {
  const { favorites } = useLists();
  const items = favorites.map((id) => store.byId.get(id)).filter((p): p is Product => !!p);
  return (
    <>
      <ScreenHeader title="Избранное" subtitle={items.length ? `${items.length} ${plural(items.length, "товар", "товара", "товаров")}` : undefined} />
      {items.length ? (
        <div className="grid" style={{ marginTop: 8 }}>
          {items.map((p, i) => (
            <ProductCard key={p.id} product={p} index={i} onOpen={onProduct} />
          ))}
        </div>
      ) : (
        <motion.div className="empty" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <motion.div className="empty-icon" animate={{ scale: [1, 1.12, 1] }} transition={{ duration: 0.9, repeat: 2, repeatDelay: 1 }}>
            <IconHeart size={32} />
          </motion.div>
          <h2>Здесь будут любимые товары</h2>
          <p>Нажмите на сердечко в карточке товара, чтобы вернуться к нему позже.</p>
          <motion.button className="btn btn-dark" style={{ margin: "22px auto 0", padding: "0 26px" }} whileTap={{ scale: 0.96 }} onClick={onCatalog}>
            Перейти в каталог
          </motion.button>
        </motion.div>
      )}
    </>
  );
}
