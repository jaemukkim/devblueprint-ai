import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // Mermaid는 다이어그램 탭에서만 지연 로딩되는 의도적인 대형 청크입니다.
    chunkSizeWarningLimit: 700,
  },
  server: {
    port: 5173,
  },
});
