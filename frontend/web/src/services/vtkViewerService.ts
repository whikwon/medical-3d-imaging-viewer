import '@kitware/vtk.js/Rendering/Misc/RenderingAPIs'

import type { Viewport, VTKViewerInstance } from '@/types/visualization'
import vtkInteractorStyleImage from '@kitware/vtk.js/Interaction/Style/InteractorStyleImage'
import vtkInteractorStyleTrackballCamera from '@kitware/vtk.js/Interaction/Style/InteractorStyleTrackballCamera'
import vtkOrientationMarkerWidget from '@kitware/vtk.js/Interaction/Widgets/OrientationMarkerWidget'
import vtkAnnotatedCubeActor from '@kitware/vtk.js/Rendering/Core/AnnotatedCubeActor'
import vtkAxesActor from '@kitware/vtk.js/Rendering/Core/AxesActor'
import vtkRenderWindow from '@kitware/vtk.js/Rendering/Core/RenderWindow'
import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor'
import vtkRenderer from '@kitware/vtk.js/Rendering/Core/Renderer'
import type { Ref } from 'vue'

interface AxesConfig {
  recenter: boolean
  tipLength: number
  tipRadius: number
  shaftRadius: number
}

/**
 * Initializes the VTK viewer with standard configuration
 * @param rootContainer - DOM element to render the VTK viewer in
 * @returns Object containing all necessary VTK objects for rendering
 */
export function initializeViewer(rootContainer: HTMLElement): VTKViewerInstance {
  // https://kitware.github.io/vtk-js/examples/QuadView.html
  const renderWindow = vtkRenderWindow.newInstance()
  const renderWindowView = renderWindow.newAPISpecificView()
  const rect = rootContainer.getBoundingClientRect()
  renderWindowView.setSize(rect.width, rect.height)
  renderWindow.addView(renderWindowView)
  renderWindowView.setContainer(rootContainer)

  // Create interactor for mouse/touch events
  const interactor = vtkRenderWindowInteractor.newInstance()
  interactor.setView(renderWindowView)
  interactor.initialize()

  // Create interactor styles
  const imageStyle = vtkInteractorStyleImage.newInstance()
  const trackballStyle = vtkInteractorStyleTrackballCamera.newInstance()
  interactor.setInteractorStyle(trackballStyle)

  // Return all the created objects
  return {
    renderWindow,
    interactor,
    rootContainer,
    imageStyle,
    trackballStyle,
  }
}

/**
 * Creates a new viewport with its renderer and container
 * @param renderWindow - The VTK render window
 * @param rootContainer - The root container element
 * @param viewport - The viewport coordinates [x1, y1, x2, y2]
 * @returns Object containing the new viewport's renderer and container
 */
export function createViewport(
  renderWindow: vtkRenderWindow,
  rootContainer: HTMLElement,
  viewport: [number, number, number, number],
  interactor: vtkRenderWindowInteractor,
  interactorStyle: vtkInteractorStyleImage | vtkInteractorStyleTrackballCamera,
): Viewport {
  // Create renderer
  const renderer = vtkRenderer.newInstance({})
  renderer.setBackground(0.1, 0.1, 0.1)
  renderer.setViewport(viewport)

  // Create container
  const container = document.createElement('div')
  container.style.position = 'absolute'
  container.style.width = `${(viewport[2] - viewport[0]) * 100}%`
  container.style.height = `${(viewport[3] - viewport[1]) * 100}%`
  container.style.left = `${viewport[0] * 100}%`
  container.style.bottom = `${viewport[1] * 100}%`
  container.style.border = '1px solid #ccc'
  rootContainer.appendChild(container)
  renderWindow.addRenderer(renderer)

  container.addEventListener('pointerenter', () => {
    if (interactor.getContainer() !== container) {
      if (interactor.getContainer()) {
        interactor.unbindEvents()
      }
      interactor.setInteractorStyle(interactorStyle)
      interactor.bindEvents(container)
    }
  })

  return { renderer, container, viewport }
}

/**
 * Sets up the axes actor
 * @param renderer - VTK renderer to render the axes in
 */
export function setupAxesActor(renderer: vtkRenderer): void {
  const axesActor = vtkAxesActor.newInstance()
  const config = axesActor.getConfig() as AxesConfig
  config.recenter = false
  axesActor.setConfig(config)
  axesActor.setScale(40, 40, 40)
  axesActor.setXAxisColor([255, 0, 0])
  axesActor.setYAxisColor([0, 255, 0])
  axesActor.setZAxisColor([0, 0, 255])
  axesActor.update()
  renderer.addActor(axesActor)
}

/**
 * Sets up the orientation widget (cube with axis labels)
 * @param interactor - VTK interactor to attach the widget to
 */
export function setupOrientationWidget(interactor: vtkRenderWindowInteractor): void {
  // Create the axes actor
  const axes = vtkAnnotatedCubeActor.newInstance()

  // Configure the default style
  axes.setDefaultStyle({
    text: '+X',
    fontStyle: 'bold',
    fontFamily: 'Arial',
    fontColor: 'black',
    fontSizeScale: (res) => res / 2,
    faceColor: '#0000ff',
    faceRotation: 0,
    edgeThickness: 0.1,
    edgeColor: 'black',
    resolution: 400,
  })

  // Configure individual faces
  axes.setXMinusFaceProperty({
    text: '-X',
    faceColor: '#ffff00',
    faceRotation: 90,
    fontStyle: 'italic',
  })

  axes.setYPlusFaceProperty({
    text: '+Y',
    faceColor: '#00ff00',
    fontSizeScale: (res) => res / 4,
  })

  axes.setYMinusFaceProperty({
    text: '-Y',
    faceColor: '#00ffff',
    fontColor: 'white',
  })

  axes.setZPlusFaceProperty({
    text: '+Z',
    edgeColor: 'yellow',
  })

  axes.setZMinusFaceProperty({
    text: '-Z',
    faceRotation: 45,
    edgeThickness: 0,
  })

  // Create the orientation widget
  const orientationWidget = vtkOrientationMarkerWidget.newInstance({
    actor: axes,
    interactor: interactor,
  })

  // Configure the widget
  orientationWidget.setEnabled(true)
  orientationWidget.setViewportCorner(vtkOrientationMarkerWidget.Corners.TOP_RIGHT)
  orientationWidget.setViewportSize(0.1)
  orientationWidget.setMinPixelSize(100)
  orientationWidget.setMaxPixelSize(300)
}

/**
 * Cleans up VTK resources when no longer needed
 * @param instance - The VTK viewer instance to clean up
 */
export function cleanupViewer(instance: VTKViewerInstance | Ref<VTKViewerInstance | null>): void {
  // Handle ref type
  const vtkInstance = 'value' in instance ? instance.value : instance

  if (vtkInstance && vtkInstance.renderWindow) {
    vtkInstance.renderWindow.delete()
  }
}
