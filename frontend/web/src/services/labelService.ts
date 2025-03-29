import type { Label, Visualization } from '@/types/visualization'
import vtkCellArray from '@kitware/vtk.js/Common/Core/CellArray'
import vtkPoints from '@kitware/vtk.js/Common/Core/Points'
import vtkPolyData from '@kitware/vtk.js/Common/DataModel/PolyData'
import vtkTubeFilter from '@kitware/vtk.js/Filters/General/TubeFilter'
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor'
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper'
import vtkRenderer from '@kitware/vtk.js/Rendering/Core/Renderer'

/**
 * Draws a centerline as a tube in the renderer.
 * @param renderer - The VTK renderer
 * @param label - The centerline label object
 * @returns The created VTK actor
 */
export function drawCenterline(renderer: vtkRenderer, label: Label): vtkActor {
  // Create points and add them to a vtkPoints object
  const points = vtkPoints.newInstance()

  // Cast label.data to array if it's a valid centerline
  console.log('label.data', label.data)
  const centerlinePoints = label.data as number[][]
  if (!Array.isArray(centerlinePoints) || centerlinePoints.length === 0) {
    throw new Error('Invalid centerline data: expected array of points')
  }

  // Add points to the vtkPoints object
  for (const point of centerlinePoints) {
    if (Array.isArray(point) && point.length >= 3) {
      points.insertNextPoint(point[0], point[1], point[2])
    }
  }

  // Create a polyline from the points
  const lines = vtkCellArray.newInstance()
  const numPoints = centerlinePoints.length

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

  // Use tube filter to create a tube along the centerline
  const tubeFilter = vtkTubeFilter.newInstance()
  tubeFilter.setCapping(true)
  tubeFilter.setNumberOfSides(16)
  tubeFilter.setRadius(label.tubeRadius || 0.5)
  tubeFilter.setInputData(polyData)

  // Create mapper and actor
  const mapper = vtkMapper.newInstance()
  mapper.setInputConnection(tubeFilter.getOutputPort())

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
 * Updates an existing centerline visualization.
 * @param label - The centerline label object with an existing vtkActor
 */
export function updateCenterline(label: Label): void {
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
      if (label.type === 'centerline') {
        drawCenterline(renderer, label)
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
