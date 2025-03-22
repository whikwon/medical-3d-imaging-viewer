import numpy as np
import vtk


def rotation_matrix_to_vtk_direction_matrix(
    rotation_matrix: np.ndarray,
) -> vtk.vtkMatrix3x3:
    direction_matrix = vtk.vtkMatrix3x3()
    for i in range(3):
        for j in range(3):
            direction_matrix.SetElement(i, j, rotation_matrix[i][j])
    return direction_matrix
