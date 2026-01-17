import { defineStore } from "pinia";

export const useUiStore = defineStore("ui", {
  state: () => ({
    isLoading: false,
    lastError: null
  }),
  actions: {
    setLoading(value) {
      this.isLoading = value;
    },
    setError(error) {
      this.lastError = error;
    },
    clearError() {
      this.lastError = null;
    }
  }
});
