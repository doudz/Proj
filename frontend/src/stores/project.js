import api from "@/services/api";
import { defineStore } from "pinia";

export const useProjectStore = defineStore("project", {
  state: () => ({
    projects: [],
    current: null,
    members: [],
    templates: [],
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
    async createCustomField(payload) {
      const { data } = await api.post("/custom-fields/", payload);
      if (this.current?.id === payload.project) this.current.custom_fields.push(data);
      return data;
    },
    async updateCustomField(id, payload) {
      const { data } = await api.patch(`/custom-fields/${id}/`, payload);
      const fields = this.current?.custom_fields;
      const idx = fields?.findIndex((f) => f.id === id) ?? -1;
      if (idx !== -1) fields[idx] = data;
      return data;
    },
    async deleteCustomField(id) {
      await api.delete(`/custom-fields/${id}/`);
      if (this.current) this.current.custom_fields = this.current.custom_fields.filter((f) => f.id !== id);
    },
    async fetchTemplates(workspaceId) {
      const { data } = await api.get("/projects/", {
        params: { workspace: workspaceId, is_template: "true", page_size: 200 },
      });
      this.templates = data.results ?? data;
      return this.templates;
    },
    async saveAsTemplate(projectId, name) {
      const { data } = await api.post(`/projects/${projectId}/save-as-template/`, { name });
      this.templates.push(data);
      return data;
    },
    async instantiateTemplate(templateId, payload) {
      const { data } = await api.post(`/projects/${templateId}/instantiate/`, payload);
      this.projects.unshift(data);
      return data;
    },
    async duplicateProject(projectId, name = null) {
      const { data } = await api.post(`/projects/${projectId}/duplicate/`, name ? { name } : {});
      this.projects.unshift(data);
      return data;
    },
    async deleteTemplate(templateId) {
      await api.delete(`/projects/${templateId}/`);
      this.templates = this.templates.filter((t) => t.id !== templateId);
    },
  },
});
