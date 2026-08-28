"""Idempotent Arabic presentation data for a field-service site.

This module deliberately creates only draft and operational records; it never
submits financial or stock documents and does not invoke external integrations.
"""

import frappe
from frappe.utils import add_days, now_datetime, today

from fsm.installed_base.commands import confirm_installation, create_customer_site, create_installed_equipment
from fsm.service_operations.commands import (
	create_job_from_request,
	create_visit,
	dispatch_visit,
	open_request,
	plan_job,
	schedule_job,
	triage_request,
)


SCENARIO_KEY = "الخدمة-الرياض"
SITE_CODE = "مركز-الأعمال-الرياض-01"


def _get_or_create(doctype, filters, values):
	name = frappe.db.exists(doctype, filters)
	if name:
		return name

	doc = frappe.get_doc({"doctype": doctype, **values})
	doc.insert()
	return doc.name


def _first(doctype, filters=None, fieldname="name"):
	return frappe.db.get_value(doctype, filters or {}, fieldname)


def _rename_if_needed(doctype, old_name, new_name):
	"""Replace legacy presentation labels while preserving all linked records."""
	if old_name != new_name and frappe.db.exists(doctype, old_name) and not frappe.db.exists(doctype, new_name):
		frappe.rename_doc(doctype, old_name, new_name, force=True)
	return new_name if frappe.db.exists(doctype, new_name) else old_name


def _migrate_legacy_labels():
	"""Update previously seeded records in place, including all dependent links."""
	for old_name, new_name in (
		("فني عرض DIGIT - الرياض", "أحمد العتيبي"),
		("فنية عرض DIGIT - جدة", "سارة القحطاني"),
		("فريق عرض DIGIT - الرياض", "فريق صيانة الرياض"),
		("فريق عرض DIGIT - جدة", "فريق الدعم الفني جدة"),
	):
		_rename_if_needed("Technician" if "فني" in old_name else "Service Team", old_name, new_name)

	for old_name, new_name in (
		("وحدة تكييف عرض - الطابق الأرضي", "وحدة تكييف مركزية - الطابق الأرضي"),
		("لوحة إنذار حريق عرض - المدخل الرئيسي", "لوحة إنذار الحريق - المدخل الرئيسي"),
		("طفاية حريق عرض - قاعة الاجتماعات", "طفاية بودرة جافة 6 كجم - قاعة الاجتماعات"),
		("إنارة طوارئ عرض - الممر الشرقي", "إنارة طوارئ - الممر الشرقي"),
		("باب حريق عرض - مخرج الطوارئ", "باب طوارئ مقاوم للحريق - المخرج الخلفي"),
	):
		equipment = frappe.db.get_value("Installed Equipment", {"equipment_name": old_name})
		if equipment:
			doc = frappe.get_doc("Installed Equipment", equipment)
			doc.equipment_name = new_name
			doc.notes = "معدات مسجلة ضمن خطة الصيانة والفحص للموقع."
			doc.flags.fsm_command = True
			doc.save()

	for old_subject, new_subject in (
		("طلب عرض: فحص إنذار الحريق في مركز DIGIT", "فحص دوري لنظام إنذار الحريق"),
		("طلب عرض عاجل: صيانة وحدة التكييف", "بلاغ عاجل: عطل في وحدة التكييف"),
	):
		request = frappe.db.get_value("Service Request", {"subject": old_subject})
		if request:
			doc = frappe.get_doc("Service Request", request)
			doc.subject = new_subject
			doc.flags.fsm_command = True
			doc.save()

	job = frappe.db.get_value("Service Job", {"request_idempotency_key": "DIGIT-DEMO-FSM-JOB-01"})
	if job:
		frappe.db.set_value("Service Job", job, "request_idempotency_key", f"{SCENARIO_KEY}-أمر-01")


def seed_presentation_data():
	"""Create a safe, linked FSM demonstration scenario and return its records.

	Run through ``bench --site <demo-site> execute fsm.demo.seed_presentation_data``.
	The method is safe to run repeatedly on a designated demo site.
	"""
	frappe.set_user("Administrator")
	_migrate_legacy_labels()

	company = _first("Company")
	if not company:
		frappe.throw("A Company is required before FSM demo data can be created.")

	customer = _first("Customer", {"disabled": 0})
	if not customer:
		customer = _get_or_create(
			"Customer",
			{"customer_name": "شركة الرواد لإدارة المرافق"},
			{
				"customer_name": "شركة الرواد لإدارة المرافق",
				"customer_type": "Company",
				"customer_group": _first("Customer Group") or "All Customer Groups",
				"territory": _first("Territory") or "All Territories",
			},
		)

	item = _first("Item", {"disabled": 0, "fsm_serviceable": 1}, "item_code")
	if not item:
		item = _get_or_create(
			"Item",
			{"item_code": "معدات-خدمات-ميدانية-01"},
			{
				"item_code": "معدات-خدمات-ميدانية-01",
				"item_name": "جهاز تحكم للخدمات الميدانية",
				"item_group": _first("Item Group") or "All Item Groups",
				"stock_uom": _first("UOM") or "Nos",
				"is_stock_item": 0,
				"fsm_serviceable": 1,
				"fsm_tracking_mode": "None",
				"fsm_create_installed_equipment": 1,
			},
		)

	_rename_if_needed("Customer Site", "DIGIT-DEMO-FSM-RUH-01", SITE_CODE)
	site = frappe.db.exists("Customer Site", {"site_code": SITE_CODE})
	if not site:
		site = create_customer_site(
			site_name="مركز الرواد للأعمال - حي العليا، الرياض",
			site_code=SITE_CODE,
			customer=customer,
			company=company,
			status="Active",
			site_type="Commercial",
			notes="موقع أعمال تجاري لخدمات الصيانة والفحص الميداني.",
		)["name"]
	else:
		site_doc = frappe.get_doc("Customer Site", site)
		site_doc.site_name = "مركز الرواد للأعمال - حي العليا، الرياض"
		site_doc.notes = "موقع أعمال تجاري لخدمات الصيانة والفحص الميداني."
		site_doc.flags.fsm_command = True
		site_doc.save()

	equipment = []
	for name in (
		"وحدة تكييف مركزية - الطابق الأرضي",
		"لوحة إنذار الحريق - المدخل الرئيسي",
		"طفاية بودرة جافة 6 كجم - قاعة الاجتماعات",
		"إنارة طوارئ - الممر الشرقي",
		"باب طوارئ مقاوم للحريق - المخرج الخلفي",
	):
		equipment_name = frappe.db.exists(
			"Installed Equipment", {"equipment_name": name, "customer_site": site}
		)
		if not equipment_name:
			equipment_name = create_installed_equipment(
				equipment_name=name,
				company=company,
				customer=customer,
				customer_site=site,
				item_code=item,
				notes="معدات مسجلة ضمن خطة الصيانة والفحص للموقع.",
			)["name"]
			confirm_installation(equipment_name, site, installation_date=add_days(today(), -180))
		equipment.append(equipment_name)

	technician = _get_or_create(
		"Technician",
		{"technician_name": "أحمد العتيبي"},
		{
			"technician_name": "أحمد العتيبي",
			"company": company,
			"status": "Available",
			"worker_type": "Employee",
			"active": 1,
			"phone": "0500000000",
		},
	)
	team = _get_or_create(
		"Service Team",
		{"team_name": "فريق صيانة الرياض"},
		{
			"team_name": "فريق صيانة الرياض",
			"company": company,
			"status": "Active",
			"team_leader": technician,
			"capacity": 6,
			"active": 1,
			"members": [{"technician": technician, "role_in_team": "Team Leader", "active": 1}],
			"notes": "فريق مسؤول عن صيانة مواقع العملاء في مدينة الرياض.",
		},
	)
	technician_two = _get_or_create(
		"Technician",
		{"technician_name": "سارة القحطاني"},
		{
			"technician_name": "سارة القحطاني",
			"company": company,
			"status": "On Job",
			"worker_type": "Employee",
			"active": 1,
			"phone": "0500000001",
		},
	)
	team_two = _get_or_create(
		"Service Team",
		{"team_name": "فريق الدعم الفني جدة"},
		{
			"team_name": "فريق الدعم الفني جدة",
			"company": company,
			"status": "Active",
			"team_leader": technician_two,
			"capacity": 4,
			"active": 1,
			"members": [{"technician": technician_two, "role_in_team": "Team Leader", "active": 1}],
			"notes": "فريق دعم فني للحالات العاجلة والزيارات المجدولة.",
		},
	)

	request = _get_or_create(
		"Service Request",
		{"subject": "فحص دوري لنظام إنذار الحريق"},
		{
			"source": "Phone",
			"priority": "High",
			"service_type": "Inspection",
			"company": company,
			"customer": customer,
			"customer_site": site,
			"installed_equipment": equipment[1],
			"subject": "فحص دوري لنظام إنذار الحريق",
			"description": "فحص وقائي للوحة الإنذار مع توثيق النتيجة وإصدار تقرير خدمة.",
		},
	)
	request_doc = frappe.get_doc("Service Request", request)
	if request_doc.status == "Draft":
		open_request(request, source="System", correlation_id=f"{SCENARIO_KEY}-طلب-فحص")
	triaged_request = _get_or_create(
		"Service Request",
		{"subject": "بلاغ عاجل: عطل في وحدة التكييف"},
		{
			"source": "WhatsApp",
			"priority": "Urgent",
			"service_type": "Corrective Maintenance",
			"company": company,
			"customer": customer,
			"customer_site": site,
			"installed_equipment": equipment[0],
			"subject": "بلاغ عاجل: عطل في وحدة التكييف",
			"description": "بلاغ عاجل يوضح تنوع مصادر الطلبات وأولوياتها في شاشة التشغيل.",
		},
	)
	if frappe.db.get_value("Service Request", triaged_request, "status") == "Draft":
		open_request(triaged_request, source="System", correlation_id=f"{SCENARIO_KEY}-طلب-عاجل")
		triage_request(triaged_request, source="System", correlation_id=f"{SCENARIO_KEY}-فرز-عاجل")
	job = frappe.db.get_value("Service Job", {"request_idempotency_key": f"{SCENARIO_KEY}-أمر-01"})
	if not job:
		job = create_job_from_request(request, idempotency_key=f"{SCENARIO_KEY}-أمر-01", source="System")["name"]
		job_doc = frappe.get_doc("Service Job", job)
		job_doc.update(
			{
				"assigned_service_team": team,
				"team_leader": technician,
				"primary_technician": technician,
				"coverage_status": "Contract Covered",
				"covered_labour": 1,
				"covered_travel": 1,
				"notes": "فحص ميداني مجدول مع فريق الصيانة والمعدات المرتبطة.",
			}
		)
		job_doc.save()
		plan_job(job, source="System", correlation_id=f"{SCENARIO_KEY}-تخطيط")
		schedule_job(
			job,
			scheduled_start=add_days(now_datetime(), 1),
			scheduled_end=add_days(now_datetime(), 2),
			source="System",
			correlation_id=f"{SCENARIO_KEY}-جدولة",
		)

	visits = frappe.get_all("Service Visit", filters={"service_job": job}, pluck="name")
	if not visits:
		visit = create_visit(
			job,
			scheduled_start=add_days(now_datetime(), 1),
			scheduled_end=add_days(now_datetime(), 2),
			primary_technician=technician,
			source="System",
			correlation_id=f"{SCENARIO_KEY}-زيارة-01",
		)["name"]
		dispatch_visit(visit, source="System", correlation_id=f"{SCENARIO_KEY}-توزيع-زيارة")
		visits = [visit]

	frappe.db.commit()
	return {
		"company": company,
		"customer": customer,
		"site": site,
		"equipment": equipment,
		"technician": technician,
		"team": team,
		"technician_two": technician_two,
		"team_two": team_two,
		"request": request,
		"triaged_request": triaged_request,
		"job": job,
		"visits": visits,
	}
