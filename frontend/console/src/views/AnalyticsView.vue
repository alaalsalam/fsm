<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { PageHeader, KpiCard } from "@digit/ui";
import {
	getServicePerformance,
	getWorkorderVolume,
	getInventoryUsage,
	getTechnicianUtilization,
	getDomainDashboard,
	type ServicePerformance,
	type WorkorderVolume,
	type InventoryUsage,
	type TechUtilization,
	type DomainDashboard,
} from "@/lib/fsm";
import { t } from "@/lib/i18n";

const statusAr: Record<string, string> = {
	Draft: "مسودة",
	Planned: "مخطط",
	Scheduled: "مجدول",
	Dispatched: "موزع",
	"In Progress": "قيد التنفيذ",
	"On Hold": "معلق",
	Completed: "مكتمل",
	Cancelled: "ملغي",
};
const showStatus = (s?: string) => (s ? t(statusAr[s] ?? s, s) : "—");

const days = ref(90);
const loading = ref(true);
const error = ref("");
const perf = ref<ServicePerformance | null>(null);
const volume = ref<WorkorderVolume | null>(null);
const usage = ref<InventoryUsage | null>(null);
const util = ref<TechUtilization | null>(null);
const domains = ref<DomainDashboard | null>(null);

const fmt = (n: number | null | undefined, suffix = "") => (n == null ? "—" : `${n}${suffix}`);
const currency = (n: number) =>
	new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(n);

const statusBars = computed(() => {
	const e = Object.entries(volume.value?.by_status ?? {});
	const max = Math.max(1, ...e.map(([, c]) => c));
	return e
		.sort((a, b) => b[1] - a[1])
		.map(([status, count]) => ({ status, count, pct: Math.round((count / max) * 100) }));
});

const serviceTypeBars = computed(() => {
	const e = Object.entries(volume.value?.by_service_type ?? {});
	const max = Math.max(1, ...e.map(([, c]) => c));
	return e
		.sort((a, b) => b[1] - a[1])
		.slice(0, 8)
		.map(([type, count]) => ({ type, count, pct: Math.round((count / max) * 100) }));
});

async function load() {
	loading.value = true;
	error.value = "";
	try {
		[perf.value, volume.value, usage.value, util.value, domains.value] = await Promise.all([
			getServicePerformance(days.value),
			getWorkorderVolume(days.value),
			getInventoryUsage(days.value),
			getTechnicianUtilization(days.value),
			getDomainDashboard(days.value),
		]);
	} catch {
		error.value = t("تعذّر تحميل التحليلات.", "Couldn't load analytics.");
	} finally {
		loading.value = false;
	}
}

onMounted(load);
</script>

<template>
	<div>
		<PageHeader
			:eyebrow="t('الرؤى', 'Insights')"
			:title="t('التحليلات والتقارير', 'Analytics & reports')"
			:subtitle="t('أداء الخدمة والعمليات', 'Service performance and operations')"
		>
			<template #actions>
				<select
					v-model.number="days"
					:aria-label="t('الفترة الزمنية', 'Time window')"
					class="rounded-xl border border-border bg-bg px-3 py-2 text-sm text-fg"
					@change="load"
				>
					<option :value="30">{{ t("آخر 30 يوماً", "Last 30 days") }}</option>
					<option :value="90">{{ t("آخر 90 يوماً", "Last 90 days") }}</option>
					<option :value="365">{{ t("آخر 12 شهراً", "Last 12 months") }}</option>
				</select>
			</template>
		</PageHeader>

		<div
			v-if="error"
			class="mb-4 rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-danger"
		>
			{{ error }}
		</div>

		<div v-if="loading" class="grid grid-cols-2 gap-4 lg:grid-cols-4">
			<div
				v-for="n in 8"
				:key="n"
				class="h-24 animate-pulse rounded-2xl border border-border bg-white/5"
			/>
		</div>

		<div v-else class="space-y-6">
			<section>
				<h2 class="mb-3 text-lg font-bold">
					{{ t("الملخص التنفيذي والصيانة", "Executive & maintenance") }}
				</h2>
				<div class="grid grid-cols-2 gap-3 lg:grid-cols-6">
					<KpiCard
						:label="t('العملاء', 'Customers')"
						:value="domains?.executive.customers ?? '—'"
						tone="brand"
					/>
					<KpiCard
						:label="t('المواقع', 'Sites')"
						:value="domains?.executive.sites ?? '—'"
						tone="neutral"
					/>
					<KpiCard
						:label="t('المعدات', 'Equipment')"
						:value="domains?.executive.installed_equipment ?? '—'"
						tone="neutral"
					/>
					<KpiCard
						:label="t('العقود النشطة', 'Active contracts')"
						:value="domains?.executive.active_contracts ?? '—'"
						tone="success"
					/>
					<KpiCard
						:label="t('صيانة وقائية متأخرة', 'PM overdue')"
						:value="domains?.maintenance.overdue ?? '—'"
						tone="danger"
					/>
					<KpiCard
						:label="t('هامش الربح الإجمالي', 'Gross margin')"
						:value="currency(domains?.executive.gross_margin ?? 0)"
						tone="warning"
					/>
				</div>
			</section>
			<div class="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
				<KpiCard
					:label="t('الإصلاح من أول زيارة', 'First-time fix')"
					:value="fmt(perf?.first_time_fix_rate, '%')"
					tone="success"
				/>
				<KpiCard
					:label="t('متوسط زمن الإصلاح', 'MTTR')"
					:value="fmt(perf?.mttr_hours, ' h')"
					tone="brand"
				/>
				<KpiCard
					:label="t('متوسط مدة العمل الميداني', 'Avg on-site')"
					:value="fmt(perf?.avg_completion_hours, ' h')"
					tone="neutral"
				/>
				<KpiCard
					:label="t('الالتزام بالمواعيد', 'Punctuality')"
					:value="fmt(perf?.punctuality_pct, '%')"
					tone="warning"
				/>
				<KpiCard
					:label="t('معدل الإنجاز', 'Completion rate')"
					:value="fmt(perf?.completion_rate, '%')"
					tone="success"
				/>
				<KpiCard
					:label="t('أوامر مكتملة', 'Completed jobs')"
					:value="perf?.completed_jobs ?? '—'"
					tone="brand"
				/>
				<KpiCard
					:label="t('تجاوزات اتفاقية الخدمة', 'SLA breaches')"
					:value="perf?.sla_breaches ?? '—'"
					tone="danger"
				/>
				<KpiCard
					:label="t('إجمالي الأوامر', 'Total jobs')"
					:value="perf?.total_jobs ?? '—'"
					tone="neutral"
				/>
			</div>

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
				<section
					class="rounded-2xl border border-border bg-bg p-4 shadow-card backdrop-blur-xl"
				>
					<h2 class="mb-3 text-lg font-bold">
						{{ t("أوامر العمل حسب الحالة", "Work orders by status") }}
					</h2>
					<div v-for="b in statusBars" :key="b.status" class="mb-2">
						<div class="mb-0.5 flex justify-between text-sm">
							<span class="text-fg">{{ showStatus(b.status) }}</span>
							<span class="font-mono text-fg-muted tabular-nums">{{ b.count }}</span>
						</div>
						<div class="h-2 rounded-full bg-white/5">
							<div
								class="kl-grad-brand h-2 rounded-full"
								:style="{ width: `${b.pct}%` }"
							/>
						</div>
					</div>
					<p v-if="statusBars.length === 0" class="text-sm text-fg-muted">
						{{ t("لا توجد بيانات.", "No data.") }}
					</p>
				</section>

				<section
					class="rounded-2xl border border-border bg-bg p-4 shadow-card backdrop-blur-xl"
				>
					<h2 class="mb-3 text-lg font-bold">
						{{ t("الطلب حسب نوع الخدمة", "Demand by service type") }}
					</h2>
					<div v-for="b in serviceTypeBars" :key="b.type" class="mb-2">
						<div class="mb-0.5 flex justify-between text-sm">
							<span class="text-fg">{{ b.type }}</span>
							<span class="font-mono text-fg-muted tabular-nums">{{ b.count }}</span>
						</div>
						<div class="h-2 rounded-full bg-white/5">
							<div class="h-2 rounded-full bg-info" :style="{ width: `${b.pct}%` }" />
						</div>
					</div>
					<p v-if="serviceTypeBars.length === 0" class="text-sm text-fg-muted">
						{{ t("لا توجد بيانات.", "No data.") }}
					</p>
				</section>
			</div>
			<section class="rounded-2xl border border-border bg-bg shadow-card backdrop-blur-xl">
				<h2 class="border-b border-border px-4 py-3 text-lg font-bold">
					{{ t("استغلال الفنيين", "Technician utilisation") }}
				</h2>
				<div class="overflow-x-auto">
					<table class="w-full text-left text-sm">
						<thead class="border-b border-border text-fg-muted">
							<tr>
								<th class="px-4 py-2 font-medium">
									{{ t("الفني", "Technician") }}
								</th>
								<th class="px-4 py-2 text-right font-medium">
									{{ t("الأوامر", "Jobs") }}
								</th>
								<th class="px-4 py-2 text-right font-medium">
									{{ t("الساعات", "Hours") }}
								</th>
								<th class="px-4 py-2 text-right font-medium">
									{{ t("المتوسط لكل أمر", "Avg/job") }}
								</th>
								<th class="px-4 py-2 text-right font-medium">
									{{ t("الإنجاز", "Completion") }}
								</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="t in util?.technicians"
								:key="t.technician"
								class="border-b border-border last:border-0"
							>
								<td class="px-4 py-2 text-fg">{{ t.technician }}</td>
								<td class="px-4 py-2 text-right font-mono tabular-nums">
									{{ t.jobs }}
								</td>
								<td class="px-4 py-2 text-right font-mono tabular-nums">
									{{ t.hours }}
								</td>
								<td class="px-4 py-2 text-right font-mono tabular-nums">
									{{ t.avg_hours_per_job }}
								</td>
								<td class="px-4 py-2 text-right font-mono tabular-nums">
									{{ t.completion_rate }}%
								</td>
							</tr>
						</tbody>
					</table>
					<p v-if="!util?.technicians.length" class="px-4 py-6 text-sm text-fg-muted">
						{{ t("لا يوجد نشاط للفنيين.", "No technician activity.") }}
					</p>
				</div>
			</section>
			<section class="rounded-2xl border border-border bg-bg shadow-card backdrop-blur-xl">
				<h2 class="border-b border-border px-4 py-3 text-lg font-bold">
					{{ t("استهلاك القطع", "Parts usage") }}
				</h2>
				<div class="overflow-x-auto">
					<table class="w-full text-left text-sm">
						<thead class="border-b border-border text-fg-muted">
							<tr>
								<th class="px-4 py-2 font-medium">{{ t("الصنف", "Item") }}</th>
								<th class="px-4 py-2 text-right font-medium">
									{{ t("الكمية المستخدمة", "Qty used") }}
								</th>
								<th class="px-4 py-2 text-right font-medium">
									{{ t("القيمة", "Value") }}
								</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="it in usage?.items"
								:key="it.item_code"
								class="border-b border-border last:border-0"
							>
								<td class="px-4 py-2 text-fg">
									{{ it.item_name || it.item_code }}
								</td>
								<td class="px-4 py-2 text-right font-mono tabular-nums">
									{{ it.qty }}
								</td>
								<td class="px-4 py-2 text-right font-mono tabular-nums">
									{{ currency(it.amount) }}
								</td>
							</tr>
						</tbody>
					</table>
					<p v-if="!usage?.items.length" class="px-4 py-6 text-sm text-fg-muted">
						{{
							t(
								"لم تُستهلك قطع خلال هذه الفترة.",
								"No parts consumed in this window.",
							)
						}}
					</p>
				</div>
			</section>
		</div>
	</div>
</template>
