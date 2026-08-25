# 101 — 8-button direct-embedded detailed switch final candidate

## Result

```text
8-BUTTON DIRECT-EMBEDDED FINAL CANDIDATE RESULT:

TRUE-BARE LOWER15 BASE USED = YES

ACTUATOR HOLES = 8/8
DIRECT SWITCH POCKETS = 8/8

ACTUATOR-ONLY EXTERNAL EXPOSURE = 8/8

BUTTON CENTERS CHANGED = 0
PRESS AXES CHANGED = 0

HARNESS = 0
LEGS = 0
PUSHERS = 0
EXTERNAL CAPS = 0

EPOXY FIXATION ASSUMED = YES
```

Verdict = **B — 8/8 CREATED, MINOR PRINT/FIT EXCEPTIONS**

- actuator projection range = **0.673–1.200 mm**
- body-outside-shell failures = **0**
- actual switch-switch collisions = **0**
- tightest conservative switch clearance = **0.656 mm** (I2-I3)
- tightest remaining pocket roof = **0.800 mm**
- N2 seam = **SIMPLE JaD/JfD SPLIT POCKET**

## Required per-button table

| Button | Center unchanged | Axis unchanged | Hole Ø | Actuator projection | Body outside | Terminal access | Switch collision | Result |
|---|---|---|---:|---:|---|---|---|---|
| N1 | YES | YES | 3.65 | 1.200 mm | NO | PASS | NONE | PASS |
| N2 | YES | YES | 3.65 | 1.200 mm | NO | PASS | NONE | PASS |
| I2 | YES | YES | 3.65 | 0.986 mm | NO | PASS | NONE | PASS |
| I3 | YES | YES | 3.65 | 0.992 mm | NO | PASS | NONE | PASS |
| I4 | YES | YES | 3.65 | 0.876 mm | NO | PASS | NONE | PASS |
| M3 | YES | YES | 3.65 | 1.200 mm | NO | PASS | NONE | PASS |
| M4 | YES | YES | 3.65 | 1.195 mm | NO | PASS | NONE | PASS |
| N3 | YES | YES | 3.65 | 0.673 mm | NO | PASS | NONE | PASS |

## Terminal access

| Button | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| N1 | PASS | PASS | PASS | PASS |
| N2 | PASS | PASS | PASS | PASS |
| I2 | PASS | PASS | PASS | PASS |
| I3 | PASS | PASS | PASS | PASS |
| I4 | PASS | PASS | PASS | PASS |
| M3 | PASS | PASS | PASS | PASS |
| M4 | PASS | PASS | PASS | PASS |
| N3 | PASS | PASS | PASS | PASS |

Preferred assembly sequence is: print halves → clean holes/pockets → pre-solder all four
terminals → insert each detailed ITS from the interior → guide its actuator into the D3.65
hole → visually align → apply epoxy around the body/corner region → cure.  Rear-open terminal
channels leave post-insertion touch-up possible, but pre-soldering is more realistic.

## Exact static checks

- I2–I3 switch distance = **0.655652 mm**;
  penetration = **0.000000000 mm³**
- M4–N3 switch distance = **0.869188 mm**;
  penetration = **0.000000000 mm³**
- JaD/JfD final intersection = **0.000000000 mm³**
- Thumb JOY/T1–T8 through-opening check after all pockets = **9/9**
- pocket overlap is not a failure where the actual detailed switches remain disjoint.

## Geometry and manufacturing

- detailed switch source = `cad_dump/mesh_PushBtn.json` (**3,530 facets**)
- preserved source geometry = main body, bottom detail, four terminals, four corner/semicircular features
- measured actuator only = **D3.35 × 2.44 mm**
- actuator opening = **D3.65 mm**, diametral clearance **0.30 mm**, radial clearance **0.15 mm**
- detailed body pocket side clearance = **0.20 mm**
- practical local roof target = **0.80 mm**; requested preferred roof = **1.20 mm**
- JaD native / STEP reimport solid count = **1 / 1**
- JfD native / STEP reimport solid count = **1 / 1**
- JaD/JfD STL watertight = **True / True**
- STL non-manifold edges = **0 / 0**
- exported floating bodies = **0 / 0**
- base/source overwrite = **0**

Physical P1S print plus actual ITS fit remains the final authority.  No mechanical-retention
strength claim is made; epoxy fixation is explicitly assumed.

## Outputs

- `build123d_workbench/out/direct_embedded_finger_switch_final_candidate/ONEGRIP_DIRECT_EMBEDDED_JaD.step`
- `build123d_workbench/out/direct_embedded_finger_switch_final_candidate/ONEGRIP_DIRECT_EMBEDDED_JfD.step`
- `build123d_workbench/out/direct_embedded_finger_switch_final_candidate/ONEGRIP_DIRECT_EMBEDDED_COMBINED_REFERENCE.step`
- `build123d_workbench/out/direct_embedded_finger_switch_final_candidate/ALL8_DETAILED_SWITCH_PLACEMENT.step`
- `build123d_workbench/out/direct_embedded_finger_switch_final_candidate/ONEGRIP_DIRECT_EMBEDDED_JaD.stl`
- `build123d_workbench/out/direct_embedded_finger_switch_final_candidate/ONEGRIP_DIRECT_EMBEDDED_JfD.stl`
- `build123d_workbench/out/direct_embedded_finger_switch_final_candidate/direct_embedded_finger_switch_final_candidate_validation.json`
- `docs/101_direct_embedded_finger_switch_final_candidate.md`
- `renders/direct_embedded_finger_switch_final_candidate/01_assembled_exterior_all8_actuator_holes.png`
- `renders/direct_embedded_finger_switch_final_candidate/02_finger_side_exterior_closeup.png`
- `renders/direct_embedded_finger_switch_final_candidate/03_opposite_finger_side_exterior_closeup.png`
- `renders/direct_embedded_finger_switch_final_candidate/04_interior_all8_detailed_switches.png`
- `renders/direct_embedded_finger_switch_final_candidate/05_representative_socket_without_switch.png`
- `renders/direct_embedded_finger_switch_final_candidate/06_representative_socket_with_detailed_switch.png`
- `renders/direct_embedded_finger_switch_final_candidate/07_four_corner_feature_fit_closeup.png`
- `renders/direct_embedded_finger_switch_final_candidate/08_i2_i3_actual_switch_clearance.png`
- `renders/direct_embedded_finger_switch_final_candidate/09_n2_simple_seam_split_pocket.png`
- `renders/direct_embedded_finger_switch_final_candidate/10_section_actuator_only_exterior_exposure.png`
