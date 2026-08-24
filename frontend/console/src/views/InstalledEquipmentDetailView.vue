<script setup lang="ts">
import { onMounted, ref } from "vue";
import { PageHeader, Spinner } from "@kodlyft/ui";
import type { EquipmentHistoryEvent, InstalledEquipmentDetail } from "@kodlyft/api";
import { installedBase } from "@/lib/fsm";
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
		error.value = "Couldn't load this equipment record.";
	} finally {
		loading.value = false;
	}
});
const printQr = () => window.print();
</script>
<template>
	<div>
		<PageHeader
			eyebrow="Installed Equipment"
			:title="equipment?.equipment_id || name"
			:subtitle="
				equipment
					? `${equipment.customer} · ${equipment.item_name || equipment.item_code}`
					: ''
			"
		/>
		<div v-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>
		<p v-else-if="error" class="text-danger">{{ error }}</p>
		<div v-else-if="equipment" class="space-y-4">
			<div class="grid gap-4 lg:grid-cols-3">
				<section class="kl-glass rounded-2xl p-5 lg:col-span-2">
					<div class="flex justify-between">
						<h2 class="font-bold">Overview</h2>
						<span class="rounded-full bg-brand/15 px-3 py-1 text-sm text-brand">{{
							equipment.status
						}}</span>
					</div>
					<dl class="mt-4 grid gap-4 sm:grid-cols-2">
						<div>
							<dt class="text-xs text-fg-muted">Site / location</dt>
							<dd>
								{{ equipment.customer_site || "—" }} ·
								{{ equipment.equipment_location || "Main site" }}
							</dd>
						</div>
						<div>
							<dt class="text-xs text-fg-muted">Product</dt>
							<dd>
								{{ equipment.item_code }} · {{ equipment.serial_no || "No serial" }}
							</dd>
						</div>
						<div>
							<dt class="text-xs text-fg-muted">Sales source</dt>
							<dd>
								{{ equipment.delivery_note || equipment.source }} ·
								{{ equipment.sales_order || "—" }}
							</dd>
						</div>
						<div>
							<dt class="text-xs text-fg-muted">Warranty</dt>
							<dd>
								{{ equipment.warranty_status }} ·
								{{ equipment.warranty_end_date || "—" }}
							</dd>
						</div>
						<div>
							<dt class="text-xs text-fg-muted">Technical</dt>
							<dd>
								{{ equipment.manufacturer || "—" }} {{ equipment.model_no || "" }}
							</dd>
						</div>
						<div>
							<dt class="text-xs text-fg-muted">Last service</dt>
							<dd>{{ equipment.last_service_date || "—" }}</dd>
						</div>
					</dl>
				</section>
				<section class="kl-glass rounded-2xl p-5 text-center">
					<h2 class="font-bold">Service QR</h2>
					<div
						class="mx-auto mt-4 flex aspect-square max-w-40 items-center justify-center rounded-xl border-2 border-dashed border-brand bg-white p-3 font-mono text-sm text-black"
					>
						{{ equipment.qr_code }}
					</div>
					<p class="mt-3 font-mono text-xs text-fg-muted">{{ equipment.qr_code }}</p>
					<button
						class="mt-3 rounded-lg border border-border px-4 py-2 text-sm"
						@click="printQr"
					>
						Print QR
					</button>
				</section>
			</div>
			<section class="kl-glass rounded-2xl p-5">
				<h2 class="font-bold">Service history</h2>
				<p v-if="!history.length" class="mt-3 text-sm text-fg-muted">
					No history events yet.
				</p>
				<ol v-else class="mt-4 space-y-3">
					<li
						v-for="event in history"
						:key="event.event_id"
						class="border-l-2 border-brand pl-4"
					>
						<p class="font-medium">{{ event.event_type }}</p>
						<p class="text-xs text-fg-muted">
							{{ new Date(event.event_time).toLocaleString() }} · {{ event.source
							}}<span v-if="event.to_status"> · {{ event.to_status }}</span>
						</p>
					</li>
				</ol>
			</section>
		</div>
	</div>
</template>
