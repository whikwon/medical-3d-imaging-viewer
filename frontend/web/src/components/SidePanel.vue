<template>
  <div class="side-panel" :class="{ 'side-panel-collapsed': isCollapsed }">
    <div class="side-panel-header">
      <h3>Medical Viewer</h3>
      <button @click="togglePanel" class="toggle-btn">
        {{ isCollapsed ? '→' : '←' }}
      </button>
    </div>
    <div class="side-panel-content">
      <!-- Active Visualizations -->
      <div class="section">
        <h4>Active Visualizations</h4>
        <div v-if="visualizations.length === 0" class="empty-state">No visualizations loaded</div>
        <div v-else class="visualization-list">
          <div
            v-for="(vis, index) in visualizations"
            :key="index"
            class="visualization-item"
            :class="{
              'visualization-item-active': activeVolume === vis || activeMultiframe === vis,
            }"
            @click="selectVisualization(index)"
          >
            <div class="visualization-info">
              <span class="visualization-name">{{ vis.description }}</span>
              <span class="visualization-type">{{ vis.type }}</span>
            </div>
            <div class="visualization-controls">
              <button
                class="control-btn"
                @click.stop="toggleVisibility(index)"
                :title="vis.visible ? 'Hide' : 'Show'"
              >
                {{ vis.visible ? '👁️' : '👁️‍🗨️' }}
              </button>
              <button class="control-btn" @click.stop="removeVisualization(index)" title="Remove">
                ❌
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Patient Study Series Selector -->
      <PatientStudySeriesSelector
        :selected-patient="selectedPatient"
        :active-series-id="activeSeriesId"
        :loading-series-id="loadingSeriesId"
        @select-patient="$emit('select-patient', $event)"
        @select-series="$emit('select-series', $event)"
      />
    </div>
  </div>
  <!-- Show side panel button when collapsed -->
  <button v-if="isCollapsed" @click="togglePanel" class="show-side-panel-btn">Show Panel</button>
</template>

<script setup lang="ts">
import PatientStudySeriesSelector from '@/components/PatientStudySeriesSelector.vue'
import type { Patient, Series } from '@/types/orthanc'
import type { Visualization } from '@/types/visualization'
import { defineEmits, defineProps } from 'vue'

// Define props
const props = defineProps<{
  isCollapsed: boolean
  visualizations: Visualization[]
  activeVolume: Visualization | null
  activeMultiframe: Visualization | null
  selectedPatient: Patient | null
  activeSeriesId: string | null
  loadingSeriesId: string | null
}>()

// Define emits
const emit = defineEmits<{
  (e: 'update:isCollapsed', value: boolean): void
  (e: 'select-visualization', index: number): void
  (e: 'toggle-visibility', index: number): void
  (e: 'remove-visualization', index: number): void
  (e: 'select-patient', patient: Patient): void
  (e: 'select-series', series: Series): void
}>()

// Toggle side panel
function togglePanel() {
  emit('update:isCollapsed', !props.isCollapsed)
}

// Pass through event handlers
function selectVisualization(index: number) {
  emit('select-visualization', index)
}

function toggleVisibility(index: number) {
  emit('toggle-visibility', index)
}

function removeVisualization(index: number) {
  emit('remove-visualization', index)
}
</script>

<style scoped>
/* Side Panel Styles */
.side-panel {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 320px;
  background-color: rgba(255, 255, 255, 0.98);
  border-right: 1px solid #ddd;
  transition: transform 0.3s ease;
  z-index: 100;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
}

.side-panel-collapsed {
  transform: translateX(-320px);
}

.side-panel-header {
  padding: 1rem;
  background-color: #2196f3;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.side-panel-header h3 {
  margin: 0;
  font-size: 1em;
  font-weight: 500;
}

.toggle-btn {
  background: none;
  border: none;
  color: white;
  font-size: 1em;
  cursor: pointer;
  padding: 0.5rem;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.toggle-btn:hover {
  opacity: 1;
}

.side-panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 0.5rem;
}

/* Show side panel button when collapsed */
.show-side-panel-btn {
  position: absolute;
  left: 0;
  top: 10px;
  transform: none;
  padding: 6px 10px;
  background-color: rgba(33, 150, 243, 0.8);
  color: white;
  border: none;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
  z-index: 100;
  font-size: 0.8em;
}

.show-side-panel-btn:hover {
  background-color: rgba(33, 150, 243, 1);
}

.section {
  margin-bottom: 1.5rem;
  padding: 0 0.5rem;
}

.section h4 {
  margin: 0 0 0.5rem 0;
  color: #2196f3;
  font-size: 0.8em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

/* Visualization List Styles */
.visualization-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.visualization-item {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 0.75rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
  cursor: pointer;
}

.visualization-item:hover {
  border-color: #2196f3;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.visualization-item-active {
  border-color: #2196f3;
  background-color: #e3f2fd;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.2);
}

.visualization-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.visualization-name {
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.85em;
}

.visualization-type {
  font-size: 0.75em;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.visualization-controls {
  display: flex;
  gap: 0.5rem;
  z-index: 1; /* Ensure controls are clickable */
}

.control-btn {
  background: none;
  border: none;
  padding: 0.25rem;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s;
  z-index: 2; /* Ensure buttons are clickable */
}

.control-btn:hover {
  opacity: 1;
}

.empty-state {
  text-align: center;
  color: #666;
  padding: 0.75rem;
  background: #f5f5f5;
  border-radius: 6px;
  font-size: 0.8em;
}
</style>
