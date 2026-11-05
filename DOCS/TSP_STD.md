# Software Test Plan & Description (STP / STD)

## 1. Purpose and scope

This plan describes the automated regression suite in `TEST/`. The suite checks
the behavior currently implemented by `SRC/`: CSV plane parsing, dimension
calculation, nearest-neighbor sampling, MP4 writing, CLI error reporting, and
end-to-end processing. It does not claim that unsupported features such as
geometric validation or trilinear interpolation are tested.

Tests use Python's standard-library `unittest`; no test-only package is
required.

## 2. Running the tests

From the repository root:

```text
python -m unittest discover -s TEST -t . -v
```

The test suite writes temporary NRRD and MP4 files and uses the existing
`MRHead_1.nrrd` / `head.csv` pair for a real-data smoke test. Generated files
are removed when each test finishes. MP4 integration tests require an
OpenCV-enabled `mp4v` writer and a decoder on the machine running the suite.

## 3. Test strategy

* **Unit tests:** Exercise parsing, dimensions, projection, canvas sizing,
  normalization, writer selection, and CLI outcomes in isolation.
* **Analytical oracle:** A synthetic volume with
  `M[x, y, z] = x + 10*y + 100*z` makes coordinate order and sampled values
  independently checkable.
* **Integration tests:** Launch the actual `SRC/Ex0.py` process, verify exit
  behavior, generate MP4 output, and decode it with OpenCV.
* **No timing threshold:** FPS varies with hardware, Numba compilation, and
  video codecs. Performance is reported by the application, not asserted by
  this correctness suite.
* **No memory ceiling assertion:** The suite checks sequential frame output
  and writer cleanup, but does not measure process-wide peak memory.

## 4. Traceability

| Area | Test module | Coverage |
|---|---|---|
| CSV schema and finite coordinates | `TEST/test_plane.py` | Triangles, trapezoids, optional numeric ID, whitespace, malformed/non-numeric/non-finite rows, float32 range |
| Plane dimensions | `TEST/test_plane.py` | Rectangle, triangle, zero-size plane, prepared `Plane` record |
| Sampling algorithm | `TEST/test_projector.py` | Analytic axis-aligned projection, triangle apex, polygon mask, volume bounds, rounding, result type and shape |
| Volume and CSV loading | `TEST/test_cli.py` | NRRD round-trip, invalid volume shapes/data, CSV header and malformed-row handling |
| Video behavior | `TEST/test_video_renderer.py` | Even canvas, MP4-only writer attempts, normalization, centering, color frames, cleanup |
| CLI behavior | `TEST/test_cli.py` | Usage, read errors, invalid input, no planes, writer errors, success output, Unicode paths |
| Executable integration | `TEST/test_integration.py` | Real subprocess invocation, decodable MP4, expected canvas/frame count, head dataset smoke test |

## 5. Software Test Descriptions (STD)

The identifiers below correspond to individual `unittest` methods. Test method
names are listed as written in the source so each case can be located directly.

### 5.1 Plane parsing and dimensions

| ID | Test | Expected result |
|---|---|---|
| PL-01 | `test_triangle_coordinates_are_mapped_to_duplicate_apex` | Triangle apex occupies both top-base points; coordinates are float32. |
| PL-02 | `test_trapezoid_coordinates_keep_point_order` | Four input points retain their order. |
| PL-03 | `test_optional_numeric_identifier_is_ignored` | A 10-value triangle row discards its leading ID. |
| PL-04 | `test_optional_trapezoid_identifier_is_ignored` | A 13-value trapezoid row discards its leading ID. |
| PL-05 | `test_whitespace_and_empty_cells_are_ignored` | Empty cells and surrounding whitespace do not change coordinates. |
| PL-06 | `test_unsupported_coordinate_counts_raise` | Unsupported row lengths raise `ValueError`. |
| PL-07 | `test_nonnumeric_coordinate_raises` | A non-numeric coordinate raises a descriptive `ValueError`. |
| PL-08 | `test_nonfinite_coordinates_are_rejected` | `NaN` and positive/negative infinity are rejected. |
| PL-09 | `test_coordinates_outside_float32_range_are_rejected` | Values that cannot be represented as float32 are rejected. |
| PL-10 | `test_csv_row_classifier_accepts_only_parseable_plane_rows` | Plane rows are recognized; headers and malformed rows are not. |
| PL-11 | `test_rectangle_dimensions_use_base_width_and_perpendicular_height` | Dimensions and base lengths match the analytical rectangle. |
| PL-12 | `test_triangle_dimensions_include_apex_and_bottom_base` | Triangle raster dimensions account for its apex and lower base. |
| PL-13 | `test_zero_size_points_still_have_one_pixel_raster` | A point plane receives a 1-by-1 raster. |
| PL-14 | `test_plane_record_contains_points_and_precomputed_dimensions` | Plane coordinates and calculated dimensions are preserved together. |

### 5.2 Projection

| ID | Test | Expected result |
|---|---|---|
| PR-01 | `test_axis_aligned_rectangle_matches_analytic_volume` | Every projected voxel matches `x + 10*y + 100*z`. |
| PR-02 | `test_triangle_apex_is_sampled_at_center_of_first_row` | The apex is sampled once, in the center of the first row. |
| PR-03 | `test_pixels_outside_polygon_remain_zero` | Raster locations outside the triangular boundary remain zero. |
| PR-04 | `test_plane_outside_volume_returns_zero_pixels` | A plane outside the volume produces only zero-valued pixels. |
| PR-05 | `test_plane_at_volume_edge_samples_last_valid_index` | Coordinates on the final valid voxel indices are sampled. |
| PR-06 | `test_rounding_uses_python_ties_to_even` | A half-coordinate at zero rounds to the even index zero. |
| PR-07 | `test_rounding_halfway_between_odd_and_even_selects_even` | A 1.5 coordinate rounds to index two. |
| PR-08 | `test_result_is_float32_and_has_expected_shape` | Projection output type and dimensions match the plane. |
| PR-09 | `test_single_voxel_volume_can_be_sampled` | A one-voxel volume projects successfully. |

### 5.3 Video writer and rendering

| ID | Test | Expected result |
|---|---|---|
| VD-01 | `test_global_canvas_is_maximum_plane_size_rounded_up_to_even` | The largest width and height are rounded up independently. |
| VD-02 | `test_global_canvas_preserves_already_even_dimensions` | Even dimensions remain unchanged. |
| VD-03 | `test_empty_plane_list_has_clear_value_error` | Canvas sizing an empty list raises a clear `ValueError`. |
| VD-04 | `test_writer_uses_mp4v_color_then_grayscale_without_container_fallback` | Writer tries color then grayscale with MP4 codec only. |
| VD-05 | `test_writer_appends_mp4_extension_when_missing` | A missing extension is changed to `.mp4`. |
| VD-06 | `test_writer_failure_never_attempts_avi` | Failed MP4 writer attempts are released; no AVI attempt is made. |
| VD-07 | `test_render_normalizes_and_centers_frames_on_global_canvas` | Intensity scaling and black padding match expected pixels. |
| VD-08 | `test_constant_volume_normalizes_every_pixel_to_zero` | A constant-intensity volume yields an all-black frame. |
| VD-09 | `test_color_writer_receives_three_channel_frames` | Color writers receive three-channel frames. |
| VD-10 | `test_writer_is_released_when_projection_fails` | Open writer is released even when projection raises. |
| VD-11 | `test_rendering_empty_plane_list_is_rejected` | Rendering with no planes raises a clear `ValueError`. |

### 5.4 CLI and file loading

| ID | Test | Expected result |
|---|---|---|
| CL-01 | `test_wrong_argument_count_prints_usage_and_returns_one` | Incorrect argument count returns code 1 and prints usage. |
| CL-02 | `test_nrrd_load_error_returns_one_with_error_message` | NRRD read failure returns code 1 and reports the error. |
| CL-03 | `test_no_parseable_planes_returns_two_without_rendering` | No valid planes returns code 2 and does not start rendering. |
| CL-04 | `test_invalid_loaded_volume_returns_one` | Invalid NRRD volume returns code 1. |
| CL-05 | `test_csv_io_error_returns_one_without_traceback` | CSV file I/O failure returns code 1 with an error message. |
| CL-06 | `test_video_writer_error_returns_three` | Unavailable MP4 writer returns code 3 and reports the failure. |
| CL-07 | `test_success_reports_output_and_frame_count` | Success returns code 0 and prints output path and frame count. |
| CL-08 | `test_non_ascii_path_does_not_break_console_reporting` | A Unicode input path does not cause a console-encoding failure. |
| CL-09 | `test_real_csv_fixture_loads_only_well_formed_rows` | CSV headers and malformed rows are skipped; a valid row is loaded. |
| VL-01 | `test_load_volume_reads_valid_3d_nrrd` | A valid NRRD round-trips with unchanged voxel values. |
| VL-02 | `test_load_volume_rejects_non_3d_arrays` | A non-3D NRRD array is rejected. |
| VL-03 | `test_load_volume_rejects_empty_axes` | A volume with an empty axis is rejected. |
| VL-04 | `test_load_volume_rejects_nonfinite_values` | A volume containing `NaN` or infinity is rejected. |
| VL-05 | `test_load_volume_rejects_non_numeric_values` | Non-numeric voxel arrays are rejected. |

### 5.5 End-to-end process

| ID | Test | Expected result |
|---|---|---|
| IN-01 | `test_cli_writes_decodable_mp4_and_no_avi` | CLI emits one decodable MP4 frame with even canvas dimensions and no AVI. |
| IN-02 | `test_cli_missing_arguments_returns_usage_exit_code` | Executable returns code 1 and prints its usage. |
| IN-03 | `test_real_head_fixture_runs_to_mp4` | The checked-in head volume and CSV produce a decodable MP4 in a temporary directory. |

## 6. Exit criteria and limitations

The current correctness gate is that all discovered `unittest` cases pass on a
machine with the runtime dependencies and MP4 codec/decoder available. Codec
availability is an environmental prerequisite, not silently replaced by AVI.
This suite does not prove that every possible input is valid, does not enforce
an FPS or memory limit, and does not test geometric properties that the
implementation does not validate.
