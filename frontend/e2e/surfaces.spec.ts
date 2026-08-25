import { expect, test, type Page, type Route } from "@playwright/test";

const json = (route: Route, body: unknown) =>
	route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

test.beforeEach(async ({ page }) => {
	// Console defaults to Arabic. Keep English assertions deterministic across clean browsers.
	await page.addInitScript(() => localStorage.setItem("kl-lang", "en"));
});

async function mockConsoleSession(page: Page) {
	await page.route(/\/api\/(method|resource)\//, (route) => {
		const url = decodeURIComponent(route.request().url());
		if (url.includes("frappe.auth.get_logged_user"))
			return json(route, { message: "manager@example.com" });
		if (url.includes("/api/resource/User/"))
			return json(route, {
				data: { name: "manager@example.com", roles: [{ role: "FSM Manager" }] },
			});
		if (url.includes("list_service_requests"))
			return json(route, {
				message: [
					{
						name: "FSM-REQ-0001",
						subject: "Cooling failure",
						status: "Triaged",
						source: "Portal",
						creation: "2026-08-24",
					},
				],
			});
		if (url.includes("get_service_request"))
			return json(route, {
				message: {
					name: "FSM-REQ-0001",
					subject: "Cooling failure",
					description: "No cooling",
					status: "Triaged",
					source: "Portal",
					creation: "2026-08-24",
					service_jobs: [],
				},
			});
		if (url.includes("create_job_from_request"))
			return json(route, {
				message: {
					name: "FSM-JOB-0001",
					customer: "Customer A",
					customer_name: "Customer A",
					status: "Planned",
					phase: "Planning",
					tasks: [],
					items: [],
				},
			});
		if (url.includes("/api/resource/Service Job/"))
			return json(route, {
				data: {
					name: "FSM-JOB-0001",
					customer: "Customer A",
					customer_name: "Customer A",
					status: "Planned",
					phase: "Planning",
					tasks: [],
					items: [],
				},
			});
		if (url.includes("create_visit"))
			return json(route, {
				message: { name: "FSM-VIS-0001", visit_number: 1, status: "Planned" },
			});
		if (url.includes("get_job_visits"))
			return json(route, {
				message:
					route.request().method() === "GET"
						? [{ name: "FSM-VIS-0001", visit_number: 1, status: "Planned" }]
						: [],
			});
		if (url.includes("get_feedback")) return json(route, { message: null });
		if (url.includes("get_job_logistics"))
			return json(route, { message: { material_requests: [], delivery_notes: [] } });
		return json(route, { message: [] });
	});
}

test("console boots and protects the jobs route", async ({ page }) => {
	const errors: Error[] = [];
	page.on("pageerror", (error) => errors.push(error));
	await page.goto("http://127.0.0.1:4174/fsm-console/jobs");
	await expect(page).toHaveURL(/\/fsm-console\/login/);
	await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
	expect(errors).toEqual([]);
});

test("portal creates a canonical service request", async ({ page }) => {
	const errors: Error[] = [];
	page.on("pageerror", (error) => errors.push(error));
	await page.route(/\/api\/(method|resource)\//, (route) => {
		const url = route.request().url();
		if (url.includes("get_portal_session"))
			return json(route, { message: { authenticated: false } });
		if (url.includes("request_service"))
			return json(route, { message: { name: "FSM-REQ-0001" } });
		return json(route, { message: null });
	});
	await page.goto("http://127.0.0.1:4175/");
	await expect(page.getByRole("heading", { name: "Request a service" })).toBeVisible();
	await page.getByLabel("Your name").fill("Customer A");
	await page.getByLabel("Phone").fill("+4912345");
	await page.getByLabel("Service address").fill("1 Main Street");
	await page.getByRole("button", { name: "Request service", exact: true }).click();
	await expect(page.getByRole("heading", { name: "Request received" })).toBeVisible();
	await expect(page.getByText("FSM-REQ-0001")).toBeVisible();
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
	await expect(page.getByText(/Couldn't load assigned jobs/)).toBeVisible();
	expect(errors).toEqual([]);
});

test("console follows Request to Job to Visit", async ({ page }) => {
	const errors: Error[] = [];
	page.on("pageerror", (error) => errors.push(error));
	await mockConsoleSession(page);
	await page.goto("http://127.0.0.1:4174/fsm-console/requests/FSM-REQ-0001");
	await expect(page.getByRole("heading", { name: "Cooling failure" })).toBeVisible();
	await page.getByRole("button", { name: "Create Service Job" }).click();
	await expect(page).toHaveURL(/\/fsm-console\/jobs\/FSM-JOB-0001/);
	await expect(page.getByRole("heading", { name: "Service Visits" })).toBeVisible();
	await page.getByRole("button", { name: "Create visit" }).click();
	await expect(page.getByText("Visit 1")).toBeVisible();
	expect(errors).toEqual([]);
});

test("portal account shows requests and their related active job", async ({ page }) => {
	await page.route(/\/api\/(method|resource)\//, (route) => {
		const url = route.request().url();
		if (url.includes("get_portal_session"))
			return json(route, {
				message: { authenticated: true, full_name: "Customer A", customer: "Customer A" },
			});
		if (url.includes("get_my_requests"))
			return json(route, {
				message: [
					{
						name: "FSM-REQ-0001",
						status: "Converted",
						subject: "Cooling failure",
						creation: "2026-08-24",
					},
				],
			});
		if (url.includes("get_my_jobs"))
			return json(route, {
				message: [{ name: "FSM-JOB-0001", status: "Planned", service_type: "HVAC repair" }],
			});
		return json(route, { message: null });
	});
	await page.goto("http://127.0.0.1:4175/account");
	await expect(page.getByRole("heading", { name: "Hi Customer A" })).toBeVisible();
	await expect(page.getByText("Cooling failure")).toBeVisible();
	await expect(page.getByText("HVAC repair")).toBeVisible();
});

test("mobile advances an assigned visit from the job", async ({ page }) => {
	let status = "Dispatched";
	await page.route(/\/api\/(method|resource)\//, (route) => {
		const url = decodeURIComponent(route.request().url());
		if (url.includes("/api/resource/Service Job/"))
			return json(route, {
				data: {
					name: "FSM-JOB-0001",
					customer: "Customer A",
					customer_name: "Customer A",
					status: "Dispatched",
					phase: "Travel",
					tasks: [],
				},
			});
		if (url.includes("start_travel")) {
			status = "En Route";
			return json(route, { message: { name: "FSM-VIS-0001", visit_number: 1, status } });
		}
		if (url.includes("get_job_visits"))
			return json(route, { message: [{ name: "FSM-VIS-0001", visit_number: 1, status }] });
		return json(route, { message: [] });
	});
	await page.goto("http://127.0.0.1:4176/jobs/FSM-JOB-0001");
	await expect(page.getByText("Visit 1")).toBeVisible();
	await page.getByRole("button", { name: "Continue" }).click();
	await expect(page.getByText("En Route")).toBeVisible();
});

test("ERPNext delivery provisioned equipment appears in Console", async ({ page }) => {
	await page.route(/\/api\/(method|resource)\//, (route) => {
		const url = decodeURIComponent(route.request().url());
		if (url.includes("frappe.auth.get_logged_user"))
			return json(route, { message: "manager@example.com" });
		if (url.includes("/api/resource/User/"))
			return json(route, {
				data: { name: "manager@example.com", roles: [{ role: "FSM Manager" }] },
			});
		if (url.includes("get_customer_equipment"))
			return json(route, {
				message: [
					{
						name: "FSM-EQ-000001",
						equipment_id: "FSM-EQ-000001",
						equipment_name: "Fire Extinguisher",
						company: "Company A",
						customer: "Customer A",
						customer_site: "SITE-A",
						item_code: "FE-001",
						item_name: "Fire Extinguisher",
						serial_no: "SER-001",
						status: "Active",
						installation_date: "2026-08-24",
						warranty_status: "Active",
						last_service_date: null,
					},
				],
			});
		return json(route, { message: [] });
	});
	await page.goto("http://127.0.0.1:4174/fsm-console/equipment");
	await expect(page.getByRole("heading", { name: "Installed Equipment" })).toBeVisible();
	await expect(page.getByText("FSM-EQ-000001")).toBeVisible();
	await expect(page.getByText("SER-001")).toBeVisible();
});

test("customer My Equipment displays only owned records", async ({ page }) => {
	await page.route(/\/api\/(method|resource)\//, (route) => {
		const url = decodeURIComponent(route.request().url());
		if (url.includes("get_portal_session"))
			return json(route, {
				message: { authenticated: true, full_name: "Customer A", customer: "Customer A" },
			});
		if (url.includes("get_customer_equipment"))
			return json(route, {
				message: [
					{
						name: "FSM-EQ-000001",
						equipment_id: "FSM-EQ-000001",
						equipment_name: "Pump",
						company: "Company A",
						customer: "Customer A",
						customer_site: "SITE-A",
						item_code: "PUMP-1",
						item_name: "Pump",
						status: "Active",
						warranty_status: "Active",
					},
				],
			});
		return json(route, { message: [] });
	});
	await page.goto("http://127.0.0.1:4175/my-equipment");
	await expect(page.getByRole("heading", { name: "My Equipment" })).toBeVisible();
	await expect(page.getByText("Pump", { exact: true })).toBeVisible();
	await expect(page.getByText("FSM-EQ-000001")).toBeVisible();
});

test("mobile job displays multiple linked equipment records", async ({ page }) => {
	await page.route(/\/api\/(method|resource)\//, (route) => {
		const url = decodeURIComponent(route.request().url());
		if (url.includes("/api/resource/Service Job/"))
			return json(route, {
				data: {
					name: "FSM-JOB-0002",
					customer: "Customer A",
					status: "Dispatched",
					tasks: [],
				},
			});
		if (url.includes("get_job_equipment"))
			return json(route, {
				message: [
					{
						installed_equipment: "FSM-EQ-000001",
						item_code: "FE-001",
						serial_no: "SER-001",
						equipment_status: "Active",
					},
					{
						installed_equipment: "FSM-EQ-000002",
						item_code: "FE-001",
						serial_no: "SER-002",
						equipment_status: "Active",
					},
				],
			});
		return json(route, { message: [] });
	});
	await page.goto("http://127.0.0.1:4176/jobs/FSM-JOB-0002");
	await expect(page.getByRole("heading", { name: "Linked equipment" })).toBeVisible();
	await expect(page.getByText("FSM-EQ-000001")).toBeVisible();
	await expect(page.getByText("FSM-EQ-000002")).toBeVisible();
});
