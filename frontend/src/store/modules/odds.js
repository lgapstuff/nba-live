import { defineStore } from "pinia";
import { fetchLatestOdds } from "../../api/endpoints";

export const useOddsStore = defineStore("odds", {
  state: () => ({
    items: [],
    updatedAt: null
  }),
  actions: {
    async loadLatest() {
      const data = await fetchLatestOdds();
      this.items = data?.items ?? [];
      this.updatedAt = new Date().toISOString();
    }
  }
});
