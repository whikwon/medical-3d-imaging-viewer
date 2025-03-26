<template>
  <div class="vtk-container">
    <!-- Combined Patient and Study List -->
    <div class="side-panel" :class="{ 'side-panel-collapsed': isSidePanelCollapsed }">
      <div class="side-panel-header">
        <h3>Medical Viewer</h3>
        <button @click="toggleSidePanel" class="toggle-btn">
          {{ isSidePanelCollapsed ? '→' : '←' }}
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
                <button
                  class="control-btn"
                  @click.stop="removeVisualizationById(index)"
                  title="Remove"
                >
                  ❌
                </button>
              </div>
            </div>
          </div>
        </div>

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
              @click="selectPatient(patient)"
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
                  @click="loadSeries(series)"
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
      </div>
    </div>

    <!-- Show side panel button when collapsed -->
    <button v-if="isSidePanelCollapsed" @click="toggleSidePanel" class="show-side-panel-btn">
      Show Panel
    </button>

    <!-- Visualization Area -->
    <div class="vtk-view-container">
      <div ref="vtkContainer" class="vtk-viewer"></div>

      <!-- Use the VolumeControls component -->
      <VolumeControls
        v-if="activeVolume && showControlOverlay"
        v-model:windowWidth="windowWidth"
        v-model:windowCenter="windowCenter"
        v-model:iSlice="iSlice"
        v-model:jSlice="jSlice"
        v-model:kSlice="kSlice"
        :windowWidthMax="windowWidthMax"
        :windowCenterMin="windowCenterMin"
        :windowCenterMax="windowCenterMax"
        :iExtentMin="iExtentMin"
        :iExtentMax="iExtentMax"
        :jExtentMin="jExtentMin"
        :jExtentMax="jExtentMax"
        :kExtentMin="kExtentMin"
        :kExtentMax="kExtentMax"
        @close="closeOverlay"
        @windowLevelChanged="updateWindowLevel"
        @slicesChanged="updateSlices"
      />

      <!-- Use the MultiframeControls component -->
      <MultiframeControls
        v-if="activeMultiframe && showControlOverlay"
        v-model:currentFrame="currentFrame"
        v-model:playbackSpeed="playbackSpeed"
        v-model:windowWidth="windowWidth"
        v-model:windowCenter="windowCenter"
        :windowWidthMax="windowWidthMax"
        :windowCenterMin="windowCenterMin"
        :windowCenterMax="windowCenterMax"
        :maxFrame="maxFrame"
        :isPlaying="isPlaying"
        @close="closeOverlay"
        @frameChanged="updateMultiframeFrame"
        @togglePlayback="playMultiframe"
        @windowLevelChanged="updateWindowLevel"
      />

      <!-- Control toggle button (visible when controls are hidden) -->
      <button
        v-if="!showControlOverlay && (activeVolume || activeMultiframe)"
        @click="showControlOverlay = true"
        class="show-controls-btn"
      >
        Show Controls
      </button>

      <!-- Add MPR button -->
      <button v-if="activeVolume" @click="openMPRViewport" class="mpr-btn">Open MPR View</button>

      <!-- Add MPR viewport -->
      <MPRViewport
        v-if="showMPRViewport"
        :image-data="mprImageData"
        :window-width="windowWidth"
        :window-center="windowCenter"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import '@kitware/vtk.js/IO/Core/DataAccessHelper/HtmlDataAccessHelper'
import '@kitware/vtk.js/IO/Core/DataAccessHelper/HttpDataAccessHelper'
import '@kitware/vtk.js/IO/Core/DataAccessHelper/JSZipDataAccessHelper'
import '@kitware/vtk.js/Rendering/Profiles/Geometry'
import '@kitware/vtk.js/Rendering/Profiles/Volume'

import { onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'

// Import our services and types
import {
  cleanupViewer,
  initializeViewer,
  type VTKViewerInstance,
} from '@/services/vtkViewerService'

// Import visualization service
import {
  applyWindowLevel,
  loadMultiframeVisualization,
  loadVolumeVisualization,
  updateMultiframeFrame as updateFramePosition,
  updateVolumeSlices,
} from '@/services/visualizationService'

// Import all components
import MPRViewport from '@/components/MPRViewport.vue'
import MultiframeControls from '@/components/MultiframeControls.vue'
import VolumeControls from '@/components/VolumeControls.vue'

// Import our new composable
import { useVisualizationState } from '@/composables/useVisualizationState'
import { useVTKInteractor } from '@/composables/useVTKInteractor'

import {
  fetchPatients,
  fetchSeriesData,
  fetchSeriesForStudy,
  fetchStudies,
} from '@/services/orthancService'
import type { Patient, Series, Study } from '@/types/orthanc'
import vtkImageData from '@kitware/vtk.js/Common/DataModel/ImageData'

// Refs for DOM elements
const vtkContainer = ref<HTMLElement | null>(null)

// Using shallowRef for VTK instance since it's a complex object we don't need to track deeply
const vtkInstanceRef = shallowRef<VTKViewerInstance | null>(null)

// Study list state
const isSidePanelCollapsed = ref(false)
const studies = ref<(Study & { series?: Series[] })[]>([])
const expandedStudies = ref<string[]>([])
const activeSeriesId = ref<string | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const loadingSeriesId = ref<string | null>(null)

// Use our visualization state composable
const {
  visualizations,
  showControlOverlay,
  activeVolume,
  activeMultiframe,
  addVisualization,
  closeOverlay,
  toggleVisibility,
  removeVisualizationById,
  setActiveVisualization,
} = useVisualizationState(vtkInstanceRef)

// Use our VTK interactor composable
const { setupInteraction } = useVTKInteractor(vtkInstanceRef)

// Volume-specific controls
const windowWidth = ref(400)
const windowCenter = ref(40)
const windowWidthMax = ref(4000)
const windowCenterMin = ref(-1000)
const windowCenterMax = ref(1000)
const iSlice = ref(0)
const jSlice = ref(0)
const kSlice = ref(0)
const iExtentMin = ref(0)
const iExtentMax = ref(100)
const jExtentMin = ref(0)
const jExtentMax = ref(100)
const kExtentMin = ref(0)
const kExtentMax = ref(100)

// Multiframe-specific controls
const currentFrame = ref(0)
const maxFrame = ref(0)
const isPlaying = ref(false)
const playbackSpeed = ref(15)
let playbackInterval: number | null = null

// Add new refs
const showMPRViewport = ref(false)
const mprImageData = ref<vtkImageData | null>(null)

// Patient selection state
const selectedPatient = ref<Patient | null>(null)
const patients = ref<Patient[]>([])
const loadingPatients = ref(true)
const patientError = ref<string | null>(null)

// Replace separate toggle functions with a single function
function toggleSidePanel() {
  isSidePanelCollapsed.value = !isSidePanelCollapsed.value
}

onMounted(async () => {
  // Initialize VTK.js
  if (vtkContainer.value) {
    vtkInstanceRef.value = initializeViewer(vtkContainer.value)
  }

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

onBeforeUnmount(() => {
  // Clean up VTK.js objects on component unmount
  if (vtkInstanceRef.value) {
    cleanupViewer(vtkInstanceRef.value)
  }

  // Clear any playback interval
  if (playbackInterval) {
    clearInterval(playbackInterval)
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

// Load series function
async function loadSeries(series: Series) {
  if (loadingSeriesId.value) return // Prevent multiple simultaneous loads
  loadingSeriesId.value = series.ID
  activeSeriesId.value = series.ID
  try {
    const result = await fetchSeriesData(series.ID)
    await handleSeriesLoaded(
      series.ID,
      series,
      result.data,
      result.windowWidth,
      result.windowCenter,
    )
  } catch (error) {
    console.error('Error loading series:', error)
    alert('Failed to load series')
  } finally {
    loadingSeriesId.value = null
  }
}

// Handler for when a series is loaded
async function handleSeriesLoaded(
  seriesId: string,
  series: Series,
  vtiData: Blob,
  receivedWindowWidth: number,
  receivedWindowCenter: number,
) {
  const vtkInstance = vtkInstanceRef.value
  if (!vtkInstance) return

  try {
    // Check if this series is already loaded
    const alreadyLoaded = visualizations.value.some((vis) => vis.seriesId === seriesId)
    if (alreadyLoaded) {
      throw new Error('This series is already loaded in the viewer')
    }

    if (series.MainDicomTags.Modality === 'XA') {
      // Load multiframe visualization
      const result = await loadMultiframeVisualization(
        vtkInstance,
        seriesId,
        series,
        vtiData,
        receivedWindowWidth,
        receivedWindowCenter,
      )

      // Add visualization using our composable
      addVisualization(result.visualization)

      // Update multiframe controls
      maxFrame.value = result.controlValues.maxFrame
      currentFrame.value = 0

      // Set window level control ranges based on data range
      windowCenterMin.value = result.controlValues.windowCenterMin
      windowCenterMax.value = result.controlValues.windowCenterMax
      windowWidthMax.value = result.controlValues.windowWidthMax

      // Apply window level settings from backend
      windowWidth.value = receivedWindowWidth
      windowCenter.value = receivedWindowCenter

      // Apply window level settings to the visualization
      applyWindowLevel(result.visualization, receivedWindowCenter, receivedWindowWidth)
    } else if (series.MainDicomTags.Modality === 'CT') {
      // Load volume visualization
      const result = await loadVolumeVisualization(
        vtkInstance,
        seriesId,
        series,
        vtiData,
        receivedWindowWidth,
        receivedWindowCenter,
      )

      // Add visualization using our composable
      addVisualization(result.visualization)

      // Update UI control values
      const controls = result.controlValues
      iExtentMin.value = controls.iExtentMin
      iExtentMax.value = controls.iExtentMax
      jExtentMin.value = controls.jExtentMin
      jExtentMax.value = controls.jExtentMax
      kExtentMin.value = controls.kExtentMin
      kExtentMax.value = controls.kExtentMax
      iSlice.value = controls.iSlice
      jSlice.value = controls.jSlice
      kSlice.value = controls.kSlice

      // Set window level control ranges based on data range
      windowCenterMin.value = controls.windowCenterMin
      windowCenterMax.value = controls.windowCenterMax
      windowWidthMax.value = controls.windowWidthMax

      // Apply window level settings from backend
      windowWidth.value = receivedWindowWidth
      windowCenter.value = receivedWindowCenter

      // Apply window level settings to the visualization
      applyWindowLevel(result.visualization, receivedWindowCenter, receivedWindowWidth)
    } else {
      throw new Error(`Unsupported modality: ${series.MainDicomTags.Modality}`)
    }

    // Setup interaction using our composable
    if (vtkInstance.renderer && vtkInstance.renderWindow) {
      // Pass the active visualization to the interaction setup
      const currentVis = activeVolume.value || activeMultiframe.value
      setupInteraction(currentVis)
      vtkInstance.renderer.resetCamera()
      vtkInstance.renderWindow.render()
    }
  } catch (error: unknown) {
    console.error('Error handling loaded series:', error)
    if (error instanceof Error) {
      alert('Failed to visualize series: ' + error.message)
    } else {
      alert('Failed to visualize series: unknown error')
    }
  }
}

function updateWindowLevel() {
  const vtkInstance = vtkInstanceRef.value
  if (!vtkInstance?.renderWindow) return

  if (activeVolume.value) {
    applyWindowLevel(activeVolume.value, windowCenter.value, windowWidth.value)
  } else if (activeMultiframe.value) {
    applyWindowLevel(activeMultiframe.value, windowCenter.value, windowWidth.value)
  }

  vtkInstance.renderWindow.render()
}

function updateSlices() {
  const vtkInstance = vtkInstanceRef.value
  if (!activeVolume.value || !vtkInstance?.renderWindow) return

  updateVolumeSlices(activeVolume.value, iSlice.value, jSlice.value, kSlice.value)
  vtkInstance.renderWindow.render()
}

// Update the current frame in multiframe data
function updateMultiframeFrame() {
  const vtkInstance = vtkInstanceRef.value
  if (!activeMultiframe.value || !vtkInstance?.renderWindow) return

  updateFramePosition(activeMultiframe.value, currentFrame.value)
  vtkInstance.renderWindow.render()
}

// Play/pause multiframe data
function playMultiframe() {
  if (!activeMultiframe.value) return

  isPlaying.value = !isPlaying.value

  if (isPlaying.value) {
    // Start playback
    if (playbackInterval) {
      clearInterval(playbackInterval)
    }

    playbackInterval = setInterval(() => {
      currentFrame.value = (currentFrame.value + 1) % (maxFrame.value + 1)
      updateMultiframeFrame()
    }, 1000 / playbackSpeed.value)
  } else {
    // Stop playback
    if (playbackInterval) {
      clearInterval(playbackInterval)
      playbackInterval = null
    }
  }
}

// Add type guard function
function isVtkImageData(obj: unknown): obj is vtkImageData {
  return (
    obj !== null &&
    typeof obj === 'object' &&
    'getDimensions' in obj &&
    'getExtent' in obj &&
    typeof (obj as vtkImageData).getDimensions === 'function' &&
    typeof (obj as vtkImageData).getExtent === 'function'
  )
}

// Add new method
function openMPRViewport() {
  if (activeVolume.value?.data && isVtkImageData(activeVolume.value.data)) {
    mprImageData.value = activeVolume.value.data
    showMPRViewport.value = true
  }
}

// Patient selection function
function selectPatient(patient: Patient) {
  selectedPatient.value = patient
  // Load studies for the selected patient
  loadStudiesForPatient(patient.ID)
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

// Add function to select visualization
function selectVisualization(index: number) {
  setActiveVisualization(index)
  // Setup interaction for the selected visualization
  if (vtkInstanceRef.value?.renderer && vtkInstanceRef.value?.renderWindow) {
    const selectedVis = visualizations.value[index]
    setupInteraction(selectedVis)
    vtkInstanceRef.value.renderer.resetCamera()
    vtkInstanceRef.value.renderWindow.render()
  }
}
</script>

<style scoped>
.vtk-container {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;
  position: relative;
}

/* Combined Side Panel Styles */
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
  padding: 0.5rem;
}

.section {
  margin-bottom: 1.5rem;
  padding: 0 1rem;
}

.section h4 {
  margin: 0 0 0.5rem 0;
  color: #2196f3;
  font-size: 0.8em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
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

/* Visualization Area Styles */
.vtk-view-container {
  flex: 1;
  position: relative;
  height: 100vh;
}

/* Remove the margin adjustment since panel is overlaid */
.side-panel-collapsed + .vtk-view-container {
  margin-left: 0;
}

/* Remove redundant styles */
.patient-list-container,
.patient-list-collapsed,
.patient-list-header,
.patient-list-content,
.study-list,
.study-list-collapsed,
.study-list-header,
.show-study-list-btn {
  display: none;
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

/* Show controls button */
.show-controls-btn {
  position: absolute;
  bottom: 20px;
  right: 20px;
  padding: 6px 10px;
  background-color: rgba(33, 150, 243, 0.8);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  z-index: 15;
  font-size: 0.8em;
}

.show-controls-btn:hover {
  background-color: rgba(33, 150, 243, 1);
}

.mpr-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 6px 10px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  z-index: 100;
}

.mpr-btn:hover {
  background-color: #1976d2;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* Show study list button when collapsed */
.show-study-list-btn {
  position: fixed;
  left: 300px;
  top: 50%;
  transform: translateY(-50%);
  padding: 8px 12px;
  background-color: rgba(33, 150, 243, 0.8);
  color: white;
  border: none;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
  z-index: 90;
  font-size: 0.9em;
}

.show-study-list-btn:hover {
  background-color: rgba(33, 150, 243, 1);
}

/* Updated Panel Styles */
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

.section {
  margin-bottom: 1.5rem;
  padding: 0 1rem;
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

/* Updated Patient Card Styles */
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

/* Updated Study/Series Styles */
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

/* Show study list button when collapsed */
.show-study-list-btn {
  position: fixed;
  left: 300px;
  top: 50%;
  transform: translateY(-50%);
  padding: 8px 12px;
  background-color: rgba(33, 150, 243, 0.8);
  color: white;
  border: none;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
  z-index: 90;
  font-size: 0.9em;
}

.show-study-list-btn:hover {
  background-color: rgba(33, 150, 243, 1);
}
</style>
