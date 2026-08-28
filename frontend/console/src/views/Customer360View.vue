<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { KlButton, LinkField, PageHeader, Spinner } from "@digit/ui";
import { getCustomer360, searchLink } from "@/lib/fsm";
import { t } from "@/lib/i18n";

const props = defineProps<{ name?: string }>();
const customer = ref(props.name || "");
const data = ref<Record<string, unknown> | null>(null);
const loading = ref(false);
const error = ref("");
const rows = (key: string) =>
	(data.value?.[key] as Record<string, string | number | null>[] | undefined) || [];

async function load() {
	if (!customer.value) return;
	loading.value = true;
	error.value = "";
	try {
		data.value = await getCustomer360(customer.value);
	} catch {
		error.value = t("تعذر تحميل سياق العميل.", "Couldn't load customer context.");
	} finally {
		loading.value = false;
	}
}

onMounted(() => {
	if (customer.value) load();
});
</script>

<template>
	<div>
		<PageHeader
			eyebrow="ERPNext Customer"
			:title="t('خدمة العميل 360', 'Customer Service 360')"
			:subtitle="
				t(
					'المواقع والمعدات والعقود والصيانة والعمل والتجارة في سياق واحد',
					'Sites, equipment, contracts, maintenance, work and commercial context',
				)
			"
		/>
		<form class="mb-6 flex max-w-2xl items-end gap-3" @submit.prevent="load">
			<div class="flex-1">
				<LinkField
					v-model="customer"
					:label="t('العميل', 'Customer')"
					required
					:search="(q) => searchLink('Customer', q, 'customer_name')"
				/>
			</div>
			<KlButton type="submit">{{ t("عرض", "View") }}</KlButton>
		</form>
		<div v-if="loading" class="flex justify-center p-12"><Spinner /></div>
		<p v-else-if="error" class="text-danger">{{ error }}</p>
		<div v-else-if="data" class="grid gap-4 lg:grid-cols-2">
			<section
				v-for="section in [
					{ key: 'sites', label: t('المواقع', 'Sites'), route: '/sites/' },
					{ key: 'equipment', label: t('المعدات', 'Equipment'), route: '/equipment/' },
					{ key: 'jobs', label: t('أوامر العمل', 'Jobs'), route: '/jobs/' },
					{ key: 'contracts', label: t('العقود', 'Contracts'), route: '/contracts' },
					{
						key: 'maintenance_plans',
						label: t('خطط الصيانة', 'Maintenance plans'),
						route: '/maintenance',
					},
					{
						key: 'requests',
						label: t('طلبات الخدمة', 'Service requests'),
						route: '/requests/',
					},
				]"
				:key="section.key"
				class="rounded-2xl border border-border bg-bg p-5 shadow-card"
			>
				<h2 class="mb-3 font-semibold">
					{{ section.label }}
					<span class="text-muted">({{ rows(section.key).length }})</span>
				</h2>
				<div class="max-h-64 space-y-2 overflow-auto">
					<RouterLink
						v-for="row in rows(section.key).slice(0, 20)"
						:key="String(row.name)"
						:to="
							section.route.endsWith('/')
								? `${section.route}${row.name}`
								: section.route
						"
						class="flex items-center justify-between rounded-xl bg-white/3 p-3 text-sm hover:bg-white/6"
					>
						<span>{{
							row.site_name ||
							row.equipment_name ||
							row.plan_title ||
							row.subject ||
							row.contract_no ||
							row.name
						}}</span>
						<span class="text-xs text-muted">{{ row.status || "" }}</span>
					</RouterLink>
				</div>
			</section>
		</div>
	</div>
</template>
