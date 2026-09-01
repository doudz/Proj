<template>
  <v-navigation-drawer v-model="drawer" width="260">
    <v-list-item :to="{ name: 'myTasks' }" class="py-4" prepend-icon="mdi-chart-gantt" title="GanttFlow" subtitle="Gestion de projet libre" />
    <v-divider />
    <v-list-item :to="{ name: 'myTasks' }" prepend-icon="mdi-view-dashboard-outline" title="Mes taches" subtitle="Ma page d'accueil" />
    <v-divider class="my-2" />
    <v-list-item
      v-for="ws in workspaceStore.workspaces"
      :key="ws.id"
      :active="workspaceStore.current?.id === ws.id"
      :title="ws.name"
      :subtitle="ws.my_role"
      @click="selectWorkspace(ws)"
    >
      <template #prepend>
        <v-avatar :color="ws.color" size="32">
          <span class="text-white text-caption font-weight-bold">{{ ws.name.slice(0, 2).toUpperCase() }}</span>
        </v-avatar>
      </template>
    </v-list-item>
    <v-list-item prepend-icon="mdi-plus" title="Nouvel espace de travail" @click="newWorkspaceDialog = true" />
    <v-divider class="my-2" />
    <v-list-item
      :to="{ name: 'portfolio' }"
      prepend-icon="mdi-view-agenda-outline"
      title="Vue multi-projets"
      subtitle="Detecter les goulots d'etranglement"
    />
    <v-divider class="my-2" />
    <v-list-subheader>Projets</v-list-subheader>
    <v-list-item
      v-for="project in projectStore.projects"
      :key="project.id"
      :to="{ name: 'project', params: { id: project.id } }"
      :title="project.name"
      :prepend-icon="project.icon"
    />
    <v-list-item prepend-icon="mdi-plus" title="Nouveau projet" @click="newProjectDialog = true" />
  </v-navigation-drawer>

  <v-app-bar flat border>
    <v-app-bar-nav-icon @click="drawer = !drawer" />
    <v-toolbar-title>{{ workspaceStore.current?.name || "GanttFlow" }}</v-toolbar-title>
    <v-spacer />
    <v-menu v-model="notifMenu" :close-on-content-click="false" location="bottom end">
      <template #activator="{ props }">
        <v-btn icon v-bind="props">
          <v-badge :content="notificationStore.unreadCount" :model-value="notificationStore.unreadCount > 0" color="error">
            <v-icon>mdi-bell-outline</v-icon>
          </v-badge>
        </v-btn>
      </template>
      <v-card width="360" max-height="420" class="overflow-y-auto">
        <v-card-title class="d-flex align-center">
          Notifications
          <v-spacer />
          <v-btn size="small" variant="text" @click="notificationStore.markAllRead()">Tout marquer lu</v-btn>
        </v-card-title>
        <v-divider />
        <v-list v-if="notificationStore.items.length" density="comfortable">
          <v-list-item
            v-for="n in notificationStore.items"
            :key="n.id"
            :class="{ 'bg-blue-lighten-5': !n.is_read }"
            @click="notificationStore.markRead(n.id)"
          >
            <v-list-item-title class="text-wrap">
              <strong v-if="n.actor">{{ n.actor.first_name }}</strong> {{ n.verb }}
            </v-list-item-title>
            <v-list-item-subtitle>{{ formatDate(n.created_at) }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
        <v-card-text v-else class="text-medium-emphasis">Aucune notification</v-card-text>
      </v-card>
    </v-menu>
    <v-menu>
      <template #activator="{ props }">
        <v-btn icon v-bind="props">
          <v-avatar :color="authStore.user?.avatar_color" size="36">
            <span class="text-white">{{ authStore.user?.initials }}</span>
          </v-avatar>
        </v-btn>
      </template>
      <v-list>
        <v-list-item :to="{ name: 'profile' }" prepend-icon="mdi-account-outline" title="Mon profil" />
        <v-list-item prepend-icon="mdi-logout" title="Deconnexion" @click="logout" />
      </v-list>
    </v-menu>
  </v-app-bar>

  <v-main>
    <router-view />
  </v-main>

  <v-dialog v-model="newWorkspaceDialog" max-width="420">
    <v-card title="Nouvel espace de travail">
      <v-card-text>
        <v-text-field v-model="newWorkspaceName" label="Nom" autofocus @keyup.enter="createWorkspace" />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="newWorkspaceDialog = false">Annuler</v-btn>
        <v-btn color="primary" @click="createWorkspace">Creer</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="newProjectDialog" max-width="420">
    <v-card title="Nouveau projet">
      <v-card-text>
        <v-text-field v-model="newProjectName" label="Nom du projet" autofocus @keyup.enter="createProject" />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="newProjectDialog = false">Annuler</v-btn>
        <v-btn color="primary" @click="createProject">Creer</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import { useNotificationStore } from "@/stores/notification";
import { useProjectStore } from "@/stores/project";
import { useWorkspaceStore } from "@/stores/workspace";
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const drawer = ref(true);
const notifMenu = ref(false);
const newWorkspaceDialog = ref(false);
const newWorkspaceName = ref("");
const newProjectDialog = ref(false);
const newProjectName = ref("");

const authStore = useAuthStore();
const workspaceStore = useWorkspaceStore();
const projectStore = useProjectStore();
const notificationStore = useNotificationStore();
const router = useRouter();
const route = useRoute();

onMounted(async () => {
  if (!authStore.user) await authStore.fetchMe();
  await workspaceStore.fetchWorkspaces();
  await notificationStore.fetchAll();
  if (workspaceStore.current) {
    await projectStore.fetchProjects(workspaceStore.current.id);
    await workspaceStore.fetchExternalContacts(workspaceStore.current.id);
  }
});

watch(
  () => workspaceStore.current,
  async (ws, previous) => {
    if (!ws) return;
    // A project displayed for the previous workspace has no meaning once the
    // workspace changes - fall back to the project list rather than leaving
    // stale data on screen (only when actually switching, not on first load).
    if (previous && route.name === "project") {
      router.push({ name: "workspaces" });
    }
    await projectStore.fetchProjects(ws.id);
    await workspaceStore.fetchExternalContacts(ws.id);
  }
);

function selectWorkspace(ws) {
  workspaceStore.setCurrent(ws);
}

async function createWorkspace() {
  if (!newWorkspaceName.value.trim()) return;
  await workspaceStore.createWorkspace({ name: newWorkspaceName.value });
  newWorkspaceName.value = "";
  newWorkspaceDialog.value = false;
}

async function createProject() {
  if (!newProjectName.value.trim() || !workspaceStore.current) return;
  const project = await projectStore.createProject({
    name: newProjectName.value,
    workspace: workspaceStore.current.id,
  });
  newProjectName.value = "";
  newProjectDialog.value = false;
  router.push({ name: "project", params: { id: project.id } });
}

function logout() {
  authStore.logout();
  router.push("/login");
}

function formatDate(value) {
  return new Date(value).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}
</script>
