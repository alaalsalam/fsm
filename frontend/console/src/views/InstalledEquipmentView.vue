<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { PageHeader, Spinner, EmptyState } from "@digit/ui";
import type { InstalledEquipmentSummary } from "@digit/api";
import { installedBase } from "@/lib/fsm";
import { t } from "@/lib/i18n";

const router = useRouter();
const rows = ref<InstalledEquipmentSummary[]>([]);
const search = ref("");
const status = ref("");
const warranty = ref("");
const loading = ref(true);
const error = ref("");
const filtered = computed(() =>
	rows.value.filter(
		(r) =>
			(!status.value || r.status === status.value) &&
			(!warranty.value || r.warranty_status === warranty.value) &&
			(!search.value ||
				`${r.equipment_id} ${r.customer} ${r.customer_site || ""} ${r.item_code} ${r.serial_no || ""}`
					.toLowerCase()
					.includes(search.value.toLowerCase())),
	),
);
onMounted(async () => {
	try {
		rows.value = await installedBase.listEquipment({ limit: 200 });
	} catch {
		error.value = t("تعذّر تحميل المعدات المركّبة.", "Couldn't load installed equipment.");
	} finally {
		loading.value = false;
	}
});
</script>
<template>
	<div>
		<PageHeader
			:eyebrow="t('العملاء والمعدات', 'Customers & Equipment')"
			:title="t('المعدات المركّبة', 'Installed Equipment')"
			:subtitle="t(`${filtered.length} أصل مسجّل`, `${filtered.length} registered assets`)"
		/>
		<div class="mb-4 grid gap-3 md:grid-cols-[1fr_auto_auto]">
			<input
				v-model="search"
				:aria-label="t('بحث في المعدات', 'Search equipment')"
				type="search"
				:placeholder="
					t(
						'العميل أو الموقع أو الصنف أو الرقم التسلسلي أو المعرّف',
						'Customer, site, item, serial or ID',
					)
				"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			/><select
				v-model="status"
				:aria-label="t('حالة المعدة', 'Equipment status')"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			>
				<option value="">{{ t("كل الحالات", "All statuses") }}</option>
				<option value="Pending Installation">
					{{ t("في انتظار التركيب", "Pending Installation") }}
				</option>
				<option value="Active">{{ t("نشط", "Active") }}</option>
				<option value="Inactive">{{ t("غير نشط", "Inactive") }}</option>
				<option value="Removed">{{ t("تمت إزالته", "Removed") }}</option>
				<option value="Returned">{{ t("مُرتجع", "Returned") }}</option>
				<option value="Replaced">{{ t("تم استبداله", "Replaced") }}</option>
				<option value="Disposed">{{ t("تم التخلص منه", "Disposed") }}</option></select
			><select
				v-model="warranty"
				:aria-label="t('حالة الضمان', 'Warranty status')"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			>
				<option value="">{{ t("كل الضمانات", "All warranties") }}</option>
				<option value="Active">{{ t("ساري", "Active") }}</option>
				<option value="Expired">{{ t("منتهي", "Expired") }}</option>
				<option value="Not Applicable">{{ t("غير مطبّق", "Not Applicable") }}</option>
			</select>
		</div>
		<div v-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>
		<p v-else-if="error" class="text-danger">{{ error }}</p>
		<EmptyState
			v-else-if="!filtered.length"
			:title="t('لا توجد معدات مركّبة', 'No installed equipment')"
			:description="
				t(
					'أرسل إشعار تسليم قابل للخدمة أو استخدم أمر الإنشاء المُدار.',
					'Submit a serviceable Delivery Note or use the managed creation command.',
				)
			"
		/>
		<div v-else class="overflow-x-auto rounded-2xl border border-border bg-bg shadow-card">
			<table class="w-full min-w-[900px] text-left text-sm">
				<thead class="border-b border-border text-fg-muted">
					<tr>
						<th class="px-4 py-3">{{ t("المعرّف", "ID") }}</th>
						<th class="px-4 py-3">{{ t("العميل / الموقع", "Customer / Site") }}</th>
						<th class="px-4 py-3">
							{{ t("الصنف / الرقم التسلسلي", "Item / Serial") }}
						</th>
						<th class="px-4 py-3">{{ t("الحالة", "Status") }}</th>
						<th class="px-4 py-3">{{ t("تاريخ التركيب", "Installed") }}</th>
						<th class="px-4 py-3">{{ t("الضمان", "Warranty") }}</th>
						<th class="px-4 py-3">{{ t("آخر خدمة", "Last service") }}</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="r in filtered"
						:key="r.name"
						class="cursor-pointer border-b border-border last:border-0 hover:bg-white/5"
						@click="router.push({ name: 'equipment-detail', params: { name: r.name } })"
					>
						<td class="px-4 py-3 font-mono">{{ r.equipment_id }}</td>
						<td class="px-4 py-3">
							{{ r.customer }}
							<p class="text-xs text-fg-muted">
								{{ r.customer_site || t("لا موقع", "No site") }}
							</p>
						</td>
						<td class="px-4 py-3">
							{{ r.item_name || r.item_code }}
							<p class="font-mono text-xs text-fg-muted">
								{{ r.serial_no || t("لا رقم تسلسلي", "No serial") }}
							</p>
						</td>
						<td class="px-4 py-3">{{ r.status }}</td>
						<td class="px-4 py-3">{{ r.installation_date || "—" }}</td>
						<td class="px-4 py-3">{{ r.warranty_status }}</td>
						<td class="px-4 py-3">{{ r.last_service_date || "—" }}</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>
