<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { EmptyState, PageHeader, Spinner, statusLabel } from "@digit/ui";
import { getJobHub, type JobHub } from "@/lib/fsm";
import { t } from "@/lib/i18n";

type RelatedType = "inspections" | "failures" | "workshop" | "reports" | "certificates";
type RelatedRow = Record<string, unknown> & { name?: string; status?: string };

const props = defineProps<{ name: string; type: RelatedType }>();
const hub = ref<JobHub | null>(null);
const loading = ref(true);
const error = ref("");

const config = computed(() => {
	const values = {
		inspections: {
			ar: "فحوصات المعدات",
			en: "Equipment inspections",
			doctype: "equipment-inspection",
		},
		failures: { ar: "تحليل الأعطال", en: "Failure analyses", doctype: "failure-analysis" },
		workshop: { ar: "حالات الورشة", en: "Workshop cases", doctype: "service-return" },
		reports: { ar: "تقارير الخدمة", en: "Service reports", doctype: "service-report" },
		certificates: {
			ar: "شهادات الخدمة",
			en: "Service certificates",
			doctype: "service-certificate",
		},
	};
	return values[props.type] ?? values.inspections;
});

const rows = computed<RelatedRow[]>(() =>
	((hub.value?.[props.type] ?? []) as RelatedRow[]).map((row) => ({ ...row })),
);

const visibleFields = (row: RelatedRow) =>
	Object.entries(row)
		.filter(
			([key, value]) => !["name", "status"].includes(key) && value != null && value !== "",
		)
		.slice(0, 4);

const fieldLabel = (key: string) => {
	const labels: Record<string, string> = {
		installed_equipment: t("المعدة", "Equipment"),
		service_visit: t("الزيارة", "Visit"),
		overall_result: t("النتيجة", "Result"),
		completed_on: t("تاريخ الإكمال", "Completed on"),
		severity: t("الخطورة", "Severity"),
		root_cause: t("السبب الجذري", "Root cause"),
		quotation: t("عرض السعر", "Quotation"),
		sales_invoice: t("الفاتورة", "Invoice"),
		report_type: t("نوع التقرير", "Report type"),
		revision: t("الإصدار", "Revision"),
		submitted_on: t("تاريخ الاعتماد", "Submitted on"),
		certificate_type: t("نوع الشهادة", "Certificate type"),
		issued_on: t("تاريخ الإصدار", "Issued on"),
	};
	return labels[key] ?? key.replaceAll("_", " ");
};

onMounted(async () => {
	try {
		hub.value = await getJobHub(props.name);
	} catch {
		error.value = t("تعذّر تحميل السجلات المرتبطة.", "Couldn't load related records.");
	} finally {
		loading.value = false;
	}
});
</script>

<template>
	<div>
		<RouterLink
			:to="`/jobs/${name}`"
			class="mb-4 inline-flex text-sm text-primary hover:underline"
		>
			← {{ t("العودة إلى أمر الخدمة", "Back to service job") }}
		</RouterLink>
		<PageHeader
			:eyebrow="name"
			:title="t(config.ar, config.en)"
			:subtitle="t('السجلات المرتبطة بأمر الخدمة', 'Records linked to this service job')"
		/>
		<div v-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>
		<p
			v-else-if="error"
			class="rounded-xl border border-danger/30 bg-danger/10 p-4 text-danger"
		>
			{{ error }}
		</p>
		<EmptyState
			v-else-if="!rows.length"
			:title="t('لا توجد سجلات في هذه القائمة', 'No records in this list')"
			:description="
				t(
					'ستظهر السجلات هنا عند إنشائها ضمن سير العمل.',
					'Records appear here when created by the workflow.',
				)
			"
		/>
		<div v-else class="grid gap-3">
			<a
				v-for="row in rows"
				:key="row.name"
				:href="`/app/${config.doctype}/${encodeURIComponent(String(row.name || ''))}`"
				class="rounded-2xl border border-border bg-bg p-4 shadow-card transition hover:border-primary/50"
			>
				<div class="flex flex-wrap items-center justify-between gap-3">
					<p class="font-mono font-semibold">{{ row.name }}</p>
					<span v-if="row.status" class="rounded-full bg-white/5 px-2.5 py-1 text-xs">
						{{ statusLabel(row.status) }}
					</span>
				</div>
				<dl class="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
					<div v-for="[key, value] in visibleFields(row)" :key="key">
						<dt class="text-xs text-fg-muted">{{ fieldLabel(key) }}</dt>
						<dd class="mt-0.5">{{ value }}</dd>
					</div>
				</dl>
			</a>
		</div>
	</div>
</template>
