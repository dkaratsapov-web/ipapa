import { AnimatePresence, motion } from "framer-motion";
import type { Store } from "../data";
import { rub } from "../format";
import { lists, MAX_COMPARE, useLists } from "../state";
import type { Product } from "../types";
import { IconClose, IconCompare } from "./Icons";
import { Img } from "./Img";
import { ScreenHeader } from "./ScreenHeader";

export function CompareScreen({ store, onProduct, onCatalog, onBack }: { store: Store; onProduct: (p: Product) => void; onCatalog: () => void; onBack?: () => void }) {
  const { compare } = useLists();
  const items = compare.map((id) => store.byId.get(id)).filter((p): p is Product => !!p);
  // Строки: общие поля + объединение характеристик в порядке появления
  const specLabels = [...new Set(items.flatMap((p) => p.specs.map(([label]) => label)))];
  const specOf = (p: Product, label: string) => p.specs.find(([l]) => l === label)?.[1] ?? "—";
  const memory = (p: Product) => {
    const attr = p.attrNames.find((a) => /памят|объём|storage/i.test(a));
    return attr ? [...new Set(p.variations.map((v) => v.attrs[attr]).filter(Boolean))].join(", ") : "—";
  };
  const colors = (p: Product) => {
    const attr = p.attrNames.find((a) => /цвет|color/i.test(a));
    return attr ? String(new Set(p.variations.map((v) => v.attrs[attr]).filter(Boolean)).size) : "—";
  };
  const rows: [string, (p: Product) => string][] = [
    ["Цена", (p) => (p.minPrice ? `${p.variations.length > 1 ? "от " : ""}${rub(p.minPrice)}` : "по запросу")],
    ["Наличие", (p) => (p.inStock ? "В наличии" : "Нет в наличии")],
    ["Память", memory],
    ["Цветов", colors],
    ...specLabels.map((l): [string, (p: Product) => string] => [l, (p) => specOf(p, l)]),
  ];

  return (
    <>
      <ScreenHeader title="Сравнение" subtitle={items.length ? `${items.length} из ${MAX_COMPARE}` : undefined} onBack={onBack} />
      {items.length === 0 ? (
        <motion.div className="empty" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="empty-icon">
            <IconCompare size={32} />
          </div>
          <h2>Нечего сравнивать</h2>
          <p>Добавьте до {MAX_COMPARE} устройств кнопкой «Сравнить» в карточке товара.</p>
          <motion.button className="btn btn-dark" style={{ margin: "22px auto 0", padding: "0 26px" }} whileTap={{ scale: 0.96 }} onClick={onCatalog}>
            Перейти в каталог
          </motion.button>
        </motion.div>
      ) : (
        <div className="compare-wrap">
          <table className="compare">
            <thead>
              <tr>
                <th scope="col" className="c-label">
                  <span className="sr-only">Параметр</span>
                </th>
                <AnimatePresence initial={false}>
                  {items.map((p) => (
                    <motion.th key={p.id} scope="col" layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9 }}>
                      <button className="compare-remove icon-btn" onClick={() => lists.toggleCompare(p.id)} aria-label={`Убрать из сравнения: ${p.name}`}>
                        <IconClose size={14} />
                      </button>
                      <button className="compare-head" onClick={() => onProduct(p)}>
                        <Img src={p.thumb} alt="" frameClass="compare-img" />
                        <span>{p.name}</span>
                      </button>
                    </motion.th>
                  ))}
                </AnimatePresence>
              </tr>
            </thead>
            <tbody>
              {rows.map(([label, get]) => {
                const values = items.map(get);
                const differs = new Set(values).size > 1;
                return (
                  <tr key={label} className={differs ? "is-diff" : ""}>
                    <th scope="row" className="c-label">
                      {label}
                    </th>
                    {items.map((p, i) => (
                      <td key={p.id}>{values[i]}</td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
          {specLabels.length === 0 && <p className="form-note pad">Характеристики подгружаются из Википедии — появятся после ближайшего обновления каталога.</p>}
          {items.some((p) => p.specsSrc) && <p className="form-note pad">Характеристики — по данным Википедии (CC BY-SA).</p>}
          <button className="follow-all muted" onClick={() => lists.clearCompare()}>
            Очистить сравнение
          </button>
        </div>
      )}
    </>
  );
}
