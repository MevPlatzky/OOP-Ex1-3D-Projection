"""Command-line orchestration for volume projection and video export."""

import sys
from typing import Optional, Sequence

from data_loader import load_planes, load_volume
from video_renderer import (
    VideoWriterError,
    get_global_canvas_size,
    render_video,
)


def _configure_console_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="backslashreplace")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI and return its process exit code."""
    _configure_console_output()
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3:
        print("Usage: python Ex0.py <file.nrrd> <file.csv> <file.mp4>")
        return 1

    nrrd_path, csv_path, output_path = args
    print(f"[INFO] Loading NRRD file: {nrrd_path}...")
    try:
        volume = load_volume(nrrd_path)
    except Exception as error:
        print(f"[ERROR] Failed to load NRRD: {error}")
        return 1

    global_min = float(volume.min())
    global_max = float(volume.max())
    print(
        f"[INFO] Volume shape: {volume.shape}, "
        f"Intensity Range: [{global_min}, {global_max}]"
    )

    print("[INFO] Parsing CSV planes and Planning Global Canvas...")
    planes = load_planes(csv_path)
    if not planes:
        print("[ERROR] No valid planes found.")
        return 2

    canvas_size = get_global_canvas_size(planes)
    max_width, max_height = canvas_size
    print(f"[INFO] Global canvas size locked at: {max_width}x{max_height}.")

    try:
        output_path, fps, frame_count = render_video(
            volume,
            planes,
            output_path,
            global_min,
            global_max,
            canvas_size,
        )
    except VideoWriterError as error:
        print(f"[ERROR] {error}")
        return 3

    print("-" * 40)
    print(f"[SUCCESS] Video saved to {output_path}")
    print(f"[PERFORMANCE] Total Frames: {frame_count}")
    print(f"[PERFORMANCE] Engine Speed: {fps:.2f} FPS")
    print("-" * 40)
    return 0
