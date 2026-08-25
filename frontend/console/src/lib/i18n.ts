import { initializeLocale, locale, setLocale, t, toggleLocale, type AppLocale } from "@kodlyft/ui";

export const lang = locale;
export const setLang = (value: AppLocale) => setLocale(value);
export const toggleLang = toggleLocale;
export { initializeLocale, t };
