from __future__ import annotations

import json
import uuid

import frappe
from frappe.utils import now_datetime

EVENT_SOURCES = {"Console", "Portal", "Mobile", "Scheduler", "API", "System"}


def append_event(
	event_type: str,
	reference,
	*,
	from_status: str | None = None,
	to_status: str | None = None,
	from_phase: str | None = None,
	to_phase: str | None = None,
	source: str = "API",
	correlation_id: str | None = None,
	metadata: dict | None = None,
):
	if source not in EVENT_SOURCES:
		source = "API"
	links = _links(reference)
	doc = frappe.get_doc(
		{
			"doctype": "Service Event Log",
			"event_id": str(uuid.uuid4()),
			"event_type": event_type,
			"reference_doctype": reference.doctype,
			"reference_name": reference.name,
			**links,
			"actor": frappe.session.user or "Guest",
			"actor_type": _actor_type(),
			"from_status": from_status,
			"to_status": to_status,
			"from_phase": from_phase,
			"to_phase": to_phase,
			"event_time": now_datetime(),
			"source": source,
			"correlation_id": correlation_id,
			"metadata_json": json.dumps(metadata or {}, sort_keys=True, default=str),
		}
	)
	doc.flags.fsm_internal_event = True
	doc.insert(ignore_permissions=True)
	return doc


def _links(reference) -> dict:
	if reference.doctype == "Service Request":
		return {"service_request": reference.name}
	if reference.doctype == "Service Job":
		return {"service_request": reference.service_request, "service_job": reference.name}
	if reference.doctype == "Service Visit":
		job = frappe.get_cached_doc("Service Job", reference.service_job)
		return {
			"service_request": job.service_request,
			"service_job": job.name,
			"service_visit": reference.name,
		}
	if reference.doctype == "Installed Equipment":
		return {"installed_equipment": reference.name}
	if reference.doctype == "Failure Analysis":
		job = frappe.get_cached_doc("Service Job", reference.service_job)
		return {
			"service_request": job.service_request,
			"service_job": job.name,
			"service_visit": reference.service_visit,
			"installed_equipment": reference.installed_equipment,
		}
	if reference.doctype == "Service Return":
		job = frappe.get_cached_doc("Service Job", reference.service_job)
		return {
			"service_request": job.service_request,
			"service_job": job.name,
			"installed_equipment": reference.installed_equipment,
		}
	return {}


def _actor_type() -> str:
	user = frappe.session.user or "Guest"
	if user == "Guest":
		return "Guest"
	roles = set(frappe.get_roles(user))
	for role in ("FSM Manager", "FSM Technician", "FSM Customer", "System Manager"):
		if role in roles:
			return role
	return "System"
