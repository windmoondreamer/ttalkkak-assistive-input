# 96 — OneGrip Play print-ready frozen exterior recovery + export

## Result

```text
PRINT-READY EXTERIOR RECOVERY RESULT:

Approved LOWER15 Thumb source found = YES

JOY + T1~T8 openings complete = YES
Finger 8 openings complete = YES

JaD print-ready = YES
JfD print-ready = YES

EXTERIOR MODIFICATION = 0 required
INTERNAL UNRESOLVED STRUCTURES INCLUDED = NO
```

Exact source used for Thumb exterior = `thumb_exact_onshape_source/{JaD,JfD}_THUMB_LOWER15_APPROVED.step`, immutable Onshape version `THUMB_LOWER15_HOUSING_V1` (`VID 50dfe4e752e447375b95493a`).

Exact source used for Finger exterior = immutable `local_cad/reference/{JAD,JFD}_CLEAN_PRE_FINGER.step` surface authority plus the centers/axes and existing `opening_cutter` BReps frozen by `finger_controls_v2_source_manifest.json`. The final shell retains the exact LOWER15 whole-shell BRep and subtracts only those approved cutters.

Any missing/recreated Thumb openings? = **NO**. The exact LOWER15 Thumb BRep remains intact; manual or approximate re-drilling count is zero.

Any exterior reconstruction performed? = **NO surface reconstruction.** Only the pre-existing frozen Finger opening cutters were subtracted from the exact approved LOWER15 shell; separated cutter slugs and zero-area STL triangles were discarded.

## Authority recovery

| Candidate | Opening evidence | Authority decision |
|---|---|---|
| Exact approved Onshape STEP pair | JOY + T1–T8 direct axis scan 9/9 PASS | **SELECTED** |
| Historical LOWER15 STL pair | Approved tessellation, mesh-only | visual cross-check only |
| `JAD/JFD_EXTERIOR_LOWERED_THUMB_V1.step` | reconstructed local opening envelopes, not exact LOWER15 BRep | rejected as final authority |

Source hashes were checked before and after generation and remained unchanged: **TRUE**.

## Thumb opening verification

| Opening | JaD/JfD owner | Exists in final BRep? | Through/open? | Source authority |
|---|---|---|---|---|
| JOY | JaD/JfD | YES | YES | exact Onshape THUMB_LOWER15_HOUSING_V1 |
| T1 | JaD | YES | YES | exact Onshape THUMB_LOWER15_HOUSING_V1 |
| T2 | JaD/JfD | YES | YES | exact Onshape THUMB_LOWER15_HOUSING_V1 |
| T3 | JfD | YES | YES | exact Onshape THUMB_LOWER15_HOUSING_V1 |
| T4 | JaD | YES | YES | exact Onshape THUMB_LOWER15_HOUSING_V1 |
| T5 | JaD/JfD | YES | YES | exact Onshape THUMB_LOWER15_HOUSING_V1 |
| T6 | JfD | YES | YES | exact Onshape THUMB_LOWER15_HOUSING_V1 |
| T7 | JaD | YES | YES | exact Onshape THUMB_LOWER15_HOUSING_V1 |
| T8 | JfD | YES | YES | exact Onshape THUMB_LOWER15_HOUSING_V1 |

## Finger opening verification

| Opening | Owner | Exists | Center unchanged | Axis unchanged |
|---|---|---|---|---|
| I2 | JfD | YES | YES | YES |
| I3 | JfD | YES | YES | YES |
| I4 | JaD | YES | YES | YES |
| M3 | JfD | YES | YES | YES |
| M4 | JaD | YES | YES | YES |
| N1 | JfD | YES | YES | YES |
| N2 | JfD | YES | YES | YES |
| N3 | JaD | YES | YES | YES |

## Exact exterior comparison

| Gate | JaD | JfD |
|---|---:|---:|
| final vs exact LOWER15 inside Thumb patch symmetric difference | 0.000000000 mm³ | 0.000000000 mm³ |
| unexpected change outside approved Finger cutters | 0.000000000 mm³ | 0.000000000 mm³ |

Thumb exterior displacement = **0**; Finger exterior displacement = **0**; frozen opening centers/axes = unchanged; vertical JaD/JfD split = preserved; unexpected exterior Boolean changes = **0**.

## Print sanity

| Check | JaD | JfD |
|---|---:|---:|
| final BRep valid / one solid | True / 1 | True / 1 |
| STEP reimport valid / solids | True / 1 | True / 1 |
| STL triangles | 20774 | 22552 |
| STL boundary edges | 0 | 0 |
| STL non-manifold edges | 0 | 0 |
| STL connected components | 1 | 1 |

STL unit is millimeter. Export tessellation is 0.04 mm linear / 0.08 rad angular tolerance, suitable for the exterior curves without unnecessarily oversized meshes.

## Outputs

- `build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_JaD.step`
- `build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_JfD.step`
- `build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_JaD.stl`
- `build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_JfD.stl`
- `build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_COMBINED_REFERENCE.step`
- `build123d_workbench/out/print_ready_frozen_exterior/print_ready_frozen_exterior_validation.json`
- `renders/print_ready_frozen_exterior/01_jad_exterior_overall.png`
- `renders/print_ready_frozen_exterior/02_jfd_exterior_overall.png`
- `renders/print_ready_frozen_exterior/03_assembled_exterior_overall.png`
- `renders/print_ready_frozen_exterior/04_thumb_joy_t1_t8_openings.png`
- `renders/print_ready_frozen_exterior/05_thumb_opposite_angle_through_openings.png`
- `renders/print_ready_frozen_exterior/06_finger_8_opening_overview.png`
- `renders/print_ready_frozen_exterior/07_jad_jfd_vertical_seam.png`
- `renders/print_ready_frozen_exterior/08_interior_openings_are_holes.png`

Production files overwritten = **0**. Internal structures included = **0**.

Generated: 2026-08-25T06:24:46.926669+00:00
