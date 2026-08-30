<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { lang, t } from "@/lib/i18n";

export interface CalendarItem {
	key: string;
	date: string;
	label: string;
	sublabel?: string;
	status?: string;
	to?: string;
}

const props = defineProps<{ items: CalendarItem[]; initialDate?: string }>();
const emit = defineEmits<{ "range-change": [range: { from: string; to: string }] }>();

const pad = (n: number) => String(n).padStart(2, "0");
const iso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

function parseInitial(value?: string) {
	const d = value ? new Date(value.slice(0, 10) + "T00:00:00") : new Date();
	return Number.isNaN(d.getTime()) ? new Date() : d;
}

const initial = parseInitial(props.initialDate);
const cursor = ref(new Date(initial.getFullYear(), initial.getMonth(), 1));
const today = iso(new Date());

// Week always starts Saturday (Saudi work week). getDay(): Sat=6 → offset (day+1)%7.
const gridStart = computed(() => {
	const d = new Date(cursor.value);
	d.setDate(d.getDate() - ((d.getDay() + 1) % 7));
	return d;
});
const gridEnd = computed(() => {
	const last = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + 1, 0);
	last.setDate(last.getDate() + ((5 - last.getDay() + 7) % 7));
	return last;
});

interface DayCell {
	date: string;
	day: number;
	inMonth: boolean;
	isToday: boolean;
	items: CalendarItem[];
}

const itemsByDate = computed(() => {
	const map = new Map<string, CalendarItem[]>();
	for (const item of props.items) {
		const key = item.date.slice(0, 10);
		const list = map.get(key);
		if (list) list.push(item);
		else map.set(key, [item]);
	}
	return map;
});

const cells = computed<DayCell[]>(() => {
	const out: DayCell[] = [];
	const end = gridEnd.value;
	for (const d = new Date(gridStart.value); d <= end; d.setDate(d.getDate() + 1)) {
		const key = iso(d);
		out.push({
			date: key,
			day: d.getDate(),
			inMonth: d.getMonth() === cursor.value.getMonth(),
			isToday: key === today,
			items: itemsByDate.value.get(key) ?? [],
		});
	}
	return out;
});

const agendaDays = computed(() => cells.value.filter((c) => c.inMonth && c.items.length > 0));

// ar-SA defaults to the Hijri calendar — force Gregorian to match the JS Date grid.
const monthFmt = computed(
	() =>
		new Intl.DateTimeFormat(lang.value === "ar" ? "ar-u-ca-gregory" : "en-GB", {
			month: "long",
			year: "numeric",
		}),
);
const dayFmt = computed(
	() =>
		new Intl.DateTimeFormat(lang.value === "ar" ? "ar-u-ca-gregory" : "en-GB", {
			weekday: "long",
			day: "numeric",
			month: "long",
		}),
);
const title = computed(() => monthFmt.value.format(cursor.value));
const agendaLabel = (date: string) => dayFmt.value.format(new Date(date + "T00:00:00"));

const weekdays = computed(() => [
	t("السبت", "Sat"),
	t("الأحد", "Sun"),
	t("الاثنين", "Mon"),
	t("الثلاثاء", "Tue"),
	t("الأربعاء", "Wed"),
	t("الخميس", "Thu"),
	t("الجمعة", "Fri"),
]);

const prevChar = computed(() => (lang.value === "ar" ? "›" : "‹"));
const nextChar = computed(() => (lang.value === "ar" ? "‹" : "›"));

function shiftMonth(delta: number) {
	cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1);
}
function goToday() {
	const now = new Date();
	cursor.value = new Date(now.getFullYear(), now.getMonth(), 1);
}

function emitRange() {
	emit("range-change", { from: iso(gridStart.value), to: iso(gridEnd.value) });
}

watch(cursor, emitRange);
onMounted(emitRange);

type Tone = "success" | "warning" | "danger" | "info" | "neutral";

const STATUS_TONE: Record<string, Tone> = {
	Completed: "success",
	Converted: "success",
	Released: "success",
	"In Progress": "info",
	"Checked In": "info",
	"Checked Out": "info",
	Triaged: "info",
	Dispatched: "warning",
	"En Route": "warning",
	"On Hold": "warning",
	Due: "warning",
	Open: "warning",
	Cancelled: "danger",
	Skipped: "danger",
	Overdue: "danger",
};

// Full literal class strings so Tailwind's scanner detects them.
const CHIP_CLASS: Record<Tone, string> = {
	success: "border-s-success bg-success/10",
	info: "border-s-info bg-info/10",
	warning: "border-s-warning bg-warning/10",
	danger: "border-s-danger bg-danger/10",
	neutral: "border-s-fg-muted bg-fg-muted/10",
};

const chipClass = (status?: string) => CHIP_CLASS[(status && STATUS_TONE[status]) || "neutral"];

const MAX_CHIPS = 3;
</script>

<template>
	<div class="overflow-hidden rounded-2xl border border-border bg-bg shadow-card">
		<header
			class="flex flex-wrap items-center justify-between gap-3 border-b border-border p-4"
		>
			<h2 class="text-lg font-bold">{{ title }}</h2>
			<div class="flex items-center gap-1.5">
				<button
					type="button"
					:aria-label="t('الشهر السابق', 'Previous month')"
					class="rounded-lg border border-border px-3 py-1.5 text-lg leading-none hover:bg-primary/5"
					@click="shiftMonth(-1)"
				>
					{{ prevChar }}
				</button>
				<button
					type="button"
					class="rounded-lg border border-border px-3 py-1.5 text-sm font-medium hover:bg-primary/5"
					@click="goToday"
				>
					{{ t("اليوم", "Today") }}
				</button>
				<button
					type="button"
					:aria-label="t('الشهر التالي', 'Next month')"
					class="rounded-lg border border-border px-3 py-1.5 text-lg leading-none hover:bg-primary/5"
					@click="shiftMonth(1)"
				>
					{{ nextChar }}
				</button>
			</div>
		</header>

		<!-- Desktop: month grid -->
		<div class="hidden md:block">
			<div
				class="grid grid-cols-7 border-b border-border text-center text-xs font-semibold text-fg-muted"
			>
				<div v-for="day in weekdays" :key="day" class="py-2">{{ day }}</div>
			</div>
			<div class="grid grid-cols-7 gap-px bg-border">
				<div
					v-for="cell in cells"
					:key="cell.date"
					class="min-h-28 bg-bg p-1.5"
					:class="{ 'bg-primary/5': cell.isToday }"
				>
					<div class="mb-1 flex justify-end">
						<span
							class="inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold"
							:class="
								cell.isToday
									? 'bg-primary text-white'
									: cell.inMonth
										? 'text-fg-muted'
										: 'text-fg-muted/40'
							"
						>
							{{ cell.day }}
						</span>
					</div>
					<div class="flex flex-col gap-1" :class="{ 'opacity-50': !cell.inMonth }">
						<component
							:is="item.to ? RouterLink : 'div'"
							v-for="item in cell.items.slice(0, MAX_CHIPS)"
							:key="item.key"
							:to="item.to"
							class="block rounded-md border-s-2 px-1.5 py-1 text-xs"
							:class="[chipClass(item.status), item.to ? 'hover:bg-primary/10' : '']"
						>
							<p class="truncate font-medium">{{ item.label }}</p>
							<p v-if="item.sublabel" class="truncate text-[11px] text-fg-muted">
								{{ item.sublabel }}
							</p>
						</component>
						<p
							v-if="cell.items.length > MAX_CHIPS"
							class="px-1.5 text-[11px] font-medium text-fg-muted"
						>
							+{{ cell.items.length - MAX_CHIPS }} {{ t("أخرى", "more") }}
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Mobile: stacked agenda -->
		<div class="md:hidden">
			<p v-if="!agendaDays.length" class="p-6 text-center text-sm text-fg-muted">
				{{ t("لا توجد عناصر في هذا الشهر", "Nothing scheduled this month") }}
			</p>
			<div v-else class="divide-y divide-border">
				<section v-for="day in agendaDays" :key="day.date" class="p-3">
					<h3
						class="mb-2 text-sm font-semibold"
						:class="day.isToday ? 'text-primary' : 'text-fg-muted'"
					>
						{{ agendaLabel(day.date) }}
						<span v-if="day.isToday">· {{ t("اليوم", "Today") }}</span>
					</h3>
					<div class="flex flex-col gap-1.5">
						<component
							:is="item.to ? RouterLink : 'div'"
							v-for="item in day.items"
							:key="item.key"
							:to="item.to"
							class="block rounded-md border-s-2 px-2.5 py-1.5 text-sm"
							:class="chipClass(item.status)"
						>
							<p class="truncate font-medium">{{ item.label }}</p>
							<p v-if="item.sublabel" class="truncate text-xs text-fg-muted">
								{{ item.sublabel }}
							</p>
						</component>
					</div>
				</section>
			</div>
		</div>
	</div>
</template>
