import api from "@/services/api";
import { defineStore } from "pinia";

/**
 * Cross-project data for the portfolio (multi-project) Gantt view.
 * Kept separate from the task store, which is scoped to a single project.
 */
export const usePortfolioStore = defineStore("portfolio", {
  state: () => ({
    tasks: [],
    loading: false,
  }),
  actions: {
    async fetchWorkspaceTasks(workspaceId) {
      this.loading = true;
      try {
        const { data } = await api.get("/tasks/", {
          params: { workspace: workspaceId, root_only: false, page_size: 2000 },
        });
        this.tasks = data.results ?? data;
        return this.tasks;
      } finally {
        this.loading = false;
      }
    },
    async rescheduleTask(id, startDate, dueDate) {
      const { data } = await api.post(`/tasks/${id}/reschedule/`, {
        start_date: startDate,
        due_date: dueDate,
      });
      const idx = this.tasks.findIndex((t) => t.id === id);
      if (idx !== -1) this.tasks[idx] = data;
      return data;
    },
  },
});
