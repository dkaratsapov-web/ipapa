import { AnimatePresence, motion, useDragControls, type PanInfo } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { CategoryScreen } from "./components/CategoryScreen";
import { DeviceScreen } from "./components/DeviceScreen";
import { Home, HomeSkeleton } from "./components/Home";
import { Preloader } from "./components/Preloader";
import { IconWifiOff } from "./components/Icons";
import { ProductScreen } from "./components/ProductScreen";
import { SearchScreen } from "./components/SearchScreen";
import { SubsScreen } from "./components/SubsScreen";
import { TabBar, type Tab } from "./components/TabBar";
import { CartScreen } from "./components/CartScreen";
import { CompareScreen } from "./components/CompareScreen";
import { FavoritesScreen } from "./components/FavoritesScreen";
import { MoreScreen } from "./components/MoreScreen";
import { ServiceScreen } from "./components/ServiceScreen";
import { TradeInScreen } from "./components/TradeInScreen";
import { useLists } from "./state";
import { Toast } from "./components/Toast";
import { cachedCatalog, loadCatalog, Store } from "./data";
import {
  bindBackButton,
  canSaveSubscriptions,
  haptic,
  inTelegram,
  initialSubs,
  saveSubscriptions,
  startProduct,
} from "./telegram";
import type { Product, Screen } from "./types";

type Mode = "push" | "pop" | "tab";
interface Entry {
  key: number;
  screen: Screen;
  opener?: HTMLElement | null;
}

let nextKey = 1;
const entry = (screen: Screen, opener?: HTMLElement | null): Entry => ({ key: nextKey++, screen, opener });
const ROOTS: Record<Tab, Screen> = {
  home: { name: "home" },
  search: { name: "search" },
  favorites: { name: "favorites" },
  cart: { name: "cart" },
  more: { name: "more" },
};
const PENDING_KEY = "ipapa-pending-subs";

const spring = { type: "spring" as const, stiffness: 380, damping: 40 };
const frame = {
  enter: (mode: Mode) => (mode === "tab" ? { opacity: 0, y: 14, x: 0 } : { x: "100%", opacity: 1, y: 0 }),
  center: { x: 0, y: 0, opacity: 1, transition: spring },
  under: { x: "-24%", y: 0, opacity: 1, transition: spring },
  exit: (mode: Mode) =>
    mode === "tab" ? { opacity: 0, transition: { duration: 0.12 } } : { x: "100%", transition: { ...spring, stiffness: 420 } },
};

function loadPending(): Map<number, boolean> {
  try {
    return new Map(JSON.parse(localStorage.getItem(PENDING_KEY) || "[]"));
  } catch {
    return new Map();
  }
}

function savePending(pending: Map<number, boolean>): void {
  try {
    localStorage.setItem(PENDING_KEY, JSON.stringify([...pending]));
  } catch {
    /* не критично */
  }
}

export default function App() {
  const [store, setStore] = useState<Store | null>(() => {
    const cached = cachedCatalog();
    return cached ? new Store(cached) : null;
  });
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("home");
  const [stack, setStack] = useState<Entry[]>(() => [entry(ROOTS.home)]);
  const [mode, setMode] = useState<Mode>("push");
  const [confirmed, setConfirmed] = useState<Set<number>>(initialSubs);
  // Изменения подписок, ещё не отправленные в бота: id -> подписаться/отписаться
  const [pending, setPending] = useState<Map<number, boolean>>(() => {
    const p = loadPending();
    for (const [id, on] of p) if (initialSubs.has(id) === on) p.delete(id); // бот уже учёл
    return p;
  });
  const [toast, setToast] = useState<string | null>(null);
  const [typing, setTyping] = useState(false);
  // Заставка: не меньше 1,4 с (чтобы анимация успела отыграть) и пока нет каталога
  const [introDone, setIntroDone] = useState(false);
  useEffect(() => {
    const t = window.setTimeout(() => setIntroDone(true), 1400);
    return () => window.clearTimeout(t);
  }, []);
  const lists = useLists();
  const toastTimer = useRef<number | undefined>(undefined);
  const screens = useRef(new Map<number, HTMLElement>());
  const openedStart = useRef(false);

  const load = useCallback(() => {
    setError(null);
    loadCatalog()
      .then((c) => setStore(new Store(c)))
      .catch((e: Error) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  // Открыть товар из ссылки (?p= или start_param), когда каталог готов
  useEffect(() => {
    if (!store || openedStart.current || !startProduct) return;
    openedStart.current = true;
    const r = store.resolve(startProduct);
    if (r) setStack((s) => [...s, entry({ name: "product", id: r.product.id, vid: r.variation?.id })]);
  }, [store]);

  useEffect(() => savePending(pending), [pending]);

  const subs = useMemo(() => {
    const s = new Set(confirmed);
    for (const [id, on] of pending) {
      if (on) s.add(id);
      else s.delete(id);
    }
    return s;
  }, [confirmed, pending]);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 2800);
  }, []);

  const push = useCallback((screen: Screen) => {
    haptic.tap();
    setMode("push");
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setStack((s) => [...s, entry(screen, opener)]);
  }, []);

  const pop = useCallback(() => {
    setMode("pop");
    setStack((s) => {
      if (s.length < 2) return s;
      const top = s[s.length - 1];
      requestAnimationFrame(() => top.opener?.focus({ preventScroll: true }));
      return s.slice(0, -1);
    });
  }, []);

  const switchTab = useCallback(
    (t: Tab) => {
      haptic.select();
      if (t === tab) {
        if (stack.length > 1) {
          setMode("pop");
          setStack((s) => s.slice(0, 1));
        }
        return;
      }
      setMode("tab");
      setTab(t);
      setStack([entry(ROOTS[t])]);
    },
    [tab, stack.length],
  );

  useEffect(() => bindBackButton(stack.length > 1, pop), [stack.length, pop]);

  // Esc — назад (клавиатура, браузер)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && stack.length > 1) pop();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [stack.length, pop]);

  // Таббар прячется, пока открыта клавиатура
  useEffect(() => {
    const isInput = (el: EventTarget | null) => el instanceof HTMLInputElement;
    const onIn = (e: FocusEvent) => isInput(e.target) && setTyping(true);
    const onOut = (e: FocusEvent) => isInput(e.target) && setTyping(false);
    document.addEventListener("focusin", onIn);
    document.addEventListener("focusout", onOut);
    return () => {
      document.removeEventListener("focusin", onIn);
      document.removeEventListener("focusout", onOut);
    };
  }, []);

  // Фокус на заголовок нового экрана после перехода вперёд
  const topKey = stack[stack.length - 1].key;
  const navigated = useRef(false);
  useEffect(() => {
    // при первом показе фокус не трогаем — только после переходов
    if (!navigated.current) {
      navigated.current = stack.length > 1 || mode === "tab";
      if (!navigated.current) return;
    }
    if (mode === "pop" || !store) return;
    const el = screens.current.get(topKey)?.querySelector<HTMLElement>("h1");
    if (el && !el.closest(".topbar")?.querySelector("input")) {
      el.tabIndex = -1;
      el.focus({ preventScroll: true });
    }
  }, [topKey, mode, store, stack.length]);

  const openProduct = useCallback((p: Product, vid?: number) => push({ name: "product", id: p.id, vid }), [push]);

  const toggleSub = useCallback(
    (id: number) => {
      haptic.success();
      const on = !subs.has(id);
      if (!canSaveSubscriptions) {
        // Демо в браузере без бота: только локально
        setConfirmed((c) => {
          const n = new Set(c);
          if (on) n.add(id);
          else n.delete(id);
          return n;
        });
        showToast(on ? "Подписка сохранится, когда откроете приложение из бота" : "Подписка убрана");
        return;
      }
      setPending((p) => {
        const n = new Map(p);
        if (confirmed.has(id) === on) n.delete(id);
        else n.set(id, on);
        return n;
      });
    },
    [subs, confirmed, showToast],
  );

  const commitPending = () => {
    const sub = [...pending].filter(([, on]) => on).map(([id]) => id);
    const unsub = [...pending].filter(([, on]) => !on).map(([id]) => id);
    const sent = saveSubscriptions(sub, unsub);
    if (!sent) return;
    haptic.success();
    showToast("Переходим в бот — там подтвердим подписку");
    setPending((p) => {
      const n = new Map(p);
      [...sent.sub, ...sent.unsub].forEach((id) => n.delete(id));
      return n;
    });
    setConfirmed((c) => {
      const n = new Set(c);
      sent.sub.forEach((id) => n.add(id));
      sent.unsub.forEach((id) => n.delete(id));
      return n;
    });
  };

  const top = stack[stack.length - 1].screen;
  const onProductScreen = top.name === "product";
  const back = !inTelegram && stack.length > 1 ? pop : undefined;

  const render = (screen: Screen, isTop: boolean): ReactNode => {
    if (!store) return <HomeSkeleton />;
    const toHome = () => switchTab("home");
    switch (screen.name) {
      case "home":
        return (
          <Home
            store={store}
            onCategory={(id) => push({ name: "category", id })}
            onProduct={openProduct}
            onSearch={() => switchTab("search")}
            onScreen={(name: "tradein" | "service") => push({ name })}
            onDevice={(key) => push({ name: "device", key })}
          />
        );
      case "device":
        return <DeviceScreen store={store} deviceKey={screen.key} onProduct={openProduct} onBack={back} />;
      case "category":
        return <CategoryScreen store={store} id={screen.id} onProduct={openProduct} onBack={back} />;
      case "product":
        return (
          <ProductScreen
            store={store}
            id={screen.id}
            vid={screen.vid}
            subs={subs}
            onToggleSub={toggleSub}
            onBack={back}
            toast={showToast}
            onCart={() => switchTab("cart")}
            onCompare={() => push({ name: "compare" })}
          />
        );
      case "search":
        return <SearchScreen store={store} onProduct={openProduct} onCatalog={toHome} autoFocus={isTop && mode === "tab"} />;
      case "subs":
        return <SubsScreen store={store} subs={subs} onProduct={openProduct} onToggleSub={toggleSub} onCatalog={toHome} onBack={back} />;
      case "favorites":
        return <FavoritesScreen store={store} onProduct={openProduct} onCatalog={toHome} />;
      case "cart":
        return <CartScreen store={store} onProduct={openProduct} onCatalog={toHome} toast={showToast} />;
      case "compare":
        return <CompareScreen store={store} onProduct={openProduct} onCatalog={toHome} onBack={back} />;
      case "more":
        return <MoreScreen subsCount={subs.size} go={(name) => push({ name })} />;
      case "service":
        return <ServiceScreen onBack={back} toast={showToast} />;
      case "tradein":
        return <TradeInScreen store={store} onBack={back} onCatalog={toHome} toast={showToast} />;
    }
  };

  if (error && !store) {
    return (
      <main className="error-box">
        <div className="empty-icon">
          <IconWifiOff />
        </div>
        <h1 style={{ fontSize: 20, margin: "14px 0 6px" }}>Не удалось загрузить каталог</h1>
        <p className="muted">{error}</p>
        <motion.button className="btn btn-dark" style={{ margin: "20px auto 0", padding: "0 28px" }} whileTap={{ scale: 0.96 }} onClick={load}>
          Повторить
        </motion.button>
      </main>
    );
  }

  const pendingCount = pending.size;
  return (
    <div className="app" aria-busy={!store}>
      <AnimatePresence initial={false} custom={mode}>
        {stack.map((e, i) => (
          <ScreenFrame
            key={e.key}
            index={i}
            isTop={i === stack.length - 1}
            mode={mode}
            noTabbar={e.screen.name === "product"}
            onPop={pop}
            register={(el) => {
              if (el) screens.current.set(e.key, el);
              else screens.current.delete(e.key);
            }}
          >
            {render(e.screen, i === stack.length - 1)}
          </ScreenFrame>
        ))}
      </AnimatePresence>

      <TabBar
        active={tab}
        onChange={switchTab}
        counts={{ favorites: lists.favorites.length, cart: lists.cart.reduce((n, i) => n + i.qty, 0) }}
        hidden={onProductScreen || typing}
      />

      <AnimatePresence>
        {pendingCount > 0 && !typing && (
          <motion.div
            className={`savebar ${onProductScreen ? "is-low" : ""}`}
            initial={{ y: 40, opacity: 0, scale: 0.96 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
          >
            <motion.button className="btn btn-dark" whileTap={{ scale: 0.97 }} onClick={commitPending}>
              <span>
                Сохранить подписки · {pendingCount}
                <small>Подтвердим в чате с ботом</small>
              </span>
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      <Toast message={toast} />
      <AnimatePresence>{(!introDone || !store) && !error && <Preloader key="preloader" />}</AnimatePresence>
    </div>
  );
}

/** Экран стека: нижние — inert (недоступны для фокуса и скринридера). */
function ScreenFrame({
  index,
  isTop,
  mode,
  noTabbar,
  onPop,
  register,
  children,
}: {
  index: number;
  isTop: boolean;
  mode: Mode;
  noTabbar: boolean;
  onPop: () => void;
  register: (el: HTMLElement | null) => void;
  children: ReactNode;
}) {
  const controls = useDragControls();
  const canSwipe = isTop && index > 0;
  const onDragEnd = (_: unknown, info: PanInfo) => {
    if (info.offset.x > 110 || info.velocity.x > 600) onPop();
  };
  // Один и тот же тег (иначе React пересоздаст экран и потеряет прокрутку); роль main — только у верхнего
  return (
    <motion.section
      ref={register}
      role={isTop ? "main" : undefined}
      className={`screen ${isTop ? "" : "is-under"} ${noTabbar ? "no-tabbar" : ""}`}
      custom={mode}
      variants={frame}
      initial={index === 0 && mode !== "tab" ? false : "enter"}
      animate={isTop ? "center" : "under"}
      exit="exit"
      style={{ zIndex: index + 1, boxShadow: isTop && index > 0 ? "-12px 0 40px rgba(7,7,9,.10)" : undefined }}
      drag={canSwipe ? "x" : false}
      dragListener={false}
      dragControls={controls}
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={{ left: 0, right: 0.9 }}
      onDragEnd={onDragEnd}
      inert={!isTop}
    >
      {/* свайп «назад» — только от левого края, чтобы не мешать горизонтальным лентам */}
      {canSwipe && <div className="edge" onPointerDown={(e) => controls.start(e)} aria-hidden="true" />}
      <div className="screen-scroll">{children}</div>
    </motion.section>
  );
}
