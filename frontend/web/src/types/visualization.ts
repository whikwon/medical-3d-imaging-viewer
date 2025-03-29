import vtkImageData from '@kitware/vtk.js/Common/DataModel/ImageData'
import vtkInteractorStyleImage from '@kitware/vtk.js/Interaction/Style/InteractorStyleImage'
import vtkInteractorStyleTrackballCamera from '@kitware/vtk.js/Interaction/Style/InteractorStyleTrackballCamera'
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor'
import vtkImageSlice from '@kitware/vtk.js/Rendering/Core/ImageSlice'
import vtkRenderer from '@kitware/vtk.js/Rendering/Core/Renderer'
import vtkRenderWindow from '@kitware/vtk.js/Rendering/Core/RenderWindow'
import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor'

/**
 * Basic interface for VTK objects
 */
export type VtkObject =
  | vtkImageData
  | vtkRenderer
  | vtkRenderWindow
  | vtkRenderWindowInteractor
  | vtkImageSlice
  | vtkActor

/**
 * Interface for a viewport with its renderer and container
 */
export interface Viewport {
  renderer: vtkRenderer
  container: HTMLElement
  viewport: [number, number, number, number] // [x1, y1, x2, y2]
}

/**
 * Represents the data and state for a single loaded label (e.g., centerline, fiducials).
 * The actual VTK actor is generated and managed by the viewer component based on this data.
 */
export interface Label {
  id: string
  filename: string
  seriesId: string
  type: 'centerline' | 'fiducial' | 'segmentation' | 'unknown'
  data: unknown
  visible: boolean
  color?: [number, number, number]
  opacity?: number
  lineWidth?: number
  pointSize?: number
  tubeRadius?: number
  vtkActor?: vtkActor | null
}

/**
 * Interface for visualization objects used in the VTK canvas, now including labels.
 */
export interface Visualization {
  type: 'volume' | 'multiframe'
  seriesId: string
  description: string
  actors: vtkImageSlice[]
  visible: boolean
  data: vtkImageData
  viewport?: Viewport
  labels?: Label[]
}

export interface VTKViewerInstance {
  renderWindow: vtkRenderWindow
  interactor: vtkRenderWindowInteractor
  rootContainer: HTMLElement
  imageInteractorStyle: vtkInteractorStyleImage
  trackballInteractorStyle: vtkInteractorStyleTrackballCamera
}
