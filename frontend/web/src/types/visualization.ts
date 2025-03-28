import vtkImageData from '@kitware/vtk.js/Common/DataModel/ImageData'
import vtkInteractorStyleImage from '@kitware/vtk.js/Interaction/Style/InteractorStyleImage'
import vtkInteractorStyleTrackballCamera from '@kitware/vtk.js/Interaction/Style/InteractorStyleTrackballCamera'
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

/**
 * Interface for a viewport with its renderer and container
 */
export interface Viewport {
  renderer: vtkRenderer
  container: HTMLElement
  viewport: [number, number, number, number] // [x1, y1, x2, y2]
}

/**
 * Interface for visualization objects used in the VTK canvas
 */
export interface Visualization {
  type: 'volume' | 'multiframe'
  seriesId: string
  description: string
  actors: vtkImageSlice[]
  visible: boolean
  data: vtkImageData
  viewport?: Viewport
}

export interface VTKViewerInstance {
  renderWindow: vtkRenderWindow
  interactor: vtkRenderWindowInteractor
  rootContainer: HTMLElement
  imageStyle: vtkInteractorStyleImage
  trackballStyle: vtkInteractorStyleTrackballCamera
}
