const base = { width: 22, height: 22, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

export const IconSearch = (p: { size?: number }) => (
  <svg {...base} width={p.size ?? 20} height={p.size ?? 20} aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
);
export const IconHome = () => (
  <svg {...base} aria-hidden="true"><path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" /></svg>
);
export const IconBell = (p: { filled?: boolean; size?: number }) => (
  <svg {...base} width={p.size ?? 22} height={p.size ?? 22} fill={p.filled ? "currentColor" : "none"} aria-hidden="true"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /></svg>
);
export const IconClose = () => (
  <svg {...base} width={18} height={18} aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
);
export const IconChevron = (p: { open?: boolean }) => (
  <svg {...base} width={18} height={18} style={{ transform: p.open ? "rotate(180deg)" : undefined, transition: "transform .25s" }} aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
);
export const IconExternal = () => (
  <svg {...base} width={18} height={18} aria-hidden="true"><path d="M15 3h6v6M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" /></svg>
);
export const IconCheck = () => (
  <svg {...base} width={18} height={18} aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
);
