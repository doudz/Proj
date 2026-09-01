<template>
  <div v-if="projectStore.current" class="d-flex flex-column fill-height">
    <div class="px-6 pt-6 pb-2">
      <div class="d-flex align-center">
        <v-avatar :color="projectStore.current.color" rounded="lg" class="mr-3">
          <v-icon :icon="projectStore.current.icon" color="white" />
        </v-avatar>
        <div>
          <h1 class="text-h5 font-weight-bold">{{ projectStore.current.name }}</h1>
          <p class="text-caption text-medium-emphasis mb-0">{{ projectStore.current.tasks_count }} tache(s) - {{ projectStore.current.progress }}% termine</p>
        </div>
        <v-spacer />
        <v-avatar-group class="mr-4">
          <v-avatar v-for="m in projectStore.current.members.slice(0, 5)" :key="m.id" :color="m.avatar_color" size="32" class="ml-n2">
            <span class="text-caption text-white">{{ m.initials }}</span>
          </v-avatar>
        </v-avatar-group>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateTask()">Nouvelle tache</v-btn>
      </div>
      <v-tabs v-model="tab" class="mt-4">
        <v-tab value="board" prepend-icon="mdi-view-column-outline">Tableau</v-tab>
        <v-tab value="gantt" prepend-icon="mdi-chart-gantt">Gantt</v-tab>
        <v-tab value="list" prepend-icon="mdi-format-list-bulleted">Liste</v-tab>
        <v-tab value="calendar" prepend-icon="mdi-calendar-month-outline">Calendrier</v-tab>
      </v-tabs>
    </div>
    <v-divider />
    <v-window v-model="tab" class="flex-grow-1 overflow-auto">
      <v-window-item value="board" class="pa-4">
        <KanbanBoard :project="projectStore.current" @open-task="openTask" @create-task="openCreateTask" />
      </v-window-item>
      <v-window-item value="gantt" class="fill-height">
        <GanttChart :project="projectStore.current" @open-task="openTask" />
      </v-window-item>
      <v-window-item value="list" class="pa-4">
        <TaskListView :project="projectStore.current" @open-task="openTask" />
      </v-window-item>
      <v-window-item value="calendar" class="pa-4">
        <CalendarView :project="projectStore.current" @open-task="openTask" />
      </v-window-item>
    </v-window>

    <TaskDetailDialog
      v-model="taskDialog"
      :task-id="selectedTaskId"
      :project="projectStore.current"
      :default-column="defaultColumn"
      @created="onTaskCreated"
      @open-task="openTask"
    />
  </div>
</template>

<script setup>
import CalendarView from "@/components/calendar/CalendarView.vue";
import GanttChart from "@/components/gantt/GanttChart.vue";
import KanbanBoard from "@/components/kanban/KanbanBoard.vue";
import TaskDetailDialog from "@/components/task/TaskDetailDialog.vue";
import TaskListView from "@/components/task/TaskListView.vue";
import { connectSocket } from "@/services/ws";
import { useNotificationStore } from "@/stores/notification";
import { useProjectStore } from "@/stores/project";
import { useTaskStore } from "@/stores/task";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({ id: { type: [String, Number], required: true } });

const projectStore = useProjectStore();
const taskStore = useTaskStore();
const notificationStore = useNotificationStore();

const tab = ref("board");
const taskDialog = ref(false);
const selectedTaskId = ref(null);
const defaultColumn = ref(null);
let socket = null;

async function load(id) {
  await projectStore.fetchProject(id);
  await taskStore.fetchTasks(id);
  socket?.close();
  socket = connectSocket(`projects/${id}`, (message) => {
    if (message.kind?.startsWith("task.")) {
      taskStore.applyRealtimeEvent(message.kind, message.payload);
    } else if (message.kind === "notification.created") {
      notificationStore.pushRealtime(message.payload);
    }
  });
}

onMounted(() => load(props.id));
watch(() => props.id, (id) => load(id));
onBeforeUnmount(() => socket?.close());

function openTask(id) {
  selectedTaskId.value = id;
  defaultColumn.value = null;
  taskDialog.value = true;
}

function openCreateTask(columnId = null) {
  selectedTaskId.value = null;
  defaultColumn.value = columnId;
  taskDialog.value = true;
}

function onTaskCreated(task) {
  selectedTaskId.value = task.id;
}
</script>
