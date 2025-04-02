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
      <!-- rootContainer for VTK -->
      <div ref="vtkContainer" class="vtk-viewer" style="width: 100%; height: 100%"></div>

      <!-- Dynamic component rendering based on visualization type -->
      <template v-if="activeVisualization">
        <component
          :is="activeVisualization.type === 'volume' ? VolumeViewer : MultiframeViewer"
          :key="activeVisualization.seriesId"
          :visualization="activeVisualization"
          :vtk-instance="vtkInstance"
          :is-active="true"
        />
      </template>
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
  createViewport,
  initializeViewer,
  setupAxesActor,
  setupOrientationWidget,
} from '@/services/vtkViewerService'
import type { Viewport, VTKViewerInstance } from '@/types/visualization'

// Import visualization service

// Import all components
import SidePanel from '@/components/SidePanel.vue'

// Import our new composable
import { useControlPanelState } from '@/composables/useControlPanelState'
import { useVTKInteractor } from '@/composables/useVTKInteractor'

// Add back vtkImageData import

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
const { visualizations, activeVisualization, activeVolume, activeMultiframe } =
  storeToRefs(visualizationStore)

// Use our VTK interactor composable
const { setupInteraction } = useVTKInteractor(vtkInstance)

// Use our new control panel state composable
const { cleanup: cleanupControlPanel } = useControlPanelState(vtkInstance)

import MultiframeViewerComponent from '@/components/MultiframeViewer.vue'
import VolumeViewerComponent from '@/components/VolumeViewer.vue'

const VolumeViewer = VolumeViewerComponent
const MultiframeViewer = MultiframeViewerComponent

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

// Watch for the store's loadingSeriesId to trigger loading in the store
watch(storeLoadingSeriesId, (newLoadingId) => {
  if (newLoadingId && initialViewport.value?.renderer) {
    console.log(`VTKCanvas: Triggering load for series ${newLoadingId} in store...`)
    // Pass the necessary renderer and viewport
    visualizationStore.loadAndAddVisualization(
      newLoadingId,
      initialViewport.value.renderer,
      initialViewport.value,
    )
  } else if (newLoadingId) {
    console.warn(
      `VTKCanvas: Cannot trigger load for ${newLoadingId}. Initial viewport or renderer not ready.`,
    )
    // Optionally, handle retry logic or inform the user/store
  }
})

// --- NEW Watcher for activeVisualization ---
// Handles setup that needs the *active* visualization context, like interaction and labels.
watch(
  activeVisualization,
  (newVis, oldVis) => {
    if (newVis && newVis !== oldVis && vtkInstance.value?.renderWindow) {
      // console.log(`VTKCanvas: Active visualization changed to ${newVis.seriesId}. Setting up interaction/labels.`);
      console.log(
        `VTKCanvas: Active visualization changed to ${newVis.seriesId}. Viewport assigned: ${!!newVis.viewport}`,
      )

      // Reset camera and render - Still do this centrally when active vis changes
      // Render needs to happen after actors/labels might have been added/updated by child component
      // Consider if rendering should also be triggered by child components upon activation
      if (newVis.viewport?.renderer) {
        newVis.viewport.renderer.resetCamera()
        console.log(`VTKCanvas: Reset camera for viewport of ${newVis.seriesId}`)
      } else {
        // Fallback to initial viewport if specific one isn't set?
        if (initialViewport.value?.renderer) {
          initialViewport.value.renderer.resetCamera()
          console.log(
            `VTKCanvas: Reset camera for initial viewport (fallback for ${newVis.seriesId})`,
          )
        } else {
          console.warn(
            `VTKCanvas: Cannot reset camera, no viewport found for ${newVis.seriesId} or initial viewport.`,
          )
        }
      }
      // Delay render slightly to allow potential updates from child component watcher?
      // Or maybe child components should trigger render?
      // For now, keep central render.
      vtkInstance.value.renderWindow.render()
      console.log(`VTKCanvas: Render triggered after ${newVis.seriesId} became active.`)
    } else if (!newVis && oldVis) {
      console.log('VTKCanvas: Active visualization set to null.')
      // Optional: Reset interaction style if needed
      if (vtkInstance.value?.interactor && vtkInstance.value.trackballInteractorStyle) {
        vtkInstance.value.interactor.setInteractorStyle(vtkInstance.value.trackballInteractorStyle)
        // Ensure container is set correctly if needed
        if (initialViewport.value?.container) {
          vtkInstance.value.interactor.setContainer(initialViewport.value.container)
        }
      }
    }
  },
  { deep: false },
) // Don't need deep watch, just reference change

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
  // NOTE: Label visibility update logic might need adjustment.
  // The `updateLabelsVisibility` function needs the visualization object.
  // It might be better to trigger this based on the store state change
  // rather than directly here.
  const vis = visualizations.value[index]
  if (vis.labels && vis.labels.length > 0) {
    updateLabelsVisibility(vis) // Make sure this function gets the updated vis.visible state
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
