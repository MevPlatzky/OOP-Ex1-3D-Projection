import unittest

import numpy as np

from SRC.plane import create_plane, parse_csv_row
from SRC.projector import project_plane_numba


def project(volume, coords):
    plane = create_plane(parse_csv_row([str(value) for value in coords]))
    return project_plane_numba(
        volume,
        plane.a1,
        plane.a2,
        plane.b,
        plane.c,
        plane.n_x,
        plane.n_y,
        plane.d_top,
        plane.d_bot,
    )


class PlaneProjectionTests(unittest.TestCase):
    def setUp(self):
        x, y, z = np.indices((12, 12, 12))
        self.volume = (x + 10 * y + 100 * z).astype(np.uint16)

    def test_axis_aligned_rectangle_matches_analytic_volume(self):
        coords = [2, 2, 1, 2, 4, 1, 2, 2, 5, 2, 4, 5]

        result = project(self.volume, coords)

        expected = np.array(
            [
                [122, 132, 142],
                [222, 232, 242],
                [322, 332, 342],
                [422, 432, 442],
                [522, 532, 542],
            ],
            dtype=np.float32,
        )
        np.testing.assert_array_equal(result, expected)

    def test_triangle_apex_is_sampled_at_center_of_first_row(self):
        coords = [1, 2, 2, 1, 5, 5, 1, -1, 5]

        result = project(self.volume, coords)

        self.assertEqual(result.shape, (4, 7))
        self.assertEqual(result[0, 3], 221)
        self.assertEqual(np.count_nonzero(result[0]), 1)
        np.testing.assert_array_equal(np.flatnonzero(result[0]), [3])

    def test_pixels_outside_polygon_remain_zero(self):
        coords = [1, 2, 2, 1, 5, 5, 1, -1, 5]

        result = project(self.volume, coords)

        self.assertEqual(result[0, 0], 0)
        self.assertEqual(result[0, -1], 0)
        self.assertEqual(result[1, 0], 0)
        self.assertEqual(result[1, -1], 0)

    def test_plane_outside_volume_returns_zero_pixels(self):
        coords = [-3, 2, 1, -3, 4, 1, -3, 2, 5, -3, 4, 5]

        result = project(self.volume, coords)

        self.assertGreater(result.size, 0)
        np.testing.assert_array_equal(result, np.zeros_like(result))

    def test_plane_at_volume_edge_samples_last_valid_index(self):
        coords = [11, 2, 1, 11, 4, 1, 11, 2, 3, 11, 4, 3]

        result = project(self.volume, coords)

        self.assertEqual(result[0, 0], 131)
        self.assertEqual(result[-1, -1], 351)

    def test_rounding_uses_python_ties_to_even(self):
        point = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        value = project_plane_numba(
            self.volume, point, point, point, point, 1, 1, 0.0, 0.0
        )

        self.assertEqual(value[0, 0], self.volume[0, 0, 0])

    def test_rounding_halfway_between_odd_and_even_selects_even(self):
        point = np.array([1.5, 1.5, 1.5], dtype=np.float32)
        value = project_plane_numba(
            self.volume, point, point, point, point, 1, 1, 0.0, 0.0
        )

        self.assertEqual(value[0, 0], self.volume[2, 2, 2])

    def test_result_is_float32_and_has_expected_shape(self):
        coords = [2, 2, 1, 2, 4, 1, 2, 2, 5, 2, 4, 5]

        result = project(self.volume, coords)

        self.assertEqual(result.dtype, np.float32)
        self.assertEqual(result.shape, (5, 3))

    def test_single_voxel_volume_can_be_sampled(self):
        volume = np.array([[[37]]], dtype=np.uint8)
        point = np.zeros(3, dtype=np.float32)

        result = project_plane_numba(volume, point, point, point, point, 1, 1, 0, 0)

        np.testing.assert_array_equal(result, np.array([[37]], dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
