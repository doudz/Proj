import api from "@/services/api";
import { defineStore } from "pinia";

export const useWorkspaceStore = defineStore("workspace", {
  state: () => ({
    workspaces: [],
    current: JSON.parse(localStorage.getItem("ganttflow_workspace") || "null"),
    members: [],
    externalContacts: [],
  }),
  actions: {
    async fetchWorkspaces() {
      const { data } = await api.get("/workspaces/");
      this.workspaces = data.results ?? data;
      if (!this.current && this.workspaces.length) {
        this.setCurrent(this.workspaces[0]);
      }
      return this.workspaces;
    },
    async createWorkspace(payload) {
      const { data } = await api.post("/workspaces/", payload);
      this.workspaces.push(data);
      this.setCurrent(data);
      return data;
    },
    setCurrent(workspace) {
      this.current = workspace;
      localStorage.setItem("ganttflow_workspace", JSON.stringify(workspace));
    },
    async fetchMembers(workspaceId) {
      const { data } = await api.get(`/workspaces/${workspaceId}/members/`);
      this.members = data;
      return data;
    },
    async invite(workspaceId, payload) {
      const { data } = await api.post(`/workspaces/${workspaceId}/invite/`, payload);
      return data;
    },
    async fetchExternalContacts(workspaceId) {
      const { data } = await api.get("/external-contacts/", { params: { workspace: workspaceId, page_size: 500 } });
      this.externalContacts = data.results ?? data;
      return this.externalContacts;
    },
    async createExternalContact(payload) {
      const { data } = await api.post("/external-contacts/", payload);
      this.externalContacts.push(data);
      return data;
    },
    async updateExternalContact(id, payload) {
      const { data } = await api.patch(`/external-contacts/${id}/`, payload);
      const idx = this.externalContacts.findIndex((c) => c.id === id);
      if (idx !== -1) this.externalContacts[idx] = data;
      return data;
    },
    async deleteExternalContact(id) {
      await api.delete(`/external-contacts/${id}/`);
      this.externalContacts = this.externalContacts.filter((c) => c.id !== id);
    },
  },
});
