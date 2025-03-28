<template>
  <div class="vtk-container">
    <!-- Use the SidePanel component -->
    <SidePanel
      v-model:isCollapsed="isSidePanelCollapsed"
      :visualizations="visualizations"
      :active-volume="activeVolume"
      :active-multiframe="activeMultiframe"
      :selected-patient="selectedPatient"
      :active-series-id="activeSeriesId"
      :loading-series-id="loadingSeriesId"
      @select-visualization="selectVisualization"
      @toggle-visibility="toggleVisibility"
      @remove-visualization="removeVisualizationById"
      @select-patient="selectPatient"
      @select-series="loadSeries"
    />

    <!-- Visualization Area -->
    <div class="vtk-view-container">
      <!-- rootContainer -->
      <div ref="vtkContainer" class="vtk-viewer" style="width: 100%; height: 100%"></div>

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
        @windowLevelChanged="updateWindowLevelUI"
        @slicesChanged="updateSlicesUI"
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
        @frameChanged="updateMultiframeFrameUI"
        @togglePlayback="playMultiframeUI"
        @windowLevelChanged="updateWindowLevelUI"
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

      <!-- Add MPR viewport with non-nullable check -->
      <MPRViewport
        v-if="showMPRViewport && mprImageData && vtkInstance"
        :image-data="mprImageData"
        :window-width="windowWidth"
        :window-center="windowCenter"
        :vtk-instance="vtkInstance"
        :mpr-viewports="mprViewports"
        @close="closeMPRViewport"
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

import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

// Import our services and types
import {
  cleanupViewer,
  cleanupViewport,
  createMPRViewports,
  createViewport,
  initializeViewer,
  setupAxesActor,
  setupOrientationWidget,
} from '@/services/vtkViewerService'
import type { Viewport, VTKViewerInstance } from '@/types/visualization'

// Import visualization service
import {
  loadMultiframeVisualization,
  loadVolumeVisualization,
} from '@/services/visualizationService'

// Import all components
import MPRViewport from '@/components/MPRViewport.vue'
import MultiframeControls from '@/components/MultiframeControls.vue'
import SidePanel from '@/components/SidePanel.vue'
import VolumeControls from '@/components/VolumeControls.vue'

// Import our new composable
import { useControlPanelState } from '@/composables/useControlPanelState'
import { useVisualizationState } from '@/composables/useVisualizationState'
import { useVTKInteractor } from '@/composables/useVTKInteractor'

import { fetchSeriesData } from '@/services/orthancService'
import type { Patient, Series } from '@/types/orthanc'
import vtkImageData from '@kitware/vtk.js/Common/DataModel/ImageData'

// Refs for DOM elements
const vtkContainer = ref<HTMLElement | null>(null)

// Using shallowRef for VTK instance since it's a complex object we don't need to track deeply
const vtkInstance: Ref<VTKViewerInstance | null> = ref(null)
const initialViewport: Ref<Viewport | null> = ref(null)

// Study list state
const isSidePanelCollapsed = ref(false)
const activeSeriesId = ref<string | null>(null)
const loadingSeriesId = ref<string | null>(null)

// Patient selection state
const selectedPatient = ref<Patient | null>(null)

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
} = useVisualizationState(vtkInstance)

// Use our VTK interactor composable
const { setupInteraction } = useVTKInteractor(vtkInstance)

// Use our new control panel state composable
const {
  // Shared controls
  windowWidth,
  windowCenter,
  windowWidthMax,
  windowCenterMin,
  windowCenterMax,

  // Volume-specific controls
  iSlice,
  jSlice,
  kSlice,
  iExtentMin,
  iExtentMax,
  jExtentMin,
  jExtentMax,
  kExtentMin,
  kExtentMax,

  // Multiframe-specific controls
  currentFrame,
  maxFrame,
  isPlaying,
  playbackSpeed,

  // Methods
  updateWindowLevel,
  updateSlices,
  updateMultiframeFrame,
  togglePlayback: playMultiframe,
  setVolumeControlParams,
  setMultiframeControlParams,
  cleanup: cleanupControlPanel,
} = useControlPanelState(vtkInstance)

// Add new refs for MPR functionality
const showMPRViewport = ref(false)
const mprImageData = ref<vtkImageData | null>(null)
const mprViewports = ref<Viewport[]>([])

onMounted(async () => {
  // Initialize VTK.js
  if (vtkContainer.value) {
    vtkInstance.value = initializeViewer(vtkContainer.value)
    initialViewport.value = createViewport(
      vtkInstance.value.renderWindow,
      vtkInstance.value.rootContainer,
      [0, 0, 1, 1],
      vtkInstance.value.interactor,
      vtkInstance.value.trackballInteractorStyle,
    )
    setupAxesActor(initialViewport.value.renderer)
    setupOrientationWidget(vtkInstance.value.interactor)
  }
})

onBeforeUnmount(() => {
  // Clean up VTK.js objects on component unmount
  if (vtkInstance.value) {
    cleanupViewer(vtkInstance)
  }

  // Clean up control panel resources
  cleanupControlPanel()
})

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
  if (!initialViewport.value || !vtkInstance.value) return

  try {
    // Check if this series is already loaded
    const alreadyLoaded = visualizations.value.some((vis) => vis.seriesId === seriesId)
    if (alreadyLoaded) {
      throw new Error('This series is already loaded in the viewer')
    }

    if (series.MainDicomTags.Modality === 'XA') {
      const result = await loadMultiframeVisualization(
        initialViewport.value.renderer,
        seriesId,
        series,
        vtiData,
        receivedWindowWidth,
        receivedWindowCenter,
      )

      // Add visualization property for viewport
      result.visualization.viewport = initialViewport.value

      // Add visualization using our composable
      addVisualization(result.visualization)

      // Update multiframe controls using our new composable
      setMultiframeControlParams({
        maxFrame: result.controlParams.maxFrame,
        windowCenterMin: result.controlParams.windowCenterMin,
        windowCenterMax: result.controlParams.windowCenterMax,
        windowWidthMax: result.controlParams.windowWidthMax,
        windowCenter: receivedWindowCenter,
        windowWidth: receivedWindowWidth,
      })

      // Apply window level settings to the visualization
      updateWindowLevel(result.visualization)
    } else if (series.MainDicomTags.Modality === 'CT') {
      // Load volume visualization
      const result = await loadVolumeVisualization(
        initialViewport.value.renderer,
        seriesId,
        series,
        vtiData,
        receivedWindowWidth,
        receivedWindowCenter,
      )

      // Add visualization property for viewport
      result.visualization.viewport = initialViewport.value

      // Add visualization using our composable
      addVisualization(result.visualization)

      // Update volume controls using our new composable
      setVolumeControlParams({
        iExtentMin: result.controlParams.iExtentMin,
        iExtentMax: result.controlParams.iExtentMax,
        jExtentMin: result.controlParams.jExtentMin,
        jExtentMax: result.controlParams.jExtentMax,
        kExtentMin: result.controlParams.kExtentMin,
        kExtentMax: result.controlParams.kExtentMax,
        iSlice: result.controlParams.iSlice,
        jSlice: result.controlParams.jSlice,
        kSlice: result.controlParams.kSlice,
        windowCenterMin: result.controlParams.windowCenterMin,
        windowCenterMax: result.controlParams.windowCenterMax,
        windowWidthMax: result.controlParams.windowWidthMax,
        windowCenter: receivedWindowCenter,
        windowWidth: receivedWindowWidth,
      })

      // Apply window level settings to the visualization
      updateWindowLevel(result.visualization)
    } else {
      throw new Error(`Unsupported modality: ${series.MainDicomTags.Modality}`)
    }

    // Setup interaction using our composable
    if (initialViewport.value.renderer && vtkInstance.value.renderWindow) {
      // Pass the active visualization to the interaction setup
      const currentVis = activeVolume.value || activeMultiframe.value
      if (currentVis) {
        setupInteraction(currentVis)
      }
      initialViewport.value.renderer.resetCamera()
      vtkInstance.value.renderWindow.render()
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

// Update the window level method to use our new composable
function updateWindowLevelUI() {
  const currentVis = activeVolume.value || activeMultiframe.value
  if (currentVis) {
    updateWindowLevel(currentVis)
  }
}

// Update the slices method to use our new composable
function updateSlicesUI() {
  if (activeVolume.value) {
    updateSlices(activeVolume.value)
  }
}

// Update the multiframe method to use our new composable
function updateMultiframeFrameUI() {
  if (activeMultiframe.value) {
    updateMultiframeFrame(activeMultiframe.value)
  }
}

// Update the play multiframe method to use our new composable
function playMultiframeUI() {
  if (activeMultiframe.value) {
    playMultiframe(activeMultiframe.value)
  }
}

// Update openMPRViewport function to use the shared window approach
function openMPRViewport() {
  if (activeVolume.value?.data && vtkInstance.value) {
    // Store the image data for the MPR viewport
    mprImageData.value = activeVolume.value.data

    // Hide the main viewport temporarily (could also use CSS to adjust the layout)
    if (initialViewport.value?.container) {
      initialViewport.value.container.style.display = 'none'
    }

    // Create MPR viewports using the existing render window
    mprViewports.value = createMPRViewports(
      vtkInstance.value.renderWindow,
      vtkInstance.value.rootContainer,
      vtkInstance.value.interactor,
      vtkInstance.value.imageInteractorStyle,
      vtkInstance.value.trackballInteractorStyle,
    )

    // Show the MPR viewport
    showMPRViewport.value = true

    // Force a render
    if (vtkInstance.value.renderWindow) {
      vtkInstance.value.renderWindow.render()
    }
  }
}

// Add a function to close the MPR viewport
function closeMPRViewport() {
  // Hide the MPR viewport
  showMPRViewport.value = false

  // Clean up MPR viewports
  if (vtkInstance.value && mprViewports.value.length > 0) {
    mprViewports.value.forEach((viewport) => {
      cleanupViewport(viewport, vtkInstance.value!.renderWindow, vtkInstance.value!.interactor)
    })
    mprViewports.value = []
  }

  // Reset the mprImageData reference to avoid memory leaks
  mprImageData.value = null

  // Show the main viewport again
  if (initialViewport.value?.container) {
    initialViewport.value.container.style.display = 'block'
  }

  // Reset view if there's an active visualization
  if (activeVolume.value && activeVolume.value.viewport?.renderer) {
    activeVolume.value.viewport.renderer.resetCamera()
  }

  // Force a render with a slight delay to ensure all cleanups are complete
  setTimeout(() => {
    if (vtkInstance.value?.renderWindow) {
      vtkInstance.value.renderWindow.render()
    }
  }, 50)
}

// Patient selection function
function selectPatient(patient: Patient) {
  selectedPatient.value = patient
}

// Add function to select visualization
function selectVisualization(index: number) {
  if (!vtkInstance.value) return
  setActiveVisualization(index)

  // Setup interaction for the selected visualization
  if (vtkInstance.value.renderWindow) {
    const selectedVis = visualizations.value[index]
    setupInteraction(selectedVis)
    if (selectedVis.viewport?.renderer) {
      selectedVis.viewport.renderer.resetCamera()
      vtkInstance.value.renderWindow.render()
    }
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

/* Visualization Area Styles */
.vtk-view-container {
  flex: 1;
  position: relative;
  height: 100vh;
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
</style>
