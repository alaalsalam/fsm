export interface ProcessText {
	code?: string;
	message?: string;
	action?: string;
	responsible_actor?: string;
}

const NEXT_ACTION_AR: Record<string, string> = {
	OPEN_REQUEST: "فتح طلب الخدمة",
	TRIAGE_REQUEST: "فرز الطلب وتصنيفه",
	CREATE_JOB: "التحويل إلى أمر خدمة",
	OPEN_JOB: "متابعة التنفيذ في أمر الخدمة المرتبط",
	PLAN_JOB: "تخطيط نطاق أمر الخدمة",
	SCHEDULE_JOB: "جدولة أمر الخدمة وإسناد الفريق",
	DISPATCH_JOB: "إسناد فريق الخدمة أو توزيعه",
	START_VISIT: "بدء التنقل للزيارة التالية",
	COMPLETE_JOB: "إكمال أمر الخدمة",
	ACTIVE_VISITS: "إكمال الزيارات النشطة أو إلغاؤها",
	CHECKLIST_INCOMPLETE: "إكمال قائمة التحقق الإلزامية",
	INSPECTIONS_INCOMPLETE: "إكمال فحوصات المعدات المطلوبة",
	CRITICAL_FAILURES_OPEN: "معالجة الأعطال الحرجة المفتوحة",
	WORKSHOP_OPEN: "معالجة حالات الورشة المفتوحة",
	SERVICE_REPORT_REQUIRED: "إنشاء تقرير الخدمة",
	SERVICE_REPORT_NOT_SUBMITTED: "مراجعة تقرير الخدمة واعتماده",
	SERVICE_CERTIFICATE_REQUIRED: "إصدار شهادة الخدمة المطلوبة",
	RESOLVE_HOLD: "معالجة سبب تعليق أمر الخدمة",
	DISPATCH_VISIT: "توزيع الزيارة",
	START_TRAVEL: "بدء التنقل",
	CHECK_IN: "تسجيل الوصول إلى موقع العميل",
	START_WORK: "بدء أعمال الخدمة",
	PROCESS_EQUIPMENT: "إكمال فحوصات المعدات ونتائجها",
	COMPLETE_VISIT: "إكمال زيارة الخدمة",
	VIEW_NEXT_DUE: "مراجعة موعد الصيانة القادم",
	ACTIVATE_CONTRACT: "مراجعة نطاق العقد وتفعيله",
	CREATE_MAINTENANCE_PLAN: "إنشاء خطة صيانة من العقد",
	VIEW_MAINTENANCE: "مراجعة صيانة العقد القادمة",
	RENEW_CONTRACT: "إنشاء أو فتح عرض سعر التجديد",
	RESOLVE_MATERIAL: "معالجة نقص المواد",
	TEST_REPAIR: "اختبار المعدة بعد الإصلاح",
	QUALITY_CHECK: "إكمال فحص الجودة",
	NONE: "لا يوجد إجراء إضافي مطلوب",
};

const ACTION_AR: Record<string, string> = {
	"Open Request": "فتح الطلب",
	Triage: "فرز الطلب",
	"Create Job": "إنشاء أمر خدمة",
	"Open Job": "فتح أمر الخدمة",
	"Plan Job": "تخطيط الأمر",
	Schedule: "الجدولة",
	Dispatch: "التوزيع",
	"Open Visits": "فتح الزيارات",
	"Complete Job": "إكمال أمر الخدمة",
	"Open Checklist": "فتح قائمة التحقق",
	"Open Inspections": "فتح الفحوصات",
	"Open Failures": "فتح الأعطال",
	"Open Workshop": "فتح الورشة",
	"Generate Report": "إنشاء التقرير",
	"Open Reports": "فتح التقارير",
	"Open Certificates": "فتح الشهادات",
	"Assign Team": "إسناد فريق",
	"Release Job": "تحرير أمر الخدمة",
	"Open Report": "فتح التقرير",
	Approve: "اعتماد",
	Receive: "استلام",
	Close: "إغلاق",
};

const ACTOR_AR: Record<string, string> = {
	"FSM Manager": "مدير التشغيل والصيانة",
	"Assigned Team": "فريق الخدمة المسند",
	"Assigned Technician": "الفني المسند",
	Dispatcher: "مسؤول التوزيع",
	Technician: "الفني",
	Customer: "العميل",
	System: "النظام",
};

const EXCEPTION_TYPE_AR: Record<string, string> = {
	"Unassigned Job": "أمر خدمة غير مسند",
	"Overdue Maintenance": "صيانة متأخرة",
	"Report Awaiting Signature": "تقرير بانتظار التوقيع",
};

function countFrom(message?: string): string {
	return message?.match(/\d+/)?.[0] ?? "";
}

export function translateNextAction(text?: ProcessText): string {
	if (!text) return "";
	return NEXT_ACTION_AR[text.code ?? ""] ?? text.message ?? text.action ?? text.code ?? "";
}

export function translateProcessAction(action?: string): string {
	return action ? (ACTION_AR[action] ?? action) : "";
}

export function translateActor(actor?: string): string {
	return actor ? (ACTOR_AR[actor] ?? actor) : "";
}

export function translateBlocker(text: ProcessText): string {
	const count = countFrom(text.message);
	switch (text.code) {
		case "ACTIVE_VISITS":
			return `أكمل أو ألغِ ${count || "كل"} زيارة خدمة نشطة`;
		case "CHECKLIST_INCOMPLETE":
			return `أكمل ${count || "كل"} بند إلزامي في قائمة التحقق`;
		case "INSPECTIONS_INCOMPLETE":
			return `توجد ${count || "عدة"} معدة ما زالت تحتاج فحصًا مكتملًا`;
		case "CRITICAL_FAILURES_OPEN":
			return `عالج ${count || "كل"} عطل حرج مفتوح`;
		case "WORKSHOP_OPEN":
			return `عالج ${count || "كل"} حالة ورشة مفتوحة`;
		default:
			return NEXT_ACTION_AR[text.code ?? ""] ?? text.message ?? "";
	}
}

export function translateExceptionType(type?: string): string {
	return type ? (EXCEPTION_TYPE_AR[type] ?? type) : "";
}

export function translateExceptionReason(reason?: string): string {
	if (!reason) return "";
	if (reason === "No service team is assigned") return "لم يتم إسناد فريق خدمة";
	if (reason === "Customer signature or refusal is pending")
		return "توقيع العميل أو إثبات رفضه ما زال معلقًا";
	const overdue = reason.match(/^Maintenance is overdue since (.+)$/);
	if (overdue) return `الصيانة متأخرة منذ ${overdue[1]}`;
	return reason;
}
