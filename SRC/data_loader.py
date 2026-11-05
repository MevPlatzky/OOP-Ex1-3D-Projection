"""Load volume data and plane definitions from input files."""

import csv
from typing import List

import nrrd
import numpy as np

from plane import Plane, create_plane, parse_csv_row


def load_volume(path: str) -> np.ndarray:
    """Read the NRRD volume; its header is not used by the projection."""
    volume, _ = nrrd.read(path)
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
            except Exception:
                continue
    return planes
