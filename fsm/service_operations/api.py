import frappe

from fsm.security.policy import bounded_int, require_authenticated, require_job_access
from fsm.service_operations.commands import _request_access, _visit_read_access


@frappe.whitelist()
def list_service_requests(status=None, limit=100):
	require_authenticated()
	filters = {"status": status} if status else {}
	return frappe.get_list(
		"Service Request", filters=filters,
		fields=["name", "subject", "customer", "status", "priority", "source", "service_type", "preferred_start", "creation"],
		order_by="creation desc", limit=bounded_int(limit, 1, 200),
	)


@frappe.whitelist()
def get_service_request(request: str):
	doc = _request_access(request)
	result = doc.as_dict()
	result["service_jobs"] = frappe.get_list(
		"Service Job", filters={"service_request": doc.name},
		fields=["name", "status", "phase", "primary_technician", "scheduled_date"],
		order_by="creation asc",
	)
	return result


@frappe.whitelist()
def get_job_visits(job: str):
	require_job_access(job, "read")
	return frappe.get_list(
		"Service Visit", filters={"service_job": job},
		fields=["name", "visit_number", "status", "primary_technician", "scheduled_start", "scheduled_end", "actual_check_in", "actual_completion"],
		order_by="visit_number asc",
	)


@frappe.whitelist()
def get_service_visit(visit: str):
	return _visit_read_access(visit).as_dict()


@frappe.whitelist()
def get_service_timeline(reference_doctype: str, reference_name: str):
	if reference_doctype == "Service Request":
		_request_access(reference_name)
		filters = {"service_request": reference_name}
	elif reference_doctype == "Service Job":
		require_job_access(reference_name, "read")
		filters = {"service_job": reference_name}
	elif reference_doctype == "Service Visit":
		_visit_read_access(reference_name)
		filters = {"service_visit": reference_name}
	else:
		frappe.throw("Unsupported service timeline reference.")
	return frappe.get_list(
		"Service Event Log", filters=filters,
		fields=["event_id", "event_type", "actor", "actor_type", "from_status", "to_status", "from_phase", "to_phase", "event_time", "source", "metadata_json"],
		order_by="event_time asc", limit=500,
	)
