<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Spinner, formatDate, statusLabel, t } from "@kodlyft/ui";
import type { EquipmentHistoryEvent, InstalledEquipmentDetail } from "@kodlyft/api";
import { installedBase } from "@/lib/api";
const props = defineProps<{ name: string }>();
const equipment = ref<InstalledEquipmentDetail>();
const history = ref<EquipmentHistoryEvent[]>([]);
const loading = ref(true);
const error = ref("");
onMounted(async () => {
	try {
		[equipment.value, history.value] = await Promise.all([
			installedBase.getEquipment(props.name),
			installedBase.getHistory(props.name),
		]);
	} catch {
		error.value = t(
			"هذه المعدة غير متاحة أو خارج حسابك.",
			"This equipment is unavailable or outside your account.",
		);
	} finally {
		loading.value = false;
	}
});
</script>
<template>
	<div>
		<RouterLink to="/my-equipment" class="text-sm text-brand"
			><span aria-hidden="true">{{ t("→", "←") }}</span>
			{{ t("معداتي", "My Equipment") }}</RouterLink
		>
		<div v-if="loading" class="flex justify-center py-16"><Spinner /></div>
		<p v-else-if="error" class="mt-6 text-danger">{{ error }}</p>
		<div v-else-if="equipment" class="mt-4 space-y-4">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div>
					<p class="font-mono text-xs text-brand">{{ equipment.equipment_id }}</p>
					<h1 class="text-3xl font-bold">
						{{ equipment.item_name || equipment.item_code }}
					</h1>
					<p class="text-fg-muted">
						{{ equipment.serial_no || t("لا يوجد رقم تسلسلي", "No serial number") }}
					</p>
				</div>
				<span class="rounded-full bg-brand/15 px-3 py-1 text-sm text-brand">{{
					statusLabel(equipment.status)
				}}</span>
			</div>
			<section class="kl-glass rounded-2xl p-5">
				<dl class="grid gap-4 sm:grid-cols-2">
					<div>
						<dt class="text-xs text-fg-muted">
							{{ t("الموقع / الموضع", "Site / location") }}
						</dt>
						<dd>
							{{ equipment.customer_site || t("الموقع الرئيسي", "Main location") }} ·
							{{ equipment.equipment_location || "—" }}
						</dd>
					</div>
					<div>
						<dt class="text-xs text-fg-muted">{{ t("الضمان", "Warranty") }}</dt>
						<dd>
							{{ statusLabel(equipment.warranty_status)
							}}<span v-if="equipment.warranty_end_date">
								{{ t("حتى", "until") }}
								{{ formatDate(equipment.warranty_end_date) }}</span
							>
						</dd>
					</div>
					<div>
						<dt class="text-xs text-fg-muted">{{ t("تاريخ التركيب", "Installed") }}</dt>
						<dd>
							{{
								equipment.installation_date
									? formatDate(equipment.installation_date)
									: t("قيد الانتظار", "Pending")
							}}
						</dd>
					</div>
					<div>
						<dt class="text-xs text-fg-muted">{{ t("الكمية", "Quantity") }}</dt>
						<dd>{{ equipment.installed_quantity }}</dd>
					</div>
				</dl>
			</section>
			<section class="kl-glass rounded-2xl p-5">
				<h2 class="font-bold">{{ t("سجل الخدمة", "Service history") }}</h2>
				<p v-if="!history.length" class="mt-3 text-sm text-fg-muted">
					{{ t("لا يوجد سجل خدمة بعد.", "No service history yet.") }}
				</p>
				<ol v-else class="mt-4 space-y-3">
					<li v-for="e in history" :key="e.event_id" class="border-s-2 border-brand ps-4">
						<p class="font-medium">{{ e.event_type }}</p>
						<p class="text-xs text-fg-muted">
							{{ formatDate(e.event_time, true) }}
						</p>
					</li>
				</ol>
			</section>
		</div>
	</div>
</template>
