<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { PageHeader, Spinner, StatusPill } from "@digit/ui";
import { listProcessVisits, type ProcessVisit } from "@/lib/fsm";
import { t } from "@/lib/i18n";

const rows = ref<ProcessVisit[]>([]);
const loading = ref(true);
const error = ref("");
onMounted(async () => {
	try {
		rows.value = await listProcessVisits({ limit: 200 });
	} catch {
		error.value = t("تعذر تحميل الزيارات.", "Couldn't load visits.");
	} finally {
		loading.value = false;
	}
});
</script>

<template>
	<div>
		<PageHeader
			:eyebrow="t('التخطيط والتنفيذ', 'Planning and execution')"
			:title="t('الزيارات', 'Visits')"
			:subtitle="
				t('عرض موحد للجدول والتنفيذ الفعلي', 'One view for schedule and actual execution')
			"
		/>
		<div v-if="loading" class="flex justify-center p-12"><Spinner /></div>
		<p v-else-if="error" class="text-danger">{{ error }}</p>
		<div v-else class="overflow-x-auto rounded-2xl border border-border bg-bg shadow-card">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-border text-start text-muted">
						<th class="p-4">{{ t("الزيارة", "Visit") }}</th>
						<th class="p-4">{{ t("الأمر", "Job") }}</th>
						<th class="p-4">{{ t("العميل", "Customer") }}</th>
						<th class="p-4">{{ t("الموعد", "Schedule") }}</th>
						<th class="p-4">{{ t("الفريق / الفني", "Team / technician") }}</th>
						<th class="p-4">{{ t("الحالة", "Status") }}</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in rows" :key="row.name" class="border-b border-border/60">
						<td class="p-4 font-medium">{{ row.name }}</td>
						<td class="p-4">
							<RouterLink class="text-primary" :to="`/jobs/${row.service_job}`">{{
								row.service_job
							}}</RouterLink>
						</td>
						<td class="p-4">{{ row.customer_name || "—" }}</td>
						<td class="p-4">{{ row.scheduled_start || "—" }}</td>
						<td class="p-4">{{ row.service_team || row.primary_technician || "—" }}</td>
						<td class="p-4"><StatusPill :status="row.status" /></td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>
