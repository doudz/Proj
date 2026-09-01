<template>
  <v-container fluid class="pa-6">
    <div v-if="!workspaceStore.current" class="text-center pa-12">
      <v-icon icon="mdi-briefcase-plus-outline" size="64" color="grey" />
      <h2 class="text-h5 mt-4">Creez votre premier espace de travail</h2>
      <p class="text-medium-emphasis">Un espace de travail regroupe vos projets et votre equipe.</p>
    </div>
    <template v-else>
      <div class="d-flex align-center mb-6">
        <div>
          <h1 class="text-h4 font-weight-bold">{{ workspaceStore.current.name }}</h1>
          <p class="text-medium-emphasis mb-0">{{ workspaceStore.current.members_count }} membre(s)</p>
        </div>
        <v-spacer />
        <v-btn prepend-icon="mdi-account-multiple-plus-outline" variant="tonal" class="mr-2" @click="membersDialog = true">Membres</v-btn>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="$router.push('/projects')">Voir les projets</v-btn>
      </div>

      <v-row>
        <v-col v-for="project in projectStore.projects" :key="project.id" cols="12" sm="6" md="4" lg="3">
          <v-card :to="{ name: 'project', params: { id: project.id } }" elevation="1" class="h-100">
            <v-card-item>
              <template #prepend>
                <v-avatar :color="project.color" rounded="lg">
                  <v-icon :icon="project.icon" color="white" />
                </v-avatar>
              </template>
              <v-card-title>{{ project.name }}</v-card-title>
              <v-card-subtitle>{{ project.tasks_count }} tache(s)</v-card-subtitle>
            </v-card-item>
            <v-card-text>
              <v-progress-linear :model-value="project.progress" height="8" rounded color="success" class="mb-1" />
              <span class="text-caption text-medium-emphasis">{{ project.progress }}% termine</span>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4" lg="3">
          <v-card class="h-100 d-flex align-center justify-center pa-6" variant="tonal" height="100%" @click="newProjectDialog = true">
            <div class="text-center">
              <v-icon icon="mdi-plus-circle-outline" size="36" />
              <div class="mt-2">Nouveau projet</div>
            </div>
          </v-card>
        </v-col>
      </v-row>
    </template>

    <v-dialog v-model="membersDialog" max-width="480">
      <v-card title="Membres de l'espace de travail">
        <v-card-text>
          <v-list>
            <v-list-item v-for="m in workspaceStore.members" :key="m.id" :title="m.user.first_name + ' ' + m.user.last_name" :subtitle="m.role">
              <template #prepend>
                <v-avatar :color="m.user.avatar_color">{{ m.user.initials }}</v-avatar>
              </template>
            </v-list-item>
          </v-list>
          <v-divider class="my-3" />
          <v-text-field v-model="inviteEmail" label="Inviter par e-mail" append-inner-icon="mdi-send" @click:append-inner="invite" @keyup.enter="invite" />
        </v-card-text>
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
  </v-container>
</template>

<script setup>
import { useProjectStore } from "@/stores/project";
import { useWorkspaceStore } from "@/stores/workspace";
import { onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

const workspaceStore = useWorkspaceStore();
const projectStore = useProjectStore();
const router = useRouter();

const membersDialog = ref(false);
const inviteEmail = ref("");
const newProjectDialog = ref(false);
const newProjectName = ref("");

onMounted(async () => {
  if (workspaceStore.current) {
    await projectStore.fetchProjects(workspaceStore.current.id);
  }
});

watch(membersDialog, async (open) => {
  if (open && workspaceStore.current) await workspaceStore.fetchMembers(workspaceStore.current.id);
});

async function invite() {
  if (!inviteEmail.value.trim()) return;
  await workspaceStore.invite(workspaceStore.current.id, { email: inviteEmail.value, role: "member" });
  inviteEmail.value = "";
}

async function createProject() {
  if (!newProjectName.value.trim()) return;
  const project = await projectStore.createProject({ name: newProjectName.value, workspace: workspaceStore.current.id });
  newProjectName.value = "";
  newProjectDialog.value = false;
  router.push({ name: "project", params: { id: project.id } });
}
</script>
