# REV_B — audit only

Date 2026-08-24 · local build123d / OCCT · Onshape API 0 · production writes 0
REV_A is untouched and read-only. C01 was read, never modified.

---

## 1. Frozen-shell authority, re-decided without cap/shell intersection

The objection is valid: REV_A's A03 inferred "the shell contains the lowered
opening" from a cap/shell intersection of ~0, and a cap that never reaches the
wall gives ~0 as well. A03 was not independently decisive.

Two replacement tests, neither of which uses cap collision.

### 1.1 Direct opening localisation (B03 TEST 2)

Holes in the Thumb wall found from the shell alone — no cap solid involved —
then matched against the ORIGINAL and LOWERED control positions.

| shell | significant holes | match LOWERED | match ORIGINAL |
|---|---:|---:|---:|
| FROZEN | 7 | **7** | 0 |
| FINGER_V2 | 10 | 2 | **8** |

FROZEN's holes sit 1.22–3.01 mm from the lowered control centres.
FINGER_V2's sit 0.21–1.01 mm from the original ones.

### 1.2 Wall thickness sampled over each control footprint (B05)

6 × 6 mm patch on the wall-thickness map, at both position sets, no caps used:

| shell | at ORIGINAL positions | at LOWERED positions |
|---|---|---|
| CLEAN | 9 of 9 open, mean wall **0.018 mm** | mean wall 2.342 mm |
| FINGER_V2 | 8 of 9 open, mean wall **0.027 mm** | mean wall 2.593 mm |
| FROZEN | 1 of 9 open, mean wall **2.470 mm** | 4 of 9 open, mean wall **1.436 mm** |

FROZEN has filled the original openings (0.018 → 2.470 mm) and cut at the
lowered ones (2.342 → 1.436 mm).

```text
FROZEN EXTERIOR AUTHORITY = CONFIRMED
    JAD/JFD_EXTERIOR_LOWERED_THUMB_V1.step is the shell carrying the lowered
    Thumb openings.  Established without cap/shell intersection.
```

### 1.3 Required table — TRUE-axis classification (B04)

TRUE axis = outward normal of each cap's **user-facing** face (B02).
A = continuous wall ≥ 2.00 mm · B = partial, not through · C = full through-opening.
Interval is measured along that exact axis, outboard of the cap.

| control | tilt | CLEAN | FINGER_V2 | FROZEN | FROZEN interval (mm) | FROZEN wall |
|---|---:|---|---|---|---|---:|
| JOY | 0.000° | B 1.349 | B 1.349 | **C** | — | 0.000 |
| T1 | 9.362° | A 3.069 | A 3.069 | **C** | — | 0.000 |
| T2 | 4.000° | A 3.012 | A 3.012 | **B** | [6.706, 7.932] | 1.227 |
| T3 | 9.377° | A 3.067 | A 3.067 | **C** | — | 0.000 |
| T4 | 7.073° | A 2.938 | A 2.938 | **B** | [6.982, 7.340] | 0.358 |
| T5 | 4.000° | A 3.051 | A 3.051 | **C** | — | 0.000 |
| T6 | 7.060° | A 2.957 | A 2.957 | **B** | [6.968, 7.245] | 0.277 |
| T7 | 1.839° | C | C | **A** | [5.991, 8.972] | 2.981 |
| T8 | 1.839° | C | C | **A** | [5.965, 8.952] | 2.987 |

(CLEAN and FINGER_V2 are identical in the Thumb region, as expected — they are
the same shell there. REV_B's first pass cropped CLEAN with a box shifted by
THUMB_DELTA and made them disagree; that was the crop, not the geometry.)

---

## 2. docs/71 "wrong shell" claim

Re-measured by placing the SZH-EK056 reference at the same datum and
intersecting it with **both** shells.

| SZH feature | docs/71 reported | Lab, FINGER_V2 | Lab, FROZEN | change |
|---|---:|---:|---:|---:|
| PCB | 181.1349 | 181.1341 | 181.1338 | −0.0003 |
| SHAFT | 11.8241 | 11.8275 | **0.0000** | **−11.83** |
| REMOVABLE_KNOB | 422.1080 | 422.1701 | **44.7960** | **−377.37** |
| HEADER_PLASTIC | 69.9069 | 73.3779 | 73.3779 | 0.0000 |
| 25° moving envelope | — | 2072.2183 | 1839.5688 | −232.65 |
| gimbal / x_pot / y_pot / push_switch | — | 0.0000 | 0.0000 | 0.0000 |

The FINGER_V2 recomputation reproduces docs/71 to 0.0008 / 0.003 / 0.06 mm³ on
PCB / SHAFT / KNOB, which confirms docs/71 did read FINGER_V2.

```text
docs/71 WRONG-SHELL CLAIM = CONFIRMED WRONG SHELL
    but the scope is narrower than REV_A implied.
```

Only **3 of 9** SZH features change when the correct shell is used:

* `SHAFT ↔ local_shell` — the collision **does not exist** in the frozen shell
* `REMOVABLE_KNOB ↔ local_shell` — 89 % smaller
* moving envelope ↔ shell — 11 % smaller

`PCB ↔ local_shell` and `HEADER_PLASTIC ↔ local_shell` are unchanged: those
collisions are with the deep cavity walls, not the Thumb face. **Every docs/71
row that involves N1/N2 rather than the shell is unaffected**, so docs/71's core
conclusion (SZH contends with N1/N2 for the same depth band) still stands.

REV_A over-stated this as "every `local_shell` row". Corrected here.
docs/71 was not modified.

---

## 3. Lineage of the approved exterior

```text
JAD/JFD_CLEAN_PRE_FINGER.step          original exterior, original Thumb openings
        |
        |  integrated_exterior_clean_v1.py
        |    1. restore_original_thumb_openings()   FILL the old openings
        |    2. opening_voids()                     take the old opening VOID solids
        |    3. move(void, (0,+12.25,-21))          translate the VOIDS rigidly
        |    4. cut_shapes(restored, voids + finger cutters)
        v
   FINAL EXTERIOR CLEAN V1
        |
        |  integrated_exterior_lowered_thumb_v1.py
        |    5. thumb_user_side_service_box(control, 0.80)
        |       = world-axis AABB of each control + 0.80 mm, clipped to a slab
        |    6. cut_shapes(shell, 9 AABB tools)
        v
   JAD/JFD_EXTERIOR_LOWERED_THUMB_V1.step        <-- the "exact" pair
        |
        |  a SEPARATE branch produced what the user actually looked at:
        |    regional mesh graft, docs/53 "Actual lower-15 housing visual graft"
        |    Thumb patch taken from THUMB_LOWER15_HOUSING_V1 Onshape STL
        v
   EXTERIOR_FIRST_LOWERED_THUMB_VISUAL_REFERENCE.stl    <-- the APPROVED image
```

So the approved exterior is **mechanism D**: the visible Thumb region came from
a different Onshape model, while the exact STEP was reconstructed by translating
old opening voids and cutting AABB service boxes. The two were never reconciled.

Measured consequences (B07 / B08):

| representation | significant holes in the Thumb wall |
|---|---:|
| `THUMB_LOWER15_HOUSING` (the approved source) | **11** — one at every control, 47.7–173.6 mm² |
| exact frozen STEP | **7** — none at T2, T4, T6, T7, T8; areas 6.7–96.8 mm² |

---

## 4. The 3.66–3.71 mm number, and whether the caps are misplaced

Cap outermost point → skins, along each control's TRUE axis:

| control | vs LOWER15 (approved surface) | vs exact STEP: wall | cap top → inner skin |
|---|---|---:|---:|
| JOY | **open** — no material outboard | open | — |
| T1 | **open** | open | — |
| T2 | **open** | 1.227 | +4.328 |
| T3 | **open** | open | — |
| T4 | **open** | 0.358 | +4.562 |
| T5 | **open** | open | — |
| T6 | **open** | 0.277 | +4.555 |
| T7 | **open** | 2.981 | **+3.655** |
| T8 | **open** | 2.987 | **+3.626** |

Reference, ORIGINAL cap vs CLEAN shell on the same axes: **all nine open** — the
same result as the frozen caps against the approved surface.

REV_A's "3.66–3.71 mm" is the cap-top-to-inner-skin distance **for T7/T8 only,
and only against the exact STEP**. It is not a property of the cap.

Outer-skin agreement, exact STEP vs LOWER15, 44 sampled columns:

* 38 surface columns: mean **+0.0197**, median **+0.0187**, max |Δ| **0.0924 mm**
* 6 columns disagree by 20–33 mm — all at JOY (v = 0) and T7/T8 (v = −20),
  i.e. exactly where LOWER15 is open and the exact STEP is not

```text
Is the CAP misplaced?                                        NO
Is the OPENING/wall mismatched around a correct cap?         YES, in the exact STEP
Is the file we called "frozen exterior" the state approved?  SURFACE yes, OPENINGS no
```

The approved surface is reproduced to 0.09 mm. The approved openings are not
reproduced at all for five of the nine controls.

**No cap axial motion is proposed, and none is required.**

---

## 5. C01 thin-region audit

100.12 mm² of the 1503.19 mm² plan area is below 1.20 mm (6.66 %), in 34
connected regions.

| class | area mm² | share of thin area |
|---|---:|---:|
| PLAN_TRIM_EDGE | 80.38 | 80.3 % |
| BOOLEAN_SLIVER | 10.00 | 10.0 % |
| BUTTON_APERTURE_EDGE | 9.75 | 9.7 % |
| STRUCTURAL_LOAD_PATH | **0.00** | 0.0 % |
| NONSTRUCTURAL_REGION | **0.00** | 0.0 % |

```text
INTERIOR (NON-EDGE) THIN AREA = 0.00 mm2
```

Every sub-1.20 mm region is an edge or a sliver, so the gate in §5 of the brief
is met and C01 keeps PROMISING on this criterion.

Measurement correction made during the audit: the first pass classified the
largest region (46.12 mm², u [−14.25, 14.25], v [−50.00, −46.00]) as an interior
`NONSTRUCTURAL_REGION`. That was a tool error — `distance_transform_edt` does not
treat the array border as background, and that region lies exactly on the blank
boundary at v = −50. Padding the mask before the transform moves it, and the two
regions at u = +21, into `PLAN_TRIM_EDGE`, which is what they are.

**Deficiency to carry forward (not a structural failure):** the trim edge thins
to 0.000–0.012 mm over roughly 80 mm². A knife edge will not print on a 0.4 mm
nozzle. A revision should trim the plan boundary back to a finite edge.

---

## 6. C01 shell-gap audit

| band | columns | area mm² | share |
|---|---:|---:|---:|
| < 0.20 mm | 117 | 7.31 | 0.5 % |
| 0.20 – 0.40 | 49 | 3.06 | 0.2 % |
| 0.40 – 0.80 | 4 | 0.25 | 0.0 % |
| 0.80 – 1.20 | 15,623 | 976.44 | 65.0 % |
| ≥ 1.20 | 8,258 | 516.12 | 34.3 % |

Six connected zones lie below 0.40 mm, 8.87 mm² in total, min gap 0.001 mm.

Classification: **none of them is intended load-transfer contact.** C01 has no
designed contact feature; these zones are a by-product of the standoff being
built by a single-direction translation, which under-clears where the wall
normal is oblique to n. On a P1S with a 0.4 mm nozzle a 0.001–0.20 mm gap between
two separately printed parts is an interference fit after tolerance, so all six
are **ASSEMBLY_CLEARANCE_BOTTLENECK**.

The more important number is the comparison with the original design:

| | contact band | |
|---|---:|---|
| original Backplate | gap ≤ 0.30 mm on **6.4 %** of columns | designed load transfer |
| C01 | gap < 0.30 mm on **0.59 %** of columns | incidental |

C01 reproduced the original *offset* but not the original *contact*. The
original plate lands on the shell along a band and pushes press load into it;
C01 floats at ~1.2 mm almost everywhere. That is the second item a revision must
address, and it is a design gap rather than a defect.

---

## 7. Answers

1. **REV_A frozen-shell authority — CONFIRMED**, by two cap-free tests (§1).
2. **docs/71 wrong-shell — CONFIRMED**, but only the SHAFT / KNOB / moving-envelope
   rows are affected; the N1/N2 rows and the PCB and header rows stand (§2).
3. **A03 vs A09 were not contradictory, both were unsound.** A03 used a criterion
   that a buried cap also satisfies. A09 used a wrong axis: REV_A's `press_axis`
   selects each cap's largest face, which is the **seating** face, giving one
   common 4.00° axis for all eight buttons. True tilts are 0.00 / 1.84 / 4.00 /
   7.06 / 7.07 / 9.36 / 9.38°. Both happened to reach the right authority
   conclusion for the wrong reason.
4. **Frozen cap 3D positions — NOT wrong.** Against the approved surface all nine
   controls are open, exactly like the original design (§4).
5. **No HARD FREEZE change is required.** No cap motion, no axis change, no
   surface change, no relocation of any opening. The openings the user approved
   already exist, at the correct places, in the approved geometry.
6. **C01 — still promising** on the stated gate (interior thin area 0.00 mm²),
   with two documented deficiencies: an unprintable 80 mm² knife edge at the plan
   trim, and no load-transfer contact band (0.59 % vs the original 6.4 %).
7. **Solvable internally, with the exterior untouched:** the conformal inner
   housing itself; the C01 trim edge; a designed contact band; the SZH 26 mm
   depth budget; N1/N2 coordination. The one thing that is *not* an internal
   problem is that the exact STEP does not reproduce the approved openings — and
   that is a reconstruction discrepancy between two artefacts, not a freeze
   violation.

## 8. Verdict

```text
B.  FROZEN EXTERIOR VALID — SPECIFIC GEOMETRIC CONFLICT FOUND,
    USER DECISION REQUIRED
```

The exterior the user approved is valid and self-consistent: correct openings at
all nine lowered controls, correct cap positions, surface reproduced by the exact
STEP to 0.09 mm.

The conflict is between two artefacts of the same approved state. The exact STEP
pair, which every downstream audit including REV_A has been measuring against,
does not reproduce the approved openings for T2, T4, T6, T7 and T8. Which
artefact is the geometric authority going forward is a decision for the user.

No unfreeze is requested. Nothing was applied.

## 9. Source integrity

All 13 Thumb authority sources are byte-identical to the REV_A baseline
(`00_admin/b11_source_check.json`).  Writes were confined to `REV_B/`.

Files outside the Lab that changed during this session: 8, all Finger
switch-harness work from the concurrent workflow
(`four_edge_leg_harness_captive_pusher_audit.py` modified; four new
`i2_*` / `direct_shell_*` scripts; `docs/80`, `docs/81`, `docs/82`).  None is in
the Thumb dependency set and none is read by any Lab script.

**One REV_A slip, recorded rather than hidden:** the source checker was first run
from `REV_A/10_scripts/a16_source_check.py`, which regenerated
`REV_A/00_admin/a16_source_check.json` at 2026-08-24.  That file is an audit
output, not a REV_A result; its verdict is unchanged (0 authority sources
changed) and only the concurrent-workflow file list grew.  No REV_A geometry,
report or measurement was touched.  The checker now lives at
`REV_B/10_scripts/b11_source_check.py` and writes into REV_B.

## 10. Renders

`thumb_inner_housing_lab/REV_B/08_renders/`

```text
01_frozen_exterior_with_axes.png     exterior + all 9 TRUE control axes
02_section_JOY.png                   axis section, exact STEP vs LOWER15
03_section_T2.png                    axis section, sealed in the exact STEP
04_section_T7.png                    axis section, 2.981 mm wall in the exact STEP
05_section_T4.png                    axis section, partially open (0.358 mm)
06_c01_thin_wall_heatmap.png         every column below 1.20 mm
07_c01_shell_gap_heatmap.png         gap bands
```
