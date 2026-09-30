import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "framer-motion";
import { useEffect } from "react";
import { rub } from "../format";

/** Цена «докручивается» до нового значения; скринридеру — только итоговое значение. */
export function AnimatedPrice({ value, className }: { value: number; className?: string }) {
  const mv = useMotionValue(value);
  const reduce = useReducedMotion();
  const text = useTransform(mv, (v) => rub(Math.round(v / 100) * 100));
  useEffect(() => {
    if (!value || reduce) {
      mv.set(value);
      return;
    }
    const controls = animate(mv, value, { duration: 0.55, ease: [0.22, 1, 0.36, 1] });
    return () => controls.stop();
  }, [value, mv, reduce]);
  return (
    <>
      <span className="sr-only" aria-live="polite">{rub(value)}</span>
      {value ? (
        <motion.span className={className} aria-hidden="true">{text}</motion.span>
      ) : (
        <span className={`${className ?? ""} is-request`} aria-hidden="true">Цена по запросу</span>
      )}
    </>
  );
}
