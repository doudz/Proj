import api from "@/services/api";
import { defineStore } from "pinia";

/**
 * Cross-project data for the portfolio (multi-project) Gantt view.
 * Kept separate from the task store, which is scoped to a single project.
 */
export const usePortfolioStore = defineStore("portfolio", {
  state: () => ({
    tasks: [],
    dependencies: [],
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
        await this.fetchDependencies(this.tasks.map((t) => t.id));
        return this.tasks;
      } finally {
        this.loading = false;
      }
    },
    async fetchDependencies(taskIds) {
      if (!taskIds.length) {
        this.dependencies = [];
        return;
      }
      const { data } = await api.get("/task-dependencies/", { params: { page_size: 2000 } });
      const idSet = new Set(taskIds);
      this.dependencies = (data.results ?? data).filter(
        (d) => idSet.has(d.predecessor) && idSet.has(d.successor)
      );
    },
    async refreshTask(id) {
      const { data } = await api.get(`/tasks/${id}/`);
      this._upsert(data);
      return data;
    },
    async rescheduleTask(id, startDate, dueDate) {
      const { data } = await api.post(`/tasks/${id}/reschedule/`, {
        start_date: startDate,
        due_date: dueDate,
      });
      this._upsert(data);
      // The dependencies have the last word on downstream tasks' dates - pull
      // them back in too, or their bars would silently go stale in this view.
      await this._refreshSuccessors(id);
      return data;
    },
    async _refreshSuccessors(id) {
      const downstream = this._downstreamIds(id);
      await Promise.all([...downstream].map((taskId) => this.refreshTask(taskId)));
    },
    _downstreamIds(id, seen = new Set()) {
      for (const dep of this.dependencies.filter((d) => d.predecessor === id)) {
        if (seen.has(dep.successor)) continue;
        seen.add(dep.successor);
        this._downstreamIds(dep.successor, seen);
      }
      return seen;
    },
    _upsert(task) {
      const idx = this.tasks.findIndex((t) => t.id === task.id);
      if (idx === -1) this.tasks.push(task);
      else this.tasks[idx] = task;
    },
  },
});
