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
  const discount = product.inStock && product.maxDiscount > 0;
  const label = [
    product.name,
    product.inStock ? "" : "нет в наличии",
    product.minPrice ? `${hasRange ? "от " : ""}${rub(product.minPrice)}` : "цена по запросу",
    discount ? `скидка до ${rub(product.maxDiscount)}` : "",
  ]
    .filter(Boolean)
    .join(", ");
  return (
    <motion.button
      layout="position"
      className="card"
      onClick={() => onOpen(product)}
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 8) * 0.03, type: "spring", stiffness: 420, damping: 36 }}
      whileTap={{ scale: 0.97 }}
      aria-label={label}
    >
      {!product.inStock ? (
        <span className="badge is-out">Нет в наличии</span>
      ) : (
        discount && <span className="badge">до −{rub(product.maxDiscount)}</span>
      )}
      <Img src={product.thumb} alt="" frameClass="card-media" />
      <span className="card-body">
        <span className="card-name">{product.name}</span>
        {colors.length > 1 && (
          <span className="swatches-mini" aria-hidden="true">
            {colors.slice(0, 6).map((c) => (
              <i key={c} style={{ background: swatch(c) }} />
            ))}
          </span>
        )}
        <span className={`card-price ${product.minPrice ? "" : "is-request"}`}>
          {hasRange && <small>от </small>}
          {rub(product.minPrice)}
        </span>
      </span>
    </motion.button>
  );
});
