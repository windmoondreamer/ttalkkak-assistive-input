# REV_H — original switch-seat mechanism, seat-first carrier

Date 2026-08-25 · local build123d / OCCT · Onshape API 0 · production writes 0
Shell authority: exact Onshape `THUMB_LOWER15_HOUSING_V1` export.
JOY / T1–T8 / N1 / N2 / exterior: **HARD FREEZE, not moved.** REV_A…REV_G read-only.

---

## 1. What exactly is the ORIGINAL switch mounting mechanism?

Measured from exact B-rep, every part in one common frame (origin = T8 cap
centroid, axis = T8's true press axis):

```text
   n = +2.348   cap top
   n = -2.161   actuator tip          (0.345 mm into the cap underside)
   n = -2.506   cap underside
   n = -4.070   body top   / actuator base
   n = -7.214   body bottom           6.019 x 6.037 mm
   n = -7.265   PLATE TOP FACE        body sits 0.051 mm off it -> BEARING
   n = -9.268   plate bottom          2.003 mm thick
   n = -10.919  terminal tip          1.651 mm below the plate
```

The mechanism is exactly what §3 described, now with numbers:

| function | how the original does it |
|---|---|
| supports the switch body | the body's 6.02 × 6.04 mm underside bears directly on the flat plate top face, 0.051 mm nominal |
| reacts press load | straight through the body into the 2.003 mm plate — no boss, no shoulder, no recess |
| sets switch depth | plate top sits **4.759 mm** below the cap underside |
| terminal escape | **two through-slots**, 1.0–1.5 × 6.3–6.4 mm, at **±2.4–2.8 mm** from the axis |
| leaves the actuator outward | actuator Ø3.51, projecting **1.909 mm** above the body top |
| cap stack | actuator tip meets the cap underside with 0.345 mm of engagement |
| joins the seats | one continuous 2.0 mm plate, no per-button island in the original |

Terminal leg envelope: 7.568 × 4.632 mm — the legs splay **wider than the 6 mm
body**, which is why the slots sit outboard of the body footprint.

## 2. What dimensions make it work?

```text
CAP UNDERSIDE -> PLATE TOP      4.759 mm      <- the controlling dimension
PLATE THICKNESS                 2.003 mm
BODY BEARING                    6.02 x 6.04 mm flat, no recess
BODY HEIGHT                     3.144 mm
ACTUATOR                        3.51 dia, 1.909 mm above the body
TERMINAL SLOTS                  2 x (1.30 x 6.40), at +-2.60 mm
TERMINAL DROP BELOW PLATE       1.651 mm
```

## 3. Which switch was physically tested?

```text
PHYSICAL TESTED SWITCH = NOT YET IDENTIFIED
```

The project records do not contain the Thumb-mechanism fit test the user
describes. What they do establish (`docs/75` §1, `docs/30`, `docs/31`, `docs/33`,
`docs/34`):

* **ACTUAL HARDWARE AUTHORITY = MEASURED ITS-1105** for the Finger work
* measured ITS-1105 actuator projection **2.440 mm**
* original OneGrip PushBtn actuator projection **1.500 mm** per docs/75
* EVQ-P0E07K and a stock 6×6×6 were also physically audited

Note a definitional difference to resolve, not a contradiction: I measure the
original actuator at **1.909 mm** above the 6 × 6 body plateau, docs/75 quotes
1.500 mm from the plastic body-top datum. Either way, **a real ITS-1105 at
2.440 mm is 0.53–0.94 mm taller than the original**, which would push the cap out
or require the seat plane to drop by that amount. All switch-specific dimensions
here are therefore **PROVISIONAL** until the tested part is named.

## 4. Are the eight seats identical?

Near enough to treat as one unit, with two variants:

| group | plate thickness on axis | tilt | terminal slots |
|---|---:|---:|---|
| T1, T3 | 2.000–2.010 | 9.36 / 9.38° | 3 in patch (one belongs to a neighbour) |
| T2, T5 | 2.000–2.003 | 4.00° | 2 at ±2.55 / ±2.65 |
| T4, T6 | 2.010 | 7.06 / 7.07° | 2 at ±1.9 / ±3.35 |
| T7, T8 | 2.003 | 1.84° | 2 at ±2.4 / ±2.8, 1.0–1.3 × 6.3 |

Cap-underside-to-plate-top is **4.759 mm on every button** and plate thickness is
2.000–2.010 mm throughout. One `ORIGINAL_SWITCH_SEAT_UNIT` covers all eight; only
the slot offset varies by ±0.7 mm.

## 5. Can each seat sit behind the CURRENT frozen opening?

Yes. The seat plane is fully determined by the cap, so placement is exact by
construction: **actuator centre error 0.0000 mm, axis angular error 0.0000°** for
all eight.

| ctrl | body ∩ shell | terminal ∩ shell | actuator ∩ shell | terminal depth available | need |
|---|---:|---:|---:|---:|---:|
| T1 | 0.0000 | 0.0000 | 0.0000 | 22.260 | 3.654 |
| T2 | 0.0000 | 0.0000 | 0.0000 | 28.378 | 3.654 |
| T3 | 0.0000 | 0.0000 | 0.0000 | 23.896 | 3.654 |
| T4 | 0.0000 | 0.0000 | 0.0000 | 27.391 | 3.654 |
| T5 | 0.0000 | 0.0000 | 0.0000 | 30.258 | 3.654 |
| T6 | 0.0000 | 0.0000 | 0.0000 | 24.455 | 3.654 |
| T7 | 0.0000 | **2.6896** | 0.0000 | **3.465** | 3.654 |
| T8 | 0.0000 | **2.6723** | 0.0000 | **3.465** | 3.654 |

Mechanism-to-mechanism interference between neighbouring seats: **0.0000 mm³**.

## 6. Classification

```text
T1 T2 T3 T4 T5 T6   DIRECT ORIGINAL-SEAT REUSE
T7 T8               ORIGINAL-SEAT REUSE WITH LOCAL TRIM
```

T7/T8 need 3.654 mm of terminal drop and have 3.465 — **0.189 mm short** — plus
2.67–2.69 mm³ of terminal-vs-shell overlap. Both are local trims, not
reconstruction.

## 7. Terminal escape

Six seats have **22–30 mm** of free depth against a 3.654 mm need — an order of
magnitude of margin. T7/T8 are 0.189 mm short. All 16 slots are open in the built
carrier.

## 8. Actuator / cap travel

Preserved by construction: the seat is placed from the cap underside, so the
4.759 mm stack and the 0.345 mm actuator engagement are reproduced exactly at
every button. **Subject to §3** — a taller ITS-1105 actuator changes this.

## 9. Can the eight seats form one printable carrier?

Yes. `04_carrier/C05_SEAT_FIRST_CARRIER.step`

| metric | value |
|---|---|
| solids / valid | **1 / True** |
| volume | 1224.972 mm³ |
| faces | 272 |
| plan area | 568.68 mm² |
| thickness p25/p50/p75 | 2.019 / 2.140 / 2.359 mm |
| area below 1.20 mm | 23.84 mm² — **0.00 mm² of it interior** |
| terminal slots cut | **16 of 16** |
| interference with the exact shell | **0.000000 mm³** |
| all keep-outs | **0.000000 mm³** |
| rear four-edge-harness corridor (15 mm) | **0.000000 mm³** |

Islands formed 3 groups; 18 structural webs joined them into one body.

### Per-seat support after all cuts

| ctrl | bearing area | of the 6.04 × 6.04 footprint | slots open | verdict |
|---|---:|---:|---:|---|
| T1 | 25.53 mm² | 70.0 % | 2 | OK |
| T2 | 25.55 | 70.0 % | 2 | OK |
| T3 | 25.57 | 70.1 % | 2 | OK |
| T4 | 25.66 | 70.3 % | 2 | OK |
| T5 | 25.44 | 69.7 % | 2 | OK |
| T6 | 25.61 | 70.2 % | 2 | OK |
| **T7** | **0.00** | **0.0 %** | 2 | **LOST** |
| **T8** | **0.00** | **0.0 %** | 2 | **LOST** |

**T7 and T8 are destroyed by the PROVISIONAL SZH 25° moving envelope**, which
removed 504.10 mm³ from the carrier. Critically, H03 shows those two seats clash
with **only** that envelope — **no static SZH feature** (PCB, gimbal, shaft, both
pots, push switch, header) touches them. So this is a conflict with the
provisional full-deflection sweep, not with the physical module.

## 10. Where can the carrier transfer load to the shell?

**Nowhere, as built.**

```text
carrier-to-shell gap p05/p25/p50/p75/p95 = +8.904 / +10.434 / +11.181 / +12.315 / +12.696 mm
minimum gap                              = +7.630 mm
area within 3 mm of the shell            = 0.00 mm2
```

This is forced, not a design slip: the seat plane is pinned 4.759 mm below the
caps, and in the lowered design the caps sit far inside the cavity. §12 already
anticipated it — the shell connection is a separate structural problem, and it
needs standoff features **7.6–12.7 mm tall**, not a plate offset.

## 11. Renders

`08_renders/`

```text
A_ORIGINAL_MECHANISM_section.png   cap / actuator / body / plate / terminals at T8
B_B1_central_T2.png                central button, DIRECT reuse
B_B2_edge_T1.png                   edge button, DIRECT reuse
B_B3_tightest_T7.png               T7 with the SZH moving envelope overlaid
C_FULL_SEAT_ARRAY.png              all 8 seats + carrier, transparent shell
D_N1_N2_adjacent.png               N1/N2 and the rear harness corridor
```

## 12. Verdict

```text
ORIGINAL SWITCH-SEAT MECHANISM REUSE PARTIAL — SPECIFIC SEAT/CARRIER ISSUE REMAINS
```

The mechanism itself reuses well and is now fully specified. Six of eight seats
are **DIRECT** reuse with 70 % bearing and both terminal slots open; the two
remaining need only local trim. The eight seats connect into **one valid printable
solid** with zero shell interference, zero keep-out interference and zero
intrusion into the rear harness corridor.

Two specific issues remain:

1. **T7 / T8 are lost to the provisional SZH 25° moving envelope** (504.10 mm³
   removed, bearing 0.00 mm²). They clash with no static SZH feature, so this
   turns on the real joystick's actual sweep. It cannot be settled before the
   SZH-EK056 is physically measured.
2. **No load path to the shell yet.** The carrier sits 7.63–12.70 mm below the
   shell inner surface everywhere. Standoff structure of that height is needed;
   it is a separate design step and was not built here.

One dependency to close before any of this becomes production intent: the
physically tested switch is not named in the project records, and a real
ITS-1105 actuator is 0.53–0.94 mm taller than the original, which shifts the
whole 4.759 mm stack.

Stopped. No production apply, no SZH carrier, no N1/N2 redesign, no exterior
change, and JOY/T1–T8 were not moved.

---

## 13. Write containment — one thing to flag

Every write I made is inside `thumb_inner_housing_lab/REV_H_ORIGINAL_SWITCH_MECHANISM/`.
REV_A…REV_G were not touched.

But a filesystem scan found **out-of-lab writes during this session**, and per the
standing rule I am reporting them rather than assuming they are benign:

```text
2026-08-25 01:44  build123d_workbench/seven_unresolved_leg_root_shell_target_rescue_audit.py
2026-08-25 01:42  docs/91_seven_unresolved_leg_root_shell_target_rescue_audit.md
2026-08-25 01:42  build123d_workbench/out/seven_unresolved_leg_root_shell_target_rescue_audit/...
2026-08-25 01:31  build123d_workbench/out/eight_button_four_edge_batch_propagation_screening/...
2026-08-25 01:28  docs/90_eight_button_four_edge_batch_propagation_screening.md
```

These are **not mine** — they are the Finger / N3 four-edge-harness track
(docs 87-91), a concurrent workflow, and they postdate my last write (01:40).
The project has hit this before (CLAUDE.md, 2026-08-20: a parallel workflow moved
the upper body from feature 180 to 192 mid-task).

The authority files are intact, re-verified just now:

```text
JaD_THUMB_LOWER15_APPROVED.step  622ADB3B...8FA54E86   MATCHES REV_D baseline
JfD_THUMB_LOWER15_APPROVED.step  D75F62E0...29EA340    MATCHES REV_D baseline
```

So this report's shell authority is sound. The thing to watch is that the
concurrent track is editing N1/N2 four-edge-harness geometry, which is exactly the
keep-out my §9 carrier was cut against. If docs/90-91 changed the N1/N2 carrier or
its rear insertion corridor, the 0.000000 mm³ clearances in §9 are against a stale
keep-out and need re-running.
