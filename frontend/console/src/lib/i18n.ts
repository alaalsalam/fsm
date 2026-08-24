import { ref, readonly } from "vue";

type Lang = "ar" | "en";
const LS_KEY = "kl-lang";

const current = ref<Lang>((localStorage.getItem(LS_KEY) as Lang) ?? "ar");

function applyLang(l: Lang) {
	document.documentElement.setAttribute("lang", l);
	document.documentElement.setAttribute("dir", l === "ar" ? "rtl" : "ltr");
}

// Apply on module load
applyLang(current.value);

export const lang = readonly(current);

export function setLang(l: Lang) {
	current.value = l;
	localStorage.setItem(LS_KEY, l);
	applyLang(l);
}

export function toggleLang() {
	setLang(current.value === "ar" ? "en" : "ar");
}

/** Returns `ar` when Arabic is active, `en` otherwise. Reactive in Vue templates. */
export function t(ar: string, en: string): string {
	return current.value === "ar" ? ar : en;
}
