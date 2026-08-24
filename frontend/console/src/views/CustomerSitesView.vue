<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { PageHeader, Spinner, EmptyState } from "@kodlyft/ui";
import type { CustomerSiteSummary } from "@kodlyft/api";
import { installedBase } from "@/lib/fsm";

const router = useRouter();
const rows = ref<CustomerSiteSummary[]>([]);
const search = ref("");
const status = ref("");
const loading = ref(true);
const error = ref("");
const filtered = computed(() =>
	rows.value.filter(
		(row) =>
			(!status.value || row.status === status.value) &&
			(!search.value ||
				`${row.site_name} ${row.site_code} ${row.customer} ${row.city || ""}`
					.toLowerCase()
					.includes(search.value.toLowerCase())),
	),
);

onMounted(async () => {
	try {
		rows.value = await installedBase.listSites({ limit: 200 });
	} catch {
		error.value = "Couldn't load customer sites.";
	} finally {
		loading.value = false;
	}
});
</script>

<template>
	<div>
		<PageHeader
			eyebrow="Customers & Equipment"
			title="Customer Sites"
			:subtitle="`${filtered.length} service locations`"
		/>
		<div class="mb-4 flex flex-wrap gap-3">
			<input
				v-model="search"
				aria-label="Search sites"
				type="search"
				placeholder="Search site, code, customer or city"
				class="min-w-64 flex-1 rounded-xl border border-border bg-bg px-3.5 py-2.5"
			/>
			<select
				v-model="status"
				aria-label="Site status"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			>
				<option value="">All statuses</option>
				<option>Active</option>
				<option>Inactive</option>
			</select>
		</div>
		<div v-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>
		<p
			v-else-if="error"
			class="rounded-xl border border-danger/30 bg-danger/10 p-4 text-danger"
		>
			{{ error }}
		</p>
		<EmptyState
			v-else-if="!filtered.length"
			title="No customer sites"
			description="Create a service site through the managed site command."
		/>
		<div v-else class="overflow-hidden rounded-2xl border border-border bg-bg shadow-card">
			<table class="w-full text-left text-sm">
				<thead class="border-b border-border text-fg-muted">
					<tr>
						<th class="px-4 py-3">Site</th>
						<th class="px-4 py-3">Customer</th>
						<th class="px-4 py-3">City</th>
						<th class="px-4 py-3">Status</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="row in filtered"
						:key="row.name"
						class="cursor-pointer border-b border-border last:border-0 hover:bg-white/5"
						@click="router.push({ name: 'site-detail', params: { name: row.name } })"
					>
						<td class="px-4 py-3">
							<p class="font-semibold">{{ row.site_name }}</p>
							<p class="font-mono text-xs text-fg-muted">{{ row.site_code }}</p>
						</td>
						<td class="px-4 py-3">{{ row.customer }}</td>
						<td class="px-4 py-3 text-fg-muted">{{ row.city || "—" }}</td>
						<td class="px-4 py-3">
							<span
								class="rounded-full px-2.5 py-1 text-xs"
								:class="
									row.status === 'Active'
										? 'bg-success/15 text-success'
										: 'bg-white/10 text-fg-muted'
								"
								>{{ row.status }}</span
							>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>
