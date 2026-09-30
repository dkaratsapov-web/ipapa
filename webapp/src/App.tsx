import { AnimatePresence, motion, type PanInfo } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { CategoryScreen } from "./components/CategoryScreen";
import { Home } from "./components/Home";
import { ProductScreen } from "./components/ProductScreen";
import { SearchScreen } from "./components/SearchScreen";
import { SubsScreen } from "./components/SubsScreen";
import { TabBar, type Tab } from "./components/TabBar";
import { Toast } from "./components/Toast";
import { loadCatalog, Store } from "./data";
import { haptic, inTelegram, initialSubs, keyboardMode, sendSubscription, startProduct, bindBackButton } from "./telegram";
import type { Product, Screen } from "./types";

type Mode = "push" | "pop" | "tab";
interface Entry {
  key: number;
  screen: Screen;
}

let nextKey = 1;
const entry = (screen: Screen): Entry => ({ key: nextKey++, screen });
const ROOTS: Record<Tab, Screen> = { home: { name: "home" }, search: { name: "search" }, subs: { name: "subs" } };

const frame = {
  enter: (mode: Mode) => (mode === "tab" ? { opacity: 0, y: 14, x: 0 } : { x: "100%", opacity: 1, y: 0 }),
  center: { x: 0, y: 0, opacity: 1, transition: { type: "spring" as const, stiffness: 380, damping: 40 } },
  under: { x: "-24%", y: 0, opacity: 1, transition: { type: "spring" as const, stiffness: 380, damping: 40 } },
  exit: (mode: Mode) =>
    mode === "tab"
      ? { opacity: 0, transition: { duration: 0.12 } }
      : { x: "100%", transition: { type: "spring" as const, stiffness: 420, damping: 42 } },
};

export default function App() {
  const [store, setStore] = useState<Store | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("home");
  const [stack, setStack] = useState<Entry[]>(() => [entry(ROOTS.home)]);
  const [mode, setMode] = useState<Mode>("push");
  const [subs, setSubs] = useState<Set<number>>(initialSubs);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<number | undefined>(undefined);

  const load = useCallback(() => {
    setError(null);
    loadCatalog()
      .then((c) => {
        const s = new Store(c);
        setStore(s);
        if (startProduct && s.resolve(startProduct)) {
          const r = s.resolve(startProduct)!;
          setStack((st) => [...st, entry({ name: "product", id: r.product.id, vid: r.variation?.id })]);
        }
      })
      .catch((e: Error) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  const showToast = (msg: string) => {
    setToast(msg);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 2600);
  };

  const push = useCallback((screen: Screen) => {
    haptic.tap();
    setMode("push");
    setStack((s) => [...s, entry(screen)]);
  }, []);

  const pop = useCallback(() => {
    setMode("pop");
    setStack((s) => (s.length > 1 ? s.slice(0, -1) : s));
  }, []);

  const switchTab = (t: Tab) => {
    haptic.select();
    if (t === tab && stack.length > 1) {
      setMode("pop");
      setStack((s) => s.slice(0, 1));
      return;
    }
    if (t === tab) return;
    setMode("tab");
    setTab(t);
    setStack([entry(ROOTS[t])]);
  };

  useEffect(() => bindBackButton(stack.length > 1, pop), [stack.length, pop]);

  const openProduct = useCallback((p: Product, vid?: number) => push({ name: "product", id: p.id, vid }), [push]);

  const toggleSub = (id: number, title: string) => {
    const on = !subs.has(id);
    haptic.success();
    setSubs((s) => {
      const n = new Set(s);
      if (on) n.add(id);
      else n.delete(id);
      return n;
    });
    const result = sendSubscription(on ? "sub" : "unsub", id);
    if (result === "unavailable") {
      showToast(inTelegram ? "Откройте приложение из бота, чтобы подписаться" : `${on ? "Подписка" : "Отписка"}: ${title} (демо)`);
    } else if (result === "link" || keyboardMode) {
      showToast(on ? "🔔 Отправляю подписку в бота…" : "Отменяю подписку…");
    }
  };

  const onDragEnd = (_: unknown, info: PanInfo) => {
    if (info.offset.x > 110 || info.velocity.x > 600) pop();
  };

  if (error) {
    return (
      <div className="error-box">
        <div className="empty-emoji">📡</div>
        <h3>Не удалось загрузить каталог</h3>
        <p className="muted">{error}</p>
        <motion.button className="btn btn-dark" style={{ margin: "20px auto 0", padding: "0 28px" }} whileTap={{ scale: 0.96 }} onClick={load}>
          Повторить
        </motion.button>
      </div>
    );
  }

  const render = (screen: Screen, isTop: boolean) => {
    if (!store) return null;
    switch (screen.name) {
      case "home":
        return <Home store={store} onCategory={(id) => push({ name: "category", id })} onProduct={openProduct} onSearch={() => switchTab("search")} />;
      case "category":
        return <CategoryScreen store={store} id={screen.id} onProduct={openProduct} />;
      case "product":
        return <ProductScreen store={store} id={screen.id} vid={screen.vid} subs={subs} onToggleSub={toggleSub} />;
      case "search":
        return <SearchScreen store={store} onProduct={openProduct} autoFocus={isTop && mode === "tab"} />;
      case "subs":
        return <SubsScreen store={store} subs={subs} onProduct={openProduct} onToggleSub={toggleSub} onCatalog={() => switchTab("home")} />;
    }
  };

  return (
    <div className="app">
      <AnimatePresence>
        {!store && (
          <motion.div className="splash" exit={{ opacity: 0, scale: 1.04 }} transition={{ duration: 0.35 }}>
            <motion.div className="logo" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <motion.span
                className="logo-mark"
                animate={{ rotate: [0, 0, 360], scale: [1, 1.08, 1] }}
                transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
              >
                i
              </motion.span>
              <span>
                iPapa<span className="logo-dot">.</span>
              </span>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {store && (
        <AnimatePresence initial={false} custom={mode}>
          {stack.map((e, i) => {
            const isTop = i === stack.length - 1;
            return (
              <motion.main
                key={e.key}
                className={`screen ${isTop ? "" : "is-under"}`}
                custom={mode}
                variants={frame}
                initial={i === 0 && mode !== "tab" ? false : "enter"}
                animate={isTop ? "center" : "under"}
                exit="exit"
                style={{ zIndex: i + 1, boxShadow: isTop && i > 0 ? "-12px 0 40px rgba(7,7,9,.10)" : undefined }}
                drag={isTop && i > 0 ? "x" : false}
                dragDirectionLock
                dragConstraints={{ left: 0, right: 0 }}
                dragElastic={{ left: 0, right: 0.9 }}
                onDragEnd={onDragEnd}
                aria-hidden={!isTop}
              >
                {render(e.screen, isTop)}
              </motion.main>
            );
          })}
        </AnimatePresence>
      )}

      {store && <TabBar active={tab} onChange={switchTab} subsCount={subs.size} />}
      <Toast message={toast} />
    </div>
  );
}
