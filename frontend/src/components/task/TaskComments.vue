<template>
  <div class="d-flex flex-column fill-height">
    <div class="flex-grow-1 overflow-y-auto pa-3 comments-scroll" ref="scrollEl">
      <div v-for="c in comments" :key="c.id" class="d-flex mb-3">
        <v-avatar :color="c.author.avatar_color" size="30" class="mr-2">
          <span class="text-caption text-white">{{ c.author.initials }}</span>
        </v-avatar>
        <div>
          <div class="text-caption">
            <strong>{{ c.author.first_name }} {{ c.author.last_name }}</strong>
            <span class="text-medium-emphasis ml-1">{{ formatTime(c.created_at) }}</span>
          </div>
          <div class="text-body-2 comment-bubble">{{ c.body }}</div>
        </div>
      </div>
      <p v-if="!comments.length" class="text-medium-emphasis text-caption">Aucun message. Lancez la discussion !</p>
      <p v-if="typingLabel" class="text-caption text-medium-emphasis font-italic">{{ typingLabel }}</p>
    </div>
    <v-divider />
    <div v-if="canComment" class="pa-2 d-flex align-center ga-2">
      <v-text-field
        v-model="draft"
        placeholder="Ecrire un message..."
        density="compact"
        hide-details
        variant="solo"
        flat
        @keyup.enter="send"
        @keyup="notifyTyping"
      />
      <v-btn icon="mdi-send" color="primary" :disabled="!draft.trim()" @click="send" />
    </div>
    <p v-else class="pa-2 text-caption text-medium-emphasis mb-0">Les observateurs ne peuvent pas commenter.</p>
  </div>
</template>

<script setup>
import api from "@/services/api";
import { connectSocket } from "@/services/ws";
import { useAuthStore } from "@/stores/auth";
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  taskId: { type: [String, Number], required: true },
  canComment: { type: Boolean, default: true },
});

const comments = ref([]);
const draft = ref("");
const scrollEl = ref(null);
const typingLabel = ref("");
const authStore = useAuthStore();
let socket = null;
let typingTimeout = null;

async function load() {
  const { data } = await api.get("/comments/", { params: { task: props.taskId, page_size: 200 } });
  comments.value = data.results ?? data;
  await nextTick();
  scrollToBottom();
  socket?.close();
  socket = connectSocket(`tasks/${props.taskId}/chat`, (message) => {
    if (message.kind === "comment.created") {
      comments.value.push(message.payload);
      nextTick(scrollToBottom);
    } else if (message.kind === "presence" && message.payload.status === "typing") {
      if (message.payload.user_id !== authStore.user?.id) {
        typingLabel.value = "Quelqu'un est en train d'ecrire...";
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => (typingLabel.value = ""), 2000);
      }
    }
  });
}

function scrollToBottom() {
  if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight;
}

async function send() {
  if (!draft.value.trim()) return;
  await api.post("/comments/", { task: props.taskId, body: draft.value.trim() });
  draft.value = "";
}

function notifyTyping() {
  socket?.send({ type: "typing" });
}

function formatTime(value) {
  return new Date(value).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

watch(() => props.taskId, load, { immediate: true });
onBeforeUnmount(() => socket?.close());
</script>

<style scoped>
.comments-scroll {
  max-height: 100%;
}
.comment-bubble {
  background: #f0f2f5;
  border-radius: 8px;
  padding: 6px 10px;
  display: inline-block;
  max-width: 100%;
  white-space: pre-wrap;
}
</style>
