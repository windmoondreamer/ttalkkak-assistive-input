# 90 — 8-button four-edge harness batch propagation screening

MODE = **BATCH SCREENING / AUDIT ONLY / PRODUCTION 0 / FROZEN EXTERIOR**

| Button | 90° +U | 90° -U | 90° +V | 90° -V | Tilted legs | Min clearance | Min shell | Rear assembly | Class |
|---|---|---|---|---|---|---:|---:|---|---|
| N1 | FAIL | FAIL | FAIL | FAIL | +U 9.000°, -U 10.000°, +V 10.000°, -V 10.000° | 0.168217 | 1.217777 | PASS | LOCAL VARIANT |
| N2 | FAIL | FAIL | FAIL | FAIL | +U UNRESOLVED≤30°, -U 10.000°, +V UNRESOLVED≤30°, -V UNRESOLVED≤30° | N/A | 1.234163 | FAIL | FAIL |
| I2 | reference | reference | reference | reference | +U 21.043°, -U 18.095°, +V 17.493°, -V 15.265° | 0.145815 | 1.200134 | PASS | REFERENCE |
| I3 | FAIL | FAIL | FAIL | FAIL | +U UNRESOLVED≤30°, -U UNRESOLVED≤30°, +V 9.000°, -V 10.000° | N/A | 1.211552 | FAIL | FAIL |
| I4 | FAIL | FAIL | FAIL | FAIL | +U UNRESOLVED≤30°, -U 8.000°, +V 10.000°, -V 9.000° | N/A | 1.279506 | FAIL | FAIL |
| M3 | FAIL | FAIL | FAIL | FAIL | +U 10.000°, -U 10.000°, +V 10.000°, -V 10.000° | 0.168836 | 1.204689 | PASS | LOCAL VARIANT |
| M4 | FAIL | FAIL | FAIL | FAIL | +U 13.000°, -U 11.000°, +V 13.000°, -V 13.000° | 0.161131 | 1.213588 | PASS | LOCAL VARIANT |
| N3 | FAIL | FAIL | FAIL | FAIL | +U 15.000°, -U 19.000°, +V UNRESOLVED≤30°, -V 14.000° | N/A | 1.342665 | FAIL | FAIL |

I2 is shown as REFERENCE but is counted in STANDARD for the required 8-button partition.

## Required numeric summary

- Buttons evaluated = **8**
- STANDARD = **1**
- LOCAL VARIANT = **3**
- FAIL = **4**
- Total legs = **32**
- 90° legs retained = **0**
- Tilted legs required = **25**
- Unresolved legs with no candidate through 30° bounded screen = **7**
- Maximum required tilt = **21.043°**
- Button with worst clearance = **I2**, 0.145815 mm
- Button with minimum remaining shell = **I2**, 1.200134 mm
- ALL-8 simultaneous static fit = **FAIL**
- bounded candidate evaluations = **1473**; global optimizer = **NO**

## Tilted-leg proof

| Button | leg | tilt from W | reason 90° failed |
|---|---|---:|---|
| N1 | +U | 9.000° | INCOMPLETE_SLOT_FOOTPRINT |
| N1 | -U | 10.000° | INCOMPLETE_SLOT_FOOTPRINT |
| N1 | +V | 10.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| N1 | -V | 10.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| N2 | +U | UNRESOLVED≤30° | INCOMPLETE_SLOT_FOOTPRINT; no valid manufacturing candidate through 30 deg bounded screen |
| N2 | -U | 10.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| N2 | +V | UNRESOLVED≤30° | INCOMPLETE_SLOT_FOOTPRINT; no valid manufacturing candidate through 30 deg bounded screen |
| N2 | -V | UNRESOLVED≤30° | INCOMPLETE_SLOT_FOOTPRINT; no valid manufacturing candidate through 30 deg bounded screen |
| I2 | +U | 21.043° | docs/81 exact 90-degree shell-footprint/material rejection |
| I2 | -U | 18.095° | docs/81 exact 90-degree shell-footprint/material rejection |
| I2 | +V | 17.493° | docs/81 exact 90-degree shell-footprint/material rejection |
| I2 | -V | 15.265° | docs/81 exact 90-degree shell-footprint/material rejection |
| I3 | +U | UNRESOLVED≤30° | INCOMPLETE_SLOT_FOOTPRINT; no valid manufacturing candidate through 30 deg bounded screen |
| I3 | -U | UNRESOLVED≤30° | INCOMPLETE_SLOT_FOOTPRINT; no valid manufacturing candidate through 30 deg bounded screen |
| I3 | +V | 9.000° | INCOMPLETE_SLOT_FOOTPRINT |
| I3 | -V | 10.000° | INCOMPLETE_SLOT_FOOTPRINT |
| I4 | +U | UNRESOLVED≤30° | INCOMPLETE_SLOT_FOOTPRINT; no valid manufacturing candidate through 30 deg bounded screen |
| I4 | -U | 8.000° | INCOMPLETE_SLOT_FOOTPRINT |
| I4 | +V | 10.000° | INCOMPLETE_SLOT_FOOTPRINT |
| I4 | -V | 9.000° | INCOMPLETE_SLOT_FOOTPRINT |
| M3 | +U | 10.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| M3 | -U | 10.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| M3 | +V | 10.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| M3 | -V | 10.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| M4 | +U | 13.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| M4 | -U | 11.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| M4 | +V | 13.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| M4 | -V | 13.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| N3 | +U | 15.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| N3 | -U | 19.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |
| N3 | +V | UNRESOLVED≤30° | INSUFFICIENT_REMAINING_SHELL; no valid manufacturing candidate through 30 deg bounded screen |
| N3 | -V | 14.000° | INCOMPLETE_SLOT_FOOTPRINT, INSUFFICIENT_REMAINING_SHELL |

## Button-by-button screening result

- **N1:** LOCAL VARIANT — MIN_3WAY 0.168217 mm; shell 1.217777 mm; rear PASS
- **N2:** FAIL — MIN_3WAY N/A; shell 1.234163 mm; rear FAIL
- **I2:** REFERENCE — MIN_3WAY 0.145815 mm; shell 1.200134 mm; rear PASS
- **I3:** FAIL — MIN_3WAY N/A; shell 1.211552 mm; rear FAIL
- **I4:** FAIL — MIN_3WAY N/A; shell 1.279506 mm; rear FAIL
- **M3:** LOCAL VARIANT — MIN_3WAY 0.168836 mm; shell 1.204689 mm; rear PASS
- **M4:** LOCAL VARIANT — MIN_3WAY 0.161131 mm; shell 1.213588 mm; rear PASS
- **N3:** FAIL — MIN_3WAY N/A; shell 1.342665 mm; rear FAIL

`0.15 mm` is treated as a practical hardening preference, not a penetration gate. A viable candidate below
that value is LOCAL VARIANT — clearance hardening required, and was not deeply optimized in this batch.

## Detailed authority and manufacturing gates

- ORIGINAL PushBtn detailed faceted BRep: **3,530 triangles**, main body + T1–T4 + corner/bottom detail;
- actuator-only authority: measured D3.35 / projection 2.44 mm;
- each selected non-I2 harness: one fused valid solid, positive four-root common volumes, minimum neck and
  effective FDM section >=1.20 mm, direct blind slots, no receiver/cage/panel/strut/carrier;
- I2: docs/89 STEP and docs/87 rear assembly reused unchanged;
- rear check: START/25/50/75/FULL only; PushBtn translation/rotation 0; no PushBtn-through-harness sequence;
- N2 remains entirely on its owning **JfD** shell half; no new seam architecture was generated.

## ALL-8 simultaneous fit

Closest pair = **M3:M4**, exact minimum
**0.032405 mm**; maximum unintended pair penetration
**0.000000000 mm³**. Pairwise checks include harness↔harness,
leg↔neighbor detailed PushBtn, slot↔slot and overlapping local shell-weakening regions.

## Renders and outputs

- [01_all8_exterior_context_overview.png](../renders/eight_button_four_edge_batch_propagation_screening/01_all8_exterior_context_overview.png)
- [02_all8_shell_interior_harness_overview.png](../renders/eight_button_four_edge_batch_propagation_screening/02_all8_shell_interior_harness_overview.png)
- [03_all8_top_local_axis_overview.png](../renders/eight_button_four_edge_batch_propagation_screening/03_all8_top_local_axis_overview.png)
- [04_all32_legs_angle_visualization.png](../renders/eight_button_four_edge_batch_propagation_screening/04_all32_legs_angle_visualization.png)
- [05_tightest_neighboring_pair_closeup.png](../renders/eight_button_four_edge_batch_propagation_screening/05_tightest_neighboring_pair_closeup.png)
- [06_worst_shell_footprint_closeup.png](../renders/eight_button_four_edge_batch_propagation_screening/06_worst_shell_footprint_closeup.png)
- [07_n2_seam_closeup.png](../renders/eight_button_four_edge_batch_propagation_screening/07_n2_seam_closeup.png)
- [08_i2_reference_closeup.png](../renders/eight_button_four_edge_batch_propagation_screening/08_i2_reference_closeup.png)
- [09_worst_local_variant_closeup.png](../renders/eight_button_four_edge_batch_propagation_screening/09_worst_local_variant_closeup.png)
- [10_fail_closeup.png](../renders/eight_button_four_edge_batch_propagation_screening/10_fail_closeup.png)

- `build123d_workbench/out/eight_button_four_edge_batch_propagation_screening/ALL8_SELECTED_FOUR_EDGE_HARNESSES_AUDIT_ONLY.step`
- `build123d_workbench/out/eight_button_four_edge_batch_propagation_screening/ALL8_DIRECT_SHELL_SLOT_CROPS_AUDIT_ONLY.step`
- `build123d_workbench/out/eight_button_four_edge_batch_propagation_screening/eight_button_four_edge_batch_propagation_screening.json`

Production modification=0; frozen shell modification=0; button pose modification=0; existing validated I2
modification=0. Protected authority hashes preserved: **True**.
STOP after batch classification; no production feature generation or physical coupon generation was performed.
