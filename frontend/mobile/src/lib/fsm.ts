import { client } from "./api";
import { InstalledBaseApi, InspectionsApi, MaterialsApi, ReportingApi } from "@digit/api";
import type { JobSummary, JobStatus } from "@digit/ui";

export const installedBase = new InstalledBaseApi(client);
export const inspectionsApi = new InspectionsApi(client);
export const materialsApi = new MaterialsApi(client);
export const reportingApi = new ReportingApi(client);

interface DispatchRow {
	name: string;
	customer_name: string;
	status: JobStatus;
	scheduled_date: string | null;
	primary_technician: string | null;
	address_display: string | null;
	total_amount: number;
}

export interface MobileJob {
	name: string;
	customer: string;
	customer_name?: string;
	status: JobStatus;
	phase?: string;
	address_display?: string;
	tasks?: { idx: number; task: string; status: string; note?: string }[];
	modified?: string;
}

export interface MobileVisit {
	name: string;
	visit_number: number;
	status: string;
	scheduled_start?: string;
	modified?: string;
}

export function getJob(name: string): Promise<MobileJob> {
	return client.getDoc<MobileJob>("Service Job", name);
}

export function getJobVisits(job: string): Promise<MobileVisit[]> {
	return client.call<MobileVisit[]>("fsm.service_operations.api.get_job_visits", { job }, "GET");
}

export function runVisitCommand(
	command: string,
	visit: string,
	values: Record<string, unknown> = {},
): Promise<MobileVisit> {
	return client.call<MobileVisit>(`fsm.service_operations.commands.${command}`, {
		visit,
		source: "Mobile",
		...values,
	});
}

export async function getDispatchJobs(
	params: { status?: string; technician?: string; limit?: number } = {},
): Promise<JobSummary[]> {
	const rows = await client.call<DispatchRow[]>("fsm.api.get_dispatch_jobs", params, "GET");
	return rows.map((r) => ({
		name: r.name,
		customer: r.customer_name,
		address: r.address_display ?? undefined,
		scheduledAt: r.scheduled_date ?? undefined,
		status: r.status,
		technician: r.primary_technician ?? undefined,
		total: r.total_amount,
	}));
}

export function clockIn(): Promise<{ technician: string; clocked_in: boolean }> {
	return client.call("fsm.tracking.clock_in", {});
}

export function clockOut(): Promise<{ technician: string; clocked_in: boolean }> {
	return client.call("fsm.tracking.clock_out", {});
}

export function updateLocation(
	latitude: number,
	longitude: number,
	accuracy?: number,
	job?: string,
): Promise<{ technician: string }> {
	return client.call("fsm.tracking.update_location", { latitude, longitude, accuracy, job });
}

export interface StockRow {
	item_code: string;
	item_name: string | null;
	warehouse: string;
	actual_qty: number;
	reserved_qty: number;
	projected_qty: number;
	reorder_level: number | null;
	low: boolean;
}

export function getVanStock(): Promise<StockRow[]> {
	return client.call<StockRow[]>("fsm.inventory.get_van_stock", {}, "GET");
}

export function startTimer(
	job: string,
	activity?: string,
): Promise<{ name: string; already_running: boolean }> {
	return client.call("fsm.costing.start_timer", { job, activity });
}

export function stopTimer(
	job: string,
): Promise<{ name: string; hours: number; actual_hours: number }> {
	return client.call("fsm.costing.stop_timer", { job });
}
