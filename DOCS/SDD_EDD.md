# System and Engineering Design (SDD / EDD)

This document describes the architecture and algorithms implemented by the
current source files in `SRC/`.

## 1. System design

### 1.1 Data flow

1. `SRC/Ex0.py` starts the command-line application.
2. `SRC/cli.py` checks the three positional arguments and coordinates the run.
3. `SRC/data_loader.py` reads the NRRD array and parses usable CSV plane rows.
4. `SRC/plane.py` converts coordinate rows and calculates each plane's raster
   dimensions.
5. `SRC/video_renderer.py` determines the common canvas, warms up the
   projection kernel, opens a video writer, and processes planes in order.
6. `SRC/projector.py` samples a single plane from the 3D array.
7. The renderer normalizes and centers the slice, then writes the frame before
   continuing to the next plane.

### 1.2 Module responsibilities

| Module | Responsibility |
|---|---|
| `Ex0.py` | Small executable entry point; converts `cli.main()`'s return value into the process exit code. |
| `cli.py` | Argument count, status messages, NRRD-load handling, canvas setup, and orchestration. |
| `data_loader.py` | NRRD reading and CSV row iteration; skips rows that cannot be parsed or prepared. |
| `plane.py` | `Plane` record, row parsing, triangle/trapezoid coordinate mapping, and raster dimension calculations. |
| `projector.py` | Numba-compiled plane-to-volume sampling kernel. |
| `video_renderer.py` | Even-sized canvas, codec selection, normalization, frame placement, video writing, and FPS measurement. |

The modules import one another as sibling files. The supported invocation from
the repository root is:

```text
python SRC/Ex0.py <file.nrrd> <file.csv> <file.mp4>
```

### 1.3 Data contracts

* The volume is the NumPy array returned by `nrrd.read`; indexing is
  `volume[x, y, z]`. The header is discarded.
* `plane.parse_csv_row` returns four `float32` points `(a1, a2, b, c)`.
  Triangle input is represented by setting `a1` and `a2` to the same point.
* `Plane` adds `n_x`, `n_y`, `d_top`, and `d_bot` to those four points.
* `project_plane_numba` returns a zero-initialized `float32` array of shape
  `(n_y, n_x)`.
* The renderer converts each projected array to `uint8`, centers it on the
  global canvas, and streams it to OpenCV.

## 2. Engineering design

### 2.1 CSV parsing and plane preparation

The parser strips whitespace and ignores empty cells. It converts remaining
cells to floating-point values, discards the first value when there are exactly
10 or 13 values, and accepts only 9-value triangle or 12-value trapezoid
coordinate rows. Parsed coordinates are stored as `float32`.

The input loader skips rows that raise `ValueError` during parsing. It also
skips rows if dimension calculation raises an exception. It does not check
finiteness, coplanarity, equal leg lengths, base parallelism, or polygon
self-intersection.

For points `(a1, a2, b, c)`, `plane.get_plane_dimensions` computes:

```text
D_top = ||a2 - a1||
D_bot = ||c - b||
D_leg = ||b - a1||
H     = sqrt(max(0, D_leg^2 - ((D_bot - D_top) / 2)^2))
W     = max(D_top, D_bot)
N_y   = ceil(H) + 1
N_x   = ceil(W) + 1
```

The clamp under the square root prevents a negative radicand; it is not a
substitute for validating the supplied geometry.

### 2.2 Plane projection kernel

`projector.project_plane_numba` is decorated with `numba.njit(parallel=True,
fastmath=True)`. It creates a zero-filled `(n_y, n_x)` image and parallelizes
the outer loop over image rows.

For row `j`, it computes `t = j / (n_y - 1)` (or zero when there is only one
row), then linearly interpolates the left and right 3D endpoints between the
top and bottom bases. The row width is interpolated between `d_top` and
`d_bot`.

For each column `i`, the centered horizontal coordinate is
`i - (n_x - 1) / 2`. The pixel is sampled only when its absolute value is no
greater than half the interpolated row width plus `0.001`. The normalized
horizontal parameter is `0.5 + x_centered / row_width`; if the row width is at
most `0.001`, the point is set to the apex `a1`.

The resulting 3D point is converted to integer indices using `round`. A value
is copied from the volume only if all three indices are in bounds. All other
pixels remain zero. No trilinear interpolation or geometric validity check is
performed.

### 2.3 Canvas, normalization, and encoding

The renderer takes the maximum `n_x` and `n_y` across all parsed planes and
rounds each maximum up to an even integer. It warms up the JIT kernel using
the first plane before opening the writer.

Each slice is scaled against the minimum and maximum of the entire volume,
clipped to `[0, 255]`, and converted to `uint8`; a constant-valued volume
produces all-zero frames. The normalized slice is centered on the shared
canvas, leaving the remaining canvas pixels zero.

OpenCV writer configurations are attempted using the `mp4v` codec, first in
color and then in grayscale mode. If neither opens, video generation fails;
there is no AVI or other-container fallback. Frames are streamed sequentially
and the writer is released in a `finally` block. Output is not written
atomically; an interrupted run may leave a partial MP4 file.

The reported FPS starts after Numba warm-up and writer initialization, and
covers projection, normalization, and frame writes. It is not an end-to-end
startup measurement and is not checked against a performance threshold.

## 3. Failure behavior and known limitations

* Incorrect argument count: usage is printed and exit code `1` is returned.
* NRRD read failure: an error is printed and exit code `1` is returned.
* No usable plane rows: an error is printed and exit code `2` is returned.
* No supported writer opens: an error is printed and exit code `3` is returned.
* CSV open errors and unexpected projection/encoding exceptions are not
  normalized by the CLI and may propagate.
* CSV rows rejected by parsing or dimension calculation are silently skipped.
* The code assumes a usable 3D volume, imposes no supported dtype/shape limits,
  and does not validate geometric properties of planes.
* The repository has no automated test suite or declared package manifest.
