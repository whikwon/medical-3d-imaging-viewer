/**
 * Basic interface for VTK objects
 */
export interface VtkObject {
  // Common vtk.js methods used across our app
  getProperty?: () => {
    setColorLevel: (level: number) => void
    setColorWindow: (window: number) => void
  }
  getMapper?: () => {
    setSlice: (slice: number) => void
  }
  setVisibility?: (visible: boolean) => void
  setMapper?: (mapper: VtkObject) => void
  // Add any other methods you need
}

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
