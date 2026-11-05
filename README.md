# 3D Volume Plane Projection Engine

A Python command-line program for projecting plane coordinates from 3D volumetric NRRD data into a video. See the [SRS](DOCS/SRS.md) for the behavior implemented today; planned features are not necessarily implemented.

## 1. Problem Definition
Volumetric 3D data (such as medical MRI scans stored in `.nrrd` format) is traditionally viewed along standard orthogonal axes (X, Y, Z slices). However, analyzing structures at arbitrary angles requires slicing the 3D volume ($M$) along any given flat plane ($p$) in space. 

The current implementation takes a 3D matrix ($M$) and plane coordinates from a CSV file, samples the resulting triangular or trapezoidal raster using nearest-neighbor indices, and writes each frame to a video.

## 2. Project Scope

### In Scope:
* **Data Loading:** Reading and parsing 3D volumetric datasets in `.nrrd` format (specifically MRI data from 3D Slicer).
* **Plane Parsing and Projection:** Reading triangle/trapezoid coordinates and sampling a 2D raster from the 3D volume with a Numba-compiled nearest-neighbor kernel.
* **Video Output:** Normalizing and centering each projection, then streaming it to an MP4 file using OpenCV's `mp4v` codec.

### Out of Scope:
* **Interactive GUI:** This project does not include an interactive graphical user interface (like 3D Slicer); output is strictly 2D matrices/images and video files.
* **Geometric Validation:** The CSV formats represent triangles and trapezoids, but the code does not verify that their coordinates form valid planar shapes.
* **Medical Diagnosis / Image Processing:** No post-processing, segmentation, or clinical analysis is performed on the projected images.
* **Alternate Interpolation:** The current code supports nearest-neighbor sampling only; trilinear interpolation is not implemented.

## 3. Documentation & Structure
The implementation and design are described in:
* [Software Requirements Specification (SRS)](DOCS/SRS.md)
* [System & Engineering Design (SDD/EDD)](DOCS/SDD_EDD.md)
* [Testing Strategy & Cases (STP/STD)](DOCS/TSP_STD.md)

The project files are organized as follows:
* `SRC/` contains the command-line implementation.
  * `Ex0.py` is the entry point; `cli.py` coordinates the application.
  * `data_loader.py` reads inputs; `plane.py` parses and prepares plane geometry.
  * `projector.py` samples the volume; `video_renderer.py` writes video frames.
* `TEST/data/` contains sample volumes and plane-coordinate CSV files.
* `TEST/` also contains the automated regression suite. Run it from the
  repository root with `python -m unittest discover -s TEST -t . -v`.
* `TEST/output/` contains example projection videos.
* `DOCS/` contains the project documentation.

Run the program from the repository root with:

```text
python SRC/Ex0.py TEST/data/onion.nrrd TEST/data/onion.csv TEST/output/new_projection.mp4
```

## 4. Data Set
*[Our class sheared data set for the assignment](https://drive.google.com/drive/folders/1koJ83uaeMYdJt6AwvVlmMJk_wzczvmmG?usp=sharing)*
