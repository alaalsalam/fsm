<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { PageHeader, Spinner } from "@digit/ui";
import { getOperationsHome, type OperationsHome } from "@/lib/fsm";
import { t } from "@/lib/i18n";

const data = ref<OperationsHome | null>(null);
const loading = ref(true);
const error = ref("");
const cards = computed(() =>
	data.value
		? [
				{
					label: t("أوامر الخدمة المفتوحة", "Open service jobs"),
					value: data.value.open_jobs,
					to: { path: "/jobs" },
				},
				{
					label: t("زيارات الشهر", "Visits this month"),
					value: data.value.visits_this_month,
					to: { path: "/visits", query: { date_scope: "month" } },
				},
				{
					label: t("الزيارات القادمة", "Upcoming visits"),
					value: data.value.upcoming_visits,
					to: { path: "/visits", query: { date_scope: "upcoming" } },
				},
				{
					label: t("العقود النشطة", "Active contracts"),
					value: data.value.active_contracts,
					to: { path: "/contracts" },
				},
				{
					label: t("المعدات تحت الخدمة", "Active equipment"),
					value: data.value.active_equipment,
					to: { path: "/equipment" },
				},
				{
					label: t("زيارات اليوم", "Visits today"),
					value: data.value.visits_today,
					to: { path: "/visits", query: { date_scope: "today" } },
				},
				{
					label: t("أوامر غير مسندة", "Unassigned jobs"),
					value: data.value.unassigned_jobs,
					to: { path: "/exceptions", query: { type: "unassigned" } },
				},
				{
					label: t("قيد التنفيذ", "In progress"),
					value: data.value.in_progress,
					to: { path: "/jobs", query: { status: "In Progress" } },
				},
				{
					label: t("موقوفة", "On hold"),
					value: data.value.on_hold,
					to: { path: "/jobs", query: { status: "On Hold" } },
				},
				{
					label: t("صيانة متأخرة", "Overdue PM"),
					value: data.value.overdue_pm,
					to: { path: "/maintenance", query: { tab: "overdue" } },
				},
				{
					label: t("تقارير بانتظار التوقيع", "Reports awaiting signature"),
					value: data.value.reports_awaiting_signature,
					to: { path: "/exceptions", query: { type: "reports" } },
				},
				{
					label: t("عقود تنتهي خلال 30 يومًا", "Contracts expiring in 30 days"),
					value: data.value.contracts_expiring_30_days,
					to: { path: "/contracts", query: { expiry: "30" } },
				},
			]
		: [],
);

onMounted(async () => {
	try {
		data.value = await getOperationsHome();
	} catch {
		error.value = t("تعذر تحميل مركز العمليات.", "Couldn't load the operations center.");
	} finally {
		loading.value = false;
	}
});
</script>

<template>
	<div>
		<PageHeader
			:eyebrow="t('صورة تشغيلية موحدة', 'Canonical operating view')"
			:title="t('مركز العمليات', 'Operations center')"
			:subtitle="data?.company || ''"
		/>
		<div v-if="loading" class="flex justify-center p-12"><Spinner /></div>
		<p
			v-else-if="error"
			class="rounded-xl border border-danger/30 bg-danger/10 p-4 text-danger"
		>
			{{ error }}
		</p>
		<div v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
			<RouterLink
				v-for="card in cards"
				:key="card.label"
				:to="card.to"
				class="rounded-2xl border border-border bg-bg p-5 shadow-card transition hover:-translate-y-0.5"
			>
				<p class="text-sm text-muted">{{ card.label }}</p>
				<p class="mt-2 text-3xl font-bold">{{ card.value }}</p>
			</RouterLink>
		</div>
		<section class="mt-6 rounded-2xl border border-primary/20 bg-primary/5 p-5">
			<div class="flex flex-wrap items-center justify-between gap-4">
				<div>
					<p class="text-xs font-semibold uppercase tracking-wide text-primary">
						{{ t("مسار موجه", "Guided workflow") }}
					</p>
					<h2 class="mt-1 text-lg font-bold">
						{{
							t(
								"من التسليم إلى التشغيل والصيانة",
								"From delivery to recurring maintenance",
							)
						}}
					</h2>
					<p class="mt-1 text-sm text-fg-muted">
						{{
							t(
								"إشعار تسليم ← معدات مركبة ← تأكيد التركيب ← عقد ← خطة ← جدول ← أمر خدمة ← زيارة وتقرير",
								"Delivery Note → equipment → installation → contract → plan → schedule → job → visit and report",
							)
						}}
					</p>
				</div>
				<RouterLink
					to="/after-sales"
					class="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white shadow-e2 hover:brightness-110"
					>{{ t("بدء رحلة ما بعد البيع", "Start after-sales journey") }}</RouterLink
				>
			</div>
		</section>
	</div>
</template>
