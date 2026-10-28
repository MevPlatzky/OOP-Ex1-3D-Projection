# Software Test Plan & Description (STP / STD)

## 1. Software Test Plan (STP)

### 1.1 Scope & Objectives
This test plan verifies the mathematical correctness, geometric validation, memory safety, I/O resilience, and rendering speed of the 3D Volumetric Plane Projection Engine against `REQ-01..12` and `NFR-01..06`.

### 1.2 Synthetic Ground Truth Methodology
Because lossy `.mp4` video compression alters individual pixel values, geometric and sampling accuracy (`REQ-04`, `REQ-09`, `NFR-06`) **must be tested on the raw 2D projection matrices prior to video encoding** using an analytical **Synthetic Ground Truth Volume**:
$$M(x, y, z) = x + 10y + 100z \quad (\text{dtype: } \text{uint16})$$
For any sampled 3D coordinate $p = (x, y, z)$ inside the volume:
* Under Nearest-Neighbor, $M(\text{round}(x), \text{round}(y), \text{round}(z))$ is known analytically (e.g., $p = (2, 1, 3) \implies 2 + 10(1) + 100(3) = 312$).
* Under Trilinear Interpolation, because $M(x,y,z)$ is linear in all axes, the exact interpolated value at fractional coordinates is also known analytically (e.g., $p = (0.5, 1.25, 2.0) \implies 0.5 + 12.5 + 200 = 213.0$).
This guarantees immediate detection of axis swaps (e.g., $x \leftrightarrow z$), off-by-one errors, or interpolation bugs.

### 1.3 Test Levels & Tools
* **Unit Tests (`pytest`):** Isolate `Geometry Validator`, `Parametric Projector`, and `Intensity Mapper`.
* **Integration & System Tests (`pytest`):** End-to-end CLI execution, `.mp4` container decoding verification via `cv2.VideoCapture`, and error exit-code verification.
* **Performance & Memory Benchmarks (`pytest-benchmark` / `tracemalloc`):** Measure Projection FPS, End-to-End FPS, and Peak RAM.

### 1.4 Entry & Exit Criteria
* **Entry Criteria:** All modules pass static linting (`flake8`/`ruff`) and type checking (`mypy`).
* **Exit Criteria:** 100% pass rate across `TC-01` through `TC-25`, $\ge 90\%$ line coverage on core modules, zero critical defects, verified benchmark $> 30\text{ FPS}$ on reference $500^3$ volume, and Peak RAM within `NFR-03` budget.

---

## 2. Traceability Matrix

| Requirement ID | Implementing Component | Verifying Test Cases |
|---|---|---|
| **REQ-01** (NRRD Loading) | `NRRD Loader` | TC-16, TC-19, TC-21 |
| **REQ-02, REQ-06** (CSV Schema) | `CSV Parser` | TC-14, TC-20, TC-22 |
| **REQ-03** (Geometry Validation) | `Geometry Validator` | TC-01..04, TC-09..14 |
| **REQ-04, REQ-07, REQ-08** (Projection & Masking) | `Projection Engine` | TC-01, TC-02, TC-05, TC-06, TC-15, TC-16 |
| **REQ-09** (Interpolation & Bounds) | `Projection Engine` | TC-05, TC-06, TC-17, TC-18 |
| **REQ-10** (Intensity Normalization) | `Intensity Mapper` | TC-19 |
| **REQ-11** (MP4 & Global Canvas) | `Streaming Video Encoder` | TC-20, TC-23 |
| **REQ-05, REQ-12, NFR-02** (CLI, Errors, Atomic Output) | `CLI & Encoder` | TC-04, TC-07, TC-14, TC-21, TC-22 |
| **NFR-01** (Performance FPS) | `Projection Engine` | TC-08, TC-24 |
| **NFR-03** (Memory Budget) | `Pipeline / Streaming Encoder` | TC-25 |
| **NFR-04, NFR-06** (Accuracy & Reproducibility) | `Projection Engine` | TC-15, TC-17 |

---

## 3. Software Test Descriptions (STD)

| TC ID | Title | Verifies | Input Data / Setup | Expected Result (Exact & Measurable) |
|---|---|---|---|---|
| **TC-01** | Valid Isosceles Triangle Projection | REQ-03, REQ-04 | Synthetic volume $20^3$. Triangle $a=(2,2,2), b=(2,8,10), c=(2,8,-6)$ ($D_{ab}=D_{ac}=10, D_{bc}=16, H=6$). | Validator passes. Output 2D matrix has shape $17 \times 7$ ($N_x \times N_y$). Apex pixel $(8, 0)$ equals $M(2,2,2) = 222$. |
| **TC-02** | Valid Isosceles Trapezoid Projection | REQ-03, REQ-04 | Synthetic volume $20^3$. Coplanar trapezoid $a_1=(5,4,2), a_2=(5,8,2), b=(5,1,6), c=(5,11,6)$ ($D_{\text{top}}=4, D_{\text{bot}}=10, D_{\text{leg}}=5, H=4$). | Validator passes. Output 2D matrix has shape $11 \times 5$. Top-left base endpoint $(3, 0)$ equals $M(5,4,2)=245$; bottom-right $(10, 4)$ equals $M(5,11,6)=715$. |
| **TC-03** | Epsilon Boundary Acceptance | REQ-03 | Triangle points where leg difference $\delta_{\text{len}} = 0.00095 < \epsilon$ and $\delta_{\text{len}} = 0.0001$. | Both geometries are accepted as valid without raising `ValueError`. |
| **TC-04** | Asymmetric Leg Rejection | REQ-03, REQ-12 | Triangle points where $\delta_{\text{len}} = 0.0015 > \epsilon$. Run via CLI. | Validator raises `ValueError`. CLI logs row error to `stderr`, exits with `Exit Code 2`, no `.mp4` created. |
| **TC-05** | Out-of-Polygon & Out-of-Volume Padding | REQ-08, REQ-09 | Volume $10^3$ filled with `100`. Triangle extends from $(5,5,5)$ to $(5, 15, 15)$ (exceeding index 9). | Pixels outside triangle mask (top corners of 2D frame) and pixels where 3D coord $> 9$ equal `0`. Valid interior pixels equal `100`. |
| **TC-06** | Negative Coordinates Handling | REQ-09 | Synthetic volume $10^3$. Plane spans $(-5, 2, 2)$ to $(5, 2, 8)$. | All sampled points with $x < 0$ are assigned `0` (not wrapped around via Python negative indexing!). Points with $x \ge 0$ match $M(x,y,z)$. |
| **TC-07** | Missing Input File CLI Handling | REQ-05, REQ-12 | Run `python Ex0.py missing.nrrd valid.csv out.mp4`. | Process terminates with `Exit Code 1`, prints error message to `stderr`, zero unhandled tracebacks, `out.mp4` does not exist. |
| **TC-08** | Core Projection Speed Benchmark | NFR-01 | Preloaded $500^3$ `uint8` volume, 1,000 slices of size $500 \times 500$, Nearest-Neighbor. | Measured `Projection FPS` is strictly $> 30\text{ FPS}$. Benchmark report logs exact mean/std frame time. |
| **TC-09** | Collinear Triangle Rejection | REQ-03 | Points $a=(0,0,0), b=(-1,0,0), c=(1,0,0)$ ($\delta_{\text{len}}=0$, but collinear). | Rejected with `ValueError` due to zero cross-product area / $H = 0 \le \epsilon$. |
| **TC-10** | Collinear Trapezoid Rejection | REQ-03 | Points $a_1=(0,0,0), a_2=(2,0,0), b=(-1,0,0), c=(3,0,0)$. | Rejected with `ValueError` due to perpendicular height $H = 0 \le \epsilon$. |
| **TC-11** | Self-Intersecting ("Bowtie") Trapezoid Rejection | REQ-03 | Points $a_1=(0,0,0), a_2=(4,0,0), b=(4,3,0), c=(0,3,0)$ (crossed legs, $\vec{u}\cdot\vec{v} < 0$). | Rejected with `ValueError` due to opposing base orientation ($\vec{u} \cdot \vec{v} \le 0$). |
| **TC-12** | Zero-Length Edge / Zero Height Rejection | REQ-03 | Triangle with $b = c = (1,1,1)$ or $a = b = c = (0,0,0)$. | Rejected cleanly with `ValueError` before any division occurs. |
| **TC-13** | Exact Epsilon Threshold ($\Delta = \epsilon$) | REQ-03 | Triangle where $|dist(a,b) - dist(a,c)| = 0.001000$. | Rejected (`ValueError`), verifying strict inequality ($< \epsilon$). |
| **TC-14** | `NaN`, `Infinity`, and Missing Values in CSV | REQ-03, REQ-06 | CSV rows containing `NaN`, `inf`, `-inf`, or only 7 columns. | Rejected by parser/validator with `Exit Code 2` and descriptive row error message. |
| **TC-15** | Diagonal Plane Synthetic Ground Truth | REQ-04, NFR-06 | Synthetic volume $M(x,y,z)=x+10y+100z$. 3D diagonal plane across $(x,y,z)$. | Every valid pixel in raw 2D matrix matches analytical formula $x+10y+100z$ with 0 error. |
| **TC-16** | NRRD Axis Ordering & Ignored Physical Metadata | REQ-01, REQ-07 | NRRD with anisotropic metadata `space directions: (0.5, 0.5, 2.0)` and non-zero origin. | System samples strictly by voxel coordinates `M[x,y,z]` matching `REQ-07` contract. |
| **TC-17** | Fractional Coordinates (Nearest vs Trilinear) | REQ-09, NFR-06 | Synthetic volume $M(x,y,z)=x+10y+100z$. Sample at $p=(0.4, 1.6, 2.0)$. | Nearest-Neighbor yields $M(0, 2, 2) = 220$. Trilinear yields $0.4 + 16 + 200 = 216.4$ (within $10^{-4}$). |
| **TC-18** | Exact Volume Boundary Sampling | REQ-09 | Sample points at exact boundary $(0, 0, 0)$ and $(s_x-1, s_y-1, s_z-1)$, vs $(s_x-0.9, 0, 0)$ and $(s_x-0.4, 0, 0)$. | Boundary points $(0,0,0)$ and $(s_x-1, \dots)$ succeed; $s_x - 0.4 > s_x - 1$ is masked as `0` out-of-bounds. |
| **TC-19** | Data Types `uint8`, `uint16`, `uint32` Normalization | REQ-01, REQ-10 | Three NRRD volumes (`uint8` max 200, `uint16` max 40000, `uint32` max 1000000). | `uint8` keeps 200; `uint16` (0..40000) maps 20000 to 128 and 40000 to 255; `uint32` maps max to 255. |
| **TC-20** | Multi-Row CSV with Varying Plane Sizes | REQ-11 | Row 1 produces $51 \times 31$ frame; Row 2 produces $103 \times 79$ frame. | Global video canvas is rounded to even dimensions $104 \times 80$. Both frames are centered with black padding. |
| **TC-21** | Corrupted NRRD / Unsupported Dtype | REQ-01, REQ-12 | Corrupted NRRD file or `float64` NRRD file. | System logs error, exits with `Exit Code 1`, no `.mp4` created. |
| **TC-22** | Empty CSV & Mid-File Bad Row Atomic Policy | REQ-12 | (a) 0-byte CSV; (b) 10 valid rows followed by 1 invalid row. | Both exit with `Exit Code 2`. Zero partial `.mp4` or `.tmp.mp4` files left on disk. |
| **TC-23** | End-to-End MP4 Playback & Metadata Verification | REQ-05, REQ-11 | 30 valid CSV rows on $100^3$ volume. Open output `.mp4` with `cv2.VideoCapture`. | File opens cleanly, `FRAME_COUNT == 30`, `FPS == 30`, width & height are even integers matching global canvas. |
| **TC-24** | End-to-End Pipeline Benchmark | NFR-01, NFR-04 | 100 frames on $500^3$ volume. Run twice. | Reports both Projection FPS and End-to-End FPS. Raw 2D matrices across both runs are bit-identical. |
| **TC-25** | Streaming Memory Ceiling Verification | NFR-03 | $512^3$ `uint32` volume (512 MB) with 500 frames. Monitor via `tracemalloc`. | Peak RAM stays strictly below $1.5 \times 512\text{ MB} + 256\text{ MB} = 1024\text{ MB}$, proving frames are not accumulated in RAM. |
