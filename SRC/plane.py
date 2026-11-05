"""Plane coordinate parsing and discrete plane dimensions."""

import math
from typing import NamedTuple, Sequence, Tuple

import numpy as np


class Plane(NamedTuple):
    a1: np.ndarray
    a2: np.ndarray
    b: np.ndarray
    c: np.ndarray
    n_x: int
    n_y: int
    d_top: float
    d_bot: float


PlanePoints = Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]


def parse_csv_row(row: Sequence[str]) -> PlanePoints:
    """Parse a triangle or trapezoid row, optionally preceded by an ID."""
    values = []
    for cell in row:
        value = cell.strip()
        if not value:
            continue
        try:
            values.append(float(value))
        except ValueError as exc:
            raise ValueError(f"Row contains non-numeric data: {row}") from exc

    if len(values) in (10, 13):
        values = values[1:]

    if len(values) not in (9, 12):
        raise ValueError(
            f"Invalid row format: expected 9 or 12 coordinates, got {len(values)}"
        )
    if not np.isfinite(values).all():
        raise ValueError("Plane coordinates must be finite numbers")
    float32_max = float(np.finfo(np.float32).max)
    if any(abs(value) > float32_max for value in values):
        raise ValueError("Plane coordinates exceed the supported float32 range")

    if len(values) == 9:
        a = np.array(values[0:3], dtype=np.float32)
        b = np.array(values[3:6], dtype=np.float32)
        c = np.array(values[6:9], dtype=np.float32)
        return a, a, b, c
    a1 = np.array(values[0:3], dtype=np.float32)
    a2 = np.array(values[3:6], dtype=np.float32)
    b = np.array(values[6:9], dtype=np.float32)
    c = np.array(values[9:12], dtype=np.float32)
    return a1, a2, b, c


def is_numeric_csv_row(row: Sequence[str]) -> bool:
    """Return whether a CSV row has a parseable plane coordinate format."""
    try:
        parse_csv_row(row)
        return True
    except ValueError:
        return False


def get_plane_dimensions(
    a1: np.ndarray, a2: np.ndarray, b: np.ndarray, c: np.ndarray
) -> Tuple[int, int, float, float]:
    """Calculate the raster dimensions and the two base lengths."""
    d_top = np.linalg.norm(a2 - a1)
    d_bot = np.linalg.norm(c - b)
    d_leg = np.linalg.norm(b - a1)

    inside_sqrt = max(0.0, d_leg**2 - ((d_bot - d_top) / 2.0) ** 2)
    height = math.sqrt(inside_sqrt)
    width = max(d_top, d_bot)

    n_y = int(math.ceil(height)) + 1
    n_x = int(math.ceil(width)) + 1
    return n_x, n_y, d_top, d_bot


def create_plane(points: PlanePoints) -> Plane:
    """Attach raster dimensions to parsed plane coordinates."""
    a1, a2, b, c = points
    n_x, n_y, d_top, d_bot = get_plane_dimensions(a1, a2, b, c)
    return Plane(a1, a2, b, c, n_x, n_y, d_top, d_bot)
