import unittest

import numpy as np

from SRC.plane import (
    create_plane,
    get_plane_dimensions,
    is_numeric_csv_row,
    parse_csv_row,
)


class PlaneParsingTests(unittest.TestCase):
    def test_triangle_coordinates_are_mapped_to_duplicate_apex(self):
        a1, a2, b, c = parse_csv_row(
            ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        )

        np.testing.assert_array_equal(a1, [1, 2, 3])
        self.assertIs(a1, a2)
        np.testing.assert_array_equal(b, [4, 5, 6])
        np.testing.assert_array_equal(c, [7, 8, 9])
        self.assertEqual(a1.dtype, np.float32)

    def test_trapezoid_coordinates_keep_point_order(self):
        points = parse_csv_row(
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
        )

        for point, expected in zip(
            points, ([1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12])
        ):
            np.testing.assert_array_equal(point, expected)

    def test_optional_numeric_identifier_is_ignored(self):
        coords = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        points = parse_csv_row(coords)
        np.testing.assert_array_equal(points[0], [1, 2, 3])

    def test_optional_trapezoid_identifier_is_ignored(self):
        coords = [str(value) for value in range(13)]
        points = parse_csv_row(coords)
        np.testing.assert_array_equal(points[0], [1, 2, 3])
        np.testing.assert_array_equal(points[3], [10, 11, 12])

    def test_whitespace_and_empty_cells_are_ignored(self):
        points = parse_csv_row(
            [" 1 ", "", " 2", "3 ", "4", "5", "6", "7", "8", "9", ""]
        )
        np.testing.assert_array_equal(points[0], [1, 2, 3])

    def test_unsupported_coordinate_counts_raise(self):
        for count in (0, 1, 8, 11, 14):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    parse_csv_row([str(value) for value in range(count)])

    def test_nonnumeric_coordinate_raises(self):
        with self.assertRaisesRegex(ValueError, "non-numeric"):
            parse_csv_row(["a"] + ["1"] * 8)

    def test_nonfinite_coordinates_are_rejected(self):
        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite"):
                    parse_csv_row([value] + ["1"] * 8)

    def test_coordinates_outside_float32_range_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "float32"):
            parse_csv_row(["1e100"] + ["1"] * 8)

    def test_csv_row_classifier_accepts_only_parseable_plane_rows(self):
        self.assertTrue(is_numeric_csv_row(["1"] * 9))
        self.assertFalse(is_numeric_csv_row(["plane", "x", "y"]))
        self.assertFalse(is_numeric_csv_row(["1"] * 8))


class PlaneDimensionTests(unittest.TestCase):
    def test_rectangle_dimensions_use_base_width_and_perpendicular_height(self):
        a1 = np.array([2, 2, 1], dtype=np.float32)
        a2 = np.array([2, 4, 1], dtype=np.float32)
        b = np.array([2, 2, 5], dtype=np.float32)
        c = np.array([2, 4, 5], dtype=np.float32)

        n_x, n_y, d_top, d_bot = get_plane_dimensions(a1, a2, b, c)

        self.assertEqual((n_x, n_y), (3, 5))
        self.assertEqual((d_top, d_bot), (2, 2))

    def test_triangle_dimensions_include_apex_and_bottom_base(self):
        a = np.array([1, 2, 2], dtype=np.float32)
        b = np.array([1, 5, 5], dtype=np.float32)
        c = np.array([1, -1, 5], dtype=np.float32)

        plane = create_plane((a, a, b, c))

        self.assertEqual((plane.n_x, plane.n_y), (7, 4))

    def test_zero_size_points_still_have_one_pixel_raster(self):
        point = np.zeros(3, dtype=np.float32)

        self.assertEqual(get_plane_dimensions(point, point, point, point), (1, 1, 0, 0))

    def test_plane_record_contains_points_and_precomputed_dimensions(self):
        points = parse_csv_row(["2", "2", "1", "2", "4", "1", "2", "2", "5", "2", "4", "5"])

        plane = create_plane(points)

        self.assertEqual((plane.n_x, plane.n_y), (3, 5))
        self.assertEqual((plane.d_top, plane.d_bot), (2, 2))


if __name__ == "__main__":
    unittest.main()
