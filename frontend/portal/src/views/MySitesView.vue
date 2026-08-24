<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Spinner, EmptyState } from "@kodlyft/ui";
import type { CustomerSiteSummary } from "@kodlyft/api";
import { installedBase } from "@/lib/api";
const rows = ref<CustomerSiteSummary[]>([]);
const loading = ref(true);
const error = ref("");
onMounted(async () => {
	try {
		rows.value = await installedBase.listSites({ limit: 200 });
	} catch {
		error.value = "Couldn't load your service sites.";
	} finally {
		loading.value = false;
	}
});
</script>
<template>
	<div>
		<p class="text-xs font-semibold uppercase tracking-[.14em] text-brand">Installed base</p>
		<h1 class="mt-1 text-3xl font-bold">My Sites</h1>
		<p class="mt-1 text-fg-muted">Service locations registered to your account.</p>
		<div v-if="loading" class="flex justify-center py-16"><Spinner /></div>
		<p v-else-if="error" class="mt-6 text-danger">{{ error }}</p>
		<EmptyState
			v-else-if="!rows.length"
			class="mt-6"
			title="No registered sites"
			description="Your service provider will add sites when equipment is delivered or installed."
		/>
		<div v-else class="mt-6 grid gap-3 sm:grid-cols-2">
			<article v-for="r in rows" :key="r.name" class="kl-glass rounded-2xl p-5">
				<div class="flex items-start justify-between gap-3">
					<div>
						<h2 class="font-bold">{{ r.site_name }}</h2>
						<p class="font-mono text-xs text-fg-muted">{{ r.site_code }}</p>
					</div>
					<span class="rounded-full bg-success/15 px-2.5 py-1 text-xs text-success">{{
						r.status
					}}</span>
				</div>
				<p class="mt-4 whitespace-pre-line text-sm text-fg-muted">
					{{ r.address_display || r.city || "Address not recorded" }}
				</p>
			</article>
		</div>
	</div>
</template>
