import { motion } from "framer-motion";
import { memo } from "react";
import { isColorAttr, swatch } from "../colors";
import { rub } from "../format";
import type { Product } from "../types";
import { Img } from "./Img";

export const ProductCard = memo(function ProductCard({
  product,
  index,
  onOpen,
}: {
  product: Product;
  index: number;
  onOpen: (p: Product) => void;
}) {
  const colorAttr = product.attrNames.find(isColorAttr);
  const colors = colorAttr ? [...new Set(product.variations.map((v) => v.attrs[colorAttr]).filter(Boolean))] : [];
  const hasRange = product.variations.length > 1 && product.minPrice > 0;
  return (
    <motion.button
      className="card"
      onClick={() => onOpen(product)}
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 12) * 0.035, type: "spring", stiffness: 380, damping: 32 }}
      whileTap={{ scale: 0.97 }}
      aria-label={`${product.name}, ${product.minPrice ? rub(product.minPrice) : "цена по запросу"}`}
    >
      {product.maxDiscount > 0 && <span className="badge">−{rub(product.maxDiscount)}</span>}
      {!product.inStock && <span className="badge is-out">Нет в наличии</span>}
      <div className="card-media">
        <Img src={product.thumb} alt="" />
      </div>
      <div className="card-body">
        <div className="card-name">{product.name}</div>
        {colors.length > 1 && (
          <div className="swatches-mini" aria-hidden="true">
            {colors.slice(0, 6).map((c) => (
              <i key={c} style={{ background: swatch(c) }} />
            ))}
          </div>
        )}
        <div className={`card-price ${product.minPrice ? "" : "is-request"}`}>
          {hasRange && <small>от </small>}
          {rub(product.minPrice)}
        </div>
      </div>
    </motion.button>
  );
});
