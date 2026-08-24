<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
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
import { installedBase } from "@/lib/fsm";

const router = useRouter();
const token = ref("");
const busy = ref(false);
const error = ref("");
async function resolve() {
	if (!token.value.trim()) return;
	busy.value = true;
	error.value = "";
	try {
		const row = await installedBase.resolveQr(token.value.trim());
		router.push(`/equipment/${encodeURIComponent(row.name)}`);
	} catch {
		error.value = "Equipment not found or not assigned to you.";
	} finally {
		busy.value = false;
	}
}
async function scan() {
	error.value = "";
	try {
		const photo = await Camera.getPhoto({
			quality: 80,
			resultType: CameraResultType.DataUrl,
			source: CameraSource.Camera,
		});
		if (!photo.dataUrl) return;
		const Detector = (
			globalThis as unknown as {
				BarcodeDetector?: new (options: { formats: string[] }) => {
					detect: (image: ImageBitmap) => Promise<Array<{ rawValue: string }>>;
				};
			}
		).BarcodeDetector;
		if (!Detector) {
			error.value = "QR scanning is unavailable on this device. Enter the asset ID instead.";
			return;
		}
		const blob = await (await fetch(photo.dataUrl)).blob();
		const image = await createImageBitmap(blob);
		const codes = await new Detector({ formats: ["qr_code"] }).detect(image);
		if (!codes[0]?.rawValue) {
			error.value = "No QR code was found in the image.";
			return;
		}
		token.value = codes[0].rawValue;
		await resolve();
	} catch {
		error.value = "QR scan was cancelled or unavailable.";
	}
}
</script>
<template>
	<IonPage
		><IonHeader
			><IonToolbar
				><IonButtons slot="start"><IonBackButton default-href="/jobs" /></IonButtons
				><IonTitle>Equipment Lookup</IonTitle></IonToolbar
			></IonHeader
		><IonContent :fullscreen="true"
			><div class="space-y-4 p-4">
				<section class="kl-glass rounded-2xl p-5">
					<h1 class="text-xl font-bold">Find installed equipment</h1>
					<p class="mt-1 text-sm text-fg-muted">
						Scan the service QR or enter the FSM equipment ID. Only equipment linked to
						your assigned jobs is visible.
					</p>
					<label class="mt-5 block text-sm font-medium"
						>Asset ID or QR token<input
							v-model="token"
							aria-label="Asset ID or QR token"
							class="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 font-mono"
							placeholder="FSM-EQ-000001"
							@keyup.enter="resolve"
					/></label>
					<div class="mt-4 grid grid-cols-2 gap-3">
						<button
							class="rounded-xl border border-border px-4 py-3 font-semibold"
							@click="scan"
						>
							Scan QR</button
						><button
							class="kl-grad-brand rounded-xl px-4 py-3 font-semibold text-white"
							:disabled="busy"
							@click="resolve"
						>
							<IonSpinner v-if="busy" class="size-4" />Lookup
						</button>
					</div>
					<p v-if="error" class="mt-3 text-sm text-danger">{{ error }}</p>
				</section>
			</div></IonContent
		></IonPage
	>
</template>
