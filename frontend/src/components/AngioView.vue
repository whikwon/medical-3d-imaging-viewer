<template>
  <div class="cornerstone-container">
    <div class="viewer-toolbar"></div>
    <div class="cornerstone-element" :id="`cornerstone-element-${viewportId}`"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import {
  init as coreInit,
  RenderingEngine,
  Enums,
  metaData,
  getRenderingEngine,
} from '@cornerstonejs/core'
import type { Types } from '@cornerstonejs/core'
import { prefetchMetadataInformation, convertMultiframeImageIds } from '../helpers/cornerstone'
import * as cornerstoneTools from '@cornerstonejs/tools'
import { init as dicomImageLoaderInit } from '@cornerstonejs/dicom-image-loader'
import { init as cornerstoneToolsInit } from '@cornerstonejs/tools'

// Add type definition for ToolGroup
interface ToolGroup {
  addTool: (toolName: string) => void
  addViewport: (viewportId: string, renderingEngineId: string) => void
  setToolActive: (toolName: string, options: any) => void
}

// Initialize cornerstone only once
const isCornerstoneInitialized = ref(false)
if (!isCornerstoneInitialized.value) {
  coreInit()
  dicomImageLoaderInit()
  cornerstoneToolsInit()
  isCornerstoneInitialized.value = true
}

const { ViewportType, MetadataModules } = Enums

const {
  PanTool,
  WindowLevelTool,
  StackScrollTool,
  ZoomTool,
  ToolGroupManager,
  Enums: csToolsEnums,
} = cornerstoneTools

const { MouseBindings } = csToolsEnums

// Define props
const props = defineProps<{
  imageIds: string[]
  viewportId: string
}>()

// Add ref for tracking image loading state
const imageLoaded = ref(false)

// Generate unique IDs for this viewport instance
const renderingEngineId = `renderingEngine-${props.viewportId}`
const toolGroupId = `toolGroup-${props.viewportId}`
const viewportElementId = `cornerstone-element-${props.viewportId}`
const stackViewportId = `stackViewport-${props.viewportId}`

let engine: RenderingEngine | null = null
let viewport: Types.IStackViewport | null = null
let toolGroup: ToolGroup | null = null

// Add these variables for playback control
let playbackHandle: number | null = null
const isPlaying = ref(false)

// Add tools to the tool group
function setupTools(toolGroupId: string): ToolGroup {
  cornerstoneTools.addTool(PanTool)
  cornerstoneTools.addTool(WindowLevelTool)
  cornerstoneTools.addTool(StackScrollTool)
  cornerstoneTools.addTool(ZoomTool)

  const toolGroup = ToolGroupManager.createToolGroup(toolGroupId) as unknown as ToolGroup

  // Add tools to the tool group
  toolGroup.addTool(WindowLevelTool.toolName)
  toolGroup.addTool(PanTool.toolName)
  toolGroup.addTool(ZoomTool.toolName)
  toolGroup.addTool(StackScrollTool.toolName)

  // Set the initial state of the tools
  toolGroup.setToolActive(WindowLevelTool.toolName, {
    bindings: [
      {
        mouseButton: MouseBindings.Primary, // Left Click
      },
    ],
  })
  toolGroup.setToolActive(PanTool.toolName, {
    bindings: [
      {
        mouseButton: MouseBindings.Auxiliary, // Middle Click
      },
    ],
  })
  toolGroup.setToolActive(ZoomTool.toolName, {
    bindings: [
      {
        mouseButton: MouseBindings.Secondary, // Right Click
      },
    ],
  })
  toolGroup.setToolActive(StackScrollTool.toolName, {
    bindings: [{ mouseButton: MouseBindings.Wheel }],
  })

  return toolGroup
}

// Initialize Cornerstone for this viewport
onMounted(async () => {
  // Wait a brief moment to ensure the DOM element is ready
  setTimeout(async () => {
    try {
      // Get the element
      const element = document.getElementById(viewportElementId)
      if (!element) {
        console.error(`Element with ID ${viewportElementId} not found`)
        return
      }

      // Create a rendering engine
      try {
        engine = new RenderingEngine(renderingEngineId)
      } catch (error) {
        console.warn(`Engine already exists, getting existing one: ${renderingEngineId}`)
        engine = getRenderingEngine(renderingEngineId)
      }

      // Create a tool group
      try {
        toolGroup = setupTools(toolGroupId)
      } catch (error) {
        console.warn(`Tool group already exists: ${toolGroupId}`)
        toolGroup = ToolGroupManager.getToolGroup(toolGroupId) as unknown as ToolGroup
      }

      // Create a stack viewport
      const viewportInput = {
        viewportId: stackViewportId,
        type: ViewportType.STACK,
        element,
        defaultOptions: {
          background: <Types.Point3>[0.2, 0, 0.2],
        },
      }

      engine.enableElement(viewportInput)
      viewport = <Types.IStackViewport>engine.getViewport(stackViewportId)

      // Add this important line to connect the tool group to the viewport
      toolGroup.addViewport(stackViewportId, renderingEngineId)

      // If imageId is already available, load the image
      if (props.imageIds) {
        await loadAndViewImage(props.imageIds)
      }
    } catch (error) {
      console.error('Error initializing viewport:', error)
    }
  }, 50) // Short delay to ensure DOM is ready
})

// Watch for changes to imageIds prop
watch(
  () => props.imageIds,
  async (newImageIds) => {
    if (newImageIds && viewport) {
      await loadAndViewImage(newImageIds)
    }
  },
)

// Clean up when component is destroyed
onUnmounted(() => {
  stopPlayback()

  // Clean up engine and viewport if needed
  if (engine) {
    try {
      engine.disableElement(stackViewportId)
    } catch (error) {
      console.warn('Error disabling element:', error)
    }
  }
})

async function loadAndViewImage(imageIds: string[]) {
  if (!imageIds || !viewport) {
    console.error('Missing imageIds or viewport not initialized')
    return
  }

  imageLoaded.value = false

  try {
    await prefetchMetadataInformation(imageIds)
    // Set the stack on the viewport
    await viewport.setStack(convertMultiframeImageIds(imageIds))

    // Render the image
    viewport.render()

    imageLoaded.value = true
  } catch (error) {
    console.error('Error loading image:', error)
    imageLoaded.value = false
  }
}

// Function to get frame rate from DICOM tags
async function getFrameRateFromDicom(imageId: string): Promise<number> {
  await prefetchMetadataInformation([imageId])

  try {
    // Try to get recommended display frame rate
    const cineModule = metaData.get('cineModule', imageId)
    if (cineModule && cineModule.recommendedDisplayFrameRate) {
      console.log('Using recommended display frame rate:', cineModule.recommendedDisplayFrameRate)
      return cineModule.recommendedDisplayFrameRate
    }

    // Try to get frame time (in milliseconds)
    if (cineModule && cineModule.frameTime) {
      // Convert frame time (in ms) to frames per second
      const fps = 1000 / cineModule.frameTime
      console.log('Calculated FPS from frame time:', fps)
      return fps
    }

    // Fallback to a reasonable default
    console.log('No frame rate information found, using default of 15 FPS')
    return 15 // Default 15 FPS if no timing info found
  } catch (error) {
    console.error('Error getting frame rate from DICOM:', error)
    return 15 // Fallback to 15 FPS
  }
}

// Function to start playback with correct frame rate
async function startPlayback() {
  if (isPlaying.value || !viewport) return

  // Get the appropriate frame rate from DICOM
  const engine = getRenderingEngine(renderingEngineId)
  if (!engine) return

  const stackViewport = engine.getViewport(stackViewportId) as Types.IStackViewport
  const currentImageId = stackViewport.getImageIds()[0]

  // Get FPS from DICOM tags
  const fps = await getFrameRateFromDicom(currentImageId)
  const frameDelayMs = 1000 / fps

  console.log(`Starting playback at ${fps} FPS (${frameDelayMs}ms delay)`)

  isPlaying.value = true

  // Start playback loop
  playbackHandle = window.setInterval(() => {
    // Get current frame index
    const currentIndex = stackViewport.getCurrentImageIdIndex()
    const numFrames = stackViewport.getImageIds().length

    // Go to next frame or loop back to beginning
    const nextIndex = (currentIndex + 1) % numFrames
    stackViewport.setImageIdIndex(nextIndex)
  }, frameDelayMs)
}

// Function to stop playback
function stopPlayback() {
  if (!isPlaying.value) return

  console.log('Stopping playback')

  if (playbackHandle !== null) {
    window.clearInterval(playbackHandle)
    playbackHandle = null
  }

  isPlaying.value = false
}
</script>

<style scoped>
.cornerstone-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.viewer-toolbar {
  height: 30px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  padding: 0 10px;
  flex-shrink: 0;
}

.cornerstone-element {
  flex: 1;
  width: 100%;
  background-color: #000;
  position: relative;
}
</style>
