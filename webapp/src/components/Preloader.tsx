import { motion, useReducedMotion } from "framer-motion";

const BASE = import.meta.env.BASE_URL;

/** Заставка при запуске: маскот, волны, плашка «айпапа.рф» и полоса загрузки. */
export function Preloader() {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className="preloader"
      role="status"
      aria-label="Загружаем каталог"
      initial={{ opacity: 1 }}
      exit={reduce ? { opacity: 0 } : { clipPath: "circle(0% at 50% 42%)", transition: { duration: 0.55, ease: [0.7, 0, 0.3, 1] } }}
      style={{ clipPath: "circle(150% at 50% 42%)" }}
    >
      <div className="preloader-stage">
        {!reduce &&
          [0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="preloader-wave"
              initial={{ scale: 0.6, opacity: 0.5 }}
              animate={{ scale: 2.6, opacity: 0 }}
              transition={{ duration: 2.2, repeat: Infinity, delay: 0.4 + i * 0.7, ease: "easeOut" }}
            />
          ))}
        <motion.img
          className="preloader-mascot"
          src={`${BASE}brand/icon-320.webp`}
          alt=""
          initial={reduce ? false : { scale: 0.2, rotate: -25, y: 40, opacity: 0 }}
          animate={reduce ? undefined : { scale: 1, rotate: 0, y: [40, -10, 0], opacity: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 14, delay: 0.05 }}
        />
        {!reduce && (
          <motion.span
            className="preloader-glint"
            initial={{ x: "-120%" }}
            animate={{ x: "220%" }}
            transition={{ duration: 1.1, delay: 0.75, repeat: Infinity, repeatDelay: 1.6, ease: "easeInOut" }}
            aria-hidden="true"
          />
        )}
      </div>
      <motion.div
        className="preloader-badge"
        initial={reduce ? false : { y: 24, opacity: 0, scale: 0.9 }}
        animate={{ y: 0, opacity: 1, scale: 1 }}
        transition={{ delay: 0.35, type: "spring", stiffness: 320, damping: 22 }}
      >
        {"айпапа.рф".split("").map((ch, i) => (
          <motion.span
            key={i}
            className={ch === "." ? "logo-dot" : undefined}
            initial={reduce ? false : { y: 14, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.45 + i * 0.035, type: "spring", stiffness: 500, damping: 26 }}
          >
            {ch}
          </motion.span>
        ))}
      </motion.div>
      <motion.p className="preloader-tag" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
        Техника Apple и Android в Твери
      </motion.p>
      <div className="preloader-bar" aria-hidden="true">
        <motion.i initial={{ x: "-100%" }} animate={{ x: ["-100%", "0%", "100%"] }} transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }} />
      </div>
    </motion.div>
  );
}
