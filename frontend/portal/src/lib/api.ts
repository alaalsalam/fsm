import { createClient } from "@kodlyft/api";
import type { JobStatus } from "@kodlyft/ui";

export const client = createClient({ baseUrl: "" });

export interface BookingPayload {
	customer_name: string;
	contact_phone: string;
	service_address?: string;
	service_type?: string;
	preferred_date?: string;
	notes?: string;
}

export interface PortalSession {
	authenticated: boolean;
	user?: string;
	full_name?: string;
	customer?: string | null;
}

export type RequestStatus = "Draft" | "Open" | "Triaged" | "Converted" | "Closed" | "Cancelled";

export interface MyRequest {
	name: string;
	status: RequestStatus;
	service_type?: string;
	subject: string;
	preferred_start?: string;
	creation: string;
}

export interface MyJob {
	name: string;
	status: JobStatus;
	priority?: string;
	service_type?: string;
	scheduled_date?: string;
	completed_on?: string;
	primary_technician?: string;
	total_amount?: number;
	sales_invoice?: string;
	address_display?: string;
}

export interface SignupPayload {
	full_name: string;
	email: string;
	password: string;
	phone?: string;
}

export function requestService(payload: BookingPayload): Promise<{ name: string }> {
	return client.call<{ name: string }>("fsm.api.request_service", { ...payload });
}

export function getSession(): Promise<PortalSession> {
	return client.call<PortalSession>("fsm.api.get_portal_session", {}, "GET");
}

export function registerCustomer(
	payload: SignupPayload,
): Promise<{ customer: string; user: string; full_name: string }> {
	return client.call("fsm.api.register_customer", { ...payload });
}

export function login(usr: string, pwd: string): Promise<unknown> {
	return client.call("login", { usr, pwd });
}

export function logout(): Promise<unknown> {
	return client.call("logout", {});
}

export function getMyRequests(): Promise<MyRequest[]> {
	return client.call<MyRequest[]>("fsm.api.get_my_requests", {}, "GET");
}

export function getMyJobs(): Promise<MyJob[]> {
	return client.call<MyJob[]>("fsm.api.get_my_jobs", {}, "GET");
}

export interface JobMessage {
	name: string;
	author_role: string;
	author_name: string | null;
	message: string;
	creation: string;
}

export function getJobMessages(job: string): Promise<JobMessage[]> {
	return client.call<JobMessage[]>("fsm.messaging.get_messages", { job }, "GET");
}

export function postJobMessage(job: string, message: string): Promise<{ name: string }> {
	return client.call("fsm.messaging.post_message", { job, message });
}

export interface JobFeedback {
	name: string;
	rating: number;
	nps_score: number | null;
	comments: string | null;
	submitted_on: string;
}

export function getJobFeedback(job: string): Promise<JobFeedback | null> {
	return client.call<JobFeedback | null>("fsm.feedback.get_feedback", { job }, "GET");
}

export function submitJobFeedback(
	job: string,
	rating: number,
	comments?: string,
	nps_score?: number,
): Promise<{ name: string }> {
	return client.call("fsm.feedback.submit_feedback", { job, rating, comments, nps_score });
}
