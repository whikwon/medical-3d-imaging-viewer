import numpy as np


def compute_optimal_window_level(voxel_array: np.ndarray):
    """
    Automatically calculate window width and level based on image percentiles
    for optimal visualization of radiographic images.

    This implementation follows the same approach used in 3D Slicer's
    vtkMRMLScalarVolumeDisplayNode::CalculateAutoLevels method, using the
    0.1 and 99.9 percentiles of the intensity distribution to determine
    an appropriate window width and center.

    Args:
        voxel_array: A numpy array containing voxel data

    Returns:
        tuple: (window_width, window_center) where:
            - window_width: Range of intensity values to display
            - window_center: Center point of the intensity window

    References:
        - https://discourse.slicer.org/t/window-width-level-range-calculation/19010
        - https://github.com/Slicer/Slicer/blob/main/Libs/MRML/Core/vtkMRMLScalarVolumeDisplayNode.cxx
    """
    # Compute the 0.1 and 99.9 percentiles
    min_val = np.percentile(voxel_array, 0.1)
    max_val = np.percentile(voxel_array, 99.9)

    # Calculate window and level
    width = max_val - min_val
    center = (max_val + min_val) / 2.0
    return width, center
