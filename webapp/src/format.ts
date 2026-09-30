export function rub(kopecks: number): string {
  if (!kopecks) return "Цена по запросу";
  const rubles = Math.round(kopecks / 100);
  return `${rubles.toLocaleString("ru-RU").replace(/ /g, " ")} ₽`;
}

export function plural(n: number, one: string, few: string, many: string): string {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

export function updatedLabel(date: Date | null): string {
  if (!date) return "";
  const diff = (Date.now() - date.getTime()) / 60_000;
  if (diff < 2) return "обновлено только что";
  if (diff < 60) return `обновлено ${Math.round(diff)} мин назад`;
  return `обновлено ${date.toLocaleString("ru-RU", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" })}`;
}
