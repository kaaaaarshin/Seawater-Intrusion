import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/recharts")) return "recharts";
          if (
            id.includes("node_modules/d3-") ||
            id.includes("node_modules/victory-vendor") ||
            id.includes("node_modules/internmap") ||
            id.includes("node_modules/delaunator")
          ) {
            return "chart-vendor";
          }
          if (
            id.includes("node_modules/react") ||
            id.includes("node_modules/scheduler")
          ) {
            return "react";
          }
          return undefined;
        },
      },
    },
  },
});
