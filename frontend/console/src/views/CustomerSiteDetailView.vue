<script setup lang="ts">
import { onMounted, ref } from "vue";
import { PageHeader, Spinner } from "@digit/ui";
import type { CustomerSiteDetail } from "@digit/api";
import { installedBase } from "@/lib/fsm";
import { t } from "@/lib/i18n";

const props = defineProps<{ name: string }>();
const site = ref<CustomerSiteDetail>();
const loading = ref(true);
const error = ref("");
onMounted(async () => {
	try {
		site.value = await installedBase.getSite(props.name);
	} catch {
		error.value = t("تعذّر تحميل موقع العميل هذا.", "Couldn't load this customer site.");
	} finally {
		loading.value = false;
	}
});
</script>
<template>
	<div>
		<PageHeader
			:eyebrow="t('موقع العميل', 'Customer Site')"
			:title="site?.site_name || name"
			:subtitle="site?.customer"
		/>
		<div v-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>
		<p v-else-if="error" class="text-danger">{{ error }}</p>
		<div v-else-if="site" class="space-y-4">
			<div class="grid gap-3 sm:grid-cols-3">
				<div class="kl-glass rounded-2xl p-4">
					<p class="text-xs text-fg-muted">{{ t("المعدات", "Equipment") }}</p>
					<p class="text-3xl font-bold">{{ site.equipment_count }}</p>
				</div>
				<div class="kl-glass rounded-2xl p-4">
					<p class="text-xs text-fg-muted">{{ t("نشط", "Active") }}</p>
					<p class="text-3xl font-bold text-success">{{ site.active_equipment }}</p>
				</div>
				<div class="kl-glass rounded-2xl p-4">
					<p class="text-xs text-fg-muted">{{ t("الحالة", "Status") }}</p>
					<p class="text-xl font-bold">{{ site.status }}</p>
				</div>
			</div>
			<section class="kl-glass rounded-2xl p-5">
				<h2 class="font-bold">{{ t("الموقع والتواصل", "Location & contact") }}</h2>
				<dl class="mt-3 grid gap-3 sm:grid-cols-2">
					<div>
						<dt class="text-xs text-fg-muted">{{ t("العنوان", "Address") }}</dt>
						<dd class="whitespace-pre-line">{{ site.address_display || "—" }}</dd>
					</div>
					<div>
						<dt class="text-xs text-fg-muted">{{ t("جهة الاتصال", "Contact") }}</dt>
						<dd>
							{{ site.primary_contact || "—" }}<br />{{ site.contact_phone }}
							{{ site.contact_email }}
						</dd>
					</div>
					<div>
						<dt class="text-xs text-fg-muted">{{ t("الإحداثيات", "Coordinates") }}</dt>
						<dd>{{ site.latitude ?? "—" }}, {{ site.longitude ?? "—" }}</dd>
					</div>
					<div>
						<dt class="text-xs text-fg-muted">
							{{ t("ساعات العمل", "Working hours") }}
						</dt>
						<dd>{{ site.working_hours || "—" }}</dd>
					</div>
				</dl>
			</section>
			<section class="kl-glass rounded-2xl p-5">
				<h2 class="font-bold">{{ t("أعمال الخدمة المرتبطة", "Linked service work") }}</h2>
				<div class="mt-3 grid gap-4 md:grid-cols-2">
					<div>
						<h3 class="text-sm text-fg-muted">{{ t("الطلبات", "Requests") }}</h3>
						<p v-if="!site.service_requests.length" class="mt-2 text-sm text-fg-muted">
							{{ t("لا شيء", "None") }}
						</p>
						<RouterLink
							v-for="r in site.service_requests"
							:key="r.name"
							:to="`/requests/${r.name}`"
							class="mt-2 block rounded-lg border border-border p-3"
							>{{ r.subject }} · {{ r.status }}</RouterLink
						>
					</div>
					<div>
						<h3 class="text-sm text-fg-muted">{{ t("أوامر العمل", "Jobs") }}</h3>
						<p v-if="!site.service_jobs.length" class="mt-2 text-sm text-fg-muted">
							{{ t("لا شيء", "None") }}
						</p>
						<RouterLink
							v-for="j in site.service_jobs"
							:key="j.name"
							:to="`/jobs/${j.name}`"
							class="mt-2 block rounded-lg border border-border p-3"
							>{{ j.name }} · {{ j.status }}</RouterLink
						>
					</div>
				</div>
			</section>
		</div>
	</div>
</template>
