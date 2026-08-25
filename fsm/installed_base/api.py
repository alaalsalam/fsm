from __future__ import annotations

import json

import frappe

from fsm.installed_base.access import require_equipment_access, require_site_access
from fsm.installed_base.warranty import get_equipment_warranty_status, warranty_status_for
from fsm.security.policy import bounded_int, require_authenticated


@frappe.whitelist()
def list_customer_sites(customer=None, company=None, status=None, limit=100):
	require_authenticated()
	filters = {
		key: value
		for key, value in {"customer": customer, "company": company, "status": status}.items()
		if value
	}
	return frappe.get_list(
		"Customer Site",
		filters=filters,
		fields=[
			"name",
			"site_name",
			"site_code",
			"customer",
			"company",
			"status",
			"address_display",
			"city",
			"territory",
		],
		order_by="site_name asc",
		limit=bounded_int(limit, 1, 200),
	)


@frappe.whitelist()
def get_customer_site(site: str):
	doc = require_site_access(site)
	result = doc.as_dict()
	result["equipment_count"] = frappe.db.count("Installed Equipment", {"customer_site": doc.name})
	result["active_equipment"] = frappe.db.count(
		"Installed Equipment", {"customer_site": doc.name, "status": "Active"}
	)
	result["service_requests"] = frappe.get_list(
		"Service Request",
		filters={"customer_site": doc.name},
		fields=["name", "subject", "status", "creation"],
		limit=100,
	)
	job_names = frappe.get_all(
		"Service Job Equipment",
		filters={"customer_site": doc.name, "parenttype": "Service Job"},
		pluck="parent",
	)
	result["service_jobs"] = (
		frappe.get_list(
			"Service Job",
			filters={"name": ("in", job_names)},
			fields=["name", "status", "scheduled_date"],
			limit=100,
		)
		if job_names
		else []
	)
	return result


@frappe.whitelist()
def list_equipment_locations(customer_site: str):
	require_site_access(customer_site)
	return frappe.get_list(
		"Equipment Location",
		filters={"customer_site": customer_site},
		fields=["name", "location_name", "location_code", "parent_location", "location_type", "active"],
		order_by="location_name asc",
		limit=500,
	)


@frappe.whitelist()
def get_customer_equipment(
	customer=None,
	customer_site=None,
	item_code=None,
	status=None,
	serial_no=None,
	company=None,
	warranty=None,
	limit=100,
):
	require_authenticated()
	filters = {
		key: value
		for key, value in {
			"customer": customer,
			"customer_site": customer_site,
			"item_code": item_code,
			"status": status,
			"serial_no": serial_no,
			"company": company,
		}.items()
		if value
	}
	rows = frappe.get_list(
		"Installed Equipment",
		filters=filters,
		fields=[
			"name",
			"equipment_id",
			"equipment_name",
			"company",
			"customer",
			"customer_site",
			"equipment_location",
			"item_code",
			"item_name",
			"serial_no",
			"status",
			"installation_date",
			"warranty_end_date",
			"last_service_date",
		],
		order_by="modified desc",
		limit=bounded_int(limit, 1, 200),
	)
	for row in rows:
		row.warranty_status = warranty_status_for(row.warranty_end_date)
	if warranty:
		rows = [row for row in rows if row.warranty_status == warranty]
	return rows


@frappe.whitelist()
def get_equipment(equipment: str):
	doc = require_equipment_access(equipment)
	result = doc.as_dict()
	result.warranty_status = get_equipment_warranty_status(doc)
	result.service_jobs = frappe.get_all(
		"Service Job Equipment",
		filters={"installed_equipment": doc.name},
		fields=["parent as service_job", "service_scope"],
		order_by="creation desc",
		limit=100,
	)
	return result


@frappe.whitelist()
def resolve_equipment_by_qr(token: str):
	require_authenticated()
	name = frappe.db.get_value("Installed Equipment", {"qr_code": token}, "name")
	if not name:
		frappe.throw("Equipment QR token was not found.", frappe.DoesNotExistError)
	return get_equipment(name)


@frappe.whitelist()
def get_equipment_history(equipment: str):
	doc = require_equipment_access(equipment)
	job_names = frappe.get_all(
		"Service Job Equipment", filters={"installed_equipment": doc.name}, pluck="parent", limit=500
	)
	filters = [["installed_equipment", "=", doc.name]]
	if job_names:
		filters = [["installed_equipment", "=", doc.name], ["service_job", "in", job_names]]
		events = frappe.get_list(
			"Service Event Log",
			or_filters=filters,
			fields=[
				"event_id",
				"event_type",
				"reference_doctype",
				"reference_name",
				"service_job",
				"service_visit",
				"from_status",
				"to_status",
				"event_time",
				"source",
				"metadata_json",
			],
			order_by="event_time asc",
			limit=1000,
		)
	else:
		events = frappe.get_list(
			"Service Event Log",
			filters={"installed_equipment": doc.name},
			fields=[
				"event_id",
				"event_type",
				"reference_doctype",
				"reference_name",
				"service_job",
				"service_visit",
				"from_status",
				"to_status",
				"event_time",
				"source",
				"metadata_json",
			],
			order_by="event_time asc",
			limit=1000,
		)
	for event in events:
		event.metadata = json.loads(event.metadata_json or "{}")
	return events


@frappe.whitelist()
def get_job_equipment(job: str):
	from fsm.security.policy import require_job_access

	require_job_access(job, "read")
	return frappe.get_all(
		"Service Job Equipment",
		filters={"parent": job, "parenttype": "Service Job"},
		fields=[
			"installed_equipment",
			"customer_site",
			"equipment_location",
			"item_code",
			"serial_no",
			"equipment_status",
			"service_scope",
			"notes",
		],
		order_by="idx asc",
		limit=500,
	)
