<script setup lang="ts">
import { ref } from "vue";
import { KlButton, LinkField, PageHeader, Spinner } from "@kodlyft/ui";
import { getAfterSalesSetup, searchLink } from "@/lib/fsm";
import { t } from "@/lib/i18n";
const deliveryNote = ref("");
const data = ref<Record<string, unknown> | null>(null);
const loading = ref(false);
const error = ref("");
async function load() {
	loading.value = true;
	error.value = "";
	try {
		data.value = await getAfterSalesSetup(deliveryNote.value);
	} catch {
		error.value = t(
			"تعذر فتح إعداد ما بعد البيع. تحقق من أن إشعار التسليم معتمد وضمن شركتك.",
			"Couldn't open after-sales setup. Confirm the Delivery Note is submitted and in your company.",
		);
	} finally {
		loading.value = false;
	}
}
</script>
<template>
	<div>
		<PageHeader
			:eyebrow="t('Delivery Note → Installed Base', 'Delivery Note → Installed Base')"
			:title="t('إعداد ما بعد البيع', 'After-sales setup')"
			:subtitle="
				t(
					'مسار واحد للمعدات والمواقع والعقود والصيانة الوقائية',
					'One path for equipment, sites, contracts, and preventive maintenance',
				)
			"
		/>
		<form
			class="mb-6 flex max-w-2xl items-end gap-3 rounded-2xl border border-border bg-bg p-5 shadow-card"
			@submit.prevent="load"
		>
			<div class="flex-1">
				<LinkField
					v-model="deliveryNote"
					:label="t('إشعار التسليم', 'Delivery Note')"
					required
					:search="(q) => searchLink('Delivery Note', q)"
				/>
			</div>
			<KlButton type="submit">{{ t("فتح", "Open") }}</KlButton>
		</form>
		<div v-if="loading" class="flex justify-center p-12"><Spinner /></div>
		<p
			v-else-if="error"
			class="rounded-xl border border-danger/30 bg-danger/10 p-4 text-danger"
		>
			{{ error }}
		</p>
		<div v-else-if="data" class="grid gap-4 md:grid-cols-2">
			<section
				v-for="key in ['delivery_note', 'readiness', 'next_action']"
				:key="key"
				class="rounded-2xl border border-border bg-bg p-5 shadow-card"
			>
				<h2 class="mb-3 font-semibold">{{ key.replace("_", " ") }}</h2>
				<pre class="overflow-auto whitespace-pre-wrap text-xs">{{
					JSON.stringify(data[key], null, 2)
				}}</pre>
			</section>
			<section class="rounded-2xl border border-border bg-bg p-5 shadow-card">
				<h2 class="mb-3 font-semibold">{{ t("النطاق", "Scope") }}</h2>
				<p>
					{{ t("المعدات", "Equipment") }}:
					{{ (data.equipment as unknown[])?.length || 0 }}
				</p>
				<p>{{ t("المواقع", "Sites") }}: {{ (data.sites as unknown[])?.length || 0 }}</p>
				<p>
					{{ t("العقود", "Contracts") }}: {{ (data.contracts as unknown[])?.length || 0 }}
				</p>
				<p>
					{{ t("خطط الصيانة", "Maintenance plans") }}:
					{{ (data.maintenance_plans as unknown[])?.length || 0 }}
				</p>
			</section>
		</div>
	</div>
</template>
