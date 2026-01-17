import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import LiveStatsStyles from "./LiveStatsStyles.vue";
import LiveCardStyles from "./LiveCardStyles.vue";
import MostValue from "./MostValue.vue";
import "./assets/base.css";

const pathname = window.location.pathname;
const useStatsStylesPage = pathname.endsWith("/styles");
const useCardStylesPage = pathname.endsWith("/cards");
const useMostValuePage = pathname.endsWith("/most-value");
const rootComponent = useCardStylesPage
  ? LiveCardStyles
  : useStatsStylesPage
    ? LiveStatsStyles
    : useMostValuePage
      ? MostValue
      : App;
const app = createApp(rootComponent);
app.use(createPinia());
app.mount("#app");
