# Software Requirements Specification (SRS)

## 1. Purpose and scope

This document describes the behavior implemented by the current Python program in
`SRC/`. It is an implementation-focused specification, not a list of planned
features. In particular, geometric validation, trilinear interpolation, an
H.264-only output guarantee, and atomic output replacement are not implemented.

The program reads a 3D NRRD volume and a CSV sequence of plane coordinates,
samples each plane, and writes the resulting frames to a video file.

## 2. Runtime and invocation

The program requires Python and the `numpy`, `pynrrd`, `opencv-python`, and
`numba` packages. The repository does not specify a minimum Python version or
provide a dependency manifest.

Run from the repository root:

```text
python SRC/Ex0.py <file.nrrd> <file.csv> <file.mp4>
```

Exactly three arguments are required. If the requested output path does not end
in `.mp4` (case-insensitive), `.mp4` is appended.

## 3. Functional requirements

### 3.1 NRRD input

The program loads the volume with `nrrd.read`. The returned array is used
directly as `volume[x, y, z]`; NRRD physical-space metadata is ignored. The
implementation assumes a non-empty three-dimensional array and does not
validate its dimensions or data type.

The global minimum and maximum are computed once from the entire loaded array
and used later for frame normalization.

### 3.2 Plane CSV input

Each parseable row describes one plane:

* 9 numeric values describe a triangle: `a, b, c` (three XYZ coordinates).
* 12 numeric values describe a trapezoid: `a1, a2, b, c` (four XYZ
  coordinates).
* If a row has exactly 10 or 13 numeric values, its first value is discarded
  as an identifier before parsing the coordinates.

Whitespace and empty cells are ignored. Coordinate values are converted to
`float32`. Non-numeric rows (including headers) and rows with unsupported
coordinate counts are skipped. Rows that fail dimension calculation are also
skipped without a row-specific diagnostic. If no planes remain, the program
prints an error and exits with code `2`.

The loader does not validate that coordinates are finite or that the points
form a coplanar, isosceles, non-degenerate triangle or trapezoid.

### 3.3 Plane dimensions and rasterization

For each plane, the program calculates:

```text
D_top = ||a2 - a1||
D_bot = ||c - b||
D_leg = ||b - a1||
H     = sqrt(max(0, D_leg^2 - ((D_bot - D_top) / 2)^2))
W     = max(D_top, D_bot)
N_y   = ceil(H) + 1
N_x   = ceil(W) + 1
```

For a triangle, the CSV parser represents its apex as `a1 = a2 = a`.
Calculation of these dimensions is not a geometric validity check.

The projection kernel in `SRC/projector.py` generates each row by linearly
interpolating between the plane's two side edges. A pixel is inside the
polygon's horizontal span when
`abs(x_centered) <= row_width / 2 + 0.001`. Pixels outside that span remain
zero. The triangle apex is handled separately when its row width is at most
`0.001`.

Each generated 3D point is rounded with `round`, then sampled from the volume
when all three integer indices are within bounds. The kernel uses nearest
neighbor sampling only; there is no trilinear interpolation option. The output
slice is a `float32` 2D array.

### 3.4 Video output

The program chooses a single canvas from the largest plane width and height,
rounding each dimension up to an even integer. Each normalized plane is centered
on this zero-initialized canvas.

Values are normalized using the global volume minimum and maximum:

```text
clip(255 * (slice - global_min) / (global_max - global_min), 0, 255)
```

The result is converted to `uint8`. If the global minimum and maximum are
equal, the entire normalized frame is zero. Values outside the sampled volume
are zero before normalization.

Frames are streamed at 30 FPS to an MP4 writer using the `mp4v` codec. The
writer tries color and grayscale modes; if neither can be opened, the program
reports an error instead of writing AVI or another container. Output is written
directly to its destination; temporary-file/atomic replacement behavior is not
implemented.

The reported engine FPS measures projection and frame writes after the first
plane has warmed up the Numba kernel. It excludes NRRD loading, CSV parsing,
kernel warm-up, and video-writer initialization. No minimum performance
threshold is currently enforced by the program.

## 4. Errors and exit codes

| Exit code | Implemented condition |
|---|---|
| `0` | The program completes video generation. |
| `1` | The argument count is incorrect, or NRRD loading raises an exception. |
| `2` | No plane rows remain after parsing and dimension calculation. |
| `3` | All configured video-writer attempts fail. |

CSV file-opening errors and unexpected errors during projection or encoding
are not translated into these exit codes; they may propagate as Python
exceptions. Invalid CSV rows are skipped rather than reported individually.

## 5. Non-functional behavior and limitations

* Numba compiles the projection kernel and parallelizes its row loop.
* Output frames are written one at a time; the program does not retain the full
  rendered video in memory.
* The code does not provide a GUI, geometric validation, alternate
  interpolation methods, or configurable FPS.
* The repository currently has sample input/output data but no automated test
  suite or dependency manifest.
