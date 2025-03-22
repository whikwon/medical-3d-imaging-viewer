from enum import Enum

import numpy as np


class CoordinateSystem(Enum):
    """Enumeration of valid coordinate systems."""

    LPS = "LPS"  # Left-Posterior-Superior
    RAS = "RAS"  # Right-Anterior-Superior
    ILA = "ILA"  # Inferior-Left-Anterior


class PatientPosition(Enum):
    """Enumeration of valid patient positions."""

    HFS = "HFS"  # Head First-Supine
    FFS = "FFS"  # Feet First-Supine


class TransformationMatrix:
    """Class that handles coordinate system transformation matrices."""

    # Transformation matrices between coordinate systems
    COORDINATE_TRANSFORM = {
        CoordinateSystem.RAS: {
            CoordinateSystem.LPS: np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]),
            CoordinateSystem.ILA: np.array([[-0, 0, -1], [-1, 0, 0], [0, 1, 0]]),
        },
        CoordinateSystem.LPS: {
            CoordinateSystem.RAS: np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]),
            CoordinateSystem.ILA: np.array([[0, 0, -1], [1, 0, 0], [0, -1, 0]]),
        },
        CoordinateSystem.ILA: {
            CoordinateSystem.LPS: np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]]),
            CoordinateSystem.RAS: np.array([[0, -1, 0], [0, 0, 1], [-1, 0, 0]]),
        },
    }

    # Transformation matrices between patient positions
    POSITION_TRANSFORM = {
        PatientPosition.HFS: {
            PatientPosition.FFS: np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]]),
        },
        PatientPosition.FFS: {
            PatientPosition.HFS: np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]]),
        },
    }

    @classmethod
    def get_coordinate_transform_matrix(
        cls, from_cs: CoordinateSystem, to_cs: CoordinateSystem
    ) -> np.ndarray:
        """Get the transformation matrix between two coordinate systems.

        Args:
            from_cs: Source coordinate system
            to_cs: Target coordinate system

        Returns:
            3x3 transformation matrix

        Raises:
            ValueError: If the coordinate systems are invalid
        """
        if from_cs == to_cs:
            return np.eye(3)

        if (
            from_cs not in cls.COORDINATE_TRANSFORM
            or to_cs not in cls.COORDINATE_TRANSFORM[from_cs]
        ):
            raise ValueError(f"No direct transformation from {from_cs} to {to_cs}")

        return cls.COORDINATE_TRANSFORM[from_cs][to_cs]

    @classmethod
    def get_position_transform_matrix(
        cls, from_pos: PatientPosition, to_pos: PatientPosition
    ) -> np.ndarray:
        """Get the transformation matrix between two patient positions.

        Args:
            from_pos: Source patient position
            to_pos: Target patient position

        Returns:
            3x3 transformation matrix

        Raises:
            ValueError: If the patient positions are invalid
        """
        if from_pos == to_pos:
            return np.eye(3)

        if (
            from_pos not in cls.POSITION_TRANSFORM
            or to_pos not in cls.POSITION_TRANSFORM[from_pos]
        ):
            raise ValueError(f"No direct transformation from {from_pos} to {to_pos}")

        return cls.POSITION_TRANSFORM[from_pos][to_pos]

    @classmethod
    def patient_to_world_transform_matrix(
        cls, patient_position: PatientPosition, coord_system: CoordinateSystem
    ) -> np.ndarray:
        """Get the transformation matrix from patient space to world space.

        Args:
            patient_position: Patient position
            coord_system: Coordinate system

        Returns:
            3x3 transformation matrix
        """
        transform_matrix = np.eye(3)

        # First transform to standard position (HFS)
        if patient_position != PatientPosition.HFS:
            transform_matrix = (
                cls.get_position_transform_matrix(patient_position, PatientPosition.HFS)
                @ transform_matrix
            )

        # Then transform to standard coordinate system (ILA)
        if coord_system != CoordinateSystem.ILA:
            transform_matrix = (
                cls.get_coordinate_transform_matrix(coord_system, CoordinateSystem.ILA)
                @ transform_matrix
            )

        return transform_matrix
