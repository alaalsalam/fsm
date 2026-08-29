from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import get_datetime

from fsm.scheduling import assign_team, assign_technician
from fsm.security.policy import require_job_access
from fsm.service_operations.commands import create_visit, plan_job, schedule_job


def _same_moment(left, right) -> bool:
	if not left and not right:
		return True
	if not left or not right:
		return False
	return get_datetime(left) == get_datetime(right)


@frappe.whitelist()
def schedule_job_with_visit(
	job: str,
	scheduled_start: str,
	scheduled_end: str | None = None,
	service_team: str | None = None,
	primary_technician: str | None = None,
):
	"""Plan, schedule, assign and create one visit as a retry-safe Desk action."""
	if not scheduled_start:
		frappe.throw(_("Scheduled start is required."))

	doc = require_job_access(job, "write", manager_only=True)
	# Serialize identical retries so two browser clicks cannot create two visits.
	frappe.db.sql("select name from `tabService Job` where name=%s for update", job)
	doc = frappe.get_doc("Service Job", job)
	if doc.status in {"Completed", "Cancelled", "Dispatched", "In Progress", "On Hold"}:
		frappe.throw(_("This job can no longer be scheduled from the guided action."))

	if doc.status == "Draft":
		plan_job(job, source="Console", correlation_id=f"guided:{job}")
		doc = frappe.get_doc("Service Job", job)

	if doc.status == "Planned":
		schedule_job(
			job,
			scheduled_start,
			scheduled_end,
			source="Console",
			correlation_id=f"guided:{job}",
		)
	elif doc.status == "Scheduled" and not (
		_same_moment(doc.scheduled_date, scheduled_start)
		and _same_moment(doc.scheduled_end, scheduled_end)
	):
		frappe.throw(
			_("This job is already scheduled at another time. Update the schedule before creating a visit.")
		)

	doc = frappe.get_doc("Service Job", job)
	if service_team and doc.assigned_service_team != service_team:
		assign_team(job, service_team)
	if primary_technician and doc.primary_technician != primary_technician:
		assign_technician(job, primary_technician)

	existing = frappe.db.get_value(
		"Service Visit",
		{
			"service_job": job,
			"scheduled_start": get_datetime(scheduled_start),
			"status": ["!=", "Cancelled"],
		},
		"name",
	)
	if existing:
		return {"job": job, "visit": existing, "visit_created": False}

	visit = create_visit(
		job,
		scheduled_start=scheduled_start,
		scheduled_end=scheduled_end,
		primary_technician=primary_technician,
		service_team=service_team,
		source="Console",
		correlation_id=f"guided:{job}",
	)
	return {"job": job, "visit": visit.name, "visit_created": True}
