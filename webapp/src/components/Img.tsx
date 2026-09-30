import { motion } from "framer-motion";
import { useState } from "react";

/** Картинка с плавным появлением после загрузки. */
export function Img({ src, alt, layoutId, eager }: { src: string; alt: string; layoutId?: string; eager?: boolean }) {
  const [loaded, setLoaded] = useState(false);
  if (!src) return <span style={{ fontSize: 34 }} aria-hidden="true">📱</span>;
  return (
    <motion.img
      layoutId={layoutId}
      src={src}
      alt={alt}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
      onLoad={() => setLoaded(true)}
      initial={false}
      animate={{ opacity: loaded ? 1 : 0, scale: loaded ? 1 : 0.96 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    />
  );
}
