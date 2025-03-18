<template>
  <div class="visualization-list">
    <h3>Loaded Visualizations</h3>
    <div class="visualization-items">
      <div
        v-for="(vis, index) in visualizations"
        :key="index"
        class="visualization-item"
        @click="$emit('select', index)"
        :class="{ active: index === activeIndex }"
      >
        <span>{{ vis.description }}</span>
        <div class="vis-controls">
          <button @click.stop="$emit('toggleVisibility', index)" class="toggle-btn">
            {{ vis.visible ? 'Hide' : 'Show' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Visualization } from '@/types/visualization'

defineProps<{
  visualizations: Visualization[]
  activeIndex: number
}>()

defineEmits<{
  (e: 'select', index: number): void
  (e: 'toggleVisibility', index: number): void
}>()
</script>

<style scoped>
.visualization-list {
  margin-top: 10px;
  padding: 8px;
  background-color: #f5f5f5;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.visualization-list h3 {
  margin: 0 0 5px 0;
  font-size: 0.9em;
}

.visualization-items {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 5px;
}

.visualization-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px;
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #ddd;
  font-size: 0.85em;
  cursor: pointer;
  transition: background-color 0.2s;
}

.visualization-item:hover {
  background-color: #f0f0f0;
}

.visualization-item.active {
  border-left: 3px solid #2196f3;
  background-color: #e3f2fd;
}

.vis-controls {
  display: flex;
  gap: 5px;
}

.toggle-btn {
  padding: 3px 6px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8em;
}
</style>
