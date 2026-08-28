<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
	IonPage,
	IonHeader,
	IonToolbar,
	IonTitle,
	IonButtons,
	IonBackButton,
	IonContent,
	IonSpinner,
} from "@ionic/vue";
import type { InstalledEquipmentDetail } from "@digit/api";
import { installedBase } from "@/lib/fsm";
import { formatDate, statusLabel, t } from "@digit/ui";
const props = defineProps<{ id: string }>();
const row = ref<InstalledEquipmentDetail>();
const loading = ref(true);
const error = ref("");
onMounted(async () => {
	try {
		row.value = await installedBase.getEquipment(props.id);
	} catch {
		error.value = t(
			"المعدة غير متاحة أو غير مرتبطة بعمل مسند.",
			"Equipment is unavailable or not linked to an assigned job.",
		);
	} finally {
		loading.value = false;
	}
});
</script>
<template>
	<IonPage
		><IonHeader
			><IonToolbar
				><IonButtons slot="start"><IonBackButton default-href="/equipment" /></IonButtons
				><IonTitle>{{ t("ملخص المعدة", "Equipment Summary") }}</IonTitle></IonToolbar
			></IonHeader
		><IonContent :fullscreen="true"
			><div class="space-y-4 p-4">
				<IonSpinner v-if="loading" />
				<p v-else-if="error" class="text-danger">{{ error }}</p>
				<template v-else-if="row"
					><section class="kl-glass rounded-2xl p-5">
						<p class="font-mono text-xs text-brand">{{ row.equipment_id }}</p>
						<div class="mt-1 flex items-start justify-between gap-3">
							<div>
								<h1 class="text-xl font-bold">
									{{ row.item_name || row.item_code }}
								</h1>
								<p class="font-mono text-sm text-fg-muted">
									{{ row.serial_no || t("لا يوجد رقم تسلسلي", "No serial") }}
								</p>
							</div>
							<span class="rounded-full bg-brand/15 px-3 py-1 text-xs text-brand">{{
								statusLabel(row.status)
							}}</span>
						</div>
					</section>
					<section class="kl-glass rounded-2xl p-5">
						<dl class="space-y-4">
							<div>
								<dt class="text-xs text-fg-muted">{{ t("العميل", "Customer") }}</dt>
								<dd>{{ row.customer }}</dd>
							</div>
							<div>
								<dt class="text-xs text-fg-muted">
									{{ t("الموقع / الموضع", "Site / location") }}
								</dt>
								<dd>
									{{ row.customer_site || t("الموقع الرئيسي", "Main site") }} ·
									{{ row.equipment_location || "—" }}
								</dd>
							</div>
							<div>
								<dt class="text-xs text-fg-muted">{{ t("الضمان", "Warranty") }}</dt>
								<dd>
									{{ statusLabel(row.warranty_status) }} ·
									{{
										row.warranty_end_date
											? formatDate(row.warranty_end_date)
											: "—"
									}}
								</dd>
							</div>
							<div>
								<dt class="text-xs text-fg-muted">
									{{ t("آخر خدمة", "Last service") }}
								</dt>
								<dd>
									{{
										row.last_service_date
											? formatDate(row.last_service_date)
											: "—"
									}}
								</dd>
							</div>
						</dl>
					</section></template
				>
			</div></IonContent
		></IonPage
	>
</template>
