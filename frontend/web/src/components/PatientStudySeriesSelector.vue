<template>
  <div class="section">
    <!-- Patient List -->
    <div class="section">
      <h4>Patients</h4>
      <div v-if="loadingPatients" class="loading">
        <div class="loader"></div>
        <p>Loading patients...</p>
      </div>
      <div v-else-if="patientError" class="error">
        <p>{{ patientError }}</p>
      </div>
      <div v-else class="patients">
        <div
          v-for="patient in patients"
          :key="patient.ID"
          class="patient-card"
          @click="$emit('select-patient', patient)"
          :class="{ 'patient-card-active': selectedPatient?.ID === patient.ID }"
        >
          <h3>{{ patient.MainDicomTags.PatientName || 'Unknown Patient' }}</h3>
          <p>ID: {{ patient.MainDicomTags.PatientID || 'N/A' }}</p>
          <p>Studies: {{ patient.Studies.length || 0 }}</p>
        </div>
      </div>
    </div>

    <!-- Study/Series List -->
    <div v-if="selectedPatient" class="section">
      <h4>Studies & Series</h4>
      <div v-if="loading" class="loading">
        <div class="loader"></div>
      </div>
      <div v-else-if="error" class="error">
        {{ error }}
      </div>
      <div v-else class="studies">
        <div v-for="study in studies" :key="study.ID" class="study-item">
          <div class="study-header" @click="toggleStudy(study.ID)">
            <span>{{ study.PatientMainDicomTags.PatientName || 'Unknown Patient' }}</span>
            <span class="study-date">{{ formatDate(study.MainDicomTags.StudyDate) }}</span>
          </div>
          <div v-if="expandedStudies.includes(study.ID)" class="series-list">
            <div
              v-for="series in study.series"
              :key="series.ID"
              class="series-item"
              @click="selectSeries(series)"
              :class="{
                'series-item-active': activeSeriesId === series.ID,
                'series-item-loading': loadingSeriesId === series.ID,
              }"
            >
              <span>{{ series.MainDicomTags.SeriesDescription || 'Unknown Series' }}</span>
              <span class="series-modality">{{ series.MainDicomTags.Modality }}</span>
              <div v-if="loadingSeriesId === series.ID" class="series-loading">
                <div class="loader"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Labels for Selected Series -->
    <div v-if="activeSeriesId" class="section">
      <h4>Available Labels</h4>
      <div v-if="loadingLabels" class="loading">
        <div class="loader"></div>
        <p>Loading labels...</p>
      </div>
      <div v-else-if="labelError" class="error">
        <p>{{ labelError }}</p>
      </div>
      <div v-else-if="availableLabels.length === 0" class="empty-state">
        No labels available for this series
      </div>
      <div v-else class="labels-list">
        <div
          v-for="label in availableLabels"
          :key="label"
          class="label-item"
          @click="toggleLabel(label)"
          :class="{ 'label-item-active': selectedLabels.includes(label) }"
        >
          <span class="label-name">{{ label }}</span>
          <span class="label-status">{{ selectedLabels.includes(label) ? '✓' : '' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  fetchPatients,
  fetchSeriesForStudy,
  fetchStudies,
  fetchAvailableLabels,
  fetchLabelContent,
} from '@/services/orthancService'
import type { Patient, Series, Study } from '@/types/orthanc'
import type { Label } from '@/types/visualization'
import { onMounted, ref, watch } from 'vue'

const props = defineProps<{
  selectedPatient: Patient | null
  activeSeriesId: string | null
  loadingSeriesId: string | null
  visualizations: Visualization[]
}>()

const emit = defineEmits<{
  (e: 'select-patient', patient: Patient): void
  (e: 'select-series', series: Series): void
  (e: 'select-label', label: Label, seriesId: string): void
  (e: 'deselect-label', labelId: string, seriesId: string): void
}>()

// Study list state
const studies = ref<(Study & { series?: Series[] })[]>([])
const expandedStudies = ref<string[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// Patient selection state
const patients = ref<Patient[]>([])
const loadingPatients = ref(true)
const patientError = ref<string | null>(null)

// Labels state
const availableLabels = ref<string[]>([])
const selectedLabels = ref<string[]>([])
const loadingLabels = ref(false)
const labelError = ref<string | null>(null)

onMounted(async () => {
  // Load patients on component mount
  try {
    loadingPatients.value = true
    patients.value = await fetchPatients()
  } catch (e) {
    patientError.value = 'Failed to load patients. Please try again.'
    console.error('Error loading patients:', e)
  } finally {
    loadingPatients.value = false
  }
})

// Study list functions
function toggleStudy(studyId: string) {
  const index = expandedStudies.value.indexOf(studyId)
  if (index === -1) {
    expandedStudies.value.push(studyId)
  } else {
    expandedStudies.value.splice(index, 1)
  }
}

function formatDate(dateStr?: string) {
  if (!dateStr) return 'N/A'

  // Handle DICOM date format (YYYYMMDD)
  if (dateStr.length === 8) {
    const year = dateStr.substring(0, 4)
    const month = dateStr.substring(4, 6)
    const day = dateStr.substring(6, 8)
    const date = new Date(`${year}-${month}-${day}`)
    return date.toLocaleDateString()
  }

  // Fallback for other date formats
  const date = new Date(dateStr)
  return date.toLocaleDateString()
}

// Function to load studies for a patient
async function loadStudiesForPatient(patientId: string) {
  try {
    loading.value = true
    const allStudies = await fetchStudies()
    // Filter studies for the current patient
    studies.value = allStudies.filter((study) => study.ParentPatient === patientId)

    // Load series for each study
    for (const study of studies.value) {
      try {
        study.series = await fetchSeriesForStudy(study.ID)
      } catch (e) {
        console.error(`Error loading series for study ${study.ID}:`, e)
        study.series = []
      }
    }
  } catch (e) {
    error.value = 'Failed to load studies'
    console.error('Error loading studies:', e)
  } finally {
    loading.value = false
  }
}

// Function to load available labels for a series
async function loadLabelsForSeries(seriesId: string) {
  try {
    loadingLabels.value = true
    availableLabels.value = await fetchAvailableLabels(seriesId)

    // Find the visualization for this series to get already selected labels
    const visualization = props.visualizations.find((vis) => vis.seriesId === seriesId)
    if (visualization && visualization.labels) {
      // Extract filenames from labels and set them as selected
      selectedLabels.value = visualization.labels.map((label) => label.filename)
    } else {
      selectedLabels.value = []
    }
  } catch (e) {
    labelError.value = 'Failed to load labels'
    console.error('Error loading labels:', e)
  } finally {
    loadingLabels.value = false
  }
}

// Function to select a series and load its labels
function selectSeries(series: Series) {
  emit('select-series', series)
  // Labels will be loaded via the watcher
}

// Function to toggle a label selection
async function toggleLabel(labelFilename: string) {
  if (!props.activeSeriesId) return

  const isSelected = selectedLabels.value.includes(labelFilename)

  if (isSelected) {
    // Deselect the label
    selectedLabels.value = selectedLabels.value.filter((l) => l !== labelFilename)
    emit('deselect-label', labelFilename, props.activeSeriesId)
  } else {
    // Select the label - first fetch its content
    try {
      const labelData = await fetchLabelContent(props.activeSeriesId, labelFilename)

      // Determine label type based on filename or content
      let labelType: 'centerline' | 'fiducial' | 'segmentation' | 'unknown' = 'unknown'
      if (labelFilename.includes('centerline')) labelType = 'centerline'
      else if (labelFilename.includes('fiducial')) labelType = 'fiducial'
      else if (labelFilename.includes('segment')) labelType = 'segmentation'

      // Create a label object
      const label: Label = {
        id: `${props.activeSeriesId}_${labelFilename}`,
        filename: labelFilename,
        seriesId: props.activeSeriesId,
        type: labelType,
        data: labelData,
        visible: true,
        color: [0.5, 0.5, 1.0], // Default blue color
        opacity: 1.0,
      }

      selectedLabels.value.push(labelFilename)
      emit('select-label', label, props.activeSeriesId)
    } catch (e) {
      console.error(`Error loading label content for ${labelFilename}:`, e)
      labelError.value = `Failed to load label: ${labelFilename}`
    }
  }
}

// Watch for patient selection changes
watch(
  () => props.selectedPatient,
  (newPatient: Patient | null) => {
    if (newPatient) {
      loadStudiesForPatient(newPatient.ID)
    }
  },
)

// Watch for active series changes to load labels
watch(
  () => props.activeSeriesId,
  (newSeriesId: string | null) => {
    if (newSeriesId) {
      loadLabelsForSeries(newSeriesId)
    } else {
      availableLabels.value = []
      selectedLabels.value = []
    }
  },
)
</script>

<style scoped>
.section {
  margin-bottom: 1.5rem;
  padding: 0;
}

.section h4 {
  margin: 0 0 0.5rem 0;
  color: #2196f3;
  font-size: 0.8em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

/* Patient List Styles */
.patient-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.patient-card:hover {
  border-color: #2196f3;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.patient-card-active {
  border-color: #2196f3;
  background-color: #e3f2fd;
}

.patient-card h3 {
  margin: 0 0 0.25rem 0;
  color: #2c3e50;
  font-size: 0.9em;
}

.patient-card p {
  margin: 0.15rem 0;
  color: #666;
  font-size: 0.8em;
}

/* Study/Series List Styles */
.study-item {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  overflow: hidden;
}

.study-header {
  padding: 0.5rem;
  background: #f5f5f5;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background-color 0.2s;
  font-size: 0.9em;
}

.study-header:hover {
  background: #e3f2fd;
}

.study-date {
  font-size: 0.8em;
  color: #666;
}

.series-list {
  padding: 0.5rem;
}

.series-item {
  padding: 0.5rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 4px;
  margin-bottom: 0.25rem;
  transition: all 0.2s;
  position: relative;
  font-size: 0.85em;
}

.series-item:hover {
  background-color: #f5f5f5;
}

.series-item-active {
  background-color: #e3f2fd;
  border-left: 3px solid #2196f3;
}

.series-item-loading {
  opacity: 0.7;
  pointer-events: none;
}

.series-loading {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.series-loading .loader {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

.series-modality {
  font-size: 0.8em;
  color: #666;
}

/* Label List Styles */
.labels-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.label-item {
  padding: 0.5rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 4px;
  background-color: white;
  border: 1px solid #e0e0e0;
  transition: all 0.2s;
  font-size: 0.85em;
}

.label-item:hover {
  background-color: #f5f5f5;
  border-color: #2196f3;
}

.label-item-active {
  background-color: #e3f2fd;
  border-color: #2196f3;
}

.label-name {
  font-weight: 500;
}

.label-status {
  color: #2196f3;
  font-weight: bold;
}

.empty-state {
  text-align: center;
  color: #666;
  padding: 0.75rem;
  background: #f5f5f5;
  border-radius: 6px;
  font-size: 0.8em;
}

/* Loading Styles */
.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1rem;
}

.loader {
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  animation: spin 1s linear infinite;
}

.error {
  color: #e74c3c;
  padding: 0.75rem;
  text-align: center;
  font-size: 0.8em;
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
