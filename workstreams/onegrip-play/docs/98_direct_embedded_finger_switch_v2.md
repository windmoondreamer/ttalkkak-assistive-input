# 98 — 8-button direct-embedded V2 corrected surface datum + axial depth rebase

## Datum authority gate — completed before socket Boolean

| Button | Clean opening center recovered | Approved axis recovered | Local shell datum valid | Axial switch shift allowed | Opposite-wall proxy used |
|---|---|---|---|---|---|
| N1 | YES | YES | YES | YES | NO |
| N2 | YES | YES | YES | YES | NO |
| I2 | YES | YES | YES | YES | NO |
| I3 | YES | YES | YES | YES | NO |
| I4 | YES | YES | YES | YES | NO |
| M3 | YES | YES | YES | YES | NO |
| M4 | YES | YES | YES | YES | NO |
| N3 | YES | YES | YES | YES | NO |

All W datums use only the approved 8 × 8 mm opening cutter neighborhood on the intact frozen exterior. Opposite wall, remote shell, and Thumb wall are excluded by the bounded −2.25…11.25 mm local W filter.

## Verdict

**C — DIRECT EMBEDDED STILL FAILS AFTER DATUM CORRECTION**

```text
Direct embedded sockets = 8/8
Actuator-only exposure = 8/8
Simultaneous detailed-switch collision-free positions = 4/8
Body-outside-shell failures = 0/8
Projection range = 1.200–1.200 mm
```

Was docs/97 failure primarily caused by incorrect axial datum interpretation? **YES**

## Per-button corrected V2

| Button | Local exterior datum | Axial depth shift | Socket fit | Body outside shell | Actuator projection | Detailed-switch collision | Terminal access | Result |
|---|---:|---:|---|---:|---:|---|---|---|
| N1 | 0.069 mm | 1.309 mm | PASS | 0.0 | 1.200 mm | NONE | PASS | PASS |
| N2 | 0.006 mm | 1.246 mm | PASS | 0.0 | 1.200 mm | NONE | PASS | PASS |
| I2 | 11.073 mm | 12.313 mm | PASS | 0.0 | 1.200 mm | I2-I3 | PASS | FAIL |
| I3 | 10.530 mm | 11.770 mm | PASS | 0.0 | 1.200 mm | I2-I3 | PASS | FAIL |
| I4 | 2.999 mm | 4.239 mm | PASS | 0.0 | 1.200 mm | NONE | PASS | PASS |
| M3 | 8.755 mm | 9.995 mm | PASS | 0.0 | 1.200 mm | M3-M4 | PASS | FAIL |
| M4 | 9.046 mm | 10.286 mm | PASS | 0.0 | 1.200 mm | M3-M4 | PASS | FAIL |
| N3 | 0.001 mm | 1.241 mm | PASS | 0.0 | 1.200 mm | NONE | PASS | PASS |

## Per-terminal access

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

## Exact neighboring checks

- I2–I3 actual detailed-switch penetration = 1.993728953 mm³; clearance = 0.000000 mm
- I2–I3 breakdown = body/body 1.952711683 mm³; I2 body/I3 terminals 0.041017271 mm³
- M3–M4 actual detailed-switch penetration = 0.009190277 mm³; clearance = 0.000000 mm
- M3–M4 breakdown = terminal/terminal 0.009190277 mm³; body/body 0
- M4–N3 actual detailed-switch penetration = 0.000000000 mm³; clearance = 2.279051 mm
- Socket overlap alone is allowed as connected relief when the detailed switches do not penetrate.
- N2 seam = simple JaD/JfD split pocket; no bridge, harness, or remote support.

Bounded axial screening tested projection pairs only inside 0.8–1.8 mm. It did not clear I2–I3 or M3–M4, so their remaining penetration is a true local detailed-switch conflict rather than a socket-only overlap.

## docs/97 comparison

| Metric | docs/97 | Corrected V2 |
|---|---:|---:|
| Direct embedded sockets | 3/8 | 8/8 |
| Actuator-only exposure | 3/8 | 8/8 |
| Maximum actuator projection reported | 44.834 mm* | 1.200 mm |
| Buttons with body outside shell | 5 | 0 |
| Buttons using local shell datum | not 8 | 8 |
| Opposite-wall proxy used | I4 diagnostic | 0 |

## Baselines and manufacturing gate

- detailed PushBtn source = `cad_dump/mesh_PushBtn.json`, 3530 facets
- measured actuator = D3.35 × 2.44 mm
- actuator hole = D3.65 mm; radial clearance = 0.15 mm
- body/socket clearance = 0.20 mm per side
- epoxy fixation = accepted
- JaD/JfD native valid one-solid = True/1 and True/1
- STEP reimport one-solid = 1 / 1
- STL watertight = True / True
- production overwrite = 0

## Outputs

- `build123d_workbench/out/direct_embedded_finger_switch_v2/DIRECT_EMBEDDED_V2_JaD_AUDIT.step`
- `build123d_workbench/out/direct_embedded_finger_switch_v2/DIRECT_EMBEDDED_V2_JfD_AUDIT.step`
- `build123d_workbench/out/direct_embedded_finger_switch_v2/ALL8_DIRECT_EMBEDDED_V2_SWITCH_REFERENCE.step`
- `build123d_workbench/out/direct_embedded_finger_switch_v2/DIRECT_EMBEDDED_V2_JaD_AUDIT.stl`
- `build123d_workbench/out/direct_embedded_finger_switch_v2/DIRECT_EMBEDDED_V2_JfD_AUDIT.stl`
- `build123d_workbench/out/direct_embedded_finger_switch_v2/direct_embedded_v2_validation.json`
- `docs/98_direct_embedded_finger_switch_v2.md`
- `renders/direct_embedded_finger_switch_v2/01_clean_shell_recovered_axes.png`
- `renders/direct_embedded_finger_switch_v2/02_all8_corrected_external_actuator_only.png`
- `renders/direct_embedded_finger_switch_v2/03_all8_corrected_interior_switches.png`
- `renders/direct_embedded_finger_switch_v2/04_i2_corrected_shell_section.png`
- `renders/direct_embedded_finger_switch_v2/05_i3_corrected_shell_section.png`
- `renders/direct_embedded_finger_switch_v2/06_i4_corrected_shell_section.png`
- `renders/direct_embedded_finger_switch_v2/07_m3_m4_corrected_region.png`
- `renders/direct_embedded_finger_switch_v2/08_i2_i3_neighbor_closeup.png`
- `renders/direct_embedded_finger_switch_v2/09_n2_corrected_split_pocket.png`
- `renders/direct_embedded_finger_switch_v2/10_terminal_access_overview.png`

docs/97 and all earlier history remain unchanged. Physical ITS fit remains the final authority.
