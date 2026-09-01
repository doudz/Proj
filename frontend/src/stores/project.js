import api from "@/services/api";
import { defineStore } from "pinia";

export const useProjectStore = defineStore("project", {
  state: () => ({
    projects: [],
    current: null,
    members: [],
  }),
  actions: {
    async fetchProjects(workspaceId) {
      const { data } = await api.get("/projects/", { params: { workspace: workspaceId } });
      this.projects = data.results ?? data;
      return this.projects;
    },
    async fetchProject(id) {
      const { data } = await api.get(`/projects/${id}/`);
      this.current = data;
      return data;
    },
    async createProject(payload) {
      const { data } = await api.post("/projects/", payload);
      this.projects.unshift(data);
      return data;
    },
    async updateProject(id, payload) {
      const { data } = await api.patch(`/projects/${id}/`, payload);
      if (this.current?.id === id) this.current = data;
      const idx = this.projects.findIndex((p) => p.id === id);
      if (idx !== -1) this.projects[idx] = data;
      return data;
    },
    async deleteProject(id) {
      await api.delete(`/projects/${id}/`);
      this.projects = this.projects.filter((p) => p.id !== id);
    },
    async reorderColumns(projectId, order) {
      await api.post(`/projects/${projectId}/reorder-columns/`, { order });
    },
    async createColumn(payload) {
      const { data } = await api.post("/board-columns/", payload);
      if (this.current) this.current.columns.push(data);
      return data;
    },
    async createLabel(payload) {
      const { data } = await api.post("/labels/", payload);
      if (this.current) this.current.labels.push(data);
      return data;
    },
    async setBaseline(projectId) {
      const { data } = await api.post(`/projects/${projectId}/set-baseline/`);
      if (this.current?.id === projectId) this.current = data;
      return data;
    },
    async clearBaseline(projectId) {
      const { data } = await api.post(`/projects/${projectId}/clear-baseline/`);
      if (this.current?.id === projectId) this.current = data;
      return data;
    },
    async fetchMembers(projectId) {
      const { data } = await api.get(`/projects/${projectId}/members/`);
      this.members = data;
      return data;
    },
    async addMember(projectId, payload) {
      const { data } = await api.post(`/projects/${projectId}/members/`, payload);
      const idx = this.members.findIndex((m) => m.user.id === data.user.id);
      if (idx !== -1) this.members[idx] = data;
      else this.members.push(data);
      return data;
    },
    async removeMember(projectId, userId) {
      await api.delete(`/projects/${projectId}/members/${userId}/`);
      this.members = this.members.filter((m) => m.user.id !== userId);
    },
  },
});
