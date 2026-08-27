from __future__ import annotations

import frappe
from frappe import _


def next_action_for(doc) -> dict:
	"""Return a read-only decision helper; it never owns lifecycle state."""
	handlers = {
		"Service Request": _request_action,
		"Service Job": _job_action,
		"Service Visit": _visit_action,
		"Maintenance Occurrence": _occurrence_action,
		"Service Contract": _contract_action,
		"Service Return": _workshop_action,
	}
	return handlers.get(doc.doctype, _no_action)(doc)


def _action(code, message, action=None, route=None, *, actor=None, blocked=False):
	return {
		"code": code,
		"message": message,
		"action": action,
		"route": route,
		"responsible_actor": actor,
		"blocked": bool(blocked),
	}


def _request_action(doc):
	if doc.status == "Draft":
		return _action("OPEN_REQUEST", _("Open the service request"), "Open Request", actor="FSM Manager")
	if doc.status == "Open":
		return _action("TRIAGE_REQUEST", _("Triage and classify the request"), "Triage", actor="FSM Manager")
	if doc.status == "Triaged":
		return _action("CREATE_JOB", _("Convert to a Service Job"), "Create Job", actor="FSM Manager")
	if doc.status == "Converted":
		job = frappe.db.get_value("Service Job", {"service_request": doc.name}, "name")
		return _action(
			"OPEN_JOB",
			_("Continue execution in the linked Service Job"),
			"Open Job",
			f"/jobs/{job}" if job else None,
			actor="FSM Manager",
		)
	return _no_action(doc)


def _job_action(doc):
	if doc.status == "Draft":
		return _action("PLAN_JOB", _("Plan the job scope and schedule"), "Plan Job", actor="FSM Manager")
	if doc.status == "Planned":
		return _action(
			"SCHEDULE_JOB", _("Schedule the job and assign a service team"), "Schedule", actor="FSM Manager"
		)
	if doc.status == "Scheduled":
		return _action(
			"DISPATCH_JOB", _("Assign or dispatch the service team"), "Dispatch", actor="FSM Manager"
		)
	if doc.status == "Dispatched":
		return _action(
			"START_VISIT",
			_("Start travel for the next service visit"),
			"Open Visits",
			f"/visits?job={doc.name}",
			actor="Assigned Team",
		)
	if doc.status == "On Hold":
		return _action(
			"RESOLVE_HOLD",
			_("Resolve the hold reason: {0}").format(doc.hold_reason or _("Not specified")),
			"Resume Job",
			actor="FSM Manager",
			blocked=True,
		)
	if doc.status == "In Progress":
		from fsm.process.completion import completion_blockers

		blockers = completion_blockers(doc)
		if blockers:
			first = blockers[0]
			return _action(
				first["code"],
				first["message"],
				first.get("action"),
				first.get("route"),
				actor=first.get("responsible_actor"),
				blocked=True,
			)
		return _action("COMPLETE_JOB", _("Complete the Service Job"), "Complete Job", actor="FSM Manager")
	return _no_action(doc)


def _visit_action(doc):
	steps = {
		"Planned": ("DISPATCH_VISIT", _("Dispatch the visit"), "Dispatch", "FSM Manager"),
		"Dispatched": ("START_TRAVEL", _("Start travel"), "Start Travel", "Assigned Technician"),
		"En Route": ("CHECK_IN", _("Check in at the customer site"), "Check In", "Assigned Technician"),
		"Checked In": ("START_WORK", _("Start service work"), "Start Work", "Assigned Technician"),
		"In Progress": (
			"PROCESS_EQUIPMENT",
			_("Complete equipment inspections and outcomes"),
			"Open Equipment",
			"Assigned Technician",
		),
		"Checked Out": (
			"COMPLETE_VISIT",
			_("Complete the service visit"),
			"Complete Visit",
			"Assigned Technician",
		),
	}
	if doc.status in steps:
		code, message, action, actor = steps[doc.status]
		return _action(code, message, action, actor=actor)
	return _no_action(doc)


def _occurrence_action(doc):
	if doc.status in {"Forecast", "Due", "Overdue"}:
		return _action(
			"RELEASE_JOB",
			_("Release the due maintenance as a grouped Service Job"),
			"Release Job",
			actor="FSM Manager",
		)
	if doc.status == "Released":
		return _action(
			"OPEN_JOB",
			_("Continue execution in the released Service Job"),
			"Open Job",
			f"/jobs/{doc.released_job}" if doc.released_job else None,
			actor="FSM Manager",
		)
	if doc.status == "Completed":
		return _action(
			"VIEW_NEXT_DUE", _("Review the next maintenance due date"), "Open Equipment", actor="FSM Manager"
		)
	return _no_action(doc)


def _contract_action(doc):
	if doc.status == "Draft":
		return _action(
			"ACTIVATE_CONTRACT", _("Review scope and activate the contract"), "Activate", actor="FSM Manager"
		)
	if doc.status == "Active":
		plan = frappe.db.get_value(
			"Maintenance Plan", {"service_contract": doc.name, "status": ["!=", "Cancelled"]}, "name"
		)
		if not plan:
			return _action(
				"CREATE_MAINTENANCE_PLAN",
				_("Create a maintenance plan from this contract"),
				"Create Plan",
				actor="FSM Manager",
			)
		return _action(
			"VIEW_MAINTENANCE",
			_("Review upcoming contract maintenance"),
			"Open Maintenance",
			"/maintenance",
			actor="FSM Manager",
		)
	if doc.status == "Expired":
		return _action(
			"RENEW_CONTRACT", _("Create or open the renewal quotation"), "Renew Contract", actor="FSM Manager"
		)
	return _no_action(doc)


def _workshop_action(doc):
	steps = {
		"Awaiting Customer Approval": (
			"APPROVE_ESTIMATE",
			_("Approve the repair estimate"),
			"Open Quotation",
		),
		"Waiting Material": ("RESOLVE_MATERIAL", _("Resolve the material shortage"), "Open Materials"),
		"Repair Completed": ("TEST_REPAIR", _("Test the repaired equipment"), "Start Testing"),
		"Testing": ("QUALITY_CHECK", _("Complete quality inspection"), "Open QA"),
		"Ready for Dispatch": (
			"DISPATCH_EQUIPMENT",
			_("Dispatch the equipment for return or reinstall"),
			"Dispatch",
		),
	}
	if doc.status in steps:
		code, message, action = steps[doc.status]
		return _action(code, message, action, actor="FSM Manager")
	return _no_action(doc)


def _no_action(doc):
	return _action("NONE", _("No further action is required"), actor=None)
