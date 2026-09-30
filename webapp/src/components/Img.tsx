import { motion } from "framer-motion";
import { useState } from "react";
import { IconDevice } from "./Icons";

/**
 * Картинка с плавным появлением. Пока грузится — родитель мерцает (класс is-loading),
 * при ошибке — нейтральная иконка. Уже закэшированные картинки не «мигают».
 */
export function Img({ src, alt, eager, frameClass }: { src: string; alt: string; eager?: boolean; frameClass: string }) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <span className={frameClass}>
        <IconDevice />
      </span>
    );
  }
  return (
    <span className={`${frameClass} ${loaded ? "" : "is-loading"}`}>
      <motion.img
        ref={(el) => {
          if (el?.complete && el.naturalWidth && !loaded) setLoaded(true);
        }}
        src={src}
        alt={alt}
        loading={eager ? "eager" : "lazy"}
        decoding="async"
        onLoad={() => setLoaded(true)}
        onError={() => setFailed(true)}
        initial={false}
        animate={{ opacity: loaded ? 1 : 0, scale: loaded ? 1 : 0.96 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      />
    </span>
  );
}
