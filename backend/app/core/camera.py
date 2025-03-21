import numpy as np
from scipy.spatial.transform import Rotation


def create_intrinsic_matrix(focal_length, pixel_spacing, principal_pt):
    """
    K = K_s @ K_f = [
        [f*s_x, f*s_theta, o_x],
        [0    , f*s_y    , o_y],
        [0    , 0        , 1  ],
    ]

    In the context of a C-arm system, think of 'f' as the SID.
    's_x' and 's_y' are factors that convert units to millimeters (mm),
    and since 'pixel_spacing' is in mm/px, taking the reciprocal gives you the correct value.

    References
    ----------
    .. [1] An Invitation to 3-D Vision: From Images to Models, p.55, eq.(3.14)
    """
    return np.array(
        [
            [focal_length / pixel_spacing[0], 0, principal_pt[0]],
            [0, focal_length / pixel_spacing[1], principal_pt[1]],
            [0, 0, 1],
        ]
    )


def world_to_camera(
    x_world: np.ndarray,
    camera_origin_world: np.ndarray,
    rotation_camera_to_world: Rotation | np.ndarray,
) -> np.ndarray:
    """
    R_cw @ (X_w - T_wc) = X_c

    Parameters
    ----------
    x_world: np.ndarray
        (n, 3)
    camera_origin_world: np.ndarray
        (3,) or (1, 3)
    rotation_camera_to_world: Rotation or np.ndarray
        (3, 3)

    Returns
    -------
    x_camera: np.ndarray
        (n, 3)

    References
    ----------
    .. [1] An Invitation to 3-D Vision: From Images to Models, p.29, eq.(2.17)
    """
    if isinstance(rotation_camera_to_world, Rotation):
        return rotation_camera_to_world.apply(x_world - camera_origin_world)
    else:
        return (rotation_camera_to_world @ (x_world - camera_origin_world).T).T


def camera_to_world(
    x_camera: np.ndarray,
    camera_origin_world: np.ndarray,
    rotation_world_to_camera: Rotation | np.ndarray,
) -> np.ndarray:
    """
    X_w = R_wc @ X_c + T_wc

    Parameters
    ----------
    x_camera: np.ndarray
        (n, 3)
    camera_origin_world: np.ndarray
        (3,) or (1, 3)
    rotation_world_to_camera: Rotation or np.ndarray
        (3, 3)

    Returns
    -------
    x_world: np.ndarray
        (n, 3)

    References
    ----------
    .. [1] An Invitation to 3-D Vision: From Images to Models, p.29, eq.(2.17)
    """
    if isinstance(rotation_world_to_camera, Rotation):
        return rotation_world_to_camera.apply(x_camera) + camera_origin_world
    else:
        return (rotation_world_to_camera @ x_camera.T).T + camera_origin_world


def camera_to_image(x_camera: np.ndarray, intrinsic_matrix: np.ndarray) -> np.ndarray:
    """
    \lambda * x' = K @ X_c
    x' = K @ X_c / \lambda

    References
    ----------
    An Invitation to 3-D Vision: From Images to Models, p.55, eq.(3.6), (3.15)
    """
    z = x_camera[..., -1][:, None]
    return ((intrinsic_matrix @ x_camera.T).T / z)[..., :2]


def to_homogeneous(pts: np.ndarray) -> np.ndarray:
    return np.concatenate([pts, np.ones([*pts.shape[:-1], 1])], axis=-1)


def image_to_camera(
    x_image: np.ndarray, intrinsic_matrix: np.ndarray, z=None
) -> np.ndarray:
    """
    Parameters
    ----------
    x_image: np.ndarray
        non-homogeneous (n, 2) or homogeneous (n, 3)
    intrinsic_matrix: np.ndarray
        (3, 3)
    z: float
        camera depth

    Returns
    -------
    x_camera: np.ndarray
        (n, 3)
    """
    if x_image.shape[-1] == 2:
        x_image = to_homogeneous(x_image)
    x = (np.linalg.inv(intrinsic_matrix) @ x_image.T).T
    if z is not None:
        return x * z
    return x


def triangulate_multi_views(
    projection_matrices: list[np.ndarray], pts: list[np.ndarray]
):
    """
    Parameters
    ----------
    projection_matrices: list[np.ndarray]
        array of (3, 4) projection matrices
    pts: list[np.ndarray]
        array of (2,) image points

    Returns
    -------
    pt_3d: np.ndarray
        (3,)

    References
    ----------
    .. [1] https://gist.github.com/davegreenwood/e1d2227d08e24cc4e353d95d0c18c914
    """
    assert len(projection_matrices) == len(pts)
    n = len(projection_matrices)
    M = np.zeros([3 * n, 4 + n])
    for i, (pt, proj_mat) in enumerate(zip(pts, projection_matrices)):
        M[3 * i : 3 * i + 3, :4] = proj_mat
        M[3 * i : 3 * i + 3, 4 + i] = -to_homogeneous(pt)
    V = np.linalg.svd(M)[-1]
    X = V[-1, :4]
    return (X / X[3])[:3]
