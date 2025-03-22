"""
DICOM API routes using the OrthancClient singleton.
This demonstrates how to use the Orthanc client throughout the application.
"""

import logging

# Now convert the NumPy volume to VTI format
from typing import Any

import numpy as np
import vtk
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pyorthanc import (
    Instance,
    Series,
    Study,
    find_instances,
    find_patients,
    find_studies,
)
from vtkmodules.util import numpy_support

from app.core.carm import CArm, CArmLPSAdapter
from app.core.dicom import BaseDicomHandler, VolumeDicomHandler
from app.core.orthanc import orthanc_client
from app.core.vtk_utils import rotation_matrix_to_vtk_direction_matrix

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/patients")
async def get_patients(query: dict[str, Any] = None, labels: list[str] | str = None):
    """Get all patients from Orthanc."""
    return find_patients(orthanc_client.client, query, labels)


@router.get("/studies")
async def get_studies(query: dict[str, Any] = None, labels: list[str] | str = None):
    """Get all studies from Orthanc."""
    studies = find_studies(orthanc_client.client, query, labels)
    return [study.get_main_information() for study in studies]


@router.get("/instances")
async def get_instances(query: dict[str, Any] = None, labels: list[str] | str = None):
    """Get all instances from Orthanc."""
    instances = find_instances(orthanc_client.client, query, labels)
    dicoms = []
    for ins in instances:
        dicoms.append(ins.get_pydicom())
    return dicoms


@router.get("/instance/{instance_id}/file")
async def get_instance_file(instance_id: str):
    """Get DICOM file for a specific instance using pyorthanc Instance class."""
    try:
        # Pass the underlying client, not the wrapper
        instance = Instance(instance_id, orthanc_client.client)
        dicom_data = instance.get_dicom_file_content()

        # Instead of using StreamingResponse directly with the bytes data,
        # we'll use Response with the bytes directly
        return Response(
            content=dicom_data,
            media_type="application/dicom",
            headers={"Content-Disposition": f"attachment; filename={instance_id}.dcm"},
        )
    except Exception as e:
        logger.error(f"Failed to retrieve file for instance {instance_id}: {e}")
        raise HTTPException(
            status_code=404, detail=f"Instance file not found: {str(e)}"
        )


# Replace the separate volume and multiframe endpoints with a single unified endpoint
@router.get("/series/{series_id}/data")
async def get_series_data(series_id: str):
    """Get 3D volume or multiframe data from a series for VTK.js visualization.
    Automatically determines whether to process as standard volumetric data or multiframe data.
    """
    # Get all instances in this series
    series = Series(series_id, orthanc_client.client)
    instances = series.instances

    if not instances:
        raise HTTPException(
            status_code=404, detail=f"No instances found in series {series_id}"
        )

    # Check if this is a multi-frame series
    first_instance = instances[0].get_pydicom()

    # Determine if this is a multiframe series (either by modality or by checking NumberOfFrames)
    is_multiframe = False
    if hasattr(first_instance, "Modality") and first_instance.Modality == "XA":
        is_multiframe = True
    elif (
        hasattr(first_instance, "NumberOfFrames")
        and int(first_instance.NumberOfFrames) > 1
    ):
        is_multiframe = True

    if is_multiframe:
        return await _process_multiframe_data(instances)
    else:
        return await _process_volume_data(instances)


async def _process_volume_data(instances):
    """Process volumetric data (CT, MR, etc.) using CtImageDicomHandler"""
    if not instances:
        raise HTTPException(status_code=404, detail="No instances found")

    # Get all DICOM datasets
    dicom_datasets = [instance.get_pydicom() for instance in instances]

    # Create CtImageDicomHandler with the datasets
    ct_handler = VolumeDicomHandler(dicom_datasets)

    # Get volume dimensions and shape
    volume = ct_handler.voxel_array
    dimensions = [
        ct_handler.columns,
        ct_handler.rows,
        ct_handler.number_of_slices,
    ]

    # Get spacing from the handler
    spacing = ct_handler.spacing

    # Get image orientation and create direction matrix
    rotation_matrix = ct_handler.image_direction_matrix
    direction_matrix = rotation_matrix_to_vtk_direction_matrix(rotation_matrix.T)

    # Get origin (position of first slice)
    ct_center_position = ct_handler.volume_center_position_mm
    origin = ct_handler.get_image_position_patient(0)
    origin -= ct_center_position

    # Create VTK image data
    vtk_image = vtk.vtkImageData()
    vtk_image.SetDimensions(dimensions)
    vtk_image.SetSpacing(spacing)
    vtk_image.SetOrigin(origin)
    vtk_image.SetDirectionMatrix(direction_matrix)

    # Ensure data type compatibility with VTK
    if volume.dtype != np.uint16 and volume.dtype != np.int16:
        # Convert to uint16 for consistency
        volume_flat = volume.astype(np.uint16).flatten()
    else:
        volume_flat = volume.flatten()

    # Convert numpy array to VTK array
    vtk_array = numpy_support.numpy_to_vtk(
        volume_flat, deep=True, array_type=vtk.VTK_UNSIGNED_SHORT
    )

    # Set the VTK array as the image data's point data
    vtk_image.GetPointData().SetScalars(vtk_array)

    # Write the VTI file to memory
    writer = vtk.vtkXMLImageDataWriter()
    writer.SetInputData(vtk_image)
    writer.SetDataModeToBinary()
    writer.SetCompressorTypeToZLib()

    # Write to memory instead of disk
    writer.WriteToOutputStringOn()
    writer.Update()

    # Get the VTI data as string and encode it
    vti_data = writer.GetOutputString()

    # Convert to bytes if it's a string (needed for base64 encoding)
    if isinstance(vti_data, str):
        vti_data = vti_data.encode("utf-8")

    return Response(content=vti_data, media_type="application/octet-stream")


async def _process_multiframe_data(instances):
    """Process multiframe data (XA, US, etc.)"""
    if not instances or len(instances) == 0:
        raise HTTPException(status_code=404, detail="No instances found")

    # For XA, we typically have one instance with multiple frames
    # Let's get the first instance that has multiple frames
    dcm_handler = None
    for instance in instances:
        dcm_handler = BaseDicomHandler(instance.get_pydicom())
        if dcm_handler.number_of_frames > 1:
            dcm_handler = dcm_handler
            break

    if not dcm_handler:
        raise HTTPException(
            status_code=404,
            detail="No multi-frame instance found in series",
        )

    # Get the number of frames
    num_frames = dcm_handler.number_of_frames

    # Get the dimensions of each frame
    frame_shape = [dcm_handler.rows, dcm_handler.columns]

    # Extract or calculate spacing
    imager_pixel_spacing = dcm_handler.imager_pixel_spacing
    spacing = [imager_pixel_spacing[0], imager_pixel_spacing[1], 1.0]

    # Isocenter
    alpha = dcm_handler.positioner_primary_angle
    beta = dcm_handler.positioner_secondary_angle
    carm = CArm(
        alpha=alpha,
        beta=beta,
        sid=dcm_handler.distance_source_to_detector,
        sod=dcm_handler.distance_source_to_patient,
        imager_pixel_spacing=spacing,
        rows=dcm_handler.rows,
        columns=dcm_handler.columns,
        table_top_position=np.array([0, 0, 0]),
    )
    carm = CArmLPSAdapter(carm)
    origin = carm.image_origin
    rotation_matrix = carm.rotation

    # Create a 3D volume from the frames
    frames = dcm_handler.pixel_array

    # Create VTK image data
    vtk_image = vtk.vtkImageData()
    vtk_image.SetDimensions(frame_shape[1], frame_shape[0], num_frames)
    vtk_image.SetSpacing(spacing)
    vtk_image.SetOrigin(origin)

    # Create vtkMatrix3x3 and populate it with rotation matrix values
    # direction matrix 값이 같은데 vtk.js로 가면 반대로 나와서 transpose 적용
    direction_matrix = rotation_matrix_to_vtk_direction_matrix(rotation_matrix.T)

    # Set the direction matrix using the vtkMatrix3x3 object
    vtk_image.SetDirectionMatrix(direction_matrix)

    # Ensure data type compatibility with VTK
    if frames.dtype != np.uint16 and frames.dtype != np.int16:
        # Convert to uint16 for consistency
        volume_flat = frames.reshape(-1).astype(np.uint16)
    else:
        volume_flat = frames.reshape(-1)

    # Convert numpy array to VTK array
    vtk_array = numpy_support.numpy_to_vtk(
        volume_flat, deep=True, array_type=vtk.VTK_UNSIGNED_SHORT
    )

    # Set the VTK array as the image data's point data
    vtk_image.GetPointData().SetScalars(vtk_array)

    # Write the VTI file to memory
    writer = vtk.vtkXMLImageDataWriter()
    writer.SetInputData(vtk_image)
    writer.SetDataModeToBinary()
    writer.SetCompressorTypeToZLib()

    # Write to memory instead of disk
    writer.WriteToOutputStringOn()
    writer.Update()

    # Get the VTI data as string and encode it
    vti_data = writer.GetOutputString()

    # Convert to bytes if it's a string (needed for base64 encoding)
    if isinstance(vti_data, str):
        vti_data = vti_data.encode("utf-8")

    # Return the VTI data with metadata
    return Response(content=vti_data, media_type="application/octet-stream")


@router.get("/studies/{study_id}/series")
async def get_study_series(study_id: str):
    """Get all series for a specific study from Orthanc."""
    try:
        study = Study(study_id, orthanc_client.client)
        series_list = [series.get_main_information() for series in study.series]

        return series_list
    except Exception as e:
        logger.error(f"Failed to get series for study {study_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Study not found or error retrieving series: {str(e)}",
        )
