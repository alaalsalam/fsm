import { expect, test } from "@playwright/test";

test("console boots and protects the jobs route", async ({ page }) => {
	const errors: Error[] = [];
	page.on("pageerror", (error) => errors.push(error));
	await page.goto("http://127.0.0.1:4174/fsm-console/jobs");
	await expect(page).toHaveURL(/\/fsm-console\/login/);
	await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
	expect(errors).toEqual([]);
});

test("portal booking surface boots", async ({ page }) => {
	const errors: Error[] = [];
	page.on("pageerror", (error) => errors.push(error));
	await page.goto("http://127.0.0.1:4175/");
	await expect(page.getByRole("heading", { name: "Request a service" })).toBeVisible();
	expect(errors).toEqual([]);
});

test("mobile jobs surface handles an unavailable API", async ({ page }) => {
	const errors: Error[] = [];
	page.on("pageerror", (error) => errors.push(error));
	await page.route("http://localhost:8000/api/**", (route) =>
		route.abort("internetdisconnected"),
	);
	await page.goto("http://127.0.0.1:4176/jobs");
	await expect(page.getByText("My jobs", { exact: true })).toBeVisible();
	await expect(page.getByText("Acme Cooling Co.", { exact: true })).toBeVisible();
	expect(errors).toEqual([]);
});
