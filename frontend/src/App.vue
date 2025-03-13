<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import CornerstoneMultiFrame from './components/CornerstoneMultiFrame.vue'
import MedicalHierarchyView from './components/MedicalHierarchyView.vue'
import { useMedicalDataStore } from './stores/medicalData'

const store = useMedicalDataStore()
const loading = computed(() => store.loading)
const error = computed(() => store.error)
const currentImageIds = computed(() => store.currentImageIds)

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
    <div class="medical-hierarchy-panel">
      <MedicalHierarchyView />
    </div>

    <div class="viewer-panel">
      <div v-if="loading" class="loading">Loading images from Orthanc server...</div>
      <div v-else-if="error" class="error">Error: {{ error }}</div>
      <div v-else-if="currentImageIds.length === 0" class="empty-state">
        No images available. Please select a series from the list.
      </div>
      <CornerstoneMultiFrame v-else :imageIds="currentImageIds" />
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
}

.viewer-panel {
  flex: 1;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
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
</style>
