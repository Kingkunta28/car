import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// In development the API is proxied so the browser sees one origin
// (session cookies + CSRF work exactly as in production behind a rewrite).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/media": "http://127.0.0.1:8000",
      "/sitemap.xml": "http://127.0.0.1:8000",
    },
  },
  build: { sourcemap: false, chunkSizeWarningLimit: 700 },
});
