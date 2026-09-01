<template>
  <v-container max-width="560" class="pa-6">
    <h1 class="text-h4 font-weight-bold mb-6">Mon profil</h1>
    <v-card class="pa-4">
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
  </v-container>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import { reactive, ref } from "vue";

const authStore = useAuthStore();
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
</script>
