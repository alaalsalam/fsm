# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

import frappe

from fsm.security.scopes import FSM_MANAGER, SYSTEM_MANAGER

SERVICE_JOB_EVENT = "fsm_service_job_update"
TECHNICIAN_EVENT = "fsm_technician_update"

_RECIPIENT_CACHE_TTL = 60


def _dispatch_recipients(company: str | None) -> list[str]:
	"""Users authorized to see dispatch telemetry for a company: System Managers
	plus FSM Managers whose Company user-permission covers it (or who have no
	company restriction). Cached briefly — doc events fire on every save."""
	cache_key = f"fsm_dispatch_recipients::{company or ''}"
	cached = frappe.cache().get_value(cache_key)
	if cached is not None:
		return cached

	role_holders = frappe.get_all(
		"Has Role",
		filters={
			"role": ["in", [FSM_MANAGER, SYSTEM_MANAGER]],
			"parenttype": "User",
		},
		pluck="parent",
		distinct=True,
	)
	enabled = set(
		frappe.get_all(
			"User",
			filters={"name": ["in", role_holders], "enabled": 1},
			pluck="name",
		)
	)
	if company:
		restricted = frappe.get_all(
			"User Permission",
			filters={"allow": "Company", "user": ["in", list(enabled)]},
			fields=["user", "for_value"],
		)
		scoped_users = {row.user for row in restricted}
		company_users = {row.user for row in restricted if row.for_value == company}
		enabled = (enabled - scoped_users) | company_users

	recipients = sorted(enabled)
	frappe.cache().set_value(cache_key, recipients, expires_in_sec=_RECIPIENT_CACHE_TTL)
	return recipients


def _publish_scoped(event: str, payload: dict, company: str | None, extra_users: list[str]):
	users = set(_dispatch_recipients(company)) | {u for u in extra_users if u}
	for user in users:
		frappe.publish_realtime(event, payload, user=user, after_commit=True)


def on_service_job_update(doc, method=None):
	"""Send a compact Service Job summary to authorized dispatch users only."""
	technician_user = (
		frappe.db.get_value("Technician", doc.primary_technician, "user")
		if doc.primary_technician
		else None
	)
	_publish_scoped(
		SERVICE_JOB_EVENT,
		{
			"name": doc.name,
			"customer_name": doc.customer_name,
			"status": doc.status,
			"priority": doc.priority,
			"scheduled_date": str(doc.scheduled_date) if doc.scheduled_date else None,
			"primary_technician": doc.primary_technician,
			"sla_breached": doc.sla_breached,
		},
		doc.company,
		[technician_user],
	)


def on_technician_update(doc, method=None):
	"""Send technician availability / location changes to authorized dispatch
	users of the technician's company only — GPS is sensitive telemetry."""
	_publish_scoped(
		TECHNICIAN_EVENT,
		{
			"name": doc.name,
			"technician_name": doc.technician_name,
			"status": doc.status,
			"clocked_in": doc.clocked_in,
			"last_seen_latitude": doc.last_seen_latitude,
			"last_seen_longitude": doc.last_seen_longitude,
			"last_seen_on": str(doc.last_seen_on) if doc.last_seen_on else None,
		},
		doc.company,
		[doc.user],
	)
