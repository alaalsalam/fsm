<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import type {
	MaintenanceOccurrence,
	MaintenanceOccurrenceStatus,
	MaintenancePlanStatus,
	MaintenancePlanSummary,
	MaintenanceSummary,
} from "@digit/api";
import { EmptyState, KlButton, LinkField, PageHeader, Spinner } from "@digit/ui";
import { maintenance, searchLink } from "@/lib/fsm";
import { lang, t } from "@/lib/i18n";

type Tab = "plans" | "schedule" | "due" | "overdue" | "occurrences" | "jobs";

const plans = ref<MaintenancePlanSummary[]>([]);
const route = useRoute();
const occurrences = ref<MaintenanceOccurrence[]>([]);
const summary = ref<MaintenanceSummary | null>(null);
const tab = ref<Tab>("plans");
const loading = ref(true);
const saving = ref(false);
const savingRow = ref("");
const error = ref("");
const showCreate = ref(false);
const form = reactive({
	plan_title: "",
	customer: "",
	company: "",
	customer_site: "",
	installed_equipment: "",
	service_contract: "",
	start_date: new Date().toISOString().slice(0, 10),
	end_date: "",
	timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
	service_type: "Preventive Maintenance",
	interval_count: 1,
	interval_unit: "Months",
	lead_days: 7,
	grace_days: 0,
});

const tabs = computed(() => [
	{ key: "plans" as Tab, label: t("الخطط", "Plans"), count: plans.value.length },
	{ key: "schedule" as Tab, label: t("الجدول", "Schedule"), count: summary.value?.forecast ?? 0 },
	{ key: "due" as Tab, label: t("المستحق", "Due"), count: summary.value?.due ?? 0 },
	{ key: "overdue" as Tab, label: t("المتأخر", "Overdue"), count: summary.value?.overdue ?? 0 },
	{
		key: "occurrences" as Tab,
		label: t("الاستحقاقات", "Occurrences"),
		count: occurrences.value.length,
	},
	{
		key: "jobs" as Tab,
		label: t("الأوامر المولدة", "Generated Jobs"),
		count: summary.value?.released ?? 0,
	},
]);

const visibleOccurrences = computed(() => {
	if (tab.value === "schedule")
		return occurrences.value.filter((row) => row.status === "Forecast");
	if (tab.value === "due") return occurrences.value.filter((row) => row.status === "Due");
	if (tab.value === "overdue") return occurrences.value.filter((row) => row.status === "Overdue");
	if (tab.value === "jobs") return occurrences.value.filter((row) => row.released_job);
	return occurrences.value;
});

const statusLabel = (value: MaintenanceOccurrenceStatus | MaintenancePlanStatus) =>
	({
		Draft: t("مسودة", "Draft"),
		Active: t("نشطة", "Active"),
		Paused: t("موقوفة", "Paused"),
		Completed: t("مكتملة", "Completed"),
		Cancelled: t("ملغاة", "Cancelled"),
		Forecast: t("متوقعة", "Forecast"),
		Due: t("مستحقة", "Due"),
		Released: t("محررة", "Released"),
		Skipped: t("متجاوزة", "Skipped"),
		Overdue: t("متأخرة", "Overdue"),
	})[value];

async function load() {
	loading.value = true;
	error.value = "";
	try {
		[plans.value, occurrences.value, summary.value] = await Promise.all([
			maintenance.listPlans(),
			maintenance.listOccurrences({ limit: 2000 }),
			maintenance.summary(),
		]);
	} catch {
		error.value = t(
			"تعذّر تحميل بيانات الصيانة الوقائية.",
			"Couldn't load preventive maintenance data.",
		);
	} finally {
		loading.value = false;
	}
}

async function createPlan() {
	saving.value = true;
	error.value = "";
	try {
		await maintenance.create({
			plan_title: form.plan_title,
			customer: form.customer,
			company: form.company,
			customer_site: form.customer_site,
			service_contract: form.service_contract || undefined,
			start_date: form.start_date,
			end_date: form.end_date || undefined,
			timezone: form.timezone,
			forecast_horizon_days: 365,
			due_window_days: 7,
			catch_up_policy: "Generate Missed",
			dst_policy: "Next Valid Time",
			equipment: [{ installed_equipment: form.installed_equipment, active: 1 }],
			lines: [
				{
					line_code: "PM-01",
					service_type: form.service_type,
					interval_count: form.interval_count,
					interval_unit: form.interval_unit,
					first_due_date: form.start_date,
					scheduled_time: "09:00:00",
					equipment_scope: "All Plan Equipment",
					lead_days: form.lead_days,
					grace_days: form.grace_days,
					auto_release_job: 1,
					active: 1,
				},
			],
		});
		showCreate.value = false;
		await load();
	} catch {
		error.value = t(
			"تعذّر إنشاء خطة الصيانة. راجع الملكية والحقول.",
			"Couldn't create the plan. Check ownership and fields.",
		);
	} finally {
		saving.value = false;
	}
}

async function transition(plan: MaintenancePlanSummary, status: MaintenancePlanStatus) {
	saving.value = true;
	try {
		await maintenance.transition(plan.name, status);
		await load();
	} catch {
		error.value = t("تعذّر تغيير حالة الخطة.", "Couldn't change plan status.");
	} finally {
		saving.value = false;
	}
}

async function generate(plan: MaintenancePlanSummary) {
	saving.value = true;
	try {
		await maintenance.generate(plan.name);
		await load();
	} catch {
		error.value = t("تعذّر توليد الاستحقاقات.", "Couldn't generate occurrences.");
	} finally {
		saving.value = false;
	}
}

async function release(plan: MaintenancePlanSummary) {
	saving.value = true;
	try {
		await maintenance.release(plan.name);
		await load();
	} catch {
		error.value = t("تعذّر تحرير أوامر العمل.", "Couldn't release jobs.");
	} finally {
		saving.value = false;
	}
}

async function releaseOccurrence(row: MaintenanceOccurrence) {
	savingRow.value = row.name;
	error.value = "";
	try {
		await maintenance.release(row.maintenance_plan);
		await load();
	} catch {
		error.value = t(
			"تعذّر إنشاء أمر الخدمة من الاستحقاق.",
			"Couldn't create a service job from the occurrence.",
		);
	} finally {
		savingRow.value = "";
	}
}

const planOccurrenceCount = (plan: string) =>
	occurrences.value.filter((row) => row.maintenance_plan === plan).length;

onMounted(() => {
	const requestedTab = typeof route.query.tab === "string" ? route.query.tab : "";
	if (["plans", "schedule", "due", "overdue", "occurrences", "jobs"].includes(requestedTab))
		tab.value = requestedTab as Tab;
	load();
});
</script>

<template>
	<div>
		<PageHeader
			:eyebrow="t('التشغيل الدوري', 'Recurring Operations')"
			:title="t('الصيانة الوقائية', 'Preventive Maintenance')"
			:subtitle="
				t(`${summary?.due_today || 0} مستحق اليوم`, `${summary?.due_today || 0} due today`)
			"
		>
			<template #actions
				><KlButton @click="showCreate = !showCreate">{{
					t("خطة جديدة", "New plan")
				}}</KlButton></template
			>
		</PageHeader>

		<p
			v-if="error"
			class="mb-4 rounded-xl border border-danger/30 bg-danger/10 p-4 text-danger"
		>
			{{ error }}
		</p>

		<section
			class="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-primary/20 bg-primary/5 p-4"
		>
			<div>
				<p class="font-semibold">{{ t("تسلسل التشغيل", "Operating sequence") }}</p>
				<p class="text-sm text-fg-muted">
					{{
						t(
							"تفعيل الخطة ← توليد المواعيد ← تحرير أمر الخدمة ← إسناد الفريق ← تنفيذ الزيارة والتقرير",
							"Activate plan → generate dates → release job → assign team → execute visit and report",
						)
					}}
				</p>
			</div>
			<RouterLink
				to="/after-sales"
				class="rounded-xl border border-primary px-3 py-2 text-sm font-semibold text-primary hover:bg-primary/10"
			>
				{{ t("بدء رحلة ما بعد البيع", "Start after-sales journey") }}
			</RouterLink>
		</section>

		<form
			v-if="showCreate"
			class="mb-6 grid gap-4 rounded-2xl border border-border bg-bg p-5 shadow-card md:grid-cols-2 xl:grid-cols-3"
			@submit.prevent="createPlan"
		>
			<label class="text-sm font-medium"
				>{{ t("اسم الخطة", "Plan title")
				}}<input
					v-model="form.plan_title"
					required
					class="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2"
			/></label>
			<LinkField
				v-model="form.customer"
				:label="t('العميل', 'Customer')"
				required
				:search="(q) => searchLink('Customer', q, 'customer_name')"
			/>
			<LinkField
				v-model="form.company"
				:label="t('الشركة', 'Company')"
				required
				:search="(q) => searchLink('Company', q, 'company_name')"
			/>
			<LinkField
				v-model="form.customer_site"
				:label="t('الموقع', 'Customer Site')"
				required
				:search="(q) => searchLink('Customer Site', q, 'site_name')"
			/>
			<LinkField
				v-model="form.installed_equipment"
				:label="t('المعدة', 'Installed Equipment')"
				required
				:search="(q) => searchLink('Installed Equipment', q, 'equipment_name')"
			/>
			<LinkField
				v-model="form.service_contract"
				:label="t('العقد (اختياري)', 'Contract (optional)')"
				:search="(q) => searchLink('Service Contract', q, 'contract_no')"
			/>
			<label class="text-sm font-medium"
				>{{ t("البداية", "Starts")
				}}<input
					v-model="form.start_date"
					required
					type="date"
					class="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2"
			/></label>
			<label class="text-sm font-medium"
				>{{ t("النهاية", "Ends")
				}}<input
					v-model="form.end_date"
					type="date"
					class="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2"
			/></label>
			<label class="text-sm font-medium"
				>{{ t("المنطقة الزمنية", "Timezone")
				}}<input
					v-model="form.timezone"
					required
					class="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2"
			/></label>
			<label class="text-sm font-medium"
				>{{ t("نوع الخدمة", "Service type")
				}}<input
					v-model="form.service_type"
					required
					class="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2"
			/></label>
			<label class="text-sm font-medium"
				>{{ t("التكرار", "Interval") }}
				<div class="mt-1 flex">
					<input
						v-model.number="form.interval_count"
						min="1"
						required
						type="number"
						class="w-24 rounded-s-md border border-border bg-bg px-3 py-2"
					/><select
						v-model="form.interval_unit"
						class="min-w-0 flex-1 rounded-e-md border border-s-0 border-border bg-bg px-3 py-2"
					>
						<option value="Days">{{ t("أيام", "Days") }}</option>
						<option value="Weeks">{{ t("أسابيع", "Weeks") }}</option>
						<option value="Months">{{ t("أشهر", "Months") }}</option>
						<option value="Years">{{ t("سنوات", "Years") }}</option>
					</select>
				</div></label
			>
			<div class="flex items-end">
				<KlButton type="submit" :disabled="saving || !form.installed_equipment">{{
					saving ? t("جارٍ الحفظ…", "Saving…") : t("حفظ المسودة", "Save draft")
				}}</KlButton>
			</div>
		</form>

		<div class="mb-5 flex gap-2 overflow-x-auto pb-1">
			<button
				v-for="item in tabs"
				:key="item.key"
				type="button"
				class="whitespace-nowrap rounded-full border px-4 py-2 text-sm"
				:class="
					tab === item.key
						? 'border-primary bg-primary/15 text-primary'
						: 'border-border bg-bg'
				"
				@click="tab = item.key"
			>
				{{ item.label }} <span class="ms-1 opacity-70">{{ item.count }}</span>
			</button>
		</div>

		<div v-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>
		<template v-else-if="tab === 'plans'">
			<EmptyState
				v-if="!plans.length"
				:title="t('لا توجد خطط صيانة', 'No maintenance plans')"
				:description="
					t(
						'أنشئ خطة مرتبطة بالموقع والمعدات.',
						'Create a plan linked to a site and equipment.',
					)
				"
			/>
			<div v-else class="grid gap-4 lg:grid-cols-2">
				<article
					v-for="plan in plans"
					:key="plan.name"
					class="rounded-2xl border border-border bg-bg p-5 shadow-card"
				>
					<div class="flex items-start justify-between gap-3">
						<div>
							<p class="font-mono text-xs text-fg-muted">
								{{ plan.name }} · r{{ plan.revision }}
							</p>
							<h2 class="text-lg font-bold">{{ plan.plan_title }}</h2>
							<p class="text-sm text-fg-muted">
								{{ plan.customer }} · {{ plan.customer_site }}
							</p>
						</div>
						<span class="rounded-full bg-info/15 px-2.5 py-1 text-xs text-info">{{
							statusLabel(plan.status)
						}}</span>
					</div>
					<p class="mt-3 text-sm">
						{{ plan.start_date }}
						<template v-if="plan.end_date">— {{ plan.end_date }}</template>
					</p>
					<p class="mt-1 text-xs text-fg-muted">
						{{
							t(
								`${planOccurrenceCount(plan.name)} موعد مولد`,
								`${planOccurrenceCount(plan.name)} generated occurrence(s)`,
							)
						}}
					</p>
					<div class="mt-4 flex flex-wrap gap-2">
						<KlButton
							v-if="plan.status === 'Draft' || plan.status === 'Paused'"
							size="sm"
							:disabled="saving"
							@click="transition(plan, 'Active')"
							>{{ t("1. تفعيل الخطة", "1. Activate plan") }}</KlButton
						>
						<KlButton
							v-if="plan.status === 'Active'"
							size="sm"
							variant="secondary"
							:disabled="saving"
							@click="transition(plan, 'Paused')"
							>{{ t("إيقاف", "Pause") }}</KlButton
						>
						<KlButton
							v-if="plan.status === 'Active'"
							size="sm"
							variant="secondary"
							:disabled="saving"
							@click="generate(plan)"
							>{{ t("2. توليد الجدول", "2. Generate schedule") }}</KlButton
						>
						<KlButton
							v-if="plan.status === 'Active'"
							size="sm"
							variant="secondary"
							:disabled="saving"
							@click="release(plan)"
							>{{ t("3. إنشاء أوامر الخدمة", "3. Create service jobs") }}</KlButton
						>
					</div>
				</article>
			</div>
		</template>
		<template v-else>
			<EmptyState
				v-if="!visibleOccurrences.length"
				:title="t('لا توجد نتائج', 'No matching occurrences')"
				:description="
					t('لا توجد استحقاقات في هذا العرض.', 'There are no occurrences in this view.')
				"
			/>
			<div v-else class="overflow-x-auto rounded-2xl border border-border bg-bg shadow-card">
				<table
					class="w-full text-sm"
					:class="{ 'text-right': lang === 'ar', 'text-left': lang !== 'ar' }"
				>
					<thead class="border-b border-border text-fg-muted">
						<tr>
							<th class="px-4 py-3">{{ t("التاريخ", "Due") }}</th>
							<th class="px-4 py-3">{{ t("الخدمة", "Service") }}</th>
							<th class="px-4 py-3">{{ t("المعدة", "Equipment") }}</th>
							<th class="px-4 py-3">{{ t("الحالة", "Status") }}</th>
							<th class="px-4 py-3">{{ t("أمر العمل", "Job") }}</th>
							<th class="px-4 py-3">{{ t("الإجراء", "Action") }}</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in visibleOccurrences"
							:key="row.name"
							class="border-b border-border last:border-0"
						>
							<td class="px-4 py-3">{{ row.due_date }}</td>
							<td class="px-4 py-3">{{ row.service_type }}</td>
							<td class="px-4 py-3 font-mono">
								<RouterLink
									:to="`/equipment/${row.installed_equipment}`"
									class="text-primary hover:underline"
									>{{ row.installed_equipment }}</RouterLink
								>
							</td>
							<td class="px-4 py-3">{{ statusLabel(row.status) }}</td>
							<td class="px-4 py-3 font-mono">
								<RouterLink
									v-if="row.released_job"
									:to="`/jobs/${row.released_job}`"
									class="text-primary hover:underline"
									>{{ row.released_job }}</RouterLink
								><span v-else>—</span>
							</td>
							<td class="px-4 py-3">
								<KlButton
									v-if="
										['Due', 'Overdue'].includes(row.status) && !row.released_job
									"
									size="sm"
									variant="secondary"
									:disabled="Boolean(savingRow)"
									@click="releaseOccurrence(row)"
									>{{
										savingRow === row.name
											? t("جارٍ الإنشاء…", "Creating…")
											: t("إنشاء أمر خدمة", "Create job")
									}}</KlButton
								>
								<RouterLink
									v-else-if="row.released_job"
									:to="`/jobs/${row.released_job}`"
									class="text-sm text-primary hover:underline"
									>{{ t("فتح ومتابعة الأمر", "Open and follow job") }}</RouterLink
								>
								<span v-else class="text-fg-muted">—</span>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</template>
	</div>
</template>
