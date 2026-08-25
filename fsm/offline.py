"""Bounded, idempotent command ingress for the Capacitor field client."""

from __future__ import annotations

import json
import uuid

import frappe
from frappe import _

from fsm.security.policy import require_role
from fsm.security.scopes import FSM_MANAGER, FSM_TECHNICIAN, SYSTEM_MANAGER


COMMANDS = {
	"visit.start_travel": ("Service Visit", "fsm.service_operations.commands.start_travel", "visit", True),
	"visit.check_in": ("Service Visit", "fsm.service_operations.commands.check_in_visit", "visit", True),
	"visit.start_work": ("Service Visit", "fsm.service_operations.commands.start_visit_work", "visit", True),
	"visit.check_out": ("Service Visit", "fsm.service_operations.commands.check_out_visit", "visit", True),
	"visit.complete": ("Service Visit", "fsm.service_operations.commands.complete_visit", "visit", True),
	"job.complete": ("Service Job", "fsm.service_operations.commands.complete_job", "job", True),
	"inspection.save": ("Equipment Inspection", "fsm.inspections.commands.save_inspection_responses", "inspection", False),
	"inspection.complete": ("Equipment Inspection", "fsm.inspections.commands.complete_inspection", "inspection", False),
	"materials.consume": ("Service Job", "fsm.materials.post_material_movement", "job", False),
	"report.update": ("Service Report", "fsm.reporting.update_service_report", "service_report", False),
	"report.transition": ("Service Report", "fsm.reporting.transition_service_report", "service_report", False),
}


def _payload(value):
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if not isinstance(value, dict):
		frappe.throw(_("Offline command payload must be an object."), frappe.ValidationError)
	if len(json.dumps(value, default=str)) > 500_000:
		frappe.throw(_("Offline command payload is too large."), frappe.ValidationError)
	return value


def _valid_uuid(value: str) -> str:
	try:
		return str(uuid.UUID(str(value)))
	except (TypeError, ValueError, AttributeError):
		frappe.throw(_("A valid command UUID is required."), frappe.ValidationError)


def _receipt(command_id: str):
	name = frappe.db.get_value("Mobile Command Receipt", {"command_id": command_id})
	if not name:
		return None
	doc = frappe.get_doc("Mobile Command Receipt", name)
	if doc.user != frappe.session.user:
		frappe.throw(_("This command identifier belongs to another user."), frappe.PermissionError)
	return doc


def _result(doc):
	return {
		"command_id": doc.command_id,
		"state": doc.state,
		"result": frappe.parse_json(doc.result_json) if doc.result_json else None,
		"error": doc.error_message,
	}


def _execute(row):
	command_id = _valid_uuid(row.get("command_id"))
	existing = _receipt(command_id)
	if existing and existing.state == "Synced":
		return _result(existing)
	if existing:
		return {"command_id": command_id, "state": "Syncing"}
	action = str(row.get("action") or "")
	if action not in COMMANDS:
		frappe.throw(_("Unsupported offline action: {0}").format(action), frappe.ValidationError)
	doctype, dotted_path, parameter, accepts_correlation = COMMANDS[action]
	entity_id = str(row.get("entity_id") or "").strip()
	if row.get("entity_type") != doctype or not entity_id:
		frappe.throw(_("Offline command entity does not match its action."), frappe.ValidationError)
	if not frappe.db.exists(doctype, entity_id):
		frappe.throw(_("Offline command target no longer exists."), frappe.DoesNotExistError)
	expected = str(row.get("expected_version") or "").strip()
	actual = str(frappe.db.get_value(doctype, entity_id, "modified") or "")
	if expected and expected != actual:
		return {"command_id": command_id, "state": "Conflict", "server_version": actual}
	payload = _payload(row.get("payload") or {})
	payload[parameter] = entity_id
	if accepts_correlation:
		payload["correlation_id"] = command_id
	if action == "materials.consume":
		payload["action"] = "Consume"
	method = frappe.get_attr(dotted_path)
	frappe.db.savepoint("offline_command")
	try:
		receipt = frappe.new_doc("Mobile Command Receipt")
		receipt.update({"command_id": command_id, "user": frappe.session.user, "action": action,
			"entity_type": doctype, "entity_id": entity_id, "state": "Processing"})
		receipt.flags.fsm_offline_command = True
		receipt.insert(ignore_permissions=True)
		value = method(**payload)
		as_dict = getattr(value, "as_dict", None)
		serialized = json.dumps(as_dict() if callable(as_dict) else value, default=str)
		receipt.update({"state": "Synced", "result_json": serialized,
			"error_message": None})
		receipt.flags.fsm_offline_command = True
		receipt.save(ignore_permissions=True)
		return _result(receipt)
	except Exception as exc:
		frappe.db.rollback(save_point="offline_command")
		frappe.log_error(title=f"Offline command {command_id}", message=frappe.get_traceback())
		return {"command_id": command_id, "state": "Failed", "error": str(exc)}


@frappe.whitelist()
def sync_commands(commands):
	"""Apply at most 50 allowlisted commands; each successful UUID is exactly-once."""
	require_role(FSM_TECHNICIAN, FSM_MANAGER, SYSTEM_MANAGER)
	commands = frappe.parse_json(commands) if isinstance(commands, str) else commands
	if not isinstance(commands, list) or len(commands) > 50:
		frappe.throw(_("Provide a list of at most 50 offline commands."), frappe.ValidationError)
	return {"results": [_execute(row) for row in commands]}


@frappe.whitelist()
def command_status(command_ids):
	require_role(FSM_TECHNICIAN, FSM_MANAGER, SYSTEM_MANAGER)
	command_ids = frappe.parse_json(command_ids) if isinstance(command_ids, str) else command_ids
	if not isinstance(command_ids, list) or len(command_ids) > 100:
		frappe.throw(_("Provide at most 100 command identifiers."), frappe.ValidationError)
	return [_result(doc) for value in command_ids if (doc := _receipt(_valid_uuid(value)))]
