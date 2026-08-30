"""Idempotent, synthetic inventory data for a customer-facing FSM showcase."""

from __future__ import annotations

import frappe
from frappe.utils import add_days, flt, now_datetime, nowdate, nowtime

from fsm.installed_base.commands import (
	confirm_installation,
	create_customer_site,
	create_installed_equipment,
)
from fsm.service_operations.commands import (
	create_job_from_request,
	create_visit,
	dispatch_visit,
	open_request,
	plan_job,
	schedule_job,
)


ITEMS = (
	("HVAC-RTU-20TR", "وحدة تكييف سطحية 20 طن", 1, 2, 68500, 52000, 730),
	("FIRE-PUMP-75KW", "مضخة حريق كهربائية 75 كيلوواط", 1, 2, 48750, 36500, 730),
	("FACP-08-LOOP", "لوحة تحكم إنذار حريق 8 حلقات", 1, 3, 22900, 16800, 730),
	("GEN-500KVA", "مولد ديزل احتياطي 500 ك.ف.أ", 1, 1, 186000, 148000, 730),
	("AIR-FILTER-592", "فلتر هواء تكييف 592×592 مم", 0, 48, 145, 82, 0),
	("GEN-OIL-15W40", "زيت محركات ديزل 15W-40 عبوة 20 لتر", 0, 24, 410, 295, 0),
	("FIRE-PANEL-BAT-12V", "بطارية لوحة إنذار حريق 12 فولت", 0, 36, 285, 190, 0),
)

CUSTOMER = "شركة الرواد للصناعات الخفيفة"
ITEM_GROUP = "معدات وقطع غيار الصيانة"
MAIN_WAREHOUSE = "مستودع الرياض للصيانة"
VAN_WAREHOUSE = "مخزن سيارة فريق الرياض"
PURCHASE_ORDER_REFERENCE = "طلب توريد أنظمة مبنى الإدارة - أغسطس 2026"
SITE_CODE = "مصنع-الرواد-الرياض-01"
OPERATION_KEY = "رحلة-الرواد-التشغيلية-01"


def _root_item_group() -> str:
	return (
		frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ["is", "not set"]})
		or "All Item Groups"
	)


def _ensure_item_group() -> str:
	if frappe.db.exists("Item Group", ITEM_GROUP):
		return ITEM_GROUP
	return frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": ITEM_GROUP,
			"parent_item_group": _root_item_group(),
			"is_group": 0,
		}
	).insert().name


def _ensure_warehouse(warehouse_name: str, company: str) -> str:
	existing = frappe.db.get_value(
		"Warehouse", {"warehouse_name": warehouse_name, "company": company}, "name"
	)
	if existing:
		return existing
	parent = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1}, "name")
	if not parent:
		frappe.throw(f"لا يوجد مستودع رئيسي للشركة {company}")
	return frappe.get_doc(
		{
			"doctype": "Warehouse",
			"warehouse_name": warehouse_name,
			"company": company,
			"parent_warehouse": parent,
			"is_group": 0,
		}
	).insert().name


def _ensure_item(item_group: str, row: tuple) -> str:
	item_code, item_name, serviceable, _qty, _selling_rate, valuation_rate, warranty_days = row
	if frappe.db.exists("Item", item_code):
		item = frappe.get_doc("Item", item_code)
	else:
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_name,
				"description": item_name,
				"item_group": item_group,
				"stock_uom": "Nos",
				"is_stock_item": 1,
			}
		)
	item.item_name = item_name
	item.description = item_name
	item.item_group = item_group
	item.standard_rate = valuation_rate
	item.fsm_serviceable = serviceable
	item.fsm_create_installed_equipment = serviceable
	item.fsm_tracking_mode = "Unit" if serviceable else "None"
	item.fsm_default_warranty_days = warranty_days
	item.save() if not item.is_new() else item.insert()
	return item.name


def _ensure_price(item_code: str, selling_rate: float, currency: str) -> str:
	price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
	if not price_list:
		frappe.throw("لا توجد قائمة أسعار بيع مفعلة")
	filters = {"item_code": item_code, "price_list": price_list, "uom": "Nos"}
	name = frappe.db.get_value("Item Price", filters, "name")
	if name:
		doc = frappe.get_doc("Item Price", name)
		doc.price_list_rate = selling_rate
		doc.currency = currency
		doc.save()
		return doc.name
	return frappe.get_doc(
		{
			"doctype": "Item Price",
			**filters,
			"currency": currency,
			"price_list_rate": selling_rate,
		}
	).insert().name


def _ensure_stock(company: str, main_warehouse: str, van_warehouse: str) -> str | None:
	targets = []
	for item_code, _name, serviceable, qty, _selling_rate, valuation_rate, _warranty in ITEMS:
		targets.append((item_code, main_warehouse, qty, valuation_rate))
		van_qty = 0 if serviceable else max(2, int(qty * 0.25))
		targets.append((item_code, van_warehouse, van_qty, valuation_rate))

	if all(
		flt(frappe.db.get_value("Bin", {"item_code": code, "warehouse": warehouse}, "actual_qty"))
		== flt(qty)
		for code, warehouse, qty, _rate in targets
	):
		return None

	doc = frappe.get_doc(
		{
			"doctype": "Stock Reconciliation",
			"company": company,
			"purpose": "Stock Reconciliation",
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"set_posting_time": 1,
			"items": [
				{
					"item_code": code,
					"warehouse": warehouse,
					"qty": qty,
					"valuation_rate": rate,
				}
				for code, warehouse, qty, rate in targets
			],
		}
	)
	doc.insert()
	doc.submit()
	return doc.name


def _ensure_sales_order(company: str, customer: str, warehouse: str, currency: str) -> str:
	existing = frappe.db.get_value(
		"Sales Order",
		{"company": company, "customer": customer, "po_no": PURCHASE_ORDER_REFERENCE, "docstatus": 0},
		"name",
	)
	if existing:
		return existing
	price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
	items = []
	for item_code, _name, serviceable, _qty, selling_rate, _valuation_rate, _warranty in ITEMS:
		if serviceable:
			items.append(
				{
					"item_code": item_code,
					"qty": 1,
					"rate": selling_rate,
					"delivery_date": add_days(nowdate(), 14),
					"warehouse": warehouse,
				}
			)
	return frappe.get_doc(
		{
			"doctype": "Sales Order",
			"company": company,
			"customer": customer,
			"transaction_date": nowdate(),
			"delivery_date": add_days(nowdate(), 14),
			"order_type": "Sales",
			"currency": currency,
			"selling_price_list": price_list,
			"po_no": PURCHASE_ORDER_REFERENCE,
			"items": items,
		}
	).insert().name


def _ensure_installed_base(company: str, customer: str) -> tuple[str, list[str]]:
	site = frappe.db.get_value("Customer Site", {"site_code": SITE_CODE}, "name")
	if not site:
		site = create_customer_site(
			site_name="مصنع الرواد - المدينة الصناعية الثانية، الرياض",
			site_code=SITE_CODE,
			customer=customer,
			company=company,
			status="Active",
			site_type="Industrial",
			notes="موقع إنتاج صناعي تغطيه خدمات التشغيل والصيانة الوقائية.",
		)["name"]

	equipment_labels = {
		"HVAC-RTU-20TR": "وحدة تكييف السطح - مبنى الإدارة",
		"FIRE-PUMP-75KW": "مضخة الحريق الرئيسية - غرفة المضخات",
		"FACP-08-LOOP": "لوحة إنذار الحريق - غرفة التحكم",
		"GEN-500KVA": "المولد الاحتياطي - منطقة الخدمات",
	}
	equipment = []
	for item_code, equipment_name in equipment_labels.items():
		name = frappe.db.get_value(
			"Installed Equipment",
			{"customer_site": site, "item_code": item_code},
			"name",
		)
		if not name:
			name = create_installed_equipment(
				equipment_name=equipment_name,
				company=company,
				customer=customer,
				customer_site=site,
				item_code=item_code,
				notes="معدات تشغيلية مسجلة ضمن برنامج الصيانة الوقائية للمصنع.",
			)["name"]
			confirm_installation(name, site, installation_date=add_days(nowdate(), -90))
		equipment.append(name)
	return site, equipment


def _ensure_operations(company: str, customer: str, site: str, equipment: list[str]) -> dict:
	request = frappe.db.get_value(
		"Service Request", {"company": company, "subject": "فحص جاهزية أنظمة السلامة والتشغيل"}, "name"
	)
	if not request:
		request = frappe.get_doc(
			{
				"doctype": "Service Request",
				"source": "Phone",
				"priority": "High",
				"service_type": "Inspection",
				"company": company,
				"customer": customer,
				"customer_site": site,
				"installed_equipment": equipment[2],
				"subject": "فحص جاهزية أنظمة السلامة والتشغيل",
				"description": "زيارة مجدولة لفحص لوحة الإنذار ومضخة الحريق والمولد الاحتياطي.",
			}
		).insert().name
	if frappe.db.get_value("Service Request", request, "status") == "Draft":
		open_request(request, source="System", correlation_id=f"{OPERATION_KEY}-طلب")

	job = frappe.db.get_value("Service Job", {"request_idempotency_key": OPERATION_KEY}, "name")
	if not job:
		job = create_job_from_request(request, idempotency_key=OPERATION_KEY, source="System")["name"]
		job_doc = frappe.get_doc("Service Job", job)
		team = frappe.db.get_value("Service Team", {"company": company, "active": 1}, "name")
		technician = frappe.db.get_value("Technician", {"company": company, "active": 1}, "name")
		job_doc.assigned_service_team = team
		job_doc.primary_technician = technician
		job_doc.notes = "أمر عمل لعرض دورة الفحص والتوزيع والتقرير الميداني."
		job_doc.save()
		plan_job(job, source="System", correlation_id=f"{OPERATION_KEY}-تخطيط")
		schedule_job(
			job,
			scheduled_start=add_days(now_datetime(), 2),
			scheduled_end=add_days(now_datetime(), 3),
			source="System",
			correlation_id=f"{OPERATION_KEY}-جدولة",
		)

	visits = frappe.get_all("Service Visit", filters={"service_job": job}, pluck="name")
	if not visits:
		technician = frappe.db.get_value("Technician", {"company": company, "active": 1}, "name")
		visit = create_visit(
			job,
			scheduled_start=add_days(now_datetime(), 2),
			scheduled_end=add_days(now_datetime(), 3),
			primary_technician=technician,
			source="System",
			correlation_id=f"{OPERATION_KEY}-زيارة",
		)["name"]
		dispatch_visit(visit, source="System", correlation_id=f"{OPERATION_KEY}-توزيع")
		visits = [visit]
	return {"request": request, "job": job, "visits": visits}


def seed_showcase_inventory(company: str = "Digit", customer: str = CUSTOMER):
	"""Create a realistic Saudi inventory and a draft after-sales journey."""
	frappe.set_user("Administrator")
	if not frappe.db.exists("Company", company):
		frappe.throw(f"الشركة غير موجودة: {company}")
	if not frappe.db.exists("Customer", customer):
		frappe.throw(f"العميل غير موجود: {customer}")

	currency = frappe.db.get_value("Company", company, "default_currency") or "SAR"
	item_group = _ensure_item_group()
	main_warehouse = _ensure_warehouse(MAIN_WAREHOUSE, company)
	van_warehouse = _ensure_warehouse(VAN_WAREHOUSE, company)
	item_codes = []
	prices = []
	for row in ITEMS:
		item_code = _ensure_item(item_group, row)
		item_codes.append(item_code)
		prices.append(_ensure_price(item_code, row[4], currency))

	reconciliation = _ensure_stock(company, main_warehouse, van_warehouse)
	sales_order = _ensure_sales_order(company, customer, main_warehouse, currency)
	site, equipment = _ensure_installed_base(company, customer)
	operations = _ensure_operations(company, customer, site, equipment)
	frappe.db.commit()
	return {
		"company": company,
		"customer": customer,
		"item_group": item_group,
		"warehouses": [main_warehouse, van_warehouse],
		"items": item_codes,
		"item_prices": prices,
		"stock_reconciliation": reconciliation,
		"sales_order": sales_order,
		"site": site,
		"equipment": equipment,
		"operations": operations,
	}
