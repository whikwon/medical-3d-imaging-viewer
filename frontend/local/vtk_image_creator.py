import numpy as np
import vtk
from app.core.carm import CArmLPSAdapter
from app.core.coordinate import CoordinateSystem, PatientCoordinates
from app.core.dicom import BaseDicomHandler, VolumeDicomHandler
from vtkmodules.util import numpy_support


class VtkImageCreator:
    @staticmethod
    def create_ct_image(dcm_handler: VolumeDicomHandler):
        """Create a VTK image from DICOM data"""
        # Get dimension and spacing information
        dimensions = [
            dcm_handler.columns,
            dcm_handler.rows,
            dcm_handler.number_of_slices,
        ]
        spacing = dcm_handler.spacing

        # Get the volume data
        volume = dcm_handler.voxel_array

        # Get origin from the first slice's ImagePositionPatient
        origin = dcm_handler.get_image_position_patient(0)
        origin = PatientCoordinates(np.array(origin), CoordinateSystem.LPS).to_world(
            "HFS"
        )

        # Create direction matrix from ImageOrientationPatient
        direction_matrix = vtk.vtkMatrix3x3()

        # Get the orientation vectors for the first two axes (x and y)
        image_orientation = dcm_handler.image_orientation_patient
        row_direction = image_orientation[:3]
        col_direction = image_orientation[3:6]

        # Calculate the z direction as the cross product of row and column direction
        slice_direction = np.cross(row_direction, col_direction)

        # Fill in the direction matrix
        for i in range(3):
            direction_matrix.SetElement(i, 0, row_direction[i])
            direction_matrix.SetElement(i, 1, col_direction[i])
            direction_matrix.SetElement(i, 2, slice_direction[i])

        # Ensure the volume data is in the right format for VTK
        if volume.ndim == 3:
            # Transpose to ensure correct VTK ordering (x, y, z)
            volume = np.transpose(volume, (1, 0, 2))

        # Convert numpy array to VTK array
        if volume.dtype != np.uint16 and volume.dtype != np.int16:
            volume_flat = volume.reshape(-1).astype(np.uint16)
        else:
            volume_flat = volume.reshape(-1)

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
