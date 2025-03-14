<template>
  <div class="orthogonal-viewer" ref="containerRef">
    <!-- Three-panel layout for orthogonal views -->
    <div class="viewports-container">
      <div class="viewport" ref="axialViewport">
        <div class="viewport-label">Axial</div>
      </div>
      <div class="viewport" ref="sagittalViewport">
        <div class="viewport-label">Sagittal</div>
      </div>
      <div class="viewport" ref="coronalViewport">
        <div class="viewport-label">Coronal</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, computed } from 'vue'
import {
  init as coreInit,
  RenderingEngine,
  Enums,
  volumeLoader,
  setVolumesForViewports,
} from '@cornerstonejs/core'
import { init as dicomImageLoaderInit } from '@cornerstonejs/dicom-image-loader'
import {
  addManipulationBindings,
  setCtTransferFunctionForVolumeActor,
  prefetchMetadataInformation,
} from '../helpers/cornerstone'
import * as cornerstoneTools from '@cornerstonejs/tools'
import { init as cornerstoneToolsInit } from '@cornerstonejs/tools'

// Initialize once
const isCornerstoneInitialized = ref(false)
if (!isCornerstoneInitialized.value) {
  coreInit()
  dicomImageLoaderInit()
  cornerstoneToolsInit()
  isCornerstoneInitialized.value = true
}

// Get required tools from cornerstone tools
const {
  ToolGroupManager,
  Enums: csToolsEnums,
  CrosshairsTool,
  synchronizers,
  TrackballRotateTool,
} = cornerstoneTools

const { createSlabThicknessSynchronizer } = synchronizers

const { MouseBindings } = csToolsEnums
const { ViewportType } = Enums

const props = defineProps<{
  imageIds: string[]
  itemId: string
  modality: string // To check if it's CT
}>()

// Refs for the viewport DOM elements
const containerRef = ref<HTMLElement | null>(null)
const axialViewport = ref<HTMLElement | null>(null)
const sagittalViewport = ref<HTMLElement | null>(null)
const coronalViewport = ref<HTMLElement | null>(null)

// IDs for cornerstone components
const volumeId = `volume-${props.itemId}`
const toolGroupId = `orthoToolGroup-${props.itemId}`
const axialViewportId = `axial-${props.itemId}`
const sagittalViewportId = `sagittal-${props.itemId}`
const coronalViewportId = `coronal-${props.itemId}`
const renderingEngineId = `orthoEngine-${props.itemId}`
const synchronizerId = `synchronizer-${props.itemId}`
const viewportIds = [axialViewportId, sagittalViewportId, coronalViewportId]

// References to cornerstone objects
let renderingEngine: RenderingEngine | null = null
let toolGroup: any = null
let synchronizer: any = null

// Check if the modality is CT
const isCT = computed(() => props.modality === 'CT')

// Colors for reference lines
const viewportColors = {
  [axialViewportId]: 'rgb(200, 0, 0)',
  [sagittalViewportId]: 'rgb(0, 200, 0)',
  [coronalViewportId]: 'rgb(0, 0, 200)',
}

function setUpSynchronizers() {
  synchronizer = createSlabThicknessSynchronizer(synchronizerId)

  // Add viewports to VOI synchronizers
  viewportIds.forEach((viewportId) => {
    synchronizer.add({
      renderingEngineId,
      viewportId,
    })
  })
  // Normally this would be left on, but here we are starting the demo in the
  // default state, which is to not have a synchronizer enabled.
  synchronizer.setEnabled(false)
}

// Define which viewports should have controllable reference lines
const viewportReferenceLineControllable = viewportIds
const viewportReferenceLineDraggableRotatable = viewportIds
const viewportReferenceLineSlabThicknessControlsOn = viewportIds

function getReferenceLineColor(viewportId: string) {
  return viewportColors[viewportId]
}

function getReferenceLineControllable(viewportId: string) {
  return viewportReferenceLineControllable.indexOf(viewportId) !== -1
}

function getReferenceLineDraggableRotatable(viewportId: string) {
  return viewportReferenceLineDraggableRotatable.indexOf(viewportId) !== -1
}

function getReferenceLineSlabThicknessControlsOn(viewportId: string) {
  return viewportReferenceLineSlabThicknessControlsOn.indexOf(viewportId) !== -1
}

// Set up the orthogonal views with crosshairs
async function setupOrthogonalViews() {
  if (!isCT.value) {
    console.warn('This component works best with CT images.')
  }

  if (!axialViewport.value || !sagittalViewport.value || !coronalViewport.value) {
    console.error('Viewport elements not found')
    return
  }

  cornerstoneTools.addTool(CrosshairsTool)
  cornerstoneTools.addTool(TrackballRotateTool)
  await prefetchMetadataInformation(props.imageIds)

  // Create and cache the volume - following the example pattern
  const volume = await volumeLoader.createAndCacheVolume(volumeId, {
    imageIds: props.imageIds,
  })

  // Load the volume
  volume.load()

  // Create a new rendering engine
  renderingEngine = new RenderingEngine(renderingEngineId)

  // Define the viewports
  const viewportInputArray = [
    {
      viewportId: axialViewportId,
      type: ViewportType.ORTHOGRAPHIC,
      element: axialViewport.value,
      defaultOptions: {
        orientation: Enums.OrientationAxis.AXIAL,
        background: [0, 0, 0],
      },
    },
    {
      viewportId: sagittalViewportId,
      type: ViewportType.ORTHOGRAPHIC,
      element: sagittalViewport.value,
      defaultOptions: {
        orientation: Enums.OrientationAxis.SAGITTAL,
        background: [0, 0, 0],
      },
    },
    {
      viewportId: coronalViewportId,
      type: ViewportType.ORTHOGRAPHIC,
      element: coronalViewport.value,
      defaultOptions: {
        orientation: Enums.OrientationAxis.CORONAL,
        background: [0, 0, 0],
      },
    },
  ]

  // Set up the viewports
  renderingEngine.setViewports(viewportInputArray)

  // Set the volumes for all viewports
  await setVolumesForViewports(
    renderingEngine,
    [{ volumeId, callback: setCtTransferFunctionForVolumeActor }],
    viewportIds,
  )

  // Create a tool group
  toolGroup = ToolGroupManager.createToolGroup(toolGroupId)
  addManipulationBindings(toolGroup)

  // Add viewports to tool group
  viewportIds.forEach((id) => {
    toolGroup.addViewport(id, renderingEngineId)
  })

  // Add tools
  toolGroup.addTool(CrosshairsTool.toolName, {
    getReferenceLineColor,
    getReferenceLineControllable,
    getReferenceLineDraggableRotatable,
    getReferenceLineSlabThicknessControlsOn,
  })

  // // Set tools active
  toolGroup.setToolActive(CrosshairsTool.toolName, {
    bindings: [{ mouseButton: MouseBindings.Primary }],
  })

  setUpSynchronizers()
  // Render all viewports
  renderingEngine.renderViewports(viewportIds)
}

// Watch for changes to imageIds and reinitialize when they change
watch(
  () => props.imageIds,
  async (newImageIds) => {
    if (newImageIds.length > 0) {
      // Clean up existing resources
      cleanup()
      // Set up new viewports
      await setupOrthogonalViews()
    }
  },
)

// Cleanup function to remove resources
function cleanup() {
  if (renderingEngine) {
    try {
      // Disable the viewports
      viewportIds.forEach((viewportId) => {
        try {
          const viewport = renderingEngine?.getViewport(viewportId)
          if (viewport) {
            // Just render one last time before cleanup
            viewport.render()
          }
        } catch (error) {
          console.warn(`Error with viewport ${viewportId}:`, error)
        }
      })

      // Remove the tool group
      if (toolGroup) {
        try {
          // Remove viewports from tool group
          viewportIds.forEach((id) => {
            try {
              toolGroup.removeViewport(id)
            } catch (e) {
              console.warn(`Error removing viewport ${id} from tool group:`, e)
            }
          })

          // We can't use destroyToolGroup directly due to TypeScript errors
          // Instead, we'll use a workaround by getting the ToolGroupManager
          const tools = cornerstoneTools as any
          if (
            tools.ToolGroupManager &&
            typeof tools.ToolGroupManager.destroyToolGroup === 'function'
          ) {
            tools.ToolGroupManager.destroyToolGroup(toolGroupId)
          }
        } catch (error) {
          console.warn('Error destroying tool group:', error)
        }
      }
    } catch (error) {
      console.error('Error during cleanup:', error)
    }
  }
}

// Set up the viewports when the component is mounted
onMounted(async () => {
  if (props.imageIds.length > 0) {
    await setupOrthogonalViews()
  }
})

// Clean up resources when component unmounts
onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.orthogonal-viewer {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #222;
}

.viewports-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 4px;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.viewport {
  position: relative;
  background-color: black;
  border: 1px solid #444;
  overflow: hidden;
}

.viewport:first-child {
  grid-column: 1 / span 2;
}

.viewport-label {
  position: absolute;
  top: 5px;
  left: 10px;
  color: white;
  font-size: 14px;
  background-color: rgba(0, 0, 0, 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  z-index: 10;
  pointer-events: none;
}
</style>
