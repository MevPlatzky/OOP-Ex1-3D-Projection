import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import numpy as np

from SRC import cli
from SRC.data_loader import load_volume
from SRC.video_renderer import VideoWriterError


class CliTests(unittest.TestCase):
    def run_cli(self, args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli.main(args)
        return code, output.getvalue()

    def test_wrong_argument_count_prints_usage_and_returns_one(self):
        code, output = self.run_cli([])

        self.assertEqual(code, 1)
        self.assertIn("Usage:", output)

    def test_nrrd_load_error_returns_one_with_error_message(self):
        with patch("SRC.cli.load_volume", side_effect=OSError("bad NRRD")):
            code, output = self.run_cli(["bad.nrrd", "planes.csv", "out.mp4"])

        self.assertEqual(code, 1)
        self.assertIn("Failed to load NRRD", output)

    def test_no_parseable_planes_returns_two_without_rendering(self):
        with (
            patch("SRC.cli.load_volume", return_value=np.zeros((2, 2, 2))),
            patch("SRC.cli.load_planes", return_value=[]),
            patch("SRC.cli.render_video") as render,
        ):
            code, output = self.run_cli(["volume.nrrd", "empty.csv", "out.mp4"])

        self.assertEqual(code, 2)
        self.assertIn("No valid planes", output)
        render.assert_not_called()

    def test_invalid_loaded_volume_returns_one(self):
        with patch(
            "SRC.cli.load_volume",
            side_effect=ValueError("NRRD volume must be a non-empty 3D array"),
        ):
            code, output = self.run_cli(["bad.nrrd", "planes.csv", "out.mp4"])

        self.assertEqual(code, 1)
        self.assertIn("Failed to load NRRD", output)

    def test_csv_io_error_returns_one_without_traceback(self):
        with (
            patch("SRC.cli.load_volume", return_value=np.zeros((2, 2, 2))),
            patch("SRC.cli.load_planes", side_effect=OSError("CSV missing")),
        ):
            code, output = self.run_cli(["volume.nrrd", "missing.csv", "out.mp4"])

        self.assertEqual(code, 1)
        self.assertIn("Failed to load CSV", output)

    def test_video_writer_error_returns_three(self):
        with (
            patch("SRC.cli.load_volume", return_value=np.zeros((2, 2, 2))),
            patch("SRC.cli.load_planes", return_value=[cli_test_plane()]),
            patch("SRC.cli.render_video", side_effect=VideoWriterError("writer unavailable")),
        ):
            code, output = self.run_cli(["volume.nrrd", "planes.csv", "out.mp4"])

        self.assertEqual(code, 3)
        self.assertIn("writer unavailable", output)

    def test_success_reports_output_and_frame_count(self):
        with (
            patch("SRC.cli.load_volume", return_value=np.ones((2, 2, 2))),
            patch("SRC.cli.load_planes", return_value=[cli_test_plane()]),
            patch("SRC.cli.render_video", return_value=("out.mp4", 31.5, 4)) as render,
        ):
            code, output = self.run_cli(["volume.nrrd", "planes.csv", "out.mp4"])

        self.assertEqual(code, 0)
        self.assertIn("[SUCCESS] Video saved to out.mp4", output)
        self.assertIn("Total Frames: 4", output)
        self.assertEqual(render.call_args.args[-1], (2, 2))

    def test_non_ascii_path_does_not_break_console_reporting(self):
        with (
            patch("SRC.cli.load_volume", side_effect=OSError("missing")),
            patch("sys.stdout", io.TextIOWrapper(io.BytesIO(), encoding="ascii")),
        ):
            code = cli.main(["נפח.nrrd", "planes.csv", "out.mp4"])

        self.assertEqual(code, 1)

    def test_real_csv_fixture_loads_only_well_formed_rows(self):
        from SRC.data_loader import load_planes

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "planes.csv"
            with path.open("w", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["header"])
                writer.writerow(
                    ["0", "0", "1", "0", "2", "1", "0", "0", "3", "0", "2", "3"]
                )
                writer.writerow(["not", "a", "plane"])

            planes = load_planes(str(path))

        self.assertEqual(len(planes), 1)
        self.assertEqual(planes[0].n_x, 3)


class VolumeLoadingTests(unittest.TestCase):
    def test_load_volume_reads_valid_3d_nrrd(self):
        volume = np.arange(24, dtype=np.uint16).reshape((2, 3, 4))

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "volume.nrrd"
            import nrrd

            nrrd.write(str(path), volume)
            loaded = load_volume(str(path))

        np.testing.assert_array_equal(loaded, volume)

    def test_load_volume_rejects_non_3d_arrays(self):
        with patch("SRC.data_loader.nrrd.read", return_value=(np.zeros((2, 2)), {})):
            with self.assertRaisesRegex(ValueError, "3D"):
                load_volume("not-used.nrrd")

    def test_load_volume_rejects_empty_axes(self):
        with patch(
            "SRC.data_loader.nrrd.read", return_value=(np.zeros((2, 0, 3)), {})
        ):
            with self.assertRaisesRegex(ValueError, "non-empty"):
                load_volume("not-used.nrrd")

    def test_load_volume_rejects_nonfinite_values(self):
        volume = np.zeros((2, 2, 2), dtype=np.float32)
        volume[0, 0, 0] = np.nan

        with patch("SRC.data_loader.nrrd.read", return_value=(volume, {})):
            with self.assertRaisesRegex(ValueError, "non-finite"):
                load_volume("not-used.nrrd")

    def test_load_volume_rejects_non_numeric_values(self):
        with patch(
            "SRC.data_loader.nrrd.read",
            return_value=(np.full((2, 2, 2), "x"), {}),
        ):
            with self.assertRaisesRegex(ValueError, "numeric dtype"):
                load_volume("not-used.nrrd")


def cli_test_plane():
    from SRC.plane import Plane

    point = np.zeros(3, dtype=np.float32)
    return Plane(point, point, point, point, 2, 2, 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()
