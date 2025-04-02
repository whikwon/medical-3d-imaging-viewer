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
 * Interface for a single label associated with a visualization.
 */

export interface CoronaryArteryData {
  position: number[][]
  orientation: number[][] // Or a more specific type if needed
  radius: number[]
}

export interface Label {
  id: string
  filename: string
  seriesId: string
  type: 'coronaryArtery'
  data: CoronaryArteryData | unknown // Allow other types for other labels
  visible: boolean
  color?: [number, number, number]
  opacity?: number
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
  controlParams?: any // Added to store initial control parameters
}

export interface VTKViewerInstance {
  renderWindow: vtkRenderWindow
  interactor: vtkRenderWindowInteractor
  rootContainer: HTMLElement
  imageInteractorStyle: vtkInteractorStyleImage
  trackballInteractorStyle: vtkInteractorStyleTrackballCamera
}
