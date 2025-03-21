from app.core.carm import CArm
from app.core.dicom import BaseDicomHandler
from pyorthanc import Orthanc, Series, Study


class DicomLoader:
    def __init__(self, orthanc_url="http://localhost:8042"):
        self.client = Orthanc(orthanc_url)

    def load_study(self, study_id):
        """Load a study by ID from Orthanc"""
        return Study(study_id, self.client)

    def load_series(self, series_id):
        """Load a series by ID from Orthanc"""
        return Series(series_id, self.client)

    def load_dicom_data(self, study_id, series_index=0):
        """Load DICOM data from a study and return handler and CArm objects"""
        study = self.load_study(study_id)
        series = self.load_series(study.series[series_index].id_)
        dcm = series.instances[0].get_pydicom()

        # Create DICOM handler
        dcm_handler = BaseDicomHandler(dcm)

        # Get spacing
        imager_pixel_spacing = dcm_handler.imager_pixel_spacing
        spacing = [imager_pixel_spacing[0], imager_pixel_spacing[1], 1.0]

        # Create CArm object
        carm = CArm(
            alpha=dcm_handler.positioner_primary_angle,
            beta=dcm_handler.positioner_secondary_angle,
            sid=dcm_handler.distance_source_to_detector,
            sod=dcm_handler.distance_source_to_patient,
            imager_pixel_spacing=spacing,
            rows=dcm_handler.rows,
            columns=dcm_handler.columns,
            table_top_position=[0, 0, 0],
        )

        return dcm_handler, carm
