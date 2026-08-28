"""Idempotent demo data for a DIGIT Field Service presentation site.

This module deliberately creates only draft and operational records; it never
submits financial or stock documents and does not invoke external integrations.
"""

import frappe
from frappe.utils import add_days, now_datetime, today

from fsm.installed_base.commands import confirm_installation, create_customer_site, create_installed_equipment


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

	request = _get_or_create(
		"Service Request",
		{"subject": "طلب عرض: فحص إنذار الحريق في مركز DIGIT"},
		{
			"source": "Phone",
			"status": "Open",
			"priority": "High",
			"service_type": "Inspection",
			"company": company,
			"customer": customer,
			"customer_site": site,
			"installed_equipment": equipment[1],
			"subject": "طلب عرض: فحص إنذار الحريق في مركز DIGIT",
			"description": "فحص وقائي للوحة الإنذار مع توثيق النتيجة وإصدار تقرير خدمة.",
			"opened_on": now_datetime(),
		},
	)
	job = _get_or_create(
		"Service Job",
		{"request_idempotency_key": f"{DEMO_PREFIX}-JOB-01"},
		{
			"request_idempotency_key": f"{DEMO_PREFIX}-JOB-01",
			"service_request": request,
			"customer": customer,
			"company": company,
			"status": "Scheduled",
			"phase": "Planning",
			"priority": "High",
			"service_type": "Inspection",
			"scheduled_date": add_days(now_datetime(), 1),
			"scheduled_end": add_days(now_datetime(), 1),
			"assigned_service_team": team,
			"team_leader": technician,
			"primary_technician": technician,
			"coverage_status": "Contract Covered",
			"covered_labour": 1,
			"covered_travel": 1,
			"notes": "أمر عرض مترابط مع طلب خدمة وموقع ومعدات وفريق تنفيذ.",
			"equipment": [
				{"installed_equipment": equipment[1], "customer_site": site, "item_code": item},
				{"installed_equipment": equipment[2], "customer_site": site, "item_code": item},
			],
		},
	)

	visits = []
	for visit_number, status, offset, note in (
		(1, "Completed", -2, "زيارة تشخيص مكتملة مع ملاحظة تحتاج متابعة."),
		(2, "Dispatched", 1, "زيارة مجدولة للفريق مع المعدات المرتبطة."),
	):
		visits.append(
			_get_or_create(
				"Service Visit",
				{"service_job": job, "visit_number": visit_number},
				{
					"service_job": job,
					"visit_number": visit_number,
					"status": status,
					"scheduled_start": add_days(now_datetime(), offset),
					"scheduled_end": add_days(now_datetime(), offset),
					"service_team": team,
					"primary_technician": technician,
					"visit_notes": note,
				},
			)
		)

	frappe.db.commit()
	return {
		"company": company,
		"customer": customer,
		"site": site,
		"equipment": equipment,
		"technician": technician,
		"team": team,
		"request": request,
		"job": job,
		"visits": visits,
	}
