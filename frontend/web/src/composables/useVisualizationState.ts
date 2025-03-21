import { removeVisualization, setVisualizationVisibility } from '@/services/visualizationService'
import type { VTKViewerInstance } from '@/services/vtkViewerService'
import type { Visualization } from '@/types/visualization'
import type { Ref } from 'vue'
import { computed, ref } from 'vue'

/**
 * Composable for managing visualization state
 */
export function useVisualizationState(vtkInstance: Ref<VTKViewerInstance | null>) {
  // Visualizations array
  const visualizations = ref<Visualization[]>([])
  const activeVisualizationIndex = ref(-1)
  const showControlOverlay = ref(true)

  // Computed properties
  const hasVisualizations = computed(() => visualizations.value.length > 0)

  // Active visualization accessors
  const activeVolume = computed(() => {
    if (
      activeVisualizationIndex.value >= 0 &&
      visualizations.value[activeVisualizationIndex.value]?.type === 'volume'
    ) {
      return visualizations.value[activeVisualizationIndex.value]
    }
    return null
  })

  const activeMultiframe = computed(() => {
    if (
      activeVisualizationIndex.value >= 0 &&
      visualizations.value[activeVisualizationIndex.value]?.type === 'multiframe'
    ) {
      return visualizations.value[activeVisualizationIndex.value]
    }
    return null
  })

  // Methods for visualization management
  function addVisualization(visualization: Visualization): number {
    visualizations.value.push(visualization)
    // Set as active visualization
    activeVisualizationIndex.value = visualizations.value.length - 1
    return activeVisualizationIndex.value
  }

  function toggleVisibility(index: number): void {
    const vis = visualizations.value[index]
    const instance = vtkInstance.value

    if (!vis || !instance) return

    const newVisibility = !vis.visible
    setVisualizationVisibility(vis, newVisibility)

    if (instance.renderWindow) {
      instance.renderWindow.render()
    }
  }

  function removeVisualizationById(index: number): void {
    const instance = vtkInstance.value
    if (!instance) return

    const vis = visualizations.value[index]
    if (!vis) return

    // Use the service to remove the visualization
    removeVisualization(instance, vis)

    // Remove from visualizations array
    visualizations.value.splice(index, 1)

    // Update active visualization if needed
    if (activeVisualizationIndex.value === index) {
      activeVisualizationIndex.value = visualizations.value.length > 0 ? 0 : -1
    } else if (activeVisualizationIndex.value > index) {
      activeVisualizationIndex.value--
    }

    if (instance.renderWindow) {
      instance.renderWindow.render()
    }
  }

  function setActiveVisualization(index: number): void {
    if (index >= 0 && index < visualizations.value.length) {
      activeVisualizationIndex.value = index
      showControlOverlay.value = true // Show controls when setting active visualization
    }
  }

  function closeOverlay(): void {
    showControlOverlay.value = false
  }

  // Return all state and methods
  return {
    // State
    visualizations,
    activeVisualizationIndex,
    showControlOverlay,

    // Computed
    hasVisualizations,
    activeVolume,
    activeMultiframe,

    // Methods
    addVisualization,
    toggleVisibility,
    removeVisualizationById,
    setActiveVisualization,
    closeOverlay,
  }
}
