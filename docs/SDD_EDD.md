# System and Engineering Design Documents (SDD / EDD)

## 1. System Design Document (SDD)

### 1.1 Architectural Overview & Dataflow Pipeline
To satisfy the strict memory budget (`NFR-03`) and high throughput (`NFR-01`), the system is architected as a **7-stage streaming pipeline**. The data flows systematically through the following stages:

* **[1] CLI & Configuration** $\rightarrow$ Parses user inputs $\rightarrow$ Sends paths to Loaders.
* **[2] NRRD Loader** $\rightarrow$ Receives `.nrrd` path $\rightarrow$ Outputs 3D NumPy Array $M$ & Global Min/Max.
* **[3] CSV Parser** $\rightarrow$ Receives `.csv` path $\rightarrow$ Outputs Raw Point Records.
* **[4] Geometry Validator** $\rightarrow$ Receives Points $\rightarrow$ Outputs Validated Planes & Canvas Size.
* **[5] Projection Engine** $\rightarrow$ Receives Array $M$ & Planes $\rightarrow$ Outputs 2D Projection Frame.
* **[6] Intensity Mapper** $\rightarrow$ Receives 2D Frame $\rightarrow$ Outputs Fixed-Size `uint8` RGB Frame.
* **[7] Video Encoder** $\rightarrow$ Receives RGB Frames sequentially $\rightarrow$ Outputs final `.mp4` file.

### 1.2 Component Responsibilities & Interfaces
1. **CLI & Configuration (`cli.py`):** Parses arguments (`input.nrrd`, `planes.csv`, `output.mp4`), verifies file existence, and manages exit codes (0, 1, 2, 3).
2. **NRRD Loader (`loader.py`):** Loads the `.nrrd` file into a C-contiguous NumPy array $M$ of shape $(s_x, s_y, s_z)$ and dtype `uint8|uint16|uint32`. Computes global $(V_{\min}, V_{\max})$ in a single pass without duplicating the volume in RAM.
3. **CSV Parser (`parser.py`):** Reads rows, strips whitespace, skips comments/headers, checks isfinite, and outputs structured 3-point or 4-point coordinate tuples.
4. **Geometry Validator & Frame Planner (`geometry.py`):** Validates every plane against REQ-03 ($\delta_{\text{len}}, \delta_{\text{plane}}, \delta_{\parallel}, H > \epsilon$). Pre-calculates each plane's local width $W_p$, perpendicular height $H_p$, and the global even canvas size $(W_{\text{global}}, H_{\text{global}})$.
5. **Projection / Resampling Engine (`projector.py`):** Executes vectorized 2D-to-3D parametric coordinate generation and samples $M$ using Nearest-Neighbor or Trilinear interpolation.
6. **Intensity Mapper & Frame Formatter (`formatter.py`):** Normalizes intensities to `uint8` [0, 255] using global $(V_{\min}, V_{\max})$ and centers the local 2D slice inside the $W_{\text{global}} \times H_{\text{global}}$ black canvas.
7. **Streaming Video Encoder (`encoder.py`):** Writes each formatted `uint8` frame immediately to an H.264 `.mp4` stream via temporary file `.tmp.mp4`, freeing the 2D frame memory immediately after encoding.

---

## 2. Engineering Design Document (EDD)

### 2.1 Refinement of the Assignment's "Sliding Ruler" into a Parametric Model
The original assignment specification outlines a conceptual "Sliding Ruler" loop. In an industrial implementation, direct translation of that pseudo-code introduces critical numerical flaws:
1. Using slant leg length $D_{ab}$ instead of perpendicular height $H$ distorts the vertical aspect ratio.
2. Advancing $a_1, a_2$ at the start of the loop skips the apex $a$.
3. Dividing by $d_{12} = 0$ at the triangle apex causes a division-by-zero crash.
4. Cumulative vector addition ($a_1 += \vec{v}_{ab}$) accumulates floating-point drift.

To eliminate all four defects while preserving the exact geometric intent of the "Sliding Ruler", we formulate the **Unified Parametric Slicing Model**.

### 2.2 Unified Mathematical Model (Triangles & Trapezoids)
Every valid shape is represented by an upper base $(a_1, a_2)$ and a lower base $(b, c)$:
* **For an Isosceles Triangle:** We set $a_1 = a_2 = a$, so upper base width $D_{\text{top}} = 0$.
* **For an Isosceles Trapezoid:** Upper base width is $D_{\text{top}} = dist(a_1, a_2) > 0$.
* In both cases, lower base width is $D_{\text{bot}} = dist(b, c) > 0$ and slant leg length is $D_{\text{leg}} = dist(a_1, b) = dist(a_2, c)$.

**The Parametric Execution:**
Instead of a cumulative loop, we calculate exact coordinates using a vertical parameter $t \in [0, 1]$ and a horizontal parameter $u \in [0, 1]$, ensuring zero drift and safe execution boundaries.
