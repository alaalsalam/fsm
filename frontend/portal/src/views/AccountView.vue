<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { StatusPill, Spinner, formatDate, formatMoney, statusLabel, t } from "@kodlyft/ui";
import { session } from "@/lib/session";
import { getMyJobs, getMyRequests, type MyJob, type MyRequest } from "@/lib/api";

const jobs = ref<MyJob[]>([]);
const requests = ref<MyRequest[]>([]);
const loading = ref(true);
const error = ref("");

const ACTIVE = ["Planned", "Scheduled", "Dispatched", "In Progress", "On Hold"];
const activeJobs = computed(() => jobs.value.filter((j) => ACTIVE.includes(j.status)));
const pastJobs = computed(() => jobs.value.filter((j) => !ACTIVE.includes(j.status)));

const REQUEST_TONE: Record<string, string> = {
	Open: "bg-warning/15 text-warning",
	Triaged: "bg-info/15 text-info",
	Converted: "bg-success/15 text-success",
	Cancelled: "bg-fg-muted/15 text-fg-muted",
};

const currency = (n?: number) => (n == null ? "—" : formatMoney(n));
const date = (iso?: string) => formatDate(iso, true);

async function load() {
	loading.value = true;
	error.value = "";
	try {
		[jobs.value, requests.value] = await Promise.all([getMyJobs(), getMyRequests()]);
	} catch {
		error.value = t(
			"تعذر تحميل سجلك. حاول مرة أخرى.",
			"Couldn't load your history. Please try again.",
		);
	} finally {
		loading.value = false;
	}
}

onMounted(load);
</script>

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div>
				<p class="text-xs font-semibold uppercase tracking-[0.14em] text-brand">
					{{ t("حسابي", "My account") }}
				</p>
				<h1 class="mt-1 text-2xl font-bold text-cmd-fg sm:text-3xl">
					{{ t("مرحبًا", "Hi") }} {{ session.session.full_name || t("بك", "there") }}
				</h1>
			</div>
			<RouterLink
				to="/"
				class="kl-grad-brand inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-e2 transition-[filter] hover:brightness-110"
			>
				<svg
					viewBox="0 0 24 24"
					class="size-4"
					fill="none"
					stroke="currentColor"
					stroke-width="2.1"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<path d="M12 5v14M5 12h14" />
				</svg>
				{{ t("طلب خدمة", "Request service") }}
			</RouterLink>
		</div>

		<div v-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>

		<div
			v-else-if="error"
			class="rounded-2xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger"
		>
			{{ error }}
		</div>

		<template v-else>
			<!-- Active jobs -->
			<section>
				<h2 class="mb-3 text-lg font-bold text-cmd-fg">
					{{ t("الزيارات النشطة", "Active visits") }}
				</h2>
				<div v-if="activeJobs.length" class="space-y-3">
					<RouterLink
						v-for="job in activeJobs"
						:key="job.name"
						:to="{ name: 'track', params: { job: job.name } }"
						class="kl-glass flex items-center justify-between gap-3 rounded-2xl p-4 transition duration-200 hover:-translate-y-0.5 hover:shadow-glass-lg"
					>
						<div class="min-w-0">
							<p class="truncate font-semibold text-cmd-fg">
								{{ job.service_type || t("زيارة خدمة", "Service visit") }}
							</p>
							<p class="truncate text-sm text-cmd-fg-muted">
								{{ date(job.scheduled_date) }}
							</p>
						</div>
						<StatusPill :status="job.status" :label="statusLabel(job.status)" />
					</RouterLink>
				</div>
				<p
					v-else
					class="rounded-2xl border border-dashed border-cmd-border px-4 py-8 text-center text-sm text-cmd-fg-muted"
				>
					{{
						t(
							"لا توجد زيارات نشطة. اطلب خدمة للبدء.",
							"No active visits. Book a service to get started.",
						)
					}}
				</p>
			</section>

			<!-- History -->
			<section v-if="pastJobs.length">
				<h2 class="mb-3 text-lg font-bold text-cmd-fg">
					{{ t("الزيارات السابقة", "Past visits") }}
				</h2>
				<div class="kl-glass overflow-hidden rounded-2xl">
					<table class="w-full text-start text-sm">
						<thead class="border-b border-cmd-border text-cmd-fg-muted">
							<tr>
								<th class="px-4 py-3 font-medium">{{ t("الخدمة", "Service") }}</th>
								<th class="px-4 py-3 font-medium">{{ t("التاريخ", "Date") }}</th>
								<th class="px-4 py-3 font-medium">{{ t("الحالة", "Status") }}</th>
								<th class="px-4 py-3 text-end font-medium">
									{{ t("الإجمالي", "Total") }}
								</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="job in pastJobs"
								:key="job.name"
								class="border-b border-cmd-border/60 last:border-0"
							>
								<td class="px-4 py-3 text-cmd-fg">
									{{ job.service_type || t("خدمة", "Service") }}
								</td>
								<td class="px-4 py-3 text-cmd-fg-muted">
									{{ date(job.completed_on || job.scheduled_date) }}
								</td>
								<td class="px-4 py-3">
									<StatusPill
										:status="job.status"
										:label="statusLabel(job.status)"
									/>
								</td>
								<td class="px-4 py-3 text-end font-mono tabular-nums text-cmd-fg">
									{{ currency(job.total_amount) }}
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- Service requests -->
			<section v-if="requests.length">
				<h2 class="mb-3 text-lg font-bold text-cmd-fg">{{ t("الطلبات", "Requests") }}</h2>
				<div class="space-y-2">
					<div
						v-for="request in requests"
						:key="request.name"
						class="flex items-center justify-between gap-3 rounded-xl border border-cmd-border bg-white/3 px-4 py-3"
					>
						<div class="min-w-0">
							<p class="truncate text-sm font-medium text-cmd-fg">
								{{
									request.subject ||
									request.service_type ||
									t("طلب خدمة", "Service request")
								}}
							</p>
							<p class="truncate text-xs text-cmd-fg-muted">
								{{ t("طُلب في", "Requested") }}
								{{ date(request.preferred_start || request.creation) }}
							</p>
						</div>
						<span
							class="shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium"
							:class="REQUEST_TONE[request.status] || REQUEST_TONE.Open"
						>
							{{ statusLabel(request.status) }}
						</span>
					</div>
				</div>
			</section>
		</template>
	</div>
</template>
