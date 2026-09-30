import type { ReactNode } from "react";
import { IconBack } from "./Icons";

export function ScreenHeader({ title, subtitle, onBack, children }: { title: string; subtitle?: ReactNode; onBack?: () => void; children?: ReactNode }) {
  return (
    <header className="topbar">
      <div className="topbar-row">
        {onBack && (
          <button className="icon-btn back-btn" onClick={onBack} aria-label="Назад">
            <IconBack />
          </button>
        )}
        <h1 className="page-title">{title}</h1>
      </div>
      {subtitle && (
        <div className="muted" style={{ fontWeight: 600, marginTop: 2 }}>
          {subtitle}
        </div>
      )}
      {children}
    </header>
  );
}
