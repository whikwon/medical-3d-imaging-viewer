from dataclasses import dataclass

import numpy as np
from scipy.spatial.transform import Rotation

from app.core.coordinate import CoordinateSystem, TransformationMatrix

from .camera import (
    camera_to_image,
    camera_to_world,
    create_intrinsic_matrix,
    image_to_camera,
    world_to_camera,
)


@dataclass
class CArmParams:
    isocenter: list[float]
    alpha: float
    beta: float
    sid: float
    sod: float
    imager_pixel_spacing: list[float]
    rows: int
    columns: int
    table_top_position: list[float]


class CArm:
    def __init__(
        self,
        alpha: float,
        beta: float,
        sid: float,
        sod: float,
        imager_pixel_spacing: list[float] | np.ndarray,
        rows: int,
        columns: int,
        table_top_position: np.ndarray,
        sisod: float | None = None,
    ):
        """
        Definition of Positioner primary and secondary angles
        - https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.8.7.5.html
        - alpha: rotate around the z-axis, LAO(+), RAO(-)
        - beta: rotate around the -x-axis, CRAN(+), CAUD(-)

        Isocenter coordinate system: LPS (Left-Posterior-Superior)
        - https://dicom.nema.org/medical/Dicom/2016e/output/chtml/part03/sect_C.8.19.6.13.html
        - To make it easier to handle, the world origin is set to the isocenter.

        C-arm coordinate system: ILA (Inferior-Left-Anterior)
        - https://www.researchgate.net/figure/Parameterization-of-the-projection-system-The-C-arm-imaging-system-is-composed-of-an_fig2_263050498
        - alpha: rotate around the x-axis, LAO(-), RAO(+)
        - beta: rotate around the y-axis, CRAN(-), CAUD(+)

        Since a stationary CAG is given, it is assumed that the c-arm moves in the opposite direction of the table.
        """
        self.alpha = alpha
        self.beta = beta
        self.sid = sid
        self.imager_pixel_spacing = imager_pixel_spacing
        self.rows = rows
        self.columns = columns
        self.sod = sod
        self.table_top_position = table_top_position  # relative position
        if sisod is None:
            self.sisod = sod
        else:
            self.sisod = sisod
        self.initialize()
        self.rotate(self.alpha, self.beta)

    def initialize(self):
        # all points below are in ILA
        self.target_object = None
        self.isocenter_pt = np.array([0, 0, 0])
        self.init_source_basis_vector_x = np.array([1, 0, 0])
        self.init_source_basis_vector_y = np.array([0, 1, 0])
        self.init_source_basis_vector_z = np.array([0, 0, 1])
        self.init_source_pt = -self.init_source_basis_vector_z * self.sisod
        self.detector_center_pt_2d = np.array(
            [(self.columns - 1) / 2, (self.rows - 1) / 2]
        )

    @property
    def params(self):
        return CArmParams(
            self.isocenter_pt,
            self.alpha,
            self.beta,
            self.sid,
            self.sod,
            self.imager_pixel_spacing,
            self.rows,
            self.columns,
            self.table_top_position,
        )

    @property
    def rotation_translation_params(self):
        return [self.alpha, self.beta, *self.table_top_position]

    def with_updates(self, alpha, beta, table_top_position):
        return CArm(
            alpha,
            beta,
            self.sid,
            self.sod,
            self.imager_pixel_spacing,
            self.rows,
            self.columns,
            table_top_position,
            self.sisod,
        )

    @property
    def source_basis_vector_x(self):
        return self.rotation @ self.init_source_basis_vector_x

    @property
    def source_basis_vector_y(self):
        return self.rotation @ self.init_source_basis_vector_y

    @property
    def source_basis_vector_z(self):
        return self.rotation @ self.init_source_basis_vector_z

    @property
    def detector_size(self):
        """
        shape (h, w) of detector
        """
        return [
            self.rows * self.imager_pixel_spacing[0],
            self.columns * self.imager_pixel_spacing[1],
        ]

    @property
    def intrinsic_matrix(self):
        return create_intrinsic_matrix(
            self.sid, self.imager_pixel_spacing, self.detector_center_pt_2d
        )

    @property
    def extrinsic_matrix(self):
        """world to camera"""
        R = self.rotation.inv().as_matrix()
        T = R @ -self.table_top_position_adjusted_source_pt.reshape(-1, 1)
        return np.concatenate([R, T], axis=1)

    @property
    def projection_matrix(self):
        return self.intrinsic_matrix @ self.extrinsic_matrix

    @property
    def rotation(self):
        return Rotation.from_euler(
            "xyz", angles=[-self.alpha, -self.beta, 0], degrees=True
        ).as_matrix()

    @property
    def table_top_position_adjusted_source_pt(self):
        return self.source_pt - self.table_top_position

    @property
    def detector_center_pt_3d(self):
        return (
            self.table_top_position_adjusted_source_pt
            + self.sid * self.source_basis_vector_z
        )

    def move_detector(self, sid: float, imager_pixel_spacing: list[float]):
        # check if imager_pixel_spacing is changed when detector is moved
        self.sid = sid
        self.imager_pixel_spacing = imager_pixel_spacing

    def set_target_object(self, target_object):
        self.target_object = target_object

    def rotate(self, alpha: float, beta: float):
        """
        Parameters
        ----------
        alpha: float
            positioner primary angle in radian
        beta: float
            positioner secondary angle in radian
        """
        self.alpha = alpha
        self.beta = beta
        self.source_pt = self.rotation @ self.init_source_pt

    def table_move(self, table_top_position):
        self.table_top_position = table_top_position

    def capture(self, obj=None):
        if obj is None:
            if self.target_object is None:
                raise ValueError(
                    "Set target object using `set_target_object` before capturing."
                )
            else:
                obj = self.target_object
        pts_2d = camera_to_image(
            world_to_camera(
                obj,
                self.table_top_position_adjusted_source_pt,
                np.linalg.inv(self.rotation),
            ),
            self.intrinsic_matrix,
        )
        return pts_2d

    def image_to_world(self, pts_2d: np.ndarray):
        return camera_to_world(
            image_to_camera(pts_2d, self.intrinsic_matrix, self.sid),
            self.table_top_position_adjusted_source_pt,
            self.rotation,
        )

    @property
    def image_origin(self):
        return (
            self.detector_center_pt_3d
            - self.source_basis_vector_x * self.detector_size[0] / 2
            - self.source_basis_vector_y * self.detector_size[1] / 2
        )


class CArmLPSAdapter:
    """
    Adapter to convert CArm to LPS coordinate system
    """

    ILA_TO_LPS = TransformationMatrix.get_coordinate_transform_matrix(
        CoordinateSystem.ILA, CoordinateSystem.LPS
    )

    def __init__(self, carm: CArm):
        self.carm = carm

    def capture(self, obj=None):
        if obj is not None:
            # Convert object from LPS to ILA for capture
            obj_ila = self.LPS_to_ILA(obj)
            return self.carm.capture(obj_ila)
        return self.carm.capture()

    def LPS_to_ILA(self, points):
        """Convert points from LPS to ILA coordinate system"""
        return np.linalg.inv(self.ILA_TO_LPS) @ points

    def ILA_to_LPS(self, points):
        """Convert points from ILA to LPS coordinate system"""
        return self.ILA_TO_LPS @ points

    @property
    def source_basis_vector_x(self):
        return self.ILA_TO_LPS @ self.carm.source_basis_vector_x

    @property
    def source_basis_vector_y(self):
        return self.ILA_TO_LPS @ self.carm.source_basis_vector_y

    @property
    def source_basis_vector_z(self):
        return self.ILA_TO_LPS @ self.carm.source_basis_vector_z

    @property
    def detector_size(self):
        return self.carm.detector_size

    @property
    def source_pt(self):
        """Return source point in LPS coordinates"""
        return self.ILA_TO_LPS @ self.carm.table_top_position_adjusted_source_pt

    @property
    def detector_center_pt_3d(self):
        """Return detector center point in LPS coordinates"""
        return self.ILA_TO_LPS @ self.carm.detector_center_pt_3d

    @property
    def rotation(self):
        """Return rotation matrix in LPS coordinates"""
        return self.ILA_TO_LPS @ self.carm.rotation

    @property
    def intrinsic_matrix(self):
        """Pass through to CArm's intrinsic matrix"""
        return self.carm.intrinsic_matrix

    @property
    def extrinsic_matrix(self):
        """Return extrinsic matrix in LPS coordinates"""
        rotation_matrix = self.rotation
        if isinstance(rotation_matrix, Rotation):
            R = rotation_matrix.inv().as_matrix()
        else:
            R = np.linalg.inv(rotation_matrix)
        T = R @ -self.source_pt_lps.reshape(-1, 1)
        return np.concatenate([R, T], axis=1)

    @property
    def projection_matrix(self):
        """Return projection matrix in LPS coordinates"""
        return self.intrinsic_matrix @ self.extrinsic_matrix

    def image_to_world(self, pts_2d: np.ndarray):
        """Convert image points to world points in LPS coordinates"""
        pts_world_ila = self.carm.image_to_world(pts_2d)
        return self.ILA_TO_LPS @ pts_world_ila

    @property
    def image_origin(self):
        return self.ILA_TO_LPS @ self.carm.image_origin
