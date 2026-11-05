import unittest
from unittest.mock import patch

import numpy as np

from SRC.plane import Plane
from SRC.video_renderer import (
    VideoWriterError,
    get_global_canvas_size,
    open_video_writer,
    render_video,
)


def make_plane(n_x, n_y):
    point = np.zeros(3, dtype=np.float32)
    return Plane(point, point, point, point, n_x, n_y, 0.0, 0.0)


class FakeWriter:
    def __init__(self):
        self.frames = []
        self.released = False

    def write(self, frame):
        self.frames.append(frame.copy())

    def release(self):
        self.released = True


class VideoWriterSetupTests(unittest.TestCase):
    def test_global_canvas_is_maximum_plane_size_rounded_up_to_even(self):
        canvas = get_global_canvas_size([make_plane(3, 5), make_plane(8, 4)])

        self.assertEqual(canvas, (8, 6))

    def test_global_canvas_preserves_already_even_dimensions(self):
        self.assertEqual(get_global_canvas_size([make_plane(8, 6)]), (8, 6))

    def test_empty_plane_list_has_clear_value_error(self):
        with self.assertRaises(ValueError):
            get_global_canvas_size([])

    def test_writer_uses_mp4v_color_then_grayscale_without_container_fallback(self):
        writers = []
        calls = []

        class Writer:
            def __init__(self, opened):
                self.opened = opened
                self.released = False

            def isOpened(self):
                return self.opened

            def release(self):
                self.released = True

        def make_writer(path, codec, fps, size, isColor):
            calls.append((path, codec, fps, size, isColor))
            writer = Writer(len(writers) == 1)
            writers.append(writer)
            return writer

        with (
            patch("SRC.video_renderer.cv2.VideoWriter_fourcc", return_value=123) as fourcc,
            patch("SRC.video_renderer.cv2.VideoWriter", side_effect=make_writer),
        ):
            writer, path, is_color = open_video_writer("output.mp4", 8, 6, 30)

        self.assertIs(writer, writers[1])
        self.assertEqual(path, "output.mp4")
        self.assertFalse(is_color)
        self.assertTrue(writers[0].released)
        self.assertEqual([call[0] for call in calls], ["output.mp4", "output.mp4"])
        self.assertTrue(all(call[1] == 123 for call in calls))
        self.assertEqual(fourcc.call_count, 2)

    def test_writer_appends_mp4_extension_when_missing(self):
        class Writer:
            def isOpened(self):
                return True

            def release(self):
                pass

        with (
            patch("SRC.video_renderer.cv2.VideoWriter_fourcc", return_value=1),
            patch("SRC.video_renderer.cv2.VideoWriter", return_value=Writer()) as writer,
        ):
            _, path, _ = open_video_writer("output", 8, 6, 30)

        self.assertEqual(path, "output.mp4")
        self.assertEqual(writer.call_args.args[0], "output.mp4")

    def test_writer_failure_never_attempts_avi(self):
        writers = []

        class Writer:
            def isOpened(self):
                return False

            def release(self):
                writers.append("released")

        with (
            patch("SRC.video_renderer.cv2.VideoWriter_fourcc", return_value=1),
            patch("SRC.video_renderer.cv2.VideoWriter", return_value=Writer()) as writer,
        ):
            with self.assertRaises(VideoWriterError):
                open_video_writer("output.mp4", 8, 6, 30)

        self.assertEqual(writer.call_count, 2)
        self.assertTrue(all(call.args[0].endswith(".mp4") for call in writer.call_args_list))
        self.assertEqual(writers, ["released", "released"])


class VideoRenderingTests(unittest.TestCase):
    def test_render_normalizes_and_centers_frames_on_global_canvas(self):
        plane = make_plane(2, 2)
        writer = FakeWriter()
        projected = np.array([[0, 5], [10, 15]], dtype=np.float32)

        with (
            patch("SRC.video_renderer.project_plane_numba", return_value=projected),
            patch(
                "SRC.video_renderer.open_video_writer",
                return_value=(writer, "result.mp4", False),
            ),
        ):
            output_path, fps, frame_count = render_video(
                np.zeros((2, 2, 2), dtype=np.uint8),
                [plane],
                "result.mp4",
                0,
                15,
                (4, 4),
            )

        expected = np.zeros((4, 4), dtype=np.uint8)
        expected[1:3, 1:3] = [[0, 85], [170, 255]]
        self.assertEqual(output_path, "result.mp4")
        self.assertEqual(frame_count, 1)
        self.assertGreaterEqual(fps, 0)
        self.assertEqual(len(writer.frames), 1)
        np.testing.assert_array_equal(writer.frames[0], expected)
        self.assertTrue(writer.released)

    def test_constant_volume_normalizes_every_pixel_to_zero(self):
        plane = make_plane(2, 2)
        writer = FakeWriter()
        projected = np.full((2, 2), 7, dtype=np.float32)

        with (
            patch("SRC.video_renderer.project_plane_numba", return_value=projected),
            patch(
                "SRC.video_renderer.open_video_writer",
                return_value=(writer, "constant.mp4", False),
            ),
        ):
            render_video(
                np.full((2, 2, 2), 7, dtype=np.uint8),
                [plane],
                "constant.mp4",
                7,
                7,
                (2, 2),
            )

        np.testing.assert_array_equal(writer.frames[0], np.zeros((2, 2), dtype=np.uint8))

    def test_color_writer_receives_three_channel_frames(self):
        plane = make_plane(2, 2)
        writer = FakeWriter()

        with (
            patch(
                "SRC.video_renderer.project_plane_numba",
                return_value=np.ones((2, 2), dtype=np.float32),
            ),
            patch(
                "SRC.video_renderer.open_video_writer",
                return_value=(writer, "color.mp4", True),
            ),
        ):
            render_video(
                np.ones((2, 2, 2), dtype=np.uint8),
                [plane],
                "color.mp4",
                0,
                2,
                (2, 2),
            )

        self.assertEqual(writer.frames[0].shape, (2, 2, 3))

    def test_writer_is_released_when_projection_fails(self):
        plane = make_plane(2, 2)
        writer = FakeWriter()

        with (
            patch(
                "SRC.video_renderer.project_plane_numba",
                side_effect=[np.zeros((2, 2), dtype=np.float32), RuntimeError("projection failed")],
            ),
            patch(
                "SRC.video_renderer.open_video_writer",
                return_value=(writer, "failure.mp4", False),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "projection failed"):
                render_video(
                    np.zeros((2, 2, 2), dtype=np.uint8),
                    [plane],
                    "failure.mp4",
                    0,
                    1,
                    (2, 2),
                )

        self.assertTrue(writer.released)

    def test_rendering_empty_plane_list_is_rejected(self):
        with self.assertRaises(ValueError):
            render_video(np.zeros((1, 1, 1)), [], "empty.mp4", 0, 0, (2, 2))


if __name__ == "__main__":
    unittest.main()
