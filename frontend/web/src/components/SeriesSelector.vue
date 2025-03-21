<template>
  <div class="series-selection-container">
    <h3>Select Data</h3>
    <div class="series-selection">
      <select v-model="selectedStudy" @change="handleStudyChange" :disabled="loadingStudies">
        <option value="">Select a study</option>
        <option v-for="study in studies" :key="study.ID" :value="study.ID">
          {{ study.PatientMainDicomTags.PatientName || 'Unknown' }} -
          {{ study.MainDicomTags.StudyDescription || 'Unknown Study' }}
        </option>
      </select>

      <select v-if="selectedStudy" v-model="selectedSeries" :disabled="loadingSeries">
        <option value="">Select a series</option>
        <option v-for="series in seriesList" :key="series.ID" :value="series.ID">
          {{ series.MainDicomTags.SeriesDescription || 'Unknown Series' }} -
          {{ series.MainDicomTags.SeriesNumber || 'Unknown' }}
          ({{ series.MainDicomTags.Modality || 'Unknown' }})
        </option>
      </select>

      <button @click="loadSeries" :disabled="!selectedSeries || loading" class="load-btn">
        Add to Viewer
      </button>
    </div>

    <div v-if="loading" class="loading">
      <p>Loading data... Please wait.</p>
      <div class="loader"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { fetchSeriesData, fetchSeriesForStudy, fetchStudies } from '@/services/orthancService'
import type { Series, Study } from '@/types/orthanc'
import { onMounted, ref } from 'vue'

// Define props and emits
const emit = defineEmits<{
  (e: 'seriesLoaded', seriesId: string, series: Series, vtiData: Blob): void
}>()

// State
const studies = ref<Study[]>([])
const seriesList = ref<Series[]>([])
const selectedStudy = ref('')
const selectedSeries = ref('')
const loading = ref(false)
const loadingStudies = ref(false)
const loadingSeries = ref(false)

// Load studies on component mount
onMounted(loadStudies)

// Fetch all studies from Orthanc
async function loadStudies() {
  loadingStudies.value = true
  try {
    studies.value = await fetchStudies()
  } catch (error) {
    console.error('Error loading studies:', error)
  } finally {
    loadingStudies.value = false
  }
}

// Handle study selection change
async function handleStudyChange() {
  if (!selectedStudy.value) {
    seriesList.value = []
    selectedSeries.value = ''
    return
  }

  loadingSeries.value = true
  try {
    // Load series for the selected study
    seriesList.value = await fetchSeriesForStudy(selectedStudy.value)
  } catch (error) {
    console.error('Error loading series:', error)
  } finally {
    loadingSeries.value = false
  }
}

// Load the selected series
async function loadSeries() {
  if (!selectedSeries.value) return

  loading.value = true
  try {
    const seriesId = selectedSeries.value
    const series = seriesList.value.find((s) => s.ID === seriesId)

    if (!series) {
      throw new Error('Series not found')
    }

    // Fetch data from the backend
    const vtiData = await fetchSeriesData(seriesId)

    // Emit the loaded series data to parent component
    emit('seriesLoaded', seriesId, series, vtiData)

    // Clear the selection after successful loading
    // But keep the study selected to allow adding more series from the same study
    selectedSeries.value = ''
  } catch (error: unknown) {
    console.error('Error loading data:', error)
    if (error instanceof Error) {
      alert('Failed to load data: ' + error.message)
    } else {
      alert('Failed to load data: unknown error')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.series-selection-container {
  margin-bottom: 15px;
  padding: 8px;
  background-color: #f5f5f5;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.series-selection-container h3 {
  margin: 0 0 8px 0;
  font-size: 0.9em;
}

.series-selection {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

select {
  padding: 6px;
  border-radius: 4px;
  border: 1px solid #ccc;
  width: 100%;
}

.load-btn {
  padding: 6px 12px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.load-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px;
}

.loader {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
