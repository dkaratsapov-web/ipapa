import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { plural } from "../format";
import { IconBag, IconGrid, IconHeart, IconHome, IconSearch } from "./Icons";

export type Tab = "home" | "search" | "favorites" | "cart" | "more";

const TABS: { id: Tab; label: string; icon: ReactNode }[] = [
  { id: "home", label: "Каталог", icon: <IconHome /> },
  { id: "search", label: "Поиск", icon: <IconSearch size={22} /> },
  { id: "favorites", label: "Избранное", icon: <IconHeart /> },
  { id: "cart", label: "Корзина", icon: <IconBag /> },
  { id: "more", label: "Ещё", icon: <IconGrid /> },
];

export function TabBar({
  active,
  onChange,
  counts,
  hidden,
}: {
  active: Tab;
  onChange: (t: Tab) => void;
  counts: Partial<Record<Tab, number>>;
  hidden: boolean;
}) {
  return (
    <motion.nav
      className="tabbar"
      aria-label="Разделы"
      initial={false}
      animate={{ y: hidden ? 130 : 0 }}
      transition={{ type: "spring", stiffness: 420, damping: 40 }}
      inert={hidden}
    >
      {TABS.map((t) => {
        const n = counts[t.id] ?? 0;
        return (
          <motion.button
            key={t.id}
            className={`tab ${active === t.id ? "is-active" : ""}`}
            onClick={() => onChange(t.id)}
            whileTap={{ scale: 0.92 }}
            aria-current={active === t.id ? "page" : undefined}
            aria-label={n ? `${t.label}, ${n} ${plural(n, "товар", "товара", "товаров")}` : undefined}
          >
            {active === t.id && (
              <motion.span className="tab-bg" layoutId="tab-bg" transition={{ type: "spring", stiffness: 500, damping: 38 }} />
            )}
            {t.icon}
            <span>{t.label}</span>
            {n > 0 && (
              <motion.span className="tab-count" key={n} initial={{ scale: 0.4 }} animate={{ scale: [1.3, 1] }} aria-hidden="true">
                {n}
              </motion.span>
            )}
          </motion.button>
        );
      })}
    </motion.nav>
  );
}
