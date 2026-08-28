<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { Spinner, StatusPill } from "@digit/ui";
import { createJobFromRequest, getServiceRequest, type ServiceRequestDoc } from "@/lib/fsm";
import { t } from "@/lib/i18n";

const props = defineProps<{ name: string }>();
const router = useRouter();
const request = ref<ServiceRequestDoc>();
const loading = ref(true);
const busy = ref(false);
onMounted(async () => {
	try {
		request.value = await getServiceRequest(props.name);
	} finally {
		loading.value = false;
	}
});
async function convert() {
	busy.value = true;
	try {
		const job = await createJobFromRequest(props.name, crypto.randomUUID());
		router.push(`/jobs/${job.name}`);
	} finally {
		busy.value = false;
	}
}
</script>
<template>
	<main class="p-4 sm:p-6" data-testid="service-request-detail">
		<Spinner v-if="loading" :size="28" /><template v-else-if="request"
			><div class="flex flex-wrap items-center justify-between gap-3">
				<div>
					<p class="text-sm text-cmd-fg-muted">{{ request.name }}</p>
					<h1 class="text-2xl font-bold text-cmd-fg">{{ request.subject }}</h1>
				</div>
				<StatusPill :status="request.status" />
			</div>
			<p class="mt-4 text-cmd-fg-muted">{{ request.description }}</p>
			<button
				v-if="['Open', 'Triaged', 'Converted'].includes(request.status)"
				class="kl-grad-brand mt-5 rounded-xl px-4 py-2 font-semibold text-white"
				:disabled="busy"
				@click="convert"
			>
				{{ t("إنشاء أمر خدمة", "Create Service Job") }}
			</button>
			<section class="mt-8">
				<h2 class="text-lg font-bold text-cmd-fg">
					{{ t("أوامر الخدمة المرتبطة", "Linked Service Jobs") }}
				</h2>
				<div class="mt-3 space-y-2">
					<RouterLink
						v-for="job in request.service_jobs"
						:key="job.name"
						:to="`/jobs/${job.name}`"
						class="kl-glass flex justify-between rounded-xl p-3"
						><span>{{ job.name }}</span
						><StatusPill :status="job.status"
					/></RouterLink>
					<p v-if="!request.service_jobs.length" class="text-sm text-cmd-fg-muted">
						{{ t("لا توجد أوامر عمل حتى الآن.", "No jobs yet.") }}
					</p>
				</div>
			</section></template
		>
	</main>
</template>
