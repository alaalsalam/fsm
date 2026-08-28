import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { initTheme } from "./lib/theme";
import { initializeLocale } from "@digit/ui";
import "./style.css";

initTheme();
initializeLocale("ar");

createApp(App).use(router).mount("#app");
