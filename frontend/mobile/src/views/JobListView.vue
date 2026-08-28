<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import {
	IonPage,
	IonHeader,
	IonToolbar,
	IonTitle,
	IonContent,
	IonRefresher,
	IonRefresherContent,
	IonSpinner,
	type RefresherCustomEvent,
} from "@ionic/vue";
import { Network } from "@capacitor/network";
import { useRouter } from "vue-router";
import { DigitBrand, JobCard, type JobSummary } from "@kodlyft/ui";
import { formatNumber, locale, t, toggleLocale } from "@kodlyft/ui";
import { getDispatchJobs, getVanStock, type StockRow } from "@/lib/fsm";
import { useDuty } from "@/lib/duty";
import { cacheGet, cachePut, listCommands, syncQueued, type OfflineCommand } from "@/lib/offline";

const router = useRouter();
const { onDuty, busy: dutyBusy, error: dutyError, toggle } = useDuty();
const online = ref(true);
const loading = ref(true);
const jobs = ref<JobSummary[]>([]);
const vanStock = ref<StockRow[]>([]);
const showStock = ref(false);
const loadError = ref("");
const commands = ref<OfflineCommand[]>([]);
let stop: (() => void) | undefined;

const todayCount = computed(() => jobs.value.length);
const activeCount = computed(() => jobs.value.filter((j) => j.status === "In Progress").length);

async function load() {
	loading.value = true;
	loadError.value = "";
	try {
		jobs.value = await getDispatchJobs({ limit: 100 });
		await cachePut("assigned-jobs", jobs.value);
	} catch {
		jobs.value = (await cacheGet<JobSummary[]>("assigned-jobs")) || [];
		if (!jobs.value.length)
			loadError.value = t(
				"تعذر تحميل الأعمال المسندة. تحقق من الاتصال وسجل الدخول مجددًا.",
				"Couldn't load assigned jobs. Check your connection and sign in again.",
			);
	} finally {
		loading.value = false;
	}
	try {
		vanStock.value = await getVanStock();
	} catch {
		vanStock.value = [];
	}
}

onMounted(async () => {
	online.value = (await Network.getStatus()).connected;
	const handle = await Network.addListener("networkStatusChange", (s) => {
		online.value = s.connected;
		if (s.connected) void synchronize();
	});
	stop = () => handle.remove();
	await load();
	commands.value = await listCommands();
});

onUnmounted(() => stop?.());

function open(name: string) {
	router.push(`/jobs/${name}`);
}

async function synchronize() {
	commands.value = await syncQueued();
	await load();
}

const pendingCount = computed(() => commands.value.filter((row) => row.state !== "Synced").length);

async function refresh(event: RefresherCustomEvent) {
	await load();
	event.target.complete();
}
</script>

<template>
	<IonPage>
		<IonHeader class="ion-no-border">
			<IonToolbar>
				<IonTitle><DigitBrand compact tone="light" :locale="locale" /></IonTitle>
				<button
					slot="end"
					type="button"
					class="me-2 text-sm font-semibold text-brand"
					:aria-label="t('تغيير اللغة إلى الإنجليزية', 'Switch language to Arabic')"
					@click="toggleLocale"
				>
					{{ locale === "ar" ? "EN" : "ع" }}
				</button>
				<RouterLink
					to="/equipment"
					slot="end"
					class="me-4 text-sm font-semibold text-brand"
					>{{ t("المعدات", "Equipment") }}</RouterLink
				>
			</IonToolbar>
		</IonHeader>
		<IonContent :fullscreen="true">
			<IonRefresher slot="fixed" @ionRefresh="refresh($event as RefresherCustomEvent)">
				<IonRefresherContent />
			</IonRefresher>

			<div class="kl-command min-h-full px-4 pb-8">
				<div class="pt-3">
					<p class="text-xs font-semibold uppercase tracking-[0.12em] text-brand">
						{{ t("التطبيق الميداني", "Field app") }}
					</p>
					<h1 class="mt-1 text-2xl font-bold text-cmd-fg">
						{{ t("أعمالي", "My jobs") }}
					</h1>
				</div>
				<button
					v-if="pendingCount"
					type="button"
					class="mt-2 w-full rounded-xl border border-brand/30 bg-brand/10 px-3 py-2 text-sm text-brand"
					@click="synchronize"
				>
					{{ formatNumber(pendingCount) }}
					{{
						t(
							"تغييرات بانتظار المزامنة · اضغط لإعادة المحاولة",
							"change(s) waiting to sync · Tap to retry",
						)
					}}
				</button>
				<div
					v-if="!online"
					class="mt-2 flex items-center gap-2 rounded-xl border border-warning/30 bg-warning/15 px-3 py-2 text-sm text-warning"
				>
					<svg
						viewBox="0 0 24 24"
						class="size-4 shrink-0"
						fill="none"
						stroke="currentColor"
						stroke-width="1.9"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
					>
						<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM12 8v4M12 16h.01" />
					</svg>
					{{
						t(
							"غير متصل — تُعرض الأعمال المحفوظة وستتم المزامنة عند عودة الاتصال.",
							"Offline — showing saved jobs. Changes sync when you reconnect.",
						)
					}}
				</div>

				<div class="kl-glass mt-3 flex items-center justify-between gap-3 rounded-2xl p-4">
					<div class="flex items-center gap-2.5">
						<span
							class="size-2.5 rounded-full"
							:class="onDuty ? 'animate-pulse bg-success' : 'bg-cmd-fg-muted'"
							aria-hidden="true"
						/>
						<div>
							<p class="text-sm font-medium text-cmd-fg">
								{{
									onDuty
										? t("في الدوام", "On duty")
										: t("خارج الدوام", "Off duty")
								}}
							</p>
							<p class="text-xs text-cmd-fg-muted">
								{{
									onDuty
										? t("تتم مشاركة موقعك", "Sharing your location")
										: t("ابدأ الدوام لاستلام الأعمال", "Clock in to take jobs")
								}}
							</p>
						</div>
					</div>
					<button
						type="button"
						:disabled="dutyBusy"
						class="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-[filter] disabled:opacity-60"
						:class="
							onDuty
								? 'border border-border bg-transparent text-cmd-fg'
								: 'kl-grad-brand text-white shadow-e2 hover:brightness-110'
						"
						@click="toggle"
					>
						<IonSpinner v-if="dutyBusy" name="crescent" class="size-4" />
						{{ onDuty ? t("إنهاء الدوام", "Clock out") : t("بدء الدوام", "Clock in") }}
					</button>
				</div>
				<p v-if="dutyError" class="mt-2 text-xs text-danger">{{ dutyError }}</p>

				<div class="kl-glass mt-3 flex items-center justify-between rounded-2xl p-5">
					<div>
						<p class="text-sm text-cmd-fg-muted">
							{{ t("المسند اليوم", "Assigned today") }}
						</p>
						<p class="mt-1 font-mono text-4xl tabular-nums text-cmd-fg">
							{{ formatNumber(todayCount) }}
						</p>
					</div>
					<div class="text-end">
						<p class="text-sm text-cmd-fg-muted">
							{{ t("قيد التنفيذ", "In progress") }}
						</p>
						<p class="mt-1 font-mono text-4xl tabular-nums text-brand">
							{{ formatNumber(activeCount) }}
						</p>
					</div>
				</div>
				<div v-if="vanStock.length" class="kl-glass mt-3 rounded-2xl p-4">
					<button
						type="button"
						class="flex w-full items-center justify-between"
						@click="showStock = !showStock"
					>
						<span class="text-sm font-medium text-cmd-fg">
							{{ t("مخزون المركبة", "Van stock") }}
							<span class="text-cmd-fg-muted">({{ vanStock.length }})</span>
						</span>
						<span class="text-xs text-cmd-fg-muted">{{
							showStock ? t("إخفاء", "Hide") : t("عرض", "Show")
						}}</span>
					</button>
					<ul v-if="showStock" class="mt-3 divide-y divide-white/10">
						<li
							v-for="s in vanStock"
							:key="s.item_code"
							class="flex items-center justify-between py-2 text-sm"
						>
							<span class="truncate text-cmd-fg">{{
								s.item_name || s.item_code
							}}</span>
							<span
								class="ms-3 shrink-0 font-mono tabular-nums"
								:class="s.low ? 'text-danger' : 'text-cmd-fg-muted'"
							>
								{{ formatNumber(s.actual_qty)
								}}<span v-if="s.low" class="ms-1">· {{ t("منخفض", "low") }}</span>
							</span>
						</li>
					</ul>
				</div>

				<div v-if="loading" class="flex justify-center py-12">
					<IonSpinner />
				</div>
				<p
					v-else-if="loadError"
					class="mt-4 rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger"
				>
					{{ loadError }}
				</p>

				<div v-else class="mt-4 flex flex-col gap-3">
					<JobCard v-for="job in jobs" :key="job.name" :job="job" @open="open" />
				</div>
			</div>
		</IonContent>
	</IonPage>
</template>
