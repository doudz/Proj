<template>
  <v-card
    class="mb-2 task-card"
    elevation="1"
    :style="{ borderLeft: '4px solid ' + (task.color || 'transparent') }"
    @click="$emit('click')"
  >
    <v-card-text class="pb-2">
      <div class="d-flex flex-wrap ga-1 mb-1">
        <v-chip v-for="l in task.labels" :key="l.id" size="x-small" :color="l.color" label>{{ l.name }}</v-chip>
      </div>
      <div class="d-flex align-center">
        <v-icon v-if="task.is_milestone" icon="mdi-flag-checkered" size="16" class="mr-1" color="warning" />
        <v-tooltip v-if="task.is_blocked" location="top">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" icon="mdi-lock-outline" size="16" class="mr-1" color="warning" />
          </template>
          <span>Bloquee par : {{ task.blocking_predecessor_titles.join(", ") }}</span>
        </v-tooltip>
        <span class="text-body-2 font-weight-medium">{{ task.title }}</span>
      </div>
      <div class="d-flex align-center mt-2">
        <v-icon :icon="priorityIcon" :color="priorityColor" size="16" class="mr-1" />
        <span class="text-caption text-medium-emphasis">{{ dueLabel }}</span>
        <v-spacer />
        <div class="d-flex ml-n1">
          <v-avatar v-for="a in task.assignees.slice(0, 3)" :key="a.id" :color="a.avatar_color" size="22" class="ml-n1 avatar-border">
            <span class="text-caption text-white">{{ a.initials }}</span>
          </v-avatar>
          <v-tooltip v-for="c in task.external_assignees.slice(0, 2)" :key="'ext-' + c.id" location="top">
            <template #activator="{ props: tooltipProps }">
              <v-avatar v-bind="tooltipProps" :color="c.color" size="22" class="ml-n1 avatar-border external-avatar">
                <span class="text-caption text-white">{{ c.initials }}</span>
              </v-avatar>
            </template>
            <span>{{ c.name }} (externe)</span>
          </v-tooltip>
        </div>
      </div>
      <v-progress-linear v-if="task.progress > 0" :model-value="task.progress" height="4" rounded class="mt-2" color="success" />
      <div v-if="task.subtasks_count" class="text-caption text-medium-emphasis mt-1">
        <v-icon icon="mdi-file-tree-outline" size="14" /> {{ task.subtasks_count }} sous-tache(s)
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({ task: { type: Object, required: true } });
defineEmits(["click"]);

const priorityMap = {
  low: { icon: "mdi-arrow-down", color: "grey" },
  medium: { icon: "mdi-equal", color: "info" },
  high: { icon: "mdi-arrow-up", color: "warning" },
  urgent: { icon: "mdi-alert", color: "error" },
};

const priorityIcon = computed(() => priorityMap[props.task.priority]?.icon || "mdi-equal");
const priorityColor = computed(() => priorityMap[props.task.priority]?.color || "grey");

const dueLabel = computed(() => {
  if (!props.task.due_date) return "Sans echeance";
  return new Date(props.task.due_date).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
});
</script>

<style scoped>
.task-card {
  cursor: pointer;
}
.avatar-border {
  border: 2px solid white;
}
.external-avatar {
  border-style: dashed;
}
</style>
