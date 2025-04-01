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
from app.core.config import settings
from app.core.dicom import BaseDicomHandler, VolumeDicomHandler
from app.core.intensity_transform import compute_optimal_window_level
from app.core.orthanc import orthanc_client
from app.core.slicer_parser import SlicerMarkupsMrkJson
from app.core.vtk_utils import (
    create_vtk_image_from_multiframe,
    create_vtk_image_from_volume,
    write_vtk_image_to_vti,
)
from app.schemas.label import Centerline

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


@router.get("/series/{series_id}/label_list")
async def get_series_label_list(series_id: str):
    """Get the list of available label filenames for a series."""
    try:
        series = Series(series_id, orthanc_client.client)
        series_info = series.get_main_information()
        series_uid = series_info.get("MainDicomTags", {}).get("SeriesInstanceUID")

        if not series_uid:
            raise HTTPException(
                status_code=404,
                detail="Could not find Study or Series UID for the series.",
            )

        # Construct the expected directory path for labels for this series
        # Assumes structure: settings.LABEL_DIR_PATH / study_uid / series_uid / *.mrk.json (or other extensions)
        series_label_dir = settings.LABEL_DIR_PATH / series_uid
        logger.info(f"Searching for labels in: {series_label_dir}")

        if not series_label_dir.is_dir():
            logger.warning(f"Label directory not found: {series_label_dir}")
            return []  # Return empty list if directory doesn't exist

        # Return the full paths as strings
        label_files = [str(p) for p in series_label_dir.glob("*") if p.is_file()]
        return label_files

    except Exception as e:
        logger.error(f"Failed to get label list for series {series_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve label list: {str(e)}",
        )


@router.get("/series/{series_id}/labels/{label_filename}")
async def get_series_label_content(series_id: str, label_filename: str):
    """Get the content of a specific label file for a series."""
    try:
        series = Series(series_id, orthanc_client.client)
        series_info = series.get_main_information()
        # Use DICOM UIDs for robust path construction
        series_uid = series_info.get("MainDicomTags", {}).get("SeriesInstanceUID")
        instances = series.instances

        # Get all DICOM datasets
        dicom_datasets = [instance.get_pydicom() for instance in instances]
        ct_handler = VolumeDicomHandler(dicom_datasets)

        if not series_uid:
            raise HTTPException(
                status_code=404,
                detail="Could not find Study or Series UID for the series.",
            )

        # Construct the full path to the specific label file
        label_file_path = settings.LABEL_DIR_PATH / series_uid / label_filename
        logger.info(f"Attempting to read label file: {label_file_path}")

        if not label_file_path.is_file():
            logger.error(f"Label file not found: {label_file_path}")
            raise HTTPException(
                status_code=404, detail=f"Label file '{label_filename}' not found."
            )

        # Assuming .mrk.json files are JSON, read and return as JSON
        # Add handling for other file types if necessary
        if (
            label_file_path.suffix.lower() == ".json"
            or label_file_path.suffix.lower() == ".mrk"
        ):  # Handle .mrk.json too if needed
            data = SlicerMarkupsMrkJson(label_file_path).control_points
            data["position"] -= ct_handler.volume_center_position_mm
            data["radius"] = np.linspace(0.5, 3, len(data["position"])).tolist()
            data["position"] = data["position"].tolist()
            data["orientation"] = data["orientation"].tolist()
            label = Centerline(
                filename=label_filename,
                data=data,
                visible=True,
                color=[0.5, 0.5, 1.0],
                opacity=1.0,
                id=label_filename,
                seriesId=series_id,
            )
            return label.model_dump()
        else:
            # For non-JSON files, you might return differently, e.g., FileResponse
            # For now, raise an error if it's not recognized JSON
            logger.error(f"Unsupported label file type: {label_file_path.suffix}")
            raise HTTPException(
                status_code=415,
                detail="Unsupported label file type. Only JSON (.json, .mrk.json) is currently supported.",
            )

    except Exception as e:
        logger.error(
            f"Failed to get label content for series {series_id}, file {label_filename}: {e}"
        )
        # Avoid leaking detailed exception info unless needed for debugging
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve label content.",
        )


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
    # dcm_handler.table_top_position is in LPS, but the CArm constructor expects ILA
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
