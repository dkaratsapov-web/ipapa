import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { useLists } from "../state";
import { HOURS, SHOP_PHONE } from "../service";
import { callPhone } from "../telegram";
import { IconBell, IconChevronRight, IconCompare, IconPhone, IconSwap, IconWrench } from "./Icons";
import { ScreenHeader } from "./ScreenHeader";

export function MoreScreen({ subsCount, go }: { subsCount: number; go: (s: "tradein" | "service" | "compare" | "subs") => void }) {
  const { compare } = useLists();
  return (
    <>
      <ScreenHeader title="Ещё" />
      <div className="promo-grid">
        <motion.button className="promo promo-dark" onClick={() => go("tradein")} whileTap={{ scale: 0.97 }} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
          <IconSwap size={28} />
          <b>Трейд-ин</b>
          <span>Узнайте, сколько стоит ваш iPhone, iPad или Watch</span>
        </motion.button>
        <motion.button className="promo" onClick={() => go("service")} whileTap={{ scale: 0.97 }} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <IconWrench size={28} />
          <b>Сервисный центр</b>
          <span>Ремонт Apple и Android при вас, гарантия до года</span>
        </motion.button>
      </div>
      <ul className="menu-list">
        <MenuRow icon={<IconCompare />} title="Сравнение" badge={compare.length} onClick={() => go("compare")} />
        <MenuRow icon={<IconBell />} title="Мои подписки на цену" badge={subsCount} onClick={() => go("subs")} />
        <MenuRow icon={<IconPhone />} title={`Позвонить в магазин`} sub={`${SHOP_PHONE} · ${HOURS}`} onClick={() => callPhone(SHOP_PHONE)} />
      </ul>
    </>
  );
}

function MenuRow({ icon, title, sub, badge, onClick }: { icon: ReactNode; title: string; sub?: string; badge?: number; onClick: () => void }) {
  return (
    <li>
      <motion.button className="menu-row" onClick={onClick} whileTap={{ scale: 0.98 }}>
        <span className="menu-icon">{icon}</span>
        <span className="row-main">
          <span className="row-title">{title}</span>
          {sub && <span className="row-sub">{sub}</span>}
        </span>
        {!!badge && <span className="menu-badge">{badge}</span>}
        <IconChevronRight />
      </motion.button>
    </li>
  );
}
