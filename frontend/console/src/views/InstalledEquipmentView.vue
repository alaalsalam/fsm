<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { PageHeader, Spinner, EmptyState } from "@kodlyft/ui";
import type { InstalledEquipmentSummary } from "@kodlyft/api";
import { installedBase } from "@/lib/fsm";
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
		error.value = "Couldn't load installed equipment.";
	} finally {
		loading.value = false;
	}
});
</script>
<template>
	<div>
		<PageHeader
			eyebrow="Customers & Equipment"
			title="Installed Equipment"
			:subtitle="`${filtered.length} registered assets`"
		/>
		<div class="mb-4 grid gap-3 md:grid-cols-[1fr_auto_auto]">
			<input
				v-model="search"
				aria-label="Search equipment"
				type="search"
				placeholder="Customer, site, item, serial or ID"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			/><select
				v-model="status"
				aria-label="Equipment status"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			>
				<option value="">All statuses</option>
				<option
					v-for="s in [
						'Pending Installation',
						'Active',
						'Inactive',
						'Removed',
						'Returned',
						'Replaced',
						'Disposed',
					]"
					:key="s"
				>
					{{ s }}
				</option></select
			><select
				v-model="warranty"
				aria-label="Warranty status"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			>
				<option value="">All warranties</option>
				<option>Active</option>
				<option>Expired</option>
				<option>Not Applicable</option>
			</select>
		</div>
		<div v-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>
		<p v-else-if="error" class="text-danger">{{ error }}</p>
		<EmptyState
			v-else-if="!filtered.length"
			title="No installed equipment"
			description="Submit a serviceable Delivery Note or use the managed creation command."
		/>
		<div v-else class="overflow-x-auto rounded-2xl border border-border bg-bg shadow-card">
			<table class="w-full min-w-[900px] text-left text-sm">
				<thead class="border-b border-border text-fg-muted">
					<tr>
						<th class="px-4 py-3">ID</th>
						<th class="px-4 py-3">Customer / Site</th>
						<th class="px-4 py-3">Item / Serial</th>
						<th class="px-4 py-3">Status</th>
						<th class="px-4 py-3">Installed</th>
						<th class="px-4 py-3">Warranty</th>
						<th class="px-4 py-3">Last service</th>
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
							<p class="text-xs text-fg-muted">{{ r.customer_site || "No site" }}</p>
						</td>
						<td class="px-4 py-3">
							{{ r.item_name || r.item_code }}
							<p class="font-mono text-xs text-fg-muted">
								{{ r.serial_no || "No serial" }}
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
