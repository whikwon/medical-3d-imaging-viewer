<!-- https://kitware.github.io/vtk-js/examples/ResliceCursorWidget.html -->

<template>
  <div class="mpr-container">
    <div class="mpr-view-container">
      <div class="mpr-controls">
        <button @click="$emit('close')" class="close-button">×</button>
        <button @click="resetView" class="action-button">Reset View</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import '@kitware/vtk.js/favicon'
import '@kitware/vtk.js/IO/Core/DataAccessHelper/HttpDataAccessHelper'
import '@kitware/vtk.js/Rendering/Profiles/All'

import type { VTKViewerInstance, Viewport } from '@/types/visualization'
import vtkImageData from '@kitware/vtk.js/Common/DataModel/ImageData'
import vtkSphereSource from '@kitware/vtk.js/Filters/Sources/SphereSource'
import vtkImageReslice from '@kitware/vtk.js/Imaging/Core/ImageReslice'
import { SlabMode } from '@kitware/vtk.js/Imaging/Core/ImageReslice/Constants'
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor'
import vtkImageMapper from '@kitware/vtk.js/Rendering/Core/ImageMapper'
import vtkImageSlice from '@kitware/vtk.js/Rendering/Core/ImageSlice'
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper'
import vtkRenderer from '@kitware/vtk.js/Rendering/Core/Renderer'
import vtkRenderWindow from '@kitware/vtk.js/Rendering/Core/RenderWindow'
import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor'
import vtkWidgetManager from '@kitware/vtk.js/Widgets/Core/WidgetManager'
import { CaptureOn } from '@kitware/vtk.js/Widgets/Core/WidgetManager/Constants'
import vtkWidgetState from '@kitware/vtk.js/Widgets/Core/WidgetState'
import vtkResliceCursorWidget from '@kitware/vtk.js/Widgets/Widgets3D/ResliceCursorWidget'
import {
  InteractionMethodsName,
  xyzToViewType,
} from '@kitware/vtk.js/Widgets/Widgets3D/ResliceCursorWidget/Constants'

import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

function createRGBStringFromRGBValues(rgb: number[]) {
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
  GLWindow: HTMLElement
  interactor: vtkRenderWindowInteractor
  widgetManager: vtkWidgetManager
  widgetInstance: any // VTK.js widget instance, difficult to type precisely
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

// Define the types for viewType - it's a string enum
type ViewType = 'XPlane' | 'YPlane' | 'ZPlane' | '3D'

interface InteractionContext {
  viewType: ViewType
  reslice: vtkImageReslice
  actor: vtkImageSlice
  renderer: vtkRenderer
  resetFocalPoint: boolean
  computeFocalPointOffset: boolean
  sphereSources: vtkSphereSource[]
  resetViewUp?: boolean
}

const props = defineProps<{
  imageData: vtkImageData
  windowWidth: number
  windowCenter: number
  vtkInstance: VTKViewerInstance
  mprViewports: Viewport[]
}>()

// Control states
const keepOrthogonality = ref(true)
const slabMode = ref(SlabMode.MEAN)
const slabNumberOfSlices = ref(1)

// Widget and state management
const widget = vtkResliceCursorWidget.newInstance()
// Type the widget state with an interface that includes the methods we need
interface WidgetStateExtended extends vtkWidgetState {
  getPlanes(): any
  setPlanes(planes: any): void
  getActiveViewType(): ViewType
  getImage(): vtkImageData
  getStatesWithLabel(label: string): any[]
}
const widgetState = widget.getWidgetState() as WidgetStateExtended
const initialPlanesState = { ...widgetState.getPlanes() }
const viewAttributes = ref<ViewObject[]>([])
const view3D = ref<ViewObject | null>(null)

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
    if (view3D.value) {
      const property = view3D.value.resliceActor.getProperty()
      property.setColorLevel(newCenter)
      property.setColorWindow(newWidth)
    }
  },
  { immediate: true },
)

// Initialize VTK.js viewer - this now uses the parent's shared rendering context
onMounted(() => {
  console.log('onMounted MPRViewport')
  if (
    !props.vtkInstance ||
    !props.imageData ||
    !props.mprViewports ||
    props.mprViewports.length < 4
  )
    return

  // Setup image data
  widget.setImage(props.imageData)

  // Use the viewports directly provided from the parent component instead of trying to access by index
  // We expect 4 viewports in this order:
  // 0: Axial view (top left)
  // 1: Coronal view (top right)
  // 2: Sagittal view (bottom left)
  // 3: 3D view (bottom right)

  // Configure each view
  for (let i = 0; i < 4; i++) {
    const viewport = props.mprViewports[i]

    // Create a view object
    const obj: ViewObject = {
      renderWindow: props.vtkInstance.renderWindow,
      renderer: viewport.renderer,
      GLWindow: props.vtkInstance.rootContainer, // This is used differently now
      interactor: props.vtkInstance.interactor,
      widgetManager: vtkWidgetManager.newInstance(),
      widgetInstance: null, // Will set up later
      reslice: vtkImageReslice.newInstance(),
      resliceMapper: vtkImageMapper.newInstance(),
      resliceActor: vtkImageSlice.newInstance(),
      sphereActors: [],
      sphereSources: [],
    }

    obj.reslice.setSlabMode(slabMode.value)
    obj.reslice.setSlabNumberOfSlices(slabNumberOfSlices.value)
    obj.reslice.setTransformInputSampling(false)
    obj.reslice.setAutoCropOutput(true)
    obj.reslice.setOutputDimensionality(2)
    obj.resliceMapper.setInputConnection(obj.reslice.getOutputPort())
    obj.resliceActor.setMapper(obj.resliceMapper)

    // Apply initial window level settings from props
    const property = obj.resliceActor.getProperty()
    property.setColorLevel(props.windowCenter)
    property.setColorWindow(props.windowWidth)

    // Setup widget manager with the renderer
    obj.widgetManager.setRenderer(obj.renderer)

    // Create sphere actors
    for (let j = 0; j < 3; j++) {
      const sphere = vtkSphereSource.newInstance()
      sphere.setRadius(10)
      const mapper = vtkMapper.newInstance()
      mapper.setInputConnection(sphere.getOutputPort())
      const actor = vtkActor.newInstance()
      actor.setMapper(mapper)
      actor.getProperty().setColor(viewColors[i][0], viewColors[i][1], viewColors[i][2])
      actor.setVisibility(true)
      obj.sphereActors.push(actor)
      obj.sphereSources.push(sphere)
    }

    // Setup MPR views
    if (i < 3) {
      // Set up slice views (axial, coronal, sagittal)
      obj.widgetInstance = obj.widgetManager.addWidget(widget, xyzToViewType[i])
      obj.widgetInstance.setScaleInPixels(true)
      obj.widgetInstance.setHoleWidth(50)
      obj.widgetInstance.setInfiniteLine(false)

      // Configure widget state lines and center
      widgetState.getStatesWithLabel('line').forEach((state) => state.setScale3(4, 4, 300))
      widgetState.getStatesWithLabel('center').forEach((state) => state.setOpacity(128))

      obj.widgetInstance.setKeepOrthogonality(keepOrthogonality.value)
      obj.widgetInstance.setCursorStyles({
        translateCenter: 'move',
        rotateLine: 'alias',
        translateAxis: 'pointer',
        default: 'default',
      })

      obj.widgetManager.enablePicking()
      obj.widgetManager.setCaptureOn(CaptureOn.MOUSE_MOVE)

      viewAttributes.value.push(obj)
    } else {
      // Set up 3D view
      view3D.value = obj
    }
  }

  // Setup image data connections and interactions
  viewAttributes.value.forEach((obj, i) => {
    obj.reslice.setInputData(props.imageData)
    obj.renderer.addActor(obj.resliceActor)

    if (view3D.value) {
      view3D.value.renderer.addActor(obj.resliceActor)
    }

    obj.sphereActors.forEach((actor) => {
      obj.renderer.addActor(actor)
      if (view3D.value) {
        view3D.value.renderer.addActor(actor)
      }
    })

    const reslice = obj.reslice
    const viewType = xyzToViewType[i] as ViewType

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
        const activeViewType = widgetState.getActiveViewType()
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
  })

  if (view3D.value) {
    view3D.value.renderer.resetCamera()
    view3D.value.renderer.resetCameraClippingRange()
  }

  props.vtkInstance.renderWindow.render()
})

// Cleanup
onBeforeUnmount(() => {
  console.log('Cleaning up MPR viewport')
  // Remove all actors and widgets from the renderers
  viewAttributes.value.forEach((obj) => {
    if (obj.widgetInstance) {
      obj.widgetInstance.delete()
    }
    if (obj.widgetManager) {
      obj.widgetManager.delete()
    }
    if (obj.reslice) {
      obj.reslice.delete()
    }
    if (obj.resliceMapper) {
      obj.resliceMapper.delete()
    }
    if (obj.resliceActor) {
      obj.resliceActor.delete()
    }
    if (obj.renderer) {
      obj.renderer.delete()
    }

    // Clean up sphere actors and sources
    obj.sphereActors.forEach((actor) => actor.delete())
    obj.sphereSources.forEach((source) => source.delete())
    obj.sphereActors = []
    obj.sphereSources = []
  })

  if (view3D.value) {
    // Delete reslice objects in 3D view
    if (view3D.value.reslice) {
      view3D.value.reslice.delete()
    }
    if (view3D.value.resliceMapper) {
      view3D.value.resliceMapper.delete()
    }
    if (view3D.value.resliceActor) {
      view3D.value.resliceActor.delete()
    }
    if (view3D.value.renderer) {
      view3D.value.renderer.delete()
    }

    // Clean up sphere actors and sources
    if (view3D.value.sphereActors) {
      view3D.value.sphereActors.forEach((actor) => actor.delete())
    }
    if (view3D.value.sphereSources) {
      view3D.value.sphereSources.forEach((source) => source.delete())
    }
  }

  // Clean up the main widget
  if (widget) {
    widget.delete()
  }

  // Reset the refs
  viewAttributes.value = []
  view3D.value = null
})

// Update reslice function
function updateReslice(interactionContext: InteractionContext) {
  const modified = widget.updateReslicePlane(
    interactionContext.reslice,
    interactionContext.viewType as any, // Type assertion needed due to API constraints
  )

  if (modified) {
    const resliceAxes = interactionContext.reslice.getResliceAxes()
    interactionContext.actor.setUserMatrix(resliceAxes)
    const planeSource = widget.getPlaneSource(interactionContext.viewType as any) // Type assertion needed due to API constraints
    interactionContext.sphereSources[0].setCenter(planeSource.getOrigin())
    interactionContext.sphereSources[1].setCenter(planeSource.getPoint1())
    interactionContext.sphereSources[2].setCenter(planeSource.getPoint2())
  }

  widget.updateCameraPoints(
    interactionContext.renderer,
    interactionContext.viewType as any, // Type assertion needed due to API constraints
    interactionContext.resetFocalPoint,
    interactionContext.computeFocalPointOffset,
  )

  if (view3D.value) {
    view3D.value.renderWindow.render()
  }

  return modified
}

// Reset view function
function resetView() {
  if (!props.imageData) return

  widgetState.setPlanes({ ...initialPlanesState })
  widget.setCenter(widgetState.getImage().getCenter())

  viewAttributes.value.forEach((obj, i) => {
    updateReslice({
      viewType: xyzToViewType[i] as ViewType,
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

  if (view3D.value) {
    view3D.value.renderer.resetCamera()
    view3D.value.renderer.resetCameraClippingRange()
  }
}

defineEmits<{
  (e: 'close'): void
}>()
</script>

<style scoped>
.mpr-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  pointer-events: none;
}

.mpr-view-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.mpr-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1001;
  display: flex;
  gap: 10px;
  pointer-events: auto;
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
  background-color: rgba(0, 0, 0, 0.5);
  color: white;
  border: none;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.close-button:hover {
  background-color: rgba(0, 0, 0, 0.7);
}
</style>
