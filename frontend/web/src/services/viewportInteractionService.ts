import vtkInteractorStyleImage from '@kitware/vtk.js/Interaction/Style/InteractorStyleImage'
import vtkInteractorStyleTrackballCamera from '@kitware/vtk.js/Interaction/Style/InteractorStyleTrackballCamera'
import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor'

/**
 * Simple manager class for viewport interactions
 * Handles coordination between multiple containers
 */
export class ViewportInteractionManager {
  // Static registry of all containers and their interactors
  private static containers = new Map<
    HTMLElement,
    {
      interactor: vtkRenderWindowInteractor
      style: vtkInteractorStyleImage | vtkInteractorStyleTrackballCamera
      widgets: Array<{ widget: unknown; enabled: boolean }>
    }
  >()

  // Currently active container
  private static activeContainer: HTMLElement | null = null

  /**
   * Register a new container with its interactor
   */
  static registerContainer(
    container: HTMLElement,
    interactor: vtkRenderWindowInteractor,
    style: vtkInteractorStyleImage | vtkInteractorStyleTrackballCamera,
  ): void {
    // Store the container with its interactor
    this.containers.set(container, {
      interactor,
      style,
      widgets: [],
    })

    // Add pointerenter handler to activate this container
    const pointerEnterHandler = () => {
      this.activateContainer(container)
    }

    // Store the handler on the container for reference
    ;(container as any)._pointerEnterHandler = pointerEnterHandler
    container.addEventListener('pointerenter', pointerEnterHandler)
  }

  /**
   * Register a widget with a container
   */
  static registerWidget(container: HTMLElement, widget: unknown): void {
    const containerData = this.containers.get(container)
    if (containerData) {
      containerData.widgets.push(widget)
    }
  }

  /**
   * Activate a specific container and deactivate all others
   */
  static activateContainer(container: HTMLElement): void {
    // Skip if already active
    if (this.activeContainer === container) {
      return
    }

    // Deactivate all other containers
    this.containers.forEach((data, currentContainer) => {
      if (currentContainer !== container) {
        // Unbind the interactor from this container
        const interactor = data.interactor
        if (interactor.getContainer() === currentContainer) {
          interactor.unbindEvents()
        }

        // Disable widgets if needed (implementation depends on widget type)
        // For most VTK widgets, this would involve calling setEnabled(false)
        data.widgets.forEach((widget) => {
          // Mark as disabled in our tracking
          widget.setEnabled(false)

          // Actual widget disabling would depend on the widget type
          // e.g., (widgetInfo.widget as any).setEnabled?.(false);
        })
      }
    })

    // Activate this container
    const containerData = this.containers.get(container)
    if (containerData) {
      const { interactor, style } = containerData

      // Set up the interactor for this container
      interactor.setInteractorStyle(style)
      interactor.bindEvents(container)

      // Enable widgets for this container
      containerData.widgets.forEach((widget) => {
        // Mark as enabled in our tracking
        widget.setEnabled(true)

        // Actual widget enabling would depend on the widget type
        // e.g., (widgetInfo.widget as any).setEnabled?.(true);
      })
    }

    // Update active container
    this.activeContainer = container
  }

  /**
   * Remove container when no longer needed
   */
  static unregisterContainer(container: HTMLElement): void {
    if (this.activeContainer === container) {
      this.activeContainer = null
    }

    // Remove pointerenter handler
    const handler = (container as any)._pointerEnterHandler
    if (handler) {
      container.removeEventListener('pointerenter', handler)
      delete (container as any)._pointerEnterHandler
    }

    this.containers.delete(container)
  }

  /**
   * Get the currently active container
   */
  static getActiveContainer(): HTMLElement | null {
    return this.activeContainer
  }
}

/**
 * Set up interaction for a viewport container
 */
export function setupViewportInteraction(
  container: HTMLElement,
  interactor: vtkRenderWindowInteractor,
  interactorStyle: vtkInteractorStyleImage | vtkInteractorStyleTrackballCamera,
): void {
  ViewportInteractionManager.registerContainer(container, interactor, interactorStyle)
}

/**
 * Register a widget with a container
 */
export function registerWidget(container: HTMLElement, widget: unknown): void {
  ViewportInteractionManager.registerWidget(container, widget)
}

/**
 * Clean up a container when no longer needed
 */
export function cleanupViewportInteraction(container: HTMLElement): void {
  ViewportInteractionManager.unregisterContainer(container)
}

/**
 * Manually activate a container
 */
export function activateViewport(container: HTMLElement): void {
  ViewportInteractionManager.activateContainer(container)
}

/**
 * Instance-based wrapper around the static manager
 * Maintains backward compatibility with previous code
 */
export class ViewportInteractionManagerInstance {
  private container: HTMLElement | null = null
  private interactor: vtkRenderWindowInteractor | null = null
  private interactorStyle: vtkInteractorStyleImage | vtkInteractorStyleTrackballCamera | null = null

  /**
   * Initialize with required objects
   */
  initialize(
    container: HTMLElement,
    interactor: vtkRenderWindowInteractor,
    interactorStyle: vtkInteractorStyleImage | vtkInteractorStyleTrackballCamera,
  ): void {
    this.cleanup() // Clean up any existing handlers

    this.container = container
    this.interactor = interactor
    this.interactorStyle = interactorStyle

    // Register with the static manager
    ViewportInteractionManager.registerContainer(container, interactor, interactorStyle)
  }

  /**
   * Register a widget with the container
   */
  registerWidget(widget: unknown): void {
    if (this.container) {
      ViewportInteractionManager.registerWidget(this.container, widget)
    }
  }

  /**
   * Clean up all handlers
   */
  cleanup(): void {
    if (this.container) {
      ViewportInteractionManager.unregisterContainer(this.container)
    }

    this.container = null
    this.interactor = null
    this.interactorStyle = null
  }

  /**
   * Check if this viewport is currently active
   */
  isActive(): boolean {
    if (!this.container) return false
    return ViewportInteractionManager.getActiveContainer() === this.container
  }

  /**
   * Manually activate this viewport
   */
  activate(): void {
    if (this.container) {
      ViewportInteractionManager.activateContainer(this.container)
    }
  }
}
