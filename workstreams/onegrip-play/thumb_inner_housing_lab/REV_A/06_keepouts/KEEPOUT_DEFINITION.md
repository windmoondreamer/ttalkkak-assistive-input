# KEEPOUT_DEFINITION

Assembly: `06_keepouts/THUMB_KEEPOUT_ASSEMBLY.step` (22 solids)
Data: `06_keepouts/a12_keepouts.json`
Frame: local Thumb frame, origin = lowered joystick centre (`DATUM_P`).

---

## 1. SZH-EK056 — PROVISIONAL, MEASURE ON ARRIVAL

Placement reproduces `szh_ek056_provisional_thumb_integration_audit.py` exactly:
module local `(JOY_X, JOY_Y, PIVOT_Z) = (0.4, 2.0, 11.5)` mapped onto `DATUM_P`,
frame `(DATUM_V, DATUM_U, OUTWARD)`.
Placement origin (world) = `(-2.218540, -29.712721, 31.045329)`.

| feature | class | vol mm³ | u | v | n |
|---|---|---:|---|---|---|
| PCB 34.5 × 26 × 1.6 | **A** | 1389.96 | −15.00 … 11.00 | −17.65 … 16.85 | −13.10 … −11.50 |
| central gimbal | **A** | 3195.50 | −8.30 … 8.30 | −8.75 … 8.75 | −11.50 … −0.50 |
| X pot | **A** | 583.44 | −6.60 … 6.60 | 8.10 … 13.30 | −11.50 … −3.00 |
| Y pot | **A** | 446.25 | 6.10 … 11.10 | −5.15 … 5.35 | −11.50 … −3.00 |
| bottom push switch | **A** | 367.50 | −14.70 … −7.70 | −5.15 … 5.35 | −11.50 … −6.50 |
| shaft | **A** | 253.34 | −2.39 … 2.39 | −2.40 … 2.40 | −0.50 … 13.50 |
| removable knob | **B** | 4549.07 | −10.94 … 10.97 | −10.95 … 10.97 | 5.50 … 26.50 |
| 1×5 header | **B / C** | 106.69 | −8.45 … 3.95 | −23.60 … −14.80 | −11.50 … −8.50 |
| 25° moving envelope | **A** | 26026.42 | −15.00 … 11.00 | −23.70 … 16.85 | −14.30 … 26.50 |

Mount-hole centres in the local frame, Ø3.0 mm, all at n = −11.50:
`(+7.95, −12.40)`, `(+7.95, +14.10)`, `(−11.50, −12.40)`, `(−11.50, +14.10)`.

```text
SZH-EK056 REFERENCE = PROVISIONAL / WEB
docs/71 reference quality = LOW
No sub-mm clearance, no shaft profile, no PCB edge, no header geometry is
treated as final.  MEASURE ON ARRIVAL.
```

Class A features are preserved. Class B (distal pin length, header insulator,
external knob) may be trimmed or replaced later — a stock-header collision alone
is **not** grounds to reject the SZH.

## 2. N1 / N2

```text
N1/N2 EXTERNAL CENTRE + PRESS AXIS   = HARD CONSTRAINT (not touched)
N1/N2 INTERNAL HARNESS               = PROVISIONAL KEEP-OUT
```

`N1_N2_SHARED_CARRIER_N1_LOCAL.step`, 379.53 mm³, occupies
u [−15.32, +5.45], v [−8.48, +4.04], n [−19.13, −11.34].

The four-edge-leg structural harness now under development in the Finger workflow
is **not** redesigned or second-guessed here; the current carrier is used as a
coordination envelope with 0.50 mm clearance and the Thumb candidate simply stays
out of it.

Note the overlap this exposes: the SZH PCB wants n [−13.10, −11.50] and the N1/N2
carrier occupies n [−19.13, −11.34] over u [−15.32, +5.45]. They contend for the
same depth band. This reproduces the `docs/71` `PCB ↔ N1/N2` conflict in the
correct (frozen) shell frame.

## 3. Original shell-side M3 screws

Three occurrences from `ORIGINAL_FASTENING_REFERENCE.step`, 176.72 mm³ each,
clearance 1.00 mm:

| # | u | v | n |
|---|---|---|---|
| 1 | −8.71 … 10.29 | −70.96 … −65.46 | −28.99 … −23.49 |
| 2 | −8.77 … 10.24 | −20.15 … −14.65 | −11.50 … −6.00 |
| 3 | −8.80 … 10.20 | 15.54 … 21.03 | −9.55 … −4.06 |

## 4. Frozen Thumb controls

Nine cap solids with their press axes, derived from each cap's dominant planar
face normal (a PCA OBB on a square plate snaps to the 45° diagonal — `docs/73`).
All eight buttons sit at **4.00°** from the joystick axis; the joystick itself at
0.00°. Cap footprints and axes are in `a12_keepouts.json` under
`FROZEN_CONTROL_AXES`.

## 5. Clearances used by C01

| target | clearance |
|---|---:|
| frozen shell (conformal standoff) | 1.20 mm |
| control apertures around cap footprint | 0.60 mm |
| SZH static + moving envelope, N1/N2 carrier | 0.50 mm |
| original M3 screws | 1.00 mm |

## 6. Depth budget — the fact that shapes the next candidate

```text
Thumb wall inner surface     n = +11.1 .. +14.0
joystick pivot (DATUM_P)     n =   0.0
SZH PCB                      n = -11.5 .. -13.1
opposite (palm) wall inner   n = -12.9 (measured at u=0, v=+-12)

usable cavity depth          about 26 mm
SZH needs                    about 13 mm below pivot + 11..14 mm above
```

The cavity is almost exactly full. A conformal plate sitting under the Thumb wall
cannot also be the SZH mounting deck; the joystick has to be carried on a cradle
that descends ~22 mm, or referenced off the opposite wall. The original HW504
needed only 12.25 mm below the pivot, which is why the original single-plate
architecture worked there and does not transfer unchanged.
