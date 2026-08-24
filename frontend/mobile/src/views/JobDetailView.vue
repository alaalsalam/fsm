<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import {
	IonPage,
	IonHeader,
	IonToolbar,
	IonTitle,
	IonButtons,
	IonBackButton,
	IonContent,
	IonSpinner,
} from "@ionic/vue";
import { Camera, CameraResultType, CameraSource } from "@capacitor/camera";
import { ChecklistItem, KlButton } from "@kodlyft/ui";
import {
	startTimer,
	stopTimer,
	getJob,
	getJobVisits,
	runVisitCommand,
	type MobileJob,
	type MobileVisit,
} from "@/lib/fsm";

const props = defineProps<{ id: string }>();

const timerRunning = ref(false);
const timerBusy = ref(false);
const elapsed = ref(0);
const lastHours = ref<number | null>(null);
const timerError = ref("");
const job = ref<MobileJob>();
const visits = ref<MobileVisit[]>([]);
const loading = ref(true);
const actionBusy = ref(false);
const actionError = ref("");
let startedAt = 0;
let tick: ReturnType<typeof setInterval> | undefined;

const clock = (s: number) => {
	const h = Math.floor(s / 3600)
		.toString()
		.padStart(2, "0");
	const m = Math.floor((s % 3600) / 60)
		.toString()
		.padStart(2, "0");
	const sec = Math.floor(s % 60)
		.toString()
		.padStart(2, "0");
	return `${h}:${m}:${sec}`;
};

async function toggleTimer() {
	timerBusy.value = true;
	timerError.value = "";
	try {
		if (timerRunning.value) {
			const res = await stopTimer(props.id);
			lastHours.value = res.actual_hours;
			timerRunning.value = false;
			clearInterval(tick);
			elapsed.value = 0;
		} else {
			await startTimer(props.id);
			timerRunning.value = true;
			startedAt = Date.now();
			tick = setInterval(() => (elapsed.value = (Date.now() - startedAt) / 1000), 1000);
		}
	} catch {
		timerError.value = "Couldn't update the timer. Check your connection.";
	} finally {
		timerBusy.value = false;
	}
}

onMounted(async () => {
	try {
		[job.value, visits.value] = await Promise.all([getJob(props.id), getJobVisits(props.id)]);
	} catch {
		actionError.value = "Couldn't load this job from the server.";
	} finally {
		loading.value = false;
	}
});
onUnmounted(() => clearInterval(tick));

const commandByStatus: Record<string, string> = {
	Dispatched: "start_travel",
	"En Route": "check_in_visit",
	"Checked In": "start_visit_work",
	"In Progress": "check_out_visit",
	"Checked Out": "complete_visit",
};
async function advance(visit: MobileVisit) {
	const command = commandByStatus[visit.status];
	if (!command) return;
	actionBusy.value = true;
	actionError.value = "";
	try {
		await runVisitCommand(command, visit.name);
		visits.value = await getJobVisits(props.id);
		job.value = await getJob(props.id);
	} catch {
		actionError.value = "Couldn't update the visit. Check assignment and connection.";
	} finally {
		actionBusy.value = false;
	}
}

const photos = ref<string[]>([]);

async function addPhoto() {
	try {
		const photo = await Camera.getPhoto({
			quality: 70,
			resultType: CameraResultType.DataUrl,
			source: CameraSource.Camera,
		});
		if (photo.dataUrl) photos.value.push(photo.dataUrl);
	} catch {
		// User cancelled or no camera (e.g. browser dev) — ignore.
	}
}
</script>

<template>
	<IonPage>
		<IonHeader>
			<IonToolbar>
				<IonButtons slot="start">
					<IonBackButton default-href="/jobs" />
				</IonButtons>
				<IonTitle>{{ id }}</IonTitle>
			</IonToolbar>
		</IonHeader>
		<IonContent :fullscreen="true">
			<div class="space-y-6 p-4">
				<IonSpinner v-if="loading" />
				<p v-if="actionError" class="text-sm text-danger">{{ actionError }}</p>
				<section v-if="job" class="rounded-lg border border-border bg-bg p-4">
					<h2 class="text-lg font-bold">{{ job.customer_name || job.customer }}</h2>
					<p class="text-sm text-fg-muted">
						{{ job.status }} · {{ job.phase || "Planning" }}
					</p>
					<p class="mt-2 text-sm">{{ job.address_display }}</p>
				</section>
				<section v-if="visits.length">
					<h2 class="mb-2 text-lg font-bold">Service visits</h2>
					<div
						v-for="visit in visits"
						:key="visit.name"
						class="mb-2 rounded-lg border border-border bg-bg p-4"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="font-semibold">Visit {{ visit.visit_number }}</p>
								<p class="text-sm text-fg-muted">{{ visit.status }}</p>
							</div>
							<button
								v-if="commandByStatus[visit.status]"
								class="rounded-lg bg-brand px-3 py-2 text-sm font-semibold text-white"
								:disabled="actionBusy"
								@click="advance(visit)"
							>
								Continue
							</button>
						</div>
					</div>
				</section>
				<section class="rounded-lg border border-border bg-bg p-4">
					<div class="flex items-center justify-between">
						<div>
							<h2 class="text-lg font-bold">Labour timer</h2>
							<p
								class="font-mono text-2xl tabular-nums"
								:class="timerRunning ? 'text-brand' : 'text-fg-muted'"
							>
								{{
									timerRunning
										? clock(elapsed)
										: lastHours != null
											? `${lastHours.toFixed(2)} h logged`
											: "00:00:00"
								}}
							</p>
						</div>
						<button
							type="button"
							:disabled="timerBusy"
							class="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-[filter] disabled:opacity-60"
							:class="
								timerRunning
									? 'border border-danger/40 text-danger'
									: 'kl-grad-brand text-white shadow-e2 hover:brightness-110'
							"
							@click="toggleTimer"
						>
							<IonSpinner v-if="timerBusy" name="crescent" class="size-4" />
							{{ timerRunning ? "Stop" : "Start" }}
						</button>
					</div>
					<p v-if="timerError" class="mt-2 text-xs text-danger">{{ timerError }}</p>
				</section>

				<section>
					<h2 class="mb-2 text-lg font-bold">Checklist</h2>
					<div class="rounded-lg border border-border bg-bg">
						<ChecklistItem
							v-for="(item, i) in job?.tasks || []"
							:key="i"
							:model-value="item.status === 'Done'"
							:label="item.task"
							:note="item.note"
							@update:model-value="() => {}"
						/>
					</div>
				</section>

				<section>
					<h2 class="mb-2 text-lg font-bold">Photos</h2>
					<div class="grid grid-cols-3 gap-2">
						<img
							v-for="(src, i) in photos"
							:key="i"
							:src="src"
							class="aspect-square w-full rounded-md object-cover"
						/>
						<button
							type="button"
							class="flex aspect-square items-center justify-center rounded-md border border-dashed border-border text-fg-muted"
							@click="addPhoto"
						>
							+ Add
						</button>
					</div>
				</section>

				<section>
					<h2 class="mb-2 text-lg font-bold">Signature</h2>
					<div
						class="flex h-32 items-center justify-center rounded-lg border border-dashed border-border text-fg-muted"
					>
						Tap to capture customer signature
					</div>
				</section>

				<KlButton block>Complete job</KlButton>
			</div>
		</IonContent>
	</IonPage>
</template>
