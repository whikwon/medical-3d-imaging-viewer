<!-- https://kitware.github.io/vtk-js/examples/ImageCPRMapper.html -->
<!-- https://kitware.github.io/vtk-js/examples/Cutter.html -->

<template>
  <div class="cpr-container">
    <div class="cpr-controls">
      <button @click="$emit('close')" class="close-button">×</button>
      <div class="control-group">
        <label for="projectionMode">Projection Mode:</label>
        <select id="projectionMode" v-model="projectionMode" class="control-select">
          <option v-for="mode in projectionModes" :key="mode" :value="mode">
            {{ formatProjectionMode(mode) }}
          </option>
        </select>
      </div>
      <div class="control-group">
        <label for="thickness">Thickness:</label>
        <input
          id="thickness"
          v-model="thickness"
          type="range"
          min="0"
          max="0.5"
          step="0.01"
          class="control-range"
        />
      </div>
      <div class="control-group">
        <label for="displayMode">Mode:</label>
        <select id="displayMode" v-model="displayMode" class="control-select">
          <option value="straightened">Straightened</option>
          <option value="stretched">Stretched</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import '@kitware/vtk.js/IO/Core/DataAccessHelper/HttpDataAccessHelper'
import '@kitware/vtk.js/Rendering/Profiles/All'

import type { VTKViewerInstance, Viewport } from '@/types/visualization'
import vtkCellArray from '@kitware/vtk.js/Common/Core/CellArray'
import vtkDataArray from '@kitware/vtk.js/Common/Core/DataArray'
import { radiansFromDegrees } from '@kitware/vtk.js/Common/Core/Math'
import vtkPlane from '@kitware/vtk.js/Common/DataModel/Plane'
import vtkPolyData from '@kitware/vtk.js/Common/DataModel/PolyData'
import vtkCutter from '@kitware/vtk.js/Filters/Core/Cutter'
import vtkTubeFilter from '@kitware/vtk.js/Filters/General/TubeFilter'
import { VaryRadius } from '@kitware/vtk.js/Filters/General/TubeFilter/Constants'
import vtkImageReslice from '@kitware/vtk.js/Imaging/Core/ImageReslice'
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor'
import vtkImageCPRMapper from '@kitware/vtk.js/Rendering/Core/ImageCPRMapper'
import { ProjectionMode } from '@kitware/vtk.js/Rendering/Core/ImageCPRMapper/Constants'
import vtkImageMapper from '@kitware/vtk.js/Rendering/Core/ImageMapper'
import vtkImageSlice from '@kitware/vtk.js/Rendering/Core/ImageSlice'
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper'
import vtkWidgetManager from '@kitware/vtk.js/Widgets/Core/WidgetManager'
import { ViewTypes } from '@kitware/vtk.js/Widgets/Core/WidgetManager/Constants'
import vtkCPRManipulator from '@kitware/vtk.js/Widgets/Manipulators/CPRManipulator'
import vtkPlaneManipulator from '@kitware/vtk.js/Widgets/Manipulators/PlaneManipulator'
import vtkResliceCursorWidget from '@kitware/vtk.js/Widgets/Widgets3D/ResliceCursorWidget'
import widgetBehavior from '@kitware/vtk.js/Widgets/Widgets3D/ResliceCursorWidget/cprBehavior'
import { updateState } from '@kitware/vtk.js/Widgets/Widgets3D/ResliceCursorWidget/helpers'
import { mat3, mat4, vec3 } from 'gl-matrix'

import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  imageData: any // vtkImageData
  windowWidth: number
  windowCenter: number
  vtkInstance: VTKViewerInstance
  viewports: Viewport[]
  centerline: { position: number[]; orientation: number[] }
}>()

defineEmits<{
  (e: 'close'): void
}>()

// Constants for viewport planes
const stretchPlane = 'Y'
const crossPlane = 'Z'
const stretchViewType = ViewTypes.XZ_PLANE
const crossViewType = ViewTypes.XY_PLANE

// Control states with reactive refs
const projectionMode = ref<string>('MAX')
const projectionModes = Object.keys(ProjectionMode)
const thickness = ref(0.1)
const displayMode = ref<'straightened' | 'stretched'>('straightened')

// Computed values
const thicknessValue = computed(() => {
  return Number.parseFloat(thickness.value.toString())
})

// Format projection mode for display
function formatProjectionMode(mode: string): string {
  return mode.charAt(0) + mode.substring(1).toLowerCase()
}

// Viewport refs
const stretchViewport = ref<Viewport | null>(null)
const crossViewport = ref<Viewport | null>(null)

// Create VTK objects with 'any' type to bypass TypeScript issues
const centerlinePolyData = ref<any>(vtkPolyData.newInstance())
const widget = vtkResliceCursorWidget.newInstance({
  planes: [stretchPlane, crossPlane],
  behavior: widgetBehavior,
})
const widgetState = widget.getWidgetState()

// Configure widget state
widgetState.getStatesWithLabel('sphere').forEach((handle: any) => handle.setScale1(20))
widgetState.getCenterHandle().setVisible(false)
widgetState
  .getStatesWithLabel(`rotationIn${stretchPlane}`)
  .forEach((handle: any) => handle.setVisible(false))

// Widget managers
const stretchWidgetManager = ref<any>(vtkWidgetManager.newInstance())
const crossWidgetManager = ref<any>(vtkWidgetManager.newInstance())
let stretchWidgetInstance: any = null
let crossWidgetInstance: any = null

// Actors and mappers
const cprActor = vtkImageSlice.newInstance()
const cprMapper = vtkImageCPRMapper.newInstance()
cprActor.setMapper(cprMapper)
const reslice = vtkImageReslice.newInstance()
const resliceMapper = vtkImageMapper.newInstance()
const resliceActor = vtkImageSlice.newInstance()

// Add plane and cutter for centerline intersection
const cutPlane = vtkPlane.newInstance()
const centerlineCutter = vtkCutter.newInstance()
centerlineCutter.setCutFunction(cutPlane)
const cutMapper = vtkMapper.newInstance()
cutMapper.setInputConnection(centerlineCutter.getOutputPort())
const cutActor = vtkActor.newInstance()
cutActor.setMapper(cutMapper)
cutActor.getProperty().setLineWidth(2)

// Add TubeFilter
const tubeFilter = vtkTubeFilter.newInstance({
  numberOfSides: 12,
  capping: false,
})
tubeFilter.setVaryRadius(VaryRadius.VARY_RADIUS_BY_SCALAR)
tubeFilter.setRadiusFactor(1)

// Intersection points visualization
const intersectionPointsPolyData = ref<any>(vtkPolyData.newInstance())
const intersectionMapper = vtkMapper.newInstance()
const intersectionActor = vtkActor.newInstance()

// Manipulators
const cprManipulator = vtkCPRManipulator.newInstance({
  cprActor,
})
const planeManipulator = vtkPlaneManipulator.newInstance()

function setupCenterline() {
  if (!props.centerline || !props.imageData) return

  const centerline = centerlinePolyData.value

  // Create points from position data
  const centerlinePoints = Float32Array.from(props.centerline.position.flat())
  const nPoints = centerlinePoints.length / 3
  centerline.getPoints().setData(centerlinePoints, 3)

  // Set polylines of the centerline
  const centerlineLines = new Uint16Array(1 + nPoints)
  centerlineLines[0] = nPoints
  for (let i = 0; i < nPoints; ++i) {
    centerlineLines[i + 1] = i
  }
  centerline.getLines().setData(centerlineLines)

  // Create orientation tensor array
  centerline.getPointData().setTensors(
    vtkDataArray.newInstance({
      name: 'Orientation',
      numberOfComponents: 16,
      values: Float32Array.from(props.centerline.orientation.flat(Infinity)),
    }),
  )
  centerline.modified()

  // Configure TubeFilter
  tubeFilter.setInputData(centerline)
  tubeFilter.setInputArrayToProcess(0, 'Radius', 'PointData', 'Scalars')

  // Connect TubeFilter output to Cutter input
  centerlineCutter.setInputConnection(tubeFilter.getOutputPort())

  return centerline
}

// Core update function for view synchronization
function updateDistanceAndDirection() {
  if (!stretchViewport.value || !crossViewport.value) return

  // Get planes from widget state
  const widgetPlanes = widgetState.getPlanes()
  const worldBitangent = widgetPlanes[stretchViewType].normal
  const worldNormal = widgetPlanes[stretchViewType].viewUp
  widgetPlanes[crossViewType].normal = worldNormal
  widgetPlanes[crossViewType].viewUp = worldBitangent

  // Calculate tangent
  const worldTangent = vec3.cross([], worldBitangent, worldNormal)
  vec3.normalize(worldTangent, worldTangent)
  const worldWidgetCenter = widgetState.getCenter()
  const distance = cprManipulator.getCurrentDistance()

  // Get orientation from CPR mapper
  const { orientation } = cprMapper.getCenterlinePositionAndOrientation(distance)

  const modelDirections = mat3.fromQuat([], orientation)
  const inverseModelDirections = mat3.invert([], modelDirections)
  const worldDirections = mat3.fromValues(...worldTangent, ...worldBitangent, ...worldNormal)

  const baseDirections = mat3.mul([], inverseModelDirections, worldDirections)
  cprMapper.setDirectionMatrix(baseDirections)

  // Cross renderer update
  widget.updateReslicePlane(reslice, crossViewType)
  resliceActor.setUserMatrix(reslice.getResliceAxes())
  widget.updateCameraPoints(crossViewport.value.renderer, crossViewType, false, false)

  const crossCamera = crossViewport.value.renderer.getActiveCamera()
  crossCamera.setViewUp(modelDirections[3], modelDirections[4], modelDirections[5])

  // Update plane manipulator - use vec3 values directly
  planeManipulator.setUserOrigin(worldWidgetCenter)
  planeManipulator.setUserNormal(worldNormal)

  // Update cut plane for centerline intersection
  cutPlane.setOrigin(worldWidgetCenter[0], worldWidgetCenter[1], worldWidgetCenter[2])
  cutPlane.setNormal(worldNormal[0], worldNormal[1], worldNormal[2])
  const cutOutput = centerlineCutter.getOutputData()

  // Update intersection points visualization
  const points = cutOutput.getPoints()
  if (points && points.getNumberOfPoints() > 0) {
    intersectionPointsPolyData.value.setPoints(points)
    const numPoints = points.getNumberOfPoints()
    // Create a vertex cell array for the points
    const vertsData = new Uint16Array(numPoints + 1)
    vertsData[0] = numPoints // Number of points in the cell
    for (let i = 0; i < numPoints; i++) {
      vertsData[i + 1] = i // Point index
    }
    const cellArray = vtkCellArray.newInstance({ values: vertsData })
    intersectionPointsPolyData.value.setVerts(cellArray) // Set the vertices cell array
    intersectionPointsPolyData.value.modified() // Notify that the polydata has changed
    intersectionActor.setVisibility(true) // Ensure actor is visible
  } else {
    // If no points, clear the polydata and hide the actor
    intersectionPointsPolyData.value.getPoints()?.setData([]) // Clear points data
    intersectionPointsPolyData.value.getVerts()?.setData([]) // Clear verts data
    intersectionPointsPolyData.value.modified()
    intersectionActor.setVisibility(false) // Hide actor
    console.log('No intersection points found.')
  }

  updateState(widgetState, widget.getScaleInPixels(), widget.getRotationHandlePosition())

  // Get dimensions for transforms
  const width = cprMapper.getWidth()
  const height = cprMapper.getHeight()

  // Calculate CPR actor transform matrix
  const worldActorTranslation = vec3.scaleAndAdd([], worldWidgetCenter, worldTangent, -0.5 * width)

  vec3.scaleAndAdd(worldActorTranslation, worldActorTranslation, worldNormal, distance - height)
  const worldActorTransform = mat4.fromValues(
    ...worldTangent,
    0,
    ...worldNormal,
    0,
    ...vec3.scale([], worldBitangent, -1),
    0,
    ...worldActorTranslation,
    1,
  )
  cprActor.setUserMatrix(worldActorTransform)

  // CPR camera reset
  const stretchCamera = stretchViewport.value.renderer.getActiveCamera()
  const cameraDistance =
    (0.5 * height) / Math.tan(radiansFromDegrees(0.5 * stretchCamera.getViewAngle()))
  stretchCamera.setParallelScale(0.5 * height)
  stretchCamera.setParallelProjection(true)
  const cameraFocalPoint = vec3.scaleAndAdd(
    [],
    worldWidgetCenter,
    worldNormal,
    distance - 0.5 * height,
  )
  const cameraPosition = vec3.scaleAndAdd([], cameraFocalPoint, worldBitangent, -cameraDistance)
  stretchCamera.setPosition(...cameraPosition)
  stretchCamera.setFocalPoint(...cameraFocalPoint)
  stretchCamera.setViewUp(...worldNormal)
  stretchViewport.value.renderer.resetCameraClippingRange()

  // Render the window
  props.vtkInstance.interactor.render()
  props.vtkInstance.renderWindow.render()
}

// Initialize viewer
function initializeViewer() {
  if (!props.vtkInstance || !props.imageData || !props.viewports || props.viewports.length < 2) {
    console.error('Missing required props for CPR viewer')
    return
  }
  props.vtkInstance.interactor.setInteractorStyle(props.vtkInstance.imageInteractorStyle)
  props.vtkInstance.interactor.setDesiredUpdateRate(15.0)

  // Assign viewport references
  stretchViewport.value = props.viewports[0] // Main CPR view
  crossViewport.value = props.viewports[1] // Cross-section view

  props.vtkInstance.renderWindow.setNumberOfLayers(2)
  crossViewport.value.renderer.setLayer(1)

  // Set image to widget
  widget.setImage(props.imageData)
  const imageDimensions = props.imageData.getDimensions()
  const imageSpacing = props.imageData.getSpacing()
  const diagonal = vec3.mul([], imageDimensions, imageSpacing)
  cprMapper.setWidth(2 * vec3.len(diagonal))

  cprActor.setUserMatrix(widget.getResliceAxes(stretchViewType))
  stretchViewport.value.renderer.addVolume(cprActor)
  widget.updateCameraPoints(stretchViewport.value.renderer, stretchViewType, true, true)

  reslice.setInputData(props.imageData)
  crossViewport.value.renderer.addActor(resliceActor)
  widget.updateReslicePlane(reslice, crossViewType)
  resliceActor.setUserMatrix(reslice.getResliceAxes())
  widget.updateCameraPoints(crossViewport.value.renderer, crossViewType, true, true)

  const widgetPlanes = widgetState.getPlanes()
  widgetState.setPlanes(widgetPlanes)

  // Configure stretch view (main CPR view)
  stretchWidgetManager.value.setRenderer(stretchViewport.value.renderer)
  stretchWidgetInstance = stretchWidgetManager.value.addWidget(widget, stretchViewType)

  // Configure cross view
  crossWidgetManager.value.setRenderer(crossViewport.value.renderer)
  crossWidgetInstance = crossWidgetManager.value.addWidget(widget, crossViewType)

  // Setup centerline
  const centerlineData = setupCenterline()

  // Configure CPR mapper
  cprMapper.setInputData(props.imageData, 0)
  cprMapper.setInputData(centerlineData, 1)
  cprMapper.setWidth(400)

  // Apply window/level
  const cprProperty = cprActor.getProperty()
  cprProperty.setColorLevel(props.windowCenter)
  cprProperty.setColorWindow(props.windowWidth)

  // Configure reslice for cross view
  reslice.setInputData(props.imageData)
  reslice.setTransformInputSampling(false)
  reslice.setAutoCropOutput(true)
  reslice.setOutputDimensionality(2)
  resliceMapper.setInputConnection(reslice.getOutputPort())
  resliceActor.setMapper(resliceMapper)

  // Apply window/level to cross view
  const resliceProperty = resliceActor.getProperty()
  resliceProperty.setColorLevel(props.windowCenter)
  resliceProperty.setColorWindow(props.windowWidth)

  // Add actors to renderers
  stretchViewport.value.renderer.addActor(cprActor)
  crossViewport.value.renderer.addActor(resliceActor)

  const midPointDistance = cprMapper.getHeight() / 2
  const { worldCoords } = cprManipulator.distanceEvent(midPointDistance)
  widgetState.setCenter(worldCoords)
  updateDistanceAndDirection()

  widgetState[`getAxis${crossPlane}in${stretchPlane}`]().setManipulator(cprManipulator)
  widgetState[`getAxis${stretchPlane}in${crossPlane}`]().setManipulator(planeManipulator)
  widget.setManipulator(cprManipulator)

  props.vtkInstance.renderWindow.render()

  stretchWidgetInstance.onInteractionEvent(updateDistanceAndDirection)
  crossWidgetInstance.onInteractionEvent(updateDistanceAndDirection)

  // Set initial projection mode
  cprMapper.setProjectionMode(ProjectionMode[projectionMode.value])

  // Set initial thickness
  const thicknessValue = vec3.len(diagonal) * thickness.value
  cprMapper.setProjectionSlabThickness(thicknessValue)

  // Set initial display mode
  if (displayMode.value === 'stretched') {
    cprMapper.useStretchedMode()
  } else {
    cprMapper.useStraightenedMode()
  }

  // Add centerline intersection actor to cross view
  crossViewport.value.renderer.addActor(cutActor)

  // Configure and add intersection points actor
  intersectionMapper.setInputData(intersectionPointsPolyData.value)
  intersectionActor.setMapper(intersectionMapper)
  intersectionActor.getProperty().setPointSize(3) // Set point size
  intersectionActor.getProperty().setColor(1, 0, 0) // Set color (e.g., red)
  intersectionActor.setVisibility(false) // Initially hidden until points are available
  crossViewport.value.renderer.addActor(intersectionActor)
}

// Initialize on mount
onMounted(() => {
  initializeViewer()
})

// Watch handlers for UI controls
watch(
  () => projectionMode.value,
  (newMode) => {
    if (cprMapper) {
      cprMapper.setProjectionMode(ProjectionMode[newMode])
      props.vtkInstance.renderWindow.render()
    }
  },
)

watch(
  () => thicknessValue.value,
  (newThickness) => {
    if (cprMapper && props.imageData) {
      const spacing = props.imageData.getSpacing()
      const dimensions = props.imageData.getDimensions()
      const diagonal = vec3.mul([], spacing, dimensions)
      const thickness = vec3.len(diagonal) * newThickness
      cprMapper.setProjectionSlabThickness(thickness)
      props.vtkInstance.renderWindow.render()
    }
  },
)

watch(
  () => displayMode.value,
  (newMode) => {
    if (cprMapper) {
      if (newMode === 'stretched') {
        cprMapper.useStretchedMode()
      } else {
        cprMapper.useStraightenedMode()
      }
      updateDistanceAndDirection()
    }
  },
)

watch(
  () => [props.windowWidth, props.windowCenter],
  ([newWidth, newCenter]) => {
    if (cprActor && resliceActor) {
      const cprProperty = cprActor.getProperty()
      cprProperty.setColorLevel(newCenter)
      cprProperty.setColorWindow(newWidth)

      const resliceProperty = resliceActor.getProperty()
      resliceProperty.setColorLevel(newCenter)
      resliceProperty.setColorWindow(newWidth)

      props.vtkInstance.renderWindow.render()
    }
  },
)

// Cleanup
onBeforeUnmount(() => {
  if (stretchWidgetManager.value) {
    stretchWidgetManager.value.delete()
  }

  if (crossWidgetManager.value) {
    crossWidgetManager.value.delete()
  }

  if (stretchWidgetInstance) {
    stretchWidgetInstance.delete()
  }

  if (crossWidgetInstance) {
    crossWidgetInstance.delete()
  }

  if (widget) {
    widget.delete()
  }

  if (cprActor) {
    cprActor.delete()
  }

  if (cprMapper) {
    cprMapper.delete()
  }

  if (resliceActor) {
    resliceActor.delete()
  }

  if (resliceMapper) {
    resliceMapper.delete()
  }

  if (reslice) {
    reslice.delete()
  }

  // Delete centerline polydata
  if (centerlinePolyData.value) {
    centerlinePolyData.value.delete()
  }

  // Delete manipulators
  if (cprManipulator) {
    cprManipulator.delete()
  }

  if (planeManipulator) {
    planeManipulator.delete()
  }

  // Clean up additional objects
  if (cutActor) {
    cutActor.delete()
  }

  if (cutMapper) {
    cutMapper.delete()
  }

  if (centerlineCutter) {
    centerlineCutter.delete()
  }

  if (cutPlane) {
    cutPlane.delete()
  }

  // Delete TubeFilter
  if (tubeFilter) {
    tubeFilter.delete()
  }

  // Delete intersection points visualization objects
  if (intersectionActor) {
    intersectionActor.delete()
  }
  if (intersectionMapper) {
    intersectionMapper.delete()
  }
  if (intersectionPointsPolyData.value) {
    intersectionPointsPolyData.value.delete()
  }

  // Clear references to avoid memory leaks
  centerlinePolyData.value = null
  stretchWidgetManager.value = null
  crossWidgetManager.value = null
  stretchWidgetInstance = null
  crossWidgetInstance = null
  stretchViewport.value = null
  crossViewport.value = null
  // Clear intersection points refs
  intersectionPointsPolyData.value = null
})
</script>

<style scoped>
.cpr-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  pointer-events: none !important;
}

.cpr-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1001;
  display: flex;
  gap: 10px;
  flex-direction: column;
  pointer-events: auto;
  background-color: rgba(0, 0, 0, 0.6);
  padding: 15px;
  border-radius: 8px;
}

.control-group {
  display: flex;
  flex-direction: column;
  margin-bottom: 10px;
}

.control-group label {
  color: white;
  margin-bottom: 5px;
  font-size: 12px;
}

.control-select,
.control-range {
  width: 100%;
  padding: 5px;
  border-radius: 4px;
  border: 1px solid #555;
  background-color: #333;
  color: white;
}

.action-button {
  padding: 8px 16px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.action-button:hover {
  background-color: #45a049;
}

.close-button {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: rgba(255, 0, 0, 0.7);
  color: white;
  border: none;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
  align-self: flex-end;
}

.close-button:hover {
  background-color: rgba(255, 0, 0, 0.9);
}
</style>
