<template>
  <div class="vtk-container">
    <div class="controls">
      <h2>3D Volume Viewer</h2>

      <!-- Always show the series selection -->
      <div class="series-selection-container">
        <h3>Select Data</h3>
        <div class="series-selection">
          <select v-model="selectedStudy" @change="handleStudyChange" :disabled="loadingStudies">
            <option value="">Select a study</option>
            <option v-for="study in studies" :key="study.ID" :value="study.ID">
              {{ study.PatientMainDicomTags.PatientName || 'Unknown' }} -
              {{ study.MainDicomTags.StudyDescription || 'Unknown Study' }}
            </option>
          </select>

          <select v-if="selectedStudy" v-model="selectedSeries" :disabled="loadingSeries">
            <option value="">Select a series</option>
            <option v-for="series in seriesList" :key="series.ID" :value="series.ID">
              {{ series.MainDicomTags.SeriesDescription || 'Unknown Series' }} -
              {{ series.MainDicomTags.SeriesNumber || 'Unknown' }}
              ({{ series.MainDicomTags.Modality || 'Unknown' }})
            </option>
          </select>

          <button
            @click="loadSelectedSeries"
            :disabled="!selectedSeries || loading"
            class="load-btn"
          >
            Add to Viewer
          </button>
        </div>
      </div>

      <!-- Show help text when no visualizations are loaded -->
      <div v-if="!hasVisualizations" class="no-data">
        <p>No data loaded. Select a series above to visualize.</p>
      </div>

      <div v-if="loading" class="loading">
        <p>Loading data... Please wait.</p>
        <div class="loader"></div>
      </div>

      <div v-if="hasVisualizations" class="visualization-list">
        <h3>Loaded Visualizations</h3>
        <div class="visualization-items">
          <div
            v-for="(vis, index) in visualizations"
            :key="index"
            class="visualization-item"
            @click="setActiveVisualization(index)"
            :class="{ active: index === activeVisualizationIndex }"
          >
            <span>{{ vis.description }}</span>
            <div class="vis-controls">
              <button @click.stop="toggleVisibility(index)" class="toggle-btn">
                {{ vis.visible ? 'Hide' : 'Show' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="vtk-view-container">
      <div ref="vtkContainer" class="vtk-viewer"></div>

      <!-- Overlay visualization tags with remove buttons -->
      <div v-if="hasVisualizations" class="visualization-overlays">
        <div class="overlay-header-label">Loaded Visualizations</div>
        <div
          v-for="(vis, index) in visualizations"
          :key="index"
          class="overlay-item"
          :class="{ active: index === activeVisualizationIndex }"
          @click="setActiveVisualization(index)"
        >
          <span>{{ vis.description }}</span>
          <div class="overlay-item-actions">
            <button @click.stop="toggleVisibility(index)" class="overlay-toggle-btn">
              <span v-if="vis.visible">👁️</span>
              <span v-else>🔍</span>
            </button>
            <button @click.stop="removeVisualization(index)" class="overlay-remove-btn">×</button>
          </div>
        </div>
      </div>

      <!-- Overlay controls for volume -->
      <div v-if="activeVolume && showControlOverlay" class="control-overlay volume-overlay">
        <div class="overlay-header">
          <h4>Volume Controls</h4>
          <button @click="closeOverlay" class="overlay-close">×</button>
        </div>

        <div class="preset-buttons">
          <button @click="applyPreset('soft')" class="control-btn">Soft Tissue</button>
          <button @click="applyPreset('lung')" class="control-btn">Lung</button>
          <button @click="applyPreset('bone')" class="control-btn">Bone</button>
        </div>

        <div class="sliders">
          <div class="slider-container">
            <label>Window Width:</label>
            <input
              type="range"
              v-model.number="windowWidth"
              :min="1"
              :max="windowWidthMax"
              @input="updateWindowLevel"
            />
            <span>{{ windowWidth }}</span>
          </div>

          <div class="slider-container">
            <label>Window Center:</label>
            <input
              type="range"
              v-model.number="windowCenter"
              :min="windowCenterMin"
              :max="windowCenterMax"
              @input="updateWindowLevel"
            />
            <span>{{ windowCenter }}</span>
          </div>
        </div>

        <div class="slice-controls">
          <h4>Slice Navigation</h4>
          <div class="slider-container">
            <label>Axial (K):</label>
            <input
              type="range"
              v-model.number="kSlice"
              :min="kExtentMin"
              :max="kExtentMax"
              @input="updateSlices"
            />
            <span>{{ kSlice }}</span>
          </div>

          <div class="slider-container">
            <label>Coronal (J):</label>
            <input
              type="range"
              v-model.number="jSlice"
              :min="jExtentMin"
              :max="jExtentMax"
              @input="updateSlices"
            />
            <span>{{ jSlice }}</span>
          </div>

          <div class="slider-container">
            <label>Sagittal (I):</label>
            <input
              type="range"
              v-model.number="iSlice"
              :min="iExtentMin"
              :max="iExtentMax"
              @input="updateSlices"
            />
            <span>{{ iSlice }}</span>
          </div>
        </div>
      </div>

      <!-- Overlay controls for multiframe -->
      <div v-if="activeMultiframe && showControlOverlay" class="control-overlay multiframe-overlay">
        <div class="overlay-header">
          <h4>Multiframe Controls</h4>
          <button @click="closeOverlay" class="overlay-close">×</button>
        </div>

        <div class="slider-container">
          <label>Frame:</label>
          <input
            type="range"
            v-model.number="currentFrame"
            :min="0"
            :max="maxFrame"
            @input="updateMultiframeFrame"
          />
          <span>{{ currentFrame + 1 }} / {{ maxFrame + 1 }}</span>
        </div>
        <div class="player-controls">
          <button @click="playMultiframe" class="control-btn">
            {{ isPlaying ? 'Pause' : 'Play' }}
          </button>
          <div class="speed-control">
            <label>Speed:</label>
            <input type="range" v-model.number="playbackSpeed" min="1" max="30" step="1" />
            <span>{{ playbackSpeed }} fps</span>
          </div>
        </div>
      </div>

      <!-- Control toggle button (visible when controls are hidden) -->
      <button
        v-if="!showControlOverlay && (activeVolume || activeMultiframe)"
        @click="showControlOverlay = true"
        class="show-controls-btn"
      >
        Show Controls
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import '@kitware/vtk.js/IO/Core/DataAccessHelper/HtmlDataAccessHelper'
import '@kitware/vtk.js/IO/Core/DataAccessHelper/HttpDataAccessHelper'
import '@kitware/vtk.js/IO/Core/DataAccessHelper/JSZipDataAccessHelper'
import '@kitware/vtk.js/Rendering/Profiles/Geometry'
import '@kitware/vtk.js/Rendering/Profiles/Volume'

import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import vtkSphereSource from '@kitware/vtk.js/Filters/Sources/SphereSource'
import vtkXMLImageDataReader from '@kitware/vtk.js/IO/XML/XMLImageDataReader'
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor'
import vtkCellPicker from '@kitware/vtk.js/Rendering/Core/CellPicker'
import vtkCoordinate from '@kitware/vtk.js/Rendering/Core/Coordinate'
import vtkImageMapper from '@kitware/vtk.js/Rendering/Core/ImageMapper'
import vtkImageSlice from '@kitware/vtk.js/Rendering/Core/ImageSlice'
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper'
import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor'
import vtkFullScreenRenderWindow from '@kitware/vtk.js/Rendering/Misc/FullScreenRenderWindow'

interface Study {
  ID: string
  MainDicomTags: {
    StudyDescription: string
  }
  PatientMainDicomTags: {
    PatientName: string
  }
}

interface Series {
  ID: string
  MainDicomTags: {
    SeriesDescription: string
    SeriesNumber: string
    Modality: string
  }
}

// Define a more specific type for VTK objects for better error handling
type VtkObject = Record<string, unknown>

interface Visualization {
  type: 'volume' | 'multiframe'
  seriesId: string
  description: string
  actors: Array<VtkObject> // VTK.js actors
  visible: boolean
  data?: VtkObject // VTK.js image data
}

// Refs for DOM elements and data
const vtkContainer = ref<HTMLElement | null>(null)
const studies = ref<Study[]>([])
const seriesList = ref<Series[]>([])
const selectedStudy = ref('')
const selectedSeries = ref('')
const loading = ref(false)
const loadingStudies = ref(false)
const loadingSeries = ref(false)
const showControlOverlay = ref(true)

// Visualization tracking
const visualizations = ref<Visualization[]>([])
const activeVisualizationIndex = ref(-1)

// Computed property to determine if any visualizations are loaded
const hasVisualizations = computed(() => visualizations.value.length > 0)

// Volume-specific controls
const windowWidth = ref(400)
const windowCenter = ref(40)
const windowWidthMax = ref(4000)
const windowCenterMin = ref(-1000)
const windowCenterMax = ref(1000)
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

// Computed properties to get active visualization data
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

// VTK.js instances - using type assertion for VTK objects
let renderWindow = null as unknown as VtkObject
let renderer = null as unknown as VtkObject
let fullScreenRenderer = null as unknown as VtkObject
let interactor = null as unknown as VtkObject

// Add these variables at the top with other refs
const coneActor = ref<unknown>(null)
const lastPosition = ref<number[] | null>(null)
const coordinate = ref<unknown>(null)

onMounted(async () => {
  // Initialize VTK.js
  if (vtkContainer.value) {
    fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({
      container: vtkContainer.value,
      background: [0.1, 0.1, 0.1],
    })
    renderWindow = fullScreenRenderer.getRenderWindow()
    renderer = fullScreenRenderer.getRenderer()
    const camera = renderer.getActiveCamera()
    camera.setParallelProjection(true)

    interactor = vtkRenderWindowInteractor.newInstance()
    interactor.setView(renderWindow.getViews()[0])
    interactor.initialize()
    interactor.bindEvents(vtkContainer.value)

    // Load studies when component is mounted
    loadStudies()
  }
})

onBeforeUnmount(() => {
  // Clean up VTK.js objects on component unmount
  if (renderWindow) {
    renderWindow.delete()
  }

  // Clear any playback interval
  if (playbackInterval) {
    clearInterval(playbackInterval)
  }

  // Modify onBeforeUnmount to clean up cone actor
  if (coneActor.value && renderer) {
    renderer.removeActor(coneActor.value)
  }
})

// Load list of studies from the backend
async function loadStudies() {
  loadingStudies.value = true
  try {
    const response = await fetch('/api/orthanc/studies')
    if (!response.ok) {
      throw new Error('Failed to fetch studies')
    }
    studies.value = await response.json()
  } catch (error) {
    console.error('Error loading studies:', error)
  } finally {
    loadingStudies.value = false
  }
}

// Handle study selection change
async function handleStudyChange() {
  if (!selectedStudy.value) {
    seriesList.value = []
    selectedSeries.value = ''
    return
  }

  loadingSeries.value = true
  try {
    // Load series for the selected study
    const response = await fetch(`/api/orthanc/studies/${selectedStudy.value}/series`)
    if (!response.ok) {
      throw new Error('Failed to fetch series')
    }
    seriesList.value = await response.json()
  } catch (error) {
    console.error('Error loading series:', error)
  } finally {
    loadingSeries.value = false
  }
}

// Determine the appropriate endpoint based on modality
function getEndpointForSeries(seriesId: string): string {
  // Use the unified endpoint for all series types
  return `/api/orthanc/series/${seriesId}/data`
}

// Load the selected series into the viewer
async function loadSelectedSeries() {
  if (!selectedSeries.value) return

  loading.value = true
  try {
    const seriesId = selectedSeries.value
    const series = seriesList.value.find((s) => s.ID === seriesId)
    if (!series) {
      throw new Error('Series not found')
    }

    // Check if this series is already loaded
    const alreadyLoaded = visualizations.value.some((vis) => vis.seriesId === seriesId)
    if (alreadyLoaded) {
      throw new Error('This series is already loaded in the viewer')
    }

    const endpoint = getEndpointForSeries(seriesId)

    // Fetch data from the backend
    const response = await fetch(endpoint)
    if (!response.ok) {
      throw new Error(`Failed to fetch data: ${response.statusText}`)
    }

    const vtiData = await response.blob()

    if (series.MainDicomTags.Modality === 'XA') {
      await loadMultiframeData(seriesId, series, vtiData)
    } else if (series.MainDicomTags.Modality === 'CT') {
      await loadVolumeData(seriesId, series, vtiData)
    } else {
      throw new Error(`Unsupported modality: ${series.MainDicomTags.Modality}`)
    }

    // Clear the selection after successful loading
    // But keep the study selected to allow adding more series from the same study
    selectedSeries.value = ''
  } catch (error: unknown) {
    console.error('Error loading data:', error)
    if (error instanceof Error) {
      alert('Failed to load data: ' + error.message)
    } else {
      alert('Failed to load data: unknown error')
    }
  } finally {
    loading.value = false
  }
}

// Add this function before loadVolumeData
function setupConeInteraction() {
  if (!renderer || !renderWindow || !interactor) return

  // Create cone source
  const sphereSource = vtkSphereSource.newInstance({
    radius: 10.0,
    thetaResolution: 12,
    phiResolution: 12,
  })

  const mapper = vtkMapper.newInstance()
  mapper.setInputConnection(sphereSource.getOutputPort())

  const actor = vtkActor.newInstance()
  actor.setMapper(mapper)
  actor.getProperty().setColor(1.0, 0.0, 0.0)

  // Position the sphere based on visualization type
  const currentVis = activeVolume.value || activeMultiframe.value
  if (currentVis && currentVis.data) {
    const extent = currentVis.data.getExtent()
    const spacing = currentVis.data.getSpacing()
    const origin = currentVis.data.getOrigin()

    if (currentVis.type === 'multiframe') {
      // For multiframe, position at bottom-left of first frame
      // Convert extent indices to world coordinates
      const x = origin[0] + extent[0] * spacing[0]
      const y = origin[1] + extent[2] * spacing[1]
      const z = origin[2] + extent[4] * spacing[2]
      actor.setPosition(x, y, z)
    } else {
      // For CT volume, position at bottom-left of last slice
      // Convert extent indices to world coordinates
      const x = origin[0] + extent[0] * spacing[0]
      const y = origin[1] + extent[2] * spacing[1]
      const z = origin[2] + extent[5] * spacing[2]
      actor.setPosition(x, y, z)
    }
  }

  // Create picker
  const picker = vtkCellPicker.newInstance()
  picker.setPickFromList(1)
  picker.setTolerance(0)
  picker.initializePickList()
  picker.addPickList(actor)

  // Create coordinate system
  const coord = vtkCoordinate.newInstance()
  coord.setCoordinateSystemToDisplay()

  // Store references
  coneActor.value = actor
  coordinate.value = coord

  // Add actor to renderer
  renderer.addActor(actor)

  // Set up interaction handlers
  interactor.onLeftButtonPress((event: any) => {
    const displayPosition = [event.position.x, event.position.y, 0]
    picker.pick(displayPosition, renderer)
    if (picker.getActors().length > 0) {
      const pickedPositions = picker.getPickedPositions()
      lastPosition.value = pickedPositions[0]
    }
  })

  interactor.onRightButtonPress((event: any) => {
    if (!lastPosition.value || !coordinate.value || !renderer) return

    const camera = renderer.getActiveCamera()
    const planeNormal = camera.getDirectionOfProjection()
    const planePoint = lastPosition.value

    const nearDisplay = [event.position.x, event.position.y, 0.0]
    coordinate.value.setValue(nearDisplay)
    const worldNear = coordinate.value.getComputedWorldValue(renderer)

    const farDisplay = [event.position.x, event.position.y, 1.0]
    coordinate.value.setValue(farDisplay)
    const worldFar = coordinate.value.getComputedWorldValue(renderer)

    const rayDirection = [
      worldFar[0] - worldNear[0],
      worldFar[1] - worldNear[1],
      worldFar[2] - worldNear[2],
    ]
    const len = Math.sqrt(
      rayDirection[0] * rayDirection[0] +
        rayDirection[1] * rayDirection[1] +
        rayDirection[2] * rayDirection[2],
    )
    rayDirection[0] /= len
    rayDirection[1] /= len
    rayDirection[2] /= len

    const num =
      (planePoint[0] - worldNear[0]) * planeNormal[0] +
      (planePoint[1] - worldNear[1]) * planeNormal[1] +
      (planePoint[2] - worldNear[2]) * planeNormal[2]
    const denom =
      rayDirection[0] * planeNormal[0] +
      rayDirection[1] * planeNormal[1] +
      rayDirection[2] * planeNormal[2]
    if (denom === 0) return
    const t = num / denom
    const currentPosition = [
      worldNear[0] + t * rayDirection[0],
      worldNear[1] + t * rayDirection[1],
      worldNear[2] + t * rayDirection[2],
    ]

    const translation = [
      currentPosition[0] - lastPosition.value[0],
      currentPosition[1] - lastPosition.value[1],
      currentPosition[2] - lastPosition.value[2],
    ]

    // Move all actors in the current visualization
    const currentVis = activeVolume.value || activeMultiframe.value
    if (currentVis) {
      currentVis.actors.forEach((actor: any) => {
        const currentPos = actor.getPosition()
        actor.setPosition(
          currentPos[0] + translation[0],
          currentPos[1] + translation[1],
          currentPos[2] + translation[2],
        )
      })
    }

    // Move the sphere along with the images
    const currentSpherePos = actor.getPosition()
    actor.setPosition(
      currentSpherePos[0] + translation[0],
      currentSpherePos[1] + translation[1],
      currentSpherePos[2] + translation[2],
    )

    lastPosition.value = currentPosition
    renderWindow.render()
  })
}

// Modify loadVolumeData to call setupConeInteraction
async function loadVolumeData(seriesId: string, series: Series, vtiData: Blob) {
  const reader = vtkXMLImageDataReader.newInstance()
  const url = URL.createObjectURL(vtiData)

  try {
    await reader.setUrl(url)
    const data = reader.getOutputData()
    const dataRange = data.getPointData().getScalars().getRange()
    const extent = data.getExtent()

    // Calculate center slices for better initial view
    const centerI = Math.floor((extent[1] - extent[0]) / 2)
    const centerJ = Math.floor((extent[3] - extent[2]) / 2)
    const centerK = Math.floor((extent[5] - extent[4]) / 2)

    // Create the image mappers and actors
    const imageMapperI = vtkImageMapper.newInstance()
    imageMapperI.setInputData(data)
    imageMapperI.setSlice(centerI)
    imageMapperI.setSlicingMode(0) // I slicing

    const imageMapperJ = vtkImageMapper.newInstance()
    imageMapperJ.setInputData(data)
    imageMapperJ.setSlice(centerJ)
    imageMapperJ.setSlicingMode(1) // J slicing

    const imageMapperK = vtkImageMapper.newInstance()
    imageMapperK.setInputData(data)
    imageMapperK.setSlice(centerK)
    imageMapperK.setSlicingMode(2) // K slicing

    const actorI = vtkImageSlice.newInstance()
    actorI.setMapper(imageMapperI)

    const actorJ = vtkImageSlice.newInstance()
    actorJ.setMapper(imageMapperJ)

    const actorK = vtkImageSlice.newInstance()
    actorK.setMapper(imageMapperK)

    // Add actors to renderer
    if (renderer) {
      renderer.addActor(actorI)
      renderer.addActor(actorJ)
      renderer.addActor(actorK)
    }

    // Update slice range controls
    iExtentMin.value = extent[0]
    iExtentMax.value = extent[1]
    jExtentMin.value = extent[2]
    jExtentMax.value = extent[3]
    kExtentMin.value = extent[4]
    kExtentMax.value = extent[5]

    iSlice.value = centerI
    jSlice.value = centerJ
    kSlice.value = centerK

    // Set data range-based bounds for sliders
    windowCenterMin.value = Math.floor(dataRange[0])
    windowCenterMax.value = Math.ceil(dataRange[1])
    windowWidthMax.value = Math.ceil(dataRange[1] - dataRange[0])

    // For CT images, default to a soft tissue window
    windowWidth.value = 400
    windowCenter.value = 40

    // Apply the window/level settings
    actorI.getProperty().setColorLevel(windowCenter.value)
    actorI.getProperty().setColorWindow(windowWidth.value)
    actorJ.getProperty().setColorLevel(windowCenter.value)
    actorJ.getProperty().setColorWindow(windowWidth.value)
    actorK.getProperty().setColorLevel(windowCenter.value)
    actorK.getProperty().setColorWindow(windowWidth.value)

    // Create a visualization record without position and isDragging
    const visualization: Visualization = {
      type: 'volume',
      seriesId,
      description: `${series.MainDicomTags.SeriesDescription || 'Unknown'} (${series.MainDicomTags.Modality || 'CT'})`,
      actors: [actorI, actorJ, actorK],
      visible: true,
      data,
    }

    // Add to visualizations array
    visualizations.value.push(visualization)
    activeVisualizationIndex.value = visualizations.value.length - 1

    if (renderer && renderWindow) {
      setupConeInteraction()
      renderer.resetCamera()
      renderWindow.render()
    }
  } finally {
    // Clean up the URL
    URL.revokeObjectURL(url)
  }
}

// Modify loadMultiframeData to call setupConeInteraction
async function loadMultiframeData(seriesId: string, series: Series, vtiData: Blob | null = null) {
  if (!vtiData) {
    // If vtiData wasn't provided, fetch it now
    const response = await fetch(`/api/orthanc/series/${seriesId}/data`)
    if (!response.ok) {
      throw new Error(`Failed to fetch multiframe data: ${response.statusText}`)
    }
    vtiData = await response.blob()
  }

  const reader = vtkXMLImageDataReader.newInstance()
  if (!vtiData) {
    throw new Error('Invalid data blob')
  }
  const url = URL.createObjectURL(vtiData)

  try {
    await reader.setUrl(url)
    const data = reader.getOutputData()
    const dataRange = data.getPointData().getScalars().getRange()
    const extent = data.getExtent()

    // For multiframe, we'll use K slicing for frame navigation
    const numFrames = extent[5] - extent[4] + 1

    // Create image mapper and actor for the multiframe data
    const imageMapper = vtkImageMapper.newInstance()
    imageMapper.setInputData(data)
    imageMapper.setSlice(0) // Start with the first frame
    imageMapper.setSlicingMode(2) // K slicing for frames

    const actor = vtkImageSlice.newInstance()
    actor.setMapper(imageMapper)

    // Add actor to renderer
    if (renderer) {
      renderer.addActor(actor)
    }

    // Set up multiframe controls
    maxFrame.value = numFrames - 1
    currentFrame.value = 0

    // Set basic window/level based on data range
    const ww = Math.ceil((dataRange[1] - dataRange[0]) / 2)
    const wc = Math.floor(dataRange[0] + ww)

    actor.getProperty().setColorLevel(wc)
    actor.getProperty().setColorWindow(ww)

    // Create a visualization record without position and isDragging
    const visualization: Visualization = {
      type: 'multiframe',
      seriesId,
      description: `${series.MainDicomTags.SeriesDescription || 'Unknown'} (${series.MainDicomTags.Modality || 'XA'})`,
      actors: [actor],
      visible: true,
      data,
    }

    // Add to visualizations array
    visualizations.value.push(visualization)
    activeVisualizationIndex.value = visualizations.value.length - 1

    if (renderer && renderWindow) {
      setupConeInteraction()
      renderer.resetCamera()
      renderWindow.render()
    }
  } finally {
    // Clean up the URL
    URL.revokeObjectURL(url)
  }
}

// Toggle visibility of a visualization
function toggleVisibility(index: number) {
  const vis = visualizations.value[index]
  if (!vis || !renderer) return

  vis.visible = !vis.visible

  // Set visibility for all actors in this visualization
  vis.actors.forEach((actor) => {
    actor.setVisibility(vis.visible)
  })

  if (renderWindow) {
    renderWindow.render()
  }
}

// Remove a visualization
function removeVisualization(index: number) {
  const vis = visualizations.value[index]
  if (!vis || !renderer) return

  // Remove all actors from renderer
  vis.actors.forEach((actor) => {
    if (renderer) {
      renderer.removeActor(actor)
    }
  })

  // Remove from visualizations array
  visualizations.value.splice(index, 1)

  // Update active visualization if needed
  if (activeVisualizationIndex.value === index) {
    activeVisualizationIndex.value = visualizations.value.length > 0 ? 0 : -1
  } else if (activeVisualizationIndex.value > index) {
    activeVisualizationIndex.value--
  }

  if (renderWindow) {
    renderWindow.render()
  }
}

function applyPreset(preset: 'soft' | 'lung' | 'bone') {
  if (!activeVolume.value) return

  switch (preset) {
    case 'soft':
      windowWidth.value = 400
      windowCenter.value = 40
      break
    case 'lung':
      windowWidth.value = 1500
      windowCenter.value = -600
      break
    case 'bone':
      windowWidth.value = 2500
      windowCenter.value = 500
      break
  }
  updateWindowLevel()
}

function updateWindowLevel() {
  if (!activeVolume.value || !renderWindow) return

  const colorLevel = windowCenter.value
  const colorWindow = windowWidth.value

  // Apply to all actors in the active volume
  activeVolume.value.actors.forEach((actor) => {
    actor.getProperty().setColorLevel(colorLevel)
    actor.getProperty().setColorWindow(colorWindow)
  })

  renderWindow.render()
}

function updateSlices() {
  if (!activeVolume.value || !renderWindow) return

  const actors = activeVolume.value.actors
  // Assuming actors are in order: I, J, K
  const iMapper = actors[0].getMapper()
  const jMapper = actors[1].getMapper()
  const kMapper = actors[2].getMapper()

  iMapper.setSlice(iSlice.value)
  jMapper.setSlice(jSlice.value)
  kMapper.setSlice(kSlice.value)

  renderWindow.render()
}

// Update the current frame in multiframe data
function updateMultiframeFrame() {
  if (!activeMultiframe.value || !renderWindow) return

  const actor = activeMultiframe.value.actors[0]
  const mapper = actor.getMapper()

  mapper.setSlice(currentFrame.value)

  renderWindow.render()
}

// Play/pause multiframe data
function playMultiframe() {
  if (!activeMultiframe.value) return

  isPlaying.value = !isPlaying.value

  if (isPlaying.value) {
    // Start playback
    if (playbackInterval) {
      clearInterval(playbackInterval)
    }

    playbackInterval = setInterval(() => {
      currentFrame.value = (currentFrame.value + 1) % (maxFrame.value + 1)
      updateMultiframeFrame()
    }, 1000 / playbackSpeed.value)
  } else {
    // Stop playback
    if (playbackInterval) {
      clearInterval(playbackInterval)
      playbackInterval = null
    }
  }
}

// Set the active visualization for controls
function setActiveVisualization(index: number) {
  if (index >= 0 && index < visualizations.value.length) {
    activeVisualizationIndex.value = index
    showControlOverlay.value = true // Show controls when setting active visualization
  }
}
</script>

<style scoped>
.vtk-container {
  display: flex;
  flex-direction: row;
  height: 100vh;
  width: 100%;
  overflow: hidden;
}

.controls {
  padding: 10px;
  background-color: #f5f5f5;
  border-right: 1px solid #ddd;
  width: 300px;
  min-width: 300px; /* Ensures width doesn't shrink */
  max-width: 300px; /* Ensures width doesn't grow */
  height: 100vh;
  overflow-y: auto;
  flex-shrink: 0;
}

.vtk-view-container {
  flex: 1;
  position: relative;
  height: 100vh;
}

.vtk-viewer {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
}

.visualization-overlays {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background-color: rgba(0, 0, 0, 0.5);
  border-radius: 6px;
  padding: 8px;
  backdrop-filter: blur(8px);
  max-width: 300px;
}

.overlay-header-label {
  color: white;
  font-weight: bold;
  margin-bottom: 5px;
  padding-bottom: 5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  font-size: 0.9em;
}

.overlay-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: rgba(0, 0, 0, 0.4);
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  transition: all 0.2s ease;
  cursor: pointer;
  border-left: 3px solid transparent;
  margin-bottom: 2px;
}

.overlay-item:hover {
  background-color: rgba(33, 33, 33, 0.8);
  transform: translateX(3px);
}

.overlay-item.active {
  background-color: rgba(33, 150, 243, 0.8);
  border-left: 3px solid #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

.overlay-item-actions {
  display: flex;
  align-items: center;
  gap: 5px;
}

.overlay-toggle-btn {
  background: none;
  color: white;
  border: none;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.overlay-toggle-btn:hover {
  opacity: 1;
}

.overlay-remove-btn {
  background: none;
  color: white;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 0 5px;
  transition: color 0.2s;
}

.overlay-remove-btn:hover {
  color: #ff5252;
}

.control-overlay {
  position: absolute;
  background-color: rgba(33, 33, 33, 0.8);
  color: white;
  border-radius: 6px;
  padding: 15px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  z-index: 20;
  max-width: 350px;
  backdrop-filter: blur(4px);
}

.volume-overlay {
  top: 20px;
  right: 20px;
}

.multiframe-overlay {
  bottom: 20px;
  right: 20px;
}

.overlay-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.overlay-header h4 {
  margin: 0;
  font-size: 1em;
}

.overlay-close {
  background: none;
  color: white;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 0 5px;
}

.overlay-close:hover {
  color: #ff5252;
}

/* Adjust control buttons and sliders for dark overlay */
.control-overlay .control-btn {
  background-color: #3f8cff;
  transition: background-color 0.2s;
}

.control-overlay .control-btn:hover {
  background-color: #2b6fc5;
}

.control-overlay .slider-container {
  color: white;
}

.control-overlay .slider-container input[type='range'] {
  background-color: rgba(255, 255, 255, 0.2);
}

/* Keep other existing styles */
.no-data {
  padding: 10px;
  text-align: center;
  background-color: #f9f9f9;
  border-radius: 4px;
  margin: 10px 0;
}

.series-selection {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

select {
  padding: 6px;
  border-radius: 4px;
  border: 1px solid #ccc;
  width: 100%;
}

.load-btn {
  padding: 6px 12px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.load-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.preset-buttons {
  display: flex;
  gap: 5px;
  margin-bottom: 10px;
}

.sliders,
.slice-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.slice-controls {
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  padding-top: 10px;
  margin-top: 10px;
}

.slice-controls h4 {
  margin: 0 0 5px 0;
  font-size: 0.9em;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.9em;
}

.slider-container label {
  width: 90px;
  font-weight: bold;
}

.slider-container input[type='range'] {
  flex: 1;
}

.slider-container span {
  width: 40px;
  text-align: right;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px;
}

.loader {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.visualization-list {
  margin-top: 10px;
  padding: 8px;
  background-color: #f5f5f5;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.visualization-list h3 {
  margin: 0 0 5px 0;
  font-size: 0.9em;
}

.visualization-items {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 5px;
}

.visualization-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px;
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #ddd;
  font-size: 0.85em;
  cursor: pointer;
  transition: background-color 0.2s;
}

.visualization-item:hover {
  background-color: #f0f0f0;
}

.vis-controls {
  display: flex;
  gap: 5px;
}

.toggle-btn {
  padding: 3px 6px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8em;
}

.player-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 5px;
}

.speed-control {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.85em;
}

.speed-control input[type='range'] {
  width: 80px;
}

/* Show controls button */
.show-controls-btn {
  position: absolute;
  bottom: 20px;
  right: 20px;
  padding: 8px 12px;
  background-color: rgba(33, 150, 243, 0.8);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  z-index: 15;
  font-size: 0.9em;
}

.show-controls-btn:hover {
  background-color: rgba(33, 150, 243, 1);
}

/* Series selection container */
.series-selection-container {
  margin-bottom: 15px;
  padding: 8px;
  background-color: #f5f5f5;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.series-selection-container h3 {
  margin: 0 0 8px 0;
  font-size: 0.9em;
}

/* Add highlight for active visualization in sidebar */
.visualization-item.active {
  border-left: 3px solid #2196f3;
  background-color: #e3f2fd;
}
</style>
