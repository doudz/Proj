import { useAuthStore } from "@/stores/auth";
import { createRouter, createWebHistory } from "vue-router";

const routes = [
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/LoginView.vue"),
    meta: { public: true },
  },
  {
    path: "/register",
    name: "register",
    component: () => import("@/views/RegisterView.vue"),
    meta: { public: true },
  },
  {
    path: "/",
    component: () => import("@/layouts/DefaultLayout.vue"),
    children: [
      { path: "", name: "workspaces", component: () => import("@/views/WorkspacesView.vue") },
      { path: "projects", name: "projects", component: () => import("@/views/ProjectsListView.vue") },
      {
        path: "projects/:id",
        name: "project",
        component: () => import("@/views/ProjectDashboardView.vue"),
        props: true,
      },
      { path: "profile", name: "profile", component: () => import("@/views/ProfileView.vue") },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  if (to.meta.public && auth.isAuthenticated) {
    return { name: "workspaces" };
  }
  return true;
});

export default router;
