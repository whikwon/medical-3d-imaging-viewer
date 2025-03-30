<!-- https://kitware.github.io/vtk-js/examples/ImageCPRMapper.html -->

<template>
  <div class="cpr-container">
    <div class="cpr-view-container">
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
  </div>
</template>

<script setup lang="ts">
import '@kitware/vtk.js/IO/Core/DataAccessHelper/HttpDataAccessHelper'
import '@kitware/vtk.js/Rendering/Profiles/All'

import type { VTKViewerInstance, Viewport } from '@/types/visualization'
import vtkDataArray from '@kitware/vtk.js/Common/Core/DataArray'
import { radiansFromDegrees } from '@kitware/vtk.js/Common/Core/Math'
import vtkPolyData from '@kitware/vtk.js/Common/DataModel/PolyData'
import vtkImageReslice from '@kitware/vtk.js/Imaging/Core/ImageReslice'
import vtkImageCPRMapper from '@kitware/vtk.js/Rendering/Core/ImageCPRMapper'
import { ProjectionMode } from '@kitware/vtk.js/Rendering/Core/ImageCPRMapper/Constants'
import vtkImageMapper from '@kitware/vtk.js/Rendering/Core/ImageMapper'
import vtkImageSlice from '@kitware/vtk.js/Rendering/Core/ImageSlice'
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

  // Clear references to avoid memory leaks
  centerlinePolyData.value = null
  stretchWidgetManager.value = null
  crossWidgetManager.value = null
  stretchWidgetInstance = null
  crossWidgetInstance = null
  stretchViewport.value = null
  crossViewport.value = null
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
  pointer-events: none;
}

.cpr-view-container {
  width: 100%;
  height: 100%;
  position: relative;
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
