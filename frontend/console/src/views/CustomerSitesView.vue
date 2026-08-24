<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { PageHeader, Spinner, EmptyState } from "@kodlyft/ui";
import type { CustomerSiteSummary } from "@kodlyft/api";
import { installedBase } from "@/lib/fsm";
import { t, lang } from "@/lib/i18n";

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
		error.value = t("تعذّر تحميل مواقع العملاء.", "Couldn't load customer sites.");
	} finally {
		loading.value = false;
	}
});
</script>

<template>
	<div>
		<PageHeader
			:eyebrow="t('العملاء والمعدات', 'Customers & Equipment')"
			:title="t('مواقع العملاء', 'Customer Sites')"
			:subtitle="t(`${filtered.length} موقع خدمة`, `${filtered.length} service locations`)"
		/>
		<div class="mb-4 flex flex-wrap gap-3">
			<input
				v-model="search"
				:aria-label="t('بحث في المواقع', 'Search sites')"
				type="search"
				:placeholder="
					t(
						'ابحث بالموقع أو الرمز أو العميل أو المدينة',
						'Search site, code, customer or city',
					)
				"
				class="min-w-64 flex-1 rounded-xl border border-border bg-bg px-3.5 py-2.5"
			/>
			<select
				v-model="status"
				:aria-label="t('حالة الموقع', 'Site status')"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			>
				<option value="">{{ t("كل الحالات", "All statuses") }}</option>
				<option value="Active">{{ t("نشط", "Active") }}</option>
				<option value="Inactive">{{ t("غير نشط", "Inactive") }}</option>
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
			:title="t('لا توجد مواقع', 'No customer sites')"
			:description="
				t(
					'أنشئ موقع خدمة عبر أمر الموقع المُدار.',
					'Create a service site through the managed site command.',
				)
			"
		/>
		<div v-else class="overflow-hidden rounded-2xl border border-border bg-bg shadow-card">
			<table
				class="w-full text-sm"
				:class="{ 'text-right': lang === 'ar', 'text-left': lang !== 'ar' }"
			>
				<thead class="border-b border-border text-fg-muted">
					<tr>
						<th class="px-4 py-3">{{ t("الموقع", "Site") }}</th>
						<th class="px-4 py-3">{{ t("العميل", "Customer") }}</th>
						<th class="px-4 py-3">{{ t("المدينة", "City") }}</th>
						<th class="px-4 py-3">{{ t("الحالة", "Status") }}</th>
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
								>{{
									row.status === "Active"
										? t("نشط", "Active")
										: t("غير نشط", "Inactive")
								}}</span
							>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>
