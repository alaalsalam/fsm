<script setup lang="ts">
import { ref, onMounted } from "vue";
import { StatusPill, formatDate, statusLabel, t } from "@digit/ui";
import {
	getJobMessages,
	postJobMessage,
	getJobFeedback,
	submitJobFeedback,
	type JobMessage,
	type JobFeedback,
} from "@/lib/api";

const props = defineProps<{ job: string }>();

const timeline = [
	{ ar: "تم استلام الطلب", en: "Request received", done: true },
	{ ar: "تم تأكيد طلب الخدمة", en: "Service request confirmed", done: true },
	{ ar: "الفني في الطريق", en: "Technician on the way", done: true, active: true },
	{ ar: "اكتمل العمل", en: "Job completed", done: false },
];

const messages = ref<JobMessage[]>([]);
const newMessage = ref("");
const sending = ref(false);

async function loadMessages() {
	try {
		messages.value = await getJobMessages(props.job);
	} catch {
		messages.value = [];
	}
}

async function send() {
	const text = newMessage.value.trim();
	if (!text) return;
	sending.value = true;
	try {
		await postJobMessage(props.job, text);
		newMessage.value = "";
		await loadMessages();
	} finally {
		sending.value = false;
	}
}

const datetime = (iso: string) => formatDate(iso, true);

const feedback = ref<JobFeedback | null>(null);
const stars = ref(0);
const comments = ref("");
const submitting = ref(false);
const feedbackError = ref("");

async function loadFeedback() {
	try {
		feedback.value = await getJobFeedback(props.job);
	} catch {
		feedback.value = null;
	}
}

async function rate() {
	if (!stars.value) return;
	submitting.value = true;
	feedbackError.value = "";
	try {
		await submitJobFeedback(props.job, stars.value, comments.value || undefined);
		await loadFeedback();
	} catch (e) {
		feedbackError.value =
			(e as { message?: string })?.message ||
			t("تعذر إرسال تقييمك.", "Couldn't submit your rating.");
	} finally {
		submitting.value = false;
	}
}

onMounted(() => {
	loadMessages();
	loadFeedback();
});
</script>

<template>
	<div class="space-y-6">
		<div class="flex items-center justify-between gap-3">
			<div>
				<h1 class="text-2xl font-bold text-cmd-fg">
					{{ t("الفني في الطريق", "Your technician is on the way") }}
				</h1>
				<p class="mt-0.5 font-mono text-sm text-cmd-fg-muted">{{ job }}</p>
			</div>
			<StatusPill status="In Progress" :label="statusLabel('In Progress')" />
		</div>

		<div
			class="flex h-48 items-center justify-center rounded-2xl border border-cmd-border bg-white/3 text-cmd-fg-muted"
		>
			{{ t("الخريطة المباشرة", "Live map") }}
		</div>

		<ol class="relative ms-2 space-y-5 border-s border-cmd-border ps-6">
			<li v-for="(step, i) in timeline" :key="i" class="relative">
				<span
					class="absolute -start-7.75 flex size-4 items-center justify-center rounded-full"
					:class="step.done ? 'bg-brand' : 'border border-cmd-border bg-cmd-bg'"
				>
					<span
						v-if="step.active"
						class="absolute size-4 animate-ping rounded-full bg-brand/40"
					/>
				</span>
				<p
					class="text-sm"
					:class="step.active ? 'font-medium text-cmd-fg' : 'text-cmd-fg-muted'"
				>
					{{ t(step.ar, step.en) }}
				</p>
			</li>
		</ol>
		<section class="kl-glass rounded-2xl p-4">
			<h2 class="mb-3 text-lg font-bold text-cmd-fg">{{ t("الرسائل", "Messages") }}</h2>
			<div class="max-h-64 space-y-3 overflow-y-auto">
				<p v-if="messages.length === 0" class="text-sm text-cmd-fg-muted">
					{{
						t(
							"لا توجد رسائل بعد. أرسل ملاحظة إلى الفني أو فريقنا.",
							"No messages yet. Send a note to your technician or our team.",
						)
					}}
				</p>
				<div v-for="m in messages" :key="m.name" class="text-sm">
					<p class="text-xs text-cmd-fg-muted">
						{{ m.author_role
						}}<span v-if="m.author_name"> · {{ m.author_name }}</span> ·
						{{ datetime(m.creation) }}
					</p>
					<p class="mt-0.5 whitespace-pre-line text-cmd-fg">{{ m.message }}</p>
				</div>
			</div>
			<div class="mt-3 flex gap-2">
				<input
					v-model="newMessage"
					:placeholder="t('اكتب رسالة…', 'Write a message…')"
					class="flex-1 rounded-lg border border-cmd-border bg-white/5 px-3 py-2 text-sm text-cmd-fg"
					@keydown.enter="send"
				/>
				<button
					type="button"
					:disabled="sending || !newMessage.trim()"
					class="kl-grad-brand rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
					@click="send"
				>
					{{ t("إرسال", "Send") }}
				</button>
			</div>
		</section>
		<section class="kl-glass rounded-2xl p-4">
			<h2 class="mb-3 text-lg font-bold text-cmd-fg">
				{{ t("قيّم الخدمة", "Rate your service") }}
			</h2>
			<div v-if="feedback">
				<p class="text-2xl text-warning">
					{{ "★".repeat(feedback.rating)
					}}<span class="text-cmd-fg-muted">{{ "★".repeat(5 - feedback.rating) }}</span>
				</p>
				<p v-if="feedback.comments" class="mt-1 text-sm text-cmd-fg">
					“{{ feedback.comments }}”
				</p>
				<p class="mt-1 text-xs text-cmd-fg-muted">
					{{ t("شكرًا لتقييمك!", "Thanks for your feedback!") }}
				</p>
			</div>
			<div v-else>
				<div class="flex gap-1" role="radiogroup" :aria-label="t('التقييم', 'rating')">
					<button
						v-for="n in 5"
						:key="n"
						type="button"
						class="text-3xl transition-transform hover:scale-110"
						:class="n <= stars ? 'text-warning' : 'text-cmd-fg-muted'"
						:aria-label="t(`${n} نجمة`, `${n} star`)"
						@click="stars = n"
					>
						★
					</button>
				</div>
				<textarea
					v-model="comments"
					rows="2"
					:placeholder="
						t('أخبرنا عن تجربتك (اختياري)', 'Tell us about your experience (optional)')
					"
					class="mt-3 w-full rounded-lg border border-cmd-border bg-white/5 px-3 py-2 text-sm text-cmd-fg"
				/>
				<p v-if="feedbackError" class="mt-1 text-xs text-danger">{{ feedbackError }}</p>
				<button
					type="button"
					:disabled="submitting || !stars"
					class="kl-grad-brand mt-3 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
					@click="rate"
				>
					{{ t("إرسال التقييم", "Submit rating") }}
				</button>
			</div>
		</section>
	</div>
</template>
