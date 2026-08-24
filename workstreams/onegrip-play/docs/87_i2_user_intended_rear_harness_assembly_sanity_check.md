# 87 — I2 user-intended rear-harness assembly sanity check

| Check | Result |
|---|---:|
| PushBtn fixed in final position | **YES** |
| Harness approaches from interior | **PASS** |
| Four legs enter four slots | **PASS** |
| Elastic deformation required | **NO** |
| Terminal interference during insertion | **NO** |
| Pusher/actuator interference | **NO** |
| Shell unintended interference | **NO** |
| Main-body-bottom seats correctly | **PASS** |
| Final static unintended penetration | **0.000000000 mm³** |

USER-INTENDED REAR-HARNESS ASSEMBLY = **PASS**

## Frozen authority and motion

- docs/86 harness, four leg directions/lengths/roots/thicknesses, seat and four slots: unchanged;
- original `ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID`, T1–T4, corner and bottom details;
- measured actuator D3.35 / projection 2.44 mm;
- PushBtn translation/rotation: exactly 0 for all states;
- common vector: normalized arithmetic mean of the four frozen leg directions = `[-0.049323699195381224, 0.06683869764738527, 0.9965439083123658]`;
- travel: **1.432707826 mm**, deterministically set by the largest blind-depth/vector projection;
- five rigid states only; no vector, angle, root or slot search.

## Five-state exact check

| state | inserted | remaining travel | maximum pair | total unintended | result |
|---:|---:|---:|---:|---:|---:|
| 0 | 0% | 1.432708 | 0.000000000 | 0.000000000 | PASS |
| 1 | 25% | 1.074531 | 0.000000000 | 0.000000000 | PASS |
| 2 | 50% | 0.716354 | 0.000000000 | 0.000000000 | PASS |
| 3 | 75% | 0.358177 | 0.000000000 | 0.000000000 | PASS |
| 4 | 100% | 0.000000 | 0.000000000 | 0.000000000 | PASS |

## Four independent slot entries

| leg | direction·common | start axial retraction | required blind retraction | start lateral offset | max leg↔shell penetration | result |
|---|---:|---:|---:|---:|---:|---:|
| +U | 0.944067 | 1.352573 | 1.352573 | 0.472439 | 0.000000000 | PASS |
| -U | 0.958405 | 1.373114 | 1.200587 | 0.408911 | 0.000000000 | PASS |
| +V | 0.974394 | 1.396023 | 1.200453 | 0.322138 | 0.000000000 | PASS |
| -V | 0.939829 | 1.346501 | 1.333023 | 0.489476 | 0.000000000 | PASS |

All four start offsets remain inside the existing 1.03 mm/side simple entry mouths, pass through the frozen slotted
shell with zero penetration at every sampled state, and end at their own frozen floor points with zero endpoint
error. No elastic bending is assumed.

## Final structural seat

- MAIN BODY BOTTOM ↔ harness seat: distance **0.000000000 mm**, penetration
  **0.000000000 mm³** (intended tangent contact);
- approximate load-bearing contact area: **16.672000 mm²**;
- minimum root neck: **1.250 mm**; all four base/leg common volumes are positive;
- minimum blind seating depth: **1.200453 mm**;
- PushBtn pose change: translation 0 / rotation 0.

The previous docs/85–86 PushBtn-through-harness insertion failure was based on a non-user-intended assembly
sequence and does not invalidate this rear-harness assembly method.

## Renders / scope / preservation

- [01_rear_harness_start.png](../renders/i2_user_intended_rear_harness_sanity_check/01_rear_harness_start.png)
- [02_rear_harness_50_percent.png](../renders/i2_user_intended_rear_harness_sanity_check/02_rear_harness_50_percent.png)
- [03_rear_harness_75_percent.png](../renders/i2_user_intended_rear_harness_sanity_check/03_rear_harness_75_percent.png)
- [04_rear_harness_full_seat.png](../renders/i2_user_intended_rear_harness_sanity_check/04_rear_harness_full_seat.png)

- `build123d_workbench/out/i2_user_intended_rear_harness_sanity_check/i2_user_intended_rear_harness_sanity_check.json`

Sequence C/I3-later=0; 8-button propagation=0; N2=0; coupon=0; production modification=0. All
150 protected docs/79–86 and prior artifacts retain identical SHA-256
hashes: **True**.
