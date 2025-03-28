"""
VTK utility functions for medical imaging visualization.

This module provides centralized functionality for creating VTK image data objects
from various medical imaging sources (DICOM, etc.) and handling common operations
like creating slice viewers, writing to VTI format, etc.

These utilities are shared between frontend and backend code to maintain consistent
behavior and reduce duplication.
"""

import numpy as np
import vtk
from vtkmodules.util import numpy_support

from app.core.carm import CArmLPSAdapter
from app.core.dicom import BaseDicomHandler, VolumeDicomHandler


def rotation_matrix_to_vtk_direction_matrix(
    rotation_matrix: np.ndarray,
    column_major: bool = False,
) -> vtk.vtkMatrix3x3:
    direction_matrix = vtk.vtkMatrix3x3()
    if column_major:
        # vtk.js
        for i in range(3):
            for j in range(3):
                direction_matrix.SetElement(i, j, rotation_matrix[j][i])
    else:
        # vtk
        for i in range(3):
            for j in range(3):
                direction_matrix.SetElement(i, j, rotation_matrix[i][j])
    return direction_matrix


def create_vtk_image_from_volume(
    ct_handler: VolumeDicomHandler,
    center_at_origin: bool = False,
    column_major: bool = False,
) -> vtk.vtkImageData:
    """
    Create a VTK image from volume DICOM data (CT, MR, etc.)

    Args:
        ct_handler: The volume DICOM handler with the dataset
        center_at_origin: If True, centers the volume at world origin (0,0,0)
        column_major: If True, uses column-major order for the direction matrix

    Returns:
        VTK image data object
    """
    # Get dimension and spacing information
    dimensions = [
        ct_handler.columns,
        ct_handler.rows,
        ct_handler.number_of_slices,
    ]
    spacing = ct_handler.spacing

    # Get the volume data
    volume = ct_handler.voxel_array

    # Set origin - either at the image position or centered at world origin
    origin = ct_handler.get_image_position_patient(0)
    if center_at_origin:
        origin -= ct_handler.volume_center_position_mm

    # Create direction matrix from image orientation
    rotation_matrix = ct_handler.image_direction_matrix
    direction_matrix = rotation_matrix_to_vtk_direction_matrix(
        rotation_matrix, column_major=column_major
    )

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


def create_vtk_image_from_multiframe(
    dcm_handler: BaseDicomHandler,
    carm: CArmLPSAdapter,
    column_major: bool = False,
) -> vtk.vtkImageData:
    """
    Create a VTK image from multiframe DICOM data (XA, US, etc.)

    Args:
        dcm_handler: The DICOM handler with the dataset
        carm: The C-arm adapter with geometry information
        column_major: If True, uses column-major order for the direction matrix

    Returns:
        VTK image data object
    """
    # Get dimension and spacing information
    num_frames = dcm_handler.number_of_frames
    frame_shape = [dcm_handler.rows, dcm_handler.columns]
    imager_pixel_spacing = dcm_handler.imager_pixel_spacing
    spacing = [imager_pixel_spacing[0], imager_pixel_spacing[1], 0.0]

    # Get frames
    frames = dcm_handler.pixel_array

    # Calculate origin and direction
    origin = carm.image_origin
    rotation_matrix = carm.rotation

    # Create direction matrix
    direction_matrix = rotation_matrix_to_vtk_direction_matrix(
        rotation_matrix, column_major=column_major
    )

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


def write_vtk_image_to_vti(vtk_image: vtk.vtkImageData) -> bytes:
    """
    Write VTK image data to VTI format as bytes

    Args:
        vtk_image: The VTK image data to write

    Returns:
        The VTI data as bytes
    """
    writer = vtk.vtkXMLImageDataWriter()
    writer.SetInputData(vtk_image)
    writer.SetDataModeToBinary()
    writer.SetCompressorTypeToZLib()
    writer.WriteToOutputStringOn()
    writer.Update()

    vti_data = writer.GetOutputString()

    # Convert to bytes if it's a string
    if isinstance(vti_data, str):
        vti_data = vti_data.encode("utf-8")

    return vti_data
