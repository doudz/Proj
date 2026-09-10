<template>
  <v-container max-width="720" class="pa-6">
    <h1 class="text-h4 font-weight-bold mb-6">Mon profil</h1>
    <v-card class="pa-4 mb-6">
      <v-card-text>
        <div class="d-flex align-center mb-6">
          <v-avatar :color="authStore.user?.avatar_color" size="64">
            <span class="text-h5 text-white">{{ authStore.user?.initials }}</span>
          </v-avatar>
        </div>
        <div class="d-flex ga-2">
          <v-text-field v-model="form.first_name" label="Prenom" />
          <v-text-field v-model="form.last_name" label="Nom" />
        </div>
        <v-text-field v-model="form.job_title" label="Poste" />
        <v-text-field :model-value="authStore.user?.email" label="E-mail" disabled />
        <v-btn color="primary" :loading="loading" @click="save">Enregistrer</v-btn>
        <v-alert v-if="saved" type="success" class="mt-4" density="compact">Profil mis a jour.</v-alert>
      </v-card-text>
    </v-card>

    <v-card class="pa-4">
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-robot-outline" class="mr-2" />
        Connecteur MCP (assistant IA)
      </v-card-title>
      <v-card-subtitle class="text-wrap">
        Connectez un client compatible MCP (assistant IA) a GanttFlow pour piloter vos projets et taches en langage
        naturel : creation de taches, mise a jour de l'avancement, etc. Chaque jeton agit avec vos propres droits
        (les observateurs restent en lecture seule).
      </v-card-subtitle>
      <v-card-text>
        <div class="text-caption text-medium-emphasis mb-1">Adresse du serveur MCP</div>
        <div class="d-flex align-center mb-4">
          <code class="mcp-code flex-grow-1">{{ mcpUrl }}</code>
          <v-btn icon="mdi-content-copy" size="small" variant="text" @click="copy(mcpUrl)" />
        </div>

        <v-expansion-panels variant="accordion" class="mb-4">
          <v-expansion-panel title="Exemple de configuration (client MCP generique)">
            <template #text>
              <div class="d-flex align-start">
                <pre class="mcp-code flex-grow-1">{{ exampleConfig }}</pre>
                <v-btn icon="mdi-content-copy" size="small" variant="text" @click="copy(exampleConfig)" />
              </div>
            </template>
          </v-expansion-panel>
        </v-expansion-panels>

        <div class="d-flex align-center mb-2">
          <div class="text-subtitle-2">Jetons API</div>
          <v-spacer />
          <v-btn size="small" color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">Nouveau jeton</v-btn>
        </div>

        <v-list v-if="tokenStore.tokens.length" density="compact" class="mcp-token-list">
          <v-list-item v-for="token in tokenStore.tokens" :key="token.id">
            <v-list-item-title>{{ token.name }}</v-list-item-title>
            <v-list-item-subtitle>
              {{ token.display_prefix }}... - cree le {{ formatDate(token.created_at) }}
              <template v-if="token.last_used_at"> - utilise le {{ formatDate(token.last_used_at) }}</template>
              <template v-else> - jamais utilise</template>
            </v-list-item-subtitle>
            <template #append>
              <v-btn icon="mdi-delete-outline" size="small" variant="text" color="error" @click="revoke(token)" />
            </template>
          </v-list-item>
        </v-list>
        <p v-else class="text-medium-emphasis">Aucun jeton API pour le moment.</p>
      </v-card-text>
    </v-card>

    <v-dialog v-model="createDialog" max-width="480" persistent>
      <v-card title="Nouveau jeton API">
        <v-card-text>
          <template v-if="!createdToken">
            <v-text-field
              v-model="newTokenName"
              label="Nom (ex: Assistant IA)"
              autofocus
              @keyup.enter="createToken"
            />
          </template>
          <template v-else>
            <v-alert type="warning" variant="tonal" density="compact" class="mb-3">
              Copiez ce jeton maintenant : il ne sera plus jamais affiche.
            </v-alert>
            <div class="d-flex align-center">
              <code class="mcp-code flex-grow-1">{{ createdToken }}</code>
              <v-btn icon="mdi-content-copy" size="small" variant="text" @click="copy(createdToken)" />
            </div>
          </template>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <template v-if="!createdToken">
            <v-btn variant="text" @click="createDialog = false">Annuler</v-btn>
            <v-btn color="primary" :disabled="!newTokenName.trim()" :loading="creating" @click="createToken">
              Creer
            </v-btn>
          </template>
          <v-btn v-else color="primary" @click="createDialog = false">Fermer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="2500">{{ snackbarText }}</v-snackbar>
  </v-container>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import { useApiTokenStore } from "@/stores/apiTokens";
import { computed, onMounted, reactive, ref } from "vue";

const authStore = useAuthStore();
const tokenStore = useApiTokenStore();

const form = reactive({
  first_name: authStore.user?.first_name || "",
  last_name: authStore.user?.last_name || "",
  job_title: authStore.user?.job_title || "",
});
const loading = ref(false);
const saved = ref(false);

async function save() {
  loading.value = true;
  saved.value = false;
  try {
    await authStore.updateProfile(form);
    saved.value = true;
  } finally {
    loading.value = false;
  }
}

const mcpUrl = computed(() => `${window.location.origin}/mcp`);
const exampleConfig = computed(() =>
  JSON.stringify(
    {
      mcpServers: {
        ganttflow: {
          url: mcpUrl.value,
          headers: { Authorization: "Bearer <votre-jeton>" },
        },
      },
    },
    null,
    2
  )
);

const createDialog = ref(false);
const newTokenName = ref("");
const creating = ref(false);
const createdToken = ref("");
const snackbar = ref(false);
const snackbarText = ref("");

onMounted(() => {
  tokenStore.fetchTokens();
});

function openCreateDialog() {
  newTokenName.value = "";
  createdToken.value = "";
  createDialog.value = true;
}

async function createToken() {
  if (!newTokenName.value.trim()) return;
  creating.value = true;
  try {
    const result = await tokenStore.createToken(newTokenName.value.trim());
    createdToken.value = result.token;
  } finally {
    creating.value = false;
  }
}

async function revoke(token) {
  if (confirm(`Revoquer le jeton "${token.name}" ? Tout client MCP l'utilisant perdra l'acces.`)) {
    await tokenStore.revokeToken(token.id);
  }
}

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text);
    snackbarText.value = "Copie dans le presse-papiers.";
  } catch {
    snackbarText.value = "Impossible de copier automatiquement.";
  }
  snackbar.value = true;
}

function formatDate(value) {
  return new Date(value).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
}
</script>

<style scoped>
.mcp-code {
  display: block;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-x: auto;
}
.mcp-token-list {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
}
</style>
