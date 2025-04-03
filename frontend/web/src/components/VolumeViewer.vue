<template>
  <div class="volume-viewer-container">
    <!-- Volume specific controls -->
    <VolumeControls
      v-if="showControlOverlay && !showMPRViewport && !showCPRViewport"
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

    <!-- Control toggle button (visible when controls are hidden) -->
    <button v-if="!showControlOverlay" @click="showControlOverlay = true" class="show-controls-btn">
      Show Controls
    </button>

    <!-- Add MPR button - Only show if neither MPR nor CPR is open -->
    <button v-if="!showMPRViewport && !showCPRViewport" @click="openMPRViewport" class="mpr-btn">
      Open MPR View
    </button>

    <!-- Add CPR button - Only show if neither MPR nor CPR is open -->
    <button v-if="!showCPRViewport" @click="openCPRViewport" class="cpr-btn">Open CPR View</button>

    <!-- MPR Viewport Placeholder - Logic to be moved here later -->
    <MPRViewport
      v-if="showMPRViewport && mprImageData && vtkInstance"
      :image-data="mprImageData"
      :window-width="windowWidth"
      :window-center="windowCenter"
      :vtk-instance="vtkInstance"
      :mpr-viewports="mprViewports"
      @close="closeMPRViewport"
    />

    <!-- CPR Viewport Placeholder - Logic to be moved here later -->
    <CPRViewport
      v-if="showCPRViewport && cprImageData && vtkInstance && coronaryArteryData"
      :image-data="cprImageData"
      :window-width="windowWidth"
      :window-center="windowCenter"
      :vtk-instance="vtkInstance"
      :viewports="cprViewports"
      :coronaryArteryData="coronaryArteryData"
      @close="closeCPRViewport"
    />

    <!-- The actual volume rendering will happen in the parent's shared viewport for now -->
    <!-- Or we might manage viewports differently later -->
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { computed, ref, watch, type PropType } from 'vue'

// Import types
import type {
  CoronaryArteryData,
  Viewport,
  Visualization,
  VTKViewerInstance,
} from '@/types/visualization'

// Import components
import CPRViewport from '@/components/CPRViewport.vue' // Placeholder
import MPRViewport from '@/components/MPRViewport.vue' // Placeholder
import VolumeControls from '@/components/VolumeControls.vue'

// Import composables and stores
import { useControlPanelState } from '@/composables/useControlPanelState'
import { useVisualizationStore } from '@/stores/useVisualizationStore'

// Import services (for future MPR/CPR logic AND labels/interaction)
import { drawLabelsForVisualization } from '@/services/labelService'
import {
  cleanupViewport,
  createCPRViewports,
  createMPRViewports,
} from '@/services/vtkViewerService'
import vtkImageData from '@kitware/vtk.js/Common/DataModel/ImageData' // For future MPR/CPR

const props = defineProps({
  visualization: {
    type: Object as PropType<Visualization>,
    required: true,
  },
  vtkInstance: {
    // Pass the VTK instance down for now, might use provide/inject later
    type: Object as PropType<VTKViewerInstance | null>,
    required: true,
  },
  isActive: {
    type: Boolean,
    default: false,
  },
})

const visualizationStore = useVisualizationStore()
const { showControlOverlay } = storeToRefs(visualizationStore)

// Use control panel state, passing the vtkInstance ref
// Note: The vtkInstance prop is potentially null, handle this if necessary
// Or ensure it's always passed non-null when this component is active.
// For now, assuming it's non-null when isActive is true.
const {
  windowWidth,
  windowCenter,
  windowWidthMax,
  windowCenterMin,
  windowCenterMax,
  iSlice,
  jSlice,
  kSlice,
  iExtentMin,
  iExtentMax,
  jExtentMin,
  jExtentMax,
  kExtentMin,
  kExtentMax,
  updateWindowLevel,
  updateSlices,
  setVolumeControlParams,
} = useControlPanelState(computed(() => props.vtkInstance)) // Pass vtkInstance as a computed ref

// MPR/CPR State (Placeholders - To be populated when logic moves here)
const showMPRViewport = ref(false)
const mprImageData = ref<vtkImageData | null>(null)
const mprViewports = ref<Viewport[]>([])
const showCPRViewport = ref(false)
const cprImageData = ref<vtkImageData | null>(null)
const cprViewports = ref<Viewport[]>([])
const coronaryArteryData = ref<CoronaryArteryData | null>(null)

// Watch when this specific visualization becomes active
watch(
  () => props.isActive,
  (newIsActive) => {
    if (newIsActive && props.visualization.type === 'volume') {
      console.log(
        `VolumeViewer: ${props.visualization.seriesId} is now active. Setting controls, interaction, and labels.`,
      )
      const params = props.visualization.controlParams
      if (params) {
        setVolumeControlParams({
          ...params,
          // Ensure window/level from controlParams are used if available,
          // otherwise default to current state (which might be initial values)
          windowCenter: params.windowCenter ?? windowCenter.value,
          windowWidth: params.windowWidth ?? windowWidth.value,
        })
      } else {
        console.warn(
          `VolumeViewer: Active volume ${props.visualization.seriesId} missing controlParams.`,
        )
      }

      // --- Draw Labels ---
      if (props.visualization.labels && props.visualization.labels.length > 0) {
        console.log(`VolumeViewer: Drawing labels for ${props.visualization.seriesId}`)
        // Ensure the visualization has the correct viewport assigned for label drawing
        if (props.visualization.viewport?.renderer) {
          drawLabelsForVisualization(props.visualization)
          // Trigger render after drawing labels if necessary
          // props.vtkInstance?.renderWindow.render();
          // Consider if render should be triggered here or centrally
        } else {
          console.warn(
            `VolumeViewer: Visualization ${props.visualization.seriesId} missing viewport/renderer for label drawing.`,
          )
        }
      } else {
        console.log(`VolumeViewer: No labels to draw for ${props.visualization.seriesId}`)
      }

      // Interaction setup and rendering are currently handled in VTKCanvas watcher
      // This might move here later if this component manages its own viewport.
    }
  },
  { immediate: true },
) // Run immediately to set initial state if active

// --- Control Update Methods ---
function updateWindowLevelUI() {
  if (props.isActive && props.visualization.type === 'volume') {
    updateWindowLevel(props.visualization)
  }
}

function updateSlicesUI() {
  if (props.isActive && props.visualization.type === 'volume') {
    updateSlices(props.visualization)
  }
}

// --- MPR/CPR Methods (Placeholders - To be implemented when logic moves) ---
function openMPRViewport() {
  if (!props.vtkInstance || props.visualization.type !== 'volume' || !props.visualization.data)
    return
  console.log('Opening MPR Viewport for:', props.visualization.seriesId)
  mprImageData.value = props.visualization.data

  // Assume the initial viewport container is hidden by the parent (VTKCanvas)
  // We just need to create the MPR viewports here

  mprViewports.value = createMPRViewports(
    props.vtkInstance.renderWindow,
    props.vtkInstance.rootContainer,
    props.vtkInstance.interactor,
    props.vtkInstance.imageInteractorStyle,
    props.vtkInstance.trackballInteractorStyle,
  )
  showMPRViewport.value = true
  props.vtkInstance.renderWindow.render() // Force render
}

function closeMPRViewport() {
  showMPRViewport.value = false
  if (props.vtkInstance && mprViewports.value.length > 0) {
    mprViewports.value.forEach((viewport) => {
      cleanupViewport(viewport, props.vtkInstance!.renderWindow, props.vtkInstance!.interactor)
    })
    mprViewports.value = []
  }
  mprImageData.value = null

  // Logic to show the main viewport again needs coordination with parent (VTKCanvas)
  // For now, just reset interactor style/container if applicable
  if (props.vtkInstance && props.visualization.viewport?.container) {
    props.vtkInstance.interactor.setInteractorStyle(props.vtkInstance.trackballInteractorStyle)
    props.vtkInstance.interactor.setContainer(props.visualization.viewport.container)
    props.vtkInstance.renderWindow?.render()
  }

  // TODO: Emit event or signal parent to show the main viewport
  console.log('Closed MPR Viewport')
}

async function openCPRViewport() {
  if (
    !props.vtkInstance ||
    props.visualization.type !== 'volume' ||
    !props.visualization.data ||
    !props.visualization.seriesId
  )
    return
  console.log('Opening CPR Viewport for:', props.visualization.seriesId)

  try {
    const coronaryArteryLabels =
      props.visualization.labels?.filter((label) => label.type === 'coronaryArtery') || []

    if (coronaryArteryLabels.length === 0) {
      alert('No coronary artery data available for this series')
      return
    } else {
      const coronaryArteryLabel = coronaryArteryLabels[0]
      coronaryArteryData.value = coronaryArteryLabel.data as CoronaryArteryData
    }

    cprImageData.value = props.visualization.data

    // Assume parent hides main viewport
    cprViewports.value = createCPRViewports(
      props.vtkInstance.renderWindow,
      props.vtkInstance.rootContainer,
      props.vtkInstance.interactor,
      props.vtkInstance.imageInteractorStyle,
    )

    showCPRViewport.value = true
    props.vtkInstance.renderWindow.render()
  } catch (error) {
    console.error('Error preparing CPR viewport:', error)
    alert('Failed to open CPR view')
  }
}

function closeCPRViewport() {
  showCPRViewport.value = false
  if (props.vtkInstance && cprViewports.value.length > 0) {
    cprViewports.value.forEach((viewport) => {
      cleanupViewport(viewport, props.vtkInstance!.renderWindow, props.vtkInstance!.interactor)
    })
    cprViewports.value = []
  }
  cprImageData.value = null
  coronaryArteryData.value = null

  // Signal parent to show main viewport and reset interactor
  if (props.vtkInstance && props.visualization.viewport?.container) {
    props.vtkInstance.interactor.setInteractorStyle(props.vtkInstance.trackballInteractorStyle)
    props.vtkInstance.interactor.setContainer(props.visualization.viewport.container)
    props.vtkInstance.renderWindow?.render()
  }
  console.log('Closed CPR Viewport')
}
</script>

<style scoped>
.volume-viewer-container {
  /* Container now overlays the VTK view */
  position: absolute;
  top: 0;
  left: 0;
  width: 100%; /* Ensure it covers the area */
  height: 100%;
  pointer-events: none; /* Allow clicks to pass through to VTK canvas */
  z-index: 5; /* Sit above VTK canvas but below side panel/modal popups */
}

/* Styles for controls, buttons need pointer-events: auto */
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
  z-index: 15; /* Ensure above container */
  font-size: 0.8em;
  pointer-events: auto; /* Make button clickable */
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
  z-index: 100; /* Ensure above container */
  pointer-events: auto; /* Make button clickable */
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
  z-index: 100; /* Ensure above container */
  pointer-events: auto; /* Make button clickable */
}
.cpr-btn:hover {
  background-color: #1976d2;
}

/* Ensure controls overlay can be interacted with */
:deep(.volume-controls-overlay) {
  position: absolute;
  bottom: 10px;
  left: 10px;
  z-index: 10;
  pointer-events: auto; /* Make controls clickable */
}

/* MPR/CPR viewports already use absolute positioning and high z-index */
:deep(.mpr-container),
:deep(.cpr-container) {
  /* Ensure MPR/CPR cover the area correctly when active */
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 20; /* Ensure they are above controls/buttons */
  pointer-events: auto; /* MPR/CPR need interaction */
}
</style>
