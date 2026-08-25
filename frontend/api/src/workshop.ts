import type { FrappeClient } from "./client";

export type WorkshopStatus =
	| "Pickup Requested"
	| "Picked Up"
	| "Workshop Received"
	| "Initial Inspection"
	| "Estimate Required"
	| "Awaiting Customer Approval"
	| "Repair In Progress"
	| "Waiting Material"
	| "Repair Completed"
	| "Testing"
	| "Quality Inspection"
	| "Ready for Dispatch"
	| "Dispatched"
	| "Reinstalled"
	| "Closed"
	| "Cancelled";

export type WorkshopOutcome =
	| "Repaired"
	| "Not Repairable"
	| "Replacement Recommended"
	| "Replaced";

export interface WorkshopCase {
	name: string;
	service_job: string;
	installed_equipment?: string;
	customer: string;
	status: WorkshopStatus;
	warehouse?: string;
	stock_entry?: string;
	quotation?: string;
	sales_invoice?: string;
	customer_approval: "Pending" | "Approved" | "Rejected";
	repair_notes?: string;
	testing_result?: string;
	quality_result?: "Pass" | "Fail";
	final_outcome?: WorkshopOutcome;
}

/** Shared Workshop/RMA contract over the existing Service Return aggregate. */
export class WorkshopApi {
	constructor(private client: FrappeClient) {}

	list(filters: { status?: string; job?: string } = {}) {
		return this.client.call<WorkshopCase[]>("fsm.returns.list_returns", filters, "GET");
	}

	get(name: string) {
		return this.client.call<WorkshopCase>("fsm.returns.get_return", { name }, "GET");
	}

	create(values: {
		service_job: string;
		installed_equipment: string;
		reason: string;
		warehouse?: string;
		pickup_date?: string;
		pickup_address?: string;
	}) {
		return this.client.call<WorkshopCase>("fsm.returns.create_workshop_case", values);
	}

	update(
		name: string,
		values: Partial<
			Pick<
				WorkshopCase,
				| "warehouse"
				| "quotation"
				| "sales_invoice"
				| "customer_approval"
				| "repair_notes"
				| "testing_result"
				| "quality_result"
				| "final_outcome"
			>
		>,
	) {
		return this.client.call<WorkshopCase>("fsm.returns.update_workshop_case", {
			name,
			...values,
		});
	}

	transition(name: string, status: WorkshopStatus, reason?: string) {
		return this.client.call<WorkshopCase>("fsm.returns.transition_workshop_case", {
			name,
			status,
			reason,
		});
	}
}
