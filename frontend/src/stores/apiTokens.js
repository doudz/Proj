import api from "@/services/api";
import { defineStore } from "pinia";

export const useApiTokenStore = defineStore("apiTokens", {
  state: () => ({
    tokens: [],
  }),
  actions: {
    async fetchTokens() {
      const { data } = await api.get("/api-tokens/");
      this.tokens = data.results ?? data;
      return this.tokens;
    },
    async createToken(name) {
      const { data } = await api.post("/api-tokens/", { name });
      // `data.token` (the raw secret) is only ever present in this one
      // response - the list/refetch below never carries it again.
      this.tokens.unshift(data);
      return data;
    },
    async revokeToken(id) {
      await api.delete(`/api-tokens/${id}/`);
      this.tokens = this.tokens.filter((t) => t.id !== id);
    },
  },
});
