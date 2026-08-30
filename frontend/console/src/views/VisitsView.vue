<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { EmptyState, PageHeader, Spinner, StatusPill, statusLabel, STATUS_TONE } from "@digit/ui";
import { listProcessVisits, type ProcessVisit } from "@/lib/fsm";
import MonthCalendar, { type CalendarItem } from "@/components/MonthCalendar.vue";
import { lang, t } from "@/lib/i18n";

type ViewMode = "table" | "cards" | "calendar";
const VIEW_KEY = "fsm-visits-view";

const route = useRoute();
const router = useRouter();

const rows = ref<ProcessVisit[]>([]);
const loading = ref(true);
const error = ref("");

const searchInput = ref("");
const search = ref("");
const statusFilter = ref("");
const techFilter = ref("");
const calendarRange = ref<{ from: string; to: string } | null>(null);

const storedView = typeof localStorage === "undefined" ? null : localStorage.getItem(VIEW_KEY);
const view = ref<ViewMode>(
	storedView === "table" || storedView === "cards" || storedView === "calendar"
		? storedView
		: "table",
);

let searchTimer = 0;
watch(searchInput, (value) => {
	window.clearTimeout(searchTimer);
	// 300ms debounce per project rule — no filtering on every keystroke.
	searchTimer = window.setTimeout(() => (search.value = value), 300);
});

const VIEWS: Array<{ key: ViewMode; label: () => string }> = [
	{ key: "table", label: () => t("جدول", "Table") },
	{ key: "cards", label: () => t("بطاقات", "Cards") },
	{ key: "calendar", label: () => t("تقويم", "Calendar") },
];

const showStatus = (s?: string) => (s ? statusLabel(s) : "—");
const timeOf = (s?: string) => (s && s.length >= 16 ? s.slice(11, 16) : "");
const dateOf = (s?: string) => (s ? s.slice(0, 10) : "");

const timeRange = (row: ProcessVisit) => {
	const start = timeOf(row.scheduled_start);
	if (!start) return "—";
	const end = timeOf(row.scheduled_end);
	return end ? `${start}–${end}` : start;
};

const filtered = computed(() => {
	const q = search.value.trim().toLowerCase();
	return rows.value.filter((row) => {
		const matchesSearch =
			!q ||
			`${row.name} ${row.service_job} ${row.customer_name || ""} ${row.primary_technician || ""} ${row.service_team || ""}`
				.toLowerCase()
				.includes(q);
		const matchesStatus = !statusFilter.value || row.status === statusFilter.value;
		const matchesTech = !techFilter.value || row.primary_technician === techFilter.value;
		return matchesSearch && matchesStatus && matchesTech;
	});
});

const statuses = computed(() => {
	const seen = new Set<string>();
	for (const row of rows.value) if (row.status) seen.add(row.status);
	return [...seen].sort();
});

const technicians = computed(() => {
	const seen = new Set<string>();
	for (const row of rows.value) if (row.primary_technician) seen.add(row.primary_technician);
	return [...seen].sort();
});

const DOT_CLASS: Record<string, string> = {
	success: "bg-success",
	warning: "bg-warning",
	danger: "bg-danger",
	info: "bg-info",
	neutral: "bg-fg-muted",
};
const statusDot = (status: string) =>
	DOT_CLASS[STATUS_TONE[status as keyof typeof STATUS_TONE] ?? "neutral"];

const statusCounts = computed(() =>
	statuses.value.map((status) => ({
		status,
		count: rows.value.filter((row) => row.status === status).length,
	})),
);

const isoDay = (offset: number) => {
	const d = new Date();
	d.setDate(d.getDate() + offset);
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

const dayLabel = (date: string) => {
	if (date === isoDay(0)) return t("اليوم", "Today");
	if (date === isoDay(1)) return t("غدًا", "Tomorrow");
	if (date === isoDay(-1)) return t("أمس", "Yesterday");
	// ar-SA defaults to the Hijri calendar — force Gregorian to match stored dates.
	return new Intl.DateTimeFormat(lang.value === "ar" ? "ar-u-ca-gregory" : "en-GB", {
		weekday: "long",
		day: "numeric",
		month: "long",
		year: "numeric",
	}).format(new Date(date + "T00:00:00"));
};

const groups = computed(() => {
	const byDate = new Map<string, ProcessVisit[]>();
	const unscheduled: ProcessVisit[] = [];
	const sorted = [...filtered.value].sort((a, b) =>
		(a.scheduled_start || "").localeCompare(b.scheduled_start || ""),
	);
	for (const row of sorted) {
		const key = dateOf(row.scheduled_start);
		if (!key) {
			unscheduled.push(row);
			continue;
		}
		const list = byDate.get(key);
		if (list) list.push(row);
		else byDate.set(key, [row]);
	}
	const out = [...byDate.entries()].map(([date, list]) => ({
		key: date,
		label: dayLabel(date),
		rows: list,
	}));
	if (unscheduled.length)
		out.push({ key: "unscheduled", label: t("غير مجدولة", "Unscheduled"), rows: unscheduled });
	return out;
});

const calendarItems = computed<CalendarItem[]>(() =>
	filtered.value
		.filter((row) => row.scheduled_start)
		.map((row) => ({
			key: row.name,
			date: row.scheduled_start as string,
			label: row.customer_name || row.service_job,
			sublabel:
				[timeOf(row.scheduled_start), row.primary_technician || row.service_team]
					.filter(Boolean)
					.join(" · ") || undefined,
			status: row.status,
			to: `/jobs/${row.service_job}`,
		})),
);

async function load() {
	loading.value = true;
	error.value = "";
	try {
		const params: Record<string, unknown> = { limit: 500 };
		if (typeof route.query.job === "string") params.job = route.query.job;
		if (view.value === "calendar" && calendarRange.value) {
			params.date_from = calendarRange.value.from;
			params.date_to = calendarRange.value.to;
		} else if (route.query.date_scope === "today") {
			const today = isoDay(0);
			params.date_from = today;
			params.date_to = today;
		}
		rows.value = await listProcessVisits(params);
	} catch {
		error.value = t("تعذر تحميل الزيارات.", "Couldn't load visits.");
	} finally {
		loading.value = false;
	}
}

function setView(mode: ViewMode) {
	view.value = mode;
	if (typeof localStorage !== "undefined") localStorage.setItem(VIEW_KEY, mode);
	// Calendar refetches via its own mount-time range-change; other views reload the default range.
	if (mode !== "calendar") {
		calendarRange.value = null;
		load();
	}
}

function onRangeChange(range: { from: string; to: string }) {
	calendarRange.value = range;
	load();
}

function openJob(job: string) {
	router.push(`/jobs/${job}`);
}

watch(() => route.fullPath, load);
onMounted(() => {
	if (view.value !== "calendar") load();
});
</script>

<template>
	<div>
		<PageHeader
			:eyebrow="t('التخطيط والتنفيذ', 'Planning and execution')"
			:title="t('الزيارات', 'Visits')"
			:subtitle="
				t('عرض موحد للجدول والتنفيذ الفعلي', 'One view for schedule and actual execution')
			"
		/>

		<!-- Summary chips -->
		<div v-if="rows.length" class="mb-4 flex flex-wrap gap-2">
			<span
				class="inline-flex items-center gap-2 rounded-full border border-border bg-bg px-3 py-1.5 text-sm font-medium"
			>
				{{ t("الإجمالي", "Total") }}
				<span class="font-bold tabular-nums">{{ rows.length }}</span>
			</span>
			<span
				v-for="item in statusCounts"
				:key="item.status"
				class="inline-flex items-center gap-2 rounded-full border border-border bg-bg px-3 py-1.5 text-sm"
			>
				<span class="h-2 w-2 rounded-full" :class="statusDot(item.status)" />
				{{ showStatus(item.status) }}
				<span class="font-bold tabular-nums">{{ item.count }}</span>
			</span>
		</div>

		<!-- Toolbar -->
		<div class="mb-4 flex flex-wrap items-center gap-3">
			<input
				v-model="searchInput"
				type="search"
				:aria-label="t('بحث في الزيارات', 'Search visits')"
				:placeholder="
					t(
						'ابحث بالزيارة أو الأمر أو العميل أو الفني',
						'Search visit, job, customer or technician',
					)
				"
				class="min-w-56 flex-1 rounded-xl border border-border bg-bg px-3.5 py-2.5 focus-visible:outline-none focus-visible:[box-shadow:var(--kl-elevation-focus)]"
			/>
			<select
				v-model="statusFilter"
				:aria-label="t('حالة الزيارة', 'Visit status')"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			>
				<option value="">{{ t("كل الحالات", "All statuses") }}</option>
				<option v-for="s in statuses" :key="s" :value="s">{{ showStatus(s) }}</option>
			</select>
			<select
				v-model="techFilter"
				:aria-label="t('الفني', 'Technician')"
				class="rounded-xl border border-border bg-bg px-3.5 py-2.5"
			>
				<option value="">{{ t("كل الفنيين", "All technicians") }}</option>
				<option v-for="tech in technicians" :key="tech" :value="tech">{{ tech }}</option>
			</select>
			<div class="flex rounded-xl bg-surface p-1">
				<button
					v-for="mode in VIEWS"
					:key="mode.key"
					type="button"
					class="rounded-lg px-3 py-2 text-sm font-medium"
					:class="view === mode.key ? 'bg-primary text-white' : 'text-muted'"
					@click="setView(mode.key)"
				>
					{{ mode.label() }}
				</button>
			</div>
		</div>

		<p
			v-if="error"
			class="mb-4 rounded-2xl border border-danger/30 bg-danger/10 p-4 text-danger"
		>
			{{ error }}
		</p>

		<!-- Calendar view stays mounted while refetching so month navigation state survives -->
		<div v-if="view === 'calendar'" class="relative">
			<div v-if="loading" class="absolute inset-0 z-20 flex items-start justify-center pt-16">
				<Spinner :size="28" />
			</div>
			<div :class="{ 'opacity-50': loading }">
				<MonthCalendar :items="calendarItems" @range-change="onRangeChange" />
			</div>
		</div>

		<div v-else-if="loading" class="flex justify-center py-16"><Spinner :size="28" /></div>

		<EmptyState
			v-else-if="!error && !filtered.length"
			:title="t('لا توجد زيارات مطابقة', 'No matching visits')"
			:description="
				t('حاول تعديل البحث أو الفلاتر.', 'Try adjusting your search or filters.')
			"
		/>

		<!-- Table view: grouped by day -->
		<div v-else-if="!error && view === 'table'" class="flex flex-col gap-5">
			<section v-for="group in groups" :key="group.key">
				<h3 class="sticky top-0 z-10 flex items-center gap-2 bg-bg py-2 text-sm font-bold">
					{{ group.label }}
					<span
						class="rounded-full bg-fg-muted/15 px-2 py-0.5 text-xs font-medium text-fg-muted tabular-nums"
						>{{ group.rows.length }}</span
					>
				</h3>
				<div class="overflow-x-auto rounded-2xl border border-border bg-bg shadow-card">
					<table
						class="w-full text-sm"
						:class="{ 'text-right': lang === 'ar', 'text-left': lang !== 'ar' }"
					>
						<thead class="border-b border-border text-fg-muted">
							<tr>
								<th class="px-4 py-3 font-medium">{{ t("الزيارة", "Visit") }}</th>
								<th class="px-4 py-3 font-medium">{{ t("الأمر", "Job") }}</th>
								<th class="px-4 py-3 font-medium">{{ t("العميل", "Customer") }}</th>
								<th class="px-4 py-3 font-medium">
									{{ t("نوع الخدمة", "Service type") }}
								</th>
								<th class="px-4 py-3 font-medium">
									{{ t("الفريق / الفني", "Team / technician") }}
								</th>
								<th class="px-4 py-3 font-medium">
									{{ t("المعدات", "Equipment") }}
								</th>
								<th class="px-4 py-3 font-medium">{{ t("الموعد", "Schedule") }}</th>
								<th class="px-4 py-3 font-medium">{{ t("الحالة", "Status") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in group.rows"
								:key="row.name"
								class="cursor-pointer border-b border-border/60 last:border-0 hover:bg-primary/5"
								@click="openJob(row.service_job)"
							>
								<td class="px-4 py-3">
									<p class="font-mono font-medium">{{ row.name }}</p>
									<p class="text-xs text-fg-muted">
										{{ t("رقم الزيارة", "Visit no.") }}
									</p>
								</td>
								<td class="px-4 py-3">
									<RouterLink
										:to="`/jobs/${row.service_job}`"
										class="font-mono text-primary hover:underline"
										@click.stop
										>{{ row.service_job }}</RouterLink
									>
								</td>
								<td class="px-4 py-3">{{ row.customer_name || "—" }}</td>
								<td class="px-4 py-3 text-fg-muted">
									{{ row.service_type || "—" }}
								</td>
								<td class="px-4 py-3 text-fg-muted">
									{{ row.service_team || row.primary_technician || "—" }}
								</td>
								<td class="px-4 py-3">
									<span
										class="rounded-full bg-fg-muted/15 px-2.5 py-1 text-xs font-medium tabular-nums"
										>{{ row.equipment_count }}</span
									>
								</td>
								<td class="px-4 py-3 tabular-nums" dir="ltr">
									{{ timeRange(row) }}
								</td>
								<td class="px-4 py-3"><StatusPill :status="row.status" /></td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>
		</div>

		<!-- Cards view -->
		<div v-else-if="!error" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			<article
				v-for="row in filtered"
				:key="row.name"
				class="cursor-pointer rounded-2xl border border-border bg-bg p-4 shadow-card transition-colors hover:border-primary/40"
				@click="openJob(row.service_job)"
			>
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0">
						<h3 class="truncate font-bold">{{ row.customer_name || "—" }}</h3>
						<p class="font-mono text-xs text-fg-muted">{{ row.name }}</p>
					</div>
					<StatusPill :status="row.status" />
				</div>
				<dl class="mt-3 flex flex-col gap-1.5 text-sm">
					<div class="flex justify-between gap-2">
						<dt class="text-fg-muted">{{ t("الموعد", "Schedule") }}</dt>
						<dd class="tabular-nums" dir="ltr">
							{{
								row.scheduled_start
									? `${dateOf(row.scheduled_start)} ${timeRange(row)}`
									: "—"
							}}
						</dd>
					</div>
					<div class="flex justify-between gap-2">
						<dt class="text-fg-muted">
							{{ t("الفريق / الفني", "Team / technician") }}
						</dt>
						<dd class="truncate">
							{{ row.service_team || row.primary_technician || "—" }}
						</dd>
					</div>
					<div class="flex justify-between gap-2">
						<dt class="text-fg-muted">{{ t("نوع الخدمة", "Service type") }}</dt>
						<dd class="truncate">{{ row.service_type || "—" }}</dd>
					</div>
					<div class="flex justify-between gap-2">
						<dt class="text-fg-muted">{{ t("المعدات", "Equipment") }}</dt>
						<dd>
							<span
								class="rounded-full bg-fg-muted/15 px-2.5 py-0.5 text-xs font-medium tabular-nums"
								>{{ row.equipment_count }}</span
							>
						</dd>
					</div>
				</dl>
				<RouterLink
					:to="`/jobs/${row.service_job}`"
					class="mt-3 inline-block font-mono text-sm text-primary hover:underline"
					@click.stop
					>{{ row.service_job }}</RouterLink
				>
			</article>
		</div>
	</div>
</template>
