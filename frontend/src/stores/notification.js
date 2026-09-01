import api from "@/services/api";
import { defineStore } from "pinia";

export const useNotificationStore = defineStore("notification", {
  state: () => ({
    items: [],
  }),
  getters: {
    unreadCount: (state) => state.items.filter((n) => !n.is_read).length,
  },
  actions: {
    async fetchAll() {
      const { data } = await api.get("/notifications/");
      this.items = data.results ?? data;
      return this.items;
    },
    async markAllRead() {
      await api.post("/notifications/mark-all-read/");
      this.items = this.items.map((n) => ({ ...n, is_read: true }));
    },
    async markRead(id) {
      await api.post(`/notifications/${id}/read/`);
      const item = this.items.find((n) => n.id === id);
      if (item) item.is_read = true;
    },
    pushRealtime(payload) {
      this.items.unshift({ ...payload, is_read: false });
    },
  },
});
