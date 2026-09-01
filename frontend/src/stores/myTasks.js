import api from "@/services/api";
import { defineStore } from "pinia";

export const useMyTasksStore = defineStore("myTasks", {
  state: () => ({
    tasks: [],
    loading: false,
    loaded: false,
  }),
  actions: {
    async fetchMine() {
      this.loading = true;
      try {
        const { data } = await api.get("/tasks/mine/");
        this.tasks = data;
        this.loaded = true;
        return this.tasks;
      } finally {
        this.loading = false;
      }
    },
  },
});
