import api, { setTokens, getTokens } from "@/services/api";
import { defineStore } from "pinia";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: JSON.parse(localStorage.getItem("ganttflow_user") || "null"),
  }),
  getters: {
    isAuthenticated: (state) => !!state.user && !!getTokens()?.access,
  },
  actions: {
    async login(email, password) {
      const { data } = await api.post("/auth/login/", { email, password });
      this._applySession(data);
    },
    async register(payload) {
      const { data } = await api.post("/auth/register/", payload);
      this._applySession(data);
    },
    async fetchMe() {
      const { data } = await api.get("/auth/me/");
      this.user = data;
      localStorage.setItem("ganttflow_user", JSON.stringify(data));
    },
    async updateProfile(payload) {
      const { data } = await api.patch("/auth/me/", payload);
      this.user = data;
      localStorage.setItem("ganttflow_user", JSON.stringify(data));
    },
    logout() {
      this.user = null;
      setTokens(null);
      localStorage.removeItem("ganttflow_user");
    },
    _applySession(data) {
      setTokens({ access: data.access, refresh: data.refresh });
      this.user = data.user;
      localStorage.setItem("ganttflow_user", JSON.stringify(data.user));
    },
  },
});
