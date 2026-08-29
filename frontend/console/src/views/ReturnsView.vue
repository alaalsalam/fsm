<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { PageHeader, EmptyState, Spinner, LinkField } from "@digit/ui";
import {
	listReturns,
	createReturn,
	processReturn,
	searchLink,
	type ServiceReturnRow,
	type ReturnItemInput,
} from "@/lib/fsm";
import { t } from "@/lib/i18n";

const rows = ref<ServiceReturnRow[]>([]);
const loading = ref(true);
const error = ref("");
const busy = ref<string | null>(null);

const showForm = ref(false);
const saving = ref(false);
const form = reactive<{
	service_job: string;
	warehouse: string;
	reason: string;
	items: ReturnItemInput[];
}>({
	service_job: "",
	warehouse: "",
	reason: "",
	items: [{ item_code: "", qty: 1, disposition: "Restock" }],
});

const searchJob = (q: string) => searchLink("Service Job", q, "customer_name", "customer_name");
const searchWarehouse = (q: string) => searchLink("Warehouse", q);
const searchItem = (q: string) => searchLink("Item", q, "item_name", "item_name");

const RETURN_TONE: Record<string, string> = {
	Draft: "bg-fg-muted/15 text-fg-muted",
	Requested: "bg-warning/15 text-warning",
	Approved: "bg-info/15 text-info",
	Received: "bg-success/15 text-success",
	Closed: "bg-fg-muted/15 text-fg-muted",
	Cancelled: "bg-danger/15 text-danger",
};

function nextAction(
	status: string,
): { action: "approve" | "receive" | "close"; label: string } | null {
	if (status === "Requested") return { action: "approve", label: t("اعتماد", "Approve") };
	if (status === "Approved") return { action: "receive", label: t("استلام", "Receive") };
	if (status === "Received") return { action: "close", label: t("إغلاق", "Close") };
	return null;
}

const returnStatus = (status: string) =>
	({
		Draft: t("مسودة", "Draft"),
		Requested: t("مطلوب", "Requested"),
		Approved: t("معتمد", "Approved"),
		Received: t("مستلم", "Received"),
		Closed: t("مغلق", "Closed"),
		Cancelled: t("ملغي", "Cancelled"),
	})[status] ?? status;

const dispositionLabel = (value: string) =>
	({
		Restock: t("إعادة للمخزون", "Restock"),
		Refurbish: t("إعادة تأهيل", "Refurbish"),
		Scrap: t("إتلاف", "Scrap"),
	})[value] ?? value;

async function load() {
	loading.value = true;
	error.value = "";
	try {
		rows.value = await listReturns();
	} catch {
		error.value = t("تعذّر تحميل المرتجعات.", "Couldn't load returns.");
	} finally {
		loading.value = false;
	}
}

function addItem() {
	form.items.push({ item_code: "", qty: 1, disposition: "Restock" });
}
function removeItem(i: number) {
	form.items.splice(i, 1);
}

async function submit() {
	const items = form.items.filter((i) => i.item_code && i.qty > 0);
	if (!form.service_job || items.length === 0) {
		error.value = t(
			"اختر أمر خدمة وصنفًا واحدًا على الأقل.",
			"Pick a job and at least one item.",
		);
		return;
	}
	saving.value = true;
	error.value = "";
	try {
		await createReturn(
			form.service_job,
			items,
			form.warehouse || undefined,
			form.reason || undefined,
		);
		showForm.value = false;
		form.service_job = "";
		form.warehouse = "";
		form.reason = "";
		form.items = [{ item_code: "", qty: 1, disposition: "Restock" }];
		await load();
	} catch {
		error.value = t("تعذّر إنشاء المرتجع.", "Couldn't create the return.");
	} finally {
		saving.value = false;
	}
}

async function advance(row: ServiceReturnRow, action: "approve" | "receive" | "close") {
	busy.value = row.name;
	error.value = "";
	try {
		await processReturn(row.name, action);
		await load();
	} catch {
		error.value = t("تعذّر تحديث المرتجع.", "Couldn't update the return.");
	} finally {
		busy.value = null;
	}
}

onMounted(load);
</script>

<template>
	<div>
		<PageHeader
			:eyebrow="t('قطع الغيار', 'Parts')"
			:title="t('المرتجعات', 'Returns')"
			:subtitle="t('القطع المعادة من أوامر الخدمة', 'Parts coming back from jobs')"
		>
			<template #actions>
				<button
					type="button"
					class="kl-grad-brand inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-e2 hover:brightness-110"
					@click="showForm = !showForm"
				>
					{{ showForm ? t("إغلاق", "Close") : t("مرتجع جديد", "New return") }}
				</button>
			</template>
		</PageHeader>

		<p
			v-if="error"
			class="mb-4 rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-danger"
		>
			{{ error }}
		</p>

		<section
			v-if="showForm"
			class="mb-6 space-y-4 rounded-2xl border border-border bg-bg p-4 shadow-card backdrop-blur-xl"
		>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
				<LinkField
					v-model="form.service_job"
					:label="t('أمر الخدمة', 'Service job')"
					:search="searchJob"
				/>
				<LinkField
					v-model="form.warehouse"
					:label="t('مستودع الاستلام', 'Receiving warehouse')"
					:search="searchWarehouse"
				/>
				<div>
					<span class="mb-1 block text-sm font-medium">{{ t("السبب", "Reason") }}</span>
					<input
						v-model="form.reason"
						class="w-full rounded-md border border-border bg-bg px-3 py-2 focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
						:placeholder="t('اختياري', 'Optional')"
					/>
				</div>
			</div>

			<div class="space-y-2">
				<div
					v-for="(it, i) in form.items"
					:key="i"
					class="grid grid-cols-1 items-end gap-2 sm:grid-cols-[1fr_5rem_8rem_auto]"
				>
					<LinkField
						v-model="it.item_code"
						:label="t('الصنف', 'Item')"
						:search="searchItem"
					/>
					<div>
						<span class="mb-1 block text-sm font-medium">{{ t("الكمية", "Qty") }}</span>
						<input
							v-model.number="it.qty"
							type="number"
							min="0"
							class="w-full rounded-md border border-border bg-bg px-3 py-2"
						/>
					</div>
					<div>
						<span class="mb-1 block text-sm font-medium">{{
							t("التصرف", "Disposition")
						}}</span>
						<select
							v-model="it.disposition"
							class="w-full rounded-md border border-border bg-bg px-3 py-2"
						>
							<option
								v-for="value in ['Restock', 'Refurbish', 'Scrap']"
								:key="value"
								:value="value"
							>
								{{ dispositionLabel(value) }}
							</option>
						</select>
					</div>
					<button
						type="button"
						class="rounded-md border border-border px-3 py-2 text-sm text-fg-muted hover:text-danger disabled:opacity-40"
						:disabled="form.items.length === 1"
						@click="removeItem(i)"
					>
						{{ t("إزالة", "Remove") }}
					</button>
				</div>
				<button
					type="button"
					class="text-sm font-medium text-brand hover:underline"
					@click="addItem"
				>
					{{ t("+ إضافة صنف", "+ Add item") }}
				</button>
			</div>

			<div class="flex justify-end">
				<button
					type="button"
					:disabled="saving"
					class="kl-grad-brand inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-e2 hover:brightness-110 disabled:opacity-60"
					@click="submit"
				>
					<Spinner v-if="saving" :size="14" />
					{{ t("إنشاء المرتجع", "Create return") }}
				</button>
			</div>
		</section>

		<div v-if="loading" class="space-y-3">
			<div
				v-for="n in 3"
				:key="n"
				class="h-14 animate-pulse rounded-xl border border-border bg-white/5"
			/>
		</div>
		<EmptyState
			v-else-if="rows.length === 0"
			:title="t('لا توجد مرتجعات بعد', 'No returns yet')"
			:description="
				t(
					'ستظهر هنا القطع المرتجعة من أوامر الخدمة. أنشئ مرتجعًا لإعادتها للمخزون أو تأهيلها أو إتلافها.',
					'Returns from jobs will appear here. Create one to restock, refurbish or scrap parts.',
				)
			"
		/>
		<div
			v-else
			class="overflow-hidden rounded-2xl border border-border bg-bg shadow-card backdrop-blur-xl"
		>
			<table class="w-full min-w-md text-left text-sm">
				<thead class="border-b border-border text-fg-muted">
					<tr>
						<th class="px-4 py-2.5 font-medium">{{ t("المرتجع", "Return") }}</th>
						<th class="px-4 py-2.5 font-medium">{{ t("أمر الخدمة", "Job") }}</th>
						<th class="px-4 py-2.5 font-medium">{{ t("العميل", "Customer") }}</th>
						<th class="px-4 py-2.5 font-medium">{{ t("الحالة", "Status") }}</th>
						<th class="px-4 py-2.5 text-right font-medium">
							{{ t("الإجراء", "Action") }}
						</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="r in rows"
						:key="r.name"
						class="border-b border-border last:border-0"
					>
						<td class="px-4 py-2.5 font-mono text-xs text-fg">{{ r.name }}</td>
						<td class="px-4 py-2.5 font-mono text-xs text-fg-muted">
							{{ r.service_job }}
						</td>
						<td class="px-4 py-2.5 text-fg">{{ r.customer }}</td>
						<td class="px-4 py-2.5">
							<span
								class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
								:class="RETURN_TONE[r.status] || RETURN_TONE.Draft"
							>
								{{ returnStatus(r.status) }}
							</span>
						</td>
						<td class="px-4 py-2.5 text-right">
							<button
								v-if="nextAction(r.status)"
								type="button"
								:disabled="busy === r.name"
								class="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-fg hover:bg-bg-subtle disabled:opacity-60"
								@click="advance(r, nextAction(r.status)!.action)"
							>
								<Spinner v-if="busy === r.name" :size="12" />
								{{ nextAction(r.status)!.label }}
							</button>
							<span v-else class="text-xs text-fg-muted">—</span>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>
