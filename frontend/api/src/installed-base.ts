import type { FrappeClient } from "./client";

export type EquipmentStatus =
	| "Pending Installation"
	| "Active"
	| "Inactive"
	| "Removed"
	| "Returned"
	| "Replaced"
	| "Disposed";

export type WarrantyStatus = "Not Applicable" | "Active" | "Expired";

export interface CustomerSiteSummary {
	name: string;
	site_name: string;
	site_code: string;
	customer: string;
	company: string;
	status: "Active" | "Inactive";
	address_display?: string;
	city?: string;
	territory?: string;
}

export interface CustomerSiteDetail extends CustomerSiteSummary {
	address?: string;
	latitude?: number;
	longitude?: number;
	primary_contact?: string;
	contact_phone?: string;
	contact_email?: string;
	site_type?: string;
	access_notes?: string;
	working_hours?: string;
	safety_notes?: string;
	equipment_count: number;
	active_equipment: number;
	service_requests: Array<{ name: string; subject: string; status: string; creation: string }>;
	service_jobs: Array<{ name: string; status: string; scheduled_date?: string }>;
}

export interface EquipmentLocation {
	name: string;
	location_name: string;
	location_code: string;
	parent_location?: string;
	location_type: string;
	active: number;
}

export interface InstalledEquipmentSummary {
	name: string;
	equipment_id: string;
	equipment_name: string;
	company: string;
	customer: string;
	customer_site?: string;
	equipment_location?: string;
	item_code: string;
	item_name?: string;
	serial_no?: string;
	status: EquipmentStatus;
	installation_date?: string;
	warranty_end_date?: string;
	warranty_status: WarrantyStatus;
	last_service_date?: string;
}

export interface JobEquipmentRow {
	installed_equipment: string;
	customer_site?: string;
	equipment_location?: string;
	item_code: string;
	serial_no?: string;
	equipment_status: EquipmentStatus;
	service_scope?: string;
	notes?: string;
}

export interface EquipmentHistoryEvent {
	event_id: string;
	event_type: string;
	reference_doctype: string;
	reference_name: string;
	service_job?: string;
	service_visit?: string;
	from_status?: string;
	to_status?: string;
	event_time: string;
	source: string;
	metadata: Record<string, unknown>;
}

export interface InstalledEquipmentDetail extends InstalledEquipmentSummary {
	qr_code: string;
	asset_tag?: string;
	item_group?: string;
	brand?: string;
	batch_no?: string;
	installed_quantity: number;
	sales_order?: string;
	delivery_note?: string;
	sales_invoice?: string;
	delivery_date?: string;
	commissioning_date?: string;
	warranty_start_date?: string;
	manufacturer?: string;
	model_no?: string;
	equipment_category?: string;
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
	last_refill_date?: string;
	last_refill_result?: string;
	last_hydro_test_date?: string;
	hydro_due_date?: string;
	exact_location_notes?: string;
	equipment_photo?: string;
	source: string;
	service_jobs: Array<{ service_job: string; service_scope?: string }>;
}

export interface EquipmentFilters {
	customer?: string;
	customer_site?: string;
	item_code?: string;
	status?: string;
	serial_no?: string;
	company?: string;
	warranty?: string;
	limit?: number;
}

/** Shared Installed Base contract used by Console, Portal and Mobile. */
export class InstalledBaseApi {
	constructor(private client: FrappeClient) {}

	listSites(
		filters: { customer?: string; company?: string; status?: string; limit?: number } = {},
	) {
		return this.client.call<CustomerSiteSummary[]>(
			"fsm.installed_base.api.list_customer_sites",
			filters,
			"GET",
		);
	}

	getSite(site: string) {
		return this.client.call<CustomerSiteDetail>(
			"fsm.installed_base.api.get_customer_site",
			{ site },
			"GET",
		);
	}

	listLocations(customer_site: string) {
		return this.client.call<EquipmentLocation[]>(
			"fsm.installed_base.api.list_equipment_locations",
			{ customer_site },
			"GET",
		);
	}

	listEquipment(filters: EquipmentFilters = {}) {
		return this.client.call<InstalledEquipmentSummary[]>(
			"fsm.installed_base.api.get_customer_equipment",
			{ ...filters },
			"GET",
		);
	}

	getEquipment(equipment: string) {
		return this.client.call<InstalledEquipmentDetail>(
			"fsm.installed_base.api.get_equipment",
			{ equipment },
			"GET",
		);
	}

	getHistory(equipment: string) {
		return this.client.call<EquipmentHistoryEvent[]>(
			"fsm.installed_base.api.get_equipment_history",
			{ equipment },
			"GET",
		);
	}

	resolveQr(token: string) {
		return this.client.call<InstalledEquipmentDetail>(
			"fsm.installed_base.api.resolve_equipment_by_qr",
			{ token },
			"GET",
		);
	}

	getJobEquipment(job: string) {
		return this.client.call<JobEquipmentRow[]>(
			"fsm.installed_base.api.get_job_equipment",
			{ job },
			"GET",
		);
	}
}
