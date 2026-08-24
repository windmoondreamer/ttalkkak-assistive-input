# 82 — I2 +W parallel-leg root-slide simplification audit

MODE = **AUDIT-ONLY / I2 / ROOT TANGENT-SLIDE ONLY / ALL LEG AXES = +W / PRODUCTION = 0**

FINAL VERDICT = **C — 90° PARALLEL LEGS STILL IMPOSSIBLE**

## 1. Scope correction from docs/81

docs/81 proved only that the four fixed side-midpoint roots cannot support one common ±W direct-shell family.
This audit does not generalize that result.  It reopens each root's tangent coordinate while preserving side
identity, switch/exterior authority and an exact +W leg direction.

The C verdict here is limited to: **current frozen I2 pose + tangent-only side-root slide + 2.60 mm straight
rectangular legs (1.60 mm primary, 1.20 mm allowed fallback) + direct frozen-shell blind slots**.

## 2. Frozen and allowed variables

- button center: `[-15.97116502911469, -26.20981698837403, 8.99880711855274]`;
- approved +W / press axis: `[-0.43398514194613513, -0.7569241977430389, -0.48859252495412786]`;
- root normal coordinates remain those of docs/81; only side tangent coordinates move;
- all leg angles to U-V = **90.000°**; maximum inter-leg angular difference = **0.000°**;
- root/candidate angular deviation = **0°**;
- production exterior, JaD/JfD split, ITS body/pose/actuator and production shell unchanged.

## 3. Side-root definition and search

The strict valid edge-support interval requires the complete 2.60 mm root width to remain projected onto its
assigned switch side.  This is the anti-corner-post gate.  A second wider diagnostic interval includes the
closure of every position with nonzero side overlap; its zero-overlap endpoints are evidence bounds only.

Strict grids use 0.050 mm spacing.  The nearest maximum-coverage point on each side is refined at 0.005 mm.
Every point uses a 3×3 exact B-rep footprint; no mesh/raster collision decides feasibility.

| side | thickness | strict tangent interval mm | grid | maximum coverage | max-coverage intervals | feasible interval | wider any-overlap max |
|---|---:|---:|---:|---:|---|---|---:|
| +U | 1.60 | -1.725…1.725 | 0.050 | 5/9 | [[1.525, 1.725]] | ∅ | 7/9 |
| +U | 1.20 | -1.725…1.725 | 0.050 | 5/9 | [[1.525, 1.725]] | ∅ | 7/9 |
| -U | 1.60 | -1.725…1.725 | 0.050 | 5/9 | [[-1.725, -0.425]] | ∅ | 8/9 |
| -U | 1.20 | -1.725…1.725 | 0.050 | 5/9 | [[-1.725, -0.425]] | ∅ | 8/9 |
| +V | 1.60 | -1.760…1.760 | 0.050 | 6/9 | [[-1.76, -1.46]] | ∅ | 8/9 |
| +V | 1.20 | -1.760…1.760 | 0.050 | 7/9 | [[-1.76, -1.46]] | ∅ | 9/9 |
| -V | 1.60 | -1.760…1.760 | 0.050 | 5/9 | [[0.54, 1.76]] | ∅ | 8/9 |
| -V | 1.20 | -1.760…1.760 | 0.050 | 5/9 | [[-1.76, -1.76], [0.54, 1.76]] | ∅ | 8/9 |

All feasible interval sets are **empty**.  The wider search reaches 9/9 only for +V at 1.20 mm in the refined
boundary interval **[-4.36, -4.285]**.  Across that interval,
actual side overlap is only **0.000…0.075 mm**
and minimum remaining shell is **1.017…1.033 mm**,
below the 1.20 mm rule.  It is therefore both a prohibited corner-post-like boundary position and a shell-thickness
failure, not a valid root-slide interval.

## 4. Nearest best root-slide diagnostics

These are evidence locations, not released roots.  Selection priority is maximum exact footprint coverage,
then minimum movement from the docs/81 midpoint.  Thickness 1.20 mm is selected only if required by ITS/body
clearance or if it improves maximum shell coverage.

| side | thickness | diagnostic root U,V,W | shift U,V,W from docs/81 | shift magnitude | side overlap | footprint pairs |
|---|---:|---|---|---:|---:|---:|
| +U | 1.20 | [3.74, 1.48, 0.0] | [0.0, 1.48, 0.0] | 1.480 | 2.600 | 5/9 |
| -U | 1.60 | [-4.04, -0.41, -0.6] | [0.0, -0.41, 0.0] | 0.410 | 2.600 | 5/9 |
| +V | 1.20 | [-1.425, 4.175, -0.6] | [-1.425, 0.0, 0.0] | 1.425 | 2.600 | 7/9 |
| -V | 1.60 | [0.535, -4.005, -0.6] | [0.535, 0.0, 0.0] | 0.535 | 2.600 | 5/9 |

## 5. Per-side numeric failure proof

Effective remaining shell is 0.000 mm when one or more footprint rays have no inner/outer shell pair; a planar
blind-slot floor does not exist at those missing samples.  Collision columns show distance / penetration mm³.

| side | missing rays | paired shell thickness mm | effective remaining shell | pusher | terminals | nearest neighbor | ITS body | corner keep-outs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| +U | 4 | 3.040…3.116 | 0.000 | 0.805 / 0.000000 | 0.157 / 0.000000 | 0.285 / 0.000000 (I3) | 0.080 / 0.000000 | 0.190 / 0.000000 |
| -U | 4 | 3.175…3.335 | 0.000 | 0.940 / 0.000000 | 0.190 / 0.000000 | 7.504 / 0.000000 (I3) | 0.180 / 0.000000 | 0.428 / 0.000000 |
| +V | 2 | 3.007…3.049 | 0.000 | 0.764 / 0.000000 | 0.982 / 0.000000 | 4.606 / 0.000000 (I3) | 0.550 / 0.000000 | 0.625 / 0.000000 |
| -V | 4 | 3.009…3.043 | 0.000 | 0.645 / 0.000000 | 1.178 / 0.000000 | 2.936 / 0.000000 (I3) | 0.180 / 0.000000 | 0.341 / 0.000000 |

The decisive failure on every side is incomplete shell footprint coverage, not leg angle.  Any pusher,
neighbor, body or corner collision is an additional rejection only; a clearance pass cannot repair a missing
shell floor.

## 6. Level-1 gate

Resolved Level-0 sides: **0/4**.  Because fewer than three sides
resolve, the permitted single simple local-pad Level-1 branch is **not opened**.  Pads, panels, receivers,
walls, struts, housing, carrier, doglegs and angled legs remain absent.

## 7. Candidate status

No successful candidate exists, so the requested successful-candidate leg lengths and minimum clearances are
not published as design values.  The STEP output contains four labeled **best-failure probes only**.  It must
not be used as manufacturing geometry.

## 8. Required renders

- [01_docs81_fixed_roots_top.png](../renders/i2_parallel_w_root_slide_simplification_audit/01_docs81_fixed_roots_top.png)
- [02_feasible_root_regions_four_sides.png](../renders/i2_parallel_w_root_slide_simplification_audit/02_feasible_root_regions_four_sides.png)
- [03_best_new_roots_top_failure_diagnostic.png](../renders/i2_parallel_w_root_slide_simplification_audit/03_best_new_roots_top_failure_diagnostic.png)
- [04_90deg_parallel_legs_only_failure_probes.png](../renders/i2_parallel_w_root_slide_simplification_audit/04_90deg_parallel_legs_only_failure_probes.png)
- [05_plus_u_minus_u_sections.png](../renders/i2_parallel_w_root_slide_simplification_audit/05_plus_u_minus_u_sections.png)
- [06_plus_v_minus_v_sections.png](../renders/i2_parallel_w_root_slide_simplification_audit/06_plus_v_minus_v_sections.png)
- [07_shell_blind_slot_footprint_ray_proof.png](../renders/i2_parallel_w_root_slide_simplification_audit/07_shell_blind_slot_footprint_ray_proof.png)
- [08_pusher_clearance_closeup.png](../renders/i2_parallel_w_root_slide_simplification_audit/08_pusher_clearance_closeup.png)
- [09_i3_clearance_closeup.png](../renders/i2_parallel_w_root_slide_simplification_audit/09_i3_clearance_closeup.png)
- [10_full_simplified_failure_combination.png](../renders/i2_parallel_w_root_slide_simplification_audit/10_full_simplified_failure_combination.png)
- [11_docs80_angled_vs_parallel_root_slide.png](../renders/i2_parallel_w_root_slide_simplification_audit/11_docs80_angled_vs_parallel_root_slide.png)

## 9. Outputs and preservation

- `build123d_workbench/out/i2_parallel_w_root_slide_simplification_audit/i2_parallel_w_root_slide_simplification_audit.json`
- `build123d_workbench/out/i2_parallel_w_root_slide_simplification_audit/I2_PARALLEL_W_ROOT_SLIDE_BEST_FAILURE_PROBES_AUDIT_ONLY.step`
- `docs/82_i2_parallel_w_root_slide_simplification_audit.md`

All 60 protected docs/79–81 and production files retain identical
SHA-256 hashes: **True**.  Production modification = 0;
production shell boolean = 0; eight-button propagation = 0; physical coupon = 0; angled-leg redesign = 0.

## 10. Stop

This audit stops at I2 +W tangent-root-slide feasibility.  It does not claim that every possible parallel-leg
architecture is impossible; changing root normal offset, side-support definition, or adding a support body is
outside this audit and would require explicit new authority.
