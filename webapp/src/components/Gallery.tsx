import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { haptic } from "../telegram";
import { IconClose } from "./Icons";

/**
 * Галерея товара: листание свайпом (scroll-snap), точки и счётчик, просмотр на весь экран.
 * focus — фото, к которому нужно перелистнуть (например, при выборе цвета).
 */
export function Gallery({ photos, alt, focus }: { photos: string[]; alt: string; focus?: string }) {
  const track = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);
  const [viewer, setViewer] = useState<number | null>(null);

  const scrollTo = (i: number, smooth = true) => {
    const el = track.current;
    if (el) el.scrollTo({ left: i * el.clientWidth, behavior: smooth ? "smooth" : "auto" });
  };

  useEffect(() => {
    const i = focus ? photos.indexOf(focus) : -1;
    if (i >= 0 && i !== index) scrollTo(i);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus]);

  const onScroll = () => {
    const el = track.current;
    if (!el) return;
    const i = Math.round(el.scrollLeft / Math.max(1, el.clientWidth));
    if (i !== index) {
      setIndex(i);
      haptic.select();
    }
  };

  if (!photos.length) return null;
  return (
    <>
      <div
        className="gallery"
        ref={track}
        onScroll={onScroll}
        role="region"
        aria-roledescription="галерея"
        aria-label={`Фото: ${alt}`}
      >
        {photos.map((src, i) => (
          <button key={src} className="gallery-slide" onClick={() => setViewer(i)} aria-label={`Открыть фото ${i + 1} из ${photos.length}`}>
            <motion.img
              src={src}
              alt={i === 0 ? alt : ""}
              loading={i === 0 ? "eager" : "lazy"}
              decoding="async"
              initial={i === 0 ? { opacity: 0, scale: 0.92 } : false}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: "spring", stiffness: 260, damping: 26 }}
              draggable={false}
            />
          </button>
        ))}
      </div>
      {photos.length > 1 && (
        <>
          <div className="gallery-dots" aria-hidden="true">
            {photos.slice(0, 10).map((src, i) => (
              <motion.i key={src} animate={{ width: i === index ? 18 : 6, opacity: i === index ? 1 : 0.35 }} transition={{ type: "spring", stiffness: 500, damping: 34 }} />
            ))}
          </div>
          <span className="gallery-count" aria-live="polite">
            {index + 1} / {photos.length}
          </span>
        </>
      )}
      {createPortal(
        <AnimatePresence>
          {viewer !== null && <Viewer photos={photos} start={viewer} alt={alt} onClose={(i) => { setViewer(null); scrollTo(i, false); }} />}
        </AnimatePresence>,
        document.body,
      )}
    </>
  );
}

function Viewer({ photos, start, alt, onClose }: { photos: string[]; start: number; alt: string; onClose: (i: number) => void }) {
  const track = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(start);
  useEffect(() => {
    const el = track.current;
    if (el) el.scrollLeft = start * el.clientWidth;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose(index);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <motion.div
      className="viewer"
      role="dialog"
      aria-modal="true"
      aria-label={`Фото: ${alt}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div
        className="viewer-track"
        ref={track}
        tabIndex={0}
        aria-label="Листайте стрелками влево и вправо"
        onKeyDown={(e) => {
          const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
          const el = track.current;
          if (step && el) el.scrollTo({ left: (index + step) * el.clientWidth, behavior: "smooth" });
        }}
        onScroll={() => {
          const el = track.current;
          if (el) setIndex(Math.round(el.scrollLeft / Math.max(1, el.clientWidth)));
        }}
      >
        {photos.map((src, i) => (
          <div key={src} className="viewer-slide">
            <motion.img src={src} alt={i === index ? alt : ""} initial={{ scale: 0.9 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 260, damping: 26 }} />
          </div>
        ))}
      </div>
      <button className="icon-btn viewer-close" onClick={() => onClose(index)} aria-label="Закрыть" autoFocus>
        <IconClose />
      </button>
      {photos.length > 1 && <span className="viewer-count">{index + 1} / {photos.length}</span>}
    </motion.div>
  );
}
