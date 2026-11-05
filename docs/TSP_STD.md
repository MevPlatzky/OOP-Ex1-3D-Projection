# Software Test Plan & Description (STP / STD)

## 1. Software Test Plan (STP)

### 1.1 Scope & Objectives
This test plan verifies the mathematical correctness, geometric validation, memory safety, I/O resilience, and rendering speed of the 3D Volumetric Plane Projection Engine against the system requirements.

### 1.2 Synthetic Ground Truth Methodology
Because lossy `.mp4` video compression alters individual pixel values, geometric and sampling accuracy **must be tested on the raw 2D projection matrices prior to video encoding** using an analytical **Synthetic Ground Truth Volume**:
$$M(x, y, z) = x + 10y + 100z \quad (\text{dtype: } \text{uint16})$$
For any sampled 3D coordinate $p = (x, y, z)$ inside the volume, under Nearest-Neighbor, $M(\text{round}(x), \text{round}(y), \text{round}(z))$ is known analytically. This guarantees immediate detection of axis swaps, off-by-one errors, or interpolation bugs.

### 1.3 Test Levels & Tools
* **Unit Tests (`pytest`):** Isolate `Geometry Validator`, `Parametric Projector`, and `Intensity Mapper`.
* **Integration & System Tests (`pytest`):** End-to-end CLI execution, `.mp4` container decoding verification, and error exit-code verification.
* **Performance & Memory Benchmarks (`pytest-benchmark`):** Measure Projection FPS, End-to-End FPS, and Peak RAM.

### 1.4 Entry & Exit Criteria
* **Entry Criteria:** All modules pass static linting and code compiles.
* **Exit Criteria:** 100% pass rate across `TC-01` through `TC-25`, zero critical defects, verified benchmark $> 30\text{ FPS}$ on reference $500^3$ volume.

---

## 2. Traceability Matrix

| Requirement ID | Implementing Component | Verifying Test Cases |
|---|---|---|
| **REQ-01..02** (I/O & Parsing) | `Loader` & `CSV Parser` | TC-14, TC-16, TC-19, TC-20, TC-21, TC-22 |
| **REQ-03** (Geometry Validation) | `Geometry Validator` | TC-01..04, TC-09..14 |
| **REQ-04..09** (Projection & Masking) | `Projection Engine` | TC-01, TC-02, TC-05, TC-06, TC-15..18 |
| **REQ-10..12** (Video & CLI Output) | `Intensity Mapper` & `Encoder` | TC-04, TC-07, TC-19, TC-23 |
| **NFR-01** (Performance FPS) | `Projection Engine` | TC-08, TC-24 |
| **NFR-03** (Memory Budget) | `Streaming Pipeline` | TC-25 |

---

## 3. Software Test Descriptions (STD)

| TC ID | Title | Input Data / Setup | Expected Result |
|---|---|---|---|
| **TC-01** | Valid Isosceles Triangle | Synthetic volume. Triangle $a=(2,2,2), b=(2,8,10), c=(2,8,-6)$. | Validator passes. Apex pixel equals $M(2,2,2) = 222$. |
| **TC-02** | Valid Isosceles Trapezoid | Coplanar trapezoid $a_1=(5,4,2), a_2=(5,8,2), b=(5,1,6), c=(5,11,6)$. | Validator passes. Output base matches calculated matrix bounds. |
| **TC-03** | Epsilon Boundary Acceptance | Triangle where leg diff $\delta_{\text{len}} = 0.00095 < 0.001$. | Accepted as valid without `ValueError`. |
| **TC-04** | Asymmetric Leg Rejection | Triangle where $\delta_{\text{len}} = 0.0015 > 0.001$. | `ValueError` raised. CLI logs error, exits code 2. |
| **TC-05** | Out-of-Volume Padding | Plane extends 20% outside $M$. | Out-of-bounds pixels strictly masked as `0`. |
| **TC-06** | Negative Coordinates | Plane spans $(-5, 2, 2)$ to $(5, 2, 8)$. | Points with $x < 0$ assigned `0`. No crash. |
| **TC-07** | Missing Input File CLI | Run `python Ex0.py missing.nrrd data.csv out.mp4`. | Exits cleanly, code 1, prints error. |
| **TC-08** | FPS Speed Benchmark | Preloaded $500^3$ volume, 1000 slices. | Mean processing speed strictly $> 30\text{ FPS}$. |
| **TC-09** | Collinear Triangle Rejection | Points $a=(0,0,0), b=(-1,0,0), c=(1,0,0)$. | Rejected (`ValueError`) due to zero height. |
| **TC-10** | Collinear Trapezoid Rejection | Points $a_1=(0,0,0), a_2=(2,0,0), b=(-1,0,0), c=(3,0,0)$. | Rejected due to zero perpendicular height. |
| **TC-11** | Self-Intersecting Trapezoid | Crossed legs forming a "bowtie" shape. | Rejected due to opposing base orientation. |
| **TC-12** | Zero-Length Edge Rejection | Triangle with $b = c = (1,1,1)$. | Rejected before division by zero occurs. |
| **TC-13** | Exact Epsilon Threshold | Triangle with leg diff exactly $0.001000$. | Rejected (verifying strict $< \epsilon$ inequality). |
| **TC-14** | `NaN` / Missing CSV Values | CSV rows with `NaN`, `inf`, or 7 columns. | Rejected by parser with descriptive row error. |
| **TC-15** | Diagonal Plane Ground Truth | Synthetic volume $x+10y+100z$. 3D diagonal plane. | Raw 2D pixels match $x+10y+100z$ with 0 error. |
| **TC-16** | Ignored Physical Metadata | NRRD with anisotropic metadata space origins. | Sampled strictly by integer voxel indices. |
| **TC-17** | Fractional Interpolation | Sample at $p=(0.4, 1.6, 2.0)$. | Nearest-Neighbor yields $M(0, 2, 2) = 220$. |
| **TC-18** | Exact Boundary Sampling | Sample points $(0, 0, 0)$ and $(s_x-1, \dots)$. | Exact bounds pass; $s_x - 0.4$ is padded to `0`. |
| **TC-19** | Data Types Normalization | Volumes of `uint8`, `uint16`, `uint32`. | Min-max scaled locally to `uint8 [0, 255]`. |
| **TC-20** | Varying Plane Sizes | CSV with multiple planes of different widths. | Global video canvas rounds up to max even dimensions. |
| **TC-21** | Corrupted NRRD Handling | Corrupted `.nrrd` or unsupported `float64`. | Logs error, exit code 1, no output file. |
| **TC-22** | Atomic Output Generation | CSV with 10 valid rows followed by 1 invalid. | Exits code 2. Zero partial `.mp4` left on disk. |
| **TC-23** | MP4 Playback & Canvas | Open output `.mp4` with video decoding library. | File opens, dimensions are even integers, frames match. |
| **TC-24** | Pipeline Benchmark | 100 frames on $500^3$ volume. Run twice. | Reports Projection & End-to-End FPS. Deterministic. |
| **TC-25** | Streaming Memory Ceiling | $512^3$ volume (512 MB). Monitor via `tracemalloc`. | Peak RAM strictly $< 1024\text{ MB}$ (no frame accumulation). |
