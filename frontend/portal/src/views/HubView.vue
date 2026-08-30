<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Spinner, StatusPill, formatDate, formatMoney, statusLabel, t } from "@digit/ui";
import { getMyPortalHub, type PortalHub } from "@/lib/api";

defineProps<{ section?: string }>();
const hub = ref<PortalHub | null>(null);
const error = ref("");

const label = (key: string) =>
	({
		sites: t("المواقع", "Sites"),
		equipment: t("المعدات", "Equipment"),
		open_jobs: t("الأعمال المفتوحة", "Open jobs"),
		upcoming_maintenance: t("الصيانة القادمة", "Upcoming"),
		overdue_maintenance: t("الصيانة المتأخرة", "Overdue"),
		active_contracts: t("العقود النشطة", "Active contracts"),
	})[key] || key;
const date = formatDate;
const money = (value?: unknown, currency = "USD") => formatMoney(Number(value || 0), currency);

onMounted(async () => {
	try {
		const result = await getMyPortalHub();
		// Keep the portal renderable during rolling API upgrades and when an older
		// cached response does not yet contain newly introduced collections.
		hub.value = {
			...result,
			dashboard: result.dashboard ?? {},
			requests: result.requests ?? [],
			jobs: result.jobs ?? [],
			service_history: result.service_history ?? [],
			upcoming_maintenance: result.upcoming_maintenance ?? [],
			overdue_maintenance: result.overdue_maintenance ?? [],
			contracts: result.contracts ?? [],
			renewals: result.renewals ?? [],
			reports: result.reports ?? [],
			certificates: result.certificates ?? [],
			quotations: result.quotations ?? [],
			invoices: result.invoices ?? [],
			visits: result.visits ?? [],
			items: result.items ?? [],
			services: result.services ?? [],
			calendar: result.calendar ?? [],
		};
	} catch {
		error.value = t(
			"تعذر تحميل لوحة الخدمة. حاول مرة أخرى.",
			"Couldn't load your service dashboard. Please try again.",
		);
	}
});
</script>

<template>
	<div class="space-y-8">
		<header>
			<p class="text-xs font-semibold uppercase tracking-[0.14em] text-brand">
				{{ t("بوابة العميل", "Customer portal") }}
			</p>
			<h1 class="mt-1 text-3xl font-bold text-cmd-fg">
				{{ t("لوحة خدمات ما بعد البيع", "After-sales dashboard") }}
			</h1>
			<p class="mt-2 text-sm text-cmd-fg-muted">
				{{
					t(
						"الصيانة وسجل الخدمة والمستندات في عرض آمن واحد.",
						"Maintenance, service history and documents in one secure view.",
					)
				}}
			</p>
		</header>
		<div v-if="!hub && !error" class="flex justify-center py-20"><Spinner :size="28" /></div>
		<p v-else-if="error" class="rounded-xl bg-danger/10 p-4 text-danger">{{ error }}</p>
		<template v-else-if="hub">
			<section class="grid grid-cols-2 gap-3 md:grid-cols-3">
				<RouterLink
					v-for="(value, key) in hub.dashboard"
					:key="key"
					:to="
						String(key).includes('maintenance')
							? '/my-schedule'
							: String(key) === 'equipment'
								? '/my-equipment'
								: String(key) === 'sites'
									? '/my-sites'
									: '/my-services'
					"
					class="kl-glass rounded-2xl p-4"
				>
					<p class="text-xs text-cmd-fg-muted">{{ label(String(key)) }}</p>
					<p class="mt-1 text-2xl font-bold tabular-nums text-cmd-fg">{{ value }}</p>
				</RouterLink>
			</section>

			<section class="grid gap-4 md:grid-cols-3">
				<RouterLink
					to="/my-schedule"
					class="rounded-2xl border border-brand/20 bg-brand/5 p-5 transition hover:shadow-glass"
					><p class="text-xs font-semibold text-brand">
						{{ t("الموعد التالي", "Next appointment") }}
					</p>
					<strong class="mt-2 block text-lg text-cmd-fg">{{
						hub.calendar?.[0]
							? statusLabel(hub.calendar[0].title)
							: t("لا يوجد موعد قريب", "No upcoming appointment")
					}}</strong>
					<p v-if="hub.calendar?.[0]" class="mt-1 text-sm text-cmd-fg-muted">
						{{ date(hub.calendar[0].start) }} ·
						{{ hub.calendar[0].site || hub.calendar[0].equipment }}
					</p></RouterLink
				>
				<RouterLink to="/my-services" class="kl-glass rounded-2xl p-5"
					><p class="text-xs font-semibold text-brand">
						{{ t("الخدمات والبنود", "Services & items") }}
					</p>
					<strong class="mt-2 block text-lg text-cmd-fg"
						>{{ hub.services.length }}
						{{ t("خدمات مرتبطة بملفك", "services in your account") }}</strong
					>
					<p class="mt-1 text-sm text-cmd-fg-muted">
						{{ t("الأعمال وقطع الغيار والتقارير", "Jobs, parts and reports") }}
					</p></RouterLink
				>
				<RouterLink to="/" class="kl-grad-brand rounded-2xl p-5 text-white"
					><p class="text-xs font-semibold opacity-80">
						{{ t("تحتاج مساعدة؟", "Need help?") }}
					</p>
					<strong class="mt-2 block text-lg">{{
						t("طلب خدمة جديدة", "Request a new service")
					}}</strong>
					<p class="mt-1 text-sm opacity-80">
						{{
							t(
								"أرسل الطلب وسنتولى الجدولة",
								"Send the request and we will schedule it",
							)
						}}
					</p></RouterLink
				>
			</section>

			<section id="maintenance" class="space-y-3">
				<h2 class="text-xl font-bold text-cmd-fg">{{ t("الصيانة", "Maintenance") }}</h2>
				<div class="grid gap-4 md:grid-cols-2">
					<div class="kl-glass rounded-2xl p-4">
						<h3 class="font-semibold text-cmd-fg">{{ t("القادمة", "Upcoming") }}</h3>
						<p
							v-if="!hub.upcoming_maintenance.length"
							class="mt-3 text-sm text-cmd-fg-muted"
						>
							{{ t("لا توجد أعمال مجدولة.", "Nothing scheduled.") }}
						</p>
						<div
							v-for="row in hub.upcoming_maintenance"
							:key="row.name"
							class="mt-3 border-t border-cmd-border pt-3 text-sm"
						>
							<p class="font-medium text-cmd-fg">
								{{
									statusLabel(
										String(row.service_type || t("صيانة", "Maintenance")),
									)
								}}
							</p>
							<p class="text-cmd-fg-muted">
								{{ date(row.due_date) }} · {{ row.installed_equipment }}
							</p>
						</div>
					</div>
					<div class="rounded-2xl border border-danger/20 bg-danger/5 p-4">
						<h3 class="font-semibold text-cmd-fg">{{ t("المتأخرة", "Overdue") }}</h3>
						<p
							v-if="!hub.overdue_maintenance.length"
							class="mt-3 text-sm text-cmd-fg-muted"
						>
							{{ t("لا توجد صيانة متأخرة.", "No overdue maintenance.") }}
						</p>
						<div
							v-for="row in hub.overdue_maintenance"
							:key="row.name"
							class="mt-3 border-t border-danger/15 pt-3 text-sm"
						>
							<p class="font-medium text-cmd-fg">
								{{
									statusLabel(
										String(row.service_type || t("صيانة", "Maintenance")),
									)
								}}
							</p>
							<p class="text-cmd-fg-muted">
								{{ t("مستحقة", "Due") }} {{ date(row.due_date) }}
							</p>
						</div>
					</div>
				</div>
			</section>

			<section id="jobs" class="space-y-3">
				<h2 class="text-xl font-bold text-cmd-fg">
					{{ t("تتبع الأعمال وسجل الخدمة", "Track jobs & service history") }}
				</h2>
				<div class="kl-glass overflow-hidden rounded-2xl">
					<RouterLink
						v-for="job in hub.jobs"
						:key="job.name"
						:to="{ name: 'track', params: { job: job.name } }"
						class="flex items-center justify-between border-b border-cmd-border p-4 last:border-0"
						><div>
							<p class="font-medium text-cmd-fg">
								{{
									job.service_type
										? statusLabel(String(job.service_type))
										: job.name
								}}
							</p>
							<p class="text-xs text-cmd-fg-muted">
								{{ date(job.completed_on || job.scheduled_date) }}
							</p>
						</div>
						<StatusPill :status="job.status" :label="statusLabel(job.status)"
					/></RouterLink>
					<p v-if="!hub.jobs.length" class="p-6 text-sm text-cmd-fg-muted">
						{{ t("لا توجد أعمال بعد.", "No jobs yet.") }}
					</p>
				</div>
			</section>

			<section id="contracts" class="space-y-3">
				<h2 class="text-xl font-bold text-cmd-fg">
					{{ t("العقود والتجديدات", "Contracts & renewals") }}
				</h2>
				<div class="grid gap-3 md:grid-cols-2">
					<div
						v-for="contract in hub.contracts"
						:key="String(contract.name)"
						class="kl-glass rounded-2xl p-4"
					>
						<div class="flex justify-between">
							<strong class="text-cmd-fg">{{ contract.name }}</strong
							><span class="text-sm text-cmd-fg-muted">{{
								statusLabel(String(contract.status))
							}}</span>
						</div>
						<p class="mt-2 text-sm text-cmd-fg-muted">
							{{ date(contract.start_date) }} — {{ date(contract.end_date) }}
						</p>
						<p v-if="contract.renewal_quotation" class="mt-2 text-sm text-brand">
							{{ t("عرض التجديد", "Renewal quotation") }}:
							{{ contract.renewal_quotation }}
						</p>
					</div>
					<p v-if="!hub.contracts.length" class="text-sm text-cmd-fg-muted">
						{{ t("لا توجد عقود خدمة.", "No service contracts.") }}
					</p>
				</div>
			</section>

			<section id="documents" class="space-y-3">
				<h2 class="text-xl font-bold text-cmd-fg">
					{{ t("التقارير والشهادات", "Reports & certificates") }}
				</h2>
				<div class="grid gap-4 md:grid-cols-2">
					<div class="kl-glass rounded-2xl p-4">
						<h3 class="font-semibold text-cmd-fg">{{ t("التقارير", "Reports") }}</h3>
						<p v-if="!hub.reports.length" class="mt-3 text-sm text-cmd-fg-muted">
							{{ t("لا توجد تقارير معتمدة.", "No submitted reports.") }}
						</p>
						<div
							v-for="row in hub.reports"
							:key="String(row.name)"
							class="mt-3 border-t border-cmd-border pt-3 text-sm"
						>
							<p class="text-cmd-fg">
								{{ statusLabel(String(row.report_type)) }} ·
								{{ t("مراجعة", "Rev") }} {{ row.revision }}
							</p>
							<p class="text-cmd-fg-muted">{{ row.name }}</p>
						</div>
					</div>
					<div class="kl-glass rounded-2xl p-4">
						<h3 class="font-semibold text-cmd-fg">
							{{ t("الشهادات", "Certificates") }}
						</h3>
						<p v-if="!hub.certificates.length" class="mt-3 text-sm text-cmd-fg-muted">
							{{ t("لا توجد شهادات صادرة.", "No issued certificates.") }}
						</p>
						<div
							v-for="row in hub.certificates"
							:key="String(row.name)"
							class="mt-3 border-t border-cmd-border pt-3 text-sm"
						>
							<p class="text-cmd-fg">
								{{ statusLabel(String(row.certificate_type)) }}
							</p>
							<p class="text-cmd-fg-muted">{{ row.name }}</p>
						</div>
					</div>
				</div>
			</section>

			<section id="billing" class="space-y-3">
				<h2 class="text-xl font-bold text-cmd-fg">
					{{ t("عروض الأسعار والفواتير", "Quotations & invoices") }}
				</h2>
				<div class="grid gap-4 md:grid-cols-2">
					<div class="kl-glass rounded-2xl p-4">
						<h3 class="font-semibold text-cmd-fg">
							{{ t("عروض الأسعار", "Quotations") }}
						</h3>
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
							{{ t("لا توجد عروض أسعار.", "No quotations.") }}
						</p>
					</div>
					<div class="kl-glass rounded-2xl p-4">
						<h3 class="font-semibold text-cmd-fg">{{ t("الفواتير", "Invoices") }}</h3>
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
								{{ statusLabel(String(row.status)) }} ·
								{{ t("المتبقي", "Outstanding") }}
								{{ money(row.outstanding_amount, String(row.currency)) }}
							</p>
						</div>
						<p v-if="!hub.invoices.length" class="mt-3 text-sm text-cmd-fg-muted">
							{{ t("لا توجد فواتير.", "No invoices.") }}
						</p>
					</div>
				</div>
			</section>
		</template>
	</div>
</template>
