from pathlib import Path

import numpy as np
from app.core.carm import CArm
from app.core.coordinate import CoordinateSystem, PatientCoordinates
from app.core.dicom import BaseDicomHandler, CtImageDicomHandler
from app.core.slicer_parser import SlicerMarkupsMrkJson
from vtk_image_creator import VtkImageCreator
from vtk_renderer import VtkRenderer

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PATIENT_ID = "12325322"
CT_DIR_PATH = DATA_DIR / "data" / PATIENT_ID / "20200827" / "CT" / "03"
XA_DIR_PATH = DATA_DIR / "data" / PATIENT_ID / "20201101" / "XA"
CT_LABEL_PATH = (
    DATA_DIR
    / "label"
    / PATIENT_ID
    / "20200827"
    / "CT"
    / "03"
    / "centerline_rca_20250218.mrk.json"
)
XA_SERIES_NO_LIST = [8, 10]


def main():
    renderer = VtkRenderer()
    renderer.set_camera(
        position=(0, 0, -100),
        focal_point=(0, 0, 0),
        view_up=(0, -1, 0),
    )
    renderer.add_axes()

    # XA
    for series_no in XA_SERIES_NO_LIST:
        dcm_handler = BaseDicomHandler(XA_DIR_PATH / f"{series_no:03d}.dcm")
        carm = CArm(
            dcm_handler.positioner_primary_angle,
            dcm_handler.positioner_secondary_angle,
            dcm_handler.distance_source_to_detector,
            dcm_handler.distance_source_to_patient,
            dcm_handler.imager_pixel_spacing,
            dcm_handler.rows,
            dcm_handler.columns,
            np.array([0, 0, 0]),
            # dcm_handler.table_top_position,
        )
        # Create VTK image
        image_data = VtkImageCreator.create_xa_image(dcm_handler, carm)
        renderer.add_image(image_data)

    # CT
    dcm_handler = CtImageDicomHandler(CT_DIR_PATH)
    ct_center_position = PatientCoordinates(
        dcm_handler.volume_center_position_mm, CoordinateSystem.LPS
    )

    # Create and add CT image
    ct_image_data = VtkImageCreator.create_ct_image(dcm_handler)
    renderer.add_image(ct_image_data)

    # Add centerline
    ct_label = SlicerMarkupsMrkJson(CT_LABEL_PATH)
    control_points = ct_label.control_points
    ct_centerline = control_points.to_world("HFS")
    # ct_centerline = (control_points - ct_center_position).to_world("HFS")

    renderer.add_centerline(
        points=ct_centerline,
        tube_radius=1.0,
        color=(0.5, 0.5, 0.5),
    )

    renderer.reset_camera()
    renderer.start_interaction()


if __name__ == "__main__":
    main()
