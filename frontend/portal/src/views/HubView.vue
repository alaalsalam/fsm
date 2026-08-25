<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Spinner, StatusPill } from "@kodlyft/ui";
import { getMyPortalHub, type PortalHub } from "@/lib/api";

defineProps<{ section?: string }>();
const hub = ref<PortalHub | null>(null);
const error = ref("");

const labels: Record<string, string> = {
	sites: "Sites",
	equipment: "Equipment",
	open_jobs: "Open jobs",
	upcoming_maintenance: "Upcoming",
	overdue_maintenance: "Overdue",
	active_contracts: "Active contracts",
};
const date = (value?: unknown) => (value ? new Date(String(value)).toLocaleDateString() : "—");
const money = (value?: unknown, currency = "USD") =>
	new Intl.NumberFormat(undefined, { style: "currency", currency }).format(Number(value || 0));

onMounted(async () => {
	try {
		hub.value = await getMyPortalHub();
	} catch {
		error.value = "Couldn't load your service dashboard. Please try again.";
	}
});
</script>

<template>
	<div class="space-y-8">
		<header>
			<p class="text-xs font-semibold uppercase tracking-[0.14em] text-brand">
				Customer portal
			</p>
			<h1 class="mt-1 text-3xl font-bold text-cmd-fg">After-sales dashboard</h1>
			<p class="mt-2 text-sm text-cmd-fg-muted">
				Maintenance, service history and documents in one secure view.
			</p>
		</header>
		<div v-if="!hub && !error" class="flex justify-center py-20"><Spinner :size="28" /></div>
		<p v-else-if="error" class="rounded-xl bg-danger/10 p-4 text-danger">{{ error }}</p>
		<template v-else-if="hub">
			<section class="grid grid-cols-2 gap-3 md:grid-cols-3">
				<div
					v-for="(value, key) in hub.dashboard"
					:key="key"
					class="kl-glass rounded-2xl p-4"
				>
					<p class="text-xs text-cmd-fg-muted">{{ labels[key] || key }}</p>
					<p class="mt-1 text-2xl font-bold tabular-nums text-cmd-fg">{{ value }}</p>
				</div>
			</section>

			<section id="maintenance" class="space-y-3">
				<h2 class="text-xl font-bold text-cmd-fg">Maintenance</h2>
				<div class="grid gap-4 md:grid-cols-2">
					<div class="kl-glass rounded-2xl p-4">
						<h3 class="font-semibold text-cmd-fg">Upcoming</h3>
						<p
							v-if="!hub.upcoming_maintenance.length"
							class="mt-3 text-sm text-cmd-fg-muted"
						>
							Nothing scheduled.
						</p>
						<div
							v-for="row in hub.upcoming_maintenance"
							:key="row.name"
							class="mt-3 border-t border-cmd-border pt-3 text-sm"
						>
							<p class="font-medium text-cmd-fg">
								{{ row.service_type || "Maintenance" }}
							</p>
							<p class="text-cmd-fg-muted">
								{{ date(row.due_date) }} · {{ row.installed_equipment }}
							</p>
						</div>
					</div>
					<div class="rounded-2xl border border-danger/20 bg-danger/5 p-4">
						<h3 class="font-semibold text-cmd-fg">Overdue</h3>
						<p
							v-if="!hub.overdue_maintenance.length"
							class="mt-3 text-sm text-cmd-fg-muted"
						>
							No overdue maintenance.
						</p>
						<div
							v-for="row in hub.overdue_maintenance"
							:key="row.name"
							class="mt-3 border-t border-danger/15 pt-3 text-sm"
						>
							<p class="font-medium text-cmd-fg">
								{{ row.service_type || "Maintenance" }}
							</p>
							<p class="text-cmd-fg-muted">Due {{ date(row.due_date) }}</p>
						</div>
					</div>
				</div>
			</section>

			<section id="jobs" class="space-y-3">
				<h2 class="text-xl font-bold text-cmd-fg">Track jobs & service history</h2>
				<div class="kl-glass overflow-hidden rounded-2xl">
					<RouterLink
						v-for="job in hub.jobs"
						:key="job.name"
						:to="{ name: 'track', params: { job: job.name } }"
						class="flex items-center justify-between border-b border-cmd-border p-4 last:border-0"
						><div>
							<p class="font-medium text-cmd-fg">
								{{ job.service_type || job.name }}
							</p>
							<p class="text-xs text-cmd-fg-muted">
								{{ date(job.completed_on || job.scheduled_date) }}
							</p>
						</div>
						<StatusPill :status="job.status"
					/></RouterLink>
					<p v-if="!hub.jobs.length" class="p-6 text-sm text-cmd-fg-muted">
						No jobs yet.
					</p>
				</div>
			</section>

			<section id="contracts" class="space-y-3">
				<h2 class="text-xl font-bold text-cmd-fg">Contracts & renewals</h2>
				<div class="grid gap-3 md:grid-cols-2">
					<div
						v-for="contract in hub.contracts"
						:key="String(contract.name)"
						class="kl-glass rounded-2xl p-4"
					>
						<div class="flex justify-between">
							<strong class="text-cmd-fg">{{ contract.name }}</strong
							><span class="text-sm text-cmd-fg-muted">{{ contract.status }}</span>
						</div>
						<p class="mt-2 text-sm text-cmd-fg-muted">
							{{ date(contract.start_date) }} — {{ date(contract.end_date) }}
						</p>
						<p v-if="contract.renewal_quotation" class="mt-2 text-sm text-brand">
							Renewal quotation: {{ contract.renewal_quotation }}
						</p>
					</div>
					<p v-if="!hub.contracts.length" class="text-sm text-cmd-fg-muted">
						No service contracts.
					</p>
				</div>
			</section>

			<section id="documents" class="space-y-3">
				<h2 class="text-xl font-bold text-cmd-fg">Reports & certificates</h2>
				<div class="grid gap-4 md:grid-cols-2">
					<div class="kl-glass rounded-2xl p-4">
						<h3 class="font-semibold text-cmd-fg">Reports</h3>
						<p v-if="!hub.reports.length" class="mt-3 text-sm text-cmd-fg-muted">
							No submitted reports.
						</p>
						<div
							v-for="row in hub.reports"
							:key="String(row.name)"
							class="mt-3 border-t border-cmd-border pt-3 text-sm"
						>
							<p class="text-cmd-fg">
								{{ row.report_type }} · Rev {{ row.revision }}
							</p>
							<p class="text-cmd-fg-muted">{{ row.name }}</p>
						</div>
					</div>
					<div class="kl-glass rounded-2xl p-4">
						<h3 class="font-semibold text-cmd-fg">Certificates</h3>
						<p v-if="!hub.certificates.length" class="mt-3 text-sm text-cmd-fg-muted">
							No issued certificates.
						</p>
						<div
							v-for="row in hub.certificates"
							:key="String(row.name)"
							class="mt-3 border-t border-cmd-border pt-3 text-sm"
						>
							<p class="text-cmd-fg">{{ row.certificate_type }}</p>
							<p class="text-cmd-fg-muted">{{ row.name }}</p>
						</div>
					</div>
				</div>
			</section>

			<section id="billing" class="space-y-3">
				<h2 class="text-xl font-bold text-cmd-fg">Quotations & invoices</h2>
				<div class="grid gap-4 md:grid-cols-2">
					<div class="kl-glass rounded-2xl p-4">
						<h3 class="font-semibold text-cmd-fg">Quotations</h3>
						<div
							v-for="row in hub.quotations"
							:key="String(row.name)"
							class="mt-3 flex justify-between border-t border-cmd-border pt-3 text-sm"
						>
							<span class="text-cmd-fg">{{ row.name }}</span
							><span class="text-cmd-fg-muted">{{
								money(row.grand_total, String(row.currency))
							}}</span>
						</div>
						<p v-if="!hub.quotations.length" class="mt-3 text-sm text-cmd-fg-muted">
							No quotations.
						</p>
					</div>
					<div class="kl-glass rounded-2xl p-4">
						<h3 class="font-semibold text-cmd-fg">Invoices</h3>
						<div
							v-for="row in hub.invoices"
							:key="String(row.name)"
							class="mt-3 border-t border-cmd-border pt-3 text-sm"
						>
							<div class="flex justify-between">
								<span class="text-cmd-fg">{{ row.name }}</span
								><span class="text-cmd-fg-muted">{{
									money(row.grand_total, String(row.currency))
								}}</span>
							</div>
							<p class="text-xs text-cmd-fg-muted">
								{{ row.status }} · Outstanding
								{{ money(row.outstanding_amount, String(row.currency)) }}
							</p>
						</div>
						<p v-if="!hub.invoices.length" class="mt-3 text-sm text-cmd-fg-muted">
							No invoices.
						</p>
					</div>
				</div>
			</section>
		</template>
	</div>
</template>
