import vtkXMLImageDataReader from '@kitware/vtk.js/IO/XML/XMLImageDataReader'
import vtkImageMapper from '@kitware/vtk.js/Rendering/Core/ImageMapper'
import vtkImageSlice from '@kitware/vtk.js/Rendering/Core/ImageSlice'

import type { Series } from '@/types/orthanc'
import type { Visualization } from '@/types/visualization'
import type vtkRenderer from '@kitware/vtk.js/Rendering/Core/Renderer'

interface VolumeControlParams {
  iExtentMin: number
  iExtentMax: number
  jExtentMin: number
  jExtentMax: number
  kExtentMin: number
  kExtentMax: number
  iSlice: number
  jSlice: number
  kSlice: number
  windowCenterMin: number
  windowCenterMax: number
  windowWidthMax: number
  windowCenter: number
  windowWidth: number
}

/**
 * Loads a CT volume visualization
 * @param renderer - The renderer to add the actors to
 * @param seriesId - Orthanc series ID
 * @param series - Series metadata
 * @param vtiData - The VTI blob data
 * @param windowWidth - Optional window width from DICOM/backend
 * @param windowCenter - Optional window center from DICOM/backend
 * @returns Visualization metadata and control values
 */
export async function loadVolumeVisualization(
  renderer: vtkRenderer,
  seriesId: string,
  series: Series,
  vtiData: Blob,
  windowWidth: number,
  windowCenter: number,
): Promise<{
  visualization: Visualization
  controlParams: VolumeControlParams
}> {
  // Use the first viewport's renderer
  const reader = vtkXMLImageDataReader.newInstance()
  const url = URL.createObjectURL(vtiData)

  try {
    await reader.setUrl(url)
    const data = reader.getOutputData()
    const dataRange = data.getPointData().getScalars().getRange()
    const extent = data.getExtent()

    // Calculate center slices for better initial view
    const centerI = Math.floor((extent[1] - extent[0]) / 2)
    const centerJ = Math.floor((extent[3] - extent[2]) / 2)
    const centerK = Math.floor((extent[5] - extent[4]) / 2)

    // Create the image mappers and actors
    const imageMapperI = vtkImageMapper.newInstance()
    imageMapperI.setInputData(data)
    imageMapperI.setSlice(centerI)
    imageMapperI.setSlicingMode(0) // I slicing

    const imageMapperJ = vtkImageMapper.newInstance()
    imageMapperJ.setInputData(data)
    imageMapperJ.setSlice(centerJ)
    imageMapperJ.setSlicingMode(1) // J slicing

    const imageMapperK = vtkImageMapper.newInstance()
    imageMapperK.setInputData(data)
    imageMapperK.setSlice(centerK)
    imageMapperK.setSlicingMode(2) // K slicing

    const actorI = vtkImageSlice.newInstance()
    actorI.setMapper(imageMapperI)

    const actorJ = vtkImageSlice.newInstance()
    actorJ.setMapper(imageMapperJ)

    const actorK = vtkImageSlice.newInstance()
    actorK.setMapper(imageMapperK)

    actorI.getProperty().setColorLevel(windowCenter)
    actorI.getProperty().setColorWindow(windowWidth)
    actorJ.getProperty().setColorLevel(windowCenter)
    actorJ.getProperty().setColorWindow(windowWidth)
    actorK.getProperty().setColorLevel(windowCenter)
    actorK.getProperty().setColorWindow(windowWidth)

    // Add actors to renderer
    renderer.addActor(actorI)
    renderer.addActor(actorJ)
    renderer.addActor(actorK)

    // Create the visualization object
    const visualization: Visualization = {
      type: 'volume',
      seriesId,
      description: `${series.MainDicomTags.SeriesDescription || 'Unknown'} (${series.MainDicomTags.Modality || 'CT'})`,
      actors: [actorI, actorJ, actorK],
      visible: true,
      data,
    }

    // Return data including control values
    return {
      visualization,
      controlParams: {
        iExtentMin: extent[0],
        iExtentMax: extent[1],
        jExtentMin: extent[2],
        jExtentMax: extent[3],
        kExtentMin: extent[4],
        kExtentMax: extent[5],
        iSlice: centerI,
        jSlice: centerJ,
        kSlice: centerK,
        windowCenterMin: Math.floor(dataRange[0]),
        windowCenterMax: Math.ceil(dataRange[1]),
        windowWidthMax: Math.ceil(dataRange[1] - dataRange[0]),
        windowCenter: windowCenter,
        windowWidth: windowWidth,
      },
    }
  } finally {
    // Clean up the URL
    URL.revokeObjectURL(url)
  }
}

interface MultiframeControlParams {
  maxFrame: number
  windowCenterMin: number
  windowCenterMax: number
  windowWidthMax: number
}

/**
 * Loads a multiframe visualization (like XA series)
 * @param renderer - The renderer to add the actors to
 * @param seriesId - Orthanc series ID
 * @param series - Series metadata
 * @param vtiData - The VTI blob data
 * @param windowWidth - Window width from DICOM/backend
 * @param windowCenter - Window center from DICOM/backend
 * @returns Visualization metadata and control values
 */
export async function loadMultiframeVisualization(
  renderer: vtkRenderer,
  seriesId: string,
  series: Series,
  vtiData: Blob,
  windowWidth: number,
  windowCenter: number,
): Promise<{
  visualization: Visualization
  controlParams: MultiframeControlParams
}> {
  const reader = vtkXMLImageDataReader.newInstance()
  const url = URL.createObjectURL(vtiData)

  try {
    await reader.setUrl(url)
    const data = reader.getOutputData()
    const dataRange = data.getPointData().getScalars().getRange()
    const extent = data.getExtent()

    // For multiframe, we'll use K slicing for frame navigation
    const numFrames = extent[5] - extent[4] + 1

    // Create image mapper and actor for the multiframe data
    const imageMapper = vtkImageMapper.newInstance()
    imageMapper.setInputData(data)
    imageMapper.setSlice(0) // Start with the first frame
    imageMapper.setSlicingMode(2) // K slicing for frames

    const actor = vtkImageSlice.newInstance()
    actor.setMapper(imageMapper)

    // Apply window/level from backend
    actor.getProperty().setColorLevel(windowCenter)
    actor.getProperty().setColorWindow(windowWidth)

    // Add actor to renderer
    renderer.addActor(actor)

    // Create a visualization record
    const visualization: Visualization = {
      type: 'multiframe',
      seriesId,
      description: `${series.MainDicomTags.SeriesDescription || 'Unknown'} (${series.MainDicomTags.Modality || 'XA'})`,
      actors: [actor],
      visible: true,
      data,
    }

    return {
      visualization,
      controlParams: {
        maxFrame: numFrames - 1,
        // Calculate window level controls from data range, same as volume visualization
        windowCenterMin: Math.floor(dataRange[0]),
        windowCenterMax: Math.ceil(dataRange[1]),
        windowWidthMax: Math.ceil(dataRange[1] - dataRange[0]),
      },
    }
  } finally {
    // Clean up the URL
    URL.revokeObjectURL(url)
  }
}

/**
 * Applies window/level settings to a volume or multiframe visualization
 * @param visualization - The visualization
 * @param windowCenter - Window center (level) value
 * @param windowWidth - Window width value
 */
export function applyWindowLevel(
  visualization: Visualization,
  windowCenter: number,
  windowWidth: number,
): void {
  // Apply to all actors in the visualization
  visualization.actors.forEach((actor) => {
    actor.getProperty().setColorLevel(windowCenter)
    actor.getProperty().setColorWindow(windowWidth)
  })
}

/**
 * Updates the slice positions for a volume visualization
 * @param visualization - The volume visualization
 * @param iSlice - I-axis slice value
 * @param jSlice - J-axis slice value
 * @param kSlice - K-axis slice value
 */
export function updateVolumeSlices(
  visualization: Visualization,
  iSlice: number,
  jSlice: number,
  kSlice: number,
): void {
  if (visualization.type !== 'volume') return

  // Assuming actors are in order: I, J, K
  const iMapper = visualization.actors[0].getMapper()
  const jMapper = visualization.actors[1].getMapper()
  const kMapper = visualization.actors[2].getMapper()

  iMapper.setSlice(iSlice)
  jMapper.setSlice(jSlice)
  kMapper.setSlice(kSlice)
}

/**
 * Updates the current frame for a multiframe visualization
 * @param visualization - The multiframe visualization
 * @param frameIndex - The frame index to show
 */
export function updateMultiframeFrame(visualization: Visualization, frameIndex: number): void {
  if (visualization.type !== 'multiframe') return

  const actor = visualization.actors[0]
  const mapper = actor.getMapper()
  mapper.setSlice(frameIndex)
}

/**
 * Toggles visibility of a visualization
 * @param visualization - The visualization to toggle
 * @param visible - Whether the visualization should be visible
 */
export function setVisualizationVisibility(visualization: Visualization, visible: boolean): void {
  // Set visibility on the visualization object
  visualization.visible = visible

  // Set visibility for all actors in this visualization
  visualization.actors.forEach((actor) => {
    actor.setVisibility(visible)
  })
}

/**
 * Removes a visualization from the renderer
 * @param renderer - The renderer to remove the actors from
 * @param visualization - The visualization to remove
 */
export function removeVisualization(renderer: vtkRenderer, visualization: Visualization): void {
  // Remove all actors from renderer
  visualization.actors.forEach((actor) => {
    renderer.removeActor(actor)
  })
}
