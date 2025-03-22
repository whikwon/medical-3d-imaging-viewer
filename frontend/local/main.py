from pathlib import Path

import numpy as np
import vtk
from app.core.carm import CArm, CArmLPSAdapter
from app.core.dicom import BaseDicomHandler, VolumeDicomHandler
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

# Global variables for window/level adjustment
window_width = 1500
window_level = 300
ct_actors = []


def window_callback(obj, event):
    """Callback for window width slider"""
    global window_width, window_level, ct_actors
    slider = obj.GetRepresentation()
    window_width = slider.GetValue()

    # Update all CT actors
    for actor in ct_actors:
        actor.GetProperty().SetColorWindow(window_width)
        actor.GetProperty().SetColorLevel(window_level)

    # Render the scene
    obj.GetInteractor().GetRenderWindow().Render()


def level_callback(obj, event):
    """Callback for window level slider"""
    global window_width, window_level, ct_actors
    slider = obj.GetRepresentation()
    window_level = slider.GetValue()

    # Update all CT actors
    for actor in ct_actors:
        actor.GetProperty().SetColorWindow(window_width)
        actor.GetProperty().SetColorLevel(window_level)

    # Render the scene
    obj.GetInteractor().GetRenderWindow().Render()


def main():
    global ct_actors, window_width, window_level

    renderer = VtkRenderer()
    renderer.set_camera(
        position=(0, -500, 0),
        focal_point=(0, 0, 0),
        view_up=(0, 0, 1),
    )
    renderer.add_axes()

    # CT
    dcm_handler = VolumeDicomHandler(CT_DIR_PATH)

    dicom_window_center = dcm_handler.window_center
    dicom_window_width = dcm_handler.window_width
    if dicom_window_center is not None and dicom_window_width is not None:
        window_width = dicom_window_width
        window_level = dicom_window_center

    # Create and add CT image
    ct_image_data = VtkImageCreator.create_ct_image(dcm_handler)

    # Create 3-axis mappers and add to renderer, passing window settings from DICOM
    three_axis_view = VtkImageCreator.create_multi_slice_image_mapper(
        ct_image_data, window_width, window_level
    )

    # Update global variables in case they were changed in create_3_axis_mappers
    window_width = three_axis_view["window_width"]
    window_level = three_axis_view["window_center"]

    # Store CT actors in global variable
    ct_actors = three_axis_view["actors"]

    # Adjust positions of the three slice actors for better visualization
    # Shift the slices to avoid overlapping
    offset = 10  # Offset between planes for better visibility

    # I slice (YZ plane)
    three_axis_view["actors"][0].SetPosition(offset, 0, 0)

    # J slice (XZ plane)
    three_axis_view["actors"][1].SetPosition(0, offset, 0)

    # K slice (XY plane)
    three_axis_view["actors"][2].SetPosition(0, 0, offset)

    # Add all three actors to the renderer
    for actor in three_axis_view["actors"]:
        renderer.add_actor(actor)

    # Add centerline
    ct_label = SlicerMarkupsMrkJson(CT_LABEL_PATH)
    ct_centerline = ct_label.control_points

    renderer.add_centerline(
        points=ct_centerline,
        tube_radius=1.0,
        color=(0.5, 0.5, 0.5),
    )

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
        carm = CArmLPSAdapter(carm)
        # Create VTK image
        image_data = VtkImageCreator.create_xa_image(dcm_handler, carm)

        # Position XA images further away to avoid overlap with CT slices
        renderer.add_image(image_data)

    # Add window/level UI controls
    # Create window width slider
    width_rep = vtk.vtkSliderRepresentation2D()
    width_rep.SetMinimumValue(100)  # Minimum window width
    width_rep.SetMaximumValue(4000)  # Maximum window width
    width_rep.SetValue(window_width)  # Initial value
    width_rep.SetTitleText("Window Width")
    width_rep.GetPoint1Coordinate().SetCoordinateSystemToNormalizedDisplay()
    width_rep.GetPoint1Coordinate().SetValue(0.1, 0.1)
    width_rep.GetPoint2Coordinate().SetCoordinateSystemToNormalizedDisplay()
    width_rep.GetPoint2Coordinate().SetValue(0.4, 0.1)

    width_widget = vtk.vtkSliderWidget()
    width_widget.SetInteractor(renderer.interactor)
    width_widget.SetRepresentation(width_rep)
    width_widget.SetAnimationModeToJump()
    width_widget.AddObserver(vtk.vtkCommand.InteractionEvent, window_callback)
    width_widget.EnabledOn()

    # Create window level slider
    level_rep = vtk.vtkSliderRepresentation2D()
    level_rep.SetMinimumValue(-1000)  # Minimum window level
    level_rep.SetMaximumValue(3000)  # Maximum window level
    level_rep.SetValue(window_level)  # Initial value
    level_rep.SetTitleText("Window Level")
    level_rep.GetPoint1Coordinate().SetCoordinateSystemToNormalizedDisplay()
    level_rep.GetPoint1Coordinate().SetValue(0.6, 0.1)
    level_rep.GetPoint2Coordinate().SetCoordinateSystemToNormalizedDisplay()
    level_rep.GetPoint2Coordinate().SetValue(0.9, 0.1)

    level_widget = vtk.vtkSliderWidget()
    level_widget.SetInteractor(renderer.interactor)
    level_widget.SetRepresentation(level_rep)
    level_widget.SetAnimationModeToJump()
    level_widget.AddObserver(vtk.vtkCommand.InteractionEvent, level_callback)
    level_widget.EnabledOn()

    renderer.reset_camera()
    renderer.start_interaction()


if __name__ == "__main__":
    main()
