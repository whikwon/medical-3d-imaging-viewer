/**
 * Basic interface for VTK objects
 */
export type VtkObject = any

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
