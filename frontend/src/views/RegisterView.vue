<template>
  <v-main class="auth-bg">
    <v-container class="fill-height" max-width="460">
      <v-row justify="center" class="w-100">
        <v-col cols="12">
          <div class="text-center mb-6">
            <v-icon icon="mdi-chart-gantt" size="48" color="primary" />
            <h1 class="text-h4 font-weight-bold mt-2">Creer un compte</h1>
          </div>
          <v-card elevation="4" class="pa-6">
            <v-form @submit.prevent="submit">
              <div class="d-flex ga-2">
                <v-text-field v-model="form.first_name" label="Prenom" required />
                <v-text-field v-model="form.last_name" label="Nom" required />
              </div>
              <v-text-field v-model="form.email" label="E-mail" type="email" prepend-inner-icon="mdi-email-outline" required />
              <v-text-field
                v-model="form.password"
                label="Mot de passe"
                type="password"
                prepend-inner-icon="mdi-lock-outline"
                hint="8 caracteres minimum"
                required
              />
              <v-alert v-if="error" type="error" density="compact" class="mb-4">{{ error }}</v-alert>
              <v-btn type="submit" color="primary" size="large" block :loading="loading">Creer mon compte</v-btn>
            </v-form>
            <div class="text-center mt-4">
              <span class="text-medium-emphasis">Deja inscrit ?</span>
              <router-link to="/login" class="ml-1">Se connecter</router-link>
            </div>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </v-main>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";

const form = reactive({ first_name: "", last_name: "", email: "", password: "" });
const loading = ref(false);
const error = ref("");

const auth = useAuthStore();
const router = useRouter();

async function submit() {
  loading.value = true;
  error.value = "";
  try {
    await auth.register(form);
    router.push("/");
  } catch (e) {
    const data = e.response?.data;
    error.value = data ? Object.values(data).flat().join(" ") : "Inscription impossible.";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-bg {
  background: linear-gradient(135deg, #e3f2fd 0%, #f5f7fa 100%);
}
</style>
