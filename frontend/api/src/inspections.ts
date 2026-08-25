import type { FrappeClient } from "./client";

export type InspectionResponseType =
	| "Yes/No"
	| "Pass/Fail"
	| "Number"
	| "Text"
	| "Select"
	| "Date"
	| "Photo"
	| "Signature"
	| "Measurement";
export type InspectionOverallResult =
	| "Pending"
	| "Pass"
	| "Fail"
	| "Needs Refill"
	| "Needs Repair"
	| "Needs Replacement"
	| "Not Accessible"
	| "Skipped";

export interface InspectionResultRow {
	item_code: string;
	label: string;
	response_type: InspectionResponseType;
	required: number;
	responded: number;
	response_value?: string;
	numeric_value?: number;
	date_value?: string;
	attachment?: string;
	signature?: string;
	evidence?: string;
	measurement_unit?: string;
	evidence_required: number;
	passed: number;
	failure_severity?: string;
	action_hint?: string;
	validation_message?: string;
}

export interface EquipmentInspection {
	name: string;
	installed_equipment: string;
	service_job: string;
	service_visit?: string;
	inspection_template: string;
	template_revision: number;
	technician: string;
	status: "In Progress" | "Completed" | "Cancelled";
	started_on: string;
	completed_on?: string;
	overall_result: InspectionOverallResult;
	corrective_action_hint?: string;
	results: InspectionResultRow[];
}

export interface InspectionTemplateSummary {
	name: string;
	template_name: string;
	company: string;
	status: string;
	revision: number;
	item_group?: string;
}

export type InspectionResponseInput = Pick<InspectionResultRow, "item_code"> &
	Partial<
		Pick<
			InspectionResultRow,
			| "response_value"
			| "numeric_value"
			| "date_value"
			| "attachment"
			| "signature"
			| "evidence"
		>
	>;

/** Shared typed inspection contract; outcome is always calculated by the server. */
export class InspectionsApi {
	constructor(private client: FrappeClient) {}

	listTemplates(filters: { company?: string; status?: string; item_group?: string } = {}) {
		return this.client.call<InspectionTemplateSummary[]>(
			"fsm.inspections.api.list_templates",
			filters,
			"GET",
		);
	}

	list(
		filters: {
			service_job?: string;
			installed_equipment?: string;
			status?: string;
			overall_result?: string;
		} = {},
	) {
		return this.client.call<EquipmentInspection[]>(
			"fsm.inspections.api.list_inspections",
			filters,
			"GET",
		);
	}

	get(inspection: string) {
		return this.client.call<EquipmentInspection>(
			"fsm.inspections.api.get_inspection",
			{ inspection },
			"GET",
		);
	}

	start(values: {
		service_job: string;
		installed_equipment: string;
		inspection_template: string;
		service_visit?: string;
		technician?: string;
	}) {
		return this.client.call<EquipmentInspection>(
			"fsm.inspections.commands.start_inspection",
			values,
		);
	}

	save(inspection: string, responses: InspectionResponseInput[]) {
		return this.client.call<EquipmentInspection>(
			"fsm.inspections.commands.save_inspection_responses",
			{ inspection, responses },
		);
	}

	complete(inspection: string) {
		return this.client.call<EquipmentInspection>(
			"fsm.inspections.commands.complete_inspection",
			{ inspection },
		);
	}

	closeWithoutAccess(inspection: string, result: "Not Accessible" | "Skipped", reason: string) {
		return this.client.call<EquipmentInspection>(
			"fsm.inspections.commands.close_inspection_without_access",
			{ inspection, result, reason },
		);
	}
}
