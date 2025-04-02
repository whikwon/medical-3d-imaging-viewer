import type { Label, Visualization } from '@/types/visualization'
import vtkCellArray from '@kitware/vtk.js/Common/Core/CellArray'
import vtkDataArray from '@kitware/vtk.js/Common/Core/DataArray'
import vtkPoints from '@kitware/vtk.js/Common/Core/Points'
import vtkPolyData from '@kitware/vtk.js/Common/DataModel/PolyData'
import vtkTubeFilter from '@kitware/vtk.js/Filters/General/TubeFilter'
import { VaryRadius } from '@kitware/vtk.js/Filters/General/TubeFilter/Constants'
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor'
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper'
import vtkRenderer from '@kitware/vtk.js/Rendering/Core/Renderer'

/**
 * Draws a coronary artery as a tube in the renderer.
 * @param renderer - The VTK renderer
 * @param label - The coronary artery label object
 * @returns The created VTK actor
 */
export function drawCoronaryArtery(renderer: vtkRenderer, label: Label): vtkActor {
  if (
    label.type !== 'coronaryArtery' ||
    !label.data ||
    typeof label.data !== 'object' ||
    !('position' in label.data) ||
    !('radius' in label.data)
  ) {
    throw new Error('Invalid label data for coronary artery: missing position or radius')
  }
  // Cast after check for type safety
  const coronaryArteryData = label.data as { position: number[][]; radius: number[] }

  // Create points and add them to a vtkPoints object
  const points = vtkPoints.newInstance()

  const coronaryArteryPoints = coronaryArteryData.position // Use checked data
  const coronaryArteryRadii = coronaryArteryData.radius // Use checked data

  if (
    !Array.isArray(coronaryArteryPoints) ||
    !Array.isArray(coronaryArteryRadii) || // Check if radii is an array
    coronaryArteryPoints.length === 0 ||
    coronaryArteryPoints.length !== coronaryArteryRadii.length // Ensure lengths match
  ) {
    throw new Error('Invalid coronary artery data: expected matching arrays of points and radii')
  }

  // Add points to the vtkPoints object
  for (const point of coronaryArteryPoints) {
    if (Array.isArray(point) && point.length >= 3) {
      points.insertNextPoint(point[0], point[1], point[2])
    } else {
      // Handle potential invalid point format if necessary
      console.warn('Skipping invalid point format:', point)
    }
  }

  // Create a polyline from the points
  const lines = vtkCellArray.newInstance()
  const numPoints = points.getNumberOfPoints()

  // Insert the polyline into the cell array
  const polyLine = new Uint16Array(numPoints + 1)
  polyLine[0] = numPoints
  for (let i = 0; i < numPoints; i++) {
    polyLine[i + 1] = i
  }
  lines.setData(polyLine)

  // Create polydata
  const polyData = vtkPolyData.newInstance()
  polyData.setPoints(points)
  polyData.setLines(lines)

  // Add radii as scalar data to the points
  const radiusData = vtkDataArray.newInstance({
    name: 'Radius',
    values: Float32Array.from(coronaryArteryRadii),
    numberOfComponents: 1, // Each radius is a single scalar value
  })
  polyData.getPointData().setScalars(radiusData)

  const tubeFilter = vtkTubeFilter.newInstance()
  tubeFilter.setCapping(true)
  tubeFilter.setNumberOfSides(16)
  // tubeFilter.setRadius(label.tubeRadius || 0.5) // Remove constant radius setting
  tubeFilter.setVaryRadius(VaryRadius.VARY_RADIUS_BY_SCALAR) // Use imported enum value
  tubeFilter.setInputData(polyData)
  // Specify which scalar array to use for varying the radius
  tubeFilter.setInputArrayToProcess(0, 'Radius', 'PointData', 'Scalars')

  // Create mapper and actor
  const mapper = vtkMapper.newInstance()
  mapper.setInputConnection(tubeFilter.getOutputPort())
  mapper.setScalarVisibility(false) // Disable coloring by scalar

  const actor = vtkActor.newInstance()
  actor.setMapper(mapper)

  // Set color and opacity from label properties
  const color = label.color || [0.5, 0.5, 1.0] // Default blue
  actor.getProperty().setColor(color[0], color[1], color[2])
  actor.getProperty().setOpacity(label.opacity || 1.0)

  // Add actor to renderer
  renderer.addActor(actor)

  // Store the actor in the label for later reference
  label.vtkActor = actor

  return actor
}

/**
 * Updates an existing coronary artery visualization.
 * @param label - The coronary artery label object with an existing vtkActor
 */
export function updateCoronaryArtery(label: Label): void {
  if (!label.vtkActor) return

  // Update color and opacity
  const color = label.color || [0.5, 0.5, 1.0]
  label.vtkActor.getProperty().setColor(color[0], color[1], color[2])
  label.vtkActor.getProperty().setOpacity(label.opacity || 1.0)

  // Update visibility
  label.vtkActor.setVisibility(label.visible)
}

/**
 * Removes a label visualization from the renderer.
 * @param renderer - The VTK renderer
 * @param label - The label object to remove
 */
export function removeLabel(renderer: vtkRenderer, label: Label): void {
  if (label.vtkActor) {
    renderer.removeActor(label.vtkActor)
    label.vtkActor = null
  }
}

/**
 * Draw all labels for a visualization.
 * @param visualization - The visualization containing labels
 */
export function drawLabelsForVisualization(visualization: Visualization): void {
  if (!visualization.viewport?.renderer || !visualization.labels) return

  const renderer = visualization.viewport.renderer

  // Draw each label based on its type
  for (const label of visualization.labels) {
    if (label.visible) {
      if (label.type === 'coronaryArtery') {
        drawCoronaryArtery(renderer, label)
      }
      // Add support for other label types here as needed
    }
  }
}

/**
 * Updates visibility of labels based on parent visualization visibility.
 * @param visualization - The visualization containing labels
 */
export function updateLabelsVisibility(visualization: Visualization): void {
  if (!visualization.labels) return

  for (const label of visualization.labels) {
    if (label.vtkActor) {
      const isVisible = visualization.visible && label.visible
      label.vtkActor.setVisibility(isVisible)
    }
  }
}

/**
 * Updates visibility of labels based on a list of selected filenames.
 * @param visualization - The visualization containing labels
 * @param selectedFilenames - An array of filenames for labels that should be visible
 */
export function updateLabelSelectionVisibility(
  visualization: Visualization,
  selectedFilenames: string[],
): void {
  if (!visualization.labels) return

  for (const label of visualization.labels) {
    if (label.vtkActor) {
      const isSelected = selectedFilenames.includes(label.filename)
      // Only make visible if the label is selected AND the overall visualization is visible
      label.vtkActor.setVisibility(isSelected && visualization.visible)
    }
  }
}

/**
 * Removes all labels from a visualization.
 * @param visualization - The visualization containing labels
 */
export function removeAllLabels(visualization: Visualization): void {
  if (!visualization.viewport?.renderer || !visualization.labels) return

  const renderer = visualization.viewport.renderer

  // Remove each label
  for (const label of visualization.labels) {
    removeLabel(renderer, label)
  }
}
