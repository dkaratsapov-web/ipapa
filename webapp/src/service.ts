/** Справочники сервиса и контакты (со страниц айпапа.рф /repair/ и /contacts/). */

// Порядок совпадает с services/leads.py (REPAIR_DEVICES / REPAIR_PROBLEMS) — по индексам работает deep link
export const REPAIR_DEVICES = ["Телефон", "Планшет", "Ноутбук", "Часы", "Другое"];
export const REPAIR_PROBLEMS = ["Разбит экран", "Не заряжается, аккумулятор", "Попала вода", "Не включается", "Другое"];

export const SERVICE_PHONE = "+7 (900) 013-14-15";
export const SHOP_PHONE = "+7 (966) 965-21-82";

export const SERVICE_FACTS = [
  { value: "0 ₽", label: "диагностика" },
  { value: "20 мин", label: "средний ремонт" },
  { value: "1 год", label: "гарантия" },
  { value: "от 250 ₽", label: "стоимость" },
];

export const LOCATIONS = [
  { address: "ул. Трёхсвятская, 25", note: "Сервисный центр — ремонт при вас" },
  { address: "Тверской пр-т, 3", note: "Магазин · приём техники" },
  { address: "пл. Гагарина, 5", note: "ТРЦ «РИО», 2 этаж · приём техники" },
  { address: "Октябрьский пр-т, 103", note: "ТЦ «Торговый парк №1» · приём техники" },
];
export const HOURS = "Пн–Вс, 10:00–22:00, без выходных";
