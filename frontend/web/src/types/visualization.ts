import vtkImageData from '@kitware/vtk.js/Common/DataModel/ImageData'

/**
 * Basic interface for VTK objects
 */
export type VtkObject = vtkImageData | null

/**
 * Interface for visualization objects used in the VTK canvas
 */
export interface Visualization {
  type: 'volume' | 'multiframe'
  seriesId: string
  description: string
  actors: VtkObject[]
  visible: boolean
  data: VtkObject
}
