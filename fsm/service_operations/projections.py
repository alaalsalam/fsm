import frappe

from fsm.service_operations.events import append_event
from fsm.service_operations.state import JOB_TRANSITIONS, transition


def project_visit_transition(visit, _previous_status: str, source: str, correlation_id: str | None):
	job = visit.get("service_job") and frappe.get_doc("Service Job", visit.service_job)
	if not job:
		return
	phase_by_status = {"En Route": "Travel", "Checked In": "Check-In", "In Progress": "On-Site Service"}
	target_phase = phase_by_status.get(visit.status)
	if target_phase and job.phase != target_phase:
		old_phase = job.phase
		job.flags.fsm_command = True
		job.phase = target_phase
		job.save()
		append_event(
			"job.phase.changed", job, from_phase=old_phase, to_phase=target_phase,
			source=source, correlation_id=correlation_id,
		)
	if visit.status == "In Progress" and job.status in {"Scheduled", "Dispatched"}:
		old_status = job.status
		transition(job, "In Progress", JOB_TRANSITIONS, "job")
		append_event(
			"job.started.from_visit", job, from_status=old_status, to_status=job.status,
			source=source, correlation_id=correlation_id, metadata={"service_visit": visit.name},
		)
