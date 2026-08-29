<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { ContractDetail, ContractStatus, ContractSummary } from "@digit/api";
import { EmptyState, KlButton, LinkField, PageHeader, Spinner } from "@digit/ui";
import { contracts, installedBase, searchLink } from "@/lib/fsm";
import { lang, t } from "@/lib/i18n";

const rows = ref<ContractSummary[]>([]);
const selected = ref<ContractDetail | null>(null);
const status = ref("");
const route = useRoute();
const router = useRouter();
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const showCreate = ref(false);
const scopeEquipment = ref<Array<{ name: string; label: string; customer_site: string }>>([]);
const pendingEquipment = ref("");
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

const filtered = computed(() => {
	let result = status.value
		? rows.value.filter((row) => row.status === status.value)
		: rows.value;
	if (route.query.expiry === "30") {
		const start = new Date();
		const end = new Date(start);
		end.setDate(end.getDate() + 30);
		result = result.filter((row) => {
			if (!row.end_date) return false;
			const date = new Date(row.end_date);
			return row.status === "Active" && date >= start && date <= end;
		});
	}
	return result;
});

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
			covered_equipment: scopeEquipment.value.map((row) => ({
				customer_site: row.customer_site,
				installed_equipment: row.name,
				active: 1,
			})),
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
		if (typeof route.query.delivery_note === "string") {
			await router.push({
				path: "/after-sales",
				query: { delivery_note: route.query.delivery_note, contract: contract.name },
			});
		}
	} catch {
		error.value = t(
			"تعذّر إنشاء العقد. راجع الحقول والنطاق.",
			"Couldn't create the contract. Check its fields and scope.",
		);
	} finally {
		saving.value = false;
	}
}

async function addScopeEquipment(name = pendingEquipment.value) {
	if (!name || scopeEquipment.value.some((row) => row.name === name)) return;
	error.value = "";
	try {
		const equipment = await installedBase.getEquipment(name);
		if (!equipment.customer_site) {
			error.value = t(
				"يجب تأكيد موقع تركيب المعدة قبل إضافتها إلى نطاق العقد.",
				"Confirm the equipment installation site before adding it to the contract scope.",
			);
			return;
		}
		if (
			(form.customer && equipment.customer !== form.customer) ||
			(form.company && equipment.company !== form.company)
		) {
			error.value = t(
				"المعدة لا تنتمي إلى عميل وشركة العقد.",
				"The equipment does not belong to the contract customer and company.",
			);
			return;
		}
		scopeEquipment.value.push({
			name: equipment.name,
			label: equipment.equipment_name || equipment.equipment_id,
			customer_site: equipment.customer_site,
		});
		pendingEquipment.value = "";
	} catch {
		error.value = t(
			"تعذر إضافة المعدة إلى نطاق العقد.",
			"Couldn't add equipment to the contract scope.",
		);
	}
}

function removeScopeEquipment(name: string) {
	scopeEquipment.value = scopeEquipment.value.filter((row) => row.name !== name);
}

async function applyJourneyContext() {
	if (route.query.create !== "1") return;
	showCreate.value = true;
	form.customer = typeof route.query.customer === "string" ? route.query.customer : "";
	form.company = typeof route.query.company === "string" ? route.query.company : "";
	if (typeof route.query.posting_date === "string") form.start_date = route.query.posting_date;
	if (form.start_date && !form.end_date) {
		const end = new Date(form.start_date);
		end.setFullYear(end.getFullYear() + 1);
		form.end_date = end.toISOString().slice(0, 10);
	}
	if (typeof route.query.delivery_note === "string") {
		form.notes = t(
			`عقد خدمة مرتبط بإشعار التسليم ${route.query.delivery_note}`,
			`Service contract linked to Delivery Note ${route.query.delivery_note}`,
		);
	}
	const equipment =
		typeof route.query.equipment === "string"
			? route.query.equipment.split(",").filter(Boolean)
			: [];
	for (const name of equipment) await addScopeEquipment(name);
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

onMounted(async () => {
	await applyJourneyContext();
	await load();
});
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
			<section class="rounded-xl border border-border bg-surface p-4 md:col-span-2">
				<div>
					<h3 class="font-semibold">
						{{ t("المعدات المشمولة بالعقد", "Covered equipment") }}
					</h3>
					<p class="text-xs text-fg-muted">
						{{
							t(
								"هذا الربط هو الذي يسمح بإنشاء خطة وجدول الصيانة تلقائيًا من العقد.",
								"This scope is what allows maintenance plans and schedules to be generated from the contract.",
							)
						}}
					</p>
				</div>
				<div class="mt-3 flex items-end gap-2">
					<div class="flex-1">
						<LinkField
							v-model="pendingEquipment"
							:label="t('إضافة معدة', 'Add equipment')"
							:search="(q) => searchLink('Installed Equipment', q, 'equipment_name')"
						/>
					</div>
					<KlButton
						type="button"
						size="sm"
						variant="secondary"
						:disabled="!pendingEquipment"
						@click="addScopeEquipment()"
					>
						{{ t("إضافة للنطاق", "Add to scope") }}
					</KlButton>
				</div>
				<div v-if="scopeEquipment.length" class="mt-3 grid gap-2 sm:grid-cols-2">
					<div
						v-for="row in scopeEquipment"
						:key="row.name"
						class="flex items-center justify-between gap-2 rounded-lg border border-border bg-bg p-3 text-sm"
					>
						<div>
							<p class="font-semibold">{{ row.label }}</p>
							<p class="font-mono text-xs text-fg-muted">
								{{ row.name }} · {{ row.customer_site }}
							</p>
						</div>
						<button
							type="button"
							class="text-xs text-danger hover:underline"
							@click="removeScopeEquipment(row.name)"
						>
							{{ t("إزالة", "Remove") }}
						</button>
					</div>
				</div>
				<p
					v-else
					class="mt-3 rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning"
				>
					{{
						t(
							"لم تضف معدات إلى نطاق العقد بعد؛ لن يمكن توليد خطة صيانة من هذا العقد.",
							"No equipment is in scope yet; a maintenance plan cannot be generated from this contract.",
						)
					}}
				</p>
			</section>
			<div class="md:col-span-2">
				<KlButton
					type="submit"
					:disabled="saving || !form.customer || !form.company || !scopeEquipment.length"
					>{{
						saving ? t("جارٍ الحفظ…", "Saving…") : t("حفظ المسودة", "Save draft")
					}}</KlButton
				>
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
				<h3 class="mb-2 mt-5 font-semibold">{{ t("نطاق المعدات", "Equipment scope") }}</h3>
				<ul class="space-y-2 text-sm">
					<li
						v-for="item in selected.covered_equipment"
						:key="`${item.customer_site}-${item.installed_equipment || item.item_group}`"
						class="rounded-xl bg-surface p-3"
					>
						<strong>{{ item.installed_equipment || item.item_group }}</strong>
						<p class="text-fg-muted">{{ item.customer_site }}</p>
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
