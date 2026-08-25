import type { FrappeClient } from "./client";
import type { InstalledEquipmentDetail } from "./installed-base";
import type { InspectionTemplateSummary } from "./inspections";

export interface FireExtinguisherProfileInput {
	equipment_category: "Fire Extinguisher";
	extinguisher_type?: string;
	capacity?: number;
	capacity_uom?: string;
	agent_type?: string;
	fire_manufacturer?: string;
	fire_model?: string;
	manufacturing_date?: string;
	expiry_date?: string;
	pressure_rating?: number;
	hydro_test_interval_months?: number;
}

/** Fire-safety specialization over Installed Base, Inspection, and canonical Service Job. */
export class FireSafetyApi {
	constructor(private client: FrappeClient) {}

	updateProfile(installed_equipment: string, values: FireExtinguisherProfileInput) {
		return this.client.call<InstalledEquipmentDetail>(
			"fsm.fire_safety.commands.update_fire_safety_profile",
			{ installed_equipment, ...values },
		);
	}

	recordService(values: {
		service_job: string;
		installed_equipment: string;
		service_visit?: string;
		refill_date?: string;
		refill_result?: "Completed" | "Failed" | "Not Required";
		hydro_test_date?: string;
	}) {
		return this.client.call<InstalledEquipmentDetail>(
			"fsm.fire_safety.commands.record_extinguisher_service",
			{ ...values },
		);
	}

	installStandardTemplate(company: string) {
		return this.client.call<
			InspectionTemplateSummary & { items: Array<Record<string, unknown>> }
		>("fsm.fire_safety.commands.install_standard_extinguisher_template", { company });
	}
}
