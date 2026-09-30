import { motion } from "framer-motion";
import { useState } from "react";
import { HOURS, LOCATIONS, REPAIR_DEVICES, REPAIR_PROBLEMS, SERVICE_FACTS, SERVICE_PHONE } from "../service";
import { callPhone, haptic, leadFormFull, sendLead } from "../telegram";
import { Chip } from "./CategoryScreen";
import { IconPhone, IconPin, IconWrench } from "./Icons";
import { LeadForm, type Contact } from "./LeadForm";
import { ScreenHeader } from "./ScreenHeader";

export function ServiceScreen({ onBack, toast }: { onBack?: () => void; toast: (m: string) => void }) {
  const [device, setDevice] = useState(0);
  const [problem, setProblem] = useState(0);
  const [model, setModel] = useState("");
  const [contact, setContact] = useState<Contact>({ name: "", phone: "", comment: "" });

  const submit = () => {
    const result = sendLead(
      { kind: "repair", device, problem, model, ...contact },
      { device: REPAIR_DEVICES[device], problem: REPAIR_PROBLEMS[problem] },
    );
    if (result === "sent") {
      haptic.success();
      toast("Переходим в бот — там подтвердим запись");
    } else {
      toast("Откройте приложение из бота или позвоните нам");
    }
  };

  return (
    <>
      <ScreenHeader title="Сервисный центр" onBack={onBack} />
      <motion.section className="service-hero pad" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <div className="service-hero-card">
          <IconWrench size={30} />
          <h2>Ремонт Apple и Android</h2>
          <p>При вас. За 25 минут. С гарантией до года.</p>
          <div className="facts">
            {SERVICE_FACTS.map((f, i) => (
              <motion.div key={f.label} className="fact" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.05 }}>
                <b>{f.value}</b>
                <span>{f.label}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.section>

      <section className="section pad" aria-labelledby="repair-form">
        <h2 className="section-title" id="repair-form" style={{ fontSize: 20 }}>
          Записаться на диагностику
        </h2>
        <p className="form-note" style={{ textAlign: "left" }}>Диагностика бесплатная. Устраним за 1 час или дадим подменное устройство.</p>
        <div className="field-label">Что ремонтируем</div>
        <div className="chips chips-wrap" role="group" aria-label="Устройство">
          {REPAIR_DEVICES.map((d, i) => (
            <Chip key={d} active={device === i} group="repair-device" onClick={() => setDevice(i)}>
              {d}
            </Chip>
          ))}
        </div>
        {leadFormFull && (
          <label className="field">
            <span>Модель</span>
            <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Например, iPhone 13 Pro" maxLength={80} />
          </label>
        )}
        <div className="field-label">Что случилось</div>
        <div className="chips chips-wrap" role="group" aria-label="Проблема">
          {REPAIR_PROBLEMS.map((p, i) => (
            <Chip key={p} active={problem === i} group="repair-problem" onClick={() => setProblem(i)}>
              {p}
            </Chip>
          ))}
        </div>
        <LeadForm value={contact} onChange={setContact} commentLabel="Подробнее о проблеме" />
        <motion.button className="btn btn-primary" style={{ width: "100%", marginTop: 16 }} whileTap={{ scale: 0.97 }} onClick={submit}>
          Записаться на диагностику
        </motion.button>
        <motion.button className="btn btn-soft" style={{ width: "100%", marginTop: 10 }} whileTap={{ scale: 0.97 }} onClick={() => callPhone(SERVICE_PHONE)}>
          <IconPhone size={18} /> {SERVICE_PHONE}
        </motion.button>
      </section>

      <section className="section" aria-labelledby="where">
        <div className="section-head">
          <h2 className="section-title" id="where" style={{ fontSize: 20 }}>
            Куда принести
          </h2>
        </div>
        <ul className="plain-list">
          {LOCATIONS.map((l) => (
            <li key={l.address} className="row">
              <span className="menu-icon">
                <IconPin />
              </span>
              <span className="row-main">
                <span className="row-title">{l.address}</span>
                <span className="row-sub">{l.note}</span>
              </span>
            </li>
          ))}
        </ul>
        <p className="form-note">{HOURS}</p>
      </section>
    </>
  );
}
