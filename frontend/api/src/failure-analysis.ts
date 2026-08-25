import type { FrappeClient } from "./client";

export type FailureAnalysisStatus =
	| "Draft"
	| "Inspection"
	| "Analysis"
	| "Root Cause Identified"
	| "Corrective Action"
	| "Verification"
	| "Closed"
	| "Cancelled";
export type FailureSeverity = "Observation" | "Minor" | "Major" | "Critical";

export interface FailureAnalysis {
	name: string;
	status: FailureAnalysisStatus;
	service_job: string;
	service_visit?: string;
	installed_equipment: string;
	inspection?: string;
	failure_code: string;
	symptom: string;
	severity: FailureSeverity;
	safety_risk: number;
	root_cause?: string;
	corrective_action?: string;
	verification?: string;
	repeat_failure: number;
	repeat_count: number;
	escalated: number;
	priority_suggestion?: "Low" | "Medium" | "High" | "Urgent";
}

/** Shared RCA contract; lifecycle and projections remain server-owned. */
export class FailureAnalysisApi {
	constructor(private client: FrappeClient) {}

	list(
		filters: {
			service_job?: string;
			installed_equipment?: string;
			status?: string;
			limit?: number;
		} = {},
	) {
		return this.client.call<FailureAnalysis[]>(
			"fsm.failure_analysis.list_failure_analyses",
			filters,
			"GET",
		);
	}

	get(failure_analysis: string) {
		return this.client.call<FailureAnalysis>(
			"fsm.failure_analysis.get_failure_analysis",
			{ failure_analysis },
			"GET",
		);
	}

	create(values: {
		service_job: string;
		installed_equipment: string;
		service_visit?: string;
		inspection?: string;
		failure_code: string;
		symptom: string;
		severity?: FailureSeverity;
		safety_risk?: number;
	}) {
		return this.client.call<FailureAnalysis>(
			"fsm.failure_analysis.create_failure_analysis",
			values,
		);
	}

	update(
		failure_analysis: string,
		values: Partial<
			Pick<
				FailureAnalysis,
				| "failure_code"
				| "symptom"
				| "severity"
				| "safety_risk"
				| "root_cause"
				| "corrective_action"
				| "verification"
			>
		>,
	) {
		return this.client.call<FailureAnalysis>("fsm.failure_analysis.update_failure_analysis", {
			failure_analysis,
			...values,
		});
	}

	transition(failure_analysis: string, status: FailureAnalysisStatus, reason?: string) {
		return this.client.call<FailureAnalysis>(
			"fsm.failure_analysis.transition_failure_analysis",
			{ failure_analysis, status, reason },
		);
	}

	applyPriority(failure_analysis: string) {
		return this.client.call<{ job: string; priority: string; changed: boolean }>(
			"fsm.failure_analysis.apply_priority_suggestion",
			{ failure_analysis },
		);
	}
}
