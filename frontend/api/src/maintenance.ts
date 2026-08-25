import type { FrappeClient } from "./client";

export type MaintenancePlanStatus = "Draft" | "Active" | "Paused" | "Completed" | "Cancelled";
export type MaintenanceOccurrenceStatus =
	| "Forecast"
	| "Due"
	| "Released"
	| "Completed"
	| "Skipped"
	| "Cancelled"
	| "Overdue";

export interface MaintenancePlanSummary {
	name: string;
	plan_title: string;
	customer: string;
	company: string;
	customer_site: string;
	service_contract?: string;
	status: MaintenancePlanStatus;
	active: number;
	start_date: string;
	end_date?: string;
	revision: number;
}

export interface MaintenanceOccurrence {
	name: string;
	maintenance_plan: string;
	installed_equipment: string;
	customer_site: string;
	service_type: string;
	due_date: string;
	release_on: string;
	status: MaintenanceOccurrenceStatus;
	released_job?: string;
	rescheduled_from?: string;
}

export interface MaintenanceSummary {
	forecast: number;
	due: number;
	overdue: number;
	released: number;
	completed: number;
	skipped: number;
	due_today: number;
}

export interface CreateMaintenancePlanInput {
	plan_title: string;
	customer: string;
	company: string;
	customer_site: string;
	service_contract?: string;
	start_date: string;
	end_date?: string;
	timezone: string;
	forecast_horizon_days?: number;
	due_window_days?: number;
	catch_up_policy?: "Generate Missed" | "Skip Missed";
	dst_policy?: "Next Valid Time" | "First Occurrence" | "Second Occurrence";
	equipment: Array<{ installed_equipment: string; active: number }>;
	lines: Array<Record<string, unknown>>;
}

/** Shared preventive-maintenance contract for Console, Portal, and Mobile. */
export class MaintenanceApi {
	constructor(private client: FrappeClient) {}

	listPlans(filters: { status?: string; customer?: string; company?: string } = {}) {
		return this.client.call<MaintenancePlanSummary[]>(
			"fsm.maintenance.api.list_plans",
			filters,
			"GET",
		);
	}

	getPlan(maintenance_plan: string) {
		return this.client.call<Record<string, unknown>>(
			"fsm.maintenance.api.get_plan",
			{ maintenance_plan },
			"GET",
		);
	}

	listOccurrences(
		filters: {
			maintenance_plan?: string;
			status?: string;
			date_from?: string;
			date_to?: string;
			limit?: number;
		} = {},
	) {
		return this.client.call<MaintenanceOccurrence[]>(
			"fsm.maintenance.api.list_occurrences",
			filters,
			"GET",
		);
	}

	summary(company?: string) {
		return this.client.call<MaintenanceSummary>(
			"fsm.maintenance.api.maintenance_summary",
			{ company },
			"GET",
		);
	}

	create(values: CreateMaintenancePlanInput) {
		return this.client.call<MaintenancePlanSummary>("fsm.maintenance.commands.create_plan", {
			...values,
		});
	}

	transition(maintenance_plan: string, status: MaintenancePlanStatus, reason?: string) {
		return this.client.call<MaintenancePlanSummary>(
			"fsm.maintenance.commands.transition_plan",
			{
				maintenance_plan,
				status,
				reason,
				source: "Console",
			},
		);
	}

	generate(maintenance_plan: string) {
		return this.client.call<{ maintenance_plan: string; occurrences: string[] }>(
			"fsm.maintenance.commands.generate_plan_occurrences",
			{ maintenance_plan },
		);
	}

	release(maintenance_plan: string) {
		return this.client.call<{ jobs: string[] }>(
			"fsm.maintenance.commands.release_plan_occurrences",
			{ maintenance_plan },
		);
	}

	skip(occurrence: string, reason: string) {
		return this.client.call<MaintenanceOccurrence>(
			"fsm.maintenance.commands.skip_plan_occurrence",
			{
				occurrence,
				reason,
			},
		);
	}

	reschedule(occurrence: string, due_date: string) {
		return this.client.call<MaintenanceOccurrence>(
			"fsm.maintenance.commands.reschedule_plan_occurrence",
			{ occurrence, due_date },
		);
	}
}
