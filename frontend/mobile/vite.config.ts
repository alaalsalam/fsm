import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

// Standalone Capacitor app — bundled into dist/ and packaged into native shells.
export default defineConfig({
	plugins: [vue(), tailwindcss()],
	test: {
		environment: "jsdom",
		clearMocks: true,
	},
	resolve: {
		alias: {
			"@": fileURLToPath(new URL("./src", import.meta.url)),
		},
	},
	server: {
		port: 8083,
	},
	build: {
		outDir: "dist",
		emptyOutDir: true,
		sourcemap: true,
		rollupOptions: {
			output: {
				// Same vendor-split policy as the Console build: keeps every chunk
				// under the 500 kB warning without touching app architecture.
				// Capacitor packages the whole dist/ locally, so splitting is
				// neutral for the offline engine.
				manualChunks(id: string) {
					if (!id.includes("node_modules")) return;
					if (id.includes("node_modules/@ionic/")) return "vendor-ionic";
					if (
						id.includes("node_modules/@vue/") ||
						id.includes("node_modules/vue") ||
						id.includes("node_modules/pinia")
					) {
						return "vendor-vue";
					}
					if (id.includes("node_modules/@capacitor/")) return "vendor-capacitor";
					if (id.includes("node_modules/ionicons")) return "vendor-ionicons";
					return "vendor";
				},
			},
		},
	},
});
