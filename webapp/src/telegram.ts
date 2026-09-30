/** Тонкая обёртка над Telegram WebApp SDK; вне Telegram все вызовы безопасны. */
interface TgWebApp {
  initData: string;
  initDataUnsafe?: { start_param?: string };
  platform: string;
  ready(): void;
  expand(): void;
  close(): void;
  sendData(data: string): void;
  openLink(url: string): void;
  openTelegramLink(url: string): void;
  showConfirm?(message: string, cb: (ok: boolean) => void): void;
  setHeaderColor(color: string): void;
  setBackgroundColor(color: string): void;
  setBottomBarColor?(color: string): void;
  disableVerticalSwipes?(): void;
  isVersionAtLeast(v: string): boolean;
  BackButton: { show(): void; hide(): void; onClick(cb: () => void): void; offClick(cb: () => void): void };
  HapticFeedback: {
    impactOccurred(style: "light" | "medium" | "heavy" | "rigid" | "soft"): void;
    selectionChanged(): void;
    notificationOccurred(type: "error" | "success" | "warning"): void;
  };
}

declare global {
  interface Window {
    Telegram?: { WebApp: TgWebApp };
  }
}

const tg: TgWebApp | null = window.Telegram?.WebApp ?? null;
/** SDK подключается и в обычном браузере, но platform там "unknown" */
export const inTelegram = !!tg && !!tg.platform && tg.platform !== "unknown";

const params = new URLSearchParams(location.search);
export const botName = params.get("bot") || "";
/** m=kb — открыто кнопкой клавиатуры: доступен sendData */
export const keyboardMode = inTelegram && params.get("m") === "kb";
export const initialSubs = new Set(
  (params.get("subs") || "").split(",").map(Number).filter((n) => Number.isFinite(n) && n > 0),
);
const startParam = tg?.initDataUnsafe?.start_param || "";
export const startProduct = Number(params.get("p")) || Number(startParam.replace(/^p/, "")) || 0;

export function initTelegram(): void {
  if (!inTelegram) return;
  tg!.ready();
  tg!.expand();
  try {
    tg!.setHeaderColor("#ffffff");
    tg!.setBackgroundColor("#ffffff");
    tg!.setBottomBarColor?.("#ffffff");
    tg!.disableVerticalSwipes?.();
  } catch {
    /* старые клиенты */
  }
}

export const haptic = {
  tap: () => inTelegram && tg!.HapticFeedback.impactOccurred("light"),
  select: () => inTelegram && tg!.HapticFeedback.selectionChanged(),
  success: () => inTelegram && tg!.HapticFeedback.notificationOccurred("success"),
};

export function openExternal(url: string): void {
  if (inTelegram) tg!.openLink(url);
  else window.open(url, "_blank", "noopener");
}

/** Поделиться товаром: ссылка на бота, который откроет карточку (/start p<ID>). */
export function shareProduct(id: number, title: string): boolean {
  if (!botName) return false;
  const link = `https://t.me/${botName}?start=p${id}`;
  const url = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(title)}`;
  if (inTelegram) tg!.openTelegramLink(url);
  else window.open(url, "_blank", "noopener");
  return true;
}

export const canSaveSubscriptions = keyboardMode || !!botName;

/** Deep link: s1_2-u3 (подписаться на 1 и 2, отписаться от 3); лимит Telegram — 64 символа. */
function batchPayload(sub: number[], unsub: number[]): string {
  const parts = [];
  if (sub.length) parts.push(`s${sub.join("_")}`);
  if (unsub.length) parts.push(`u${unsub.join("_")}`);
  return parts.join("-");
}

/**
 * Сохранить подписки. Своего сервера у приложения нет, поэтому изменения уходят в бота
 * одним пакетом: sendData (запуск с кнопки клавиатуры) или deep link. Приложение закроется.
 * Возвращает, что именно отправлено (null — отправить некуда).
 */
export function saveSubscriptions(sub: number[], unsub: number[]): { sub: number[]; unsub: number[] } | null {
  if (keyboardMode) {
    tg!.sendData(JSON.stringify({ a: "batch", sub, unsub }));
    return { sub, unsub };
  }
  if (!botName) return null;
  // Deep link ограничен 64 символами — отправляем столько, сколько влезает, остальное позже
  const fit = { sub: [] as number[], unsub: [] as number[] };
  for (const [list, key] of [[sub, "sub"], [unsub, "unsub"]] as const) {
    for (const id of list) {
      const next = { ...fit, [key]: [...fit[key], id] };
      if (batchPayload(next.sub, next.unsub).length > 64) break;
      fit[key].push(id);
    }
  }
  const payload = batchPayload(fit.sub, fit.unsub);
  const link = `https://t.me/${botName}?start=${payload}`;
  if (inTelegram) {
    tg!.openTelegramLink(link);
    setTimeout(() => tg!.close(), 400);
  } else {
    window.open(link, "_blank", "noopener");
  }
  return fit;
}

export function bindBackButton(enabled: boolean, onBack: () => void): () => void {
  if (!inTelegram) return () => {};
  if (enabled) {
    tg!.BackButton.show();
    tg!.BackButton.onClick(onBack);
  } else {
    tg!.BackButton.hide();
  }
  return () => tg!.BackButton.offClick(onBack);
}
