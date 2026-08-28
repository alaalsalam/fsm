# Copyright (c) 2026, DIGIT and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, flt, get_datetime, nowdate, time_diff_in_hours

from fsm.security.policy import bounded_int, require_manager_scope, require_role, resolve_manager_company
from fsm.security.scopes import FSM_MANAGER, SYSTEM_MANAGER


def _since(days: int) -> str:
	return add_days(nowdate(), -int(days))


@frappe.whitelist()
def service_performance(days: int = 90):
	"""Headline service KPIs over a recent window."""
	require_role(FSM_MANAGER, SYSTEM_MANAGER)
	since = _since(days)
	jobs = frappe.get_list(
		"Service Job",
		filters=[["creation", ">=", since]],
		fields=[
			"name",
			"status",
			"creation",
			"scheduled_date",
			"promised_response_by",
			"responded_on",
			"completed_on",
			"actual_hours",
			"sla_breached",
		],
	)
	total = len(jobs)
	completed = [j for j in jobs if j.status == "Completed"]

	mttr_vals = [time_diff_in_hours(j.completed_on, j.creation) for j in completed if j.completed_on]
	mttr = round(sum(mttr_vals) / len(mttr_vals), 2) if mttr_vals else None

	hour_vals = [j.actual_hours for j in completed if j.actual_hours]
	avg_completion = round(sum(hour_vals) / len(hour_vals), 2) if hour_vals else None

	punctual_base, punctual_ok = 0, 0
	for j in jobs:
		target = j.promised_response_by or j.scheduled_date
		if target and j.responded_on:
			punctual_base += 1
			if get_datetime(j.responded_on) <= get_datetime(target):
				punctual_ok += 1
	punctuality = round(punctual_ok / punctual_base * 100) if punctual_base else None

	returned = set(
		frappe.get_list(
			"Service Return",
			filters=[["service_job", "in", [j.name for j in completed] or [""]]],
			pluck="service_job",
		)
	)
	ftf = None
	if completed:
		first_time = len([j for j in completed if j.name not in returned])
		ftf = round(first_time / len(completed) * 100)

	return {
		"window_days": int(days),
		"total_jobs": total,
		"completed_jobs": len(completed),
		"completion_rate": round(len(completed) / total * 100) if total else None,
		"first_time_fix_rate": ftf,
		"mttr_hours": mttr,
		"avg_completion_hours": avg_completion,
		"punctuality_pct": punctuality,
		"sla_breaches": len([j for j in jobs if j.sla_breached]),
	}


@frappe.whitelist()
def workorder_volume(days: int = 90):
	"""Volume & mix of work orders: by status, by service type, and a daily trend."""
	require_role(FSM_MANAGER, SYSTEM_MANAGER)
	since = _since(days)
	jobs = frappe.get_list(
		"Service Job",
		filters=[["creation", ">=", since]],
		fields=["status", "service_type", "creation"],
	)
	by_status = _count_by(jobs, lambda j: j.status)
	by_service_type = _count_by(jobs, lambda j: j.service_type or "Unspecified")
	by_day = _count_by(jobs, lambda j: str(get_datetime(j.creation).date()))

	open_statuses = {"Draft", "Planned", "Scheduled", "Dispatched", "In Progress", "On Hold"}
	return {
		"window_days": int(days),
		"total": len(jobs),
		"open": len([j for j in jobs if j.status in open_statuses]),
		"completed": len([j for j in jobs if j.status == "Completed"]),
		"by_status": by_status,
		"by_service_type": by_service_type,
		"trend": [{"date": d, "count": c} for d, c in sorted(by_day.items())],
	}


@frappe.whitelist()
def inventory_usage(days: int = 90, limit: int = 20):
	"""Parts consumed on completed jobs in the window, ranked by quantity."""
	require_role(FSM_MANAGER, SYSTEM_MANAGER)
	since = _since(days)
	job_names = frappe.get_list(
		"Service Job",
		filters=[["status", "=", "Completed"], ["completed_on", ">=", since]],
		pluck="name",
	)
	if not job_names:
		return {"window_days": int(days), "items": []}

	rows = frappe.get_all(
		"Service Job Item",
		filters=[["parent", "in", job_names]],
		fields=["item_code", "item_name", "qty", "amount"],
	)
	agg: dict[str, dict] = {}
	for r in rows:
		a = agg.setdefault(
			r.item_code, {"item_code": r.item_code, "item_name": r.item_name, "qty": 0.0, "amount": 0.0}
		)
		a["qty"] += r.qty or 0
		a["amount"] += r.amount or 0

	items = sorted(agg.values(), key=lambda x: x["qty"], reverse=True)[: bounded_int(limit, 1, 100)]
	for it in items:
		it["qty"] = round(it["qty"], 2)
		it["amount"] = round(it["amount"], 2)
	return {"window_days": int(days), "items": items}


@frappe.whitelist()
def technician_utilization(days: int = 90):
	"""Per-technician job count, hours, average pace and completion rate."""
	require_role(FSM_MANAGER, SYSTEM_MANAGER)
	since = _since(days)
	jobs = frappe.get_list(
		"Service Job",
		filters=[["creation", ">=", since], ["primary_technician", "is", "set"]],
		fields=["primary_technician", "status", "actual_hours"],
	)
	agg: dict[str, dict] = {}
	for j in jobs:
		a = agg.setdefault(
			j.primary_technician,
			{"technician": j.primary_technician, "jobs": 0, "completed": 0, "hours": 0.0},
		)
		a["jobs"] += 1
		a["hours"] += j.actual_hours or 0
		if j.status == "Completed":
			a["completed"] += 1

	out = []
	for a in agg.values():
		a["hours"] = round(a["hours"], 2)
		a["avg_hours_per_job"] = round(a["hours"] / a["jobs"], 2) if a["jobs"] else 0
		a["completion_rate"] = round(a["completed"] / a["jobs"] * 100) if a["jobs"] else 0
		out.append(a)
	out.sort(key=lambda x: x["jobs"], reverse=True)
	return {"window_days": int(days), "technicians": out}


def _count_by(rows, key) -> dict:
	out: dict[str, int] = {}
	for r in rows:
		k = key(r)
		out[k] = out.get(k, 0) + 1
	return out


@frappe.whitelist()
def domain_dashboard(days: int = 90):
	"""Cross-domain operational scorecard; every root is explicitly Company scoped."""
	days = bounded_int(days, 1, 730)
	company = resolve_manager_company()
	require_manager_scope(company)
	since = _since(days)
	jobs = frappe.get_list(
		"Service Job",
		filters={"company": company, "creation": [">=", since]},
		fields=["name", "customer", "status", "assigned_service_team", "service_contract", "actual_hours", "completed_on", "sales_invoice", "total_cost"],
		limit=5000,
	)
	job_names = [row.name for row in jobs]
	completed_names = [row.name for row in jobs if row.status == "Completed"]
	sites = frappe.get_list("Customer Site", filters={"company": company}, pluck="name", limit=0)
	equipment = frappe.get_list("Installed Equipment", filters={"company": company}, fields=["name", "customer", "model_no", "expiry_date", "hydro_due_date"], limit=0)
	contracts = frappe.get_list("Service Contract", filters={"company": company}, fields=["name", "status", "end_date", "included_visits"], limit=1000)
	occurrences = frappe.get_list("Maintenance Occurrence", filters={"company": company}, fields=["status", "installed_equipment", "due_date"], limit=5000)
	inspections = frappe.get_list("Equipment Inspection", filters={"company": company, "creation": [">=", since]}, fields=["overall_result", "installed_equipment"], limit=5000)
	failures = frappe.get_list("Failure Analysis", filters={"service_job": ["in", job_names or [""]]}, fields=["installed_equipment", "repeat_failure", "severity"], limit=5000)
	returns = frappe.get_list("Service Return", filters={"service_job": ["in", job_names or [""]]}, fields=["installed_equipment", "final_outcome", "status"], limit=5000)
	profit = _profit_totals(jobs)
	team_rows = _team_metrics(jobs, completed_names)
	contract_usage = frappe.get_all("Service Contract Entitlement", filters={"parent": ["in", [row.name for row in contracts] or [""]]}, fields=["included_quantity", "used_quantity", "remaining_quantity"])
	today = nowdate()
	return {
		"window_days": days,
		"company": company,
		"executive": {
			"customers": len({row.customer for row in jobs if row.customer}), "sites": len(sites), "installed_equipment": len(equipment),
			"active_contracts": sum(row.status == "Active" for row in contracts), "due_maintenance": sum(row.status == "Due" for row in occurrences),
			"overdue_maintenance": sum(row.status == "Overdue" for row in occurrences), **profit,
		},
		"operations": service_performance(days),
		"maintenance": {
			"pm_compliance_pct": _percent(sum(row.status == "Completed" for row in occurrences), sum(row.status in {"Completed", "Overdue"} for row in occurrences)),
			"due": sum(row.status == "Due" for row in occurrences), "overdue": sum(row.status == "Overdue" for row in occurrences),
			"first_time_pass_pct": _percent(sum(row.overall_result == "Pass" for row in inspections), len(inspections)),
			"failed_inspections": sum(row.overall_result in {"Fail", "Needs Repair", "Needs Replacement"} for row in inspections),
			"refill_due": sum(row.overall_result == "Needs Refill" for row in inspections),
			"hydro_due": sum(bool(row.hydro_due_date and str(row.hydro_due_date) <= today) for row in equipment),
			"expired_equipment": sum(bool(row.expiry_date and str(row.expiry_date) <= today) for row in equipment),
		},
		"teams": team_rows,
		"contracts": {
			"active": sum(row.status == "Active" for row in contracts), "renewal_due": sum(row.status == "Active" and str(row.end_date) <= add_days(today, 60) for row in contracts),
			"expired": sum(row.status == "Expired" for row in contracts), "visits_used": sum(flt(row.used_quantity) for row in contract_usage),
			"visits_remaining": sum(flt(row.remaining_quantity) for row in contract_usage), "revenue": profit["service_revenue"], "cost": profit["service_cost"], "margin": profit["gross_margin"],
		},
		"equipment": {
			"failures": len(failures), "repeat_failures": sum(row.repeat_failure for row in failures),
			"repair": sum(row.final_outcome == "Repaired" for row in returns), "replacement": sum(row.final_outcome in {"Replacement Recommended", "Replaced"} for row in returns),
			"model_trends": _count_by(equipment, lambda row: row.model_no or "Unspecified"),
		},
	}


def _profit_totals(jobs):
	revenue = 0.0
	for job in jobs:
		if job.sales_invoice:
			revenue += flt(frappe.db.get_value("Sales Invoice", job.sales_invoice, "grand_total"))
	cost = sum(flt(row.total_cost) for row in jobs)
	return {"service_revenue": revenue, "service_cost": cost, "gross_margin": revenue - cost}


def _team_metrics(jobs, completed_names):
	by_team: dict[str, dict] = {}
	for job in jobs:
		team = job.assigned_service_team or "Unassigned"
		row = by_team.setdefault(team, {"team": team, "jobs": 0, "completed": 0, "units_inspected": 0, "hours": 0.0, "revisits": 0, "customer_rating": None})
		row["jobs"] += 1
		row["completed"] += int(job.status == "Completed")
		row["hours"] += flt(job.actual_hours)
	if completed_names:
		units = frappe.get_all("Service Job Equipment", filters={"parent": ["in", completed_names]}, fields=["parent"])
		team_by_job = {row.name: row.assigned_service_team or "Unassigned" for row in jobs}
		for unit in units:
			by_team[team_by_job[unit.parent]]["units_inspected"] += 1
		visits = frappe.get_all("Service Visit", filters={"service_job": ["in", completed_names]}, fields=["service_job"])
		visit_counts = _count_by(visits, lambda row: row.service_job)
		for job, count in visit_counts.items():
			by_team[team_by_job[job]]["revisits"] += max(count - 1, 0)
		feedback = frappe.get_all("Service Feedback", filters={"service_job": ["in", completed_names]}, fields=["service_job", "rating"])
		for team in by_team:
			ratings = [flt(row.rating) for row in feedback if team_by_job[row.service_job] == team]
			by_team[team]["customer_rating"] = round(sum(ratings) / len(ratings), 2) if ratings else None
	for row in by_team.values():
		row["units_per_hour"] = round(row["units_inspected"] / row["hours"], 2) if row["hours"] else 0
	return sorted(by_team.values(), key=lambda row: row["jobs"], reverse=True)


def _percent(value, total):
	return round(value / total * 100) if total else None
