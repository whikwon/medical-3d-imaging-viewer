<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import MedicalHierarchyView from './components/MedicalHierarchyView.vue'
import MultiViewRenderer from './components/MultiViewRenderer.vue'
import { useMedicalDataStore } from './stores/medicalData'
import { useRenderedItemsStore } from './stores/renderedItems'

const store = useMedicalDataStore()
const renderedItemsStore = useRenderedItemsStore()

const loading = computed(() => store.loading)
const error = computed(() => store.error)
const currentSeries = computed(() => store.currentSeries)
const isHierarchyCollapsed = ref(false)

// Handle rendering the selected series when user clicks on a series
function renderCurrentSeries() {
  if (currentSeries.value) {
    renderedItemsStore.addRenderedItem(currentSeries.value.id)
  }
}

onMounted(async () => {
  try {
    // Load all patient, study, and series data
    await store.loadAllData()
  } catch (err) {
    console.error('Failed to load medical data:', err)
  }
})
</script>

<template>
  <div class="app-container">
    <div class="medical-hierarchy-panel" :class="{ collapsed: isHierarchyCollapsed }">
      <MedicalHierarchyView @toggle-collapse="isHierarchyCollapsed = $event" />
    </div>

    <div class="viewer-panel">
      <div class="viewer-toolbar">
        <button v-if="currentSeries" class="render-button" @click="renderCurrentSeries">
          Render Selected Series
        </button>
        <div v-if="currentSeries" class="modality-info">
          {{
            currentSeries.modality === 'CT'
              ? 'CT data will render with orthogonal views (axial, sagittal, coronal)'
              : ''
          }}
        </div>
      </div>

      <div v-if="loading" class="loading">Loading images from Orthanc server...</div>
      <div v-else-if="error" class="error">Error: {{ error }}</div>
      <MultiViewRenderer v-else />
    </div>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.medical-hierarchy-panel {
  width: 40%;
  min-width: 300px;
  max-width: 500px;
  height: 100%;
  overflow: auto;
  border-right: 1px solid #e0e0e0;
  background-color: #fafafa;
  transition: width 0.3s ease;
}

.medical-hierarchy-panel.collapsed {
  width: 250px;
  min-width: 250px;
}

.viewer-panel {
  flex: 1;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.viewer-toolbar {
  height: 50px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.render-button {
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.render-button:hover {
  background-color: #1976d2;
}

.loading,
.error,
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  padding: 2rem;
  text-align: center;
  font-size: 1.2rem;
  color: #666;
}

.error {
  color: red;
}

.modality-info {
  margin-left: 16px;
  color: #666;
  font-size: 0.9rem;
  font-style: italic;
}
</style>
