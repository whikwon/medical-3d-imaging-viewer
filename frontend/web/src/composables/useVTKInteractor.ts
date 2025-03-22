import vtkSphereSource from '@kitware/vtk.js/Filters/Sources/SphereSource'
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor'
import vtkCellPicker from '@kitware/vtk.js/Rendering/Core/CellPicker'
import vtkCoordinate from '@kitware/vtk.js/Rendering/Core/Coordinate'
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper'
import { onBeforeUnmount, ref, type Ref } from 'vue'

import type { VTKViewerInstance } from '@/services/vtkViewerService'
import type { Visualization } from '@/types/visualization'; // Ensure this path is correct

export function useVTKInteractor(vtkInstanceRef: Ref<VTKViewerInstance | null>) {
  const sphereActor = ref<any>(null)
  const lastPosition = ref<number[] | null>(null)
  const coordinate = ref<any>(null)

  function setupInteraction(activeVisualization: Visualization | null) {
    const vtkInstance = vtkInstanceRef.value
    if (!vtkInstance) return

    // Clean up previous actors if they exist
    cleanupInteraction()

    const { renderer, renderWindow, interactor } = vtkInstance

    // Create sphere source
    const sphereSource = vtkSphereSource.newInstance({
      radius: 10,
      thetaResolution: 12,
      phiResolution: 12,
    })

    const mapper = vtkMapper.newInstance()
    mapper.setInputConnection(sphereSource.getOutputPort())

    const actor = vtkActor.newInstance()
    actor.setMapper(mapper)
    actor.getProperty().setColor(1.0, 0.0, 0.0)

    // Position the sphere based on visualization type
    if (activeVisualization && activeVisualization.data) {
      const origin = activeVisualization.data.getOrigin()
      actor.setPosition(origin[0], origin[1], origin[2])
    }

    // Create picker
    const picker = vtkCellPicker.newInstance()
    picker.setPickFromList(1)
    picker.setTolerance(0)
    picker.initializePickList()
    picker.addPickList(actor)

    // Create coordinate system
    const coord = vtkCoordinate.newInstance()
    coord.setCoordinateSystemToDisplay()

    // Store references
    sphereActor.value = actor
    coordinate.value = coord

    // Add actor to renderer
    renderer.addActor(actor)

    // Set up interaction handlers
    interactor.onLeftButtonPress((event: any) => {
      const displayPosition = [event.position.x, event.position.y, 0]
      picker.pick(displayPosition, renderer)
      if (picker.getActors().length > 0) {
        const pickedPositions = picker.getPickedPositions()
        lastPosition.value = pickedPositions[0]
      }
    })

    interactor.onRightButtonPress((event: any) => {
      if (!lastPosition.value || !coordinate.value || !renderer) return

      const camera = renderer.getActiveCamera()
      const planeNormal = camera.getDirectionOfProjection()
      const planePoint = lastPosition.value

      const nearDisplay = [event.position.x, event.position.y, 0.0]
      coordinate.value.setValue(nearDisplay)
      const worldNear = coordinate.value.getComputedWorldValue(renderer)

      const farDisplay = [event.position.x, event.position.y, 1.0]
      coordinate.value.setValue(farDisplay)
      const worldFar = coordinate.value.getComputedWorldValue(renderer)

      const rayDirection = [
        worldFar[0] - worldNear[0],
        worldFar[1] - worldNear[1],
        worldFar[2] - worldNear[2],
      ]
      const len = Math.sqrt(
        rayDirection[0] * rayDirection[0] +
          rayDirection[1] * rayDirection[1] +
          rayDirection[2] * rayDirection[2],
      )
      rayDirection[0] /= len
      rayDirection[1] /= len
      rayDirection[2] /= len

      const num =
        (planePoint[0] - worldNear[0]) * planeNormal[0] +
        (planePoint[1] - worldNear[1]) * planeNormal[1] +
        (planePoint[2] - worldNear[2]) * planeNormal[2]
      const denom =
        rayDirection[0] * planeNormal[0] +
        rayDirection[1] * planeNormal[1] +
        rayDirection[2] * planeNormal[2]
      if (denom === 0) return
      const t = num / denom
      const currentPosition = [
        worldNear[0] + t * rayDirection[0],
        worldNear[1] + t * rayDirection[1],
        worldNear[2] + t * rayDirection[2],
      ]

      const translation = [
        currentPosition[0] - lastPosition.value[0],
        currentPosition[1] - lastPosition.value[1],
        currentPosition[2] - lastPosition.value[2],
      ]

      // Move all actors in the current visualization
      if (activeVisualization) {
        activeVisualization.actors.forEach((actor: any) => {
          const currentPos = actor.getPosition()
          actor.setPosition(
            currentPos[0] + translation[0],
            currentPos[1] + translation[1],
            currentPos[2] + translation[2],
          )
        })
      }

      // Move the sphere along with the images
      const currentSpherePos = actor.getPosition()
      actor.setPosition(
        currentSpherePos[0] + translation[0],
        currentSpherePos[1] + translation[1],
        currentSpherePos[2] + translation[2],
      )

      lastPosition.value = currentPosition
      renderWindow.render()
    })

    renderWindow.render()
  }

  function cleanupInteraction() {
    const vtkInstance = vtkInstanceRef.value
    if (sphereActor.value && vtkInstance?.renderer) {
      vtkInstance.renderer.removeActor(sphereActor.value)
      sphereActor.value = null
    }
    lastPosition.value = null
  }

  // Cleanup on unmount
  onBeforeUnmount(() => {
    cleanupInteraction()
  })

  return {
    setupInteraction,
    cleanupInteraction,
  }
}
