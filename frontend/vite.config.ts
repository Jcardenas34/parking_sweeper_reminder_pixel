import { defineConfig } from "vite";

export default defineConfig({
  // Relative paths so Capacitor's WebView can load dist/ from the APK.
  base: "./",
  server: { host: true, port: 5173, strictPort: true },
});
