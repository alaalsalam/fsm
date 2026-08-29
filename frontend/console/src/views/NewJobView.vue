<script setup lang="ts">
import { ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { LinkField, KlButton, Spinner } from "@digit/ui";
import { createJob, searchLink, type JobDoc } from "@/lib/fsm";
import { t } from "@/lib/i18n";

const router = useRouter();

const priorityAr: Record<string, string> = {
	Low: "منخفضة",
	Medium: "متوسطة",
	High: "عالية",
	Urgent: "عاجلة",
};
const showPriority = (s: string) => t(priorityAr[s] ?? s, s);

interface ItemRow {
	item_code: string;
	qty: number;
	rate: number;
}

const form = ref({
	customer: "",
	service_type: "",
	priority: "Medium",
	scheduled_date: "",
	territory: "",
	primary_technician: "",
	checklist_template: "",
	notes: "",
});
const items = ref<ItemRow[]>([]);
const busy = ref(false);
const error = ref("");

const PRIORITIES = ["Low", "Medium", "High", "Urgent"];

const searchCustomer = (q: string) => searchLink("Customer", q, "customer_name", "customer_name");
const searchTerritory = (q: string) => searchLink("Service Territory", q);
const searchTechnician = (q: string) => searchLink("Technician", q);
const searchTemplate = (q: string) => searchLink("Checklist Template", q);
const searchItem = (q: string) => searchLink("Item", q, "item_name", "item_name");

function addItem() {
	items.value.push({ item_code: "", qty: 1, rate: 0 });
}
function removeItem(i: number) {
	items.value.splice(i, 1);
}

function toFrappeDatetime(v: string): string | undefined {
	return v ? v.replace("T", " ") + ":00" : undefined;
}

async function submit() {
	if (!form.value.customer) {
		error.value = t("يرجى اختيار عميل.", "Please choose a customer.");
		return;
	}
	error.value = "";
	busy.value = true;
	try {
		const payload: Partial<JobDoc> = {
			customer: form.value.customer,
			service_type: form.value.service_type || undefined,
			priority: form.value.priority,
			scheduled_date: toFrappeDatetime(form.value.scheduled_date),
			territory: form.value.territory || undefined,
			primary_technician: form.value.primary_technician || undefined,
			checklist_template: form.value.checklist_template || undefined,
			notes: form.value.notes || undefined,
			status: form.value.scheduled_date ? "Scheduled" : "Draft",
			items: items.value.filter((r) => r.item_code),
		};
		const job = await createJob(payload);
		router.push({ name: "job-detail", params: { name: job.name } });
	} catch {
		error.value = t(
			"تعذّر إنشاء أمر الخدمة. تحقق من الحقول وحاول مجدداً.",
			"Couldn't create the job. Check the fields and try again.",
		);
	} finally {
		busy.value = false;
	}
}
</script>

<template>
	<div class="mx-auto max-w-3xl">
		<RouterLink
			to="/"
			class="mb-4 inline-flex items-center gap-1 text-sm text-fg-muted hover:text-fg"
		>
			← {{ t("العودة إلى لوحة التوزيع", "Back to dispatch") }}
		</RouterLink>
		<h1 class="mb-6 text-2xl font-bold">{{ t("أمر خدمة جديد", "New job") }}</h1>

		<form class="space-y-6" @submit.prevent="submit">
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<LinkField
					:label="t('العميل', 'Customer')"
					:search="searchCustomer"
					v-model="form.customer"
					required
				/>
				<label class="block">
					<span class="mb-1 block text-sm font-medium">{{
						t("نوع الخدمة", "Service type")
					}}</span>
					<input
						v-model="form.service_type"
						class="w-full rounded-md border border-border bg-bg px-3 py-2 focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
					/>
				</label>
				<label class="block">
					<span class="mb-1 block text-sm font-medium">{{
						t("الأولوية", "Priority")
					}}</span>
					<select
						v-model="form.priority"
						class="w-full rounded-md border border-border bg-bg px-3 py-2 focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
					>
						<option v-for="p in PRIORITIES" :key="p" :value="p">
							{{ showPriority(p) }}
						</option>
					</select>
				</label>
				<label class="block">
					<span class="mb-1 block text-sm font-medium">{{
						t("موعد البدء", "Scheduled start")
					}}</span>
					<input
						v-model="form.scheduled_date"
						type="datetime-local"
						class="w-full rounded-md border border-border bg-bg px-3 py-2 focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
					/>
				</label>
				<LinkField
					:label="t('منطقة الخدمة', 'Service territory')"
					:search="searchTerritory"
					v-model="form.territory"
				/>
				<LinkField
					:label="t('الفني الرئيسي', 'Primary technician')"
					:search="searchTechnician"
					v-model="form.primary_technician"
				/>
				<LinkField
					:label="t('قالب قائمة المهام', 'Checklist template')"
					:search="searchTemplate"
					v-model="form.checklist_template"
				/>
			</div>

			<section>
				<div class="mb-2 flex items-center justify-between">
					<h2 class="text-lg font-bold">
						{{ t("قطع الغيار والخدمات", "Parts & services") }}
					</h2>
					<KlButton type="button" variant="secondary" size="sm" @click="addItem">{{
						t("إضافة صنف", "Add item")
					}}</KlButton>
				</div>
				<div v-if="items.length" class="space-y-2">
					<div v-for="(row, i) in items" :key="i" class="flex items-end gap-2">
						<div class="flex-1">
							<LinkField
								:search="searchItem"
								v-model="row.item_code"
								:placeholder="t('الصنف', 'Item')"
							/>
						</div>
						<label class="w-20">
							<span class="mb-1 block text-xs text-fg-muted">{{
								t("الكمية", "Qty")
							}}</span>
							<input
								v-model.number="row.qty"
								type="number"
								min="0"
								class="w-full rounded-md border border-border bg-bg px-2 py-2 text-right focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
							/>
						</label>
						<label class="w-28">
							<span class="mb-1 block text-xs text-fg-muted">{{
								t("السعر", "Rate")
							}}</span>
							<input
								v-model.number="row.rate"
								type="number"
								min="0"
								class="w-full rounded-md border border-border bg-bg px-2 py-2 text-right focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
							/>
						</label>
						<button
							type="button"
							class="px-2 py-2 text-fg-muted hover:text-danger"
							:aria-label="t('إزالة الصنف', 'Remove item')"
							@click="removeItem(i)"
						>
							✕
						</button>
					</div>
				</div>
				<p v-else class="text-sm text-fg-muted">
					{{
						t(
							"لا توجد بنود بعد — أضف قطعاً أو خدمات لفوترتها لاحقاً.",
							"No items yet — add parts or services to invoice later.",
						)
					}}
				</p>
			</section>

			<label class="block">
				<span class="mb-1 block text-sm font-medium">{{ t("الملاحظات", "Notes") }}</span>
				<textarea
					v-model="form.notes"
					rows="3"
					class="w-full rounded-md border border-border bg-bg px-3 py-2 focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
				></textarea>
			</label>

			<p v-if="error" class="text-sm text-danger">{{ error }}</p>

			<div class="flex gap-2">
				<KlButton type="submit" :disabled="busy">
					<Spinner v-if="busy" :size="18" />
					{{ busy ? t("جارٍ الإنشاء…", "Creating…") : t("إنشاء أمر خدمة", "Create job") }}
				</KlButton>
				<KlButton type="button" variant="ghost" @click="router.push('/')">{{
					t("إلغاء", "Cancel")
				}}</KlButton>
			</div>
		</form>
	</div>
</template>
