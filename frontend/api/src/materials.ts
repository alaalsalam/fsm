import type { FrappeClient } from "./client";

export type MaterialType = "Spare" | "Consumable" | "Refill";
export type MaterialAction = "Transfer" | "Issue" | "Consume" | "Return";

export interface MaterialInput {
	item_code: string;
	qty: number;
	installed_equipment?: string;
	uom?: string;
	serial_no?: string;
	batch_no?: string;
}

export interface MaterialPlanRow {
	requirement_row: string;
	item_code: string;
	item_name?: string;
	installed_equipment?: string;
	material_type: MaterialType;
	warehouse: string;
	required_qty: number;
	on_hand_qty: number;
	available_qty: number;
	reserved_qty: number;
	issued_qty: number;
	consumed_qty: number;
	returned_qty: number;
	shortage_qty: number;
}

export interface MaterialPlan {
	job: string;
	service_visit?: string;
	warehouse: string;
	items: MaterialPlanRow[];
}

/** Shared material workflow contract used by Console, Portal, and Mobile. */
export class MaterialsApi {
	constructor(private client: FrappeClient) {}

	plan(job: string, service_visit?: string, warehouse?: string) {
		return this.client.call<MaterialPlan>(
			"fsm.materials.get_material_plan",
			{ job, service_visit, warehouse },
			"GET",
		);
	}

	requestShortage(
		job: string,
		items: MaterialInput[],
		service_visit?: string,
		warehouse?: string,
	) {
		return this.client.call<{ name: string; status: string; warehouse: string }>(
			"fsm.materials.request_shortage",
			{ job, items, service_visit, warehouse },
		);
	}

	reserve(job: string, items: MaterialInput[], service_visit?: string, warehouse?: string) {
		return this.client.call<{ name: string; status: string; warehouse: string }>(
			"fsm.materials.reserve_materials",
			{ job, items, service_visit, warehouse },
		);
	}

	move(
		job: string,
		action: MaterialAction,
		items: MaterialInput[],
		context: {
			service_visit?: string;
			source_warehouse?: string;
			target_warehouse?: string;
		} = {},
	) {
		return this.client.call<{
			name: string;
			status: string;
			action: MaterialAction;
			purpose: string;
		}>("fsm.materials.post_material_movement", { job, action, items, ...context });
	}
}
