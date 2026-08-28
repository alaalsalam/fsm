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
					label: t("زيارات اليوم", "Visits today"),
					value: data.value.visits_today,
					to: "/visits",
				},
				{
					label: t("أوامر غير مسندة", "Unassigned jobs"),
					value: data.value.unassigned_jobs,
					to: "/exceptions",
				},
				{
					label: t("قيد التنفيذ", "In progress"),
					value: data.value.in_progress,
					to: "/jobs",
				},
				{ label: t("موقوفة", "On hold"), value: data.value.on_hold, to: "/jobs" },
				{
					label: t("صيانة متأخرة", "Overdue PM"),
					value: data.value.overdue_pm,
					to: "/maintenance",
				},
				{
					label: t("تقارير بانتظار التوقيع", "Reports awaiting signature"),
					value: data.value.reports_awaiting_signature,
					to: "/exceptions",
				},
				{
					label: t("عقود تنتهي خلال 30 يومًا", "Contracts expiring in 30 days"),
					value: data.value.contracts_expiring_30_days,
					to: "/contracts",
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
	</div>
</template>
