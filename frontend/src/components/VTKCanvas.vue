<template>
  <div class="vtk-container">
    <div class="controls">
      <h2>3D Volume Viewer</h2>
      <div v-if="!loading" class="no-data">
        <p>No volume data loaded. Select a series to visualize.</p>
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
            </option>
          </select>

          <button @click="loadVolume" :disabled="!selectedSeries || loading" class="load-btn">
            Load Volume
          </button>
        </div>
      </div>

      <div v-if="loading" class="loading">
        <p>Loading volume data... Please wait.</p>
        <div class="loader"></div>
      </div>

      <div v-if="volumeLoaded" class="volume-controls">
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
    </div>

    <div ref="vtkContainer" class="vtk-viewer"></div>
  </div>
</template>

<script setup lang="ts">
import '@kitware/vtk.js/IO/Core/DataAccessHelper/HtmlDataAccessHelper'
import '@kitware/vtk.js/IO/Core/DataAccessHelper/HttpDataAccessHelper'
import '@kitware/vtk.js/IO/Core/DataAccessHelper/JSZipDataAccessHelper'
import '@kitware/vtk.js/Rendering/Profiles/Volume'
import { onBeforeUnmount, onMounted, ref } from 'vue'

import vtkFullScreenRenderWindow from '@kitware/vtk.js/Rendering/Misc/FullScreenRenderWindow'

import vtkXMLImageDataReader from '@kitware/vtk.js/IO/XML/XMLImageDataReader'
import vtkImageMapper from '@kitware/vtk.js/Rendering/Core/ImageMapper'
import vtkImageSlice from '@kitware/vtk.js/Rendering/Core/ImageSlice'

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
  }
}

// Refs for DOM elements and data
const vtkContainer = ref(null)
const studies = ref<Study[]>([])
const seriesList = ref<Series[]>([])
const selectedStudy = ref('')
const selectedSeries = ref('')
const loading = ref(false)
const loadingStudies = ref(false)
const loadingSeries = ref(false)
const volumeLoaded = ref(false)
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

// VTK.js instances
let renderWindow = null
let renderer = null
let fullScreenRenderer = null
const imageActorI = vtkImageSlice.newInstance()
const imageActorJ = vtkImageSlice.newInstance()
const imageActorK = vtkImageSlice.newInstance()

onMounted(async () => {
  // Load studies when component is mounted
  fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({
    rootContainer: vtkContainer.value,
    background: [0.1, 0.1, 0.1],
  })
  renderWindow = fullScreenRenderer.getRenderWindow()
  renderer = fullScreenRenderer.getRenderer()
  renderer.addActor(imageActorK)
  renderer.addActor(imageActorJ)
  renderer.addActor(imageActorI)
  loadStudies()
})

onBeforeUnmount(() => {
  // Clean up VTK.js objects on component unmount
  if (renderWindow) {
    renderWindow.delete()
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

// Load 3D volume data for the selected series
async function loadVolume() {
  if (!selectedSeries.value) return

  loading.value = true
  try {
    // Fetch VTI data from the backend
    const response = await fetch(`/api/orthanc/series/${selectedSeries.value}/volume`)
    if (!response.ok) {
      throw new Error('Failed to fetch VTI data')
    }
    const vtiData = await response.blob()
    const reader = vtkXMLImageDataReader.newInstance()
    const url = URL.createObjectURL(vtiData)
    reader.setUrl(url, { loadData: true }).then(() => {
      const data = reader.getOutputData()
      const dataRange = data.getPointData().getScalars().getRange()
      const extent = data.getExtent()

      // Calculate center slices for better initial view
      const centerI = Math.floor((extent[1] - extent[0]) / 2)
      const centerJ = Math.floor((extent[3] - extent[2]) / 2)
      const centerK = Math.floor((extent[5] - extent[4]) / 2)

      const imageMapperK = vtkImageMapper.newInstance()
      imageMapperK.setInputData(data)
      imageMapperK.setKSlice(centerK)
      imageActorK.setMapper(imageMapperK)

      const imageMapperJ = vtkImageMapper.newInstance()
      imageMapperJ.setInputData(data)
      imageMapperJ.setJSlice(centerJ)
      imageActorJ.setMapper(imageMapperJ)

      const imageMapperI = vtkImageMapper.newInstance()
      imageMapperI.setInputData(data)
      imageMapperI.setISlice(centerI)
      imageActorI.setMapper(imageMapperI)

      // Apply proper window/level settings for CT images
      // Set data range-based bounds for sliders
      windowCenterMin.value = Math.floor(dataRange[0])
      windowCenterMax.value = Math.ceil(dataRange[1])
      windowWidthMax.value = Math.ceil(dataRange[1] - dataRange[0])

      // For CT images, default to a soft tissue window
      windowWidth.value = 400
      windowCenter.value = 40

      // Apply the window/level settings
      updateWindowLevel()

      // Set up slice position controls
      iExtentMin.value = extent[0]
      iExtentMax.value = extent[1]
      jExtentMin.value = extent[2]
      jExtentMax.value = extent[3]
      kExtentMin.value = extent[4]
      kExtentMax.value = extent[5]

      iSlice.value = centerI
      jSlice.value = centerJ
      kSlice.value = centerK

      volumeLoaded.value = true

      renderer.resetCamera()
      renderer.resetCameraClippingRange()
      renderWindow.render()
    })

    // Create the volume visualization from VTI data
  } catch (error) {
    console.error('Error loading volume:', error)
    alert('Failed to load volume data: ' + error.message)
  } finally {
    loading.value = false
  }
}

function applyPreset(preset) {
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
  if (!volumeLoaded.value) return

  const colorLevel = windowCenter.value
  const colorWindow = windowWidth.value

  // Get properties directly and apply values
  imageActorI.getProperty().setColorLevel(colorLevel)
  imageActorI.getProperty().setColorWindow(colorWindow)
  imageActorJ.getProperty().setColorLevel(colorLevel)
  imageActorJ.getProperty().setColorWindow(colorWindow)
  imageActorK.getProperty().setColorLevel(colorLevel)
  imageActorK.getProperty().setColorWindow(colorWindow)

  renderWindow.render()
}

function updateSlices() {
  if (!volumeLoaded.value) return

  const iMapper = imageActorI.getMapper()
  const jMapper = imageActorJ.getMapper()
  const kMapper = imageActorK.getMapper()

  iMapper.setISlice(iSlice.value)
  jMapper.setJSlice(jSlice.value)
  kMapper.setKSlice(kSlice.value)

  renderWindow.render()
}
</script>

<style scoped>
.vtk-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.controls {
  padding: 10px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #ddd;
}

.vtk-viewer {
  flex: 1;
  min-height: 500px;
  position: relative;
}

.vtk-viewer.hidden {
  display: none;
}

.no-data {
  padding: 20px;
  text-align: center;
  background-color: #f9f9f9;
  border-radius: 4px;
  margin: 20px 0;
}

.series-selection {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}

select {
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ccc;
  flex: 1;
  min-width: 200px;
}

.load-btn {
  padding: 8px 16px;
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

.volume-controls {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-top: 15px;
  background-color: #f0f0f0;
  padding: 15px;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.preset-buttons {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.control-btn {
  padding: 8px 16px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.control-btn:hover {
  background-color: #0b7dda;
}

.sliders,
.slice-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.slice-controls {
  border-top: 1px solid #ddd;
  padding-top: 15px;
  margin-top: 10px;
}

.slice-controls h4 {
  margin: 0 0 10px 0;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.slider-container label {
  width: 100px;
  font-weight: bold;
}

.slider-container input[type='range'] {
  flex: 1;
}

.slider-container span {
  width: 50px;
  text-align: right;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.loader {
  border: 5px solid #f3f3f3;
  border-top: 5px solid #3498db;
  border-radius: 50%;
  width: 30px;
  height: 30px;
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
</style>
