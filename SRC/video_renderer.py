"""Video writer setup and plane-to-frame rendering."""

import time
from typing import List, Tuple

import cv2
import numpy as np

from plane import Plane
from projector import project_plane_numba


class VideoWriterError(RuntimeError):
    """Raised when none of the supported video writer configurations opens."""


def get_global_canvas_size(planes: List[Plane]) -> Tuple[int, int]:
    """Return the largest plane dimensions, rounded up to even values."""
    max_width = max(plane.n_x for plane in planes)
    max_height = max(plane.n_y for plane in planes)
    max_height = max_height if max_height % 2 == 0 else max_height + 1
    max_width = max_width if max_width % 2 == 0 else max_width + 1
    return max_width, max_height


def open_video_writer(
    path: str, width: int, height: int, fps: float
) -> Tuple[cv2.VideoWriter, str, bool]:
    """Open an MP4 writer or fail without switching to another container."""
    if not path.lower().endswith(".mp4"):
        path += ".mp4"

    for is_color in (True, False):
        codec = "mp4v"
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(path, fourcc, fps, (width, height), isColor=is_color)
        if writer.isOpened():
            return writer, path, is_color
        writer.release()

    raise VideoWriterError("Could not open an MP4 video writer using the mp4v codec.")


def render_video(
    volume: np.ndarray,
    planes: List[Plane],
    output_path: str,
    global_min: float,
    global_max: float,
    canvas_size: Tuple[int, int],
) -> Tuple[str, float, int]:
    """Project, normalize, center, and stream all planes to a video file."""
    max_width, max_height = canvas_size
    first_plane = planes[0]
    project_plane_numba(
        volume,
        first_plane.a1,
        first_plane.a2,
        first_plane.b,
        first_plane.c,
        first_plane.n_x,
        first_plane.n_y,
        first_plane.d_top,
        first_plane.d_bot,
    )

    writer, output_path, is_color = open_video_writer(
        output_path, max_width, max_height, 30.0
    )
    video_frame = np.zeros((max_height, max_width), dtype=np.uint8)
    engine_start = time.time()

    try:
        for plane in planes:
            image = project_plane_numba(
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

            if global_max > global_min:
                normalized = np.clip(
                    255.0 * (image - global_min) / (global_max - global_min),
                    0,
                    255,
                ).astype(np.uint8)
            else:
                normalized = np.zeros_like(image, dtype=np.uint8)

            pad_h = (max_height - normalized.shape[0]) // 2
            pad_w = (max_width - normalized.shape[1]) // 2
            video_frame.fill(0)
            video_frame[
                pad_h : pad_h + normalized.shape[0],
                pad_w : pad_w + normalized.shape[1],
            ] = normalized

            if is_color:
                writer.write(cv2.cvtColor(video_frame, cv2.COLOR_GRAY2BGR))
            else:
                writer.write(video_frame)
    finally:
        writer.release()

    elapsed = time.time() - engine_start
    frame_count = len(planes)
    fps = frame_count / elapsed if elapsed > 0 else 0
    return output_path, fps, frame_count
