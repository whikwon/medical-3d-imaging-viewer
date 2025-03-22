import math
import os
import re
from pathlib import Path

import numpy as np
import pydicom
from pydicom.dataset import FileDataset

# https://numpy.org/devdocs/reference/arrays.scalars.html#sized-aliases
DATA_VAL_REPR_MAPPPER = {
    0: np.uint16,
    1: np.int16,
    2: np.float32,
    3: np.float64,
    4: np.int64,
}

# https://pydicom.github.io/pydicom/stable/guides/element_value_types.html?highlight=representation
VR_LIST_VM_NOT_GREATER_THAN_ONE = [
    "LT",
    "OB",
    "OD",
    "OF",
    "OL",
    "OW",
    "ST",
    "UN",
    "UR",
    "UT",
]

NAME2TAG = {
    "AnatomicalOrientationType": "0x00102210",
    "SeriesDescription": "0x0008103e",
    "DataValueRepresentation": "0x50000103",
    "MinimumCoordinateValue": "0x50000104",
    "MaximumCoordinateValue": "0x50000105",
    "CurveDimensions": "0x50000005",
    "NumberOfPoints": "0x50000010",
    "CurveDataDescriptor": "0x50000110",
    "CoordinateStartValue": "0x50000112",
    "CoordinateStepValue": "0x50000114",
    "CurveData": "0x50003000",
    "PixelData": "0x7fe00010",
    "PixelSpacing": "0x280030",
    "CineRate": "0x00180040",
    "SliceThickness": "0x00180050",
    "StudyDate": "0x00080020",
    "SOPInstanceUID": "0x00080018",
    "StudyInstanceUID": "0x0020000D",
    "SpacingBetweenSlices": "0x00180088",
    "Manufacturer": "0x00080070",
    "Modality": "0x00080060",
    "NumberOfFrames": "0x00280008",
    "ImagerPixelSpacing": "0x00181164",
    "IVUSPullbackRate_Philips": "0x00291000",
    "TypeOfData": "0x50000020",
    "AcquisitionDateTime": "0x0008002a",
    "AcquisitionTime": "0x00080032",
    "AcquisitionDate": "0x00080022",
    "ContentTime": "0x00080033",
    "IVUSPullbackRate": "0x001803101",
    "Rows": "0x00280010",
    "Columns": "0x00280011",
    "DistanceSourceToPatient": "0x00181111",
    "DistanceSourceToDetector": "0x00181110",
    "WindowCenter": "0x00281050",
    "WindowWidth": "0x00281051",
    "PositionerPrimaryAngle": "0x00181510",
    "PositionerSecondaryAngle": "0x00181511",
    "TableTopVerticalPosition": "0x300a0128",
    "TableTopLongitudinalPosition": "0x300a0129",
    "TableTopLateralPosition": "0x300a012a",
    "SliceLocation": "0x00201041",
    "ImagePositionPatient": "0x00200032",
    "ImageOrientationPatient": "0x00200037",
    "TableHeight": "0x00181130",
    "PatientPosition": "0x00185100",
    "PhilipsFieldOfView": "0x20031003",
    "PatientID": "0x00100020",
}


def read_dicom_element_value(dcm, elem_name, type_cast_to=None):
    def _to_list(value, type_cast_to=None):
        value = list(value)
        if type_cast_to is not None:
            value = [type_cast_to(v) for v in value]
        return value

    assert elem_name in NAME2TAG.keys()

    tag = NAME2TAG[elem_name]
    try:
        element = dcm[tag]
    except KeyError:
        element = None
    if element is not None:
        vr = element.VR
        value = element.value
        if vr == "SQ":
            return _to_list(value, type_cast_to)
        else:
            if vr not in VR_LIST_VM_NOT_GREATER_THAN_ONE:
                vm = element.VM
                if vm > 1:
                    return _to_list(value, type_cast_to)
            if type_cast_to is not None:
                value = type_cast_to(value)
        return value


class BaseDicomHandler:
    def __init__(self, dcm_or_path: Path | str | FileDataset):
        self.dcm_path = None
        if isinstance(dcm_or_path, (Path, str)):
            self.dcm_path = dcm_or_path
            self.dcm = pydicom.dcmread(dcm_or_path)
        else:
            self.dcm = dcm_or_path

    def __repr__(self):
        return str(self.dcm)

    @property
    def series_description(self):
        """str: Long String"""
        return read_dicom_element_value(self.dcm, "SeriesDescription")

    @property
    def study_instance_uid(self):
        """str: Unique Identifier"""
        return read_dicom_element_value(self.dcm, "StudyInstanceUID")

    @property
    def sop_instance_uid(self):
        """str: Unique Identifier"""
        return read_dicom_element_value(self.dcm, "SOPInstanceUID")

    @property
    def study_date(self):
        """str: Date"""
        return read_dicom_element_value(self.dcm, "StudyDate")

    @property
    def pixel_array(self):
        """
        np.ndarray

        - IVUS(3-channel), CAG(1-channel)
        - IVUS의 1번째 channel에 촬영 이미지가 있고 2, 3번째 channel에는 눈금자가 그려져있다.
        """
        return self.dcm.pixel_array

    @property
    def imager_pixel_spacing(self):
        """
        float, list[float] or list[int]: Decimal String
        """
        return read_dicom_element_value(self.dcm, "ImagerPixelSpacing", float)

    @property
    def number_of_frames(self):
        """int: Integer String"""
        return read_dicom_element_value(self.dcm, "NumberOfFrames", int)

    @property
    def cine_rate(self):
        """float: Integer String

        Number of frames per second.
        """
        return read_dicom_element_value(self.dcm, "CineRate", float)

    @property
    def rows(self):
        """int: Unsigned Short"""
        return read_dicom_element_value(self.dcm, "Rows")

    @property
    def columns(self):
        """int: Unsigned Short"""
        return read_dicom_element_value(self.dcm, "Columns")

    @property
    def pixel_spacing(self):
        """
        float, list[float] or list[int]: Decimal String

        The first value is the row spacing in mm, that is the spacing between the centers of adjacent rows, or vertical spacing.
        The second value is the column spacing in mm, that is the spacing between the centers of adjacent columns, or horizontal spacing.

        Notes
        -----
        - mm/pixel, IVUS 눈금은 pixel spacing 매칭이 되며 10x10mm 영역을 500x500px으로 나타낸다.

        References
        ----------
        .. [1] https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_10.7.html#sect_10.7.1.3
        """
        return read_dicom_element_value(self.dcm, "PixelSpacing", float)

    @property
    def manufacturer(self):
        """str: Long String"""
        return read_dicom_element_value(self.dcm, "Manufacturer")

    @property
    def modality(self):
        """str: Code String"""
        return read_dicom_element_value(self.dcm, "Modality")

    @property
    def data_value_representation(self):
        """int: Unsigned Short"""
        return read_dicom_element_value(self.dcm, "DataValueRepresentation")

    @property
    def curve_dimensions(self):
        """int: Unsigned Short"""
        return read_dicom_element_value(self.dcm, "CurveDimensions")

    @property
    def curve_data_descriptor(self):
        """int or list[int]: Unsigned Short"""
        return read_dicom_element_value(self.dcm, "CurveDataDescriptor")

    @property
    def coordinate_start_value(self):
        """int or list[int]: Unsigned Short"""
        return read_dicom_element_value(self.dcm, "CoordinateStartValue")

    @property
    def coordinate_step_value(self):
        """int or list[int]: Unsigned Short"""
        return read_dicom_element_value(self.dcm, "CoordinateStepValue")

    @property
    def number_of_points(self):
        """int: Unsigned Short

        Number of data points in curve.
        """
        return read_dicom_element_value(self.dcm, "NumberOfPoints")

    @property
    def content_time(self):
        """str: Time"""
        return read_dicom_element_value(self.dcm, "ContentTime")

    @property
    def acquisition_date(self):
        """str: Date Time"""
        date = read_dicom_element_value(self.dcm, "AcquisitionDate")
        if date is None:
            date_time = read_dicom_element_value(self.dcm, "AcquisitionDateTime")
            if date_time is not None:
                date = date_time[:8]
        return date

    @property
    def acquisition_time(self):
        """str: Date Time"""
        time = read_dicom_element_value(self.dcm, "AcquisitionTime")
        if time is None:
            date_time = read_dicom_element_value(self.dcm, "AcquisitionDateTime")
            if date_time is not None:
                time = date_time[8:]
        return time

    @property
    def acquisition_date_time(self):
        """str: Date Time"""
        date_time = read_dicom_element_value(self.dcm, "AcquisitionDateTime")
        if date_time is None:
            date = read_dicom_element_value(self.dcm, "AcquisitionDate")
            time = read_dicom_element_value(self.dcm, "AcquisitionTime")
            if date is not None:
                if time is not None:
                    date_time = date + time
                else:
                    date_time = date
        return date_time

    @property
    def ivus_pullback_rate(self):
        """
        float, list[float] or list[int]: Decimal String

        References
        ----------
        .. [1] https://www.documents.philips.com/doclib/enc/fetch/2000/4504/577242/577256/588723/5144873/5144488/5144772/DICOM_Conformance_Statement_Philips_IntraSight_1.0.pdf
        """
        pullback_rate = read_dicom_element_value(self.dcm, "IVUSPullbackRate", float)
        if pullback_rate is None:
            if self.manufacturer.lower().startswith("volcano"):
                return read_dicom_element_value(
                    self.dcm, "IVUSPullbackRate_Philips", float
                )

    @property
    def type_of_data(self):
        """str: Code String"""
        return read_dicom_element_value(self.dcm, "TypeOfData")

    @property
    def curve_data(self):
        """
        np.ndarray: Other Byte or Other word

        References
        ----------
        .. [1] http://dicom.nema.org/dicom/2004/04_03pu.pdf
        """
        curve_data = read_dicom_element_value(self.dcm, "CurveData")

        if curve_data is not None:
            data_val_repr = self.data_value_representation
            number_of_pts = self.number_of_points
            type_to = DATA_VAL_REPR_MAPPPER[data_val_repr]
            curve_data = np.frombuffer(curve_data, dtype=type_to)
            curve_dims = self.curve_dimensions
            curve_data_descriptor = self.curve_data_descriptor

            if curve_data_descriptor is not None:
                ndims_wo_interval = curve_dims - sum(
                    [i == 0 for i in curve_data_descriptor]
                )

                if ndims_wo_interval < curve_dims:
                    if isinstance(self.coordinate_start_value, list):
                        coord_start_val = self.coordinate_start_value[0]
                    else:
                        coord_start_val = self.coordinate_start_value

                    if isinstance(self.coordinate_step_value, list):
                        coord_step_val = self.coordinate_step_value[0]
                    else:
                        coord_step_val = self.coordinate_step_value

                    # dtype=type_to를 넣어줘야 하는데, overflow 일어나는 경우가 있어서 제외.
                    interval_data = np.array(
                        [
                            coord_start_val + coord_step_val * i
                            for i in range(number_of_pts)
                        ]
                    )
            else:
                ndims_wo_interval = curve_dims
                interval_data = None

            curve_data = curve_data.reshape(-1, ndims_wo_interval)
            if interval_data is not None:
                curve_data = np.concatenate(
                    [interval_data.reshape(-1, 1), curve_data], axis=-1
                )
        return curve_data

    @property
    def has_ecg_signal(self):
        return (
            self.curve_data is not None
            and self.cine_rate is not None
            and self.type_of_data == "ECG"
        )

    @property
    def ecg_signal(self):
        if self.has_ecg_signal:
            sampling_rate = int(
                self.number_of_points / self.number_of_frames * self.cine_rate
            )
            curve_data = self.curve_data
        else:
            sampling_rate = None
            curve_data = None
        return curve_data, sampling_rate

    @property
    def distance_source_to_patient(self):
        """
        float: Decimal String
        """
        return read_dicom_element_value(self.dcm, "DistanceSourceToPatient", float)

    @property
    def distance_source_to_detector(self):
        """
        float: Decimal String
        """
        return read_dicom_element_value(self.dcm, "DistanceSourceToDetector", float)

    @property
    def window_center(self):
        """
        float: Decimal String
        """
        return read_dicom_element_value(self.dcm, "WindowCenter", float)

    @property
    def window_width(self):
        """
        float: Decimal String
        """
        return read_dicom_element_value(self.dcm, "WindowWidth", float)

    @property
    def positioner_primary_angle(self):
        """
        float: Decimal String
        """
        return read_dicom_element_value(self.dcm, "PositionerPrimaryAngle", float)

    @property
    def positioner_secondary_angle(self):
        """
        float: Decimal String
        """
        return read_dicom_element_value(self.dcm, "PositionerSecondaryAngle", float)

    @property
    def field_of_view(self):
        if self.manufacturer.lower().startswith("philips"):
            return read_dicom_element_value(self.dcm, "PhilipsFieldOfView", str)

    @property
    def patient_id(self):
        """
        str: Long String
        """
        return read_dicom_element_value(self.dcm, "PatientID")

    @property
    def table_top_position(self):
        # https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.19.6.11.html
        if self.manufacturer.lower().startswith("philips"):
            try:
                dataset = self.dcm["0x2003102e"][0]
                lateral = read_dicom_element_value(
                    dataset, "TableTopLateralPosition", float
                )
                longitudinal = read_dicom_element_value(
                    dataset, "TableTopLongitudinalPosition", float
                )
                vertical = read_dicom_element_value(
                    dataset, "TableTopVerticalPosition", float
                )
                return [lateral, -vertical, longitudinal]
            except KeyError:
                return None

    @property
    def slice_location(self):
        """
        float: Decimal String
        """
        return read_dicom_element_value(self.dcm, "SliceLocation", float)

    @property
    def image_position_patient(self):
        """list[float]: Decimal String

        The x, y, and z coordinates of the upper left hand corner (center of the first voxel transmitted) of the image, in mm.

        If Anatomical Orientation Type (0010,2210) is absent or has a value of BIPED, the x-axis is increasing to the left hand side of the patient.
        The y-axis is increasing to the posterior side of the patient. The z-axis is increasing toward the head of the patient.

        Notes
        -----
        TableHeight can be a reference point. (Siemens SOMATOM Force)

        References
        ----------
        .. [1] https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.2.html#sect_C.7.6.2.1.1
        """
        return read_dicom_element_value(self.dcm, "ImagePositionPatient", float)

    @property
    def anatomical_orientation_type(self):
        """str: Code String"""
        return read_dicom_element_value(self.dcm, "AnatomicalOrientationType")

    @property
    def spacing_between_slices(self):
        """
        float, list[float] or list[int]: Decimal String

        References
        ----------
        .. [1] https://stackoverflow.com/questions/14930222/how-to-calculate-space-between-dicom-slices-for-mpr
        """
        return read_dicom_element_value(self.dcm, "SpacingBetweenSlices", float)

    @property
    def slice_thickness(self):
        """
        float, list[float] or list[int]: Decimal String
        """
        return read_dicom_element_value(self.dcm, "SliceThickness", float)

    @property
    def image_orientation_patient(self):
        """list[float]: Decimal String

        Image Orientation (Patient) (0020,0037) specifies the direction cosines of the first row and the first column with respect to the patient.

        References
        ----------
        .. [1] https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.2.html#sect_C.7.6.2.1.1
        """
        return read_dicom_element_value(self.dcm, "ImageOrientationPatient", float)

    @property
    def table_height(self):
        """float: Decimal String"""
        return read_dicom_element_value(self.dcm, "TableHeight", float)

    @property
    def patient_position(self):
        """str: Code String"""
        return read_dicom_element_value(self.dcm, "PatientPosition")

    @property
    def spacing(self):
        """
        np.ndarray
        """
        pixel_spacing = self.pixel_spacing
        if not isinstance(pixel_spacing, list):
            pixel_spacing = [pixel_spacing, pixel_spacing]
        if self.spacing_between_slices is not None:
            spacing_between_slices = self.spacing_between_slices
        elif self.slice_thickness is not None:
            spacing_between_slices = self.slice_thickness
        else:
            raise ValueError("Spacing between slices is not defined")
        return pixel_spacing + [spacing_between_slices]


class VolumeDicomHandler:
    def __init__(self, dir_path_or_dcms: Path | str | list[FileDataset]):
        self.dcm_dir_path = None
        if isinstance(dir_path_or_dcms, (Path, str)):
            if not isinstance(dir_path_or_dcms, Path):
                self.dcm_dir_path = Path(dir_path_or_dcms)
            else:
                self.dcm_dir_path = dir_path_or_dcms
            self.dcm_series = self.load_dicom_series()
        else:
            self.dcm_series = [BaseDicomHandler(dcm) for dcm in dir_path_or_dcms]
        self.dcm_series = self._sort_dicom_datasets(self.dcm_series)
        self.ref_dcm = self.dcm_series[0]
        self.identity_map = {}

    @property
    def columns(self):
        return self.ref_dcm.columns

    @property
    def rows(self):
        return self.ref_dcm.rows

    @property
    def spacing(self):
        return self.ref_dcm.spacing

    @property
    def spacing_between_slices(self):
        return self.ref_dcm.spacing_between_slices

    @property
    def slice_thickness(self):
        return self.ref_dcm.slice_thickness

    @property
    def image_orientation_patient(self):
        return self.ref_dcm.image_orientation_patient

    def load_dicom_series(self):
        """
        Load a DICOM series from the directory provided during object initialization.

        Returns:
            list: List of DICOM objects representing the series, sorted by anatomical position.
        """
        dcm_path_list = list(self.dcm_dir_path.glob("*.dcm"))
        dcm_series = []
        for dcm_path in dcm_path_list:
            dcm_series.append(BaseDicomHandler(dcm_path))
        return dcm_series

    def _sort_dicom_datasets(self, dicom_datasets):
        """
        Sort DICOM datasets by anatomical position.

        Args:
            dicom_datasets: List of DICOM datasets to sort

        Returns:
            list: Sorted list of DICOM datasets
        """
        position_info = []

        for i, dataset in enumerate(dicom_datasets):
            if dataset.slice_location is not None:
                position = dataset.slice_location
            elif dataset.image_position_patient is not None:
                position = dataset.image_position_patient[2]
            else:
                position = i

            position_info.append((position, i))

        position_info.sort(key=lambda x: x[0])
        sorted_datasets = [dicom_datasets[idx] for _, idx in position_info]
        return sorted_datasets

    def __getitem__(self, idx):
        return self.dcm_series[idx]

    def __repr__(self):
        return f"{self.modality} image DICOM data, spacing({self.spacing}), voxel({self.voxel_array.shape}, {self.voxel_array.dtype})"

    @property
    def number_of_slices(self):
        return len(self.dcm_series)

    @property
    def voxel_array(self):
        """
        np.ndarray
        """
        if "voxel_array" in self.identity_map:
            return self.identity_map["voxel_array"]
        pixel_array_list = []
        for dcm in self.dcm_series:
            pixel_array_list.append(dcm.pixel_array)
        voxel_array = np.stack(pixel_array_list, axis=-1)
        self.identity_map.update({"voxel_array": voxel_array})
        return voxel_array

    @property
    def volume_center_position_mm(self):
        """
        Volume center position in mm

        Notes
        -----
        TableHeight can be a reference point. (Siemens SOMATOM Force)
        """
        return self.voxel_to_rcs_coordinate(self.volume_center_position_px)

    @property
    def volume_center_position_px(self):
        """
        Volume center position in px

        Notes
        -----
        TableHeight can be a reference point. (Siemens SOMATOM Force)
        """
        return np.array(
            [
                (self.columns - 1) / 2,
                (self.rows - 1) / 2,
                self.number_of_slices / 2,
            ]
        )

    @property
    def gating_delay(self):
        delay = re.findall("(\d{1,3}(?:\.\d+)?)\s{0,1}%", self.series_description)
        if len(delay) == 1:
            return float(delay[0]) / 100
        return None

    def get_image_position_patient(self, idx: int | float):
        if isinstance(idx, int):
            return self.dcm_series[idx].image_position_patient
        else:
            frac_part, int_part = math.modf(idx)
            int_part = int(int_part)
            if frac_part > 0:
                x1, y1, z1 = self.dcm_series[int_part].image_position_patient
                x2, y2, z2 = self.dcm_series[int_part + 1].image_position_patient
                return (
                    x1 + (x2 - x1) * frac_part,
                    y1 + (y2 - y1) * frac_part,
                    z1 + (z2 - z1) * frac_part,
                )
            else:
                return self.dcm_series[int_part].image_position_patient

    def voxel_to_rcs_coordinate(self, voxel_coordinate):
        """
        See Equation C.7.6.2.1-1.

        DICOM's RCS(Reference Coordinate System) is LPS(Left-Posterior-Superior).

        References
        ----------
        .. [1] https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.2.html#sect_C.7.6.2.1.1
        .. [2] https://blog.redbrickai.com/blog-posts/introduction-to-dicom-coordinate
        """
        if self.ref_dcm.anatomical_orientation_type == "QUADRUPED":
            raise NotImplementedError("QUADRUPED is not supported yet")

        x, y, z = voxel_coordinate

        pixel_spacing = self.ref_dcm.pixel_spacing
        image_orientation = np.array(self.ref_dcm.image_orientation_patient)
        image_position = np.array(self.get_image_position_patient(z))  # [S_x, S_y, S_z]

        M = np.stack(
            [
                image_orientation[:3] * pixel_spacing[1],
                image_orientation[3:] * pixel_spacing[0],
                np.zeros((3,)),
                image_position,
            ],
            axis=-1,
        )
        return (M @ np.array([[x, y, 0, 1]]).T).T[0]
