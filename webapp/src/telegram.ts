/** Тонкая обёртка над Telegram WebApp SDK; вне Telegram все вызовы безопасны. */
interface TgWebApp {
  initData: string;
  colorScheme: "light" | "dark";
  platform: string;
  ready(): void;
  expand(): void;
  close(): void;
  sendData(data: string): void;
  openLink(url: string): void;
  openTelegramLink(url: string): void;
  setHeaderColor(color: string): void;
  setBackgroundColor(color: string): void;
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

export const tg: TgWebApp | null =
  window.Telegram?.WebApp && window.Telegram.WebApp.initData !== undefined ? window.Telegram.WebApp : null;

export const inTelegram = !!tg?.platform && tg.platform !== "unknown";

const params = new URLSearchParams(location.search);
export const botName = params.get("bot") || "";
/** m=kb — открыто кнопкой клавиатуры: доступен sendData */
export const keyboardMode = params.get("m") === "kb";
export const initialSubs = new Set(
  (params.get("subs") || "").split(",").map(Number).filter((n) => Number.isFinite(n) && n > 0),
);
export const startProduct = Number(params.get("p")) || 0;

export function initTelegram(): void {
  if (!tg) return;
  tg.ready();
  tg.expand();
  try {
    tg.setHeaderColor("#ffffff");
    tg.setBackgroundColor("#ffffff");
    tg.disableVerticalSwipes?.();
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

/**
 * Подписка/отписка. Своего сервера у приложения нет, поэтому действие уходит в бота:
 * sendData (запуск с кнопки клавиатуры) или deep link /start s<ID> / u<ID>.
 */
export function sendSubscription(action: "sub" | "unsub", id: number): "sent" | "link" | "unavailable" {
  if (inTelegram && keyboardMode) {
    tg!.sendData(JSON.stringify({ a: action, id }));
    return "sent";
  }
  if (!botName) return "unavailable";
  const link = `https://t.me/${botName}?start=${action === "sub" ? "s" : "u"}${id}`;
  if (inTelegram) {
    tg!.openTelegramLink(link);
    setTimeout(() => tg!.close(), 300);
  } else {
    window.open(link, "_blank", "noopener");
  }
  return "link";
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
