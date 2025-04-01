<template>
  <div class="vtk-container">
    <!-- Use the SidePanel component -->
    <SidePanel
      v-model:isCollapsed="isSidePanelCollapsed"
      :visualizations="visualizations"
      :active-volume="activeVolume"
      :active-multiframe="activeMultiframe"
      @select-visualization="selectVisualization"
      @toggle-visibility="handleToggleVisibility"
      @remove-visualization="
        (index) => visualizationStore.removeVisualizationById(index, vtkInstance)
      "
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
        @close="visualizationStore.closeOverlay"
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
        @close="visualizationStore.closeOverlay"
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

      <!-- Add CPR button -->
      <button v-if="activeVolume" @click="openCPRViewport" class="cpr-btn">Open CPR View</button>

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

      <!-- Add CPR viewport -->
      <CPRViewport
        v-if="showCPRViewport && cprImageData && vtkInstance && centerlineData"
        :image-data="cprImageData"
        :window-width="windowWidth"
        :window-center="windowCenter"
        :vtk-instance="vtkInstance"
        :viewports="cprViewports"
        :centerline="centerlineData"
        @close="closeCPRViewport"
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

import { onBeforeUnmount, onMounted, ref, type Ref, watch } from 'vue'

// Import our services and types
import {
  cleanupViewer,
  cleanupViewport,
  createCPRViewports,
  createMPRViewports,
  createViewport,
  initializeViewer,
  setupAxesActor,
  setupOrientationWidget,
} from '@/services/vtkViewerService'
import type { CenterlineData, Viewport, VTKViewerInstance } from '@/types/visualization'

// Import visualization service
import {
  loadMultiframeVisualization,
  loadVolumeVisualization,
} from '@/services/visualizationService'

// Import all components
import CPRViewport from '@/components/CPRViewport.vue'
import MPRViewport from '@/components/MPRViewport.vue'
import MultiframeControls from '@/components/MultiframeControls.vue'
import SidePanel from '@/components/SidePanel.vue'
import VolumeControls from '@/components/VolumeControls.vue'

// Import our new composable
import { useControlPanelState } from '@/composables/useControlPanelState'
import { useVTKInteractor } from '@/composables/useVTKInteractor'

import { fetchSeriesData } from '@/services/orthancService'
import type { Series } from '@/types/orthanc'
import vtkImageData from '@kitware/vtk.js/Common/DataModel/ImageData'

import { drawLabelsForVisualization, updateLabelsVisibility } from '@/services/labelService'
import { usePatientStudyStore } from '@/stores/usePatientStudyStore'
import { useVisualizationStore } from '@/stores/useVisualizationStore'
import { storeToRefs } from 'pinia'

// Refs for DOM elements
const vtkContainer = ref<HTMLElement | null>(null)

// Using shallowRef for VTK instance since it's a complex object we don't need to track deeply
const vtkInstance: Ref<VTKViewerInstance | null> = ref(null)
const initialViewport: Ref<Viewport | null> = ref(null)

// Study list state - Managed by Pinia now
const isSidePanelCollapsed = ref(false)

// Patient selection state - Managed by Pinia now

// Use our visualization state composable
const patientStudyStore = usePatientStudyStore()
const visualizationStore = useVisualizationStore()

// Get reactive refs from the patient store (remove unused activeSeriesId)
const { loadingSeriesId: storeLoadingSeriesId } = storeToRefs(patientStudyStore)

// Get reactive refs from the visualization store
const { visualizations, showControlOverlay, activeVolume, activeMultiframe } =
  storeToRefs(visualizationStore)

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

// Add new refs for CPR functionality
const showCPRViewport = ref(false)
const cprImageData = ref<vtkImageData | null>(null)
const cprViewports = ref<Viewport[]>([])
const centerlineData = ref<CenterlineData | null>(null)

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

// Watch for the store's loadingSeriesId to change - This triggers the load
watch(storeLoadingSeriesId, (newLoadingId, oldLoadingId) => {
  if (newLoadingId && newLoadingId !== oldLoadingId) {
    // Find the series details from the patient store (assuming studies are loaded)
    let seriesToLoad: Series | null = null
    for (const study of patientStudyStore.studies) {
      const foundSeries = study.series?.find((s) => s.ID === newLoadingId)
      if (foundSeries) {
        seriesToLoad = foundSeries
        break
      }
    }

    if (seriesToLoad) {
      loadSeriesData(seriesToLoad)
    } else {
      console.error(`VTKCanvas: Could not find series details for ID ${newLoadingId} in store.`)
      // Inform the store that loading failed because we couldn't find the series details
      patientStudyStore.setSeriesLoadingCompleteAction(newLoadingId, false)
    }
  }
})

// Actual data loading function - triggered by watcher
async function loadSeriesData(series: Series) {
  let success = false
  try {
    const result = await fetchSeriesData(series.ID)
    await handleSeriesLoaded(
      series.ID,
      series,
      result.data,
      result.windowWidth,
      result.windowCenter,
    )
    success = true
  } catch (error) {
    console.error(`Error loading series data for ${series.ID}:`, error)
    alert('Failed to load series data')
    success = false
  } finally {
    patientStudyStore.setSeriesLoadingCompleteAction(series.ID, success)
  }
}

// Handler for when a series is loaded (mostly unchanged, but now called by loadSeriesData)
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
      const index = visualizations.value.findIndex((vis) => vis.seriesId === seriesId)
      if (index !== -1) {
        visualizationStore.setActiveVisualization(index) // Update local active state
      }
      return
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

      // Add viewport reference to the visualization object BEFORE adding to store
      result.visualization.viewport = initialViewport.value

      // Add visualization using our composable
      visualizationStore.addVisualization(result.visualization)

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

      // If the visualization has labels, draw them
      if (result.visualization.labels && result.visualization.labels.length > 0) {
        drawLabelsForVisualization(result.visualization)
      }
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

      // Add viewport reference to the visualization object BEFORE adding to store
      result.visualization.viewport = initialViewport.value

      // Add visualization using our composable
      visualizationStore.addVisualization(result.visualization)

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

      // If the visualization has labels, draw them
      if (result.visualization.labels && result.visualization.labels.length > 0) {
        drawLabelsForVisualization(result.visualization)
      }
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
    console.error(`Error in handleSeriesLoaded for ${seriesId}:`, error)
    if (error instanceof Error) {
      alert('Failed to visualize series: ' + error.message)
    } else {
      alert('Failed to visualize series: unknown error')
    }
    throw error // Propagate error so loadSeriesData knows it failed
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

// Add a function to open the CPR viewport
async function openCPRViewport() {
  if (activeVolume.value?.data && vtkInstance.value && activeVolume.value.seriesId) {
    try {
      // Find centerline data from labels
      const centerlineLabels =
        activeVolume.value.labels?.filter((label) => label.type === 'centerline') || []

      if (centerlineLabels.length === 0) {
        alert('No centerline data available for this series')
        return
      } else {
        // Use the first centerline label (could add a selection UI for multiple centerlines)
        const centerlineLabel = centerlineLabels[0]

        // Use the defined interface and type assertion
        const labelData = centerlineLabel.data as CenterlineData | undefined
        if (
          !labelData ||
          !Array.isArray(labelData.position) ||
          !Array.isArray(labelData.orientation)
        ) {
          alert('Invalid centerline data format in label')
          centerlineData.value = null // Clear potentially invalid data
          return
        }

        centerlineData.value = {
          position: labelData.position,
          orientation: labelData.orientation,
          radius: labelData.radius,
        }
      }

      // Store the image data for the CPR viewport
      cprImageData.value = activeVolume.value.data

      // Hide the main viewport temporarily
      if (initialViewport.value?.container) {
        initialViewport.value.container.style.display = 'none'
      }

      // Create CPR viewports using the existing render window
      cprViewports.value = createCPRViewports(
        vtkInstance.value.renderWindow,
        vtkInstance.value.rootContainer,
        vtkInstance.value.interactor,
        vtkInstance.value.imageInteractorStyle,
      )

      // Show the CPR viewport
      showCPRViewport.value = true

      // Force a render
      if (vtkInstance.value.renderWindow) {
        vtkInstance.value.renderWindow.render()
      }
    } catch (error) {
      console.error('Error loading centerline data:', error)
      alert('Failed to load centerline data for CPR view')
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

  vtkInstance.value?.interactor.setInteractorStyle(vtkInstance.value?.trackballInteractorStyle)
  // Add null check before setting container
  if (initialViewport.value?.container) {
    vtkInstance.value?.interactor.setContainer(initialViewport.value.container)
  }

  vtkInstance.value?.renderWindow?.render()
}

// Add a function to close the CPR viewport
function closeCPRViewport() {
  // Hide the CPR viewport
  showCPRViewport.value = false

  // Clean up CPR viewports
  if (vtkInstance.value && cprViewports.value.length > 0) {
    cprViewports.value.forEach((viewport) => {
      cleanupViewport(viewport, vtkInstance.value!.renderWindow, vtkInstance.value!.interactor)
    })
    cprViewports.value = []
  }

  // Reset the cprImageData and centerlineData references to avoid memory leaks
  cprImageData.value = null
  centerlineData.value = null

  // Show the main viewport again
  if (initialViewport.value?.container) {
    initialViewport.value.container.style.display = 'block'
  }

  vtkInstance.value?.interactor.setInteractorStyle(vtkInstance.value?.trackballInteractorStyle)
  // Add null check before setting container
  if (initialViewport.value?.container) {
    vtkInstance.value?.interactor.setContainer(initialViewport.value.container)
  }

  vtkInstance.value?.renderWindow?.render()
}

// Update function to select visualization (mostly unchanged, interacts with local composable)
function selectVisualization(index: number) {
  if (!vtkInstance.value) return
  visualizationStore.setActiveVisualization(index) // Use the store action

  // Setup interaction for the selected visualization
  if (vtkInstance.value.renderWindow) {
    const selectedVis = visualizations.value[index]
    setupInteraction(selectedVis)

    // Draw any labels that exist for this visualization
    // This might eventually be triggered by watching the visualization store state
    if (selectedVis.labels && selectedVis.labels.length > 0) {
      drawLabelsForVisualization(selectedVis)
    }

    if (selectedVis.viewport?.renderer) {
      selectedVis.viewport.renderer.resetCamera()
      vtkInstance.value.renderWindow.render()
    }
  }
}

// Update toggleVisibility function to handle label visibility
function handleToggleVisibility(index: number) {
  if (!vtkInstance.value || !vtkInstance.value.renderWindow) return

  // Call the store action, passing the vtkInstance
  visualizationStore.toggleVisibility(index, vtkInstance.value)

  // Update label visibility based on parent visualization
  const vis = visualizations.value[index]
  if (vis.labels && vis.labels.length > 0) {
    updateLabelsVisibility(vis)
    vtkInstance.value.renderWindow.render()
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
  right: 120px;
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

.cpr-btn {
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

.cpr-btn:hover {
  background-color: #1976d2;
}
</style>
