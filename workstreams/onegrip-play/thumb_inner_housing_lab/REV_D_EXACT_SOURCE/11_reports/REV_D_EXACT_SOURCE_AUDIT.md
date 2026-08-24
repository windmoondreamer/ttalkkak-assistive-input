# REV_D — exact Onshape source audit

Date 2026-08-24 · local build123d / OCCT · Onshape API 0 · production writes 0
REV_A / REV_B / REV_C read-only. C01 read-only. No shell reconstruction.

---

## 0. Authority

```text
MASTER            Onshape OneGrip_Play_V1
                  did a21e64f36bc61df760d4587c
                  version THUMB_LOWER15_HOUSING_V1 (50dfe4e752e447375b95493a)
                  eid 425d9199b59cfb1efd9ddc35, configuration default
LOCAL EXACT       thumb_exact_onshape_source/JaD|JfD_THUMB_LOWER15_APPROVED.step
LEGACY DEFECTIVE  JAD|JFD_EXTERIOR_LOWERED_THUMB_V1.step  (explanation only)
DIAGNOSTIC ONLY   REV_C reconciled shell
```

---

## 1. Export verification — PASS

SHA-256, all four files, independently recomputed:

| file | result |
|---|---|
| `JaD_THUMB_LOWER15_APPROVED.step` | **MATCH** `622ADB…4E86` |
| `JfD_THUMB_LOWER15_APPROVED.step` | **MATCH** `D75F62…A340` |
| `JaD_THUMB_LOWER15_APPROVED.x_t` | **MATCH** `2CFD9C…2453` |
| `JfD_THUMB_LOWER15_APPROVED.x_t` | **MATCH** `5C50F3…55F5` |

Independent import (not trusting the supplied validation file):

| | JaD | JfD |
|---|---|---|
| solids / shells | 1 / 1 | 1 / 1 |
| valid | **True** | **True** |
| faces | 189 | 506 |
| volume mm³ | 47672.492182 | 50150.761749 |
| Δ vs supplied | **−0.458247** | **+0.263678** |
| bbox size mm | 38.779774, 123.860259, 152.135292 | 38.779770, 123.860259, 152.135292 |
| Δ bbox | 0, −0, 0 | −0, −0, 0 |
| X span | [−0.000005, 38.779770] | [−38.779770, 0.000000] |

The volume deltas are 0.00096 % and 0.00053 % — OCC-versus-Onshape mass-property
tolerance, the same class of difference already documented in `docs/26`. Bounding
boxes agree to 1e-6 mm. The shell split at X = 0 is clean.

**Through-openings on each control's TRUE press axis: PASS 9 / 9.**
Footprint open fraction: JOY 73 %, T1 98 %, T2 96 %, T3 94 %, T4 100 %, T5 96 %,
T6 96 %, T7 98 %, T8 92 %.

---

## 2. Does the exact shell contain the expected Thumb geometry?

**Yes.** Nine full through-openings, correct wall, correct split, single valid
solid per half. Nothing needs restoring, recutting or reconstructing.

---

## 3. What survives from REV_A / REV_B / REV_C

Re-measured against the exact shell, not assumed.

| finding | status |
|---|---|
| **Lowered Backplate does not conform** — REV_A's core result | **CONFIRMED and real.** gap p50 was 9.027 mm against the defective STEP; against the exact approved shell it is **8.948 mm**. Not a reconstruction artefact. |
| ORIGINAL design law: one ~2 mm swept plate riding ~1.2 mm off the shell with a real contact band | **CONFIRMED.** Re-measured: thickness p50 **2.003 mm**, gap p10/p25/p50/p75/p90 = **+0.350 / +0.796 / +1.230 / +1.443 / +1.633**, contact band ≤0.30 mm = **95.06 mm² = 7.48 %**, 0 interfering columns, 0 columns beyond 6 mm |
| Original contact is at the plate **perimeter**, not under the buttons | **CONFIRMED.** Two zones: **71.69 mm²** at u[−20.00, −12.00] v[−49.00, −30.75] (7.42 mm from T3) and **23.38 mm²** at u[13.25, 19.50] v[−49.00, −40.25] (8.71 mm from T1) |
| Frozen cap 3D positions and press axes are correct; no HARD FREEZE change needed | **CONFIRMED, and now stronger** — the approved shell opens all nine |
| TRUE press axes 0.00 / 1.84 / 4.00 / 7.06 / 7.07 / 9.36 / 9.38° | **VALID**, used throughout REV_D |
| REV_A's `press_axis` returned one common 4.00° seating-plane axis for all eight buttons | **VALID** — the bug is real and stays corrected |
| docs/71 read `FINGER_V2`, not the approved shell | **VALID** — but its numbers change again, see §6 |

## 4. What must be discarded

Everything below was a property of the **defective local reconstruction**, not of
the approved design:

* **T2 / T4 / T6 / T7 / T8 sealed or partially cut.** The approved shell opens
  all nine. REV_A's "0.0 % clear path" and REV_B's A/B/C classification table
  describe the legacy file only.
* **"Caps sit 3.66–3.71 mm behind an intact wall."** Discarded.
* **The whole REV_C reconciliation branch**: the 97.43 mm² excess, the 53.86 mm²
  "inherited over-cut", the **T1 0.283 mm ligament**, the JOY/T1/T3 over-size —
  all artefacts. There is nothing to reconcile.
* **REV_C C01R**, including its two inward-shifted pads, its trim strategy and
  its 0.200 mm³ residual interference. Built against a diagnostic shell;
  superseded. Not carried forward.
* **REV_B's docs/71 correction figures** are themselves superseded — see §6.

---

## 5. ORIGINAL Inner Housing vs the TRUE approved lowered shell

| | ORIGINAL Backplate vs ORIGINAL shell | LOWERED Backplate vs EXACT APPROVED shell |
|---|---:|---:|
| plan area | 1986.62 mm² | 1986.62 mm² |
| gap p25 / p50 / p75 | +0.796 / **+1.230** / +1.443 | +6.594 / **+8.948** / +10.475 |
| gap min / max | +0.000 / +4.801 | +0.003 / +14.151 |
| contact ≤ 0.30 mm | **95.06 mm² (7.48 %)** | **2.88 mm² (0.18 %)** |
| contact zones ≥ 1 mm² | 2 | **none** |
| columns beyond 3 mm | 301 | 24,138 |
| columns beyond 6 mm | **0** | 19,956 |
| plate thickness p50 | 2.003 mm | 2.003 mm |

The rigid `(0, +12.25, −21.00)` transform genuinely moves the Backplate about
9 mm away from the shell inner surface, and destroys the contact band that
carried press load. This is confirmed against the true approved geometry.

**Why the original was so compact:** it did not float. It rode 0.8–1.6 mm off
the inner surface across the whole span and **landed on the shell along two
perimeter zones at the −v end**, one on each side, 7–9 mm clear of the nearest
button. Those zones are the load path; the rest is assembly clearance. There is
no zero-gap-everywhere intent anywhere in the original.

---

## 6. SZH-EK056 vs the exact shell — PROVISIONAL, no carrier designed

| feature | legacy (defective) | **EXACT APPROVED** | delta |
|---|---:|---:|---:|
| PCB | 181.1338 | **181.1344** | +0.0006 |
| gimbal / x-pot / y-pot / push switch | 0 | **0** | 0 |
| shaft | 0.0000 | **0.0000** | 0 |
| removable knob | 44.7960 | **141.8982** | **+97.10** |
| header plastic | 73.3779 | **73.3779** | 0 |
| 25° moving envelope | 1839.5688 | **2050.5410** | **+210.97** |

The knob and the moving envelope interfere substantially **more** with the true
shell than with the defective one, so REV_B's "knob collision is 89 % smaller"
correction is itself superseded. PCB and header are unchanged: they contend with
the deep cavity, not the Thumb face.

Free depth below the pivot, measured on 14 columns, exact vs legacy:

```text
EXACT APPROVED   min 6.403   median 17.241   max 33.757 mm
LEGACY           min 6.403   median 18.460   max 33.760 mm
SZH PCB needs    13.1 mm
```

The two shells agree here to ~0.03 mm on every common column, so the depth budget
is **not** a reconstruction artefact. At the joystick centre there is 17.08 mm of
free depth against 13.1 mm required. The shallow spot is at (0, −20), 6.40 mm.

SZH remains **PROVISIONAL / MEASURE ON ARRIVAL**. No sub-mm design decision was
taken and no carrier was created.

---

## 7. C01 against the exact approved shell

| metric | result |
|---|---|
| interference | **0.002603 mm³** (tolerance level, over 1503 mm² of plan) |
| gap p10 / p25 / p50 / p75 / p90 | +1.144 / **+1.177 / +1.192 / +1.201** / +1.211 mm |
| gap min / max | +0.002 / +3.570 mm |
| structural continuity | **1 solid** |
| aperture alignment | **blocks 0 % of all nine openings**; clear path 73–99 % |
| N1/N2 shared carrier | **0.000000 mm³** |
| all nine SZH features + 25° moving envelope | **0.000000 mm³** each |
| three original M3 screws | **0.000000 mm³** each |
| contact ≤ 0.30 mm | 20.81 mm² = 1.39 % |
| thickness p25 / p50 / p75 | 2.396 / 2.400 / 2.400 mm |

The conformal law C01 was built to still holds against the true shell, and the
numbers barely moved from those measured against the defective file (p50 1.196 →
1.192). C01's design never depended on the bad openings.

### What is specifically wrong with C01

**1. Plan-boundary knife edge.** 100.12 mm² of the 1503.19 mm² plan is below
1.20 mm, minimum **0.0004 mm**. 15.12 mm² of that sits more than 1 mm inboard of
the boundary, but never more than **2.25 mm** — it is a taper band at the −v end
(u[−11.00, −3.25] and u[3.75, 11.50] at v[−49.00, −47.50]), not an interior
island. Unprintable on a 0.4 mm nozzle; must be trimmed back.

**2. Load path is 4.6× short.** C01 has 20.81 mm² of contact against the
original's 95.06 mm². Its five contact zones are all at the plate edge:

| zone | area mm² | min gap | location | nearest control |
|---|---:|---:|---|---|
| 1 | 5.44 | 0.012 | u[−14.00, −8.75] v[−47.25, −46.00] | T3, 5.84 mm |
| 2 | 5.25 | 0.031 | u[9.25, 14.25] v[−47.25, −46.00] | T1, 5.96 mm |
| 3–5 | 8.44 total | 0.002 | u = ±20.25…20.75 | JOY / T7, 13–21 mm |

Zones 1 and 2 are in the **same region as the original's two perimeter zones**
(−v end, one left one right). So C01 touches in roughly the right places — it
simply does not reach far enough or bear enough area. That is a much smaller
problem than REV_C concluded.

---

## 8. Is a new candidate required?

**Yes, but a targeted revision, not a replacement.** The architecture is right:
one conformal swept plate at ~1.2 mm standoff, single solid, clear of every
opening and every keep-out. Two local changes are needed:

1. trim the plan boundary back to full thickness (≥ 1.60 mm preferred);
2. extend and thicken the plate at the two −v perimeter zones so it lands on the
   shell where the original did, recovering something near 95 mm² of contact.

**Do not** reuse REV_C's C01R pads: they were snapped 13.68 / 14.21 mm inboard
because the C01R plan could not reach the perimeter, which put the load path
between the buttons instead of at the rim. The correct move is the opposite —
grow the plate outward to the original zones.

---

## 9. Source-faithful load-transfer strategy for the next candidate

```text
CONTACT           two perimeter zones at the -v end, one per side,
                  target 70 mm2 left and 25 mm2 right, matching
                  u[-20.0,-12.0] v[-49.0,-30.8] and u[13.3,19.5] v[-49.0,-40.3]
STANDOFF THERE    0.00 - 0.15 mm (the original reaches 0.000 on the left zone)
EVERYWHERE ELSE   0.8 - 1.6 mm assembly clearance, as the original
NEVER             a global offset, a zero-gap field, or a friction fit
```

Every low-gap zone in the next candidate must be labelled INTENTIONAL LOAD
TRANSFER or ASSEMBLY CLEARANCE, as here.

---

## 10. Are we ready to design the final architecture?

Partly.

* **Conformal substrate — ready.** The exact shell is verified, the design law is
  measured, and C01 is a validated starting point needing two local fixes.
* **Button seats — not ready.** The Thumb switch is still open in `CLAUDE.md` §3
  (`PushBtn` vs ITS-1105). No seat pocket is defensible until that closes.
* **SZH carrier — not ready.** SZH stays provisional; the knob and moving-envelope
  interference both grew against the true shell and need real measurements.

---

## 11. Renders

`thumb_inner_housing_lab/REV_D_EXACT_SOURCE/08_renders/` — five matched section
planes × three configurations, identical camera per section.

```text
S1_JOY_{A,B,C}.png            v =  +0.0   through the joystick centre
S2_BUTTON_ROW_{A,B,C}.png     v = -30.4   T2 / T4 / T6 row
S3_T1_T3_{A,B,C}.png          v = -40.8   T1 / T3 / T5 row
S4_N1_ADJACENT_{A,B,C}.png    u = -10.0   through the N1/N2 carrier region
S5_N2_ADJACENT_{A,B,C}.png    u =  +2.0
```
A = original shell + original Backplate · B = exact approved shell + lowered
Backplate · C = exact approved shell + C01.

Most legible: **S2_BUTTON_ROW_A vs _B vs _C**.

---

## 12. Verdict

```text
EXACT SOURCE VERIFIED — C01 REQUIRES SPECIFIC REVISION
```

The export is byte-verified and geometrically sound, with all nine Thumb
openings present. C01 remains a valid conformal substrate against it —
0.0026 mm³ interference, the 1.19 mm gap law intact, zero keep-out contact, zero
opening obstruction. It needs exactly two local revisions: remove the
plan-boundary knife edge, and extend the plate to the two original perimeter
zones to restore the load path from 20.81 mm² toward 95.06 mm².
