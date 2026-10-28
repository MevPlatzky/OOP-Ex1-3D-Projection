# System and Engineering Design Documents

This document outlines how the software is structured globally, and details the specific algorithms used in its core components.

## 1. System Design Document (SDD)
**Purpose:** To architect the entire system and explain how its sub-components interact.

The system is composed of a linear pipeline of four main logical components:
1. **I/O & Parser:** Parses Command Line Interface (CLI) arguments, loads the 3D `.nrrd` volume into memory, and reads the `.csv` file coordinates.
2. **Geometry Validator:** Validates points to ensure they mathematically form an isosceles triangle or isosceles trapezoid within $\epsilon = 0.001$. Calculates dimensions ($D_{ab}, D_{bc}$) and unit vectors.
3. **Projection Engine (Core):** Implements the sampling algorithm to map 3D voxels onto a 2D matrix ($E$).
4. **Video Compiler:** Aggregates all generated 2D frames and encodes them into a sequential `.mp4` video output.

## 2. Engineering Design Document (EDD)
**Purpose:** To define the internal engineering details and mathematical logic of a specific component (The Projection Engine).

**Goal:** Project a 3D matrix $M$ onto a 2D plane $E$ bounded by an isosceles triangle $(a, b, c)$.

**Definitions & Setup:**
* $D_{ab} = dist(a, b)$ (Height/Length of the plane)
* $D_{bc} = dist(b, c)$ (Base width of the plane)
* Output Image $E$ is instantiated with size $D_{bc} \times D_{ab}$.
* Normalized directional vectors along the edges: $\vec{v}_{ab}$ and $\vec{v}_{ac}$.

**The "Sliding Ruler" Execution:**
1. Initialize tracking points at the tip of the triangle: $a_1 = a$, $a_2 = a$.
2. Loop over the height of the image: `for y from 0 to D_ab`:
   * **Advance the edges:** 
     $$a_1 = a_1 + \vec{v}_{ab} \quad \text{and} \quad a_2 = a_2 + \vec{v}_{ac}$$
   * **Calculate current width:** 
     $$d_{12} = dist(a_1, a_2)$$
   * **Get horizontal step vector:** 
     $$\vec{dp} = \frac{a_2 - a_1}{d_{12}}$$
   * **Scan the horizontal line:** `for x1 from 0 to d_12`:
     * Set current 3D sample point: $p = a_1 + (x_1 \cdot \vec{dp})$.
     * Read voxel value: $v = M[p]$ (if $p$ is strictly inside $M$; else $v = 0$).
     * Calculate horizontally centered X-coordinate on the 2D canvas: 
       $$x = \frac{D_{bc}}{2} - \frac{d_{12}}{2} + x_1$$
     * Map to image: $E[x, y] = v$.
3. Return the fully populated 2D matrix $E$.

*(Note: For an isosceles trapezoid, the logic remains identical, starting the sliding ruler with initial width $dist(a_1, a_2)$ instead of 0)*.
