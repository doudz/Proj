import api from "@/services/api";
import { defineStore } from "pinia";

// The company-wide user directory - this is a single-tenant, enterprise
// deployment, so every account is fair game when picking who to add to a
// workspace or project, not just people already sharing one with you.
export const useDirectoryStore = defineStore("directory", {
  state: () => ({
    users: [],
  }),
  actions: {
    async fetchUsers(search = "") {
      const { data } = await api.get("/users/", { params: { search, page_size: 200 } });
      this.users = data.results ?? data;
      return this.users;
    },
  },
});
