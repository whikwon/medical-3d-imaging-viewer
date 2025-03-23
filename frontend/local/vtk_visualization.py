import vtk


def create_multi_slice_image_mapper(
    image_data: vtk.vtkImageData, window_width: float, window_center: float
) -> dict:
    """
    Create a multi-slice image mapper and actors for orthogonal views (axial, coronal, sagittal)

    Args:
        image_data: VTK image data
        window_width: Optional window width from DICOM
        window_center: Optional window center from DICOM

    Returns:
        dict: Dictionary containing mappers, actors, and extent information
    """
    # Get the extent of the volume
    extent = image_data.GetExtent()

    # Calculate center slices for better initial view
    center_i = (extent[1] - extent[0]) // 2
    center_j = (extent[3] - extent[2]) // 2
    center_k = (extent[5] - extent[4]) // 2

    # Create actors for each orthogonal view
    # For I plane (YZ)
    actor_i = vtk.vtkImageActor()
    actor_i.GetMapper().SetInputData(image_data)
    actor_i.SetDisplayExtent(
        center_i, center_i, extent[2], extent[3], extent[4], extent[5]
    )

    # For J plane (XZ)
    actor_j = vtk.vtkImageActor()
    actor_j.GetMapper().SetInputData(image_data)
    actor_j.SetDisplayExtent(
        extent[0], extent[1], center_j, center_j, extent[4], extent[5]
    )

    # For K plane (XY)
    actor_k = vtk.vtkImageActor()
    actor_k.GetMapper().SetInputData(image_data)
    actor_k.SetDisplayExtent(
        extent[0], extent[1], extent[2], extent[3], center_k, center_k
    )

    # Set initial window/level settings
    # Get data range
    scalar_range = image_data.GetScalarRange()

    # Apply window/level settings to all actors
    actor_i.GetProperty().SetColorLevel(window_center)
    actor_i.GetProperty().SetColorWindow(window_width)
    actor_j.GetProperty().SetColorLevel(window_center)
    actor_j.GetProperty().SetColorWindow(window_width)
    actor_k.GetProperty().SetColorLevel(window_center)
    actor_k.GetProperty().SetColorWindow(window_width)

    return {
        "actors": [actor_i, actor_j, actor_k],
        "extent": extent,
        "center_slices": {"i": center_i, "j": center_j, "k": center_k},
        "scalar_range": scalar_range,
        "window_width": window_width,
        "window_center": window_center,
    }
