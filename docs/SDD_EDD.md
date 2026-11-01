# System and Engineering Design Documents (SDD / EDD)

This document defines the global system architecture (SDD) and the detailed mathematical and algorithmic design of the core projection engine (EDD).

---

## 1. System Design Document (SDD)

### 1.1 Architectural Overview & Dataflow Pipeline
To satisfy the strict memory budget (`NFR-03`) and high throughput (`NFR-01`), the system is architected as a **7-stage streaming pipeline** with no in-memory accumulation of output video frames:

1. **[Stage 1: CLI & Configuration]** $\rightarrow$ Parses paths (`input.nrrd`, `planes.csv`, `output.mp4`) and options (`--interp`).
2. **[Stage 2: NRRD Loader]** $\rightarrow$ Reads the `.nrrd` file into a 3D NumPy array $M$ and extracts global intensity bounds $(V_{\min}, V_{\max})$.
3. **[Stage 3: CSV Parser]** $\rightarrow$ Reads and sanitizes raw 3-point (triangle) or 4-point (trapezoid) coordinate rows from `planes.csv`.
4. **[Stage 4: Geometry Validator & Frame Planner]** $\rightarrow$ Validates each plane against geometric tolerances ($\epsilon = 0.001$) and computes the global even-sized video canvas $(W_{\text{global}}, H_{\text{global}})$.
5. **[Stage 5: Projection / Resampling Engine]** $\rightarrow$ Executes the core vectorized 2D-to-3D slicing algorithm on $M$ to produce a raw 2D slice $E$.
6. **[Stage 6: Intensity Mapper & Frame Formatter]** $\rightarrow$ Normalizes pixel values to `uint8` $[0, 255]$ and centers each 2D slice inside the global black canvas.
7. **[Stage 7: Streaming Video Encoder]** $\rightarrow$ Encodes each frame on-the-fly to a temporary `.tmp.mp4` stream and performs an atomic rename to `output.mp4` upon completion.

### 1.2 Component Responsibilities & Interfaces
1. **CLI & Configuration (`cli.py`):** Parses command-line arguments, verifies input file existence, and enforces standardized process exit codes (`0` = Success, `1` = I/O Error, `2` = Validation/CSV Error, `3` = Runtime/Encoding Error).
2. **NRRD Loader (`loader.py`):** Loads the `.nrrd` volume into a C-contiguous NumPy array $M$ of shape $(s_x, s_y, s_z)$ where $1 \le s_x, s_y, s_z \le 2^{10}$ and `dtype` $\in \{\text{uint8}, \text{uint16}, \text{uint32}\}$. Computes global $(V_{\min}, V_{\max})$ in a single pass without duplicating the volume in RAM.
3. **CSV Parser (`parser.py`):** Reads rows, strips whitespace, skips empty lines or headers, verifies all values are finite numbers (`isfinite`), and outputs structured 3-point $(a, b, c)$ or 4-point $(a_1, a_2, b, c)$ coordinate tuples.
4. **Geometry Validator & Frame Planner (`geometry.py`):** Validates every plane against `REQ-03` ($\delta_{\text{len}} < \epsilon$, coplanarity $\delta_{\text{plane}} < \epsilon$, parallel bases $\delta_{\parallel} < \epsilon$, non-self-intersection, and perpendicular height $H > \epsilon$). Pre-calculates each plane's discrete local dimensions $(N_x, N_y)$ and the global even canvas size $(W_{\text{global}}, H_{\text{global}})$.
5. **Projection / Resampling Engine (`projector.py`):** Implements the core Unified Parametric Slicing Algorithm (detailed in Section 2) using vectorized NumPy broadcasting and samples $M$ via Nearest-Neighbor (default) or Trilinear interpolation.
6. **Intensity Mapper & Frame Formatter (`formatter.py`):** Linearly scales raw voxel intensities from $[V_{\min}, V_{\max}]$ to `uint8` $[0, 255]$ and centers the local $N_x \times N_y$ slice inside the $W_{\text{global}} \times H_{\text{global}}$ black canvas.
7. **Streaming Video Encoder (`encoder.py`):** Writes each formatted `uint8` frame immediately to an H.264 `.mp4` stream at 30 FPS via a temporary file, freeing the 2D frame memory immediately after encoding.

---

## 2. Engineering Design Document (EDD) – Core Projection Algorithm

### 2.1 Refinement of the Assignment's "Sliding Ruler" into a Parametric Model
The original assignment specification outlines a conceptual "Sliding Ruler" loop. Direct translation of that pseudo-code introduces four numerical defects:
1. Using slant leg length $D_{ab}$ instead of perpendicular height $H$ distorts the vertical aspect ratio.
2. Advancing $a_1, a_2$ at the start of the loop skips the triangle apex $a$.
3. Dividing by $d_{12} = 0$ at the triangle apex causes a division-by-zero error.
4. Cumulative vector addition ($a_1 \mathrel{+}= \vec{v}_{ab}$) accumulates floating-point drift over hundreds of steps.

To eliminate all four defects while preserving the exact geometric behavior of the "Sliding Ruler", the engine implements the **Unified Parametric Slicing Algorithm**.

### 2.2 Unified Mathematical Model (Triangles & Trapezoids)
Every valid slicing plane $p$ is represented by an upper base $(a_1, a_2)$ and a lower base $(b, c)$ in 3D space:
* **Isosceles Triangle (3 points $a, b, c$):** Set $a_1 = a_2 = a$, giving upper base width $D_{\text{top}} = 0$.
* **Isosceles Trapezoid (4 points $a_1, a_2, b, c$):** Upper base width is $D_{\text{top}} = \text{dist}(a_1, a_2) > 0$.
* **Shared Properties:** Lower base width is $D_{\text{bot}} = \text{dist}(b, c) > 0$, and equal slant leg length is $D_{\text{leg}} = \text{dist}(a_1, b) = \text{dist}(a_2, c)$.

### 2.3 Step-by-Step Mathematical Formulation

#### Step 1: True Perpendicular Height & Discrete Frame Dimensions
The perpendicular height $H$ of the plane in voxel units is derived via the Pythagorean theorem:

$$H = \sqrt{D_{\text{leg}}^2 - \left(\frac{D_{\text{bot}} - D_{\text{top}}}{2}\right)^2}$$

The maximum horizontal width of the polygon is $W = \max(D_{\text{top}}, D_{\text{bot}})$. Using a 1:1 voxel-to-pixel scale, the discrete integer dimensions of the local 2D image matrix $E$ (with origin $(0,0)$ at the top-left corner) are:

$$N_y = \text{ceil}(H) + 1, \quad N_x = \text{ceil}(W) + 1$$

#### Step 2: Parametric Row Endpoints (The "Sliding Ruler" Positions)
For each discrete row index $j \in \{0, 1, \dots, N_y - 1\}$ from top to bottom, define the normalized vertical parameter $t \in [0, 1]$:

$$t(j) = \frac{j}{N_y - 1} \quad (\text{for } N_y > 1, \text{ else } 0)$$

The left endpoint $L(t)$ and right endpoint $R(t)$ of the sliding ruler at row $j$ are computed directly without cumulative drift:

$$L(t) = (1 - t)a_1 + t \cdot b$$

$$R(t) = (1 - t)a_2 + t \cdot c$$

The physical width of the horizontal scanline at row $j$ is:

$$w(t) = \|R(t) - L(t)\|_2 = (1 - t)D_{\text{top}} + t \cdot D_{\text{bot}}$$

#### Step 3: Horizontal Centering & 3D Sample Point Generation
For each discrete column index $i \in \{0, 1, \dots, N_x - 1\}$ from left to right, the horizontal offset from the center of the image is:

$$x(i) = i - \frac{N_x - 1}{2}$$

*(Note: This is mathematically equivalent to the assignment's centering formula $i = \frac{W}{2} - \frac{w(t)}{2} + x_1$ where $x_1 \in [0, w(t)]$)*.

* **Out-of-Polygon Masking:** A pixel $(i, j)$ lies inside the triangle/trapezoid boundary if and only if:

$$|x(i)| \le \frac{w(t)}{2} + \epsilon$$

Pixels outside this bound are assigned background value $v = 0$.

* **3D Coordinate Calculation:** For valid interior pixels:
  * If $w(t) \le \epsilon$ (at the exact apex of a triangle where $t = 0$ and $x(i) = 0$):

$$P(i, j) = a_1$$

  * If $w(t) > \epsilon$, compute the normalized horizontal parameter $u \in [0, 1]$ along the current scanline:

$$u(i, j) = \frac{1}{2} + \frac{x(i)}{w(t)}$$

  * The exact 3D sample point in voxel space is:

$$P(i, j) = (1 - u)L(t) + uR(t)$$

#### Step 4: Vectorized Voxel Sampling & Boundary Enforcement
To achieve $> 100\text{ FPS}$ (and target $300+\text{ FPS}$) in Python (`NFR-01`), Steps 2–3 are executed across all pixels simultaneously using 2D NumPy array broadcasting without Python `for` loops:

1. **Grid Construction:** Generate 1D index arrays $i \in [0, N_x - 1]$ of shape $(1, N_x)$ and $j \in [0, N_y - 1]$ of shape $(N_y, 1)$.
2. **Broadcasted 3D Coordinates:** Compute $t(j)$, $L(t)$, $R(t)$, $w(t)$, $u(i, j)$, and the full 3D coordinate tensor $P$ of shape $(N_y, N_x, 3)$.
3. **Volume Boundary Check (`REQ-09`):** Construct a boolean mask verifying that the pixel is both inside the polygon and strictly within the 3D matrix bounds $(s_x, s_y, s_z)$:

$$\text{mask}(i, j) = \left(|x(i)| \le \frac{w(t)}{2} + \epsilon\right) \land (0 \le P_x \le s_x - 1) \land (0 \le P_y \le s_y - 1) \land (0 \le P_z \le s_z - 1)$$

4. **Voxel Sampling:**
   * Initialize the 2D output matrix $E = \text{zeros}((N_y, N_x))$ with `v = 0`.
   * **Nearest-Neighbor Mode:** Round valid 3D coordinates to the nearest integer indices $(i_x, i_y, i_z) = \text{rint}(P[\text{mask}])$ and sample directly in C-speed:

$$E[\text{mask}] = M[i_x, i_y, i_z]$$

   * **Trilinear Mode (Optional):** Extract integer floor indices $\lfloor P \rfloor$ and fractional weights $(\Delta_x, \Delta_y, \Delta_z)$ to compute the weighted average of the 8 surrounding voxels.
5. **Return Frame:** Return the populated 2D matrix $E$ to Stage 6 for normalization and video encoding.
