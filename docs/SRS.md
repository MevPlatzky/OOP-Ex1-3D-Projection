# Software Requirements Specification (SRS)

## 1. Introduction
### 1.1 Purpose
This document specifies the functional and non-functional requirements for the **3D Volumetric Plane Projection Engine**. It serves as a binding engineering contract for design, implementation, and verification.

### 1.2 Scope
The system is a Command Line Interface (CLI) application that loads a 3D volumetric dataset (`.nrrd`), parses a sequence of 3D geometric slicing planes (isosceles triangles or isosceles trapezoids) from a `.csv` file, projects the intersected 3D voxel intensities onto 2D frames, and streams them into a standardized `.mp4` video file.

---

## 2. Overall Description & Assumptions
* **Operating Environment (NFR-05):** Python $\ge 3.10$ on 64-bit Linux/macOS/Windows. Required packages: `numpy`, `pynrrd`, `opencv-python` (or `imageio-ffmpeg`), and `pytest`.
* **Coordinate System Contract (REQ-07):** All geometric coordinates in the `.csv` file are defined directly in **continuous 3D Voxel Coordinates** $(x, y, z)$ corresponding to array axes $(0, 1, 2)$ in C-contiguous order `M[x, y, z]`. Physical world metadata (`space origin`, `space directions`) in the NRRD header is explicitly ignored for geometric slicing.

---

## 3. Functional Requirements

* **REQ-01 (NRRD Volume Loading):** The system shall load 3D volumetric matrices from `.nrrd` files supporting unsigned integer data types `uint8`, `uint16`, and `uint32`, where each spatial dimension satisfies $1 \le s_x, s_y, s_z \le 2^{10}$ (up to $1024^3$ voxels).
* **REQ-02 (CSV Input Parsing):** The system shall parse a `.csv` file describing sequential slicing planes.
* **REQ-03 (Geometric Validation):** The system shall validate every CSV row to confirm it forms a non-degenerate **Isosceles Triangle** (3 points: $a, b, c$) or **Isosceles Trapezoid** (4 points: $a_1, a_2, b, c$) using the following dimensional tolerance rules with $\epsilon = 0.001$:
  1. **Finiteness:** All coordinates must be finite real numbers (no `NaN` or `Infinity`).
  2. **Positive Base & Edge Lengths:**
     * Triangle ($a_1 = a_2 = a$): $dist(b, c) > \epsilon$, $dist(a, b) > \epsilon$, $dist(a, c) > \epsilon$.
     * Trapezoid: $dist(a_1, a_2) > \epsilon$, $dist(b, c) > \epsilon$, $dist(a_1, b) > \epsilon$, $dist(a_2, c) > \epsilon$.
  3. **Isosceles Leg Equality (Length units in voxels):**
     $$\delta_{\text{len}} = |dist(a_1, b) - dist(a_2, c)| < \epsilon$$
  4. **Non-Degeneracy & Positive Perpendicular Height:**
     * Triangle area / cross-product check: $\frac{\|(b - a) \times (c - a)\|}{dist(b, c)} > \epsilon$ ( guarantees non-collinearity and perpendicular height $H > \epsilon$).
     * Trapezoid perpendicular height between bases: $H = \frac{\|(a_2 - a_1) \times (b - a_1)\|}{dist(a_1, a_2)}$ (or via base $bc$) must satisfy $H > \epsilon$.
  5. **Trapezoid Coplanarity (Length units in voxels):** With plane normal $\vec{n} = (b - a_1) \times (c - a_1)$ where $\|\vec{n}\| > \epsilon$:
     $$\delta_{\text{plane}} = \frac{|(a_2 - a_1) \cdot \vec{n}|}{\|\vec{n}\|} < \epsilon$$
  6. **Trapezoid Base Parallelism & Non-Self-Intersection (Unitless):** Let $\vec{u} = a_2 - a_1$ and $\vec{v} = c - b$. The bases must be parallel:
     $$\delta_{\parallel} = \frac{\|\vec{u} \times \vec{v}\|}{\|\vec{u}\|\|\vec{v}\|} < \epsilon$$
     Furthermore, to prevent self-intersecting ("bowtie") polygons, the bases must share the same orientation: $\vec{u} \cdot \vec{v} > 0$. *(Note: An inclusive definition of trapezoid is adopted; rectangles/rectangles with equal bases are valid).*
* **REQ-04 (2D Plane Projection):** The system shall project each valid 3D plane onto a 2D image matrix using a parametric mapping that preserves the true perpendicular height $H = \sqrt{D_{\text{leg}}^2 - \left(\frac{D_{bc} - D_{a_1a_2}}{2}\right)^2}$ and horizontal centering.
* **REQ-05 (CLI & Video Export):** The system shall be executable via:
  `python Ex0.py <input.nrrd> <planes.csv> <output.mp4>`
* **REQ-06 (CSV Schema Contract):** Each row in the `.csv` file shall contain either 9 comma-separated floats ($a_x, a_y, a_z, b_x, b_y, b_z, c_x, c_y, c_z$ for a triangle) or 12 comma-separated floats ($a_{1x}, a_{1y}, a_{1z}, a_{2x}, a_{2y}, a_{2z}, b_x, b_y, b_z, c_x, c_y, c_z$ for a trapezoid). Standard decimal and scientific notation (e.g., `1.5e2`) are supported. Empty lines and an optional single header line (starting with non-numeric characters) shall be safely ignored.
* **REQ-07 (Coordinate Space & Axis Ordering):** Voxel coordinates $(x, y, z)$ map directly to array indices $[i, j, k]$ where $0 \le x < s_x$, $0 \le y < s_y$, and $0 \le z < s_z$.
* **REQ-08 (Output Resolution, Sampling Step & Masking):**
  * Sampling resolution is 1 pixel per 1.0 voxel unit of length.
  * For a plane with maximum base width $W_p = \max(dist(a_1, a_2), dist(b, c))$ and perpendicular height $H_p$, the local frame dimensions are $W_{\text{frame}} = \text{ceil}(W_p) + 1$ and $H_{\text{frame}} = \text{ceil}(H_p) + 1$.
  * Pixels inside the 2D frame that fall outside the triangle/trapezoid boundary (out-of-polygon) shall be assigned value `0` (black background).
* **REQ-09 (Interpolation, Rounding & Volume Boundaries):**
  * **Default Sampling:** Nearest-Neighbor interpolation by rounding continuous coordinates $(x, y, z)$ to the nearest integer via `np.rint` (round half to even).
  * **Optional Sampling:** Trilinear interpolation across the 8 surrounding voxels via CLI flag `--interp trilinear`.
  * **Out-of-Volume Policy:** Any 3D sample point $p = (x, y, z)$ where $x < 0$, $x > s_x - 1$, $y < 0$, $y > s_y - 1$, $z < 0$, or $z > s_z - 1$ is strictly out-of-bounds and shall be assigned intensity `0`.
* **REQ-10 (Intensity Normalization to 8-Bit Video):**
  * For `uint8` volumes, voxel values `[0, 255]` are preserved directly.
  * For `uint16` and `uint32` volumes, intensities are mapped linearly to `[0, 255]` (`uint8`) using the **global volume minimum and maximum** ($V_{\min}, V_{\max}$) computed once upon loading to prevent frame-to-frame flickering:
    $$I_{\text{out}} = \text{clip}\left(\text{round}\left(255 \cdot \frac{I - V_{\min}}{\max(V_{\max} - V_{\min}, 1)}\right), 0, 255\right)$$
  * Out-of-polygon and out-of-volume pixels always map to `0`.
* **REQ-11 (Video Container, Codec & Variable Frame Size Policy):**
  * Output format: `.mp4` container, `H.264` (`avc1`/`mp4v`) codec, `30 FPS` playback rate, 8-bit grayscale converted to 3-channel RGB (`yuv420p` compatible).
  * **Global Canvas Policy:** Across all valid rows in the CSV, the system computes $W_{\text{global}} = \max(W_{\text{frame}})$ and $H_{\text{global}} = \max(H_{\text{frame}})$, rounds both up to the nearest **even integer** (required by `yuv420p`), and centers each rendered frame on this fixed $W_{\text{global}} \times H_{\text{global}}$ canvas padded with `0`.
* **REQ-12 (Error Handling, Exit Codes & Atomic Output):**
  * **Fail-Fast Validation:** All CSV rows are validated before video encoding starts. If the CSV is empty or any row violates `REQ-03` or `REQ-06`, the system logs the exact row number and reason to `stderr`, produces no output file, and exits with code:
    * `Exit Code 0`: Success.
    * `Exit Code 1`: CLI usage or file I/O error (missing/corrupt NRRD or CSV).
    * `Exit Code 2`: CSV format or geometric validation error.
    * `Exit Code 3`: Video encoding / runtime error.
  * **Atomic File Output:** Video is written to a temporary file and renamed to `<output.mp4>` (overwriting any existing file) only upon successful completion. On failure, partial files are deleted.

---

## 4. Non-Functional Requirements

* **NFR-01 (Projection Performance):**
  * **Projection FPS (Core Engine):** On a reference machine (8-core CPU, 16 GB RAM), sampling 1,000 consecutive $500 \times 500$ frames from a preloaded $500^3$ `uint8` volume using Nearest-Neighbor vectorized NumPy operations shall achieve strictly **$> 30\text{ FPS}$** (Mandatory Must), with a target of **$\ge 100\text{ FPS}$** (Expected) and **$\ge 300\text{ FPS}$** (Stretch Goal).
  * **End-to-End FPS** (including NRRD loading and MP4 encoding) shall be measured and reported separately.
* **NFR-02 (Reliability & Graceful Failure):** The system shall never crash with an unhandled Python traceback on malformed user inputs or out-of-bounds coordinates.
* **NFR-03 (Memory Budget & Streaming):** Peak RAM usage shall not exceed **$1.5 \times$ the raw NRRD volume size + 256 MB overhead** (e.g., $\le 6.25\text{ GiB}$ for a 4 GiB `uint32` $1024^3$ volume). Frames must be generated and streamed one-by-one to the video encoder without accumulating all frames in memory.
* **NFR-04 (Numerical Reproducibility):** Given identical inputs and interpolation settings, the system shall produce bit-identical 2D projection matrices across runs.
* **NFR-06 (Geometric & Sampling Accuracy):** Projected 2D matrices prior to lossy video compression shall match analytical ground-truth values with 0 error for integer Nearest-Neighbor coordinates and within $\le 10^{-4}$ relative error for Trilinear interpolation.
