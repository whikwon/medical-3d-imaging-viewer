"""
DICOM API routes using the OrthancClient singleton.
This demonstrates how to use the Orthanc client throughout the application.
"""

import logging
from typing import Any

import numpy as np
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

from app.core.carm import CArm, CArmLPSAdapter
from app.core.dicom import BaseDicomHandler, VolumeDicomHandler
from app.core.intensity_transform import compute_optimal_window_level
from app.core.orthanc import orthanc_client
from app.core.vtk_utils import (
    create_vtk_image_from_multiframe,
    create_vtk_image_from_volume,
    write_vtk_image_to_vti,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/patients")
async def get_patients(query: dict[str, Any] = None, labels: list[str] | str = None):
    """Get all patients from Orthanc."""
    patients = find_patients(orthanc_client.client, query, labels)
    return [patient.get_main_information() for patient in patients]


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
    """Process volumetric data (CT, MR, etc.) using VolumeDicomHandler"""
    if not instances:
        raise HTTPException(status_code=404, detail="No instances found")

    # Get all DICOM datasets
    dicom_datasets = [instance.get_pydicom() for instance in instances]

    # Create VolumeDicomHandler with the datasets
    ct_handler = VolumeDicomHandler(dicom_datasets)

    # Create VTK image data using the centralized utility function
    vtk_image = create_vtk_image_from_volume(
        ct_handler, center_at_origin=True, column_major=True
    )

    # Write to VTI format
    vti_data = write_vtk_image_to_vti(vtk_image)

    # If window level information is not available in DICOM, calculate optimal values
    window_width, window_center = compute_optimal_window_level(ct_handler.voxel_array)

    # Create response with binary data and window level info
    return Response(
        content=vti_data,
        media_type="application/octet-stream",
        headers={
            "X-Window-Width": str(window_width),
            "X-Window-Center": str(window_center),
        },
    )


async def _process_multiframe_data(instances):
    """Process multiframe data (XA, US, etc.)"""
    if not instances or len(instances) == 0:
        raise HTTPException(status_code=404, detail="No instances found")

    if len(instances) > 1:
        raise HTTPException(
            status_code=404,
            detail="Multiple instances found in series",
        )

    instance = instances[0]
    dcm_handler = BaseDicomHandler(instance.get_pydicom())

    if not dcm_handler:
        raise HTTPException(
            status_code=404,
            detail="No multi-frame instance found in series",
        )

    # Create CArm object from the DICOM parameters
    alpha = dcm_handler.positioner_primary_angle
    beta = dcm_handler.positioner_secondary_angle
    carm = CArm(
        alpha=alpha,
        beta=beta,
        sid=dcm_handler.distance_source_to_detector,
        sod=dcm_handler.distance_source_to_patient,
        imager_pixel_spacing=dcm_handler.imager_pixel_spacing,
        rows=dcm_handler.rows,
        columns=dcm_handler.columns,
        table_top_position=np.array([0, 0, 0]),
    )
    carm = CArmLPSAdapter(carm)

    # Create VTK image data using the centralized utility function
    vtk_image = create_vtk_image_from_multiframe(dcm_handler, carm, column_major=True)

    window_center = dcm_handler.window_center
    window_width = dcm_handler.window_width
    pixel_array = dcm_handler.pixel_array
    assert pixel_array.dtype == np.uint8

    if window_width is None or window_center is None:
        window_width, window_center = compute_optimal_window_level(pixel_array)

    # Write to VTI format
    vti_data = write_vtk_image_to_vti(vtk_image)

    # Include window level info and pixel type info in response headers
    headers = {
        "X-Window-Width": str(window_width),
        "X-Window-Center": str(window_center),
    }

    return Response(
        content=vti_data,
        media_type="application/octet-stream",
        headers=headers,
    )


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
