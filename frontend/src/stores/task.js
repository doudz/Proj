import api from "@/services/api";
import { defineStore } from "pinia";

export const useTaskStore = defineStore("task", {
  state: () => ({
    tasks: [],
    dependencies: [],
  }),
  getters: {
    byId: (state) => (id) => state.tasks.find((t) => t.id === id),
    rootTasks: (state) => state.tasks.filter((t) => !t.parent),
    subtasksOf: (state) => (id) => state.tasks.filter((t) => t.parent === id),
  },
  actions: {
    async fetchTasks(projectId) {
      const { data } = await api.get("/tasks/", { params: { project: projectId, page_size: 500 } });
      this.tasks = data.results ?? data;
      await this.fetchDependencies(this.tasks.map((t) => t.id));
      return this.tasks;
    },
    async fetchDependencies(taskIds) {
      if (!taskIds.length) {
        this.dependencies = [];
        return;
      }
      const { data } = await api.get("/task-dependencies/", { params: { page_size: 1000 } });
      const idSet = new Set(taskIds);
      this.dependencies = (data.results ?? data).filter(
        (d) => idSet.has(d.predecessor) && idSet.has(d.successor)
      );
    },
    async createTask(payload) {
      const { data } = await api.post("/tasks/", payload);
      this._upsert(data);
      return data;
    },
    async updateTask(id, payload) {
      const { data } = await api.patch(`/tasks/${id}/`, payload);
      this._upsert(data);
      // A date change can shift every downstream task, so pull the successors
      // back in rather than leaving stale dates on screen.
      if (this._touchesSchedule(payload)) await this._refreshSuccessors(id);
      return data;
    },
    async refreshTask(id) {
      const { data } = await api.get(`/tasks/${id}/`);
      this._upsert(data);
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
    _touchesSchedule(payload) {
      return ["start_date", "due_date", "duration_days"].some((key) => key in payload);
    },
    async deleteTask(id) {
      await api.delete(`/tasks/${id}/`);
      this.tasks = this.tasks.filter((t) => t.id !== id);
    },
    async moveTask(id, column, order) {
      const { data } = await api.post(`/tasks/${id}/move/`, { column, order });
      this._upsert(data);
      return data;
    },
    async rescheduleTask(id, startDate, dueDate) {
      const { data } = await api.post(`/tasks/${id}/reschedule/`, {
        start_date: startDate,
        due_date: dueDate,
      });
      this._upsert(data);
      await this._refreshSuccessors(id);
      return data;
    },
    async startTask(id, date = null) {
      const { data } = await api.post(`/tasks/${id}/start/`, date ? { date } : {});
      this._upsert(data);
      return data;
    },
    async completeTask(id, date = null) {
      const { data } = await api.post(`/tasks/${id}/complete/`, date ? { date } : {});
      this._upsert(data);
      return data;
    },
    async addDependency(predecessor, successor, type = "FS", enforceBlocking = false) {
      const { data } = await api.post("/task-dependencies/", {
        predecessor,
        successor,
        type,
        enforce_blocking: enforceBlocking,
      });
      this.dependencies.push(data);
      return data;
    },
    async removeDependency(id) {
      await api.delete(`/task-dependencies/${id}/`);
      this.dependencies = this.dependencies.filter((d) => d.id !== id);
    },
    async toggleDependencyBlocking(id, enforceBlocking) {
      const { data } = await api.patch(`/task-dependencies/${id}/`, { enforce_blocking: enforceBlocking });
      const idx = this.dependencies.findIndex((d) => d.id === id);
      if (idx !== -1) this.dependencies[idx] = data;
      return data;
    },
    applyRealtimeEvent(kind, payload) {
      if (kind === "task.created" || kind === "task.updated") {
        this._upsert(payload);
      } else if (kind === "task.deleted") {
        this.tasks = this.tasks.filter((t) => t.id !== payload.id);
      }
    },
    _upsert(task) {
      const idx = this.tasks.findIndex((t) => t.id === task.id);
      if (idx === -1) this.tasks.push(task);
      else this.tasks[idx] = task;
    },
  },
});
