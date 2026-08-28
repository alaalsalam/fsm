# Copyright (c) 2026, DIGIT and contributors
# For license information, please see license.txt


# Dynamic scheduling / dispatch engine.
#
# Ranks technicians for a Service Job by availability, skill match and territory
# coverage so dispatchers (console) get a suggested order and can one-click assign.
# Intentionally dependency-free heuristics, the AI/ML optimiser (Phase 6) can later
# replace `score_technician` without touching the API surface.

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime

from fsm.security.policy import (
	bounded_int,
	require_job_access,
	require_manager_scope,
	resolve_manager_company,
)

_SKILL_WEIGHT = 50
_TERRITORY_WEIGHT = 30
_AVAILABLE_WEIGHT = 20
_PROXIMITY_WEIGHT = 25
_PROFICIENCY_BONUS = {"Beginner": 0, "Intermediate": 5, "Expert": 10}

_TEAM_CAPACITY_WEIGHT = 20
_TEAM_WORKLOAD_WEIGHT = 15
_LIVE_JOB_STATUSES = ("Scheduled", "Dispatched", "In Progress")


@frappe.whitelist()
def suggest_technicians(job: str, limit: int = 10):
	"""Return technicians ranked for a job, best first, each with a match breakdown.

	Consumed by the console dispatch board to power "suggested technician" UX."""
	doc = frappe.get_doc("Service Job", job)
	require_job_access(doc, "read", manager_only=True)
	candidates = _eligible_technicians(doc.company)
	territories = _territory_ancestors(doc.territory)

	ranked = []
	for tech in candidates:
		score, reasons = score_technician(tech, doc, territories)
		if score is None:
			continue
		ranked.append(
			{
				"technician": tech.name,
				"technician_name": tech.technician_name,
				"status": tech.status,
				"territory": tech.territory,
				"score": score,
				"reasons": reasons,
			}
		)

	ranked.sort(key=lambda r: r["score"], reverse=True)
	return ranked[: bounded_int(limit, 1, 50)]


@frappe.whitelist()
def assign_technician(job: str, technician: str):
	"""Assign a technician to a job (with a conflict check) and return the job."""
	doc = frappe.get_doc("Service Job", job)
	require_job_access(doc, "write", manager_only=True)
	technician_company = frappe.db.get_value("Technician", technician, "company")
	if technician_company != doc.company:
		frappe.throw(_("The technician and job must belong to the same company."), frappe.PermissionError)
	if doc.scheduled_date and _has_conflict(technician, doc):
		frappe.throw(
			_("{0} already has a job booked at that time.").format(
				frappe.db.get_value("Technician", technician, "technician_name") or technician
			)
		)
	doc.primary_technician = technician
	doc.save()
	return doc.as_dict()


@frappe.whitelist()
def get_available_technicians(
	territory: str | None = None,
	service_type: str | None = None,
	scheduled_date: str | None = None,
	company: str | None = None,
):
	"""Lightweight finder used when creating a job (no Service Job doc yet)."""
	company = resolve_manager_company(company)
	require_manager_scope(company, territory)
	territories = _territory_ancestors(territory)
	out = []
	for tech in _eligible_technicians(company):
		if scheduled_date and _busy_at(tech.name, scheduled_date):
			continue
		matches_territory = not tech.territory or tech.territory in territories
		matches_skill = not service_type or _has_skill(tech.name, service_type)
		out.append(
			{
				"technician": tech.name,
				"technician_name": tech.technician_name,
				"status": tech.status,
				"territory": tech.territory,
				"matches_territory": matches_territory,
				"matches_skill": matches_skill,
			}
		)
	out.sort(
		key=lambda r: (r["matches_skill"], r["matches_territory"], r["status"] == "Available"),
		reverse=True,
	)
	return out


@frappe.whitelist()
def suggest_teams(job: str, limit: int = 10):
	"""Return service teams ranked for a job, best first, with a match breakdown.

	Mirrors suggest_technicians so the dispatch board can suggest a crew, not just
	a lone technician."""
	doc = frappe.get_doc("Service Job", job)
	require_job_access(doc, "read", manager_only=True)
	territories = _territory_ancestors(doc.territory)

	ranked = []
	for team in _eligible_teams(doc.company):
		score, reasons = score_team(team, doc, territories)
		if score is None:
			continue
		ranked.append(
			{
				"team": team.name,
				"team_name": team.team_name,
				"territory": team.territory,
				"team_leader": team.team_leader,
				"score": score,
				"reasons": reasons,
			}
		)

	ranked.sort(key=lambda r: r["score"], reverse=True)
	return ranked[: bounded_int(limit, 1, 50)]


@frappe.whitelist()
def assign_team(job: str, team: str):
	"""Assign a service team to a job (company + capacity checked) and return the job.

	team_leader is fetched onto the job automatically via fetch_from."""
	doc = frappe.get_doc("Service Job", job)
	require_job_access(doc, "write", manager_only=True)

	team_doc = frappe.db.get_value(
		"Service Team", team, ["company", "status", "active", "capacity"], as_dict=True
	)
	if not team_doc:
		frappe.throw(_("Service Team {0} was not found.").format(team), frappe.DoesNotExistError)
	if team_doc.company != doc.company:
		frappe.throw(_("The team and job must belong to the same company."), frappe.PermissionError)
	if not team_doc.active or team_doc.status != "Active":
		frappe.throw(_("Team {0} is not active.").format(team), frappe.ValidationError)
	if team_doc.capacity and _team_open_job_count(team, exclude_job=doc.name) >= team_doc.capacity:
		frappe.throw(_("Team {0} is already at capacity.").format(team), frappe.ValidationError)

	doc.assigned_service_team = team
	doc.save()
	return doc.as_dict()


def score_team(team, job, territories: set[str]) -> tuple[int | None, list[str]]:
	"""Score one team against a job. Returns (score, reasons) or (None, _) when the
	team is hard-excluded (over capacity, or every active member double-booked)."""
	members = _team_active_members(team.name)

	open_jobs = _team_open_job_count(team.name, exclude_job=job.name)
	if team.capacity and open_jobs >= team.capacity:
		return None, []

	if members:
		conflicted = sum(1 for m in members if _has_conflict(m, job))
		if job.scheduled_date and conflicted >= len(members):
			return None, []
	else:
		conflicted = 0

	score, reasons = 0, []

	if job.service_type and any(_has_skill(m, job.service_type) for m in members):
		bonus = max((_best_proficiency_bonus(m, job.service_type) for m in members), default=0)
		score += _SKILL_WEIGHT + bonus
		reasons.append(_("A member has the required skill"))

	if not team.territory or (territories and team.territory in territories):
		score += _TERRITORY_WEIGHT
		reasons.append(_("Covers the territory"))

	if team.status == "Active":
		score += _AVAILABLE_WEIGHT
		reasons.append(_("Team is active"))

	if team.capacity:
		remaining = team.capacity - open_jobs
		score += round(_TEAM_CAPACITY_WEIGHT * remaining / team.capacity)
		reasons.append(_("Has spare capacity"))

	if conflicted:
		score -= _TEAM_WORKLOAD_WEIGHT * conflicted
		reasons.append(_("{0} member(s) have a clashing booking").format(conflicted))

	return score, reasons


def _eligible_teams(company: str) -> list:
	"""Active service teams for a company, with the fields team scoring needs."""
	return frappe.get_list(
		"Service Team",
		filters={"active": 1, "status": "Active", "company": company},
		fields=["name", "team_name", "territory", "team_leader", "status", "capacity"],
	)


def _team_active_members(team: str) -> list[str]:
	"""Technician names of a team's active members."""
	return frappe.get_all(
		"Service Team Member",
		filters={"parent": team, "parenttype": "Service Team", "active": 1},
		pluck="technician",
	)


def _team_open_job_count(team: str, exclude_job: str | None = None) -> int:
	"""Count of live jobs currently assigned to a team."""
	filters = {
		"assigned_service_team": team,
		"status": ["in", list(_LIVE_JOB_STATUSES)],
	}
	if exclude_job:
		filters["name"] = ["!=", exclude_job]
	return frappe.db.count("Service Job", filters)


def score_technician(tech, job, territories: set[str]) -> tuple[int | None, list[str]]:
	"""Score one technician against a job. Returns (score, reasons) or (None, _)
	when the technician is hard-excluded (double-booked at the slot)."""
	if job.scheduled_date and _has_conflict(tech.name, job):
		return None, []

	score, reasons = 0, []

	if job.service_type and _has_skill(tech.name, job.service_type):
		bonus = _best_proficiency_bonus(tech.name, job.service_type)
		score += _SKILL_WEIGHT + bonus
		reasons.append(_("Has the required skill"))

	if not tech.territory or (territories and tech.territory in territories):
		score += _TERRITORY_WEIGHT
		reasons.append(_("Covers the territory"))

	if tech.status == "Available":
		score += _AVAILABLE_WEIGHT
		reasons.append(_("Currently available"))

	proximity = _proximity_score(tech, job)
	if proximity is not None:
		score += proximity
		reasons.append(_("Near the job site"))

	return score, reasons


def _eligible_technicians(company: str) -> list:
	"""Active technicians who are not off duty, with the fields scoring needs."""
	return frappe.get_list(
		"Technician",
		filters={"active": 1, "status": ["!=", "Off Duty"], "company": company},
		fields=[
			"name",
			"technician_name",
			"status",
			"territory",
			"last_seen_latitude",
			"last_seen_longitude",
		],
	)


def _has_skill(technician: str, service_type: str) -> bool:
	"""A technician 'has the skill' when one of their skills matches the service type."""
	skills = frappe.get_all("Technician Skill", filters={"parent": technician}, pluck="skill")
	needle = (service_type or "").strip().lower()
	return any(needle and needle in (s or "").strip().lower() for s in skills)


def _best_proficiency_bonus(technician: str, service_type: str) -> int:
	needle = (service_type or "").strip().lower()
	rows = frappe.get_all(
		"Technician Skill",
		filters={"parent": technician},
		fields=["skill", "proficiency"],
	)
	best = 0
	for row in rows:
		if needle and needle in (row.skill or "").strip().lower():
			best = max(best, _PROFICIENCY_BONUS.get(row.proficiency, 0))
	return best


def _territory_ancestors(territory: str | None) -> set[str]:
	"""The territory plus its ancestors, so a technician covering a parent zone
	is considered a match for a child zone."""
	chain: set[str] = set()
	current = territory
	guard = 0
	while current and guard < 20:
		chain.add(current)
		current = frappe.db.get_value("Service Territory", current, "parent_territory")
		guard += 1
	return chain


def _has_conflict(technician: str, job) -> bool:
	"""True if the technician already has a live job overlapping this job's window."""
	if not job.scheduled_date:
		return False
	start = get_datetime(job.scheduled_date)
	end = get_datetime(job.scheduled_end) if job.scheduled_end else add_to_date(start, hours=1)

	others = frappe.get_list(
		"Service Job",
		filters={
			"primary_technician": technician,
			"name": ["!=", job.name or ""],
			"status": ["in", ["Scheduled", "Dispatched", "In Progress"]],
			"scheduled_date": ["is", "set"],
		},
		fields=["scheduled_date", "scheduled_end"],
	)
	for other in others:
		o_start = get_datetime(other.scheduled_date)
		o_end = get_datetime(other.scheduled_end) if other.scheduled_end else add_to_date(o_start, hours=1)
		if start < o_end and o_start < end:
			return True
	return False


def _busy_at(technician: str, scheduled_date: str) -> bool:
	stub = frappe._dict({"name": None, "scheduled_date": scheduled_date, "scheduled_end": None})
	return _has_conflict(technician, stub)


def has_coords(lat, lng) -> bool:
	"""True when a lat/lng pair is a real fix."""
	return bool((lat or 0) or (lng or 0))


def _proximity_score(tech, job) -> int | None:
	"""Distance-decayed score from technician's last-known location to the job site.
	Returns None when coordinates are unavailable on either side."""

	t_lat, t_lng = tech.get("last_seen_latitude"), tech.get("last_seen_longitude")
	j_lat = job.get("service_latitude")
	j_lng = job.get("service_longitude")
	if not has_coords(t_lat, t_lng) or not has_coords(j_lat, j_lng):
		return None
	km = _haversine_km(t_lat, t_lng, j_lat, j_lng)
	if km <= 5:
		return _PROXIMITY_WEIGHT
	if km >= 50:
		return 0
	return round(_PROXIMITY_WEIGHT * (1 - (km - 5) / 45))


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
	from math import asin, cos, radians, sin, sqrt

	lat1, lng1, lat2, lng2 = map(radians, (lat1, lng1, lat2, lng2))
	dlat, dlng = lat2 - lat1, lng2 - lng1
	a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
	return 6371 * 2 * asin(sqrt(a))
