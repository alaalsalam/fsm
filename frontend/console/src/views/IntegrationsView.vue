<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { PageHeader, Spinner } from "@digit/ui";
import {
	generateApiKeys,
	listWebhooks,
	registerWebhook,
	type ApiKeys,
	type WebhookRow,
} from "@/lib/fsm";
import { t } from "@/lib/i18n";

const keys = ref<ApiKeys | null>(null);
const generating = ref(false);
const keyError = ref("");

async function genKeys() {
	generating.value = true;
	keyError.value = "";
	try {
		keys.value = await generateApiKeys();
	} catch (e) {
		keyError.value =
			(e as { message?: string })?.message ||
			t("تعذّر إنشاء المفاتيح.", "Couldn't generate keys.");
	} finally {
		generating.value = false;
	}
}

const webhooks = ref<WebhookRow[]>([]);
const newUrl = ref("");
const adding = ref(false);
const hookError = ref("");

async function loadWebhooks() {
	try {
		webhooks.value = await listWebhooks();
	} catch {
		webhooks.value = [];
	}
}

async function addWebhook() {
	const url = newUrl.value.trim();
	if (!url) return;
	adding.value = true;
	hookError.value = "";
	try {
		await registerWebhook(url);
		newUrl.value = "";
		await loadWebhooks();
	} catch (e) {
		hookError.value =
			(e as { message?: string })?.message ||
			t("تعذّر تسجيل الويب هوك.", "Couldn't register webhook.");
	} finally {
		adding.value = false;
	}
}

const endpoints = computed(() => [
	{
		method: "POST",
		path: "/api/method/fsm.integrations.create_job",
		desc: t(
			"إنشاء أمر خدمة (customer, service_type, items…)",
			"Create a job (customer, service_type, items…)",
		),
	},
	{
		method: "GET",
		path: "/api/method/fsm.integrations.get_job_status",
		desc: t("الاستعلام عن حالة أمر الخدمة (job)", "Poll a job's status (job)"),
	},
	{
		method: "GET",
		path: "/api/method/fsm.integrations.list_jobs",
		desc: t(
			"عرض أوامر الخدمة (status?, customer?, limit?)",
			"List jobs (status?, customer?, limit?)",
		),
	},
	{
		method: "POST",
		path: "/api/method/fsm.api.request_service",
		desc: t("استقبال طلبات الخدمة العامة", "Public service request intake"),
	},
]);

onMounted(loadWebhooks);
</script>

<template>
	<div>
		<PageHeader
			:eyebrow="t('الربط', 'Connect')"
			:title="t('التكاملات وواجهة البرمجة', 'Integrations & API')"
			:subtitle="t('مفاتيح API والويب هوك ونقاط النهاية', 'API keys, webhooks and endpoints')"
		/>

		<div class="space-y-6">
			<section
				class="rounded-2xl border border-border bg-bg p-4 shadow-card backdrop-blur-xl"
			>
				<div class="flex items-center justify-between">
					<div>
						<h2 class="text-lg font-bold">{{ t("مفاتيح API", "API keys") }}</h2>
						<p class="text-sm text-fg-muted">
							{{
								t(
									"أصدر مفتاحاً وسراً لنظام خارجي. يُعرض السر مرة واحدة فقط.",
									"Issue a key/secret for an external system. The secret is shown once.",
								)
							}}
						</p>
					</div>
					<button
						type="button"
						:disabled="generating"
						class="kl-grad-brand inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-e2 hover:brightness-110 disabled:opacity-60"
						@click="genKeys"
					>
						<Spinner v-if="generating" :size="14" />
						{{
							keys
								? t("إعادة الإنشاء", "Regenerate")
								: t("إنشاء المفاتيح", "Generate keys")
						}}
					</button>
				</div>
				<p v-if="keyError" class="mt-2 text-sm text-danger">{{ keyError }}</p>
				<div
					v-if="keys"
					class="mt-3 space-y-1 rounded-xl border border-border bg-white/5 p-3 font-mono text-xs"
				>
					<p><span class="text-fg-muted">api_key:</span> {{ keys.api_key }}</p>
					<p><span class="text-fg-muted">api_secret:</span> {{ keys.api_secret }}</p>
					<p class="break-all pt-1 text-fg-muted">
						Authorization: token {{ keys.api_key }}:{{ keys.api_secret }}
					</p>
				</div>
			</section>
			<section class="rounded-2xl border border-border bg-bg shadow-card backdrop-blur-xl">
				<h2 class="border-b border-border px-4 py-3 text-lg font-bold">
					{{ t("نقاط النهاية العامة", "Public API endpoints") }}
				</h2>
				<ul class="divide-y divide-border">
					<li v-for="e in endpoints" :key="e.path" class="px-4 py-2.5">
						<div class="flex items-center gap-2">
							<span
								class="rounded px-1.5 py-0.5 font-mono text-xs font-semibold"
								:class="
									e.method === 'GET'
										? 'bg-info/15 text-info'
										: 'bg-brand/15 text-brand'
								"
							>
								{{ e.method }}
							</span>
							<code class="font-mono text-xs text-fg">{{ e.path }}</code>
						</div>
						<p class="mt-0.5 text-xs text-fg-muted">{{ e.desc }}</p>
					</li>
				</ul>
			</section>
			<section
				class="rounded-2xl border border-border bg-bg p-4 shadow-card backdrop-blur-xl"
			>
				<h2 class="text-lg font-bold">{{ t("الويب هوك الصادرة", "Outbound webhooks") }}</h2>
				<p class="text-sm text-fg-muted">
					{{
						t(
							"إرسال تغييرات أمر الخدمة (POST) إلى رابط خارجي.",
							"POST Service Job changes to an external URL.",
						)
					}}
				</p>
				<div class="mt-3 flex gap-2">
					<input
						v-model="newUrl"
						:aria-label="t('رابط الويب هوك', 'Webhook URL')"
						placeholder="https://example.com/hooks/fsm"
						class="flex-1 rounded-lg border border-border bg-white/5 px-3 py-2 text-sm"
						@keydown.enter="addWebhook"
					/>
					<button
						type="button"
						:disabled="adding || !newUrl.trim()"
						class="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-fg hover:bg-bg-subtle disabled:opacity-50"
						@click="addWebhook"
					>
						<Spinner v-if="adding" :size="14" />
						{{ t("إضافة", "Add") }}
					</button>
				</div>
				<p v-if="hookError" class="mt-2 text-sm text-danger">{{ hookError }}</p>
				<ul v-if="webhooks.length" class="mt-3 divide-y divide-border">
					<li
						v-for="w in webhooks"
						:key="w.name"
						class="flex items-center justify-between py-2 text-sm"
					>
						<span class="truncate font-mono text-xs text-fg">{{ w.request_url }}</span>
						<span class="ml-3 shrink-0 text-xs text-fg-muted">
							{{ w.webhook_docevent }} ·
							{{ w.enabled ? t("مفعل", "on") : t("معطل", "off") }}
						</span>
					</li>
				</ul>
			</section>
		</div>
	</div>
</template>
