import type { FrappeClient } from "./client";

export type ContractStatus = "Draft" | "Active" | "Suspended" | "Expired" | "Cancelled";
export type CoverageStatus =
	| "Warranty"
	| "Contract Covered"
	| "Partially Covered"
	| "Chargeable"
	| "FOC"
	| "Not Covered";

export interface ContractSummary {
	name: string;
	contract_no: string;
	customer: string;
	company: string;
	status: ContractStatus;
	start_date: string;
	end_date: string;
	expiring_soon: number;
	renewal_recommended: number;
	renewal_quotation?: string;
}

export interface ContractCoverageRule {
	name?: string;
	rule_name: string;
	service_type?: string;
	item_group?: string;
	classification: Exclude<CoverageStatus, "Warranty" | "Chargeable">;
	labour: number;
	parts: number;
	travel: number;
	consumables: number;
	refill: number;
	inspection: number;
	workshop: number;
	limits_json?: string;
	active: number;
}

export interface ContractEntitlement {
	name: string;
	entitlement_type: string;
	service_type?: string;
	included_quantity: number;
	used_quantity: number;
	remaining_quantity: number;
	period_start?: string;
	period_end?: string;
	active: number;
}

export interface ContractDetail extends ContractSummary {
	included_visits: number;
	emergency_visits: number;
	response_sla_hours?: number;
	resolution_sla_hours?: number;
	quotation?: string;
	sales_order?: string;
	sales_invoice?: string;
	delivery_note?: string;
	maintenance_service_type?: string;
	maintenance_interval_count?: number;
	maintenance_interval_unit?: "Days" | "Weeks" | "Months" | "Years";
	first_maintenance_date?: string;
	covered_equipment: Array<{
		customer_site: string;
		installed_equipment?: string;
		item_group?: string;
		active: number;
	}>;
	coverage_rules: ContractCoverageRule[];
	entitlements: ContractEntitlement[];
	notes?: string;
}

export interface CoverageDecision {
	status: CoverageStatus;
	reason: string;
	service_contract?: string;
	installed_equipment?: string;
	covered_labour: boolean;
	covered_parts: boolean;
	covered_travel: boolean;
	limits: Record<string, unknown>;
	entitlement_row?: string;
	remaining_entitlement?: number;
}

export interface CreateContractInput {
	customer: string;
	company: string;
	start_date: string;
	end_date: string;
	included_visits?: number;
	emergency_visits?: number;
	response_sla_hours?: number;
	resolution_sla_hours?: number;
	delivery_note?: string;
	sales_order?: string;
	sales_invoice?: string;
	maintenance_service_type?: string;
	maintenance_interval_count?: number;
	maintenance_interval_unit?: "Days" | "Weeks" | "Months" | "Years";
	first_maintenance_date?: string;
	covered_equipment?: Array<Record<string, unknown>>;
	coverage_rules: Array<Partial<ContractCoverageRule>>;
	entitlements?: Array<Record<string, unknown>>;
	notes?: string;
}

/** Shared contract used by Console, Portal, and Mobile. */
export class ContractsApi {
	constructor(private client: FrappeClient) {}

	list(filters: { status?: string; customer?: string; company?: string } = {}) {
		return this.client.call<ContractSummary[]>(
			"fsm.contracts.api.list_contracts",
			filters,
			"GET",
		);
	}

	get(service_contract: string) {
		return this.client.call<ContractDetail>(
			"fsm.contracts.api.get_contract",
			{ service_contract },
			"GET",
		);
	}

	create(values: CreateContractInput) {
		return this.client.call<ContractDetail>("fsm.contracts.commands.create_contract", {
			...values,
		});
	}

	update(service_contract: string, values: Partial<CreateContractInput>) {
		return this.client.call<ContractDetail>("fsm.contracts.commands.update_contract", {
			service_contract,
			...values,
		});
	}

	transition(service_contract: string, status: ContractStatus, reason?: string) {
		return this.client.call<ContractDetail>("fsm.contracts.commands.transition_contract", {
			service_contract,
			status,
			reason,
			source: "Console",
		});
	}

	evaluate(service_job: string, installed_equipment?: string) {
		return this.client.call<CoverageDecision>(
			"fsm.contracts.api.get_job_coverage",
			{ service_job, installed_equipment },
			"GET",
		);
	}
}
