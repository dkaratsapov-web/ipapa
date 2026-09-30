import { leadFormFull } from "../telegram";

export interface Contact {
  name: string;
  phone: string;
  comment: string;
}

/** Имя/телефон/комментарий: доступны, только когда приложение открыто кнопкой клавиатуры (sendData). */
export function LeadForm({ value, onChange, commentLabel = "Комментарий" }: { value: Contact; onChange: (c: Contact) => void; commentLabel?: string }) {
  if (!leadFormFull) {
    return <p className="form-note">Имя и телефон бот спросит в чате — это займёт пару секунд.</p>;
  }
  return (
    <div className="form">
      <label className="field">
        <span>Как вас зовут</span>
        <input value={value.name} onChange={(e) => onChange({ ...value, name: e.target.value })} autoComplete="name" maxLength={80} />
      </label>
      <label className="field">
        <span>Телефон</span>
        <input value={value.phone} onChange={(e) => onChange({ ...value, phone: e.target.value })} inputMode="tel" autoComplete="tel" placeholder="+7" maxLength={30} />
      </label>
      <label className="field">
        <span>{commentLabel}</span>
        <textarea value={value.comment} onChange={(e) => onChange({ ...value, comment: e.target.value })} rows={2} maxLength={500} />
      </label>
    </div>
  );
}
