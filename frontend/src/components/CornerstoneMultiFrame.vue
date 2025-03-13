<template>
  <div class="cornerstone-container">
    <div id="demo-toolbar"></div>
    <div id="content"></div>
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
import {
  prefetchMetadataInformation,
  htmlSetup,
  addButtonToToolbar,
  convertMultiframeImageIds,
} from '../helpers/cornerstone'
import * as cornerstoneTools from '@cornerstonejs/tools'
import uids from '../helpers/cornerstone/uids'
import { init as dicomImageLoaderInit, wadouri } from '@cornerstonejs/dicom-image-loader'

// Add type definition for ToolGroup
interface ToolGroup {
  addTool: (toolName: string) => void
  addViewport: (viewportId: string, renderingEngineId: string) => void
  setToolActive: (toolName: string, options: any) => void
}

coreInit()
dicomImageLoaderInit()

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
}>()

// Add ref for tracking image loading state
const imageLoaded = ref(false)

const renderingEngineId = 'myRenderingEngine'
const toolGroupId = 'toolGroup'

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

// Initialize Cornerstone
onMounted(async () => {
  // await initDemo()

  const { element } = htmlSetup(document)
  // Reference to the cornerstone element
  engine = new RenderingEngine(renderingEngineId)
  toolGroup = setupTools(toolGroupId)

  // Create a stack viewport
  const viewportId = 'CT_STACK'
  const viewportInput = {
    viewportId,
    type: ViewportType.STACK,
    element,
    defaultOptions: {
      background: <Types.Point3>[0.2, 0, 0.2],
    },
  }
  engine.enableElement(viewportInput)
  viewport = <Types.IStackViewport>engine.getViewport(viewportId)

  // Add this important line to connect the tool group to the viewport
  toolGroup.addViewport(viewportId, renderingEngineId)

  addButtonToToolbar({
    title: 'Next Image',
    onClick: () => {
      // Get the rendering engine
      const engine = getRenderingEngine(renderingEngineId)

      // Get the stack viewport
      const viewport = engine.getViewport(viewportId) as Types.IStackViewport

      // Get the current index of the image displayed
      const currentImageIdIndex = viewport.getCurrentImageIdIndex()

      // Increment the index, clamping to the last image if necessary
      const numImages = viewport.getImageIds().length
      let newImageIdIndex = currentImageIdIndex + 1

      newImageIdIndex = Math.min(newImageIdIndex, numImages - 1)

      // Set the new image index, the viewport itself does a re-render
      viewport.setImageIdIndex(newImageIdIndex)
    },
  })

  // Add playback controls
  addButtonToToolbar({
    title: 'Play',
    onClick: () => {
      if (viewport && !isPlaying.value) {
        startPlayback('CT_STACK')
      }
    },
  })

  addButtonToToolbar({
    title: 'Stop',
    onClick: () => {
      stopPlayback()
    },
  })

  // If imageId is already available, load the image
  if (props.imageIds) {
    await loadAndViewImage(props.imageIds)
  }
})

// Watch for changes to imageId prop
watch(
  () => props.imageIds,
  async (newImageIds) => {
    if (newImageIds) {
      await loadAndViewImage(newImageIds)
    }
  },
)

function getDataset(imageId: string) {
  const parsedImageId = wadouri.parseImageId(imageId)
  return wadouri.dataSetCacheManager.get(parsedImageId.url)
}

async function loadAndViewImage(imageIds: string[]) {
  if (!imageIds || !viewport) {
    console.error('Missing imageId or viewport not initialized')
    return
  }

  imageLoaded.value = false

  try {
    await prefetchMetadataInformation(imageIds)
    // Set the stack on the viewport
    await viewport.setStack(convertMultiframeImageIds(imageIds))

    // Render the image
    viewport.render()

    const imageData = viewport.getImageData()
    // const dataset = getDataset(imageId)
    // console.log(dataset)

    const { pixelRepresentation, bitsAllocated, bitsStored, highBit, photometricInterpretation } =
      metaData.get(MetadataModules.IMAGE_PIXEL, imageIds[0])

    const voiLutModule = metaData.get(MetadataModules.VOI_LUT, imageIds[0])
    const sopCommonModule = metaData.get(MetadataModules.SOP_COMMON, imageIds[0])
    const transferSyntax = metaData.get('transferSyntax', imageIds[0])
    // console.log(metaData.get('instance', imageId))

    // Update metadata display elements
    const updateElement = (id: string, value: any) => {
      const element = document.getElementById(id)
      if (element) {
        element.innerHTML = value?.toString() || ''
      }
    }

    updateElement('transfersyntax', transferSyntax?.transferSyntaxUID || '')
    updateElement(
      'sopclassuid',
      sopCommonModule?.sopClassUID
        ? `${sopCommonModule.sopClassUID} [${uids[sopCommonModule.sopClassUID] || 'Unknown'}]`
        : '',
    )
    updateElement('sopinstanceuid', sopCommonModule?.sopInstanceUID || '')
    updateElement('rows', imageData?.dimensions?.[0]?.toString() || '')
    updateElement('columns', imageData?.dimensions?.[1]?.toString() || '')
    updateElement('spacing', imageData?.spacing?.join('\\') || '')
    updateElement(
      'direction',
      imageData?.direction?.map((x) => Math.round(x * 100) / 100).join(',') || '',
    )
    updateElement(
      'origin',
      imageData?.origin?.map((x) => Math.round(x * 100) / 100).join(',') || '',
    )
    updateElement('modality', imageData?.metadata?.Modality || '')
    updateElement('pixelrepresentation', pixelRepresentation || '')
    updateElement('bitsallocated', bitsAllocated || '')
    updateElement('bitsstored', bitsStored || '')
    updateElement('highbit', highBit || '')
    updateElement('photometricinterpretation', photometricInterpretation || '')
    updateElement('windowcenter', voiLutModule?.windowCenter || '')
    updateElement('windowwidth', voiLutModule?.windowWidth || '')

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

    // Check for frame increment pointer
    const frameIncrementPointer = metaData.get('frameIncrementPointer', imageId)
    if (frameIncrementPointer) {
      console.log('Using frame increment pointer:', frameIncrementPointer)
      return 1000 / frameIncrementPointer
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
async function startPlayback(viewportId: string) {
  if (isPlaying.value || !viewport) return

  // Get the appropriate frame rate from DICOM
  const engine = getRenderingEngine(renderingEngineId)
  if (!engine) return

  const stackViewport = engine.getViewport(viewportId) as Types.IStackViewport
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

// Make sure to stop playback when component is unmounted
onUnmounted(() => {
  stopPlayback()
})

// Ensure playback stops when a new image is loaded
watch(
  () => props.imageId,
  () => {
    // Stop any ongoing playback when image changes
    stopPlayback()
  },
)
</script>

<style scoped>
.cornerstone-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

#cornerstone-element {
  width: 100%;
  height: 70vh;
  background-color: #000;
}

.image-info {
  padding: 10px;
  background-color: #f5f5f5;
  overflow-y: auto;
  max-height: 30vh;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 10px;
}

.metadata-row {
  display: flex;
  margin-bottom: 5px;
}

.metadata-label {
  font-weight: bold;
  margin-right: 10px;
  min-width: 170px;
}

.metadata-value {
  font-family: monospace;
  word-break: break-all;
}
</style>
