<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Spinner, EmptyState, statusLabel, t } from "@kodlyft/ui";
import type { InstalledEquipmentSummary } from "@kodlyft/api";
import { installedBase } from "@/lib/api";
const rows = ref<InstalledEquipmentSummary[]>([]);
const loading = ref(true);
const error = ref("");
onMounted(async () => {
	try {
		rows.value = await installedBase.listEquipment({ limit: 200 });
	} catch {
		error.value = t("تعذر تحميل معداتك.", "Couldn't load your equipment.");
	} finally {
		loading.value = false;
	}
});
</script>
<template>
	<div>
		<p class="text-xs font-semibold uppercase tracking-[.14em] text-brand">
			{{ t("قاعدة المعدات", "Installed base") }}
		</p>
		<h1 class="mt-1 text-3xl font-bold">{{ t("معداتي", "My Equipment") }}</h1>
		<p class="mt-1 text-fg-muted">
			{{
				t(
					"المنتجات المسلمة أو المركبة لحسابك.",
					"Products delivered or installed for your account.",
				)
			}}
		</p>
		<div v-if="loading" class="flex justify-center py-16"><Spinner /></div>
		<p v-else-if="error" class="mt-6 text-danger">{{ error }}</p>
		<EmptyState
			v-else-if="!rows.length"
			class="mt-6"
			:title="t('لا توجد معدات مسجلة', 'No registered equipment')"
			:description="
				t(
					'تظهر المعدات المؤهلة هنا بعد التسليم.',
					'Eligible equipment appears here after delivery provisioning.',
				)
			"
		/>
		<div v-else class="mt-6 space-y-3">
			<RouterLink
				v-for="r in rows"
				:key="r.name"
				:to="{ name: 'my-equipment-detail', params: { name: r.name } }"
				class="kl-glass flex items-center justify-between gap-4 rounded-2xl p-5 transition hover:-translate-y-0.5"
				><div class="min-w-0">
					<h2 class="truncate font-bold">{{ r.item_name || r.item_code }}</h2>
					<p class="font-mono text-xs text-fg-muted">
						{{ r.equipment_id }}<span v-if="r.serial_no"> · {{ r.serial_no }}</span>
					</p>
					<p class="mt-1 truncate text-sm text-fg-muted">
						{{ r.customer_site || t("موقع العميل الرئيسي", "Main customer location") }}
					</p>
				</div>
				<div class="text-end">
					<span class="rounded-full bg-brand/15 px-2.5 py-1 text-xs text-brand">{{
						statusLabel(r.status)
					}}</span>
					<p class="mt-2 text-xs text-fg-muted">
						{{ t("الضمان", "Warranty") }}: {{ statusLabel(r.warranty_status) }}
					</p>
				</div></RouterLink
			>
		</div>
	</div>
</template>
