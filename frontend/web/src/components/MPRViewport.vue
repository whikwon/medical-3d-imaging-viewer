<!-- https://kitware.github.io/vtk-js/examples/ResliceCursorWidget.html -->

<template>
  <div class="mpr-container">
    <div class="mpr-view-container">
      <div ref="axialView" class="axial-view"></div>
      <div ref="coronalView" class="coronal-view"></div>
      <div ref="sagittalView" class="sagittal-view"></div>
      <div ref="volumeView" class="volume-view"></div>
    </div>
    <div class="button-container">
      <button @click="resetView" class="action-button">Reset View</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import '@kitware/vtk.js/favicon'
import '@kitware/vtk.js/IO/Core/DataAccessHelper/HttpDataAccessHelper'
import '@kitware/vtk.js/Rendering/Profiles/All'

import vtkSphereSource from '@kitware/vtk.js/Filters/Sources/SphereSource'
import vtkImageReslice from '@kitware/vtk.js/Imaging/Core/ImageReslice'
import { SlabMode } from '@kitware/vtk.js/Imaging/Core/ImageReslice/Constants'
import vtkInteractorStyleImage from '@kitware/vtk.js/Interaction/Style/InteractorStyleImage'
import vtkInteractorStyleTrackballCamera from '@kitware/vtk.js/Interaction/Style/InteractorStyleTrackballCamera'
import vtkOrientationMarkerWidget from '@kitware/vtk.js/Interaction/Widgets/OrientationMarkerWidget'
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor'
import vtkAnnotatedCubeActor from '@kitware/vtk.js/Rendering/Core/AnnotatedCubeActor'
import vtkImageMapper from '@kitware/vtk.js/Rendering/Core/ImageMapper'
import vtkImageSlice from '@kitware/vtk.js/Rendering/Core/ImageSlice'
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper'
import vtkRenderer from '@kitware/vtk.js/Rendering/Core/Renderer'
import vtkRenderWindow from '@kitware/vtk.js/Rendering/Core/RenderWindow'
import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor'
import vtkGenericRenderWindow from '@kitware/vtk.js/Rendering/Misc/GenericRenderWindow'
import vtkWidgetManager from '@kitware/vtk.js/Widgets/Core/WidgetManager'
import { CaptureOn } from '@kitware/vtk.js/Widgets/Core/WidgetManager/Constants'
import vtkResliceCursorWidget from '@kitware/vtk.js/Widgets/Widgets3D/ResliceCursorWidget'
import {
  InteractionMethodsName,
  xyzToViewType,
} from '@kitware/vtk.js/Widgets/Widgets3D/ResliceCursorWidget/Constants'

import type { VtkObject } from '@/types/visualization'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

function createRGBStringFromRGBValues(rgb) {
  if (rgb.length !== 3) {
    return 'rgb(0, 0, 0)'
  }
  return `rgb(${(rgb[0] * 255).toString()}, ${(rgb[1] * 255).toString()}, ${(
    rgb[2] * 255
  ).toString()})`
}

interface ViewObject {
  renderWindow: vtkRenderWindow
  renderer: vtkRenderer
  GLWindow: any // This is a WebGL context, which is browser-specific
  interactor: vtkRenderWindowInteractor
  widgetManager: vtkWidgetManager
  orientationWidget: vtkOrientationMarkerWidget
  widgetInstance: any // VTK.js widget instance
  reslice: vtkImageReslice
  resliceMapper: vtkImageMapper
  resliceActor: vtkImageSlice
  sphereActors: vtkActor[]
  sphereSources: vtkSphereSource[]
}

const viewColors = [
  [1, 0, 0], // sagittal
  [0, 1, 0], // coronal
  [0, 0, 1], // axial
  [0.5, 0.5, 0.5], // 3D
]

interface InteractionContext {
  viewType: string // Using string for now as VTK.js types are not fully exposed
  reslice: vtkImageReslice
  actor: vtkImageSlice
  renderer: vtkRenderer
  resetFocalPoint: boolean
  computeFocalPointOffset: boolean
  sphereSources: vtkSphereSource[]
  resetViewUp: boolean
}

const props = defineProps<{
  imageData: VtkObject
  windowWidth: number
  windowCenter: number
}>()

// Refs for view containers
const axialView = ref<HTMLElement | null>(null)
const coronalView = ref<HTMLElement | null>(null)
const sagittalView = ref<HTMLElement | null>(null)
const volumeView = ref<HTMLElement | null>(null)

// Control states
const keepOrthogonality = ref(true)
const slabMode = ref(SlabMode.MEAN)
const slabNumberOfSlices = ref(1)
const maxSlices = ref(100)

// Widget and state management
const widget = vtkResliceCursorWidget.newInstance()
const widgetState = widget.getWidgetState()
const initialPlanesState = { ...widgetState.getPlanes() }
const viewAttributes = ref<ViewObject[]>([])
let view3D: ViewObject | null = null

// Add watch for window level changes
watch(
  () => [props.windowWidth, props.windowCenter],
  ([newWidth, newCenter]) => {
    viewAttributes.value.forEach((obj) => {
      if (obj.resliceActor) {
        const property = obj.resliceActor.getProperty()
        property.setColorLevel(newCenter)
        property.setColorWindow(newWidth)
      }
    })
    if (view3D) {
      const property = view3D.resliceActor.getProperty()
      property.setColorLevel(newCenter)
      property.setColorWindow(newWidth)
    }
  },
  { immediate: true },
)

// Initialize VTK.js viewer
onMounted(() => {
  if (!axialView.value || !coronalView.value || !sagittalView.value || !volumeView.value) return

  // Create views
  const views = [
    { element: axialView.value, index: 0 },
    { element: coronalView.value, index: 1 },
    { element: sagittalView.value, index: 2 },
    { element: volumeView.value, index: 3 },
  ]

  views.forEach(({ element, index }) => {
    const grw = vtkGenericRenderWindow.newInstance()
    grw.setContainer(element)
    grw.resize()

    const obj: ViewObject = {
      renderWindow: grw.getRenderWindow(),
      renderer: grw.getRenderer(),
      GLWindow: grw.getApiSpecificRenderWindow(),
      interactor: grw.getInteractor(),
      widgetManager: vtkWidgetManager.newInstance(),
      orientationWidget: null,
      sphereActors: [],
      sphereSources: [],
    }

    obj.renderer.getActiveCamera().setParallelProjection(true)
    obj.renderer.setBackground(0.1, 0.1, 0.1)
    obj.renderWindow.addRenderer(obj.renderer)
    obj.renderWindow.addView(obj.GLWindow)
    obj.renderWindow.setInteractor(obj.interactor)
    obj.interactor.setView(obj.GLWindow)
    obj.interactor.initialize()
    obj.interactor.bindEvents(element)
    obj.widgetManager.setRenderer(obj.renderer)

    if (index < 3) {
      obj.interactor.setInteractorStyle(vtkInteractorStyleImage.newInstance())
      obj.widgetInstance = obj.widgetManager.addWidget(widget, xyzToViewType[index])
      obj.widgetInstance.setScaleInPixels(true)
      obj.widgetInstance.setHoleWidth(50)
      obj.widgetInstance.setInfiniteLine(false)
      widgetState.getStatesWithLabel('line').forEach((state: any) => state.setScale3(4, 4, 300))
      widgetState.getStatesWithLabel('center').forEach((state: any) => state.setOpacity(128))
      obj.widgetInstance.setKeepOrthogonality(keepOrthogonality.value)
      obj.widgetInstance.setCursorStyles({
        translateCenter: 'move',
        rotateLine: 'alias',
        translateAxis: 'pointer',
        default: 'default',
      })
      obj.widgetManager.enablePicking()
      obj.widgetManager.setCaptureOn(CaptureOn.MOUSE_MOVE)
    } else {
      obj.interactor.setInteractorStyle(vtkInteractorStyleTrackballCamera.newInstance())
    }

    obj.reslice = vtkImageReslice.newInstance()
    obj.reslice.setSlabMode(slabMode.value)
    obj.reslice.setSlabNumberOfSlices(slabNumberOfSlices.value)
    obj.reslice.setTransformInputSampling(false)
    obj.reslice.setAutoCropOutput(true)
    obj.reslice.setOutputDimensionality(2)
    obj.resliceMapper = vtkImageMapper.newInstance()
    obj.resliceMapper.setInputConnection(obj.reslice.getOutputPort())
    obj.resliceActor = vtkImageSlice.newInstance()
    obj.resliceActor.setMapper(obj.resliceMapper)

    // Apply window level settings
    const property = obj.resliceActor.getProperty()
    property.setColorLevel(props.windowCenter)
    property.setColorWindow(props.windowWidth)

    for (let j = 0; j < 3; j++) {
      const sphere = vtkSphereSource.newInstance()
      sphere.setRadius(10)
      const mapper = vtkMapper.newInstance()
      mapper.setInputConnection(sphere.getOutputPort())
      const actor = vtkActor.newInstance()
      actor.setMapper(mapper)
      actor.getProperty().setColor(...viewColors[index])
      actor.setVisibility(true)
      obj.sphereActors.push(actor)
      obj.sphereSources.push(sphere)
    }

    if (index < 3) {
      viewAttributes.value.push(obj)
    } else {
      view3D = obj
    }

    // Setup orientation widget
    const axes = vtkAnnotatedCubeActor.newInstance()
    axes.setDefaultStyle({
      text: '+X',
      fontStyle: 'bold',
      fontFamily: 'Arial',
      fontColor: 'black',
      fontSizeScale: (res) => res / 2,
      faceColor: createRGBStringFromRGBValues(viewColors[0]),
      faceRotation: 0,
      edgeThickness: 0.1,
      edgeColor: 'black',
      resolution: 400,
    })
    axes.setXMinusFaceProperty({
      text: '-X',
      faceColor: createRGBStringFromRGBValues(viewColors[0]),
      faceRotation: 90,
      fontStyle: 'italic',
    })
    axes.setYPlusFaceProperty({
      text: '+Y',
      faceColor: createRGBStringFromRGBValues(viewColors[1]),
      fontSizeScale: (res) => res / 4,
    })
    axes.setYMinusFaceProperty({
      text: '-Y',
      faceColor: createRGBStringFromRGBValues(viewColors[1]),
      fontColor: 'white',
    })
    axes.setZPlusFaceProperty({
      text: '+Z',
      faceColor: createRGBStringFromRGBValues(viewColors[2]),
    })
    axes.setZMinusFaceProperty({
      text: '-Z',
      faceColor: createRGBStringFromRGBValues(viewColors[2]),
      faceRotation: 45,
    })

    obj.orientationWidget = vtkOrientationMarkerWidget.newInstance({
      actor: axes,
      interactor: obj.renderWindow.getInteractor(),
    })
    obj.orientationWidget.setEnabled(true)
    obj.orientationWidget.setViewportCorner(vtkOrientationMarkerWidget.Corners.BOTTOM_RIGHT)
    obj.orientationWidget.setViewportSize(0.15)
    obj.orientationWidget.setMinPixelSize(100)
    obj.orientationWidget.setMaxPixelSize(300)
  })

  // Setup image data
  if (props.imageData) {
    widget.setImage(props.imageData)
    viewAttributes.value.forEach((obj, i) => {
      obj.reslice.setInputData(props.imageData)
      obj.renderer.addActor(obj.resliceActor)
      view3D.renderer.addActor(obj.resliceActor)
      obj.sphereActors.forEach((actor) => {
        obj.renderer.addActor(actor)
        view3D.renderer.addActor(actor)
      })

      const reslice = obj.reslice
      const viewType = xyzToViewType[i]

      viewAttributes.value.forEach((v) => {
        v.widgetInstance.onStartInteractionEvent(() => {
          updateReslice({
            viewType,
            reslice,
            actor: obj.resliceActor,
            renderer: obj.renderer,
            resetFocalPoint: false,
            computeFocalPointOffset: true,
            sphereSources: obj.sphereSources,
          })
        })

        v.widgetInstance.onInteractionEvent((interactionMethodName: string) => {
          const canUpdateFocalPoint = interactionMethodName === InteractionMethodsName.RotateLine
          const activeViewType = widgetState.getActiveViewType() as string
          const computeFocalPointOffset = activeViewType === viewType || !canUpdateFocalPoint
          updateReslice({
            viewType,
            reslice,
            actor: obj.resliceActor,
            renderer: obj.renderer,
            resetFocalPoint: false,
            computeFocalPointOffset,
            sphereSources: obj.sphereSources,
          })
        })
      })

      updateReslice({
        viewType,
        reslice,
        actor: obj.resliceActor,
        renderer: obj.renderer,
        resetFocalPoint: true,
        computeFocalPointOffset: true,
        sphereSources: obj.sphereSources,
      })
      obj.interactor.render()
    })

    view3D.renderer.resetCamera()
    view3D.renderer.resetCameraClippingRange()

    // Set max slices
    const dimensions = props.imageData.getDimensions()
    maxSlices.value = Math.max(...dimensions)
  }
})

// Cleanup
onBeforeUnmount(() => {
  viewAttributes.value.forEach((obj) => {
    obj.renderWindow.delete()
  })
  if (view3D) {
    view3D.renderWindow.delete()
  }
})

// Update reslice function
function updateReslice(interactionContext: InteractionContext) {
  const modified = widget.updateReslicePlane(
    interactionContext.reslice,
    interactionContext.viewType,
  )
  if (modified) {
    const resliceAxes = interactionContext.reslice.getResliceAxes()
    interactionContext.actor.setUserMatrix(resliceAxes)
    const planeSource = widget.getPlaneSource(interactionContext.viewType)
    interactionContext.sphereSources[0].setCenter(planeSource.getOrigin())
    interactionContext.sphereSources[1].setCenter(planeSource.getPoint1())
    interactionContext.sphereSources[2].setCenter(planeSource.getPoint2())
  }
  widget.updateCameraPoints(
    interactionContext.renderer,
    interactionContext.viewType,
    interactionContext.resetFocalPoint,
    interactionContext.computeFocalPointOffset,
  )
  view3D.renderWindow.render()
  return modified
}

// Reset view function
function resetView() {
  if (!props.imageData) return

  widgetState.setPlanes({ ...initialPlanesState })
  widget.setCenter(widgetState.getImage().getCenter())

  viewAttributes.value.forEach((obj, i) => {
    updateReslice({
      viewType: xyzToViewType[i],
      reslice: obj.reslice,
      actor: obj.resliceActor,
      renderer: obj.renderer,
      resetFocalPoint: true,
      computeFocalPointOffset: true,
      sphereSources: obj.sphereSources,
      resetViewUp: true,
    })
    obj.renderWindow.render()
  })

  view3D.renderer.resetCamera()
  view3D.renderer.resetCameraClippingRange()
}
</script>

<style scoped>
.mpr-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.mpr-view-container {
  width: 90%;
  height: 90%;
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 20px;
}

.axial-view,
.coronal-view,
.sagittal-view,
.volume-view {
  width: 100%;
  height: 100%;
  background-color: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.button-container {
  display: flex;
  gap: 10px;
  margin-top: 20px;
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
</style>
