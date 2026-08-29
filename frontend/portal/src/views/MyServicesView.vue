<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Spinner, StatusPill, formatDate, statusLabel, t } from "@digit/ui";
import { getMyPortalHub, type PortalHub } from "@/lib/api";

const hub = ref<PortalHub | null>(null);
const loading = ref(true);
const error = ref("");
const itemsByJob = computed(() =>
	(hub.value?.items || []).reduce<Record<string, Array<Record<string, string | number>>>>(
		(groups, row) => {
			const parent = String(row.parent);
			(groups[parent] ||= []).push(row);
			return groups;
		},
		{},
	),
);
onMounted(async () => {
	try {
		hub.value = await getMyPortalHub();
	} catch {
		error.value = t("تعذر تحميل الخدمات.", "Couldn't load services.");
	} finally {
		loading.value = false;
	}
});
</script>
<template>
	<div class="space-y-7">
		<header class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<p class="text-xs font-semibold uppercase tracking-[0.14em] text-brand">
					{{ t("ملف الخدمة", "Service portfolio") }}
				</p>
				<h1 class="mt-1 text-3xl font-bold text-cmd-fg">
					{{ t("الخدمات والبنود", "Services & items") }}
				</h1>
				<p class="mt-2 text-sm text-cmd-fg-muted">
					{{
						t(
							"تابع الأعمال المنفذة والخدمات وقطع الغيار والتقارير المرتبطة بها.",
							"Track delivered services, parts and related reports.",
						)
					}}
				</p>
			</div>
			<RouterLink
				to="/"
				class="kl-grad-brand rounded-xl px-4 py-2.5 text-sm font-semibold text-white"
				>{{ t("طلب خدمة", "Request service") }}</RouterLink
			>
		</header>
		<div v-if="loading" class="flex justify-center py-20"><Spinner /></div>
		<p v-else-if="error" class="rounded-xl bg-danger/10 p-4 text-danger">{{ error }}</p>
		<template v-else-if="hub"
			><section>
				<h2 class="mb-3 text-lg font-bold text-cmd-fg">
					{{ t("الخدمات المتاحة في ملفك", "Services in your account") }}
				</h2>
				<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
					<div
						v-for="service in hub.services"
						:key="service"
						class="kl-glass rounded-2xl p-4"
					>
						<span
							class="mb-3 flex size-10 items-center justify-center rounded-xl bg-brand/10 text-brand"
							>✓</span
						><strong>{{ statusLabel(service) }}</strong>
						<p class="mt-1 text-xs text-cmd-fg-muted">
							{{
								t(
									"متاحة حسب عقدك وسجل معداتك",
									"Available according to your contract and equipment history",
								)
							}}
						</p>
					</div>
					<p v-if="!hub.services.length" class="text-sm text-cmd-fg-muted">
						{{
							t(
								"ستظهر الخدمات بعد تفعيل العقد أو أول طلب.",
								"Services appear after your contract or first request is active.",
							)
						}}
					</p>
				</div>
			</section>
			<section>
				<h2 class="mb-3 text-lg font-bold text-cmd-fg">
					{{ t("أعمال الخدمة", "Service jobs") }}
				</h2>
				<div class="space-y-4">
					<article
						v-for="job in hub.jobs"
						:key="job.name"
						class="kl-glass rounded-2xl p-5"
					>
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div>
								<RouterLink
									:to="`/track/${job.name}`"
									class="text-lg font-bold text-brand"
									>{{
										job.service_type ? statusLabel(job.service_type) : job.name
									}}</RouterLink
								>
								<p class="mt-1 text-xs text-cmd-fg-muted">
									{{ job.name }} ·
									{{ formatDate(job.scheduled_date || job.completed_on, true) }}
								</p>
							</div>
							<StatusPill :status="job.status" :label="statusLabel(job.status)" />
						</div>
						<div
							v-if="itemsByJob[job.name]?.length"
							class="mt-4 overflow-x-auto rounded-xl border border-cmd-border"
						>
							<table class="w-full text-sm">
								<thead>
									<tr class="border-b border-cmd-border text-cmd-fg-muted">
										<th class="p-3">
											{{ t("الخدمة / البند", "Service / item") }}
										</th>
										<th class="p-3">{{ t("النوع", "Type") }}</th>
										<th class="p-3">{{ t("الكمية", "Qty") }}</th>
										<th class="p-3">{{ t("المعدة", "Equipment") }}</th>
									</tr>
								</thead>
								<tbody>
									<tr
										v-for="item in itemsByJob[job.name]"
										:key="String(item.item_code)"
										class="border-b border-cmd-border/60"
									>
										<td class="p-3 font-medium">
											{{ item.item_name || item.item_code }}
										</td>
										<td class="p-3">
											{{ statusLabel(String(item.material_type)) }}
										</td>
										<td class="p-3">{{ item.qty }} {{ item.uom }}</td>
										<td class="p-3">{{ item.installed_equipment || "—" }}</td>
									</tr>
								</tbody>
							</table>
						</div>
						<p v-else class="mt-4 rounded-xl bg-white/5 p-3 text-sm text-cmd-fg-muted">
							{{
								t(
									"لا توجد بنود خدمة أو قطع غيار مسجلة لهذا الأمر.",
									"No service items or parts recorded for this job.",
								)
							}}
						</p>
						<div class="mt-4 flex flex-wrap gap-2">
							<RouterLink
								:to="`/track/${job.name}`"
								class="rounded-lg border border-cmd-border px-3 py-2 text-sm font-semibold"
								>{{ t("تتبع العمل", "Track job") }}</RouterLink
							><span
								v-if="job.sales_invoice"
								class="rounded-lg bg-brand/10 px-3 py-2 text-sm text-brand"
								>{{ t("فاتورة", "Invoice") }}: {{ job.sales_invoice }}</span
							>
						</div>
					</article>
					<p
						v-if="!hub.jobs.length"
						class="kl-glass rounded-2xl p-10 text-center text-cmd-fg-muted"
					>
						{{ t("لا توجد أعمال خدمة حتى الآن.", "No service jobs yet.") }}
					</p>
				</div>
			</section>
			<section class="grid gap-4 md:grid-cols-2">
				<div class="kl-glass rounded-2xl p-5">
					<h2 class="font-bold">{{ t("التقارير المعتمدة", "Submitted reports") }}</h2>
					<div
						v-for="report in hub.reports"
						:key="String(report.name)"
						class="mt-3 border-t border-cmd-border pt-3 text-sm"
					>
						<strong>{{ statusLabel(String(report.report_type)) }}</strong>
						<p class="text-cmd-fg-muted">
							{{ report.name }} · {{ formatDate(report.submitted_on) }}
						</p>
					</div>
					<p v-if="!hub.reports.length" class="mt-3 text-sm text-cmd-fg-muted">
						{{ t("لا توجد تقارير بعد.", "No reports yet.") }}
					</p>
				</div>
				<div class="kl-glass rounded-2xl p-5">
					<h2 class="font-bold">{{ t("العقود النشطة", "Active contracts") }}</h2>
					<div
						v-for="contract in hub.contracts"
						:key="String(contract.name)"
						class="mt-3 border-t border-cmd-border pt-3 text-sm"
					>
						<strong>{{ contract.name }}</strong>
						<p class="text-cmd-fg-muted">
							{{ formatDate(contract.start_date) }} —
							{{ formatDate(contract.end_date) }}
						</p>
					</div>
					<p v-if="!hub.contracts.length" class="mt-3 text-sm text-cmd-fg-muted">
						{{ t("لا توجد عقود خدمة.", "No service contracts.") }}
					</p>
				</div>
			</section></template
		>
	</div>
</template>
