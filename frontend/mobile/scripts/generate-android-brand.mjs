import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const mobileRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const resources = join(mobileRoot, "resources");
const androidRes = join(mobileRoot, "android/app/src/main/res");

if (!existsSync(androidRes)) {
	throw new Error(
		"Android project not found. Run `npx cap add android` before generating brand assets.",
	);
}

const icon = readFileSync(join(resources, "icon.svg"), "utf8");
const foreground = readFileSync(join(resources, "icon-foreground.svg"), "utf8");
const splashLogo = `data:image/png;base64,${readFileSync(join(resources, "digit-logo-light.png")).toString("base64")}`;

const iconSizes = { mdpi: 48, hdpi: 72, xhdpi: 96, xxhdpi: 144, xxxhdpi: 192 };
const foregroundSizes = { mdpi: 108, hdpi: 162, xhdpi: 216, xxhdpi: 324, xxxhdpi: 432 };
const splashSizes = {
	"drawable/splash.png": [480, 320],
	"drawable-land-mdpi/splash.png": [480, 320],
	"drawable-land-hdpi/splash.png": [800, 480],
	"drawable-land-xhdpi/splash.png": [1280, 720],
	"drawable-land-xxhdpi/splash.png": [1600, 960],
	"drawable-land-xxxhdpi/splash.png": [1920, 1280],
	"drawable-port-mdpi/splash.png": [320, 480],
	"drawable-port-hdpi/splash.png": [480, 800],
	"drawable-port-xhdpi/splash.png": [720, 1280],
	"drawable-port-xxhdpi/splash.png": [960, 1600],
	"drawable-port-xxxhdpi/splash.png": [1280, 1920],
};

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

async function renderSvg(svg, width, height, output) {
	await page.setViewportSize({ width, height });
	await page.setContent(
		`<style>html,body{margin:0;width:100%;height:100%;background:transparent}svg{display:block;width:100%;height:100%}</style>${svg}`,
	);
	await page.screenshot({ path: output, omitBackground: true });
}

for (const [density, size] of Object.entries(iconSizes)) {
	for (const filename of ["ic_launcher.png", "ic_launcher_round.png"]) {
		await renderSvg(icon, size, size, join(androidRes, `mipmap-${density}`, filename));
	}
}

for (const [density, size] of Object.entries(foregroundSizes)) {
	await renderSvg(
		foreground,
		size,
		size,
		join(androidRes, `mipmap-${density}`, "ic_launcher_foreground.png"),
	);
}

for (const [relativePath, [width, height]] of Object.entries(splashSizes)) {
	await page.setViewportSize({ width, height });
	await page.setContent(
		`<style>html,body{margin:0;width:100%;height:100%;background:#064E3B}body{display:flex;align-items:center;justify-content:center}img{width:min(54vw,440px);height:auto}</style><img src="${splashLogo}" alt="DIGIT"/>`,
	);
	await page.screenshot({ path: join(androidRes, relativePath), omitBackground: false });
}

await browser.close();
console.log("✓ DIGIT Android launcher and splash assets generated");
