import type { FrappeClient } from "./client";

export type ServiceReportType =
	| "Service Report"
	| "Inspection Report"
	| "Preventive Maintenance Report";
export type ServiceReportStatus =
	| "Draft"
	| "Generated"
	| "Customer Review"
	| "Customer Signed"
	| "Verified"
	| "Submitted";
export type CertificateType = "Refill Certificate" | "Hydro Test Certificate";

export interface ServiceReport {
	name: string;
	service_job: string;
	report_type: ServiceReportType;
	revision: number;
	supersedes?: string;
	status: ServiceReportStatus;
	customer: string;
	company: string;
	customer_site?: string;
	snapshot: string;
	work_performed?: string;
	recommendations?: string;
	customer_name?: string;
	customer_signature?: string;
	signature_refused: 0 | 1;
	refusal_reason?: string;
}

export interface ServiceCertificate {
	name: string;
	service_report: string;
	service_job: string;
	installed_equipment?: string;
	certificate_type: CertificateType;
	revision: number;
	status: "Issued" | "Revoked";
	issued_on: string;
}

export class ReportingApi {
	constructor(private client: FrappeClient) {}

	generate(service_job: string, report_type: ServiceReportType, generation_key: string) {
		return this.client.call<ServiceReport>("fsm.reporting.generate_service_report", {
			service_job,
			report_type,
			generation_key,
		});
	}

	update(service_report: string, values: Partial<ServiceReport>) {
		return this.client.call<ServiceReport>("fsm.reporting.update_service_report", {
			service_report,
			...values,
		});
	}

	transition(service_report: string, status: ServiceReportStatus) {
		return this.client.call<ServiceReport>("fsm.reporting.transition_service_report", {
			service_report,
			status,
		});
	}

	revise(service_report: string, generation_key: string) {
		return this.client.call<ServiceReport>("fsm.reporting.revise_service_report", {
			service_report,
			generation_key,
		});
	}

	issueCertificate(
		service_report: string,
		certificate_type: CertificateType,
		generation_key: string,
		installed_equipment?: string,
	) {
		return this.client.call<ServiceCertificate>("fsm.reporting.issue_service_certificate", {
			service_report,
			certificate_type,
			generation_key,
			installed_equipment,
		});
	}

	list(service_job: string) {
		return this.client.call<{ reports: ServiceReport[]; certificates: ServiceCertificate[] }>(
			"fsm.reporting.list_service_documents",
			{ service_job },
			"GET",
		);
	}
}
