import { drawLabelsForVisualization, removeLabel } from '@/services/labelService'
import { fetchAvailableLabels, fetchLabelContent, fetchSeriesData } from '@/services/orthancService'
import {
  loadMultiframeVisualization,
  loadVolumeVisualization,
  removeVisualization,
  setVisualizationVisibility,
} from '@/services/visualizationService'
import type { Series } from '@/types/orthanc'; // Added Series type
import type { Label, Viewport, Visualization, VTKViewerInstance } from '@/types/visualization'; // Correct import path & Added Label
import type vtkRenderer from '@kitware/vtk.js/Rendering/Core/Renderer'; // Added vtkRenderer type
import { defineStore, storeToRefs } from 'pinia'
import { computed, ref, type Ref } from 'vue'
import { usePatientStudyStore } from './usePatientStudyStore'; // Added Patient Study Store

export const useVisualizationStore = defineStore('visualization', () => {
  // --- State ---
  const visualizations: Ref<Visualization[]> = ref([])
  const activeVisualizationIndex: Ref<number> = ref(-1)
  const showControlOverlay: Ref<boolean> = ref(true)

  // --- Label State ---
  const availableLabelFilenames: Ref<string[]> = ref([])
  const selectedLabelFilenames: Ref<string[]> = ref([])
  const loadingLabels: Ref<boolean> = ref(false)
  const labelError: Ref<string | null> = ref(null)

  // --- Getters ---
  const hasVisualizations = computed(() => visualizations.value.length > 0)

  const activeVisualization = computed<Visualization | null>(() => {
    if (
      activeVisualizationIndex.value >= 0 &&
      activeVisualizationIndex.value < visualizations.value.length
    ) {
      return visualizations.value[activeVisualizationIndex.value]
    }
    return null
  })

  const activeVolume = computed(() => {
    const activeVis = activeVisualization.value
    return activeVis?.type === 'volume' ? activeVis : null
  })

  const activeMultiframe = computed(() => {
    const activeVis = activeVisualization.value
    return activeVis?.type === 'multiframe' ? activeVis : null
  })

  // --- Actions ---
  function addVisualization(visualization: Visualization): number {
    visualizations.value.push(visualization)
    // Set as active visualization
    activeVisualizationIndex.value = visualizations.value.length - 1
    showControlOverlay.value = true // Ensure controls are shown for the new active vis
    return activeVisualizationIndex.value
  }

  function toggleVisibility(index: number, vtkInstance: VTKViewerInstance | null): void {
    const vis = visualizations.value[index]
    if (!vis || !vtkInstance) return

    const newVisibility = !vis.visible
    setVisualizationVisibility(vis, newVisibility) // Assuming this updates vis.visible internally

    if (vtkInstance.renderWindow) {
      vtkInstance.renderWindow.render()
    }
  }

  function removeVisualizationById(index: number, vtkInstance: VTKViewerInstance | null): void {
    if (!vtkInstance) return

    const visToRemove = visualizations.value[index]
    if (!visToRemove) return

    // Use the service to remove the visualization actors/resources
    // Ensure the viewport and renderer exist before calling
    if (visToRemove.viewport?.renderer) {
      removeVisualization(visToRemove.viewport.renderer, visToRemove)
    } else {
      console.warn('Attempted to remove visualization without a valid viewport/renderer.')
      // Handle cases where actors might have been added differently, if necessary
    }

    // Remove from visualizations array
    visualizations.value.splice(index, 1)

    // Update active visualization index
    const newLength = visualizations.value.length
    if (newLength === 0) {
      activeVisualizationIndex.value = -1
      showControlOverlay.value = false // Hide overlay if no visualizations left
    } else if (activeVisualizationIndex.value === index) {
      // If the removed one was active, make the first one active
      activeVisualizationIndex.value = 0
      showControlOverlay.value = true // Show controls for the new active vis
    } else if (activeVisualizationIndex.value > index) {
      // If an item before the active one was removed, decrement the index
      activeVisualizationIndex.value--
    }
    // If an item after the active one was removed, the index remains correct

    if (vtkInstance.renderWindow) {
      vtkInstance.renderWindow.render()
    }
  }

  function setActiveVisualization(index: number): void {
    if (index >= 0 && index < visualizations.value.length) {
      activeVisualizationIndex.value = index
      showControlOverlay.value = true // Show controls when setting active visualization
    } else if (visualizations.value.length === 0) {
      // Handle case where last visualization was removed externally somehow
      activeVisualizationIndex.value = -1
      showControlOverlay.value = false
    }
    // If index is invalid but there are visualizations, maybe default to 0 or do nothing?
    // Current behavior: does nothing if index is out of bounds but visualizations exist.
  }

  function closeOverlay(): void {
    showControlOverlay.value = false
  }

  // --- NEW Action for Loading Series ---
  async function loadAndAddVisualization(
    seriesId: string,
    renderer: vtkRenderer,
    viewport: Viewport, // Need viewport for label drawing association for now
  ): Promise<void> {
    const patientStudyStore = usePatientStudyStore()
    const { studies } = storeToRefs(patientStudyStore)

    // Check if already loaded
    const alreadyLoaded = visualizations.value.some((vis) => vis.seriesId === seriesId)
    if (alreadyLoaded) {
      const index = visualizations.value.findIndex((vis) => vis.seriesId === seriesId)
      if (index !== -1) {
        setActiveVisualization(index)
      }
      // Notify store loading is complete (even though it was already loaded)
      patientStudyStore.setSeriesLoadingCompleteAction(seriesId, true)
      return
    }

    // Find series details
    let seriesToLoad: Series | null = null
    for (const study of studies.value) {
      const foundSeries = study.series?.find((s) => s.ID === seriesId)
      if (foundSeries) {
        seriesToLoad = foundSeries
        break
      }
    }

    if (!seriesToLoad) {
      console.error(`Store: Could not find series details for ID ${seriesId}.`)
      patientStudyStore.setSeriesLoadingCompleteAction(seriesId, false)
      // Consider throwing an error or setting an error state in this store
      return
    }

    let success = false
    try {
      // Fetch raw data
      const result = await fetchSeriesData(seriesId)
      const {
        data: vtiData,
        windowWidth: receivedWindowWidth,
        windowCenter: receivedWindowCenter,
      } = result

      let loadedVisResult: Awaited<
        ReturnType<typeof loadVolumeVisualization | typeof loadMultiframeVisualization>
      > | null = null

      // Create visualization based on modality
      if (seriesToLoad.MainDicomTags.Modality === 'XA') {
        loadedVisResult = await loadMultiframeVisualization(
          renderer,
          seriesId,
          seriesToLoad,
          vtiData,
          receivedWindowWidth,
          receivedWindowCenter,
        )
      } else if (seriesToLoad.MainDicomTags.Modality === 'CT') {
        loadedVisResult = await loadVolumeVisualization(
          renderer,
          seriesId,
          seriesToLoad,
          vtiData,
          receivedWindowWidth,
          receivedWindowCenter,
        )
      } else {
        throw new Error(`Unsupported modality: ${seriesToLoad.MainDicomTags.Modality}`)
      }

      // Store viewport reference and control parameters with the visualization
      loadedVisResult.visualization.viewport = viewport
      // Assuming load... functions return { visualization: ..., controlParams: ... }
      // We'll store controlParams directly on the visualization object
      // Modify Visualization type if needed to accommodate this
      ;(loadedVisResult.visualization as any).controlParams = loadedVisResult.controlParams

      // Add the successfully created visualization to the store
      addVisualization(loadedVisResult.visualization)

      // Note: Label drawing is NOT done here. It will be triggered by the component
      //       watching the activeVisualization or its labels.

      success = true
    } catch (error: unknown) {
      console.error(`Store: Error loading series data for ${seriesId}:`, error)
      // Maybe set an error state in this store?
      success = false
      // Rethrow or handle more gracefully?
      if (error instanceof Error) {
        alert('Store: Failed to visualize series: ' + error.message)
      } else {
        alert('Store: Failed to visualize series: unknown error')
      }
    } finally {
      patientStudyStore.setSeriesLoadingCompleteAction(seriesId, success)
    }
  }

  // --- Label Management Actions ---

  function addLabelToVisualizationAction(label: Label, seriesId: string): void {
    const visualization = visualizations.value.find((vis) => vis.seriesId === seriesId)
    if (!visualization) {
      console.error(`Could not find visualization with seriesId ${seriesId} to add label.`)
      return
    }
    // Ensure the labels array exists
    if (!visualization.labels) {
      visualization.labels = []
    }
    // Avoid adding duplicate labels (based on filename)
    if (!visualization.labels.some((l) => l.filename === label.filename)) {
      visualization.labels.push(label)
    } else {
      console.warn(`Label ${label.filename} already exists for series ${seriesId}.`)
    }
  }

  function removeLabelFromVisualizationAction(labelFilename: string, seriesId: string): void {
    const visualization = visualizations.value.find((vis) => vis.seriesId === seriesId)
    if (!visualization || !visualization.labels) {
      console.warn(
        `Could not find visualization or labels for seriesId ${seriesId} to remove label ${labelFilename}.`,
      )
      return
    }

    const labelIndex = visualization.labels.findIndex((l) => l.filename === labelFilename)
    if (labelIndex !== -1) {
      // Remove the label VTK actor if it exists
      const labelToRemove = visualization.labels[labelIndex]
      if (visualization.viewport?.renderer && labelToRemove.vtkActor) {
        removeLabel(visualization.viewport.renderer, labelToRemove)
      }

      // Remove the label object from the store state
      visualization.labels.splice(labelIndex, 1)
    } else {
      console.warn(`Label ${labelFilename} not found in visualization for series ${seriesId}.`)
    }
  }

  async function fetchAvailableLabelsAction(seriesId: string | null): Promise<void> {
    if (!seriesId) {
      availableLabelFilenames.value = []
      return
    }

    loadingLabels.value = true
    labelError.value = null

    try {
      // Use the orthancService function
      const labels = await fetchAvailableLabels(seriesId)
      availableLabelFilenames.value = labels

      // Update selected labels based on what's already loaded in the visualization
      const vis = visualizations.value.find((v) => v.seriesId === seriesId)
      if (vis && vis.labels) {
        selectedLabelFilenames.value = vis.labels.map((label) => label.filename)
      } else {
        selectedLabelFilenames.value = []
      }
    } catch (error) {
      console.error('Error fetching available labels:', error)
      labelError.value = error instanceof Error ? error.message : 'Unknown error fetching labels'
      availableLabelFilenames.value = []
    } finally {
      loadingLabels.value = false
    }
  }

  async function toggleLabelSelectionAction(
    labelFilename: string,
    seriesId: string,
  ): Promise<void> {
    const isSelected = selectedLabelFilenames.value.includes(labelFilename)

    if (isSelected) {
      // Remove the label
      selectedLabelFilenames.value = selectedLabelFilenames.value.filter(
        (filename) => filename !== labelFilename,
      )

      // Remove from visualization
      removeLabelFromVisualizationAction(labelFilename, seriesId)
    } else {
      // Add the label
      selectedLabelFilenames.value.push(labelFilename)

      try {
        // Use the orthancService function
        const label = (await fetchLabelContent(seriesId, labelFilename)) as Label

        // Add to visualization
        addLabelToVisualizationAction(label, seriesId)

        // If visualization is currently active, draw the label
        const vis = visualizations.value.find((v) => v.seriesId === seriesId)
        if (vis && vis === activeVisualization.value && vis.viewport?.renderer) {
          drawLabelsForVisualization(vis)
        }
      } catch (error) {
        console.error(`Error loading label ${labelFilename}:`, error)
        // Remove from selected if loading failed
        selectedLabelFilenames.value = selectedLabelFilenames.value.filter(
          (filename) => filename !== labelFilename,
        )
      }
    }
  }

  // Return all state, getters, and actions
  return {
    // State
    visualizations,
    activeVisualizationIndex,
    showControlOverlay,

    // Label State
    availableLabelFilenames,
    selectedLabelFilenames,
    loadingLabels,
    labelError,

    // Getters
    hasVisualizations,
    activeVolume,
    activeMultiframe,
    activeVisualization, // Expose general active vis getter

    // Actions
    addVisualization,
    toggleVisibility,
    removeVisualizationById,
    setActiveVisualization,
    closeOverlay,

    // Label actions
    addLabelToVisualizationAction,
    removeLabelFromVisualizationAction,
    fetchAvailableLabelsAction,
    toggleLabelSelectionAction,
    // New loading action
    loadAndAddVisualization,
  }
})
