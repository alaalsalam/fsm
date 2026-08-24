<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Spinner, StatusPill } from "@kodlyft/ui";
import { listServiceRequests, type ServiceRequestRow } from "@/lib/fsm";

const rows = ref<ServiceRequestRow[]>([]);
const loading = ref(true);
const error = ref("");
onMounted(async () => {
	try {
		rows.value = await listServiceRequests();
	} catch {
		error.value = "Could not load service requests.";
	} finally {
		loading.value = false;
	}
});
</script>

<template>
	<main class="p-4 sm:p-6" data-testid="service-requests">
		<h1 class="text-2xl font-bold text-cmd-fg">Service Requests</h1>
		<p class="mt-1 text-sm text-cmd-fg-muted">
			Intake and triage; work execution remains in Service Jobs.
		</p>
		<div v-if="loading" class="py-12"><Spinner :size="28" /></div>
		<p v-else-if="error" class="mt-6 text-danger">{{ error }}</p>
		<div v-else class="kl-glass mt-6 overflow-hidden rounded-2xl">
			<RouterLink
				v-for="row in rows"
				:key="row.name"
				:to="`/requests/${row.name}`"
				class="flex items-center justify-between gap-4 border-b border-cmd-border p-4 last:border-0"
			>
				<div class="min-w-0">
					<p class="truncate font-semibold text-cmd-fg">{{ row.subject }}</p>
					<p class="text-sm text-cmd-fg-muted">
						{{ row.name }} · {{ row.customer || row.source }}
					</p>
				</div>
				<StatusPill :status="row.status" />
			</RouterLink>
		</div>
	</main>
</template>
