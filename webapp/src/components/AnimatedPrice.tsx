import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect } from "react";
import { rub } from "../format";

/** Цена, которая «докручивается» до нового значения при смене варианта. */
export function AnimatedPrice({ value, className }: { value: number; className?: string }) {
  const mv = useMotionValue(value);
  const text = useTransform(mv, (v) => rub(Math.round(v / 100) * 100));
  useEffect(() => {
    if (!value) {
      mv.set(0);
      return;
    }
    const from = mv.get() || value;
    mv.set(from);
    const controls = animate(mv, value, { duration: 0.55, ease: [0.22, 1, 0.36, 1] });
    return () => controls.stop();
  }, [value, mv]);
  if (!value) return <span className={`${className ?? ""} is-request`}>Цена по запросу</span>;
  return <motion.span className={className} aria-live="polite">{text}</motion.span>;
}
