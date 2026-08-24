# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.core.doctype.user.user import is_signup_disabled
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, validate_email_address

from fsm.field_service_management.doctype.service_job.service_job import make_invoice_from_job
from fsm.security.field_allowlists import CUSTOMER_REGISTRATION_FIELDS, GUEST_BOOKING_FIELDS
from fsm.security.policy import (
	bounded_int,
	require_authenticated,
	require_job_access,
	validate_allowed_fields,
)
from fsm.security.scopes import current_customer


@frappe.whitelist()
def get_dispatch_jobs(status: str | None = None, technician: str | None = None, limit: int = 50):
	"""Jobs for the console dispatch board / mobile job list (permission-aware)."""
	require_authenticated()
	filters: dict = {}
	if status:
		filters["status"] = status
	if technician:
		filters["primary_technician"] = technician

	return frappe.get_list(
		"Service Job",
		filters=filters,
		fields=[
			"name",
			"customer_name",
			"status",
			"phase",
			"priority",
			"scheduled_date",
			"primary_technician",
			"total_amount",
			"address_display",
			"service_request",
			"sla_breached",
			"promised_response_by",
		],
		order_by="scheduled_date asc",
		limit=bounded_int(limit, 1, 200),
	)


@frappe.whitelist()
def get_dashboard_stats():
	"""Headline metrics for the console dashboard."""
	require_authenticated()
	from frappe.utils import today

	start, end = today() + " 00:00:00", today() + " 23:59:59"
	open_statuses = ["Planned", "Scheduled", "Dispatched", "In Progress", "On Hold"]

	jobs = frappe.get_list(
		"Service Job",
		filters={"status": ["in", [*open_statuses, "Completed"]]},
		fields=["status", "completed_on", "total_amount", "sla_breached"],
		limit=0,
	)
	completed_today = [
		job
		for job in jobs
		if job.status == "Completed" and job.completed_on and start <= str(job.completed_on) <= end
	]
	revenue_today = sum((row.total_amount or 0) for row in completed_today)

	return {
		"open_jobs": len([job for job in jobs if job.status in open_statuses]),
		"in_progress": len([job for job in jobs if job.status == "In Progress"]),
		"completed_today": len(completed_today),
		"revenue_today": revenue_today,
		"sla_breached": len([job for job in jobs if job.sla_breached and job.status in open_statuses]),
	}


@frappe.whitelist()
def create_invoice_from_job(job: str):
	"""Generate a draft Sales Invoice from a job's parts & services and link it back."""
	require_job_access(job, "write", manager_only=True)
	return {"name": make_invoice_from_job(job)}


@frappe.whitelist()
def start_job_task(job: str, idx: int):
	"""Begin a checklist step (sequential) and return the refreshed job."""
	return require_job_access(job, "write").start_task(idx)


@frappe.whitelist()
def complete_job_task(job: str, idx: int, note: str | None = None):
	"""Finish a checklist step and return the refreshed job."""
	return require_job_access(job, "write").complete_task(idx, note)


@frappe.whitelist()
def complete_job(job: str):
	"""Compatibility alias; lifecycle ownership remains in the command service."""
	from fsm.service_operations.commands import complete_job as command

	return command(job)


@frappe.whitelist(allow_guest=True)
@rate_limit(key="email", limit=5, seconds=60 * 60, methods="POST")
def register_customer(full_name: str, email: str, password: str, phone: str | None = None):
	"""Self-service customer signup from the portal.

	Creates a Website User, a linked Customer, and a Contact that ties the two
	together, then signs the new user in so the SPA can load their history."""
	values = {"full_name": full_name, "email": email, "password": password, "phone": phone}
	validate_allowed_fields(values, CUSTOMER_REGISTRATION_FIELDS)
	full_name = (full_name or "").strip()
	email = validate_email_address((email or "").strip().lower(), throw=True)
	phone = (phone or "").strip() or None
	if not (full_name and email and password):
		frappe.throw(_("Name, email and password are required."))
	if is_signup_disabled():
		frappe.throw(_("Customer registration is disabled."), frappe.PermissionError)
	if frappe.db.exists("User", email):
		frappe.throw(_("An account with this email already exists. Please sign in."))
	if frappe.db.exists("Contact Email", {"email_id": email}):
		frappe.throw(_("A contact with this email already exists."))

	first_name, separator, last_name = full_name.partition(" ")
	savepoint = f"fsm_register_{frappe.generate_hash(length=8)}"
	frappe.db.savepoint(savepoint)
	try:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name if separator else "",
				"send_welcome_email": 0,
				"user_type": "Website User",
				"new_password": password,
			}
		).insert(ignore_permissions=True)
		user.add_roles("FSM Customer")

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": full_name,
				"customer_type": "Individual",
				"customer_group": _default_customer_group(),
				"territory": _default_territory(),
			}
		).insert(ignore_permissions=True)

		contact = frappe.get_doc(
			{"doctype": "Contact", "first_name": first_name, "last_name": last_name if separator else ""}
		)
		contact.user = email
		contact.append("email_ids", {"email_id": email, "is_primary": 1})
		if phone:
			contact.append("phone_nos", {"phone": phone, "is_primary_mobile_no": 1})
		contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
		contact.insert(ignore_permissions=True)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise
	else:
		frappe.db.release_savepoint(savepoint)

	if getattr(frappe.local, "login_manager", None):
		frappe.local.login_manager.login_as(email)
	return {"customer": customer.name, "user": email, "full_name": full_name}


@frappe.whitelist(allow_guest=True)
def get_portal_session():
	"""Tell the portal who is signed in (and their linked customer), if anyone."""
	user = frappe.session.user
	if not user or user == "Guest":
		return {"authenticated": False}
	customer = _current_customer(optional=True)
	return {
		"authenticated": True,
		"user": user,
		"full_name": frappe.db.get_value("User", user, "full_name") or user,
		"customer": customer,
	}


@frappe.whitelist()
def get_my_requests():
	"""Service request history for the signed-in customer."""
	customer = _current_customer()
	return frappe.get_list(
		"Service Request",
		filters={"customer": customer},
		fields=[
			"name",
			"status",
			"service_type",
			"subject",
			"preferred_start",
			"creation",
		],
		order_by="creation desc",
	)


@frappe.whitelist()
def get_my_appointments():
	"""Deprecated compatibility alias for clients upgrading to get_my_requests."""
	return get_my_requests()


@frappe.whitelist()
def get_my_jobs():
	"""Job history for the signed-in customer."""
	customer = _current_customer()
	return frappe.get_list(
		"Service Job",
		filters={"customer": customer},
		fields=[
			"name",
			"status",
			"phase",
			"priority",
			"service_type",
			"scheduled_date",
			"completed_on",
			"primary_technician",
			"total_amount",
			"sales_invoice",
			"address_display",
			"service_request",
		],
		order_by="creation desc",
	)


@frappe.whitelist()
def get_my_job(job: str):
	"""A single job (with checklist + items) — only if it belongs to the caller."""
	customer = _current_customer()
	owner = frappe.db.get_value("Service Job", job, "customer")
	if owner != customer:
		raise frappe.PermissionError(_("This job is not on your account."))

	doc = frappe.get_doc("Service Job", job)
	return {
		"name": doc.name,
		"status": doc.status,
		"phase": doc.phase,
		"service_request": doc.service_request,
		"priority": doc.priority,
		"service_type": doc.service_type,
		"scheduled_date": doc.scheduled_date,
		"completed_on": doc.completed_on,
		"primary_technician": doc.primary_technician,
		"address_display": doc.address_display,
		"total_amount": doc.total_amount,
		"sales_invoice": doc.sales_invoice,
		"notes": doc.notes,
		"tasks": [{"task": t.task, "completed": t.completed, "note": t.note} for t in doc.tasks],
		"items": [
			{
				"item_code": i.item_code,
				"item_name": i.item_name,
				"qty": i.qty,
				"rate": i.rate,
				"amount": i.amount,
			}
			for i in doc.items
		],
		"visits": frappe.get_list(
			"Service Visit", filters={"service_job": doc.name},
			fields=["name", "visit_number", "status", "scheduled_start", "primary_technician"],
			order_by="visit_number asc",
		),
	}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60 * 60, methods="POST")
def request_service(
	customer_name: str,
	contact_phone: str,
	service_address: str | None = None,
	service_type: str | None = None,
	preferred_date: str | None = None,
	notes: str | None = None,
):
	"""Create a scoped Service Request intake record.

	Public (guest) bookings capture just a name + phone; a signed-in customer's
	booking is linked straight to their Customer record."""
	values = {
		"customer_name": customer_name,
		"contact_phone": contact_phone,
		"service_address": service_address,
		"service_type": service_type,
		"preferred_date": preferred_date,
		"notes": notes,
	}
	validate_allowed_fields(values, GUEST_BOOKING_FIELDS)
	customer_name = (customer_name or "").strip()
	contact_phone = (contact_phone or "").strip()
	if not customer_name or not contact_phone:
		frappe.throw(_("Customer name and contact phone are required."))
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		frappe.throw(_("A default company must be configured before accepting bookings."))
	request = frappe.get_doc(
		{
			"doctype": "Service Request",
			"company": company,
			"customer": _current_customer(optional=True),
			"subject": service_type or _("Service request from {0}").format(customer_name),
			"phone": contact_phone,
			"service_address": service_address,
			"service_type": service_type,
			"preferred_start": preferred_date,
			"description": notes,
			"source": "Portal",
			"status": "Open",
		}
	)
	request.flags.fsm_command = True
	request.insert(ignore_permissions=True)

	from fsm.service_operations.events import append_event

	append_event("request.opened", request, to_status="Open", source="Portal")
	return {"name": request.name}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60 * 60, methods="POST")
def book_appointment(**kwargs):
	"""Deprecated request_service alias retained for rolling client upgrades."""
	return request_service(**kwargs)


def _current_customer(optional: bool = False) -> str | None:
	"""Resolve the Customer linked to the signed-in user (via their Contact)."""
	return current_customer(optional=optional)


def _default_customer_group() -> str:
	return (
		frappe.db.get_single_value("Selling Settings", "customer_group")
		or frappe.db.get_value("Customer Group", {"is_group": 0})
		or "All Customer Groups"
	)


def _default_territory() -> str:
	return (
		frappe.db.get_single_value("Selling Settings", "territory")
		or frappe.db.get_value("Territory", {"is_group": 0})
		or "All Territories"
	)
