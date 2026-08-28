"""Idempotent demo data for a DIGIT Field Service presentation site.

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


DEMO_PREFIX = "DIGIT-DEMO-FSM"


def _get_or_create(doctype, filters, values):
	name = frappe.db.exists(doctype, filters)
	if name:
		return name

	doc = frappe.get_doc({"doctype": doctype, **values})
	doc.insert()
	return doc.name


def _first(doctype, filters=None, fieldname="name"):
	return frappe.db.get_value(doctype, filters or {}, fieldname)


def seed_presentation_data():
	"""Create a safe, linked FSM demonstration scenario and return its records.

	Run through ``bench --site <demo-site> execute fsm.demo.seed_presentation_data``.
	The method is safe to run repeatedly on a designated demo site.
	"""
	frappe.set_user("Administrator")

	company = _first("Company")
	if not company:
		frappe.throw("A Company is required before FSM demo data can be created.")

	customer = _first("Customer", {"disabled": 0})
	if not customer:
		customer = _get_or_create(
			"Customer",
			{"customer_name": "عميل عرض DIGIT للخدمة الميدانية"},
			{
				"customer_name": "عميل عرض DIGIT للخدمة الميدانية",
				"customer_type": "Company",
				"customer_group": _first("Customer Group") or "All Customer Groups",
				"territory": _first("Territory") or "All Territories",
			},
		)

	item = _first("Item", {"disabled": 0, "fsm_serviceable": 1}, "item_code")
	if not item:
		item = _get_or_create(
			"Item",
			{"item_code": "DIGIT-DEMO-SERVICE-EQUIPMENT"},
			{
				"item_code": "DIGIT-DEMO-SERVICE-EQUIPMENT",
				"item_name": "معدات عرض الخدمة الميدانية",
				"item_group": _first("Item Group") or "All Item Groups",
				"stock_uom": _first("UOM") or "Nos",
				"is_stock_item": 0,
				"fsm_serviceable": 1,
				"fsm_tracking_mode": "None",
				"fsm_create_installed_equipment": 1,
			},
		)

	site = frappe.db.exists("Customer Site", {"site_code": f"{DEMO_PREFIX}-RUH-01"})
	if not site:
		site = create_customer_site(
			site_name="مركز عرض DIGIT للخدمات الميدانية - الرياض",
			site_code=f"{DEMO_PREFIX}-RUH-01",
			customer=customer,
			company=company,
			status="Active",
			site_type="Commercial",
			notes="بيانات عرض مترابطة لنظام DIGIT Field Service.",
		)["name"]

	equipment = []
	for name in (
		"وحدة تكييف عرض - الطابق الأرضي",
		"لوحة إنذار حريق عرض - المدخل الرئيسي",
		"طفاية حريق عرض - قاعة الاجتماعات",
		"إنارة طوارئ عرض - الممر الشرقي",
		"باب حريق عرض - مخرج الطوارئ",
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
				notes="معدات مهيأة لعرض DIGIT Field Service.",
			)["name"]
			confirm_installation(equipment_name, site, installation_date=add_days(today(), -180))
		equipment.append(equipment_name)

	technician = _get_or_create(
		"Technician",
		{"technician_name": "فني عرض DIGIT - الرياض"},
		{
			"technician_name": "فني عرض DIGIT - الرياض",
			"company": company,
			"status": "Available",
			"worker_type": "Employee",
			"active": 1,
			"phone": "0500000000",
		},
	)
	team = _get_or_create(
		"Service Team",
		{"team_name": "فريق عرض DIGIT - الرياض"},
		{
			"team_name": "فريق عرض DIGIT - الرياض",
			"company": company,
			"status": "Active",
			"team_leader": technician,
			"capacity": 6,
			"active": 1,
			"members": [{"technician": technician, "role_in_team": "Team Leader", "active": 1}],
			"notes": "فريق عرض مخصص لسيناريو الخدمة الميدانية.",
		},
	)
	technician_two = _get_or_create(
		"Technician",
		{"technician_name": "فنية عرض DIGIT - جدة"},
		{
			"technician_name": "فنية عرض DIGIT - جدة",
			"company": company,
			"status": "On Job",
			"worker_type": "Employee",
			"active": 1,
			"phone": "0500000001",
		},
	)
	team_two = _get_or_create(
		"Service Team",
		{"team_name": "فريق عرض DIGIT - جدة"},
		{
			"team_name": "فريق عرض DIGIT - جدة",
			"company": company,
			"status": "Active",
			"team_leader": technician_two,
			"capacity": 4,
			"active": 1,
			"members": [{"technician": technician_two, "role_in_team": "Team Leader", "active": 1}],
			"notes": "فريق عرض ثانٍ لإظهار توزيع العمل بين الفرق.",
		},
	)

	request = _get_or_create(
		"Service Request",
		{"subject": "طلب عرض: فحص إنذار الحريق في مركز DIGIT"},
		{
			"source": "Phone",
			"priority": "High",
			"service_type": "Inspection",
			"company": company,
			"customer": customer,
			"customer_site": site,
			"installed_equipment": equipment[1],
			"subject": "طلب عرض: فحص إنذار الحريق في مركز DIGIT",
			"description": "فحص وقائي للوحة الإنذار مع توثيق النتيجة وإصدار تقرير خدمة.",
		},
	)
	request_doc = frappe.get_doc("Service Request", request)
	if request_doc.status == "Draft":
		open_request(request, source="System", correlation_id=f"{DEMO_PREFIX}-REQUEST-OPEN")
	triaged_request = _get_or_create(
		"Service Request",
		{"subject": "طلب عرض عاجل: صيانة وحدة التكييف"},
		{
			"source": "WhatsApp",
			"priority": "Urgent",
			"service_type": "Corrective Maintenance",
			"company": company,
			"customer": customer,
			"customer_site": site,
			"installed_equipment": equipment[0],
			"subject": "طلب عرض عاجل: صيانة وحدة التكييف",
			"description": "بلاغ عاجل يوضح تنوع مصادر الطلبات وأولوياتها في شاشة التشغيل.",
		},
	)
	if frappe.db.get_value("Service Request", triaged_request, "status") == "Draft":
		open_request(triaged_request, source="System", correlation_id=f"{DEMO_PREFIX}-REQUEST-URGENT-OPEN")
		triage_request(triaged_request, source="System", correlation_id=f"{DEMO_PREFIX}-REQUEST-URGENT-TRIAGE")
	job = frappe.db.get_value("Service Job", {"request_idempotency_key": f"{DEMO_PREFIX}-JOB-01"})
	if not job:
		job = create_job_from_request(request, idempotency_key=f"{DEMO_PREFIX}-JOB-01", source="System")["name"]
		job_doc = frappe.get_doc("Service Job", job)
		job_doc.update(
			{
				"assigned_service_team": team,
				"team_leader": technician,
				"primary_technician": technician,
				"coverage_status": "Contract Covered",
				"covered_labour": 1,
				"covered_travel": 1,
				"notes": "أمر عرض مترابط مع طلب خدمة وموقع ومعدات وفريق تنفيذ.",
			}
		)
		job_doc.save()
		plan_job(job, source="System", correlation_id=f"{DEMO_PREFIX}-JOB-PLAN")
		schedule_job(
			job,
			scheduled_start=add_days(now_datetime(), 1),
			scheduled_end=add_days(now_datetime(), 2),
			source="System",
			correlation_id=f"{DEMO_PREFIX}-JOB-SCHEDULE",
		)

	visits = frappe.get_all("Service Visit", filters={"service_job": job}, pluck="name")
	if not visits:
		visit = create_visit(
			job,
			scheduled_start=add_days(now_datetime(), 1),
			scheduled_end=add_days(now_datetime(), 2),
			primary_technician=technician,
			source="System",
			correlation_id=f"{DEMO_PREFIX}-VISIT-01",
		)["name"]
		dispatch_visit(visit, source="System", correlation_id=f"{DEMO_PREFIX}-VISIT-DISPATCH")
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
