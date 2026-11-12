import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.VITE_BACKEND_URL?.trim();

  if (mode === "production") {
    if (!backendUrl) {
      throw new Error("Set VITE_BACKEND_URL to the deployed HTTPS API origin before building for production.");
    }

    let parsedBackendUrl;
    try {
      parsedBackendUrl = new URL(backendUrl);
    } catch {
      throw new Error("VITE_BACKEND_URL must be a valid HTTPS URL for production builds.");
    }

    if (
      parsedBackendUrl.protocol !== "https:" ||
      ["localhost", "127.0.0.1", "::1"].includes(parsedBackendUrl.hostname)
    ) {
      throw new Error("VITE_BACKEND_URL must point to a deployed HTTPS API, not a local development server.");
    }
  }

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src"),
      },
    },
    build: {
      outDir: "dist",
      emptyOutDir: true,
    },
    esbuild: {
      loader: "jsx",
      include: /src\/.*\.[jt]sx?$/,
      exclude: [],
    },
    optimizeDeps: {
      esbuildOptions: {
        loader: {
          ".js": "jsx",
        },
      },
    },
    server: {
      port: 3001,
      watch: {
        ignored: ["**/dist.zip"],
      },
      proxy: {
        "/api": "http://127.0.0.1:8000",
        "/admin": "http://127.0.0.1:8000",
      },
    },
    preview: {
      port: 4173,
    },
  };
});
