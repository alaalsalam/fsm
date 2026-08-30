<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import type { MaintenancePlanStatus } from "@digit/api";
import { KlButton, LinkField, PageHeader, Spinner, statusLabel } from "@digit/ui";
import {
	confirmEquipmentInstallation,
	confirmDeliveryInstallations,
	getAfterSalesSetup,
	maintenance,
	provisionAfterSalesEquipment,
	retryAfterSalesContract,
	searchSubmittedDeliveryNotes,
	seedMaintenancePlans,
	type AfterSalesEquipment,
	type AfterSalesSetup,
	type MaintenancePlanSeedResult,
} from "@/lib/fsm";
import { t } from "@/lib/i18n";

const route = useRoute();
const router = useRouter();
const deliveryNote = ref("");
const data = ref<AfterSalesSetup | null>(null);
const loading = ref(false);
const busy = ref("");
const error = ref("");
const success = ref("");
const selectedSite = ref("");
const selectedContract = ref("");
const planPreview = ref<MaintenancePlanSeedResult | null>(null);
const cadence = reactive({
	service_type: "Preventive Maintenance",
	interval_count: 3,
	interval_unit: "Months",
	first_due_date: new Date().toISOString().slice(0, 10),
	timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
});

const steps = computed(() => {
	const d = data.value;
	const states = [
		Boolean(d),
		Boolean(d?.readiness.equipment_provisioned),
		Boolean(d?.readiness.equipment_provisioned && d.readiness.pending_installation === 0),
		Boolean(d?.readiness.contract_active),
		Boolean(d?.readiness.maintenance_configured),
		Boolean(d?.readiness.schedule_generated),
	];
	const labels = [
		t("التسليم", "Delivery"),
		t("المعدات", "Equipment"),
		t("التركيب", "Installation"),
		t("العقد", "Contract"),
		t("خطة الصيانة", "Maintenance plan"),
		t("الجدول الدوري", "Recurring schedule"),
	];
	const firstPending = states.findIndex((value) => !value);
	return labels.map((label, index) => ({
		index: index + 1,
		label,
		state: states[index] ? "done" : index === firstPending ? "current" : "pending",
	}));
});

const pendingEquipment = computed(() =>
	(data.value?.equipment ?? []).filter((row) => row.status === "Pending Installation"),
);

const nextActionText = computed(() => {
	const code = data.value?.next_action.code;
	return (
		{
			PROVISION_EQUIPMENT: t(
				"إنشاء سجلات المعدات من إشعار التسليم",
				"Create equipment from delivery",
			),
			ASSIGN_SITE: t("تحديد موقع تركيب المعدات", "Assign equipment installation sites"),
			CONFIRM_INSTALLATION: t("تأكيد تركيب المعدات", "Confirm equipment installation"),
			PREPARE_CONTRACT: t("تجهيز مسودة عقد الخدمة", "Prepare the draft service contract"),
			REVIEW_CONTRACT: t(
				"مراجعة واعتماد عقد الخدمة",
				"Review and activate the service contract",
			),
			PREPARE_PM: t("تجهيز مسودات خطط الصيانة", "Prepare draft maintenance plans"),
			APPROVE_PLANS: t("مراجعة واعتماد خطط الصيانة", "Review and activate maintenance plans"),
			GENERATE_SCHEDULE: t(
				"تفعيل الخطط وتوليد الجدول",
				"Activate plans and generate schedule",
			),
			READY: t("المسار جاهز للتشغيل والمتابعة", "The journey is ready for operations"),
		}[code || ""] ||
		data.value?.next_action.action ||
		""
	);
});

async function load(preserveFeedback = false) {
	if (!deliveryNote.value) return;
	loading.value = true;
	if (!preserveFeedback) {
		error.value = "";
		success.value = "";
	}
	try {
		data.value = await getAfterSalesSetup(deliveryNote.value);
		if (!data.value.sites.some((row) => row.name === selectedSite.value)) {
			const activeSites = data.value.sites.filter((row) => row.status === "Active");
			selectedSite.value = activeSites.length === 1 ? activeSites[0]?.name || "" : "";
		}
		const requestedContract =
			typeof route.query.contract === "string" &&
			data.value.contracts.some((row) => row.name === route.query.contract)
				? route.query.contract
				: "";
		if (!data.value.contracts.some((row) => row.name === selectedContract.value)) {
			selectedContract.value =
				requestedContract ||
				data.value.contracts.find((row) => row.status === "Active")?.name ||
				data.value.contracts[0]?.name ||
				"";
		}
		planPreview.value = null;
		cadence.first_due_date = data.value.delivery_note.posting_date || cadence.first_due_date;
		await router.replace({
			query: {
				...route.query,
				delivery_note: deliveryNote.value,
				contract: selectedContract.value || undefined,
			},
		});
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t(
				"تعذر فتح رحلة ما بعد البيع. تحقق من اعتماد إشعار التسليم وصلاحيات الشركة.",
				"Couldn't open the after-sales journey. Confirm the Delivery Note and company access.",
			);
	} finally {
		loading.value = false;
	}
}

async function confirmAllInstallations() {
	if (!selectedSite.value) {
		error.value = t("اختر موقع التركيب أولًا.", "Select an installation site first.");
		return;
	}
	busy.value = "install-all";
	error.value = "";
	success.value = "";
	try {
		const result = await confirmDeliveryInstallations(deliveryNote.value, selectedSite.value);
		data.value = result.journey;
		success.value = t(
			`تم تأكيد تركيب ${result.count} معدة وربطها بالعقد.`,
			`${result.count} equipment installations were confirmed and linked to the contract.`,
		);
		await load(true);
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t(
				"تعذر تأكيد تركيب معدات التسليم.",
				"Couldn't confirm the delivered equipment installations.",
			);
	} finally {
		busy.value = "";
	}
}

async function provision() {
	busy.value = "provision";
	error.value = "";
	try {
		await provisionAfterSalesEquipment(deliveryNote.value);
		success.value = t(
			"تم إنشاء سجلات المعدات وربطها بإشعار التسليم.",
			"Equipment records were created and linked to the Delivery Note.",
		);
		await load(true);
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t("تعذر إنشاء المعدات.", "Couldn't provision equipment.");
	} finally {
		busy.value = "";
	}
}

async function confirmInstallation(row: AfterSalesEquipment) {
	const site = row.customer_site || selectedSite.value;
	if (!site) {
		error.value = t("اختر موقع التركيب أولًا.", "Select an installation site first.");
		return;
	}
	busy.value = row.name;
	error.value = "";
	try {
		await confirmEquipmentInstallation(row.name, site, row.equipment_location);
		success.value = t(
			`تم تأكيد تركيب ${row.equipment_id}.`,
			`${row.equipment_id} installation confirmed.`,
		);
		await load(true);
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t("تعذر تأكيد التركيب.", "Couldn't confirm installation.");
	} finally {
		busy.value = "";
	}
}

async function openContractSetup() {
	if (!data.value) return;
	const existing = data.value.contracts[0];
	if (existing) {
		await router.push({
			path: "/contracts",
			query: { contract: existing.name, delivery_note: deliveryNote.value },
		});
		return;
	}
	busy.value = "contract";
	error.value = "";
	try {
		const contract = await retryAfterSalesContract(deliveryNote.value);
		await router.push({
			path: "/contracts",
			query: { contract: contract.name, delivery_note: deliveryNote.value },
		});
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t(
				"تعذر تجهيز مسودة العقد من إشعار التسليم.",
				"Couldn't prepare the draft contract from the delivery.",
			);
	} finally {
		busy.value = "";
	}
}

async function previewPlans() {
	if (!selectedContract.value) {
		error.value = t("اختر عقد الخدمة أولًا.", "Select a service contract first.");
		return;
	}
	busy.value = "preview";
	error.value = "";
	try {
		planPreview.value = await seedMaintenancePlans(selectedContract.value, { preview: 1 });
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t(
				"تعذر تجهيز معاينة الخطط. تحقق من نطاق المعدات في العقد.",
				"Couldn't preview plans. Check the contract equipment scope.",
			);
	} finally {
		busy.value = "";
	}
}

async function createPlans() {
	if (!selectedContract.value) return;
	busy.value = "plans";
	error.value = "";
	try {
		await seedMaintenancePlans(selectedContract.value, {
			...cadence,
			preview: 0,
		});
		success.value = t(
			"تم إنشاء خطط الصيانة وربطها بالعقد والمعدات.",
			"Maintenance plans were created and linked to the contract and equipment.",
		);
		planPreview.value = null;
		await load(true);
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t("تعذر إنشاء خطط الصيانة.", "Couldn't create maintenance plans.");
	} finally {
		busy.value = "";
	}
}

async function generateSchedule() {
	if (!data.value) return;
	busy.value = "schedule";
	error.value = "";
	try {
		for (const plan of data.value.maintenance_plans) {
			if (["Draft", "Paused"].includes(plan.status)) {
				await maintenance.transition(plan.name, "Active" as MaintenancePlanStatus);
			}
			await maintenance.generate(plan.name);
		}
		success.value = t(
			"تم تفعيل الخطط وتوليد جدول الصيانة الدوري.",
			"Plans were activated and the recurring schedule was generated.",
		);
		await load(true);
	} catch (e) {
		error.value =
			(e as { message?: string })?.message ||
			t("تعذر توليد الجدول الدوري.", "Couldn't generate the recurring schedule.");
	} finally {
		busy.value = "";
	}
}

onMounted(() => {
	if (typeof route.query.delivery_note === "string") {
		deliveryNote.value = route.query.delivery_note;
		load();
	}
});
</script>

<template>
	<div>
		<PageHeader
			:eyebrow="t('من البيع إلى الخدمة الدورية', 'From sale to recurring service')"
			:title="t('رحلة ما بعد البيع', 'After-sales journey')"
			:subtitle="
				t(
					'مسار واحد يقودك من إشعار التسليم إلى جدول الصيانة وأوامر النزول',
					'One guided path from Delivery Note to maintenance schedule and field jobs',
				)
			"
		/>

		<section class="mb-6 rounded-2xl border border-primary/20 bg-primary/5 p-5">
			<h2 class="font-bold">
				{{ t("ما الذي يحدث تلقائيًا؟", "What happens automatically?") }}
			</h2>
			<p class="mt-1 text-sm text-fg-muted">
				{{
					t(
						"عند اعتماد الفاتورة أو إشعار التسليم ينشئ النظام مسودة العقد، وعند التسليم ينشئ المعدات. بعد تأكيد التركيب تراجع العقد ودورية الصيانة، ثم يؤدي اعتماد العقد إلى تجهيز خطط الصيانة كمسودات لاعتمادها وتوليد الجدول.",
						"Submitting an invoice or delivery prepares a draft contract, while delivery provisions equipment. Confirm installation, review the contract and cadence, then activate it to prepare draft maintenance plans for approval and scheduling.",
					)
				}}
			</p>
		</section>

		<form
			class="mb-6 flex max-w-3xl items-end gap-3 rounded-2xl border border-border bg-bg p-5 shadow-card"
			@submit.prevent="load()"
		>
			<div class="flex-1">
				<LinkField
					v-model="deliveryNote"
					:label="t('إشعار التسليم المعتمد', 'Submitted Delivery Note')"
					required
					:search="searchSubmittedDeliveryNotes"
				/>
			</div>
			<KlButton type="submit" :disabled="loading || !deliveryNote">{{
				t("عرض الرحلة", "Open journey")
			}}</KlButton>
		</form>

		<div v-if="loading" class="flex justify-center p-12"><Spinner /></div>
		<template v-else-if="data">
			<div class="mb-6 grid gap-2 sm:grid-cols-3 xl:grid-cols-6">
				<div
					v-for="step in steps"
					:key="step.index"
					class="rounded-xl border p-3"
					:class="
						step.state === 'done'
							? 'border-success/30 bg-success/10'
							: step.state === 'current'
								? 'border-primary bg-primary/10'
								: 'border-border bg-bg opacity-60'
					"
				>
					<div class="flex items-center gap-2">
						<span
							class="flex size-6 items-center justify-center rounded-full text-xs font-bold"
							:class="
								step.state === 'done'
									? 'bg-success text-white'
									: step.state === 'current'
										? 'bg-primary text-white'
										: 'bg-surface'
							"
							>{{ step.state === "done" ? "✓" : step.index }}</span
						><span class="text-sm font-semibold">{{ step.label }}</span>
					</div>
				</div>
			</div>

			<p
				v-if="error"
				class="mb-4 rounded-xl border border-danger/30 bg-danger/10 p-4 text-danger"
			>
				{{ error }}
			</p>
			<p
				v-if="success"
				class="mb-4 rounded-xl border border-success/30 bg-success/10 p-4 text-success"
			>
				{{ success }}
			</p>

			<section class="mb-6 rounded-2xl border border-primary/30 bg-bg p-5 shadow-card">
				<p class="text-xs uppercase tracking-wide text-fg-muted">
					{{ t("الخطوة التالية", "Next step") }}
				</p>
				<h2 class="mt-1 text-xl font-bold">{{ nextActionText }}</h2>
				<div class="mt-4 flex flex-wrap gap-2">
					<KlButton
						v-if="data.next_action.code === 'PROVISION_EQUIPMENT'"
						:disabled="Boolean(busy)"
						@click="provision"
						>{{ t("إعادة إنشاء المعدات", "Retry equipment provisioning") }}</KlButton
					>
					<KlButton
						v-if="
							['ASSIGN_SITE', 'CONFIRM_INSTALLATION'].includes(
								data.next_action.code,
							) && pendingEquipment.length
						"
						:disabled="Boolean(busy) || !selectedSite"
						@click="confirmAllInstallations"
						>{{
							t(
								`تأكيد تركيب ${pendingEquipment.length} معدة في الموقع المحدد`,
								`Confirm ${pendingEquipment.length} installations at the selected site`,
							)
						}}</KlButton
					>
					<KlButton
						v-if="
							['PREPARE_CONTRACT', 'REVIEW_CONTRACT'].includes(data.next_action.code)
						"
						:disabled="Boolean(busy)"
						@click="openContractSetup"
						>{{
							data.next_action.code === "PREPARE_CONTRACT"
								? t("تجهيز مسودة العقد", "Prepare draft contract")
								: t("مراجعة واعتماد العقد", "Review and activate contract")
						}}</KlButton
					>
					<KlButton
						v-if="data.next_action.code === 'PREPARE_PM'"
						:disabled="Boolean(busy)"
						@click="previewPlans"
						>{{ t("معاينة خطط الصيانة", "Preview maintenance plans") }}</KlButton
					>
					<KlButton
						v-if="
							['APPROVE_PLANS', 'GENERATE_SCHEDULE'].includes(data.next_action.code)
						"
						:disabled="Boolean(busy)"
						@click="generateSchedule"
						>{{
							t("اعتماد الخطط وتوليد الجدول", "Approve plans and generate schedule")
						}}</KlButton
					>
					<RouterLink
						v-if="data.next_action.code === 'READY'"
						to="/maintenance?tab=schedule"
						class="inline-flex rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white"
						>{{ t("فتح جدول الصيانة", "Open maintenance schedule") }}</RouterLink
					>
				</div>
			</section>

			<div class="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
				<section class="rounded-2xl border border-border bg-bg p-5 shadow-card">
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div>
							<p class="font-mono text-xs text-fg-muted">
								{{ data.delivery_note.name }}
							</p>
							<h2 class="text-lg font-bold">{{ data.delivery_note.customer }}</h2>
							<p class="text-sm text-fg-muted">
								{{ data.delivery_note.company }} ·
								{{ data.delivery_note.posting_date }}
							</p>
						</div>
						<span class="rounded-full bg-success/15 px-2.5 py-1 text-xs text-success">{{
							statusLabel(data.delivery_note.provisioning_status || "Submitted")
						}}</span>
					</div>

					<div
						v-if="pendingEquipment.length"
						class="mt-5 rounded-xl border border-warning/30 bg-warning/5 p-4"
					>
						<label class="text-sm font-medium"
							>{{ t("موقع التركيب الافتراضي", "Default installation site") }}
							<select
								v-model="selectedSite"
								class="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2"
							>
								<option value="">{{ t("اختر الموقع", "Select site") }}</option>
								<option
									v-for="site in data.sites"
									:key="site.name"
									:value="site.name"
								>
									{{ site.site_name || site.name }}
								</option>
							</select>
						</label>
					</div>

					<div class="mt-4 divide-y divide-border">
						<div
							v-for="row in data.equipment"
							:key="row.name"
							class="flex flex-wrap items-center justify-between gap-3 py-3"
						>
							<RouterLink
								:to="`/equipment/${row.name}`"
								class="min-w-0 hover:text-primary"
								><p class="font-semibold">
									{{ row.equipment_name || row.item_code }}
								</p>
								<p class="font-mono text-xs text-fg-muted">
									{{ row.equipment_id }} ·
									{{ row.serial_no || t("بدون رقم تسلسلي", "No serial") }}
								</p>
								<p class="text-xs text-fg-muted">
									{{
										row.customer_site ||
										t("لم يحدد موقع التركيب", "Installation site not assigned")
									}}
								</p></RouterLink
							>
							<div class="flex items-center gap-2">
								<span
									class="rounded-full bg-info/15 px-2.5 py-1 text-xs text-info"
									>{{ statusLabel(row.status) }}</span
								><KlButton
									v-if="row.status === 'Pending Installation'"
									size="sm"
									:disabled="Boolean(busy)"
									@click="confirmInstallation(row)"
									>{{
										busy === row.name
											? t("جارٍ التأكيد…", "Confirming…")
											: t("تأكيد التركيب", "Confirm installation")
									}}</KlButton
								>
							</div>
						</div>
					</div>
				</section>

				<div class="space-y-5">
					<section class="rounded-2xl border border-border bg-bg p-5 shadow-card">
						<div class="flex items-center justify-between">
							<h2 class="font-bold">
								{{ t("العقد ونطاق التغطية", "Contract and coverage scope") }}
							</h2>
							<RouterLink
								to="/contracts"
								class="text-sm text-primary hover:underline"
								>{{ t("كل العقود", "All contracts") }}</RouterLink
							>
						</div>
						<div v-if="data.contracts.length" class="mt-3">
							<select
								v-model="selectedContract"
								class="w-full rounded-lg border border-border bg-bg px-3 py-2"
							>
								<option
									v-for="contract in data.contracts"
									:key="contract.name"
									:value="contract.name"
								>
									{{ contract.contract_no || contract.name }} ·
									{{ contract.status }}
								</option>
							</select>
						</div>
						<p v-else class="mt-3 text-sm text-fg-muted">
							{{
								t(
									"لا يوجد عقد مرتبط بالعميل بعد.",
									"No service contract is linked to this customer yet.",
								)
							}}
						</p>
						<KlButton
							class="mt-3"
							size="sm"
							variant="secondary"
							@click="openContractSetup"
							>{{
								data.contracts.length
									? t("مراجعة العقد المرتبط", "Review linked contract")
									: t("تجهيز مسودة العقد", "Prepare draft contract")
							}}</KlButton
						>
					</section>

					<section class="rounded-2xl border border-border bg-bg p-5 shadow-card">
						<div class="flex items-center justify-between">
							<h2 class="font-bold">
								{{ t("الخطة والجدول الدوري", "Plan and recurring schedule") }}
							</h2>
							<RouterLink
								to="/maintenance"
								class="text-sm text-primary hover:underline"
								>{{ t("فتح الصيانة", "Open maintenance") }}</RouterLink
							>
						</div>
						<div class="mt-3 grid grid-cols-2 gap-2 text-sm">
							<div class="rounded-lg bg-surface p-3">
								<p class="text-fg-muted">{{ t("الخطط", "Plans") }}</p>
								<strong class="text-xl">{{ data.maintenance_plans.length }}</strong>
							</div>
							<div class="rounded-lg bg-surface p-3">
								<p class="text-fg-muted">{{ t("المواعيد", "Occurrences") }}</p>
								<strong class="text-xl">{{ data.occurrence_summary.total }}</strong>
							</div>
							<div class="rounded-lg bg-surface p-3">
								<p class="text-fg-muted">
									{{ t("المستحق والمتأخر", "Due / overdue") }}
								</p>
								<strong
									>{{ data.occurrence_summary.due }} /
									{{ data.occurrence_summary.overdue }}</strong
								>
							</div>
							<div class="rounded-lg bg-surface p-3">
								<p class="text-fg-muted">{{ t("الموعد القادم", "Next due") }}</p>
								<strong>{{ data.occurrence_summary.next_due_date || "—" }}</strong>
							</div>
						</div>
						<KlButton
							v-if="selectedContract && !data.maintenance_plans.length"
							class="mt-3"
							size="sm"
							:disabled="Boolean(busy)"
							@click="previewPlans"
							>{{
								t("تجهيز الخطط من العقد", "Prepare plans from contract")
							}}</KlButton
						>
					</section>
				</div>
			</div>

			<section
				v-if="planPreview?.proposals?.length"
				class="mt-6 rounded-2xl border border-primary/30 bg-bg p-5 shadow-card"
			>
				<h2 class="text-lg font-bold">
					{{ t("تأكيد دورية الصيانة", "Confirm maintenance cadence") }}
				</h2>
				<p class="mt-1 text-sm text-fg-muted">
					{{
						t(
							"سينشئ النظام خطة مستقلة لكل موقع ويضم إليها معدات العقد في ذلك الموقع.",
							"The system creates one plan per site and includes the contract equipment at that site.",
						)
					}}
				</p>
				<div class="mt-4 grid gap-3 md:grid-cols-4">
					<label class="text-sm"
						>{{ t("نوع الخدمة", "Service type")
						}}<input
							v-model="cadence.service_type"
							class="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2" /></label
					><label class="text-sm"
						>{{ t("كل", "Every")
						}}<input
							v-model.number="cadence.interval_count"
							type="number"
							min="1"
							class="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2" /></label
					><label class="text-sm"
						>{{ t("الوحدة", "Unit")
						}}<select
							v-model="cadence.interval_unit"
							class="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2"
						>
							<option value="Days">{{ t("أيام", "Days") }}</option>
							<option value="Weeks">{{ t("أسابيع", "Weeks") }}</option>
							<option value="Months">{{ t("أشهر", "Months") }}</option>
							<option value="Years">{{ t("سنوات", "Years") }}</option>
						</select></label
					><label class="text-sm"
						>{{ t("أول موعد", "First due")
						}}<input
							v-model="cadence.first_due_date"
							type="date"
							class="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2"
					/></label>
				</div>
				<div class="mt-4 grid gap-2 sm:grid-cols-2">
					<div
						v-for="proposal in planPreview.proposals"
						:key="proposal.customer_site"
						class="rounded-xl bg-surface p-3"
					>
						<p class="font-semibold">{{ proposal.customer_site }}</p>
						<p class="text-sm text-fg-muted">
							{{
								t(
									`${proposal.equipment_count} معدة`,
									`${proposal.equipment_count} equipment`,
								)
							}}
							·
							{{
								proposal.existing_plan
									? t("ستستخدم الخطة الموجودة", "Existing plan will be reused")
									: t("ستنشأ خطة جديدة", "A new plan will be created")
							}}
						</p>
					</div>
				</div>
				<KlButton
					class="mt-4"
					:disabled="Boolean(busy) || !cadence.service_type"
					@click="createPlans"
					>{{
						busy === "plans"
							? t("جارٍ الإنشاء…", "Creating…")
							: t("إنشاء الخطط وربطها", "Create and link plans")
					}}</KlButton
				>
			</section>

			<section
				v-if="data.upcoming_occurrences.length"
				class="mt-6 overflow-hidden rounded-2xl border border-border bg-bg shadow-card"
			>
				<div class="flex items-center justify-between border-b border-border p-4">
					<h2 class="font-bold">{{ t("المواعيد القادمة", "Upcoming maintenance") }}</h2>
					<RouterLink
						to="/maintenance?tab=schedule"
						class="text-sm text-primary hover:underline"
						>{{ t("عرض الجدول الكامل", "Full schedule") }}</RouterLink
					>
				</div>
				<div class="overflow-x-auto">
					<table class="w-full min-w-[700px] text-sm">
						<thead class="border-b border-border text-fg-muted">
							<tr>
								<th class="p-3">{{ t("الموعد", "Due") }}</th>
								<th class="p-3">{{ t("الموقع", "Site") }}</th>
								<th class="p-3">{{ t("المعدة", "Equipment") }}</th>
								<th class="p-3">{{ t("الخدمة", "Service") }}</th>
								<th class="p-3">{{ t("الحالة / الأمر", "Status / job") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in data.upcoming_occurrences"
								:key="row.name"
								class="border-b border-border last:border-0"
							>
								<td class="p-3">{{ row.due_date }}</td>
								<td class="p-3">{{ row.customer_site }}</td>
								<td class="p-3">
									<RouterLink
										:to="`/equipment/${row.installed_equipment}`"
										class="text-primary"
										>{{ row.installed_equipment }}</RouterLink
									>
								</td>
								<td class="p-3">{{ row.service_type }}</td>
								<td class="p-3">
									<RouterLink
										v-if="row.released_job"
										:to="`/jobs/${row.released_job}`"
										class="text-primary"
										>{{ row.released_job }}</RouterLink
									><span
										v-else
										class="rounded-full bg-info/15 px-2.5 py-1 text-xs text-info"
										>{{ statusLabel(row.status) }}</span
									>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>
		</template>
	</div>
</template>
