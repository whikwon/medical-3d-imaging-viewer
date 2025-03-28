import type { VtkObject } from '@/types/visualization'
import vtkOrientationMarkerWidget from '@kitware/vtk.js/Interaction/Widgets/OrientationMarkerWidget'
import vtkAnnotatedCubeActor from '@kitware/vtk.js/Rendering/Core/AnnotatedCubeActor'
import vtkAxesActor from '@kitware/vtk.js/Rendering/Core/AxesActor'
import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor'
import vtkFullScreenRenderWindow from '@kitware/vtk.js/Rendering/Misc/FullScreenRenderWindow'

export interface VTKViewerInstance {
  renderWindow: {
    render: () => void
    delete: () => void
    getViews: () => any[]
  }
  renderer: {
    addActor: (actor: VtkObject) => void
    removeActor: (actor: VtkObject) => void
    resetCamera: () => void
    getActiveCamera: () => any
  }
  fullScreenRenderer: VtkObject
  interactor: {
    setView: (view: any) => void
    initialize: () => void
    bindEvents: (container: HTMLElement) => void
  }
}

interface AxesConfig {
  recenter: boolean
  tipLength: number
  tipRadius: number
  shaftRadius: number
}

/**
 * Initializes the VTK viewer with standard configuration
 * @param container - DOM element to render the VTK viewer in
 * @returns Object containing all necessary VTK objects for rendering
 */
export function initializeViewer(container: HTMLElement): VTKViewerInstance {
  // Create fullscreen renderer
  const fullScreenRenderer = vtkFullScreenRenderWindow.newInstance({
    container: container,
    background: [0.1, 0.1, 0.1],
  })

  // Get render window and renderer
  const renderWindow = fullScreenRenderer.getRenderWindow()
  const renderer = fullScreenRenderer.getRenderer()

  // Set camera to parallel projection
  // const camera = renderer.getActiveCamera()
  // camera.setParallelProjection(true)

  // Create interactor for mouse/touch events
  const interactor = vtkRenderWindowInteractor.newInstance()
  interactor.setView(renderWindow.getViews()[0])
  interactor.initialize()
  interactor.bindEvents(container)

  // Create axes and orientation widget
  setupOrientationWidget(interactor)
  setupAxesActor(renderer)

  // Return all the created objects
  return {
    renderWindow,
    renderer,
    fullScreenRenderer,
    interactor,
  }
}

/**
 * Sets up the axes actor
 * @param renderer - VTK renderer to render the axes in
 */
function setupAxesActor(renderer: VtkObject): void {
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
 * @param renderer - VTK renderer to render the widget in
 */
function setupOrientationWidget(interactor: VtkObject): void {
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
  orientationWidget.setViewportCorner(vtkOrientationMarkerWidget.Corners.BOTTOM_LEFT)
  orientationWidget.setViewportSize(0.1)
  orientationWidget.setMinPixelSize(100)
  orientationWidget.setMaxPixelSize(300)
}

/**
 * Cleans up VTK resources when no longer needed
 * @param instance - The VTK viewer instance to clean up
 */
export function cleanupViewer(instance: VTKViewerInstance): void {
  if (instance.renderWindow) {
    instance.renderWindow.delete()
  }
}
