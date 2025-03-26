<template>
  <div class="vtk-container">
    <div class="controls">
      <h2>3D Volume Viewer</h2>

      <!-- Use the series selector component -->
      <SeriesSelector @series-loaded="handleSeriesLoaded" />

      <!-- Show help text when no visualizations are loaded -->
      <div v-if="!hasVisualizations" class="no-data">
        <p>No data loaded. Select a series above to visualize.</p>
      </div>

      <!-- Use the VisualizationList component -->
      <VisualizationList
        v-if="hasVisualizations"
        :visualizations="visualizations"
        :activeIndex="activeVisualizationIndex"
        @select="setActiveVisualization"
        @toggleVisibility="toggleVisibility"
      />
    </div>

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
import SeriesSelector from '@/components/SeriesSelector.vue'
import VisualizationList from '@/components/VisualizationList.vue'
import VolumeControls from '@/components/VolumeControls.vue'

// Import our new composable
import { useVisualizationState } from '@/composables/useVisualizationState'
import { useVTKInteractor } from '@/composables/useVTKInteractor'

import type { Series } from '@/types/orthanc'
import vtkImageData from '@kitware/vtk.js/Common/DataModel/ImageData'

// Refs for DOM elements
const vtkContainer = ref<HTMLElement | null>(null)

// Using shallowRef for VTK instance since it's a complex object we don't need to track deeply
const vtkInstanceRef = shallowRef<VTKViewerInstance | null>(null)

// Use our visualization state composable
const {
  visualizations,
  activeVisualizationIndex,
  showControlOverlay,
  hasVisualizations,
  activeVolume,
  activeMultiframe,
  addVisualization,
  toggleVisibility,
  setActiveVisualization,
  closeOverlay,
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

onMounted(async () => {
  // Initialize VTK.js
  if (vtkContainer.value) {
    // Use our new VTK service
    vtkInstanceRef.value = initializeViewer(vtkContainer.value)
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

  // The cleanup of sphere actor is now handled in the composable
})

// Handler for when a series is loaded from the SeriesSelector component
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
</script>

<style scoped>
.vtk-container {
  display: flex;
  flex-direction: row;
  height: 100vh;
  width: 100%;
  overflow: hidden;
}

.controls {
  padding: 10px;
  background-color: #f5f5f5;
  border-right: 1px solid #ddd;
  width: 300px;
  min-width: 300px; /* Ensures width doesn't shrink */
  max-width: 300px; /* Ensures width doesn't grow */
  height: 100vh;
  overflow-y: auto;
  flex-shrink: 0;
}

.vtk-view-container {
  flex: 1;
  position: relative;
  height: 100vh;
}

.vtk-viewer {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
}

.no-data {
  padding: 10px;
  text-align: center;
  background-color: #f9f9f9;
  border-radius: 4px;
  margin: 10px 0;
}

/* Show controls button */
.show-controls-btn {
  position: absolute;
  bottom: 20px;
  right: 20px;
  padding: 8px 12px;
  background-color: rgba(33, 150, 243, 0.8);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  z-index: 15;
  font-size: 0.9em;
}

.show-controls-btn:hover {
  background-color: rgba(33, 150, 243, 1);
}

.mpr-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 8px 16px;
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
</style>
