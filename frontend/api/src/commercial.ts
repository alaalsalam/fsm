import type { FrappeClient } from "./client";

export interface BillableLine {
	row_name: string;
	item_code: string;
	installed_equipment?: string;
	component: "labour" | "parts" | "consumables" | "refill";
	qty: number;
	rate: number;
	amount: number;
	classification: "Covered" | "Billable";
	coverage_status: string;
	reason: string;
}

export interface ProfitabilityRow {
	service_job: string;
	customer: string;
	service_contract?: string;
	revenue: number;
	labour_cost: number;
	material_cost: number;
	travel_cost: number;
	total_cost: number;
	gross_margin: number;
}

export class CommercialApi {
	constructor(private client: FrappeClient) {}

	classify(service_job: string) {
		return this.client.call<{
			service_job: string;
			coverage_status?: string;
			lines: BillableLine[];
			billable_total: number;
			covered_total: number;
		}>("fsm.commercial.get_billable_classification", { service_job }, "GET");
	}

	createQuotation(service_job: string) {
		return this.client.call<{ name: string; created: boolean }>(
			"fsm.commercial.create_quotation_from_job",
			{ service_job },
		);
	}

	createInvoice(service_job: string) {
		return this.client.call<{ name: string }>("fsm.commercial.create_sales_invoice_from_job", {
			service_job,
		});
	}

	paymentStatus(service_job: string) {
		return this.client.call<{
			sales_invoice?: string;
			status: "Not Invoiced" | "Missing" | "Draft" | "Paid" | "Unpaid";
			grand_total: number;
			outstanding_amount: number;
		}>("fsm.commercial.get_payment_status", { service_job }, "GET");
	}

	profitability(service_job: string) {
		return this.client.call<ProfitabilityRow>(
			"fsm.commercial.get_profitability",
			{ service_job },
			"GET",
		);
	}
}
