# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from fsm.security.policy import require_job_access

STAFF_ROLES = {"FSM Manager", "FSM Technician", "System Manager"}


@frappe.whitelist()
def get_messages(job: str):
	"""The message thread for a job (oldest first). Customers see only their own."""
	_assert_job_access(job)
	return frappe.get_list(
		"Service Job Message",
		filters={"service_job": job},
		fields=["name", "author_role", "author_name", "message", "creation"],
		order_by="creation asc",
	)


@frappe.whitelist()
def post_message(job: str, message: str, author_role: str | None = None):
	"""Post a message to a job thread. Role is inferred from the caller unless given."""
	_assert_job_access(job)
	if not (message or "").strip():
		frappe.throw(_("Message can't be empty."))
	doc = frappe.get_doc(
		{
			"doctype": "Service Job Message",
			"service_job": job,
			"message": message,
			"author_role": _role_for_current_user(),
		}
	).insert()
	return {"name": doc.name, "creation": str(doc.creation)}


def post_system_message(job: str, message: str):
	"""Post a System message (used by controllers, e.g. reschedule notices)."""
	frappe.get_doc(
		{
			"doctype": "Service Job Message",
			"service_job": job,
			"message": message,
			"author_role": "System",
			"author_name": "System",
		}
	).insert(ignore_permissions=True)


def _assert_job_access(job: str):
	"""Staff see every thread; a customer only threads for their own jobs."""
	require_job_access(job, "read")


def _role_for_current_user() -> str:
	roles = set(frappe.get_roles())
	if {"FSM Manager", "System Manager"} & roles:
		return "Dispatcher"
	if "FSM Technician" in roles:
		return "Technician"
	return "Customer"
