<template>
  <div class="medical-hierarchy">
    <div v-if="store.loading" class="loading">Loading patient data...</div>
    <div v-else-if="store.error" class="error">Error: {{ store.error }}</div>
    <div v-else-if="store.patients.length === 0" class="empty-state">No patient data available</div>
    <div v-else class="hierarchy-container">
      <div class="header">
        <h2>Patient / Study / Series</h2>
        <div class="refresh-button" @click="store.loadAllData"><span>↻</span> Refresh</div>
      </div>

      <div class="hierarchy-content">
        <div class="panel">
          <h3>Patients</h3>
          <ul class="list">
            <li
              v-for="patient in store.patients"
              :key="patient.id"
              :class="{ active: patient.id === store.currentPatientId }"
              @click="store.selectPatient(patient.id)"
            >
              <div class="item-content">
                <div class="item-title">{{ patient.name }}</div>
                <div class="item-subtitle">ID: {{ patient.patientId }}</div>
              </div>
            </li>
          </ul>
        </div>

        <div class="panel">
          <h3>Studies</h3>
          <ul class="list">
            <li
              v-for="study in currentPatientStudies"
              :key="study.id"
              :class="{ active: study.id === store.currentStudyId }"
              @click="store.selectStudy(study.id)"
            >
              <div class="item-content">
                <div class="item-title">{{ study.description }}</div>
                <div class="item-subtitle">Date: {{ formatDate(study.date) }}</div>
              </div>
            </li>
          </ul>
        </div>

        <div class="panel">
          <h3>Series</h3>
          <ul class="list">
            <li
              v-for="series in currentStudySeries"
              :key="series.id"
              :class="{ active: series.id === store.currentSeriesId }"
              @click="store.selectSeries(series.id)"
            >
              <div class="item-content">
                <div class="item-title">{{ series.description }}</div>
                <div class="item-subtitle">
                  {{ series.modality }} - {{ series.instanceCount }} images
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMedicalDataStore } from '../stores/medicalData'

const store = useMedicalDataStore()

// Computed properties for displaying hierarchical data
const currentPatientStudies = computed(() => {
  const patient = store.currentPatient
  return patient ? patient.studies : []
})

const currentStudySeries = computed(() => {
  const study = store.currentStudy
  return study ? study.series : []
})

// Format DICOM date (YYYYMMDD) to a more readable format
function formatDate(dicomDate: string): string {
  if (!dicomDate || dicomDate === 'Unknown date') return dicomDate

  // DICOM dates are in YYYYMMDD format
  if (dicomDate.length === 8) {
    const year = dicomDate.substring(0, 4)
    const month = dicomDate.substring(4, 6)
    const day = dicomDate.substring(6, 8)
    return `${year}-${month}-${day}`
  }

  return dicomDate
}
</script>

<style scoped>
.medical-hierarchy {
  display: flex;
  flex-direction: column;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

.loading,
.error,
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  font-size: 1rem;
  color: #666;
}

.error {
  color: #e53935;
}

.hierarchy-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.header h2 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 500;
}

.refresh-button {
  cursor: pointer;
  color: #2196f3;
  display: flex;
  align-items: center;
  font-size: 0.9rem;
}

.refresh-button span {
  margin-right: 4px;
  font-size: 1.1rem;
}

.hierarchy-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e0e0e0;
  overflow: hidden;
}

.panel:last-child {
  border-right: none;
}

.panel h3 {
  margin: 0;
  padding: 8px 16px;
  font-size: 1rem;
  font-weight: 500;
  background-color: #f9f9f9;
  border-bottom: 1px solid #e0e0e0;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1;
}

.list li {
  padding: 8px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.2s;
}

.list li:hover {
  background-color: #f5f5f5;
}

.list li.active {
  background-color: #e3f2fd;
  border-left: 3px solid #2196f3;
}

.item-content {
  display: flex;
  flex-direction: column;
}

.item-title {
  font-weight: 500;
  margin-bottom: 4px;
}

.item-subtitle {
  font-size: 0.85rem;
  color: #666;
}
</style>
