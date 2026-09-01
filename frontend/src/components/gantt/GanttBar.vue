<template>
  <div
    v-if="task.is_milestone"
    class="gantt-milestone"
    :style="{ left: x + dayWidth / 2 - 8 + 'px', top: y + barTop + barHeight / 2 - 8 + 'px' }"
    :title="task.title"
    @pointerdown.stop="startDrag($event, 'move')"
    @click.stop
  ></div>
  <div
    v-else
    class="gantt-bar"
    :class="{ dragging }"
    :style="{ left: liveX + 'px', top: y + barTop + 'px', width: liveWidth + 'px', height: barHeight + 'px', background: task.color || defaultColor }"
    :title="task.title"
    @pointerdown.stop="startDrag($event, 'move')"
    @click.stop
  >
    <div class="gantt-bar-progress" :style="{ width: task.progress + '%' }"></div>
    <span class="gantt-bar-label">{{ task.title }}</span>
    <div class="gantt-handle left" @pointerdown.stop="startDrag($event, 'resize-start')"></div>
    <div class="gantt-handle right" @pointerdown.stop="startDrag($event, 'resize-end')"></div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  task: { type: Object, required: true },
  x: { type: Number, required: true },
  y: { type: Number, required: true },
  width: { type: Number, required: true },
  dayWidth: { type: Number, required: true },
  barTop: { type: Number, default: 6 },
  barHeight: { type: Number, default: 28 },
});
const emit = defineEmits(["click", "reschedule"]);

const defaultColor = "#42A5F5";
const dragging = ref(false);
const mode = ref(null);
const startPointerX = ref(0);
const offsetX = ref(0);
const offsetWidth = ref(0);

const liveX = computed(() => props.x + offsetX.value);
const liveWidth = computed(() => Math.max(props.dayWidth, props.width + offsetWidth.value));

function startDrag(event, dragMode) {
  mode.value = dragMode;
  dragging.value = true;
  startPointerX.value = event.clientX;
  offsetX.value = 0;
  offsetWidth.value = 0;
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
}

function onMove(event) {
  const deltaPx = event.clientX - startPointerX.value;
  if (mode.value === "move") {
    offsetX.value = deltaPx;
  } else if (mode.value === "resize-end") {
    offsetWidth.value = deltaPx;
  } else if (mode.value === "resize-start") {
    offsetX.value = Math.min(deltaPx, props.width - props.dayWidth);
    offsetWidth.value = -offsetX.value;
  }
}

function onUp() {
  window.removeEventListener("pointermove", onMove);
  window.removeEventListener("pointerup", onUp);
  const deltaDays = Math.round(offsetX.value / props.dayWidth);
  const widthDeltaDays = Math.round((offsetX.value + offsetWidth.value) / props.dayWidth) - deltaDays;
  dragging.value = false;
  if (deltaDays !== 0 || widthDeltaDays !== 0) {
    if (mode.value === "move") {
      emit("reschedule", { startDeltaDays: deltaDays, endDeltaDays: deltaDays });
    } else if (mode.value === "resize-end") {
      emit("reschedule", { startDeltaDays: 0, endDeltaDays: widthDeltaDays });
    } else if (mode.value === "resize-start") {
      emit("reschedule", { startDeltaDays: deltaDays, endDeltaDays: 0 });
    }
  } else if (mode.value === "move") {
    emit("click");
  }
  offsetX.value = 0;
  offsetWidth.value = 0;
  mode.value = null;
}
</script>

<style scoped>
.gantt-bar {
  position: absolute;
  border-radius: 6px;
  display: flex;
  align-items: center;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
  cursor: grab;
  overflow: visible;
  user-select: none;
}
.gantt-bar.dragging {
  cursor: grabbing;
  opacity: 0.85;
  z-index: 5;
}
.gantt-bar-progress {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 6px 0 0 6px;
}
.gantt-bar-label {
  position: relative;
  padding-left: 8px;
  font-size: 12px;
  color: white;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.3);
}
.gantt-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: ew-resize;
}
.gantt-handle.left {
  left: 0;
}
.gantt-handle.right {
  right: 0;
}
.gantt-milestone {
  position: absolute;
  width: 16px;
  height: 16px;
  background: #ffa726;
  transform: rotate(45deg);
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
}
</style>
