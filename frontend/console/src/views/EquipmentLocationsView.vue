<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { PageHeader, Spinner } from "@kodlyft/ui";
import type { CustomerSiteSummary, EquipmentLocation } from "@kodlyft/api";
import { installedBase } from "@/lib/fsm";
import { t } from "@/lib/i18n";

const sites = ref<CustomerSiteSummary[]>([]);
const selected = ref("");
const rows = ref<EquipmentLocation[]>([]);
const loading = ref(true);
async function load() {
	rows.value = selected.value ? await installedBase.listLocations(selected.value) : [];
}
watch(selected, load);
onMounted(async () => {
	sites.value = await installedBase.listSites({ limit: 200 });
	selected.value = sites.value[0]?.name || "";
	loading.value = false;
});
</script>
<template>
	<div>
		<PageHeader
			:eyebrow="t('العملاء والمعدات', 'Customers & Equipment')"
			:title="t('مواضع المعدات', 'Equipment Locations')"
			:subtitle="
				t(
					'تسلسل هرمي للمبنى والطابق والمنطقة والغرفة',
					'Expandable building, floor, zone and room hierarchy',
				)
			"
		/><label class="mb-4 block text-sm text-fg-muted"
			>{{ t("موقع العميل", "Customer site")
			}}<select
				v-model="selected"
				class="mt-1 block w-full rounded-xl border border-border bg-bg px-3.5 py-2.5"
			>
				<option value="">{{ t("اختر موقعاً", "Select a site") }}</option>
				<option v-for="s in sites" :key="s.name" :value="s.name">
					{{ s.site_name }} · {{ s.customer }}
				</option>
			</select></label
		>
		<div v-if="loading" class="flex justify-center py-16"><Spinner /></div>
		<div v-else class="space-y-2">
			<div v-for="r in rows" :key="r.name" class="kl-glass rounded-xl p-4">
				<p class="font-semibold">{{ r.location_name }}</p>
				<p class="text-xs text-fg-muted">
					{{ r.location_type }} · {{ r.location_code
					}}<span v-if="r.parent_location">
						· {{ t("أصل", "Parent") }} {{ r.parent_location }}</span
					>
				</p>
			</div>
			<p
				v-if="selected && !rows.length"
				class="rounded-xl border border-dashed border-border p-8 text-center text-fg-muted"
			>
				{{
					t(
						"لا توجد مواضع فرعية. يمكن ربط المعدات بالموقع الرئيسي مباشرةً.",
						"No sub-locations. Equipment can remain linked to the main site.",
					)
				}}
			</p>
		</div>
	</div>
</template>
