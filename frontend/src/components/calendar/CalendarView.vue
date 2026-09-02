<template>
  <div>
    <div class="d-flex align-center mb-4">
      <v-btn icon="mdi-chevron-left" variant="text" @click="shiftMonth(-1)" />
      <h2 class="text-h6 mx-2 text-capitalize">{{ monthLabel }}</h2>
      <v-btn icon="mdi-chevron-right" variant="text" @click="shiftMonth(1)" />
      <v-spacer />
      <v-btn size="small" variant="tonal" @click="cursor = new Date()">Aujourd'hui</v-btn>
    </div>
    <div class="calendar-grid">
      <div v-for="d in weekdays" :key="d" class="calendar-weekday">{{ d }}</div>
      <div
        v-for="cell in cells"
        :key="cell.key"
        class="calendar-cell"
        :class="{ 'other-month': !cell.inMonth, today: cell.isToday }"
      >
        <div class="calendar-date">{{ cell.date.getDate() }}</div>
        <div class="calendar-tasks">
          <v-chip
            v-for="task in cell.tasks"
            :key="task.id"
            size="x-small"
            class="mb-1"
            :color="priorityColor(task.priority)"
            label
            @click="$emit('open-task', task.id)"
          >
            <span v-if="task.color" class="task-color-dot" :style="{ backgroundColor: task.color }"></span>
            {{ task.title }}
          </v-chip>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatDate } from "@/components/gantt/ganttMath";
import { useTaskStore } from "@/stores/task";
import { computed, ref } from "vue";

defineEmits(["open-task"]);
const taskStore = useTaskStore();

const cursor = ref(new Date());
const weekdays = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const priorityColors = { low: "grey", medium: "info", high: "warning", urgent: "error" };
function priorityColor(p) {
  return priorityColors[p] || "grey";
}

const monthLabel = computed(() =>
  new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" }).format(cursor.value)
);

const tasksByDate = computed(() => {
  const map = {};
  for (const task of taskStore.tasks) {
    if (!task.due_date) continue;
    if (!map[task.due_date]) map[task.due_date] = [];
    map[task.due_date].push(task);
  }
  return map;
});

const cells = computed(() => {
  const year = cursor.value.getFullYear();
  const month = cursor.value.getMonth();
  const firstOfMonth = new Date(year, month, 1);
  const startOffset = (firstOfMonth.getDay() + 6) % 7; // lundi = 0
  const gridStart = new Date(year, month, 1 - startOffset);
  const todayIso = formatDate(new Date());

  const out = [];
  for (let i = 0; i < 42; i++) {
    const date = new Date(gridStart);
    date.setDate(gridStart.getDate() + i);
    const iso = formatDate(date);
    out.push({
      key: iso,
      date,
      inMonth: date.getMonth() === month,
      isToday: iso === todayIso,
      tasks: tasksByDate.value[iso] || [],
    });
  }
  return out;
});

function shiftMonth(delta) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1);
}
</script>

<style scoped>
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.calendar-weekday {
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  padding-bottom: 4px;
  color: rgba(0, 0, 0, 0.6);
}
.calendar-cell {
  min-height: 110px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  padding: 4px;
}
.calendar-cell.other-month {
  background: rgba(0, 0, 0, 0.02);
  opacity: 0.6;
}
.calendar-cell.today {
  border-color: #1976d2;
  border-width: 2px;
}
.calendar-date {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
}
.calendar-tasks {
  display: flex;
  flex-direction: column;
}
.task-color-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 4px;
  flex: none;
}
</style>
