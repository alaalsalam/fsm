import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { initTheme } from "./lib/theme";
import { initializeLocale } from "./lib/i18n";
import "./style.css";

initTheme();
initializeLocale("ar");

createApp(App).use(createPinia()).use(router).mount("#app");
