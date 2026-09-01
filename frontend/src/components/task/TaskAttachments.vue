<template>
  <div>
    <div class="d-flex align-center mb-1">
      <span class="text-caption text-medium-emphasis">Pieces jointes</span>
      <v-spacer />
      <v-btn v-if="canEdit" size="x-small" variant="text" prepend-icon="mdi-upload" :loading="uploading" @click="triggerUpload">
        Ajouter
      </v-btn>
      <input ref="fileInput" type="file" class="d-none" @change="onFileChange" />
    </div>

    <v-list v-if="attachments.length" density="compact" class="py-0 bounded-list">
      <v-list-item v-for="att in attachments" :key="att.id" class="px-0">
        <template #prepend>
          <v-avatar v-if="att.is_image" size="28" rounded class="mr-2 thumb" @click="openLightbox(att)">
            <v-img :src="att.file" cover />
          </v-avatar>
          <v-icon v-else icon="mdi-file-outline" size="20" class="mr-2" @click="openFile(att)" />
        </template>
        <v-list-item-title class="text-caption text-truncate" style="max-width: 160px" @click="att.is_image ? openLightbox(att) : openFile(att)">
          {{ att.filename }}
        </v-list-item-title>
        <v-list-item-subtitle class="text-caption d-flex align-center ga-1">
          <v-chip :color="statusColor(att.status)" size="x-small" variant="tonal">{{ statusLabel(att.status) }}</v-chip>
          <span v-if="att.comments_count">- {{ att.comments_count }} remarque(s)</span>
        </v-list-item-subtitle>
        <template #append>
          <v-menu v-if="canReview">
            <template #activator="{ props: menuProps }">
              <v-btn v-bind="menuProps" icon="mdi-dots-vertical" variant="text" size="x-small" />
            </template>
            <v-list density="compact">
              <v-list-item prepend-icon="mdi-check-circle-outline" title="Approuver" @click="review(att, 'approve')" />
              <v-list-item prepend-icon="mdi-close-circle-outline" title="Demander une revision" @click="review(att, 'request-changes')" />
            </v-list>
          </v-menu>
          <v-btn v-if="canEdit" icon="mdi-delete-outline" variant="text" size="x-small" @click="remove(att)" />
        </template>
      </v-list-item>
    </v-list>
    <p v-else class="text-caption text-medium-emphasis">Aucune piece jointe.</p>

    <v-dialog v-model="lightbox" max-width="720">
      <v-card v-if="active">
        <v-card-title class="d-flex align-center text-body-1">
          {{ active.filename }}
          <v-chip :color="statusColor(active.status)" size="small" variant="tonal" class="ml-2">
            {{ statusLabel(active.status) }}
          </v-chip>
          <v-spacer />
          <template v-if="canReview">
            <v-btn size="small" variant="tonal" color="success" class="mr-1" @click="review(active, 'approve')">
              Approuver
            </v-btn>
            <v-btn size="small" variant="tonal" color="warning" @click="review(active, 'request-changes')">
              A revoir
            </v-btn>
          </template>
          <v-btn icon="mdi-close" variant="text" size="small" class="ml-1" @click="lightbox = false" />
        </v-card-title>
        <v-card-subtitle v-if="canReview" class="px-4 text-caption">
          Cliquez sur l'image pour epingler une remarque a un endroit precis.
        </v-card-subtitle>
        <v-card-text>
          <div class="image-wrap" @click="onImageClick">
            <img ref="imgRef" :src="active.file" class="proof-image" />
            <v-tooltip v-for="pin in pins" :key="pin.id" location="top">
              <template #activator="{ props: tipProps }">
                <div
                  v-bind="tipProps"
                  class="pin"
                  :style="{ left: pin.x_percent + '%', top: pin.y_percent + '%' }"
                  @click.stop
                >
                  {{ pins.indexOf(pin) + 1 }}
                </div>
              </template>
              <strong>{{ pin.author.first_name }}</strong> : {{ pin.body }}
            </v-tooltip>
          </div>

          <div v-if="pendingPin" class="d-flex align-center ga-2 mt-2">
            <v-text-field
              v-model="pendingPinText"
              placeholder="Votre remarque a cet endroit..."
              density="compact"
              hide-details
              autofocus
              @keyup.enter="submitPin"
            />
            <v-btn size="small" color="primary" :disabled="!pendingPinText.trim()" @click="submitPin">Epingler</v-btn>
            <v-btn size="small" variant="text" @click="pendingPin = null">Annuler</v-btn>
          </div>

          <v-divider class="my-3" />
          <div class="text-caption text-medium-emphasis mb-1">Remarques generales</div>
          <v-list density="compact" class="py-0">
            <v-list-item v-for="c in generalComments" :key="c.id" class="px-0">
              <v-list-item-title class="text-caption">
                <strong>{{ c.author.first_name }}</strong> : {{ c.body }}
              </v-list-item-title>
            </v-list-item>
          </v-list>
          <div v-if="canComment" class="d-flex align-center ga-2 mt-1">
            <v-text-field
              v-model="newComment"
              placeholder="Ajouter une remarque generale..."
              density="compact"
              hide-details
              @keyup.enter="submitGeneralComment"
            />
            <v-btn size="small" variant="tonal" :disabled="!newComment.trim()" @click="submitGeneralComment">Envoyer</v-btn>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import api from "@/services/api";
import { computed, ref, watch } from "vue";

const props = defineProps({
  taskId: { type: [String, Number], required: true },
  canEdit: { type: Boolean, default: false },
  canReview: { type: Boolean, default: false },
  canComment: { type: Boolean, default: false },
});

const attachments = ref([]);
const uploading = ref(false);
const fileInput = ref(null);
const lightbox = ref(false);
const active = ref(null);
const pins = ref([]);
const generalComments = ref([]);
const pendingPin = ref(null);
const pendingPinText = ref("");
const newComment = ref("");
const imgRef = ref(null);

const statusLabels = { pending: "En attente", approved: "Approuve", changes_requested: "A revoir" };
const statusColors = { pending: "grey", approved: "success", changes_requested: "warning" };

function statusLabel(status) {
  return statusLabels[status] || status;
}
function statusColor(status) {
  return statusColors[status] || "grey";
}

async function load() {
  const { data } = await api.get("/attachments/", { params: { task: props.taskId, page_size: 100 } });
  attachments.value = data.results ?? data;
}

watch(() => props.taskId, load);
load();

function triggerUpload() {
  fileInput.value?.click();
}

async function onFileChange(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  uploading.value = true;
  try {
    const form = new FormData();
    form.append("task", props.taskId);
    form.append("file", file);
    const { data } = await api.post("/attachments/", form, { headers: { "Content-Type": "multipart/form-data" } });
    attachments.value.unshift(data);
  } finally {
    uploading.value = false;
    event.target.value = "";
  }
}

async function remove(attachment) {
  if (!confirm(`Supprimer "${attachment.filename}" ?`)) return;
  await api.delete(`/attachments/${attachment.id}/`);
  attachments.value = attachments.value.filter((a) => a.id !== attachment.id);
}

async function review(attachment, action) {
  const { data } = await api.post(`/attachments/${attachment.id}/${action}/`);
  const idx = attachments.value.findIndex((a) => a.id === data.id);
  if (idx !== -1) attachments.value[idx] = data;
  if (active.value?.id === data.id) active.value = data;
}

function openFile(attachment) {
  window.open(attachment.file, "_blank");
}

async function openLightbox(attachment) {
  active.value = attachment;
  pendingPin.value = null;
  newComment.value = "";
  lightbox.value = true;
  const { data } = await api.get("/attachment-comments/", { params: { attachment: attachment.id, page_size: 200 } });
  const comments = data.results ?? data;
  pins.value = comments.filter((c) => c.x_percent !== null && c.y_percent !== null);
  generalComments.value = comments.filter((c) => c.x_percent === null || c.y_percent === null);
}

function onImageClick(event) {
  if (!props.canReview && !props.canComment) return;
  if (event.target !== imgRef.value) return;
  const rect = imgRef.value.getBoundingClientRect();
  pendingPin.value = {
    x_percent: ((event.clientX - rect.left) / rect.width) * 100,
    y_percent: ((event.clientY - rect.top) / rect.height) * 100,
  };
  pendingPinText.value = "";
}

async function submitPin() {
  if (!pendingPinText.value.trim() || !pendingPin.value) return;
  const { data } = await api.post("/attachment-comments/", {
    attachment: active.value.id,
    body: pendingPinText.value.trim(),
    x_percent: pendingPin.value.x_percent,
    y_percent: pendingPin.value.y_percent,
  });
  pins.value.push(data);
  const idx = attachments.value.findIndex((a) => a.id === active.value.id);
  if (idx !== -1) attachments.value[idx].comments_count += 1;
  pendingPin.value = null;
  pendingPinText.value = "";
}

async function submitGeneralComment() {
  if (!newComment.value.trim()) return;
  const { data } = await api.post("/attachment-comments/", {
    attachment: active.value.id,
    body: newComment.value.trim(),
  });
  generalComments.value.push(data);
  const idx = attachments.value.findIndex((a) => a.id === active.value.id);
  if (idx !== -1) attachments.value[idx].comments_count += 1;
  newComment.value = "";
}
</script>

<style scoped>
.bounded-list {
  max-height: 150px;
  overflow-y: auto;
}
.thumb {
  cursor: pointer;
}
.image-wrap {
  position: relative;
  display: inline-block;
  max-width: 100%;
  cursor: crosshair;
}
.proof-image {
  max-width: 100%;
  max-height: 50vh;
  display: block;
  border-radius: 4px;
}
.pin {
  position: absolute;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ef5350;
  color: white;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
}
</style>
