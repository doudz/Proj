<template>
  <v-main class="auth-bg">
    <v-container class="fill-height" max-width="420">
      <v-row justify="center" class="w-100">
        <v-col cols="12">
          <div class="text-center mb-6">
            <v-icon icon="mdi-chart-gantt" size="48" color="primary" />
            <h1 class="text-h4 font-weight-bold mt-2">GanttFlow</h1>
            <p class="text-medium-emphasis">L'alternative libre a Monday.com &amp; Asana</p>
          </div>
          <v-card elevation="4" class="pa-6">
            <v-form @submit.prevent="submit">
              <v-text-field v-model="email" label="E-mail" type="email" prepend-inner-icon="mdi-email-outline" required />
              <v-text-field
                v-model="password"
                label="Mot de passe"
                :type="showPassword ? 'text' : 'password'"
                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                prepend-inner-icon="mdi-lock-outline"
                @click:append-inner="showPassword = !showPassword"
                required
              />
              <v-alert v-if="error" type="error" density="compact" class="mb-4">{{ error }}</v-alert>
              <v-btn type="submit" color="primary" size="large" block :loading="loading">Se connecter</v-btn>
            </v-form>
            <div class="text-center mt-4">
              <span class="text-medium-emphasis">Pas encore de compte ?</span>
              <router-link to="/register" class="ml-1">Creer un compte</router-link>
            </div>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </v-main>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

const email = ref("");
const password = ref("");
const showPassword = ref(false);
const loading = ref(false);
const error = ref("");

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

async function submit() {
  loading.value = true;
  error.value = "";
  try {
    await auth.login(email.value, password.value);
    router.push(route.query.redirect || "/");
  } catch (e) {
    error.value = e.response?.data?.detail || "Identifiants invalides.";
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
