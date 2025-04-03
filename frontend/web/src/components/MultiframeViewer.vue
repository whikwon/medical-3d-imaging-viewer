<template>
  <div class="multiframe-viewer-container">
    <!-- Multiframe specific controls -->
    <MultiframeControls
      v-if="showControlOverlay"
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
    <button v-if="!showControlOverlay" @click="showControlOverlay = true" class="show-controls-btn">
      Show Controls
    </button>

    <!-- The actual multiframe rendering will happen in the parent's shared viewport for now -->
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { computed, watch, type PropType } from 'vue'

// Import types
import type { Visualization, VTKViewerInstance } from '@/types/visualization'

// Import components
import MultiframeControls from '@/components/MultiframeControls.vue'

// Import composables and stores
import { useControlPanelState } from '@/composables/useControlPanelState'
import { useVisualizationStore } from '@/stores/useVisualizationStore'

// Import services
import { drawLabelsForVisualization } from '@/services/labelService'

const props = defineProps({
  visualization: {
    type: Object as PropType<Visualization>,
    required: true,
  },
  vtkInstance: {
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

// Use control panel state
const {
  windowWidth,
  windowCenter,
  windowWidthMax,
  windowCenterMin,
  windowCenterMax,
  currentFrame,
  maxFrame,
  isPlaying,
  playbackSpeed,
  updateWindowLevel,
  updateMultiframeFrame,
  togglePlayback: playMultiframe,
  setMultiframeControlParams,
} = useControlPanelState(computed(() => props.vtkInstance))

// Watch when this specific visualization becomes active
watch(
  () => props.isActive,
  (newIsActive) => {
    if (newIsActive && props.visualization.type === 'multiframe') {
      console.log(
        `MultiframeViewer: ${props.visualization.seriesId} is now active. Setting controls, interaction, and labels.`,
      )
      const params = props.visualization.controlParams
      if (params) {
        setMultiframeControlParams({
          ...params,
          windowCenter: params.windowCenter ?? windowCenter.value,
          windowWidth: params.windowWidth ?? windowWidth.value,
          // Ensure other multiframe specific params are handled if needed
          maxFrame: params.maxFrame ?? maxFrame.value,
          currentFrame: params.currentFrame ?? currentFrame.value,
          playbackSpeed: params.playbackSpeed ?? playbackSpeed.value,
        })
        // Reset playback state when activating
        if (isPlaying.value) {
          playMultiframe(props.visualization) // Toggles it off if it was playing
        }
      } else {
        console.warn(
          `MultiframeViewer: Active multiframe ${props.visualization.seriesId} missing controlParams.`,
        )
      }

      // --- Draw Labels ---
      if (props.visualization.labels && props.visualization.labels.length > 0) {
        console.log(`MultiframeViewer: Drawing labels for ${props.visualization.seriesId}`)
        // Ensure the visualization has the correct viewport assigned for label drawing
        if (props.visualization.viewport?.renderer) {
          drawLabelsForVisualization(props.visualization)
          // Trigger render after drawing labels if necessary
          // props.vtkInstance?.renderWindow.render();
        } else {
          console.warn(
            `MultiframeViewer: Visualization ${props.visualization.seriesId} missing viewport/renderer for label drawing.`,
          )
        }
      } else {
        console.log(`MultiframeViewer: No labels to draw for ${props.visualization.seriesId}`)
      }

      // Interaction setup and rendering are currently handled in VTKCanvas watcher
    }
  },
  { immediate: true },
)

// --- Control Update Methods ---
function updateWindowLevelUI() {
  if (props.isActive && props.visualization.type === 'multiframe') {
    updateWindowLevel(props.visualization)
  }
}

function updateMultiframeFrameUI() {
  if (props.isActive && props.visualization.type === 'multiframe') {
    updateMultiframeFrame(props.visualization)
  }
}

function playMultiframeUI() {
  if (props.isActive && props.visualization.type === 'multiframe') {
    playMultiframe(props.visualization)
  }
}
</script>

<style scoped>
.multiframe-viewer-container {
  /* Container now overlays the VTK view */
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* Allow clicks to pass through to VTK canvas */
  z-index: 5; /* Match VolumeViewer */
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
  z-index: 15;
  font-size: 0.8em;
  pointer-events: auto; /* Make button clickable */
}
.show-controls-btn:hover {
  background-color: rgba(33, 150, 243, 1);
}

/* Ensure controls overlay can be interacted with */
:deep(.multiframe-controls-overlay) {
  position: absolute;
  bottom: 10px;
  left: 10px;
  z-index: 10;
  pointer-events: auto; /* Make controls clickable */
}
</style>
