# 97 — 8-button direct-embedded detailed ITS switch reset

## Source recovery

```text
PRE-HARNESS CLEAN EXTERIOR SOURCE FOUND = YES

Source JaD = build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_JaD.step
Source JfD = build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_JfD.step

Finger 8 centers recovered = 8/8
Finger 8 axes recovered = 8/8

Legacy harness slots present in source = NO
Legacy internal harness geometry present = NO
```

## Verdict

**C — DIRECT EMBEDDED ARCHITECTURE FAILS AT SPECIFIC POSITIONS**

```text
Direct embedded sockets completed = 3/8
Actuator-only external exposure = 3/8
Button centers moved = 0 required
Press axes changed = 0 required
Harness parts = 0
Structural legs = 0
Blind leg slots = 0
Pusher parts = 0
Remote/Thumb-wall support = 0
```

## Per-button result

| Button | Center unchanged | Axis unchanged | Socket fit | Actuator hole Ø | External projection | Body visible outside? | Terminal access | Seam issue |
|---|---|---|---|---:|---:|---|---|---|
| N1 | YES | YES | PASS | 3.65 | 0.069 mm | NO | PASS | NONE |
| N2 | YES | YES | PASS | 3.65 | 0.006 mm | NO | PASS | SIMPLE SPLIT POCKET |
| I2 | YES | YES | FAIL | 3.65 | 11.073 mm | YES | FAIL | NONE |
| I3 | YES | YES | FAIL | 3.65 | 10.530 mm | YES | FAIL | NONE |
| I4 | YES | YES | FAIL | 3.65 | 44.834 mm* | YES | FAIL | NONE |
| M3 | YES | YES | FAIL | 3.65 | 8.755 mm | YES | FAIL | NONE |
| M4 | YES | YES | FAIL | 3.65 | 9.046 mm | YES | FAIL | NONE |
| N3 | YES | YES | PASS | 3.65 | 0.001 mm | NO | PASS | NONE |

N2 uses a simple JaD/JfD split pocket. Epoxy is to be applied primarily from the JfD/interior side while keeping the vertical mating seam free; no remote wall is used.

### Per-terminal access

| Button | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| N1 | PASS | PASS | PASS | PASS |
| N2 | PASS | PASS | PASS | PASS |
| I2 | FAIL | FAIL | FAIL | FAIL |
| I3 | FAIL | FAIL | FAIL | FAIL |
| I4 | FAIL | FAIL | FAIL | FAIL |
| M3 | FAIL | FAIL | FAIL | FAIL |
| M4 | FAIL | FAIL | FAIL | FAIL |
| N3 | PASS | PASS | PASS | PASS |

## Bounded failure evidence

- **I2:** body top is 8.633 mm outside local shell; minimum surrounding rim 1.134 mm < 1.20 mm
- **I3:** body top is 8.090 mm outside local shell; minimum surrounding rim 0.964 mm < 1.20 mm
- **I4:** approved centerline has no local direct shell intersection; the 44.834 mm value is a nearest-ring/opposite-wall depth proxy; body top is 42.394 mm outside that proxy
- **M3:** body top is 6.315 mm outside local shell; minimum surrounding rim 1.040 mm < 1.20 mm
- **M4:** body top is 6.606 mm outside local shell; minimum surrounding rim 0.840 mm < 1.20 mm

The measured actuator tip is fixed at every approved external button center (datum error 0.000 mm). A large external-projection value therefore does not mean a longer actuator exists; when the local shell lies more than 2.44 mm behind that frozen point, the original switch body would also remain outside and the direct-embedded position fails.

## Selected bounded values

- actuator-hole candidates: 3.55 / **3.65 selected** / 3.75 mm
- body/socket clearance candidates: 0.15 / **0.20 selected** / 0.25 mm per side
- measured actuator: D3.35 × 2.44 mm
- projection range: 0.001–44.834 mm
- tightest switch pair: I2-I3 = 0.308862 mm, penetration 0.000000000 mm³
- socket-overlap exceptions: I2-I3 = 4.115334 mm³; M4-N3 = 5.797744 mm³

`*` I4 has no direct local-shell hit on the approved centerline; 44.834 mm is the nearest-ring/opposite-wall proxy and is used only to demonstrate failure, not as a manufacturable projection.

The cavity is not a 6 × 6 proxy. Its front region is a non-uniformly expanded copy of the original detailed body, retaining the four exact corner-region features and bottom/body detail while adding 0.20 mm nominal side allowance. A simple rear insertion mouth and four open solder channels are added only behind the body. Epoxy fixation is explicitly allowed; the 0.20 mm side gap and rear-open mouth provide pre-apply or post-seat access.

Original detailed PushBtn source facet count = **3530**. Only its actuator is replaced by the measured D3.35 × 2.44 mm cylinder. Physical ITS fit remains the final authority; CAD PASS is not production approval.

## Manufacturing gate

| Gate | JaD | JfD |
|---|---:|---:|
| valid / one solid | True / 1 | True / 1 |
| STEP reimport valid / one solid | True / 1 | True / 1 |
| STL boundary / non-manifold edges | 0 / 0 | 0 / 0 |

## Outputs

- `build123d_workbench/out/direct_embedded_finger_switch_reset/DIRECT_EMBEDDED_SWITCH_JaD_AUDIT.step`
- `build123d_workbench/out/direct_embedded_finger_switch_reset/DIRECT_EMBEDDED_SWITCH_JfD_AUDIT.step`
- `build123d_workbench/out/direct_embedded_finger_switch_reset/ALL8_DIRECT_EMBEDDED_SWITCH_REFERENCE.step`
- `build123d_workbench/out/direct_embedded_finger_switch_reset/DIRECT_EMBEDDED_SWITCH_JaD_AUDIT.stl`
- `build123d_workbench/out/direct_embedded_finger_switch_reset/DIRECT_EMBEDDED_SWITCH_JfD_AUDIT.stl`
- `build123d_workbench/out/direct_embedded_finger_switch_reset/direct_embedded_finger_switch_reset.json`
- `renders/direct_embedded_finger_switch_reset/01_clean_pre_harness_source.png`
- `renders/direct_embedded_finger_switch_reset/02_all8_exterior_actuator_only.png`
- `renders/direct_embedded_finger_switch_reset/03_all8_interior_switch_overview.png`
- `renders/direct_embedded_finger_switch_reset/04_detailed_pushbtn_measured_actuator.png`
- `renders/direct_embedded_finger_switch_reset/05_representative_embedded_socket.png`
- `renders/direct_embedded_finger_switch_reset/06_four_corner_feature_cavity.png`
- `renders/direct_embedded_finger_switch_reset/07_tightest_neighboring_switch_pair.png`
- `renders/direct_embedded_finger_switch_reset/08_n2_vertical_seam_socket.png`
- `renders/direct_embedded_finger_switch_reset/09_terminal_access_interior.png`
- `renders/direct_embedded_finger_switch_reset/10_assembled_jad_jfd_overview.png`

Production overwrite = **0**. docs/79–96 and all legacy harness research remain preserved.
