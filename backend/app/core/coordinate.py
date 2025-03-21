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


class CoordinateBase:
    """Base class for coordinate objects."""

    def __init__(self, coords: np.ndarray):
        """Initialize with coordinates.

        Args:
            coords: Array of 3D coordinates (N,3) or single point (3,)
        """
        assert coords.ndim in [1, 2] and coords.shape[-1] == 3, (
            "Coordinates must be 3D points"
        )
        self.coords = coords

    def __add__(self, other):
        if isinstance(other, CoordinateBase):
            return self.__class__(self.coords + other.coords)
        elif isinstance(other, np.ndarray):
            return self.__class__(self.coords + other)
        elif isinstance(other, (int, float)):
            return self.__class__(self.coords + other)
        else:
            raise TypeError("Unsupported operand type for +")

    def __sub__(self, other):
        if isinstance(other, CoordinateBase):
            return self.__class__(self.coords - other.coords)
        elif isinstance(other, np.ndarray):
            return self.__class__(self.coords - other)
        elif isinstance(other, (int, float)):
            return self.__class__(self.coords - other)
        else:
            raise TypeError("Unsupported operand type for -")

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(self.coords * other)
        elif isinstance(other, np.ndarray):
            return self.__class__(self.coords * other)
        else:
            raise TypeError("Unsupported operand type for *")

    def __getitem__(self, index):
        return self.coords[index]

    def __setitem__(self, index, value):
        self.coords[index] = value


class PatientCoordinates(CoordinateBase):
    """Coordinates in a specific patient coordinate system."""

    def __init__(self, coords: np.ndarray, coord_system: CoordinateSystem | str):
        """Initialize with coordinates and their reference system.

        Args:
            coords: Array of coordinates
            coord_system: Coordinate system enum or string
        """
        super().__init__(coords)

        # Handle string input for backward compatibility
        if isinstance(coord_system, str):
            try:
                self.coord_system = CoordinateSystem(coord_system)
            except ValueError:
                raise ValueError(f"Invalid coordinate system: {coord_system}")
        else:
            self.coord_system = coord_system

    def __add__(self, other):
        if isinstance(other, PatientCoordinates):
            if self.coord_system != other.coord_system:
                raise ValueError("Cannot add coordinates in different systems")
            return self.__class__(self.coords + other.coords, self.coord_system)
        return super().__add__(other)

    def __sub__(self, other):
        if isinstance(other, PatientCoordinates):
            if self.coord_system != other.coord_system:
                raise ValueError("Cannot subtract coordinates in different systems")
            return self.__class__(self.coords - other.coords, self.coord_system)
        return super().__sub__(other)

    def change_coordinate_system(
        self, new_system: CoordinateSystem | str
    ) -> "PatientCoordinates":
        """Convert coordinates to a new coordinate system.

        Args:
            new_system: Target coordinate system

        Returns:
            New PatientCoordinates object in the target system
        """
        # Handle string input for backward compatibility
        if isinstance(new_system, str):
            try:
                new_system = CoordinateSystem(new_system)
            except ValueError:
                raise ValueError(f"Invalid coordinate system: {new_system}")

        if self.coord_system == new_system:
            return self

        transform_matrix = TransformationMatrix.get_coordinate_transform_matrix(
            self.coord_system, new_system
        )

        new_coords = (transform_matrix @ self.coords.T).T
        return PatientCoordinates(new_coords, new_system)

    def to_world(self, patient_position: PatientPosition | str) -> np.ndarray:
        """Transform coordinates to world space.

        Args:
            patient_position: Patient position

        Returns:
            World coordinates as numpy array
        """
        # Handle string input for backward compatibility
        if isinstance(patient_position, str):
            try:
                patient_position = PatientPosition(patient_position)
            except ValueError:
                raise ValueError(f"Invalid patient position: {patient_position}")

        transform_matrix = TransformationMatrix.patient_to_world_transform_matrix(
            patient_position, self.coord_system
        )

        world_coords = (transform_matrix @ self.coords.T).T
        return world_coords

    @classmethod
    def from_world(
        cls,
        world_coords: np.ndarray,
        patient_position: PatientPosition | str,
        coord_system: CoordinateSystem | str,
    ) -> "PatientCoordinates":
        """Create patient coordinates from world coordinates.

        Args:
            world_coords: World coordinates
            patient_position: Patient position
            coord_system: Target coordinate system

        Returns:
            PatientCoordinates object
        """
        # Handle string inputs for backward compatibility
        if isinstance(patient_position, str):
            try:
                patient_position = PatientPosition(patient_position)
            except ValueError:
                raise ValueError(f"Invalid patient position: {patient_position}")

        if isinstance(coord_system, str):
            try:
                coord_system = CoordinateSystem(coord_system)
            except ValueError:
                raise ValueError(f"Invalid coordinate system: {coord_system}")

        transform_matrix = np.linalg.inv(
            TransformationMatrix.patient_to_world_transform_matrix(
                patient_position, coord_system
            )
        )

        patient_coords = (transform_matrix @ world_coords.T).T
        return cls(patient_coords, coord_system)
