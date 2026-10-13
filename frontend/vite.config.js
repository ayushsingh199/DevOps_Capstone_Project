import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the Vite server proxies /api to a locally running FastAPI.
// In containers, Nginx (compose) or the Kubernetes Ingress does the same job.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": process.env.VITE_API_PROXY ?? "http://localhost:8000" },
  },
  build: { outDir: "dist", sourcemap: false },
});
