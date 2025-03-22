import numpy as np
import vtk
from app.core.carm import CArmLPSAdapter
from app.core.dicom import BaseDicomHandler, VolumeDicomHandler
from app.core.vtk_utils import rotation_matrix_to_vtk_direction_matrix
from vtkmodules.util import numpy_support


class VtkImageCreator:
    @staticmethod
    def create_ct_image(ct_handler: VolumeDicomHandler):
        """Create a VTK image from DICOM data"""
        # Get dimension and spacing information
        dimensions = [
            ct_handler.columns,
            ct_handler.rows,
            ct_handler.number_of_slices,
        ]
        spacing = ct_handler.spacing

        # Get the volume data
        volume = ct_handler.voxel_array

        # To center the CT volume at the world origin (0,0,0),
        # we need to set the origin such that half the volume's physical size
        # extends in negative coordinates and half in positive.
        # Calculate the physical size of the volume in each dimension
        origin = ct_handler.get_image_position_patient(0)
        # origin -= dcm_handler.volume_center_position_mm

        # Create direction matrix from ImageOrientationPatient
        direction_matrix = vtk.vtkMatrix3x3()

        # Get the orientation vectors for the first two axes (x and y)
        rotation_matrix = ct_handler.image_direction_matrix
        direction_matrix = rotation_matrix_to_vtk_direction_matrix(rotation_matrix)

        # Convert numpy array to VTK array
        if volume.dtype != np.uint16 and volume.dtype != np.int16:
            volume_flat = volume.flatten().astype(np.uint16)
        else:
            volume_flat = volume.flatten()

        vtk_array = numpy_support.numpy_to_vtk(
            volume_flat, deep=True, array_type=vtk.VTK_UNSIGNED_SHORT
        )

        # Create VTK image data
        image_data = vtk.vtkImageData()
        image_data.SetDimensions(dimensions)
        image_data.SetSpacing(spacing)
        image_data.SetOrigin(origin)
        image_data.SetDirectionMatrix(direction_matrix)
        image_data.GetPointData().SetScalars(vtk_array)

        return image_data

    @staticmethod
    def create_xa_image(dcm_handler: BaseDicomHandler, carm: CArmLPSAdapter):
        """Create a VTK image from DICOM data and CArm parameters"""
        # Get dimension and spacing information
        num_frames = dcm_handler.number_of_frames
        frame_shape = [dcm_handler.rows, dcm_handler.columns]
        imager_pixel_spacing = dcm_handler.imager_pixel_spacing
        spacing = [imager_pixel_spacing[0], imager_pixel_spacing[1], 1.0]

        # Get frames
        frames = dcm_handler.pixel_array

        # Calculate origin and direction
        origin = carm.image_origin
        rotation_matrix = carm.rotation

        # Create direction matrix
        direction_matrix = vtk.vtkMatrix3x3()

        for i in range(3):
            for j in range(3):
                direction_matrix.SetElement(i, j, rotation_matrix[i][j])

        # Convert numpy array to VTK array
        if frames.dtype != np.uint16 and frames.dtype != np.int16:
            volume_flat = frames.reshape(-1).astype(np.uint16)
        else:
            volume_flat = frames.reshape(-1)

        vtk_array = numpy_support.numpy_to_vtk(
            volume_flat, deep=True, array_type=vtk.VTK_UNSIGNED_SHORT
        )

        # Create VTK image data
        image_data = vtk.vtkImageData()
        image_data.SetDimensions(frame_shape[1], frame_shape[0], num_frames)
        image_data.SetSpacing(spacing)
        image_data.SetOrigin(origin)
        image_data.SetDirectionMatrix(direction_matrix)
        image_data.GetPointData().SetScalars(vtk_array)

        return image_data

    @staticmethod
    def create_multi_slice_image_mapper(
        image_data, window_width=None, window_center=None
    ):
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

        # Use DICOM window values if provided, otherwise use defaults
        if window_width is not None and window_center is not None:
            print(
                f"Using DICOM window settings: Width={window_width}, Center={window_center}"
            )
        else:
            # Adjust window/level settings for better CT visualization
            # Typical window/level values for different CT tissues:
            # - Bone: width ~2000, center ~500
            # - Soft tissue: width ~400, center ~40
            # - Lung: width ~1500, center ~-600

            # Try a bone-like window that shows more detail and less brightness
            window_width = 1500  # Wider window to see more range of values
            window_center = 300  # Higher center value to reduce brightness
            print(
                f"Using default window settings: Width={window_width}, Center={window_center}"
            )

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
