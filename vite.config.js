// Vite build tooling for the vanilla ES-module frontend.
//
// Production: `npm run build` bundles + minifies templates/index.html and
// static/js/** into static/dist/, which the FastAPI backend serves at `/`.
// Development: `npm run dev` starts a HMR server on :5173 that proxies API and
// WebSocket traffic to the backend on :8000.

import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  base: "/static/dist/",
  plugins: [tailwindcss()],
  build: {
    outDir: "static/dist",
    emptyOutDir: true,
    rollupOptions: {
      input: "templates/index.html",
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/healthz": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
});
