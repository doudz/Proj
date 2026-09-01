<template>
  <div class="d-flex flex-column fill-height">
    <div class="px-6 pt-6 pb-2">
      <h1 class="text-h5 font-weight-bold">Vue multi-projets</h1>
      <p class="text-caption text-medium-emphasis mb-0">
        Toutes les taches de « {{ workspaceStore.current?.name }} » sur une seule frise, pour reperer les goulots
        d'etranglement : surcharge d'une personne, taches d'une meme categorie qui se chevauchent, etc.
      </p>
    </div>
    <v-divider class="mt-2" />
    <div v-if="!workspaceStore.current" class="pa-8 text-center text-medium-emphasis">
      Selectionnez d'abord un espace de travail.
    </div>
    <PortfolioGanttChart v-else :workspace-id="workspaceStore.current.id" :projects="projectStore.projects" class="flex-grow-1" />
  </div>
</template>

<script setup>
import PortfolioGanttChart from "@/components/gantt/PortfolioGanttChart.vue";
import { useProjectStore } from "@/stores/project";
import { useWorkspaceStore } from "@/stores/workspace";
import { onMounted, watch } from "vue";

const workspaceStore = useWorkspaceStore();
const projectStore = useProjectStore();

async function load() {
  if (workspaceStore.current) await projectStore.fetchProjects(workspaceStore.current.id);
}

onMounted(load);
watch(() => workspaceStore.current, load);
</script>
