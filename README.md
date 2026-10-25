# 3D Volume Plane Projection Engine

A high-performance Python engine for projecting arbitrary 2D planes (defined as isosceles triangles or trapezoids) from 3D volumetric NRRD data.

## 1. Problem Definition
Volumetric 3D data (such as medical MRI scans stored in `.nrrd` format) is traditionally viewed along standard orthogonal axes (X, Y, Z slices). However, analyzing structures at arbitrary angles requires slicing the 3D volume ($M$) along any given flat plane ($p$) in space. 

The goal of this project is to design and implement a robust, efficient algorithm that takes a 3D matrix ($M$) and a geometric plane ($p$)—defined by either 3 points forming an isosceles triangle or 4 points forming an isosceles trapezoid—and projects the intersecting 3D voxels (pixels with volume) onto a 2D output image matrix ($E$) in real-time (expected >=100 FPS, and targeting 300+ FPS on a 500^3 volume).

## 2. Project Scope

### In Scope:
* **Data Loading:** Reading and parsing 3D volumetric datasets in `.nrrd` format (specifically MRI data from 3D Slicer).
* **Geometric Validation:** Verifying that the input coordinates validly represent an isosceles triangle (3 points) or an isosceles trapezoid (4 coplanar points) within a defined numerical tolerance ($\epsilon = 0.001$).
* **Core Projection Algorithm:** Sampling the 3D matrix $M$ along the plane $p$ and mapping the values onto a 2D image matrix $E$ (assigning $0$ to out-of-bounds coordinates).
* **High-Performance Execution:** Utilizing vectorized operations to achieve an expected rendering rate of >=100 FPS and a target goal of 300+ FPS on a 500^3 byte matrix (with 30 FPS as a strict lower bound).
* **Testing & Demo:** Automated unit tests and a demonstration script (`main.py`) that generates a smooth video sequence of slices across the 3D volume.

### Out of Scope:
* **Interactive GUI:** This project does not include an interactive graphical user interface (like 3D Slicer); output is strictly 2D matrices/images and video files.
* **Non-Planar or Arbitrary Polygons:** Only flat planes bounded by isosceles triangles or isosceles trapezoids are supported.
* **Medical Diagnosis / Image Processing:** No post-processing, segmentation, or clinical analysis is performed on the projected images.

## 3. Documentation & Structure
* **SRS (Software Requirements Specification):** *(To be added)*
* **Algorithm & Design (SDD/EDD):** *(To be added)*
* **Testing Strategy:** *(To be added)*
