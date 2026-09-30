import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" — чтобы приложение работало из подкаталога GitHub Pages (/ipapa/)
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: { target: "es2020", sourcemap: false },
});
