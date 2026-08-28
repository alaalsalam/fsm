<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import type { ContractDetail, ContractStatus, ContractSummary } from "@digit/api";
import { EmptyState, KlButton, LinkField, PageHeader, Spinner } from "@digit/ui";
import { contracts, searchLink } from "@/lib/fsm";
import { lang, t } from "@/lib/i18n";

const rows = ref<ContractSummary[]>([]);
const selected = ref<ContractDetail | null>(null);
const status = ref("");
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const showCreate = ref(false);
const form = reactive({
	customer: "",
	company: "",
	start_date: new Date().toISOString().slice(0, 10),
	end_date: "",
	service_type: "Preventive Maintenance",
	included_visits: 1,
	emergency_visits: 0,
	response_sla_hours: 4,
	resolution_sla_hours: 24,
	notes: "",
});

const filtered = computed(() =>
	status.value ? rows.value.filter((row) => row.status === status.value) : rows.value,
);

const statusLabel = (value: ContractStatus) =>
	({
		Draft: t("مسودة", "Draft"),
		Active: t("نشط", "Active"),
		Suspended: t("موقوف", "Suspended"),
		Expired: t("منتهي", "Expired"),
		Cancelled: t("ملغى", "Cancelled"),
	})[value];

const statusClass = (value: ContractStatus) =>
	value === "Active"
		? "bg-success/15 text-success"
		: value === "Draft"
			? "bg-info/15 text-info"
			: value === "Suspended"
				? "bg-warning/15 text-warning"
				: "bg-danger/15 text-danger";

async function load() {
	loading.value = true;
	error.value = "";
	try {
		rows.value = await contracts.list();
	} catch {
		error.value = t("تعذّر تحميل عقود الخدمة.", "Couldn't load service contracts.");
	} finally {
		loading.value = false;
	}
}

async function open(row: ContractSummary) {
	try {
		selected.value = await contracts.get(row.name);
	} catch {
		error.value = t("تعذّر تحميل تفاصيل العقد.", "Couldn't load contract details.");
	}
}

async function create() {
	saving.value = true;
	error.value = "";
	try {
		const contract = await contracts.create({
			customer: form.customer,
			company: form.company,
			start_date: form.start_date,
			end_date: form.end_date,
			included_visits: form.included_visits,
			emergency_visits: form.emergency_visits,
			response_sla_hours: form.response_sla_hours,
			resolution_sla_hours: form.resolution_sla_hours,
			coverage_rules: [
				{
					rule_name: "Standard Coverage",
					service_type: form.service_type,
					classification: "Contract Covered",
					labour: 1,
					parts: 0,
					travel: 1,
					consumables: 0,
					refill: 0,
					inspection: 1,
					workshop: 0,
					active: 1,
				},
			],
			entitlements: form.included_visits
				? [
						{
							entitlement_type: "Visit",
							service_type: form.service_type,
							included_quantity: form.included_visits,
							active: 1,
						},
					]
				: [],
			notes: form.notes,
		});
		showCreate.value = false;
		selected.value = contract;
		await load();
	} catch {
		error.value = t(
			"تعذّر إنشاء العقد. راجع الحقول والنطاق.",
			"Couldn't create the contract. Check its fields and scope.",
		);
	} finally {
		saving.value = false;
	}
}

async function transition(next: ContractStatus) {
	if (!selected.value) return;
	saving.value = true;
	try {
		selected.value = await contracts.transition(selected.value.name, next);
		await load();
	} catch {
		error.value = t("تعذّر تغيير حالة العقد.", "Couldn't change contract status.");
	} finally {
		saving.value = false;
	}
}

onMounted(load);
</script>

<template>
	<div>
		<PageHeader
			:eyebrow="t('الخدمة التجارية', 'Commercial Service')"
			:title="t('عقود الخدمة والصيانة', 'Service Contracts & AMC')"
			:subtitle="t(`${filtered.length} عقد`, `${filtered.length} contracts`)"
		>
			<template #actions>
				<KlButton @click="showCreate = !showCreate">{{
					t("عقد جديد", "New contract")
				}}</KlButton>
			</template>
		</PageHeader>

		<p
			v-if="error"
			class="mb-4 rounded-xl border border-danger/30 bg-danger/10 p-4 text-danger"
		>
			{{ error }}
		</p>

		<form
			v-if="showCreate"
			class="mb-6 grid gap-4 rounded-2xl border border-border bg-bg p-5 shadow-card md:grid-cols-2"
			@submit.prevent="create"
		>
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
			<label class="text-sm font-medium"
				>{{ t("بداية العقد", "Start date")
				}}<input
					v-model="form.start_date"
					required
					type="date"
					class="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2"
			/></label>
			<label class="text-sm font-medium"
				>{{ t("نهاية العقد", "End date")
				}}<input
					v-model="form.end_date"
					required
					type="date"
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
				>{{ t("الزيارات المشمولة", "Included visits")
				}}<input
					v-model.number="form.included_visits"
					min="0"
					type="number"
					class="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2"
			/></label>
			<label class="text-sm font-medium"
				>{{ t("SLA الاستجابة بالساعات", "Response SLA hours")
				}}<input
					v-model.number="form.response_sla_hours"
					min="0"
					type="number"
					class="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2"
			/></label>
			<label class="text-sm font-medium"
				>{{ t("SLA الحل بالساعات", "Resolution SLA hours")
				}}<input
					v-model.number="form.resolution_sla_hours"
					min="0"
					type="number"
					class="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2"
			/></label>
			<label class="text-sm font-medium md:col-span-2"
				>{{ t("ملاحظات", "Notes")
				}}<textarea
					v-model="form.notes"
					class="mt-1 w-full rounded-md border border-border bg-bg px-3 py-2"
				/>
			</label>
			<div class="md:col-span-2">
				<KlButton type="submit" :disabled="saving || !form.customer || !form.company">{{
					saving ? t("جارٍ الحفظ…", "Saving…") : t("حفظ المسودة", "Save draft")
				}}</KlButton>
			</div>
		</form>

		<div class="mb-4 flex gap-3">
			<select
				v-model="status"
				:aria-label="t('حالة العقد', 'Contract status')"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			>
				<option value="">{{ t("كل الحالات", "All statuses") }}</option>
				<option
					v-for="value in ['Draft', 'Active', 'Suspended', 'Expired', 'Cancelled']"
					:key="value"
					:value="value"
				>
					{{ statusLabel(value as ContractStatus) }}
				</option>
			</select>
		</div>

		<div v-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>
		<EmptyState
			v-else-if="!filtered.length"
			:title="t('لا توجد عقود خدمة', 'No service contracts')"
			:description="
				t(
					'أنشئ أول عقد وحدد التغطية والاستحقاقات ثم فعّله.',
					'Create a contract, define coverage and entitlements, then activate it.',
				)
			"
		/>
		<div v-else class="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
			<div class="overflow-hidden rounded-2xl border border-border bg-bg shadow-card">
				<table
					class="w-full text-sm"
					:class="{ 'text-right': lang === 'ar', 'text-left': lang !== 'ar' }"
				>
					<thead class="border-b border-border text-fg-muted">
						<tr>
							<th class="px-4 py-3">{{ t("العقد", "Contract") }}</th>
							<th class="px-4 py-3">{{ t("العميل", "Customer") }}</th>
							<th class="px-4 py-3">{{ t("النهاية", "Ends") }}</th>
							<th class="px-4 py-3">{{ t("الحالة", "Status") }}</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in filtered"
							:key="row.name"
							class="cursor-pointer border-b border-border last:border-0 hover:bg-white/5"
							@click="open(row)"
						>
							<td class="px-4 py-3 font-mono font-semibold">{{ row.contract_no }}</td>
							<td class="px-4 py-3">{{ row.customer }}</td>
							<td class="px-4 py-3">{{ row.end_date }}</td>
							<td class="px-4 py-3">
								<span
									class="rounded-full px-2.5 py-1 text-xs"
									:class="statusClass(row.status)"
									>{{ statusLabel(row.status) }}</span
								>
							</td>
						</tr>
					</tbody>
				</table>
			</div>

			<aside v-if="selected" class="rounded-2xl border border-border bg-bg p-5 shadow-card">
				<div class="mb-4 flex items-start justify-between gap-3">
					<div>
						<p class="font-mono text-sm text-fg-muted">{{ selected.contract_no }}</p>
						<h2 class="text-xl font-bold">{{ selected.customer }}</h2>
					</div>
					<span
						class="rounded-full px-2.5 py-1 text-xs"
						:class="statusClass(selected.status)"
						>{{ statusLabel(selected.status) }}</span
					>
				</div>
				<dl class="grid grid-cols-2 gap-3 text-sm">
					<div>
						<dt class="text-fg-muted">{{ t("الفترة", "Period") }}</dt>
						<dd>{{ selected.start_date }} — {{ selected.end_date }}</dd>
					</div>
					<div>
						<dt class="text-fg-muted">{{ t("SLA", "SLA") }}</dt>
						<dd>
							{{ selected.response_sla_hours || 0 }}h /
							{{ selected.resolution_sla_hours || 0 }}h
						</dd>
					</div>
				</dl>
				<h3 class="mb-2 mt-5 font-semibold">{{ t("التغطية", "Coverage") }}</h3>
				<ul class="space-y-2 text-sm">
					<li
						v-for="rule in selected.coverage_rules"
						:key="rule.name"
						class="rounded-xl bg-surface p-3"
					>
						<strong>{{ rule.rule_name }}</strong>
						<p class="text-fg-muted">
							{{ rule.service_type || t("كل الخدمات", "All services") }} ·
							{{ rule.classification }}
						</p>
					</li>
				</ul>
				<h3 class="mb-2 mt-5 font-semibold">{{ t("الاستحقاقات", "Entitlements") }}</h3>
				<ul class="space-y-2 text-sm">
					<li
						v-for="item in selected.entitlements"
						:key="item.name"
						class="flex justify-between rounded-xl bg-surface p-3"
					>
						<span
							>{{ item.entitlement_type }} ·
							{{ item.service_type || t("عام", "General") }}</span
						><strong
							>{{ item.remaining_quantity }} / {{ item.included_quantity }}</strong
						>
					</li>
				</ul>
				<div class="mt-5 flex flex-wrap gap-2">
					<KlButton
						v-if="selected.status === 'Draft' || selected.status === 'Suspended'"
						size="sm"
						:disabled="saving"
						@click="transition('Active')"
						>{{ t("تفعيل", "Activate") }}</KlButton
					><KlButton
						v-if="selected.status === 'Active'"
						size="sm"
						variant="secondary"
						:disabled="saving"
						@click="transition('Suspended')"
						>{{ t("إيقاف مؤقت", "Suspend") }}</KlButton
					><KlButton
						v-if="selected.status !== 'Expired' && selected.status !== 'Cancelled'"
						size="sm"
						variant="danger"
						:disabled="saving"
						@click="transition('Cancelled')"
						>{{ t("إلغاء", "Cancel") }}</KlButton
					>
				</div>
			</aside>
		</div>
	</div>
</template>
