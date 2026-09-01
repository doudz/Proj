<template>
  <div>
    <div class="d-flex align-center mb-1">
      <span class="text-caption text-medium-emphasis">Temps passe</span>
      <v-spacer />
      <span class="text-caption font-weight-medium">{{ formatMinutes(totalMinutes) }}</span>
    </div>

    <div v-if="canTrack" class="d-flex align-center ga-2 mb-2">
      <v-btn
        v-if="!activeEntry"
        size="small"
        variant="tonal"
        color="primary"
        prepend-icon="mdi-play"
        @click="start"
      >
        Demarrer le chrono
      </v-btn>
      <template v-else>
        <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-stop" @click="stop">
          Arreter ({{ formatMinutes(runningMinutes) }})
        </v-btn>
      </template>
      <v-btn size="small" variant="text" prepend-icon="mdi-plus" @click="manualDialog = true">Saisie manuelle</v-btn>
    </div>

    <v-list v-if="entries.length" density="compact" class="py-0 bounded-list">
      <v-list-item v-for="entry in entries" :key="entry.id" class="px-0">
        <template #prepend>
          <v-avatar :color="entry.user.avatar_color" size="20" class="mr-2">
            <span class="text-white" style="font-size: 9px">{{ entry.user.initials }}</span>
          </v-avatar>
        </template>
        <v-list-item-title class="text-caption">
          {{ formatMinutes(entry.duration_minutes) }}
          <span v-if="entry.is_running" class="text-primary">(en cours)</span>
          <span v-if="entry.note"> - {{ entry.note }}</span>
        </v-list-item-title>
        <v-list-item-subtitle class="text-caption">{{ formatDate(entry.started_at) }}</v-list-item-subtitle>
        <template #append>
          <v-btn
            v-if="canDelete(entry)"
            icon="mdi-close"
            variant="text"
            size="x-small"
            @click="remove(entry)"
          />
        </template>
      </v-list-item>
    </v-list>
    <p v-else class="text-caption text-medium-emphasis">Aucun temps enregistre.</p>

    <v-dialog v-model="manualDialog" max-width="380">
      <v-card title="Ajouter du temps">
        <v-card-text>
          <v-row dense>
            <v-col cols="6">
              <v-text-field v-model="manual.date" label="Date" type="date" density="compact" hide-details />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="manual.minutes"
                label="Duree (minutes)"
                type="number"
                min="1"
                density="compact"
                hide-details
              />
            </v-col>
            <v-col cols="12">
              <v-text-field v-model="manual.note" label="Note (optionnel)" density="compact" hide-details />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="manualDialog = false">Annuler</v-btn>
          <v-btn color="primary" :disabled="!manual.minutes" @click="addManual">Ajouter</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import api from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

const props = defineProps({
  taskId: { type: [String, Number], required: true },
  canTrack: { type: Boolean, default: false },
  canManageAll: { type: Boolean, default: false },
});

const authStore = useAuthStore();
const entries = ref([]);
const manualDialog = ref(false);
const manual = reactive({ date: new Date().toISOString().slice(0, 10), minutes: null, note: "" });
const nowTick = ref(Date.now());
let tickTimer = null;

const activeEntry = computed(() =>
  entries.value.find((e) => e.is_running && e.user.id === authStore.user?.id)
);

const runningMinutes = computed(() => {
  if (!activeEntry.value) return 0;
  return Math.floor((nowTick.value - new Date(activeEntry.value.started_at).getTime()) / 60000);
});

const totalMinutes = computed(() =>
  entries.value.reduce((sum, e) => sum + (e.is_running ? runningMinutes.value : e.duration_minutes), 0)
);

function canDelete(entry) {
  return props.canManageAll || entry.user.id === authStore.user?.id;
}

function formatMinutes(total) {
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (h === 0) return `${m} min`;
  return `${h} h ${String(m).padStart(2, "0")}`;
}

function formatDate(value) {
  return new Date(value).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
}

async function load() {
  const { data } = await api.get("/time-entries/", { params: { task: props.taskId, page_size: 200 } });
  entries.value = data.results ?? data;
}

watch(() => props.taskId, load);

onMounted(() => {
  load();
  tickTimer = setInterval(() => {
    nowTick.value = Date.now();
  }, 30000);
});

onBeforeUnmount(() => clearInterval(tickTimer));

async function start() {
  const { data } = await api.post("/time-entries/start/", { task: props.taskId });
  entries.value.unshift(data);
}

async function stop() {
  if (!activeEntry.value) return;
  const { data } = await api.post(`/time-entries/${activeEntry.value.id}/stop/`);
  const idx = entries.value.findIndex((e) => e.id === data.id);
  if (idx !== -1) entries.value[idx] = data;
}

async function addManual() {
  if (!manual.minutes) return;
  const started = new Date(`${manual.date}T09:00:00`);
  const ended = new Date(started.getTime() + manual.minutes * 60000);
  const { data } = await api.post("/time-entries/", {
    task: props.taskId,
    started_at: started.toISOString(),
    ended_at: ended.toISOString(),
    note: manual.note,
  });
  entries.value.unshift(data);
  manualDialog.value = false;
  manual.minutes = null;
  manual.note = "";
}

async function remove(entry) {
  await api.delete(`/time-entries/${entry.id}/`);
  entries.value = entries.value.filter((e) => e.id !== entry.id);
}
</script>

<style scoped>
.bounded-list {
  max-height: 130px;
  overflow-y: auto;
}
</style>
