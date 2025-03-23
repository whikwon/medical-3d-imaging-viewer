from app.core.carm import CArmLPSAdapter
from app.core.dicom import BaseDicomHandler, VolumeDicomHandler
from app.core.vtk_utils import (
    create_vtk_image_from_multiframe,
    create_vtk_image_from_volume,
)
from vtk_visualization import create_multi_slice_image_mapper


class VtkImageCreator:
    @staticmethod
    def create_ct_image(ct_handler: VolumeDicomHandler):
        """Create a VTK image from DICOM data"""
        return create_vtk_image_from_volume(ct_handler)

    @staticmethod
    def create_xa_image(dcm_handler: BaseDicomHandler, carm: CArmLPSAdapter):
        """Create a VTK image from DICOM data and CArm parameters"""
        return create_vtk_image_from_multiframe(dcm_handler, carm)

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
        return create_multi_slice_image_mapper(image_data, window_width, window_center)
