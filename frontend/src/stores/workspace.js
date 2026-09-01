import api from "@/services/api";
import { defineStore } from "pinia";

export const useWorkspaceStore = defineStore("workspace", {
  state: () => ({
    workspaces: [],
    current: JSON.parse(localStorage.getItem("ganttflow_workspace") || "null"),
    members: [],
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
  },
});
