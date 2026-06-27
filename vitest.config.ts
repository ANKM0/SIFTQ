import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    environmentOptions: {
      jsdom: {
        url: "http://localhost/"
      }
    },
    exclude: ["**/.sympohy/**", "**/node_modules/**", "**/dist/**", "**/tests/e2e/**"]
  }
});
