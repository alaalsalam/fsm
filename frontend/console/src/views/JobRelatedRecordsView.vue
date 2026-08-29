<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import type { ServiceReport, ServiceReportStatus, ServiceReportType } from "@digit/api";
import { EmptyState, KlButton, PageHeader, Spinner, statusLabel } from "@digit/ui";
import { getJobHub, reportingApi, type JobHub } from "@/lib/fsm";
import { t } from "@/lib/i18n";

type RelatedType = "inspections" | "failures" | "workshop" | "reports" | "certificates";
type RelatedRow = Record<string, unknown> & { name?: string; status?: string };

const props = defineProps<{ name: string; type: RelatedType }>();
const hub = ref<JobHub | null>(null);
const loading = ref(true);
const error = ref("");
const busy = ref("");
const reports = ref<ServiceReport[]>([]);
const editing = ref("");
const workPerformed = ref("");
const recommendations = ref("");

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
	props.type === "reports"
		? reports.value.map((row) => ({ ...row }))
		: ((hub.value?.[props.type] ?? []) as RelatedRow[]).map((row) => ({ ...row })),
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

async function load() {
	loading.value = true;
	error.value = "";
	try {
		hub.value = await getJobHub(props.name);
		if (props.type === "reports") {
			reports.value = (await reportingApi.list(props.name)).reports;
		}
	} catch {
		error.value = t("تعذّر تحميل السجلات المرتبطة.", "Couldn't load related records.");
	} finally {
		loading.value = false;
	}
}

function editReport(report: ServiceReport) {
	editing.value = report.name;
	workPerformed.value = report.work_performed || "";
	recommendations.value = report.recommendations || "";
}

async function createReport() {
	busy.value = "create";
	error.value = "";
	try {
		const reportType: ServiceReportType =
			hub.value?.job.service_type === "Preventive Maintenance"
				? "Preventive Maintenance Report"
				: "Service Report";
		const report = await reportingApi.generate(props.name, reportType, crypto.randomUUID());
		await load();
		editReport(reports.value.find((row) => row.name === report.name) || report);
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t("تعذّر إنشاء تقرير الخدمة.", "Couldn't create the service report.");
	} finally {
		busy.value = "";
	}
}

async function saveReport(report: ServiceReport, prepareReview = false) {
	busy.value = report.name;
	error.value = "";
	try {
		let updated = await reportingApi.update(report.name, {
			work_performed: workPerformed.value,
			recommendations: recommendations.value,
		});
		if (prepareReview && updated.status === "Draft") {
			updated = await reportingApi.transition(updated.name, "Generated");
			updated = await reportingApi.transition(updated.name, "Customer Review");
		}
		editing.value = "";
		await load();
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t("تعذّر حفظ تقرير الخدمة.", "Couldn't save the service report.");
	} finally {
		busy.value = "";
	}
}

async function transitionReport(report: ServiceReport, status: ServiceReportStatus) {
	busy.value = report.name;
	error.value = "";
	try {
		await reportingApi.transition(report.name, status);
		await load();
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t("تعذّر تغيير حالة التقرير.", "Couldn't change the report status.");
	} finally {
		busy.value = "";
	}
}

onMounted(load);
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
		>
			<template v-if="type === 'reports'" #actions>
				<KlButton :disabled="Boolean(busy)" @click="createReport">{{
					busy === "create"
						? t("جارٍ الإنشاء…", "Creating…")
						: t("إنشاء تقرير خدمة", "Create service report")
				}}</KlButton>
			</template>
		</PageHeader>
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
		<div v-else-if="type === 'reports'" class="grid gap-4">
			<article
				v-for="report in reports"
				:key="report.name"
				class="rounded-2xl border border-border bg-bg p-5 shadow-card"
			>
				<div class="flex flex-wrap items-start justify-between gap-3">
					<div>
						<p class="font-mono text-xs text-fg-muted">
							{{ report.name }} · r{{ report.revision }}
						</p>
						<h2 class="font-bold">{{ report.report_type }}</h2>
					</div>
					<span class="rounded-full bg-info/15 px-2.5 py-1 text-xs text-info">{{
						statusLabel(report.status)
					}}</span>
				</div>
				<div v-if="editing === report.name" class="mt-4 grid gap-4">
					<label class="text-sm font-medium"
						>{{ t("الأعمال المنفذة أثناء النزول", "Work performed during the visit")
						}}<textarea
							v-model="workPerformed"
							rows="5"
							class="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2"
							:placeholder="
								t(
									'اكتب الفحوصات والإصلاحات والإجراءات المنفذة…',
									'Describe inspections, repairs and actions performed…',
								)
							"
						/>
					</label>
					<label class="text-sm font-medium"
						>{{ t("التوصيات والمتابعة", "Recommendations and follow-up")
						}}<textarea
							v-model="recommendations"
							rows="4"
							class="mt-1 w-full rounded-xl border border-border bg-bg px-3 py-2"
							:placeholder="
								t(
									'اكتب التوصيات أو القطع المطلوبة أو موعد المتابعة…',
									'Add recommendations, required parts or follow-up date…',
								)
							"
						/>
					</label>
					<div class="flex flex-wrap gap-2">
						<KlButton size="sm" :disabled="Boolean(busy)" @click="saveReport(report)">{{
							t("حفظ التقرير", "Save report")
						}}</KlButton
						><KlButton
							v-if="report.status === 'Draft'"
							size="sm"
							variant="secondary"
							:disabled="Boolean(busy)"
							@click="saveReport(report, true)"
							>{{
								t(
									"حفظ وإرساله لتوقيع العميل",
									"Save and send for customer signature",
								)
							}}</KlButton
						><button
							type="button"
							class="px-3 text-sm text-fg-muted"
							@click="editing = ''"
						>
							{{ t("إلغاء", "Cancel") }}
						</button>
					</div>
				</div>
				<div v-else class="mt-4">
					<p class="whitespace-pre-line text-sm">
						{{
							report.work_performed ||
							t(
								"لم تكتب الأعمال المنفذة بعد.",
								"Work performed has not been recorded yet.",
							)
						}}
					</p>
					<p
						v-if="report.recommendations"
						class="mt-3 whitespace-pre-line rounded-xl bg-surface p-3 text-sm"
					>
						<strong>{{ t("التوصيات", "Recommendations") }}:</strong>
						{{ report.recommendations }}
					</p>
					<div class="mt-4 flex flex-wrap gap-2">
						<KlButton
							v-if="['Draft', 'Generated', 'Customer Review'].includes(report.status)"
							size="sm"
							variant="secondary"
							:disabled="Boolean(busy)"
							@click="editReport(report)"
							>{{ t("كتابة / تعديل التقرير", "Write / edit report") }}</KlButton
						><KlButton
							v-if="report.status === 'Customer Signed'"
							size="sm"
							:disabled="Boolean(busy)"
							@click="transitionReport(report, 'Verified')"
							>{{ t("تحقق المدير", "Manager verify") }}</KlButton
						><KlButton
							v-if="report.status === 'Verified'"
							size="sm"
							:disabled="Boolean(busy)"
							@click="transitionReport(report, 'Submitted')"
							>{{ t("اعتماد التقرير", "Submit report") }}</KlButton
						><span
							v-if="report.status === 'Customer Review'"
							class="rounded-lg bg-warning/10 px-3 py-2 text-xs text-warning"
							>{{
								t(
									"بانتظار توقيع العميل من تطبيق الفني",
									"Waiting for customer signature in the technician app",
								)
							}}</span
						>
					</div>
				</div>
			</article>
		</div>
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
