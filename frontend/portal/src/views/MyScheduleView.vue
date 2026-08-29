<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { Spinner, formatDate, locale, statusLabel, t } from "@digit/ui";
import { getMyPortalHub, type PortalHub } from "@/lib/api";

const hub = ref<PortalHub | null>(null);
const loading = ref(true);
const error = ref("");
const mode = ref<"calendar" | "list">("calendar");
const cursor = ref(new Date());
const month = computed(() => new Date(cursor.value.getFullYear(), cursor.value.getMonth(), 1));
const cells = computed(() => {
	const first = month.value;
	const offset = (first.getDay() + 6) % 7;
	const start = new Date(first);
	start.setDate(first.getDate() - offset);
	return Array.from({ length: 42 }, (_, index) => {
		const date = new Date(start);
		date.setDate(start.getDate() + index);
		return date;
	});
});
const iso = (date: Date) => date.toISOString().slice(0, 10);
const events = (date: Date) =>
	(hub.value?.calendar || []).filter((event) => String(event.start).slice(0, 10) === iso(date));
const monthLabel = computed(() =>
	new Intl.DateTimeFormat(locale.value === "ar" ? "ar-SA" : "en-GB", {
		month: "long",
		year: "numeric",
	}).format(month.value),
);
function move(value: number) {
	cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + value, 1);
}

onMounted(async () => {
	try {
		hub.value = await getMyPortalHub();
	} catch {
		error.value = t("تعذر تحميل جدول الصيانة.", "Couldn't load your maintenance schedule.");
	} finally {
		loading.value = false;
	}
});
</script>

<template>
	<div class="space-y-6">
		<header class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<p class="text-xs font-semibold uppercase tracking-[0.14em] text-brand">
					{{ t("مواعيدي", "My appointments") }}
				</p>
				<h1 class="mt-1 text-3xl font-bold text-cmd-fg">
					{{ t("جدول الصيانة والزيارات", "Maintenance & visits schedule") }}
				</h1>
				<p class="mt-2 text-sm text-cmd-fg-muted">
					{{
						t(
							"تعرف على الموعد والمهمة والموقع والفريق المسند من شاشة واحدة.",
							"See the appointment, task, site and assigned team in one place.",
						)
					}}
				</p>
			</div>
			<RouterLink
				to="/"
				class="kl-grad-brand rounded-xl px-4 py-2.5 text-sm font-semibold text-white"
				>{{ t("طلب خدمة جديدة", "Request a service") }}</RouterLink
			>
		</header>
		<div v-if="loading" class="flex justify-center py-20"><Spinner /></div>
		<p v-else-if="error" class="rounded-xl bg-danger/10 p-4 text-danger">{{ error }}</p>
		<template v-else-if="hub">
			<div class="kl-glass flex flex-wrap items-center justify-between gap-3 rounded-2xl p-3">
				<div class="flex items-center gap-2">
					<button class="rounded-lg border border-cmd-border px-3 py-2" @click="move(-1)">
						‹</button
					><strong class="min-w-36 text-center">{{ monthLabel }}</strong
					><button class="rounded-lg border border-cmd-border px-3 py-2" @click="move(1)">
						›
					</button>
				</div>
				<div class="flex rounded-xl bg-white/5 p-1">
					<button
						class="rounded-lg px-3 py-2 text-sm"
						:class="mode === 'calendar' ? 'bg-brand text-white' : 'text-cmd-fg-muted'"
						@click="mode = 'calendar'"
					>
						{{ t("تقويم", "Calendar") }}</button
					><button
						class="rounded-lg px-3 py-2 text-sm"
						:class="mode === 'list' ? 'bg-brand text-white' : 'text-cmd-fg-muted'"
						@click="mode = 'list'"
					>
						{{ t("قائمة المواعيد", "Agenda") }}
					</button>
				</div>
			</div>
			<div v-if="mode === 'calendar'" class="overflow-x-auto">
				<div class="min-w-[760px]">
					<div
						class="mb-2 grid grid-cols-7 text-center text-xs font-semibold text-cmd-fg-muted"
					>
						<span
							v-for="name in [
								t('الاثنين', 'Mon'),
								t('الثلاثاء', 'Tue'),
								t('الأربعاء', 'Wed'),
								t('الخميس', 'Thu'),
								t('الجمعة', 'Fri'),
								t('السبت', 'Sat'),
								t('الأحد', 'Sun'),
							]"
							:key="name"
							>{{ name }}</span
						>
					</div>
					<div
						class="grid grid-cols-7 overflow-hidden rounded-2xl border border-cmd-border"
					>
						<div
							v-for="day in cells"
							:key="iso(day)"
							class="min-h-28 border-b border-e border-cmd-border p-2"
							:class="day.getMonth() !== month.getMonth() ? 'opacity-40' : ''"
						>
							<span class="text-xs font-semibold">{{ day.getDate() }}</span>
							<div
								v-for="event in events(day)"
								:key="event.name"
								class="mt-1 rounded-lg p-2 text-xs"
								:class="
									event.type === 'visit'
										? 'bg-brand/10 text-brand'
										: 'bg-warning/10 text-cmd-fg'
								"
							>
								<RouterLink
									v-if="event.service_job"
									:to="`/track/${event.service_job}`"
									class="font-semibold"
									>{{ event.title }}</RouterLink
								><strong v-else>{{ event.title }}</strong>
								<p class="mt-0.5 truncate opacity-75">
									{{ event.site || event.equipment }}
								</p>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div v-else class="space-y-3">
				<article
					v-for="event in hub.calendar"
					:key="event.name"
					class="kl-glass flex flex-wrap items-center justify-between gap-4 rounded-2xl p-4"
				>
					<div class="flex items-center gap-4">
						<div class="rounded-xl bg-brand/10 px-4 py-3 text-center text-brand">
							<strong class="block text-lg">{{
								new Date(String(event.start).replace(" ", "T")).getDate()
							}}</strong
							><span class="text-xs">{{ formatDate(event.start, true) }}</span>
						</div>
						<div>
							<RouterLink
								v-if="event.service_job"
								:to="`/track/${event.service_job}`"
								class="font-bold text-cmd-fg"
								>{{ statusLabel(event.title) }}</RouterLink
							><strong v-else class="text-cmd-fg">{{
								statusLabel(event.title)
							}}</strong>
							<p class="mt-1 text-sm text-cmd-fg-muted">
								{{ event.site || event.equipment || "—" }}
							</p>
							<p
								v-if="event.team || event.technician"
								class="mt-1 text-xs text-cmd-fg-muted"
							>
								{{ event.team || event.technician }}
							</p>
						</div>
					</div>
					<span
						class="rounded-full bg-brand/10 px-3 py-1 text-xs font-medium text-brand"
						>{{ statusLabel(event.status) }}</span
					>
				</article>
				<p
					v-if="!hub.calendar.length"
					class="kl-glass rounded-2xl p-10 text-center text-cmd-fg-muted"
				>
					{{
						t(
							"لا توجد مواعيد صيانة أو زيارات حالياً.",
							"No maintenance or visit appointments yet.",
						)
					}}
				</p>
			</div>
		</template>
	</div>
</template>
