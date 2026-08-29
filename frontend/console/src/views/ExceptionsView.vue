<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { PageHeader, Spinner } from "@digit/ui";
import { listProcessExceptions, type ProcessException } from "@/lib/fsm";
import { t } from "@/lib/i18n";
import {
	translateExceptionReason,
	translateExceptionType,
	translateProcessAction,
} from "@/lib/translations";
const route = useRoute();
const rows = ref<ProcessException[]>([]);
const loading = ref(true);
const error = ref("");
const routeFor = (row: ProcessException) =>
	row.reference_doctype === "Service Job"
		? `/jobs/${row.reference}`
		: row.parent
			? `/jobs/${row.parent}`
			: row.reference_doctype === "Maintenance Occurrence"
				? "/maintenance"
				: "/exceptions";
const filteredRows = computed(() => {
	const type = route.query.type;
	if (type === "unassigned") return rows.value.filter((row) => row.type === "Unassigned Job");
	if (type === "reports")
		return rows.value.filter((row) => row.type === "Report Awaiting Signature");
	return rows.value;
});
const showType = (value: string) => t(translateExceptionType(value), value);
const showReason = (value: string) => t(translateExceptionReason(value), value);
const showAction = (value: string) => t(translateProcessAction(value), value);
onMounted(async () => {
	try {
		rows.value = await listProcessExceptions();
	} catch {
		error.value = t("تعذر تحميل الاستثناءات.", "Couldn't load exceptions.");
	} finally {
		loading.value = false;
	}
});
</script>
<template>
	<div>
		<PageHeader
			:eyebrow="t('لا طرق مسدودة', 'No dead ends')"
			:title="t('قائمة الاستثناءات', 'Exception queue')"
			:subtitle="
				t('سبب واضح، مالك واضح، وإجراء تالٍ', 'Clear reason, owner, and next action')
			"
		/>
		<div v-if="loading" class="flex justify-center p-12"><Spinner /></div>
		<p v-else-if="error" class="text-danger">{{ error }}</p>
		<div v-else class="grid gap-3">
			<article
				v-for="row in filteredRows"
				:key="`${row.type}-${row.reference}`"
				class="rounded-2xl border border-border bg-bg p-5 shadow-card"
			>
				<div class="flex flex-wrap items-start justify-between gap-3">
					<div>
						<p class="font-semibold">{{ showType(row.type) }} · {{ row.reference }}</p>
						<p class="mt-1 text-sm text-muted">{{ showReason(row.reason) }}</p>
					</div>
					<RouterLink
						:to="routeFor(row)"
						class="rounded-lg bg-primary px-3 py-2 text-sm text-white"
						>{{ showAction(row.action) }}</RouterLink
					>
				</div>
			</article>
			<p
				v-if="!filteredRows.length"
				class="rounded-2xl border border-border bg-bg p-8 text-center text-muted"
			>
				{{ t("لا توجد استثناءات مفتوحة.", "No open exceptions.") }}
			</p>
		</div>
	</div>
</template>
