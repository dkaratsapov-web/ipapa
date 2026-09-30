const base = {
  width: 22,
  height: 22,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};
type P = { size?: number };
const sz = (p: P, d = 22) => ({ width: p.size ?? d, height: p.size ?? d });

export const IconSearch = (p: P) => <svg {...base} {...sz(p, 20)}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>;
export const IconHome = (p: P) => <svg {...base} {...sz(p)}><path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" /></svg>;
export const IconBell = (p: P & { filled?: boolean }) => (
  <svg {...base} {...sz(p)} fill={p.filled ? "currentColor" : "none"}><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /></svg>
);
export const IconClose = (p: P) => <svg {...base} {...sz(p, 18)}><path d="M18 6 6 18M6 6l12 12" /></svg>;
export const IconBack = (p: P) => <svg {...base} {...sz(p)}><path d="m15 18-6-6 6-6" /></svg>;
export const IconShare = (p: P) => <svg {...base} {...sz(p, 20)}><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M16 6l-4-4-4 4M12 2v13" /></svg>;
export const IconChevron = (p: { open?: boolean }) => (
  <svg {...base} width={18} height={18} style={{ transform: p.open ? "rotate(180deg)" : undefined, transition: "transform .25s" }}><path d="m6 9 6 6 6-6" /></svg>
);
export const IconExternal = (p: P) => <svg {...base} {...sz(p, 18)}><path d="M15 3h6v6M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" /></svg>;
export const IconCheck = (p: P) => <svg {...base} {...sz(p, 18)}><path d="M20 6 9 17l-5-5" /></svg>;
export const IconDevice = (p: P) => <svg {...base} {...sz(p, 30)} strokeWidth={1.6} opacity={0.35}><rect x="6" y="2" width="12" height="20" rx="3" /><path d="M11 18h2" /></svg>;
export const IconBox = (p: P) => <svg {...base} {...sz(p, 32)}><path d="M21 8 12 3 3 8v8l9 5 9-5z" /><path d="m3 8 9 5 9-5M12 13v8" /></svg>;
export const IconWifiOff = (p: P) => <svg {...base} {...sz(p, 32)}><path d="m2 2 20 20M8.5 16.5a5 5 0 0 1 7 0M5 12.9a10 10 0 0 1 5.2-2.8M19 12.9a10 10 0 0 0-2.3-1.6M2 8.8a15 15 0 0 1 4.2-2.6M22 8.8A15 15 0 0 0 11 5" /><path d="M12 20h.01" /></svg>;
