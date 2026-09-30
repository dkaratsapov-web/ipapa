import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { IconBell, IconHome, IconSearch } from "./Icons";

export type Tab = "home" | "search" | "subs";

const TABS: { id: Tab; label: string; icon: ReactNode }[] = [
  { id: "home", label: "Каталог", icon: <IconHome /> },
  { id: "search", label: "Поиск", icon: <IconSearch size={22} /> },
  { id: "subs", label: "Слежу", icon: <IconBell /> },
];

export function TabBar({ active, onChange, subsCount }: { active: Tab; onChange: (t: Tab) => void; subsCount: number }) {
  return (
    <nav className="tabbar" aria-label="Разделы">
      {TABS.map((t) => (
        <motion.button
          key={t.id}
          className={`tab ${active === t.id ? "is-active" : ""}`}
          onClick={() => onChange(t.id)}
          whileTap={{ scale: 0.92 }}
          aria-current={active === t.id ? "page" : undefined}
        >
          {active === t.id && (
            <motion.span className="tab-bg" layoutId="tab-bg" transition={{ type: "spring", stiffness: 500, damping: 38 }} />
          )}
          {t.icon}
          <span>{t.label}</span>
          {t.id === "subs" && subsCount > 0 && (
            <motion.span className="tab-count" key={subsCount} initial={{ scale: 0.4 }} animate={{ scale: 1 }}>
              {subsCount}
            </motion.span>
          )}
        </motion.button>
      ))}
    </nav>
  );
}
