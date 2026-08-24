<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Spinner } from "@kodlyft/ui";
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
		error.value = "This equipment is unavailable or outside your account.";
	} finally {
		loading.value = false;
	}
});
</script>
<template>
	<div>
		<RouterLink to="/my-equipment" class="text-sm text-brand">← My Equipment</RouterLink>
		<div v-if="loading" class="flex justify-center py-16"><Spinner /></div>
		<p v-else-if="error" class="mt-6 text-danger">{{ error }}</p>
		<div v-else-if="equipment" class="mt-4 space-y-4">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div>
					<p class="font-mono text-xs text-brand">{{ equipment.equipment_id }}</p>
					<h1 class="text-3xl font-bold">
						{{ equipment.item_name || equipment.item_code }}
					</h1>
					<p class="text-fg-muted">{{ equipment.serial_no || "No serial number" }}</p>
				</div>
				<span class="rounded-full bg-brand/15 px-3 py-1 text-sm text-brand">{{
					equipment.status
				}}</span>
			</div>
			<section class="kl-glass rounded-2xl p-5">
				<dl class="grid gap-4 sm:grid-cols-2">
					<div>
						<dt class="text-xs text-fg-muted">Site / location</dt>
						<dd>
							{{ equipment.customer_site || "Main location" }} ·
							{{ equipment.equipment_location || "—" }}
						</dd>
					</div>
					<div>
						<dt class="text-xs text-fg-muted">Warranty</dt>
						<dd>
							{{ equipment.warranty_status
							}}<span v-if="equipment.warranty_end_date">
								until {{ equipment.warranty_end_date }}</span
							>
						</dd>
					</div>
					<div>
						<dt class="text-xs text-fg-muted">Installed</dt>
						<dd>{{ equipment.installation_date || "Pending" }}</dd>
					</div>
					<div>
						<dt class="text-xs text-fg-muted">Quantity</dt>
						<dd>{{ equipment.installed_quantity }}</dd>
					</div>
				</dl>
			</section>
			<section class="kl-glass rounded-2xl p-5">
				<h2 class="font-bold">Service history</h2>
				<p v-if="!history.length" class="mt-3 text-sm text-fg-muted">
					No service history yet.
				</p>
				<ol v-else class="mt-4 space-y-3">
					<li v-for="e in history" :key="e.event_id" class="border-l-2 border-brand pl-4">
						<p class="font-medium">{{ e.event_type }}</p>
						<p class="text-xs text-fg-muted">
							{{ new Date(e.event_time).toLocaleString() }}
						</p>
					</li>
				</ol>
			</section>
		</div>
	</div>
</template>
