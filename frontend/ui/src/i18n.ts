import { readonly, ref } from "vue";

export type AppLocale = "ar" | "en";

const STORAGE_KEY = "kl-lang";
const current = ref<AppLocale>("ar");

function apply(locale: AppLocale) {
	if (typeof document === "undefined") return;
	document.documentElement.lang = locale;
	document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";
	document.documentElement.classList.toggle("kl-rtl", locale === "ar");
}

export function initializeLocale(defaultLocale: AppLocale = "ar") {
	const saved =
		typeof localStorage === "undefined"
			? null
			: (localStorage.getItem(STORAGE_KEY) as AppLocale | null);
	current.value = saved === "ar" || saved === "en" ? saved : defaultLocale;
	apply(current.value);
}

export function setLocale(locale: AppLocale) {
	current.value = locale;
	if (typeof localStorage !== "undefined") localStorage.setItem(STORAGE_KEY, locale);
	apply(locale);
}

export function toggleLocale() {
	setLocale(current.value === "ar" ? "en" : "ar");
}

export function t(arabic: string, english: string) {
	return current.value === "ar" ? arabic : english;
}

export function formatDate(value?: unknown, withTime = false) {
	if (!value) return "—";
	return new Intl.DateTimeFormat(current.value === "ar" ? "ar-SA" : "en-GB", {
		dateStyle: "medium",
		...(withTime ? { timeStyle: "short" as const } : {}),
	}).format(new Date(String(value)));
}

export function formatNumber(value: number) {
	return new Intl.NumberFormat(current.value === "ar" ? "ar-SA" : "en-GB").format(value);
}

export function formatMoney(value: number, currency = "USD") {
	return new Intl.NumberFormat(current.value === "ar" ? "ar-SA" : "en-GB", {
		style: "currency",
		currency,
	}).format(value);
}

export function statusLabel(status?: string) {
	if (!status || current.value === "en") return status || "—";
	return (
		{
			Draft: "مسودة",
			Open: "مفتوح",
			Triaged: "تم الفرز",
			Converted: "تم التحويل",
			Planned: "مخطط",
			Scheduled: "مجدول",
			Dispatched: "تم الإرسال",
			"En Route": "في الطريق",
			"Checked In": "تم الوصول",
			"In Progress": "قيد التنفيذ",
			"Checked Out": "تم المغادرة",
			"On Hold": "معلق",
			Completed: "مكتمل",
			Cancelled: "ملغي",
			Active: "نشط",
			Expired: "منتهي",
			Pending: "معلق",
			Pass: "ناجح",
			Fail: "فاشل",
			"Customer Review": "مراجعة العميل",
			"Customer Signed": "وقع العميل",
			Planning: "التخطيط",
			Travel: "التنقل",
			Inspection: "الفحص",
			Diagnosis: "التشخيص",
			"On-Site Service": "الخدمة في الموقع",
			Workshop: "الورشة",
			Testing: "الاختبار",
			"Customer Verification": "تحقق العميل",
			Closeout: "الإغلاق",
			"Service Report": "تقرير الخدمة",
			"Inspection Report": "تقرير الفحص",
			"Preventive Maintenance Report": "تقرير الصيانة الوقائية",
			"Refill Certificate": "شهادة إعادة التعبئة",
			"Hydro Test Certificate": "شهادة الاختبار الهيدروستاتيكي",
			"Under Warranty": "تحت الضمان",
			"Out of Warranty": "خارج الضمان",
			Unknown: "غير معروف",
		}[status] || status
	);
}

export const locale = readonly(current);
