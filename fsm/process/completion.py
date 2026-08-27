from __future__ import annotations

import frappe
from frappe import _

TERMINAL_WORKSHOP = {"Closed", "Cancelled"}


def _configured_service_types(fieldname: str) -> set[str]:
	value = frappe.db.get_single_value("Service Settings", fieldname) or ""
	return {row.strip() for row in value.replace(",", "\n").splitlines() if row.strip()}


def _block(code, message, action, route=None, actor="FSM Manager"):
	return {"code": code, "message": message, "action": action, "route": route, "responsible_actor": actor}


def completion_blockers(job) -> list[dict]:
	"""Compute structured completion blockers without changing lifecycle state."""
	blockers = []
	active_visits = frappe.get_all(
		"Service Visit",
		filters={"service_job": job.name, "status": ["not in", ["Completed", "Cancelled"]]},
		pluck="name",
		limit=500,
	)
	if active_visits:
		blockers.append(
			_block(
				"ACTIVE_VISITS",
				_("Complete or cancel {0} active service visit(s)").format(len(active_visits)),
				"Open Visits",
				f"/visits?job={job.name}",
			)
		)

	incomplete_tasks = [row for row in job.tasks if row.status != "Done"]
	if incomplete_tasks:
		blockers.append(
			_block(
				"CHECKLIST_INCOMPLETE",
				_("Complete {0} mandatory checklist item(s)").format(len(incomplete_tasks)),
				"Open Checklist",
				f"/jobs/{job.name}?tab=overview",
			)
		)

	equipment = {row.installed_equipment for row in job.equipment if row.installed_equipment}
	if equipment and job.service_type in _configured_service_types("inspection_required_service_types"):
		completed = set(
			frappe.get_all(
				"Equipment Inspection",
				filters={
					"service_job": job.name,
					"status": "Completed",
					"installed_equipment": ["in", sorted(equipment)],
				},
				pluck="installed_equipment",
				limit=max(len(equipment), 1),
			)
		)
		missing = equipment - completed
		if missing:
			blockers.append(
				_block(
					"INSPECTIONS_INCOMPLETE",
					_("{0} equipment item(s) still require a completed inspection").format(len(missing)),
					"Open Inspections",
					f"/jobs/{job.name}?tab=inspections",
					actor="Assigned Team",
				)
			)

	critical_failures = frappe.db.count(
		"Failure Analysis",
		filters={
			"service_job": job.name,
			"severity": "Critical",
			"status": ["not in", ["Closed", "Cancelled"]],
		},
	)
	if critical_failures:
		blockers.append(
			_block(
				"CRITICAL_FAILURES_OPEN",
				_("Resolve {0} critical failure(s)").format(critical_failures),
				"Open Failures",
				f"/jobs/{job.name}?tab=failures",
			)
		)

	open_workshop = frappe.db.count(
		"Service Return",
		filters={"service_job": job.name, "status": ["not in", sorted(TERMINAL_WORKSHOP)]},
	)
	if open_workshop:
		blockers.append(
			_block(
				"WORKSHOP_OPEN",
				_("Resolve {0} open workshop case(s)").format(open_workshop),
				"Open Workshop",
				f"/jobs/{job.name}?tab=workshop",
			)
		)

	if job.service_type in _configured_service_types("report_required_service_types"):
		reports = frappe.get_all(
			"Service Report", filters={"service_job": job.name}, fields=["name", "status"], limit=100
		)
		if not reports:
			blockers.append(
				_block(
					"SERVICE_REPORT_REQUIRED",
					_("Generate the Service Report"),
					"Generate Report",
					f"/jobs/{job.name}?tab=reports",
				)
			)
		elif not any(row.status == "Submitted" for row in reports):
			blockers.append(
				_block(
					"SERVICE_REPORT_NOT_SUBMITTED",
					_("Verify and submit the Service Report"),
					"Open Reports",
					f"/jobs/{job.name}?tab=reports",
				)
			)

	if job.service_type in _configured_service_types(
		"certificate_required_service_types"
	) and not frappe.db.exists("Service Certificate", {"service_job": job.name, "status": "Issued"}):
		blockers.append(
			_block(
				"SERVICE_CERTIFICATE_REQUIRED",
				_("Issue the required Service Certificate"),
				"Open Certificates",
				f"/jobs/{job.name}?tab=reports",
			)
		)

	return blockers
