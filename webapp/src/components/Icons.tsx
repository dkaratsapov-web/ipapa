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
export const IconHeart = (p: P & { filled?: boolean }) => (
  <svg {...base} {...sz(p)} fill={p.filled ? "currentColor" : "none"}><path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7Z" /></svg>
);
export const IconBag = (p: P) => <svg {...base} {...sz(p)}><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" /><path d="M3 6h18M16 10a4 4 0 0 1-8 0" /></svg>;
export const IconCompare = (p: P) => <svg {...base} {...sz(p)}><path d="M9 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M12 2v20" /></svg>;
export const IconWrench = (p: P) => <svg {...base} {...sz(p)}><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9Z" /></svg>;
export const IconSwap = (p: P) => <svg {...base} {...sz(p)}><path d="M16 3l4 4-4 4M20 7H4M8 21l-4-4 4-4M4 17h16" /></svg>;
export const IconPhone = (p: P) => <svg {...base} {...sz(p)}><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z" /></svg>;
export const IconGrid = (p: P) => <svg {...base} {...sz(p)}><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></svg>;
export const IconPin = (p: P) => <svg {...base} {...sz(p, 18)}><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" /></svg>;
export const IconChevronRight = (p: P) => <svg {...base} {...sz(p, 18)}><path d="m9 18 6-6-6-6" /></svg>;
