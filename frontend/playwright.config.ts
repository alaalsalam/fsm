import { defineConfig } from "@playwright/test";

export default defineConfig({
	testDir: "./e2e",
	// Vite's on-demand dependency optimizer restarts when the lazy CORE routes are
	// first requested. Serial execution keeps both viewport projects deterministic.
	fullyParallel: false,
	workers: 1,
	reporter: "line",
	use: {
		headless: true,
		trace: "retain-on-failure",
	},
	projects: [
		{ name: "mobile-390", use: { viewport: { width: 390, height: 844 } } },
		{ name: "desktop-1440", use: { viewport: { width: 1440, height: 900 } } },
	],
	webServer: [
		{
			command: "yarn workspace @digit/console dev --host 127.0.0.1 --port 4174",
			url: "http://127.0.0.1:4174/fsm-console/login",
			reuseExistingServer: true,
		},
		{
			command: "yarn workspace @digit/portal dev --host 127.0.0.1 --port 4175",
			url: "http://127.0.0.1:4175/",
			reuseExistingServer: true,
		},
		{
			command: "yarn workspace @digit/mobile dev --host 127.0.0.1 --port 4176",
			url: "http://127.0.0.1:4176/jobs",
			reuseExistingServer: true,
		},
	],
});
