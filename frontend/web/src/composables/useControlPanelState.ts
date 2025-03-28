import {
  applyWindowLevel,
  updateMultiframeFrame as updateFramePosition,
  updateVolumeSlices,
} from '@/services/visualizationService'
import type { Visualization, VTKViewerInstance } from '@/types/visualization'
import { ref, type Ref } from 'vue'

export type ControlMode = 'volume' | 'multiframe' | 'none'

/**
 * Composable to manage control panel state for different visualization types
 */
export function useControlPanelState(vtkInstance: Ref<VTKViewerInstance | null>) {
  // Shared window level controls
  const windowWidth = ref(400)
  const windowCenter = ref(40)
  const windowWidthMax = ref(4000)
  const windowCenterMin = ref(-1000)
  const windowCenterMax = ref(1000)

  // Volume-specific controls
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

  // Track current control mode
  const controlMode = ref<ControlMode>('none')

  /**
   * Update window level for the current visualization
   */
  function updateWindowLevel(visualization: Visualization) {
    if (!vtkInstance.value?.renderWindow) return

    applyWindowLevel(visualization, windowCenter.value, windowWidth.value)
    vtkInstance.value.renderWindow.render()
  }

  /**
   * Update volume slices
   */
  function updateSlices(volumeVisualization: Visualization) {
    if (!volumeVisualization || !vtkInstance.value?.renderWindow) return

    updateVolumeSlices(volumeVisualization, iSlice.value, jSlice.value, kSlice.value)
    vtkInstance.value.renderWindow.render()
  }

  /**
   * Update multiframe frame position
   */
  function updateMultiframeFrame(multiframeVisualization: Visualization) {
    if (!multiframeVisualization || !vtkInstance.value?.renderWindow) return

    updateFramePosition(multiframeVisualization, currentFrame.value)
    vtkInstance.value.renderWindow.render()
  }

  /**
   * Toggle multiframe playback
   */
  function togglePlayback(multiframeVisualization: Visualization) {
    if (!multiframeVisualization) return

    isPlaying.value = !isPlaying.value

    if (isPlaying.value) {
      // Start playback
      if (playbackInterval) {
        clearInterval(playbackInterval)
      }

      playbackInterval = setInterval(() => {
        currentFrame.value = (currentFrame.value + 1) % (maxFrame.value + 1)
        updateMultiframeFrame(multiframeVisualization)
      }, 1000 / playbackSpeed.value)
    } else {
      // Stop playback
      if (playbackInterval) {
        clearInterval(playbackInterval)
        playbackInterval = null
      }
    }
  }

  /**
   * Set control parameters for volume visualization
   */
  function setVolumeControlParams(params: {
    iExtentMin: number
    iExtentMax: number
    jExtentMin: number
    jExtentMax: number
    kExtentMin: number
    kExtentMax: number
    iSlice: number
    jSlice: number
    kSlice: number
    windowCenterMin: number
    windowCenterMax: number
    windowWidthMax: number
    windowCenter: number
    windowWidth: number
  }) {
    // Set volume-specific controls
    iExtentMin.value = params.iExtentMin
    iExtentMax.value = params.iExtentMax
    jExtentMin.value = params.jExtentMin
    jExtentMax.value = params.jExtentMax
    kExtentMin.value = params.kExtentMin
    kExtentMax.value = params.kExtentMax
    iSlice.value = params.iSlice
    jSlice.value = params.jSlice
    kSlice.value = params.kSlice

    // Set common window level controls
    windowCenterMin.value = params.windowCenterMin
    windowCenterMax.value = params.windowCenterMax
    windowWidthMax.value = params.windowWidthMax
    windowCenter.value = params.windowCenter
    windowWidth.value = params.windowWidth

    // Update control mode
    controlMode.value = 'volume'
  }

  /**
   * Set control parameters for multiframe visualization
   */
  function setMultiframeControlParams(params: {
    maxFrame: number
    windowCenterMin: number
    windowCenterMax: number
    windowWidthMax: number
    windowCenter: number
    windowWidth: number
  }) {
    // Set multiframe-specific controls
    maxFrame.value = params.maxFrame
    currentFrame.value = 0

    // Set common window level controls
    windowCenterMin.value = params.windowCenterMin
    windowCenterMax.value = params.windowCenterMax
    windowWidthMax.value = params.windowWidthMax
    windowCenter.value = params.windowCenter
    windowWidth.value = params.windowWidth

    // Update control mode
    controlMode.value = 'multiframe'
  }

  /**
   * Clean up resources
   */
  function cleanup() {
    if (playbackInterval) {
      clearInterval(playbackInterval)
      playbackInterval = null
    }
  }

  return {
    // Shared controls
    windowWidth,
    windowCenter,
    windowWidthMax,
    windowCenterMin,
    windowCenterMax,
    controlMode,

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
    togglePlayback,
    setVolumeControlParams,
    setMultiframeControlParams,
    cleanup,
  }
}
