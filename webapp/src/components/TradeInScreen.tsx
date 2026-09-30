import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";
import type { Store } from "../data";
import { rub } from "../format";
import { haptic, sendLead } from "../telegram";
import { AnimatedPrice } from "./AnimatedPrice";
import { Chip } from "./CategoryScreen";
import { IconSwap } from "./Icons";
import { LeadForm, type Contact } from "./LeadForm";
import { ScreenHeader } from "./ScreenHeader";

/** «iPhone 17 Pro Esim» / «13 Pro» -> короткое имя без названия устройства, SIM — единообразно. */
function shortName(name: string, device: string): string {
  let n = name.replace(new RegExp(`^${device}\\s+`, "i"), "").trim();
  n = n.replace(/\s*esim$/i, " · eSIM").replace(/\s*nano\s*sim$/i, " · nano-SIM");
  return n;
}

function fullName(name: string, device: string): string {
  return `${device} ${shortName(name, device)}`.replace(" · ", ", ");
}

export function TradeInScreen({ store, onBack, onCatalog, toast }: { store: Store; onBack?: () => void; onCatalog: () => void; toast: (m: string) => void }) {
  const data = store.tradein;
  const [deviceIdx, setDeviceIdx] = useState(0);
  const device = data?.devices[deviceIdx];
  // Новые модели — первыми
  const models = useMemo(() => [...(device?.models ?? [])].reverse(), [device]);
  const [modelId, setModelId] = useState<string>("");
  const model = models.find((m) => m.id === modelId) ?? models[0];
  const [variantId, setVariantId] = useState<string>("");
  const variant = model?.variants.find((v) => v.id === variantId) ?? model?.variants[0];
  const [condId, setCondId] = useState<string>("");
  const condition = data?.conditions.find((c) => c.id === condId) ?? data?.conditions[0];
  const [contact, setContact] = useState<Contact>({ name: "", phone: "", comment: "" });

  if (!data || !device || !model || !variant || !condition) {
    return (
      <>
        <ScreenHeader title="Трейд-ин" onBack={onBack} />
        <div className="empty">
          <div className="empty-icon">
            <IconSwap size={32} />
          </div>
          <h2>Калькулятор обновляется</h2>
          <p>Прайс подтянется с сайта при ближайшем обновлении каталога. Пока можно оставить заявку по телефону.</p>
        </div>
      </>
    );
  }

  const estimate = variant.prices[condition.id] ?? 0;
  const modelName = fullName(model.name, device.label === "Watch" ? "Apple Watch" : device.label);

  const submit = () => {
    const result = sendLead(
      {
        kind: "tradein",
        model: model.id,
        variant: variant.id,
        condition: condition.id,
        modelName,
        variantLabel: variant.label,
        conditionLabel: condition.label,
        estimate,
        ...contact,
      },
      {},
    );
    if (result === "sent") {
      haptic.success();
      toast("Переходим в бот — менеджер уточнит детали");
    } else {
      toast("Откройте приложение из бота, чтобы отправить заявку");
    }
  };

  return (
    <>
      <ScreenHeader title="Трейд-ин" subtitle="Сдайте старое устройство и зачтите его стоимость при покупке" onBack={onBack} />

      <div className="chips" role="group" aria-label="Устройство">
        {data.devices.map((d, i) => (
          <Chip key={d.slug} active={deviceIdx === i} group="ti-device" onClick={() => { setDeviceIdx(i); setModelId(""); setVariantId(""); }}>
            {d.label}
          </Chip>
        ))}
      </div>

      <section className="pad">
        <div className="field-label">Модель</div>
        <div className="ti-models" role="radiogroup" aria-label="Модель">
          {models.map((m) => {
            const active = m.id === model.id;
            return (
              <motion.button key={m.id} role="radio" aria-checked={active} className={`ti-model ${active ? "is-active" : ""}`} whileTap={{ scale: 0.96 }}
                onClick={() => { haptic.select(); setModelId(m.id); setVariantId(""); }}>
                {active && <motion.span className="chip-bg" layoutId="ti-model-bg" transition={{ type: "spring", stiffness: 500, damping: 38 }} />}
                <span>{shortName(m.name, device.label)}</span>
              </motion.button>
            );
          })}
        </div>

        {model.variants.length > 1 && (
          <>
            <div className="field-label">Память</div>
            <div className="chips chips-wrap" role="group" aria-label="Память">
              {model.variants.map((v) => (
                <Chip key={v.id} active={v.id === variant.id} group="ti-variant" onClick={() => { haptic.select(); setVariantId(v.id); }}>
                  {v.label}
                </Chip>
              ))}
            </div>
          </>
        )}

        <div className="field-label">Состояние</div>
        <div className="ti-conds" role="radiogroup" aria-label="Состояние">
          {data.conditions.map((c) => {
            const active = c.id === condition.id;
            return (
              <motion.button key={c.id} role="radio" aria-checked={active} className={`ti-cond ${active ? "is-active" : ""}`} whileTap={{ scale: 0.98 }}
                onClick={() => { haptic.select(); setCondId(c.id); }}>
                <span className="ti-radio" aria-hidden="true">{active && <motion.i layoutId="ti-cond-dot" />}</span>
                <span className="row-main">{c.label}</span>
                <span className="muted">до {rub((variant.prices[c.id] ?? 0) * 100)}</span>
              </motion.button>
            );
          })}
        </div>
      </section>

      <section className="pad section">
        <motion.div className="ti-result" key={`${model.id}-${variant.id}-${condition.id}`} initial={{ scale: 0.97 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 400, damping: 20 }}>
          <span className="ti-result-label">{modelName} · {variant.label}</span>
          <span className="ti-result-price">
            <small>до</small> <AnimatedPrice value={estimate * 100} className="" />
          </span>
          <span className="ti-result-note">Предварительная оценка. Точную цену назовём после осмотра — это бесплатно и займёт 10 минут.</span>
        </motion.div>
        <AnimatePresence>
          <LeadForm value={contact} onChange={setContact} />
        </AnimatePresence>
        <motion.button className="btn btn-primary" style={{ width: "100%", marginTop: 16 }} whileTap={{ scale: 0.97 }} onClick={submit}>
          Получить расчёт у менеджера
        </motion.button>
        <button className="follow-all" onClick={onCatalog}>
          Выбрать новое устройство
        </button>
      </section>
    </>
  );
}
