# Software Test Plan & Description (STP / STD)

## 1. Test Strategy & Plan (STP)

**1.1 Scope and Items Under Test:**
This document outlines the testing strategy for the 3D Projection Engine, covering geometric validation, matrix manipulation bounding limits, system file I/O, and performance requirements.

**1.2 Test Levels:**
* **Unit Testing:** Tests individual mathematical functions in the `Geometry Validator` (epsilon precision bounds) and the 3D-to-2D matrix coordinate mapping.
* **Integration Testing:** Tests the interaction between the CSV parser, the NRRD volume loader, and the Core Projection Engine.
* **System Testing:** End-to-end testing from CLI command execution to `.mp4` video output verification.

**1.3 Environment & Tools:**
* **Python Framework:** `pytest` for automated unit and integration tests.
* **Test Data:** Pre-generated `.nrrd` volumes (e.g., $100^3$, $500^3$) and `.csv` files containing deliberately crafted valid and invalid geometric configurations.

**1.4 Entry and Exit Criteria:**
* **Entry:** Code compiles without syntax errors; all modules are implemented.
* **Exit:** 100% of defined Test Cases pass. Code coverage is $\ge 90\%$. No unhandled exceptions in edge cases.

---

## 2. Test Case Descriptions (STD)

The following matrix ensures full traceability to the SRS requirements and Use Cases.

| TC ID | Title | Verifies | Preconditions | Steps | Input Data | Expected Result |
|---|---|---|---|---|---|---|
| **TC-01** | Valid Isosceles Triangle (Happy Path) | REQ-03, REQ-04, UC-01 | NRRD and CSV exist. | Run system pipeline. | 3 points where $\|dist(a,b) - dist(a,c)\| = 0$. | System generates valid 2D matrix. No errors. |
| **TC-02** | Valid Isosceles Trapezoid (Happy Path) | REQ-03, REQ-04 | NRRD and CSV exist. | Run system pipeline. | 4 coplanar points forming a valid trapezoid. | System generates valid 2D matrix. No errors. |
| **TC-03** | Epsilon Boundary Validation (Edge Case) | REQ-03 | CSV prepared with micro-deviations. | Run geometry validator. | 3 points where $\|dist(a,b) - dist(a,c)\| = 0.00099$. | System accepts the geometry as valid ($\Delta < 0.001$). |
| **TC-04** | Invalid Geometry Rejection (Sad Path) | REQ-03, UC-01 (3a) | CSV prepared with asymmetric points. | Run geometry validator. | 3 points where $\|dist(a,b) - dist(a,c)\| = 0.0011$. | System explicitly rejects the plane and logs a `ValueError`. |
| **TC-05** | Out-of-Bounds Padding (Edge Case) | REQ-04, UC-01 (3b) | NRRD loaded. CSV points explicitly exceed volume dimensions. | Inspect the generated 2D image matrix $E$. | Plane dimensions $D_{ab}, D_{bc}$ extend $20\%$ outside matrix $M$. | Pixels strictly outside $M$ are assigned `v = 0` (black). No `IndexError` crashes. |
| **TC-06** | Negative Coordinates Handling (Edge Case) | REQ-04 | CSV prepared with points outside origin. | Run projection algorithm. | Plane origin starts at $(-10, -5, -5)$. | Negative coordinates are safely treated as out-of-bounds (`v = 0`). |
| **TC-07** | Missing Files / CLI Error (Sad Path) | REQ-05, UC-01 (1a) | Execution environment missing `.nrrd` file. | Run CLI command. | Command: `python Ex0.py missing.nrrd data.csv out.mp4` | System catches missing file, prints graceful error/usage guide, and exits cleanly. |
| **TC-08** | Frame Rate Performance (NFR) | NFR-01 | Large test volume prepared. | Run projection for 100 sequential frames, measure time. | Matrix size: $500^3$ bytes. | Average processing speed is strictly $> 30$ FPS (Expected $\ge 100$ FPS). |
