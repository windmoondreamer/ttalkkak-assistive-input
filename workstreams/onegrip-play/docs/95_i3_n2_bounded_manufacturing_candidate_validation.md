# 95 — I3 + N2 bounded manufacturing candidate build and validation

## Final result

```text
I3 / N2 manufacturing candidate result:

I3 = FAIL
N2 = FAIL

REMOTE/THUMB-WALL SUPPORT USED = NO required

N2 support configuration:
mechanical slots = 2/4
local compression contacts = 2/4

I3 support configuration:
mechanical slots = 3/4
local compression contacts = 1/4

ALL-8 COMPLETE TOPOLOGY AVAILABLE = NO
ALL-8 STATIC FIT = NOT RUN
```

- Did I3 require any I2 modification? **NO.** Frozen I2 was not modified.
- Did N2 captively bridge JaD/JfD? **YES.** The +U foot interferes with JaD during removal.
- Can JaD still be removed? **NO**, not without breaking/deforming the bounded N2 candidate.
- Does either button rely on adhesive for normal press load? **NO.** Adhesive is not primary load-bearing.

## Scope and authority

docs/94 was used as the latest diagnostic authority. Exterior, button centers, press axes, JaD/JfD split, I2, I4, N1, M3, M4, and N3 remained frozen. Production geometry modification = **0**; physical coupon = **0**; remote/thumb support = **0**. Final checks used the original **3530-facet PushBtn** and the D3.35 × 2.44 mm actuator.

## I3 — bounded 3-slot + 1-contact candidate

| Required metric | Result |
|---|---:|
| -U ↔ frozen I2 harness penetration | 0.067425879 mm³ |
| seat ↔ I2 T3 penetration | 0.000000000 mm³ |
| insertion shell penetration (max) | 0.015558879 mm³ |
| minimum neck | 1.200000 mm |
| minimum effective section | 1.241204 mm |
| rear assembly | FAIL |
| I3 FINAL | **FAIL** |

The allowed corrections were implemented only at the -U root/straight member, the colliding seat edge, and the +U approach edge. The seat–T3 collision is removed and +U retains 2.080153 mm² finite contact area. However, the smallest permitted 1.20 mm -U tangent section still penetrates frozen I2 by 0.067425879 mm³. Further local narrowing would violate the 1.20 mm gate; larger relocation is outside the bounded correction.

| I3 rear state | max unintended penetration (mm³) | limiter |
|---|---:|---|
| START | 0.137921265 | OWN_T1 |
| 25% | 0.125943621 | OWN_T1 |
| 50% | 0.125780483 | OWN_T1 |
| 75% | 0.123998369 | OWN_T1 |
| FULL SEAT | 0.120953465 | OWN_T1 |

## N2 — bounded 2-slot + 2-contact candidate

| Required item | Result |
|---|---|
| -U mechanical slot | PASS |
| -V mechanical slot | FAIL |
| added local thickening | 0.150000 mm |
| added pad volume | 0.867360 mm³ |
| final remaining shell | 1.229642 mm |
| +V local compression foot | PASS |
| +V contact area | 2.080001 mm² |
| +V direct compression | YES |
| +U JaD closure contact | FAIL |
| +U contact area | 2.080000 mm² |
| +U nominal gap / interference | 0.000000000 / 0.000000000 mm |
| captively bridges seam | YES |
| Stage-1 harness insertion | FAIL |
| Stage-2 JaD closure | FAIL |
| JaD removable afterward | False |
| adhesive primary load-bearing | NO |
| N2 FINAL | **FAIL** |

The 0.15 mm inward pad raises the analytical remaining shell to 1.229642 mm, but the seated -V straight leg still has 0.002240894 mm³ JfD-shell penetration. Its collision envelope requires about 0.087217 mm further local W relief, exceeding the remaining 0.029642 mm margin above the 1.20 mm shell gate.

The +U foot forms near-zero-gap finite-area contact only at CLOSED, but at 0.25 mm JaD opening it produces 0.006450649 mm³ penetration. Therefore the candidate mechanically captures JaD and fails serviceability.
Stage-2 closure itself also fails because non-foot N2 geometry has 0.015772462 mm³ unintended penetration with JaD at CLOSED.

| N2 Stage-1 state | max penetration (mm³) | +V gap (mm) | limiter |
|---|---:|---:|---|
| START | 0.000660015 | 0.802619 | JFD_SHELL |
| 25% | 0.000941736 | 0.502515 | JFD_SHELL |
| 50% | 0.001293897 | 0.208704 | JFD_SHELL |
| 75% | 0.001724334 | 0.054770 | JFD_SHELL |
| JfD-SEATED | 0.002240894 | 0.000000 | JFD_SHELL |

| N2 Stage-2 state | candidate-added penetration (mm³) | +U gap (mm) | limiter |
|---|---:|---:|---|
| OPEN | 0.000000000 | 4.036663 | HARNESS |
| 25% | 0.000000000 | 3.402899 | HARNESS |
| 50% | 0.000000000 | 2.484411 | HARNESS |
| 75% | 0.000000000 | 0.486929 | HARNESS |
| CLOSED | 0.015772462 | 0.000000 | JFD_CLOSURE |

## Manufacturing solids

- I3 audit candidate: `build123d_workbench/out/i3_n2_bounded_manufacturing_candidate_validation/I3_BOUNDED_3SLOT_1CONTACT_MANUFACTURING_CANDIDATE_FAIL_AUDIT_ONLY.step` — one fused, valid STEP-reimported solid; system verdict remains FAIL due frozen-I2 interference.
- N2 audit candidate: `build123d_workbench/out/i3_n2_bounded_manufacturing_candidate_validation/N2_BOUNDED_2SLOT_2CONTACT_MANUFACTURING_CANDIDATE_FAIL_AUDIT_ONLY.step` — one fused, valid STEP-reimported solid; system verdict remains FAIL due -V insertion and JaD capture.
- Production outputs: **0**.
- ALL-8 was correctly **NOT RUN** because both bounded candidates did not pass.

## Audit outputs

- JSON: `build123d_workbench/out/i3_n2_bounded_manufacturing_candidate_validation/i3_n2_bounded_manufacturing_candidate_validation.json`
- Report: `docs/95_i3_n2_bounded_manufacturing_candidate_validation.md`
- Render: `renders/i3_n2_bounded_manufacturing_candidate_validation/01_i3_complete_candidate_i2_limit.png`
- Render: `renders/i3_n2_bounded_manufacturing_candidate_validation/02_i3_seat_edge_setback.png`
- Render: `renders/i3_n2_bounded_manufacturing_candidate_validation/03_i3_plus_u_lead_in.png`
- Render: `renders/i3_n2_bounded_manufacturing_candidate_validation/04_n2_two_slot_two_contact_candidate.png`
- Render: `renders/i3_n2_bounded_manufacturing_candidate_validation/05_n2_minus_v_slot_limit.png`
- Render: `renders/i3_n2_bounded_manufacturing_candidate_validation/06_n2_local_contact_feet.png`
- Render: `renders/i3_n2_bounded_manufacturing_candidate_validation/07_n2_jad_removal_capture.png`

Generated: 2026-08-24T19:32:00.763016+00:00
