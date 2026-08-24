// Shared FSM domain types + status → color mapping used across all surfaces.

// Values match the Service Job `status` doctype options exactly.
export type JobStatus =
	| "Draft"
	| "Open"
	| "Triaged"
	| "Converted"
	| "Closed"
	| "Planned"
	| "Scheduled"
	| "Dispatched"
	| "En Route"
	| "Checked In"
	| "In Progress"
	| "Checked Out"
	| "On Hold"
	| "Completed"
	| "Cancelled"
	| "Overdue";

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

/** Maps a job status to a design-system status tone (status colors mean status). */
export const STATUS_TONE: Record<JobStatus, StatusTone> = {
	Draft: "neutral",
	Open: "warning",
	Triaged: "info",
	Converted: "success",
	Closed: "neutral",
	Planned: "neutral",
	Scheduled: "warning",
	Dispatched: "info",
	"En Route": "info",
	"Checked In": "info",
	"In Progress": "info",
	"Checked Out": "warning",
	"On Hold": "warning",
	Completed: "success",
	Cancelled: "neutral",
	Overdue: "danger",
};

/** Sentence-case display labels — never Title Case or ALL CAPS. */
export const STATUS_LABEL: Record<JobStatus, string> = {
	Draft: "Draft",
	Open: "Open",
	Triaged: "Triaged",
	Converted: "Converted",
	Closed: "Closed",
	Planned: "Planned",
	Scheduled: "Scheduled",
	Dispatched: "Dispatched",
	"En Route": "En route",
	"Checked In": "Checked in",
	"In Progress": "In progress",
	"Checked Out": "Checked out",
	"On Hold": "On hold",
	Completed: "Completed",
	Cancelled: "Cancelled",
	Overdue: "Overdue",
};

export interface LinkOption {
	value: string;
	label: string;
}

export interface JobSummary {
	name: string;
	customer: string;
	address?: string;
	scheduledAt?: string;
	status: JobStatus;
	technician?: string;
	total?: number;
}
