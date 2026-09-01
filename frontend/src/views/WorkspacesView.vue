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
        <v-btn prepend-icon="mdi-account-hard-hat-outline" variant="tonal" class="mr-2" @click="contactsDialog = true">
          Contacts externes
        </v-btn>
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

    <v-dialog v-model="contactsDialog" max-width="560">
      <v-card title="Contacts externes">
        <v-card-subtitle class="px-4">
          Personnes ou sous-traitants sans compte GanttFlow, assignables a des taches (travail externalise). Notifies
          par e-mail uniquement.
        </v-card-subtitle>
        <v-card-text>
          <v-list v-if="workspaceStore.externalContacts.length">
            <v-list-item v-for="c in workspaceStore.externalContacts" :key="c.id">
              <template #prepend>
                <v-avatar :color="c.color">{{ c.initials }}</v-avatar>
              </template>
              <v-list-item-title>{{ c.name }}<span v-if="c.company" class="text-medium-emphasis"> - {{ c.company }}</span></v-list-item-title>
              <v-list-item-subtitle>{{ c.email || "Sans e-mail" }}</v-list-item-subtitle>
              <template #append>
                <v-btn icon="mdi-delete-outline" variant="text" size="small" @click="removeContact(c.id)" />
              </template>
            </v-list-item>
          </v-list>
          <p v-else class="text-medium-emphasis">Aucun contact externe pour le moment.</p>
          <v-divider class="my-3" />
          <div class="text-subtitle-2 mb-2">Ajouter un contact</div>
          <v-text-field v-model="newContact.name" label="Nom" density="compact" />
          <v-text-field v-model="newContact.email" label="E-mail (pour les notifications)" density="compact" />
          <v-text-field v-model="newContact.company" label="Societe (optionnel)" density="compact" />
          <v-btn color="primary" :disabled="!newContact.name.trim()" @click="createContact">Ajouter</v-btn>
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
import { onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";

const workspaceStore = useWorkspaceStore();
const projectStore = useProjectStore();
const router = useRouter();

const membersDialog = ref(false);
const inviteEmail = ref("");
const contactsDialog = ref(false);
const newContact = reactive({ name: "", email: "", company: "" });
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

watch(contactsDialog, async (open) => {
  if (open && workspaceStore.current) await workspaceStore.fetchExternalContacts(workspaceStore.current.id);
});

async function createContact() {
  if (!newContact.name.trim() || !workspaceStore.current) return;
  await workspaceStore.createExternalContact({ ...newContact, workspace: workspaceStore.current.id });
  newContact.name = "";
  newContact.email = "";
  newContact.company = "";
}

async function removeContact(id) {
  if (confirm("Supprimer ce contact externe ? Il sera retire des taches qui lui sont assignees.")) {
    await workspaceStore.deleteExternalContact(id);
  }
}

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
