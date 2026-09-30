/** Цвета для кружков выбора цвета. Неизвестные названия — нейтральный градиент. */
const COLORS: [RegExp, string][] = [
  [/space black|черн|black|midnight|graphite|onyx|obsidian|nightfreeze/i, "#1d1d1f"],
  [/space gr[ae]y|серый|gray|grey|titanium gray/i, "#6e6e73"],
  [/silver|серебр|starlight|сияющ/i, "#e3e4e5"],
  [/white|бел|cloud|snow/i, "#f5f5f7"],
  [/natural|натурал/i, "#bab4a9"],
  [/desert|песоч|sand|beige|бежев/i, "#cbb89d"],
  [/gold|золот|champagne/i, "#e6cfa3"],
  [/cosmic orange|orange|оранж/i, "#f07a2c"],
  [/deep blue|navy|темно-син/i, "#2c3e63"],
  [/mist blue|sky|light blue|голуб/i, "#a9c4dc"],
  [/ultramarine|blue|син/i, "#3b6fd8"],
  [/teal|бирюз/i, "#4f9d9b"],
  [/sage|olive|оливк/i, "#b7bda3"],
  [/green|зел|mint|мят/i, "#6fae7b"],
  [/lavender|лаванд|lilac/i, "#c9bfe6"],
  [/purple|violet|фиолет/i, "#8e6cc9"],
  [/pink|роз|blush/i, "#f3c1cf"],
  [/red|красн|product/i, "#e0312b"],
  [/yellow|желт/i, "#f5d25a"],
  [/brown|коричн|bronze|бронз|copper/i, "#8b5e3c"],
];

export function swatch(name: string): string {
  for (const [re, color] of COLORS) if (re.test(name)) return color;
  return "linear-gradient(135deg, #e9e6ed, #cfc8d8)";
}

export function isColorAttr(attr: string): boolean {
  return /цвет|color/i.test(attr);
}
