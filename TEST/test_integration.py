import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
import nrrd

ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINT = ROOT / "SRC" / "Ex0.py"


class CommandLineIntegrationTests(unittest.TestCase):
    def make_inputs(self, directory):
        volume_path = Path(directory) / "tiny.nrrd"
        planes_path = Path(directory) / "planes.csv"
        output_path = Path(directory) / "projection.mp4"
        x, y, z = np.indices((8, 8, 8))
        volume = (x + 10 * y + 100 * z).astype(np.uint8)
        nrrd.write(str(volume_path), volume)
        with planes_path.open("w", newline="") as csv_file:
            csv.writer(csv_file).writerow(
                ["2", "2", "1", "2", "4", "1", "2", "2", "5", "2", "4", "5"]
            )
        return volume_path, planes_path, output_path

    def test_cli_writes_decodable_mp4_and_no_avi(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            volume, planes, output = self.make_inputs(temp_dir)
            result = subprocess.run(
                [sys.executable, str(ENTRY_POINT), str(volume), str(planes), str(output)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=ROOT,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("[SUCCESS]", result.stdout)
            self.assertTrue(output.is_file())
            self.assertFalse(output.with_suffix(".avi").exists())

            reader = cv2.VideoCapture(str(output))
            try:
                self.assertTrue(reader.isOpened())
                ok, frame = reader.read()
                self.assertTrue(ok)
                self.assertEqual(frame.shape[:2], (6, 4))
                self.assertEqual(int(reader.get(cv2.CAP_PROP_FRAME_COUNT)), 1)
            finally:
                reader.release()

    def test_cli_missing_arguments_returns_usage_exit_code(self):
        result = subprocess.run(
            [sys.executable, str(ENTRY_POINT)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=ROOT,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stdout)

    def test_real_head_fixture_runs_to_mp4(self):
        volume = ROOT / "TEST" / "data" / "MRHead_1.nrrd"
        planes = ROOT / "TEST" / "data" / "head.csv"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "head.mp4"
            result = subprocess.run(
                [sys.executable, str(ENTRY_POINT), str(volume), str(planes), str(output)],
                capture_output=True,
                text=True,
                timeout=90,
                cwd=ROOT,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(output.is_file())
            reader = cv2.VideoCapture(str(output))
            try:
                self.assertTrue(reader.isOpened())
                ok, frame = reader.read()
                self.assertTrue(ok)
                self.assertIsNotNone(frame)
            finally:
                reader.release()


if __name__ == "__main__":
    unittest.main()
