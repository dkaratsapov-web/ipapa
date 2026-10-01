import { MotionConfig } from "framer-motion";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "@fontsource-variable/manrope";
import "./styles.css";
import { initMetrika } from "./analytics";
import { initTelegram } from "./telegram";

initTelegram();
initMetrika();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* Учитываем системную настройку «уменьшить движение» */}
    <MotionConfig reducedMotion="user">
      <App />
    </MotionConfig>
  </StrictMode>,
);
