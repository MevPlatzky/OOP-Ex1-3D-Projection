"""Numba-accelerated sampling of 3D volumes along 2D planes."""

import numpy as np
from numba import njit, prange


@njit(parallel=True, fastmath=True)
def project_plane_numba(
    volume, a1, a2, b, c, n_x, n_y, d_top, d_bot
):
    """Sample a plane into a zero-filled 2D image using nearest-neighbor indices."""
    size_x, size_y, size_z = volume.shape
    image = np.zeros((n_y, n_x), dtype=np.float32)
    epsilon = 0.001

    for j in prange(n_y):
        t = j / (n_y - 1) if n_y > 1 else 0.0

        left_x = (1.0 - t) * a1[0] + t * b[0]
        left_y = (1.0 - t) * a1[1] + t * b[1]
        left_z = (1.0 - t) * a1[2] + t * b[2]

        right_x = (1.0 - t) * a2[0] + t * c[0]
        right_y = (1.0 - t) * a2[1] + t * c[1]
        right_z = (1.0 - t) * a2[2] + t * c[2]

        row_width = (1.0 - t) * d_top + t * d_bot
        safe_width = row_width if row_width > epsilon else 1.0

        for i in range(n_x):
            x_centered = i - (n_x - 1) / 2.0
            if abs(x_centered) <= (row_width / 2.0) + epsilon:
                u = 0.5 + (x_centered / safe_width)

                if row_width <= epsilon:
                    point_x, point_y, point_z = a1[0], a1[1], a1[2]
                else:
                    point_x = (1.0 - u) * left_x + u * right_x
                    point_y = (1.0 - u) * left_y + u * right_y
                    point_z = (1.0 - u) * left_z + u * right_z

                index_x = int(round(point_x))
                index_y = int(round(point_y))
                index_z = int(round(point_z))

                if (
                    0 <= index_x < size_x
                    and 0 <= index_y < size_y
                    and 0 <= index_z < size_z
                ):
                    image[j, i] = volume[index_x, index_y, index_z]

    return image
