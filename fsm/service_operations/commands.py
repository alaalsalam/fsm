from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from fsm.security.policy import require_job_access, require_manager_scope
from fsm.security.scopes import FSM_MANAGER, FSM_TECHNICIAN, SYSTEM_MANAGER, user_roles
from fsm.service_operations.events import append_event
from fsm.service_operations.policies import CompletionPolicy, validate_coordinates
from fsm.service_operations.projections import project_visit_transition
from fsm.service_operations.state import JOB_TRANSITIONS, REQUEST_TRANSITIONS, VISIT_TRANSITIONS, transition


def _source(value: str | None) -> str:
	return value if value in {"Console", "Portal", "Mobile", "Scheduler", "API", "System"} else "API"


def _result(doc):
	return frappe.get_doc(doc.doctype, doc.name).as_dict()


def _request_access(name: str, *, manager_only=False):
	doc = frappe.get_doc("Service Request", name)
	roles = user_roles()
	if SYSTEM_MANAGER in roles or FSM_MANAGER in roles:
		require_manager_scope(doc.company, doc.territory)
		return doc
	if not manager_only and "FSM Customer" in roles:
		from fsm.security.policy import require_customer_ownership

		require_customer_ownership(doc.customer)
		return doc
	frappe.throw(_("You are not permitted to access this service request."), frappe.PermissionError)


def _request_transition(name, target, event_type, source="API", correlation_id=None, **values):
	doc = _request_access(name, manager_only=True)
	old = doc.status
	transition(doc, target, REQUEST_TRANSITIONS, "request", **values)
	append_event(event_type, doc, from_status=old, to_status=target, source=_source(source), correlation_id=correlation_id)
	return _result(doc)


@frappe.whitelist()
def open_request(request: str, source="API", correlation_id=None):
	return _request_transition(request, "Open", "request.opened", source, correlation_id, opened_on=now_datetime())


@frappe.whitelist()
def triage_request(request: str, source="API", correlation_id=None):
	return _request_transition(request, "Triaged", "request.triaged", source, correlation_id, triaged_on=now_datetime())


@frappe.whitelist()
def cancel_request(request: str, source="API", correlation_id=None):
	return _request_transition(request, "Cancelled", "request.cancelled", source, correlation_id)


@frappe.whitelist()
def close_request(request: str, source="API", correlation_id=None):
	return _request_transition(request, "Closed", "request.closed", source, correlation_id, closed_on=now_datetime())


@frappe.whitelist()
def create_job_from_request(request: str, idempotency_key: str | None = None, source="API"):
	req = _request_access(request, manager_only=True)
	if req.status not in {"Open", "Triaged", "Converted"}:
		frappe.throw(_("Only open, triaged or converted requests can create jobs."))
	if idempotency_key:
		idempotency_key = str(idempotency_key).strip()
		if not idempotency_key or len(idempotency_key) > 128:
			frappe.throw(_("Idempotency key must contain 1 to 128 characters."))
		operation_key = hashlib.sha256(f"{req.name}:{idempotency_key}".encode()).hexdigest()
		existing = frappe.db.get_value("Service Job", {"request_operation_key": operation_key})
		if existing:
			return _result(frappe.get_doc("Service Job", existing))
	else:
		operation_key = None
	job = frappe.get_doc(
		{
			"doctype": "Service Job", "service_request": req.name,
			"request_idempotency_key": idempotency_key, "request_operation_key": operation_key,
			"company": req.company, "project": req.project, "customer": req.customer, "contact": req.contact,
			"priority": req.priority, "service_type": req.service_type, "territory": req.territory,
			"service_address": req.service_address if req.service_address and frappe.db.exists("Address", req.service_address) else None, "service_latitude": req.latitude,
			"service_longitude": req.longitude, "notes": req.description, "status": "Draft",
		}
	)
	if req.installed_equipment:
		job.append("equipment", {"installed_equipment": req.installed_equipment})
	job.flags.fsm_command = True
	try:
		job.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		# A concurrent retry may pass the lookup above before the first request commits.
		# The unique operation key is the serialization point; return its winning Job.
		existing = operation_key and frappe.db.get_value("Service Job", {"request_operation_key": operation_key})
		if not existing:
			raise
		return _result(frappe.get_doc("Service Job", existing))
	append_event("job.created.from_request", job, to_status="Draft", source=_source(source), correlation_id=idempotency_key)
	if req.status != "Converted":
		old = req.status
		req.flags.fsm_command = True
		req.status = "Converted"
		req.converted_on = now_datetime()
		req.save()
		append_event("request.converted", req, from_status=old, to_status="Converted", source=_source(source), correlation_id=idempotency_key)
	return _result(job)


def _job_transition(name, target, event_type, source="API", correlation_id=None, manager_only=False, **values):
	doc = require_job_access(name, "write", manager_only=manager_only)
	old, old_phase = doc.status, doc.phase
	transition(doc, target, JOB_TRANSITIONS, "job", **values)
	append_event(event_type, doc, from_status=old, to_status=target, from_phase=old_phase,
		to_phase=doc.phase, source=_source(source), correlation_id=correlation_id)
	return _result(doc)


@frappe.whitelist()
def plan_job(job: str, source="API", correlation_id=None):
	return _job_transition(job, "Planned", "job.planned", source, correlation_id, True, phase="Planning")


@frappe.whitelist()
def schedule_job(job: str, scheduled_start: str, scheduled_end: str | None = None, source="API", correlation_id=None):
	if not scheduled_start:
		frappe.throw(_("Scheduled start is required."))
	if scheduled_end and get_datetime(scheduled_end) <= get_datetime(scheduled_start):
		frappe.throw(_("Scheduled end must be after scheduled start."))
	return _job_transition(job, "Scheduled", "job.scheduled", source, correlation_id, True,
		scheduled_date=scheduled_start, scheduled_end=scheduled_end)


@frappe.whitelist()
def dispatch_job(job: str, technician: str | None = None, source="API", correlation_id=None):
	doc = require_job_access(job, "write", manager_only=True)
	technician = technician or doc.primary_technician
	if not technician:
		frappe.throw(_("A primary technician is required before dispatch."))
	tech = frappe.get_doc("Technician", technician)
	if not tech.active or (tech.company and tech.company != doc.company):
		frappe.throw(_("Select an active technician in the job company."), frappe.PermissionError)
	return _job_transition(job, "Dispatched", "job.dispatched", source, correlation_id, True,
		primary_technician=technician, phase="Travel")


@frappe.whitelist()
def start_job(job: str, source="API", correlation_id=None):
	return _job_transition(job, "In Progress", "job.started", source, correlation_id, phase="On-Site Service")


@frappe.whitelist()
def hold_job(job: str, reason: str, source="API", correlation_id=None):
	if reason not in {"Customer", "Material", "Approval", "Access", "Weather", "Workshop", "Other"}:
		frappe.throw(_("Select a valid hold reason."))
	doc = require_job_access(job, "write")
	return _job_transition(job, "On Hold", "job.held", source, correlation_id,
		hold_reason=reason, hold_from_status=doc.status)


@frappe.whitelist()
def resume_job(job: str, source="API", correlation_id=None):
	doc = require_job_access(job, "write")
	if doc.status != "On Hold":
		frappe.throw(_("Only an on-hold job can resume."))
	target = doc.hold_from_status if doc.hold_from_status in {"Scheduled", "Dispatched", "In Progress"} else "Scheduled"
	return _job_transition(job, target, "job.resumed", source, correlation_id, hold_reason=None, hold_from_status=None)


@frappe.whitelist()
def cancel_job(job: str, source="API", correlation_id=None):
	return _job_transition(job, "Cancelled", "job.cancelled", source, correlation_id, True)


@frappe.whitelist()
def complete_job(job: str, source="API", correlation_id=None):
	doc = require_job_access(job, "write")
	CompletionPolicy().validate(doc)
	return _job_transition(job, "Completed", "job.completed", source, correlation_id,
		completed_on=now_datetime(), phase="Closeout")


def _visit_access(name: str, *, manager_only=False):
	visit = frappe.get_doc("Service Visit", name)
	require_job_access(visit.service_job, "write", manager_only=manager_only)
	roles = user_roles()
	if FSM_TECHNICIAN in roles and not ({FSM_MANAGER, SYSTEM_MANAGER} & roles):
		from fsm.security.scopes import current_technician

		if not visit.primary_technician or visit.primary_technician != current_technician():
			frappe.throw(_("This visit is not assigned to you."), frappe.PermissionError)
	return visit


def _visit_read_access(name: str):
	visit = frappe.get_doc("Service Visit", name)
	require_job_access(visit.service_job, "read")
	return visit


@frappe.whitelist()
def create_visit(job: str, scheduled_start: str | None = None, scheduled_end: str | None = None,
	primary_technician: str | None = None, source="API", correlation_id=None):
	job_doc = require_job_access(job, "write", manager_only=True)
	if job_doc.status in {"Draft", "Completed", "Cancelled"}:
		frappe.throw(_("Visits can only be created for an active planned job."))
	if scheduled_end and (not scheduled_start or get_datetime(scheduled_end) <= get_datetime(scheduled_start)):
		frappe.throw(_("Scheduled end must be after scheduled start."))
	if primary_technician:
		tech = frappe.get_doc("Technician", primary_technician)
		if not tech.active or (tech.company and tech.company != job_doc.company):
			frappe.throw(_("Select an active technician in the job company."), frappe.PermissionError)
	count = frappe.db.count("Service Visit", {"service_job": job})
	visit = frappe.get_doc({"doctype": "Service Visit", "service_job": job, "project": job_doc.project,
		"visit_number": count + 1, "scheduled_start": scheduled_start, "scheduled_end": scheduled_end,
		"primary_technician": primary_technician or job_doc.primary_technician,
		"service_address": job_doc.service_address, "latitude": job_doc.service_latitude,
		"longitude": job_doc.service_longitude, "status": "Planned"})
	visit.flags.fsm_command = True
	visit.insert(ignore_permissions=True)
	append_event("visit.created", visit, to_status="Planned", source=_source(source), correlation_id=correlation_id)
	return _result(visit)


def _visit_transition(name, target, event_type, source="API", correlation_id=None, manager_only=False, **values):
	visit = _visit_access(name, manager_only=manager_only)
	old = visit.status
	transition(visit, target, VISIT_TRANSITIONS, "visit", **values)
	append_event(event_type, visit, from_status=old, to_status=target, source=_source(source), correlation_id=correlation_id)
	project_visit_transition(visit, old, _source(source), correlation_id)
	return _result(visit)


@frappe.whitelist()
def dispatch_visit(visit: str, source="API", correlation_id=None):
	doc = _visit_access(visit, manager_only=True)
	if not doc.primary_technician:
		frappe.throw(_("A technician is required before dispatch."))
	return _visit_transition(visit, "Dispatched", "visit.dispatched", source, correlation_id, True)


@frappe.whitelist()
def start_travel(visit: str, source="Mobile", correlation_id=None):
	return _visit_transition(visit, "En Route", "visit.travel.started", source, correlation_id,
		actual_departure=now_datetime())


@frappe.whitelist()
def check_in_visit(visit: str, latitude=None, longitude=None, accuracy=None, source="Mobile", correlation_id=None):
	validate_coordinates(latitude, longitude, accuracy)
	return _visit_transition(visit, "Checked In", "visit.checked_in", source, correlation_id,
		actual_check_in=now_datetime(), check_in_latitude=latitude, check_in_longitude=longitude,
		check_in_accuracy=accuracy)


@frappe.whitelist()
def start_visit_work(visit: str, source="Mobile", correlation_id=None):
	return _visit_transition(visit, "In Progress", "visit.work.started", source, correlation_id,
		actual_start=now_datetime())


@frappe.whitelist()
def check_out_visit(visit: str, latitude=None, longitude=None, accuracy=None, source="Mobile", correlation_id=None):
	validate_coordinates(latitude, longitude, accuracy)
	return _visit_transition(visit, "Checked Out", "visit.checked_out", source, correlation_id,
		actual_check_out=now_datetime(), check_out_latitude=latitude, check_out_longitude=longitude,
		check_out_accuracy=accuracy)


@frappe.whitelist()
def complete_visit(visit: str, source="Mobile", correlation_id=None):
	return _visit_transition(visit, "Completed", "visit.completed", source, correlation_id,
		actual_completion=now_datetime())


@frappe.whitelist()
def cancel_visit(visit: str, source="API", correlation_id=None):
	return _visit_transition(visit, "Cancelled", "visit.cancelled", source, correlation_id)
