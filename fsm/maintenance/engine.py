from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta, timezone

import frappe
from dateutil import tz
from frappe import _
from frappe.utils import add_days, add_months, add_years, cint, get_datetime, getdate, now_datetime, nowdate

from fsm.service_operations.commands import plan_job

OPEN_OCCURRENCE_STATES = {"Forecast", "Due", "Overdue"}


def generate_occurrences(plan_name: str, horizon_date: str | None = None) -> list[str]:
	plan = frappe.get_doc("Maintenance Plan", plan_name)
	if plan.status != "Active":
		frappe.throw(_("Only an Active Maintenance Plan can generate occurrences."))
	today = getdate(nowdate())
	horizon = getdate(horizon_date or add_days(today, cint(plan.forecast_horizon_days)))
	if plan.end_date:
		horizon = min(horizon, getdate(plan.end_date))
	created = []
	for line in plan.lines:
		if not line.active:
			continue
		for equipment in _line_equipment(plan, line):
			due = getdate(line.first_due_date or plan.start_date)
			while due <= horizon:
				if due >= getdate(plan.start_date):
					name = _ensure_occurrence(plan, line, equipment, due, today)
					if name:
						created.append(name)
				due = _advance(due, cint(line.interval_count), line.interval_unit)
	return created


def _ensure_occurrence(plan, line, equipment, due, today, *, rescheduled_from=None):
	identity = _identity(plan.name, cint(plan.revision), line.name, equipment.installed_equipment, due)
	existing = frappe.db.get_value("Maintenance Occurrence", {"identity_key": identity})
	if existing:
		return existing
	status = _date_status(due, cint(line.grace_days), today)
	skip_reason = None
	if due < today and plan.catch_up_policy == "Skip Missed":
		status = "Skipped"
		skip_reason = "Skipped by Plan catch-up policy"
	due_utc, offset = _due_utc(due, line.scheduled_time, plan.timezone, plan.dst_policy)
	grouping_key = _grouping_key(plan, line, due)
	doc = frappe.get_doc(
		{
			"doctype": "Maintenance Occurrence",
			"identity_key": identity,
			"maintenance_plan": plan.name,
			"plan_revision": plan.revision,
			"plan_line": line.name,
			"plan_line_code": line.line_code,
			"installed_equipment": equipment.installed_equipment,
			"customer": plan.customer,
			"company": plan.company,
			"project": plan.project,
			"customer_site": plan.customer_site,
			"service_contract": plan.service_contract,
			"service_type": line.service_type,
			"due_date": due,
			"due_at_utc": due_utc,
			"due_timezone": plan.timezone,
			"due_offset_minutes": offset,
			"release_on": add_days(due, -cint(line.lead_days)),
			"grace_days": line.grace_days,
			"auto_release_job": line.auto_release_job,
			"status": status,
			"generated_on": now_datetime(),
			"grouping_key": grouping_key,
			"rescheduled_from": rescheduled_from,
			"skip_reason": skip_reason,
		}
	)
	doc.flags.fsm_occurrence_command = True
	try:
		doc.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		return frappe.db.get_value("Maintenance Occurrence", {"identity_key": identity})
	return doc.name


def update_occurrence_statuses(today=None) -> int:
	today = getdate(today or nowdate())
	updated = 0
	for name in frappe.get_all(
		"Maintenance Occurrence", filters={"status": ["in", sorted(OPEN_OCCURRENCE_STATES)]}, pluck="name"
	):
		doc = frappe.get_doc("Maintenance Occurrence", name)
		target = _date_status(getdate(doc.due_date), cint(doc.grace_days), today)
		if target != doc.status:
			doc.flags.fsm_occurrence_command = True
			doc.status = target
			doc.save()
			updated += 1
	return updated


def release_occurrences(names: list[str] | None = None, today=None) -> list[str]:
	today = getdate(today or nowdate())
	filters = {
		"status": ["in", sorted(OPEN_OCCURRENCE_STATES)],
		"auto_release_job": 1,
		"release_on": ["<=", today],
	}
	if names:
		filters["name"] = ["in", names]
	rows = frappe.get_all(
		"Maintenance Occurrence",
		filters=filters,
		fields=["name", "grouping_key"],
		order_by="due_date asc, name asc",
		limit=10000,
	)
	groups = defaultdict(list)
	for row in rows:
		groups[row.grouping_key].append(row.name)
	jobs = []
	for grouping_key, occurrence_names in groups.items():
		job = _release_group(grouping_key, occurrence_names)
		if job:
			jobs.append(job)
	return jobs


def _release_group(grouping_key: str, occurrence_names: list[str]):
	operation_key = hashlib.sha256(f"pm-release:{grouping_key}".encode()).hexdigest()
	frappe.db.sql(
		"select name from `tabMaintenance Occurrence` where grouping_key=%s order by name for update",
		grouping_key,
	)
	docs = [
		frappe.get_doc("Maintenance Occurrence", name)
		for name in occurrence_names
		if frappe.db.get_value("Maintenance Occurrence", name, "status") in OPEN_OCCURRENCE_STATES
	]
	if not docs:
		return None
	existing = frappe.db.get_value("Service Job", {"maintenance_release_key": operation_key})
	if existing:
		job = frappe.get_doc("Service Job", existing)
		if job.status in {"Completed", "Cancelled"}:
			frappe.throw(_("The deterministic PM release Job is already terminal."))
	else:
		first = docs[0]
		contracts = {doc.service_contract for doc in docs if doc.service_contract}
		job = frappe.get_doc(
			{
				"doctype": "Service Job",
				"maintenance_release_key": operation_key,
				"company": first.company,
				"project": first.project,
				"customer": first.customer,
				"service_type": first.service_type,
				"service_contract": next(iter(contracts)) if len(contracts) == 1 else None,
				"scheduled_date": min(get_datetime(doc.due_at_utc) for doc in docs),
				"status": "Draft",
				"notes": _("Generated from Preventive Maintenance occurrences."),
			}
		)
		job.flags.fsm_command = True
		for equipment in sorted({doc.installed_equipment for doc in docs}):
			job.append("equipment", {"installed_equipment": equipment, "service_scope": "Inspect"})
		try:
			job.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			job = frappe.get_doc(
				"Service Job", frappe.db.get_value("Service Job", {"maintenance_release_key": operation_key})
			)
		if job.status == "Draft":
			plan_job(job.name, source="Scheduler", correlation_id=operation_key)
			job = frappe.get_doc("Service Job", job.name)

	existing_equipment = {row.installed_equipment for row in job.equipment}
	missing = sorted({doc.installed_equipment for doc in docs} - existing_equipment)
	if missing:
		for equipment in missing:
			job.append("equipment", {"installed_equipment": equipment, "service_scope": "Inspect"})
		job.flags.fsm_command = True
		job.save()
	for doc in docs:
		doc.flags.fsm_occurrence_command = True
		doc.status = "Released"
		doc.released_job = job.name
		doc.save()
	return job.name


def skip_occurrence(name: str, reason: str):
	doc = frappe.get_doc("Maintenance Occurrence", name)
	if doc.status not in OPEN_OCCURRENCE_STATES:
		frappe.throw(_("Only an unreleased occurrence can be skipped."))
	doc.flags.fsm_occurrence_command = True
	doc.status = "Skipped"
	doc.skip_reason = reason
	doc.save()
	return doc


def reschedule_occurrence(name: str, due_date: str):
	doc = frappe.get_doc("Maintenance Occurrence", name)
	if doc.status not in OPEN_OCCURRENCE_STATES:
		frappe.throw(_("Only an unreleased occurrence can be rescheduled."))
	plan = frappe.get_doc("Maintenance Plan", doc.maintenance_plan)
	line = next((row for row in plan.lines if row.name == doc.plan_line), None)
	if not line:
		frappe.throw(_("The source Plan Line no longer exists."))
	equipment = next(row for row in plan.equipment if row.installed_equipment == doc.installed_equipment)
	new_name = _ensure_occurrence(
		plan, line, equipment, getdate(due_date), getdate(nowdate()), rescheduled_from=doc.name
	)
	doc.flags.fsm_occurrence_command = True
	doc.status = "Cancelled"
	doc.skip_reason = f"Rescheduled to {due_date}"
	doc.save()
	return frappe.get_doc("Maintenance Occurrence", new_name)


def supersede_revision(plan_name: str, old_revision: int, new_revision: int) -> int:
	count = 0
	for name in frappe.get_all(
		"Maintenance Occurrence",
		filters={
			"maintenance_plan": plan_name,
			"plan_revision": old_revision,
			"status": ["in", sorted(OPEN_OCCURRENCE_STATES)],
		},
		pluck="name",
	):
		doc = frappe.get_doc("Maintenance Occurrence", name)
		doc.flags.fsm_occurrence_command = True
		doc.status = "Cancelled"
		doc.skip_reason = f"Superseded by Plan revision {new_revision}"
		doc.save()
		count += 1
	return count


def project_job_completion(job) -> int:
	if job.status != "Completed":
		return 0
	count = 0
	for name in frappe.get_all(
		"Maintenance Occurrence", filters={"released_job": job.name, "status": "Released"}, pluck="name"
	):
		doc = frappe.get_doc("Maintenance Occurrence", name)
		doc.flags.fsm_occurrence_command = True
		doc.status = "Completed"
		doc.save()
		count += 1
	return count


def _line_equipment(plan, line):
	rows = [row for row in plan.equipment if row.active]
	if line.equipment_scope == "Single Equipment":
		return [row for row in rows if row.installed_equipment == line.installed_equipment]
	if line.equipment_scope == "Item Group":
		return [row for row in rows if row.item_group == line.item_group]
	return rows


def _advance(value, count: int, unit: str):
	if unit == "Days":
		return getdate(add_days(value, count))
	if unit == "Weeks":
		return getdate(add_days(value, count * 7))
	if unit == "Months":
		return getdate(add_months(value, count))
	if unit == "Years":
		return getdate(add_years(value, count))
	frappe.throw(_("Unsupported maintenance interval unit."), frappe.ValidationError)


def _date_status(due, grace_days: int, today):
	if add_days(due, grace_days) < today:
		return "Overdue"
	if due <= today:
		return "Due"
	return "Forecast"


def _identity(plan, revision, line, equipment, due) -> str:
	return hashlib.sha256(f"{plan}:{revision}:{line}:{equipment}:{due}".encode()).hexdigest()


def _grouping_key(plan, line, due) -> str:
	window = max(cint(plan.due_window_days), 1)
	bucket = getdate(due).toordinal() // window
	value = f"{plan.name}:{plan.revision}:{plan.company}:{plan.customer}:{plan.customer_site}:{line.service_type}:{window}:{bucket}"
	return hashlib.sha256(value.encode()).hexdigest()


def _due_utc(due, scheduled_time, timezone_name: str, dst_policy: str):
	clock = scheduled_time or time(9, 0)
	if isinstance(clock, str):
		clock = time.fromisoformat(clock)
	elif isinstance(clock, timedelta):
		seconds = int(clock.total_seconds()) % (24 * 60 * 60)
		clock = time(seconds // 3600, (seconds % 3600) // 60, seconds % 60)
	zone = tz.gettz(timezone_name)
	local = datetime.combine(getdate(due), clock).replace(tzinfo=zone)
	if not tz.datetime_exists(local):
		local = tz.resolve_imaginary(local)
	elif tz.datetime_ambiguous(local):
		local = local.replace(fold=1 if dst_policy == "Second Occurrence" else 0)
	offset = int((local.utcoffset() or UTC.utcoffset(local)).total_seconds() / 60)
	return local.astimezone(UTC).replace(tzinfo=None), offset
