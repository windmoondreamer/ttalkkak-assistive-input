# 80 — I2 direct-shell four-edge-leg simplification audit

MODE
= **AUDIT-ONLY / I2 REPRESENTATIVE / PRODUCTION PROPAGATION = 0**

FINAL VERDICT
= **A — DIRECT-SHELL SIMPLE DESIGN WORKS**

CURRENT docs/79 PRESERVED
= **True**

SIMPLIFIED LOAD PATH
= **ITS BODY → ONE FOUR-EDGE HARNESS → FOUR STRAIGHT LEGS → FOUR DIRECT SHELL BLIND-SLOT FLOORS/WALLS → FROZEN SHELL**

PRINTED/SUPPORT SOLID COUNT
= **3: ONE FUSED HARNESS + EXISTING PUSHER + EXISTING GUIDE/HARD-STOP INTERFACE**

## 1. What docs/79 actually built

The source generator and the exported STEP are not identical.  The source defines 4 conformal panels,
8 receiver walls and 4 outboard struts.  However, the `housing` compound stored in the full-stack STEP
collapses to one solid whose bounds exactly match the **-V outboard strut**.  This is an audit finding;
docs/79 and its files were not repaired or overwritten.

| source component | source solids | decision | reason |
|---|---:|---|---|
| FOUR EDGE LEGS | 4 | SIMPLIFY | replace upper/lower/transition stack with four straight full-length legs |
| MINIMAL LANDINGS | 4 | REMOVE | 0.60 mm structural reaction ledge is below the 1.20 mm rule |
| FOUR RECEIVERS | 4 | REMOVE | replace references with four voids cut directly in the shell crop |
| RECEIVER WALLS | 8 | REMOVE | eight separate walls are not part of the direct-shell load path |
| OUTBOARD STRUTS | 4 | REMOVE | their span is absorbed into the straight structural legs |
| CONFORMAL PANELS | 4 | REMOVE | Level 0 uses frozen shell material directly |
| INNER HOUSING | 1 | REMOVE | separate support body is prohibited by the simplified intent |
| ROOT TRANSITIONS | 4 | REMOVE | four separate root transitions disappear into four straight legs |
| N2 REAR TRANSITION | 0 | REMOVE | not present in I2; no rear-route family is carried forward by default |
| PUSHER GUIDE | 1 | KEEP | existing simple guide; checked only for collision |
| HARD STOP | 1 | KEEP | existing independent shoulder/cavity-floor stop |
| PUSHER | 1 | KEEP | existing separate captive pusher |
| RETENTION CLIP | 1 | KEEP | retention only; excluded from press load |
| SECONDARY GLUE BEADS | 8 | REMOVE | not required to define the Level-0 structural path |

### Actual children in the existing docs/79 I2 full-stack STEP

| exported child label | type | solids | volume mm³ |
|---|---|---:|---:|
| I2_FOUR_RECEIVER_LOCAL_CONFORMAL_INNER_HOUSING | Solid | 1 | 20.415 |
| I2_FOUR_EDGE_LEG_STRUCTURAL_HARNESS | Solid | 1 | 158.485 |
| ITS1105_MEASURED_BODY | Solid | 1 | 131.813 |
| ITS1105_MEASURED_ACTUATOR | Solid | 1 | 21.506 |
| AUDIT_OUTER_SHELL_GUIDE_AND_STOP_INTERFACE | Solid | 1 | 28.345 |
| SEPARATE_CAPTIVE_PUSHER_PIN | Solid | 1 | 68.051 |
| METAL_E_CLIP_REPRESENTATION_RETENTION_ONLY | Solid | 1 | 13.667 |
| I2_RECEIVER_EXIT_SECONDARY_ADHESIVE | Compound | 8 | 3.906 |

Existing STEP solid total: **15**.  Existing exported
`INNER_HOUSING` matches only the -V strut: **True**.

## 2. Frozen orientation authority

| item | value |
|---|---|
| frozen button center | [-15.97116502911469, -26.20981698837403, 8.99880711855274] |
| approved press axis | [-0.43398514194613513, -0.7569241977430389, -0.48859252495412786] |
| approved local exterior normal | [-0.47237675018851943, -0.7367637373812471, -0.48377618912194265] |
| angle axis ↔ exterior normal | **2.500°** |
| ITS actuator axis | identical to approved press axis |
| exterior / JaD-JfD split | unchanged / unchanged |

The exact STEP has an aperture at the button center, so a face normal cannot be sampled at the void.
The frozen approved pre-cut surface normal stored with the button datum is therefore the tangent-plane authority.

## 3. Level-0 direct-shell feasibility

Roots remain at the four +U/-U/+V/-V switch side mid-regions.  Every leg is one straight rectangular prism.
The I2-I3 gap requires the allowed 1.20 mm minimum at +U; the other three retain 1.60 mm.  Tangent width is
2.60 mm throughout.  The shell endpoint alone moves to a region where the complete clearance slot footprint
has a valid exact inner/outer BRep pair.  Every footprint was checked at 3×3 points.

| leg | length mm | thickness | shell center thickness | footprint min thickness | footprint min remaining | depth range | shell target U,V |
|---|---:|---:|---:|---:|---:|---:|---:|
| +U | 7.264 | 1.20 | 3.030 | 2.720 | 1.301 | 1.200…1.741 | 4.80, 1.60 |
| -U | 6.566 | 1.60 | 3.068 | 3.016 | 1.243 | 1.200…1.907 | -6.00, 0.00 |
| +V | 7.900 | 1.60 | 3.025 | 2.528 | 1.328 | 1.200…1.628 | 0.00, 5.50 |
| -V | 7.804 | 1.60 | 3.034 | 2.531 | 1.331 | 1.200…1.608 | 0.00, -5.50 |

Blind-slot depth is **1.20 mm** and clearance is
**0.20 mm/side**.  Minimum remaining exterior material over
all four footprints is **1.243 mm**.  Therefore no
local pad, conformal panel, receiver cage or strut network is geometrically required for this I2 audit candidate.

## 4. Clearances

| terminal | minimum distance mm | penetration mm³ | clear |
|---|---:|---:|---|
| TNN | 0.600 | 0.000000 | True |
| TNP | 0.600 | 0.000000 | True |
| TPN | 0.889 | 0.000000 | True |
| TPP | 0.594 | 0.000000 | True |

| requested value | result |
|---|---:|
| minimum terminal clearance | 0.594 mm |
| minimum pusher-to-harness clearance | 1.459 mm |
| minimum neighboring-geometry clearance | 0.215 mm to I3 |

Neighbor scope is `other seven frozen measured ITS body+actuator envelopes`.  No production carrier or neighboring button was modified.

## 5. What was removed

- four 0.60 × 0.60 structural landings;
- eight separate receiver walls;
- four outboard struts;
- four ruled conformal panels;
- the separate inner-housing/support concept;
- glue beads as a structural definition;
- the N2 rear-route architecture as a default assumption.

The open body-bottom cross, four side-midpoint origins, existing pusher, retention-only clip and independent
hard stop remain.  N2 was not rebuilt in this I2-only stop stage; any later N2 work must begin with the same
four direct-ray test before an offset is allowed.

## 6. FDM and assembly

- P1S / 0.4 mm nozzle basis;
- structural leg thickness 1.20 mm at +U / 1.60 mm at the other three; tangent width 2.60 mm;
- blind depth 1.20 mm; no sub-mm structural shoulder or landing;
- unequal leg lengths are intentional consequences of the frozen curved shell;
- the four legs and open cross are fused into one printable harness solid.

## 7. Required renders

- [01_current_docs79_i2_full_stack_exploded_named.png](../renders/direct_shell_four_edge_i2_simplification_audit/01_current_docs79_i2_full_stack_exploded_named.png)
- [02_current_receiver_panel_strut_closeup.png](../renders/direct_shell_four_edge_i2_simplification_audit/02_current_receiver_panel_strut_closeup.png)
- [03_simplified_direct_shell_candidate_top.png](../renders/direct_shell_four_edge_i2_simplification_audit/03_simplified_direct_shell_candidate_top.png)
- [04_simplified_candidate_isometric.png](../renders/direct_shell_four_edge_i2_simplification_audit/04_simplified_candidate_isometric.png)
- [05_section_plus_u_minus_u_legs.png](../renders/direct_shell_four_edge_i2_simplification_audit/05_section_plus_u_minus_u_legs.png)
- [06_section_plus_v_minus_v_legs.png](../renders/direct_shell_four_edge_i2_simplification_audit/06_section_plus_v_minus_v_legs.png)
- [07_four_shell_blind_slots_only.png](../renders/direct_shell_four_edge_i2_simplification_audit/07_four_shell_blind_slots_only.png)
- [08_its_harness_four_legs_only.png](../renders/direct_shell_four_edge_i2_simplification_audit/08_its_harness_four_legs_only.png)
- [09_full_simplified_assembly.png](../renders/direct_shell_four_edge_i2_simplification_audit/09_full_simplified_assembly.png)
- [10_current_vs_simplified_comparison.png](../renders/direct_shell_four_edge_i2_simplification_audit/10_current_vs_simplified_comparison.png)

## 8. Outputs and preservation

- `build123d_workbench/out/direct_shell_four_edge_i2_simplification_audit/I2_DIRECT_SHELL_FOUR_EDGE_HARNESS_AUDIT_ONLY.step`
- `build123d_workbench/out/direct_shell_four_edge_i2_simplification_audit/I2_DIRECT_SHELL_LOCAL_CROP_WITH_BLIND_SLOTS_AUDIT_ONLY.step`
- `build123d_workbench/out/direct_shell_four_edge_i2_simplification_audit/I2_DIRECT_SHELL_SIMPLIFIED_FULL_ASSEMBLY_AUDIT_ONLY.step`
- `build123d_workbench/out/direct_shell_four_edge_i2_simplification_audit/direct_shell_four_edge_i2_simplification_audit.json`

All 35 protected prior/production files retained identical SHA-256 hashes:
**True**.  Production shell boolean = **0**; only a separate local
audit crop copy was cut.  Physical coupon = **not created**.  Eight-button propagation = **0**.

## 9. Stop

This audit stops at one I2 simplified candidate.  No production geometry, frozen exterior, button center, press axis,
JaD/JfD split, docs/79 file or previous audit output was changed.
