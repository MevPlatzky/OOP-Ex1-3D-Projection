# Software Requirements Specification (SRS)

## 1. Functional Requirements (REQ)
* **REQ-01 (NRRD Input):** Load a 3D matrix $M$ ($s_x \times s_y \times s_z$, where $1 \le s_x, s_y, s_z < 2^{10}$) of unsigned integers (`uint8`, `uint16`, or `uint32`) from an `.nrrd` file.
* **REQ-02 (CSV Input):** Parse a `.csv` file where each row defines a slicing plane $p$ using 3D coordinates of 3 points $(a, b, c)$ or 4 points $(a_1, a_2, b, c)$.
* **REQ-03 (Geometric Validation):** Validate each plane within tolerance $\epsilon = 0.001$:
  * **Triangle (3 points):** $|dist(a,b) - dist(a,c)| < \epsilon$ and $dist(b,c) > 0$.
  * **Trapezoid (4 points):** Coplanar points, $\vec{a_1a_2} \parallel \vec{bc}$, $|dist(a_1,b) - dist(a_2,c)| < \epsilon$, and $dist(a_1,a_2) \le dist(b,c)$.
* **REQ-04 (2D Projection):** Sample $M$ along plane $p$ into a 2D matrix $E$, centering each scanline horizontally via $x = \frac{D_{bc}}{2} - \frac{d_{12}}{2} + x_1$. Assign $0$ to coordinates outside $M$.
* **REQ-05 (CLI & Video Output):** Run via `python Ex0.py <file.nrrd> <file.csv> <file.mp4>` and encode all projected 2D frames sequentially into `<file.mp4>`.

## 2. Non-Functional Requirements (NFR)
* **NFR-01 (Performance):** On a $500^3$ byte matrix, projection speed shall be strictly $> 30$ FPS (Must), $\ge 100$ FPS (Expected NFR), with a stretch goal of $300+$ FPS (Good to have).
* **NFR-02 (Robustness):** Handle missing files, invalid geometry, and out-of-bounds coordinates safely without unhandled crashes.

## 3. Main Use Case (UC-01)
* **Name:** `UC-01: Generate Projection Video from CLI`
* **Actor:** User / Grading Script
* **Preconditions:** `<file.nrrd>` and `<file.csv>` exist and are readable.
* **Main Flow:**
  1. Actor runs `python Ex0.py file.nrrd file.csv file.mp4`.
  2. System loads 3D matrix $M$ and parses plane rows from the CSV.
  3. System validates each plane, projects the 3D slice onto a 2D frame $E$, and appends it to the video stream.
  4. System saves `file.mp4` and prints FPS performance.
* **Alternative / Error Flows:**
  * **1a. Bad CLI args / missing files:** Print usage/error message and exit cleanly.
  * **3a. Invalid geometry ($\ge \epsilon$):** Raise/log `ValueError` for the invalid plane.
  * **3b. Out-of-bounds coordinates:** Set pixel value $v = 0$ and continue.
* **Postconditions:** A playable `.mp4` video of the projected slices is saved to disk.
