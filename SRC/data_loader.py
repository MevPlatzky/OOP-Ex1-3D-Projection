"""Load volume data and plane definitions from input files."""

import csv
from typing import List

import nrrd
import numpy as np

if __package__:
    from .plane import Plane, create_plane, parse_csv_row
else:
    from plane import Plane, create_plane, parse_csv_row


def load_volume(path: str) -> np.ndarray:
    """Read and validate a non-empty, finite, real-valued 3D NRRD volume."""
    volume, _ = nrrd.read(path)

    if volume.ndim != 3 or any(size == 0 for size in volume.shape):
        raise ValueError(
            f"NRRD volume must be a non-empty 3D array; got shape {volume.shape}"
        )
    if not (
        np.issubdtype(volume.dtype, np.integer)
        or np.issubdtype(volume.dtype, np.floating)
    ):
        raise ValueError(f"NRRD volume must have a real numeric dtype; got {volume.dtype}")
    if not np.isfinite(volume).all():
        raise ValueError("NRRD volume contains non-finite values")

    return volume


def load_planes(path: str) -> List[Plane]:
    """Read parseable plane rows, skipping headers and rows that fail preparation."""
    planes = []
    with open(path, "r") as csv_file:
        for row in csv.reader(csv_file):
            if not row:
                continue
            try:
                points = parse_csv_row(row)
            except ValueError:
                continue
            try:
                planes.append(create_plane(points))
            except (FloatingPointError, OverflowError, TypeError, ValueError):
                continue
    return planes
