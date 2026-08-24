# REV_C — approved Thumb exterior → exact B-rep reconciliation

Date 2026-08-24 · local build123d / OCCT · Onshape API 0 · production writes 0
REV_A and REV_B untouched. C01 read-only. Everything here is LAB geometry.

---

## 1. Authority used

| role | source | quality |
|---|---|---|
| outer skin / silhouette | `JAD/JFD_EXTERIOR_LOWERED_THUMB_V1.step` | exact B-rep |
| control position / axis | frozen cartridge `LOWERED_ORIGINAL_THUMB_CARTRIDGE.step` | exact B-rep |
| opening topology | `THUMB_LOWER15_HOUSING_V1` STL | **NON-EXACT / MESH ONLY** |
| opening construction rule | original OneGrip `#button_tolerance = 0.20 mm` | documented constant |

The LOWER15 mesh was never converted into geometry. It was measured, and every
cutter was then derived analytically from exact inputs. The one exception is the
joystick cross-section, marked **NON-EXACT-DERIVED** below.

---

## 2. The approved openings, measured (section 3)

Measured on each control's own TRUE press axis, 0.10 mm ray grid.

| ctrl | approved area mm² | surrounding wall mm | entry w | exit w | approved vs ORIGINAL opening |
|---|---:|---:|---:|---:|---:|
| JOY | 173.070 | 2.430 | 1.814 | 4.244 | 323.43 (different: split slot) |
| T1 | 47.830 | 1.916 | 2.858 | 4.780 | 47.460 |
| T2 | 64.000 | 3.028 | 4.844 | 7.873 | 64.000 |
| T3 | 47.860 | 1.916 | 2.781 | 4.702 | 47.300 |
| T4 | 62.490 | 2.326 | 4.455 | 6.781 | 61.600 |
| T5 | 63.200 | 2.965 | 2.941 | 5.906 | 64.000 |
| T6 | 61.970 | 2.191 | 4.543 | 6.734 | 62.400 |
| T7 | 67.450 | 2.326 | 6.155 | 8.485 | 68.730 |
| T8 | 68.080 | 2.548 | 6.078 | 8.626 | 68.290 |

For T1–T8 the approved lowered openings reproduce the ORIGINAL opening areas to
within 0.4–1.3 mm². The approved geometry is the original opening correctly
re-cut at the new location — which is exactly what the exact STEP failed to do.

---

## 3. Root cause (section 4)

Both cutter families were reconstructed exactly as the generator builds them and
measured against the wall they had to cut.

### Family 1 — translated original opening VOIDS

`opening_voids()` returns `defeature(shell, faces) − shell`: a **plug the
thickness of the wall at the ORIGINAL location**, ~3 mm. Translating it rigidly
by `(0, +12.25, −21)` does not make it deeper.

| ctrl | plug reach along the axis | wall inner at the new position | shortfall |
|---|---:|---:|---:|
| T1 | 0.686 | 2.437 | **+1.750** |
| T2 | 1.270 | 4.935 | **+3.664** |
| T3 | 0.641 | 2.306 | **+1.665** |
| T4 | 0.939 | 4.290 | **+3.352** |
| T5 | 1.163 | 3.120 | **+1.957** |
| T6 | 0.868 | 4.184 | **+3.316** |

The plug stops 1.67–3.66 mm short of the wall. **It cuts nothing.**

### Family 2 — world-axis AABB service boxes

`thumb_user_side_service_box(cap, 0.80)` = the **world-axis AABB of the CAP**
grown 0.80 mm, clipped to the seat slab. Two independent defects:

* it is sized to the CAP, and the cap does not reach the wall;
* its outward face is a **world-axis plane**, not parallel to the wall, so where
  it does bite it shears the wall at an angle and leaves a skin.

The slab is not the limiter: it spans local n = −7.525 … +16.107, past the outer
skin.

**The proof is numerical.** The residual wall left in the frozen STEP begins at
exactly the AABB tool's reach along the control axis:

| ctrl | AABB reach on the axis ray | FROZEN residual wall interval | residual |
|---|---:|---|---:|
| T2 | **6.706** | **[6.706, 7.932]** | 1.227 |
| T4 | **6.982** | **[6.982, 7.340]** | 0.358 |
| T6 | **6.968** | **[6.968, 7.245]** | 0.277 |
| T7 | 5.894 | [5.991, 8.972] | 2.981 |
| T8 | 5.906 | [5.965, 8.952] | 2.987 |

Identical to three decimals for T2/T4/T6. The cutter cut up to its own outward
face and everything beyond it survived.

### T7 / T8 — an additional mechanism

At their lowered positions the ORIGINAL T1/T3 openings sit ~2 mm away, so CLEAN
is already open there. `restore_original_thumb_openings()` **filled** those old
openings, creating fresh 3 mm wall exactly where the new opening was needed —
and then the AABB reach (5.894 / 5.906) stopped 0.10 mm short of the new wall
inner face (5.991 / 5.965). Result: a full 2.98 mm wall, 0 % open.

```text
WHY LOWER15 WORKS   : the CAD re-cut the opening at the new position, normal to
                      the local surface, through the full wall
WHY THE EXACT STEP FAILS : it translated a wall-thickness plug and cut with a
                      world-axis box sized to the cap, neither of which reaches
                      a curved wall that is 1.7-3.7 mm further out
```

---

## 4. The reconciled reference (section 5)

`03_reconciled/FROZEN_THUMB_EXTERIOR_RECONCILED_REFERENCE.step` (+ JAD/JFD halves)

Built by starting from the exact frozen STEP — whose outer skin is already the
approved surface — and removing **only** the material the approved openings
require. Cutting cannot change the surface outside the cut, so 5A holds by
construction and is verified independently in section 6.

Cutter per control:

* cross-section = convex hull of the cap's **user-facing face**, parallel-offset
  by `#button_tolerance = 0.20 mm` (exact B-rep inputs)
* direction = the frozen TRUE press axis (unchanged)
* depth = cap face − 0.50 mm to cap face + 14.0 mm
* JOY = circle of the approved area, **NON-EXACT-DERIVED from the LOWER15 mesh**
  (the knob is a cone + sphere and has no planar user face)

Cutter cross-section vs approved area: T2 **0.00 %**, JOY −0.29 %, T5 +1.27 %,
T4 +2.89 %, T8 +3.02 %, T6 +3.75 %, T7 +3.98 %, T3 +5.71 %, T1 +5.81 %.

Removed: JAD 445.102 mm³, JFD 449.288 mm³. Each half stayed a single solid.

*Correction made during the build:* the first cutter hulled the whole cap
silhouette instead of its user-facing face, which inflated T1/T3 by 16 % and
T4/T6/T7/T8 by 7–9 % on wedged caps. Corrected before the shell was cut.

---

## 5. Opening validation (section 6)

| ctrl | through | recon mm² | approved mm² | excess | deficit | coverage | ligament mm |
|---|---|---:|---:|---:|---:|---:|---:|
| JOY | **YES** | 195.28 | 173.09 | 29.70 | 7.51 | 95.7 % | 0.800 |
| T1 | **YES** | 65.70 | 47.88 | 18.60 | 0.78 | 98.4 % | **0.283** |
| T2 | **YES** | 64.00 | 64.00 | 3.17 | 3.17 | 95.0 % | 3.400 |
| T3 | **YES** | 67.10 | 47.85 | 20.81 | 1.56 | 96.7 % | 2.000 |
| T4 | **YES** | 64.88 | 62.49 | 3.05 | 0.66 | 98.9 % | 3.400 |
| T5 | **YES** | 67.40 | 63.20 | 5.73 | 1.53 | 97.6 % | 2.000 |
| T6 | **YES** | 65.35 | 61.97 | 7.53 | 4.15 | 93.3 % | 3.400 |
| T7 | **YES** | 70.00 | 67.42 | 4.07 | 1.49 | 97.8 % | 5.200 |
| T8 | **YES** | 70.00 | 68.08 | 5.49 | 3.57 | 94.8 % | 5.200 |

Axis angular error **0.000°** for all nine (the cutters use the frozen axes).
Centroid error 0.13–1.29 mm.

### Where the excess comes from

| | total | JOY | T1 | T3 | T5 | others |
|---|---:|---:|---:|---:|---:|---:|
| excess | 97.43 | 29.73 | 18.64 | 20.79 | 5.73 | 22.54 |
| **inherited from the frozen STEP's own over-cut** | **53.86** | 14.56 | 16.80 | 19.10 | 3.40 | 0 |
| added by the reconciled cutter | 43.57 | 15.17 | 1.84 | 1.69 | 2.33 | 22.54 |

**55.3 % of the excess is inherited.** At JOY/T1/T3/T5 the frozen STEP's AABB
tool already removed material outside the approved opening, and cutting cannot
put it back. This is the hard limit of reconciliation-by-cutting.

---

## 6. Surface preservation (section 7)

Ray sampling outside 8 mm control neighbourhoods gave median 0.000000000 mm,
p95 0.0125 mm, max 0.1826 mm — but that compares two **independent
tessellations**, so the maximum is chord error, not geometry change. It is not
used as the proof.

Exact proof, by point membership on a 0.5 mm grid:

```text
cells inside RECONCILED           208,395   ( 26,049.375 mm3 )
cells inside FROZEN               215,132   ( 26,891.500 mm3 )
cells in RECONCILED not FROZEN        331   (     41.375 mm3 )
   surviving a 3x3x3 erosion            0
   connected components               238, largest 9 cells
cells in FROZEN not RECONCILED      7,068   (    883.500 mm3 )
exact volume change                        -886.114 mm3   (pure decrease)
```

No flagged cell survives erosion and the largest cluster is 9 voxels, so all 331
are 0.5 mm cells straddling a surface. **No material was added anywhere; the
outer skin is unchanged.**

---

## 7. docs/71 shell-sensitive rerun (section 8) — docs/71 NOT modified

| SZH feature | FINGER_V2 (docs/71 used this) | old exact FROZEN | RECONCILED |
|---|---:|---:|---:|
| PCB | 181.1341 | 181.1338 | **181.1338** |
| shaft | 11.8275 | 0.0000 | **0.0000** |
| removable knob | 422.1701 | 44.7960 | **32.1251** |
| header plastic | 73.3779 | 73.3779 | **73.3779** |
| 25° moving envelope | 2072.2183 | 1839.5688 | **1826.8814** |
| gimbal / x-pot / y-pot / push switch | 0 | 0 | **0** |

The correct exterior removes the shaft collision entirely and cuts the knob
collision by 92 %. PCB and header are unchanged — they contend with the deep
cavity, not the Thumb face, so those docs/71 rows stand, as do all its N1/N2
rows. **SZH remains PROVISIONAL / MEASURE ON ARRIVAL.**

---

## 8. Existing C01 against the reconciled shell (section 9)

| metric | vs old FROZEN | vs RECONCILED |
|---|---:|---:|
| interference | 0.000000 mm³ | **0.000000 mm³** |
| gap median | +1.199 mm | **+1.199 mm** |
| gap min | +0.142 mm | +0.142 mm |
| C01 material inside each reconciled opening prism | — | **0.0000 mm³ for all nine** |

**C01's design was not influenced by the bad openings.** It was derived from the
wall's *inner* surface plus its own axis-swept apertures; the defect was in the
*outer* part of the wall. C01 blocks none of the corrected openings.

C01R was therefore created for the two reasons REV_B already identified, not
because of the shell correction.

---

## 9. C01R (sections 10–12)

`07_c01r/C01R_RECONCILED_SOURCE_FAITHFUL.step` / `.stl`

| metric | ORIGINAL | C01 | **C01R** |
|---|---:|---:|---:|
| solids | 1 | 1 | **1** |
| volume mm³ | 5899.53 | 3375.46 | **3087.94** |
| plan area mm² | ~1580 | 1503.19 | **1298.56** |
| interference with its shell | ~0 | 0.000000 | **0.200215** |
| area below 1.20 mm | — | 100.12 mm² | **21.81 mm²** |
| interior (non-edge) thin area | — | 0.00 mm² | **0.00 mm²** |
| gap ≤ 0.30 mm | **6.39 %** | 0.59 % | **3.52 %** |
| intentional load transfer | 96.25 mm² in 2 zones | none | **38.00 mm² in 2 pads** |

Gap bands: <0.20 → 37.56 mm² (2.9 %) · 0.20–0.40 → 9.19 · 0.40–0.80 → 0.44 ·
0.80–1.20 → 816.44 (62.9 %) · ≥1.20 → 434.94 (33.5 %).

Every low-gap zone is classified:

| zone | area mm² | min gap | class |
|---|---:|---:|---|
| u[−8.00, 0.25] v[−38.25, −28.75] | 28.44 | 0.106 | **INTENTIONAL LOAD TRANSFER** |
| u[5.00, 10.25] v[−37.00, −32.50] | 9.56 | 0.105 | **INTENTIONAL LOAD TRANSFER** |
| five slivers at u = ±20.0…20.75 | 8.25 total | 0.249 | ASSEMBLY CLEARANCE |

Pads use a designed 0.10 mm standoff, achieved 0.105–0.123 mm. No zero-clearance
fit, no broad friction fit, no contact nib.

**Documented deviation:** the original contact zones are at u[−20,−11.5]
v[−49,−32] and u[12.5,19] v[−49,−44] — the plate *perimeter*. C01R's trimmed
plan does not reach there (the right side ends at v ≈ −37), so the pads were
snapped to the nearest valid interior positions, **13.68 mm and 14.21 mm** from
the original centroids. They react the T1/T3/T5 press load, but they are not the
original perimeter load path. This is a real difference from the original design
and is left for user review.

Build defects found and fixed during C01R:
1. building the conformal band from the *reconciled* shell silently failed at the
   plate edges — `shifted(gap+t) − shifted(gap)` returned the first operand, so
   the plate came out 3.29 mm thick at a 0.30 mm gap instead of 2.40 at 1.20.
   Rebuilt from the frozen shell, where the same construction is well conditioned.
2. pads at the original centroids landed on nothing (0 mm³) — snapped as above.
3. the pad band overshot into the wall by 7.067 mm³; guarded by subtracting the
   shell shifted in ±u, ±v and n, bringing interference to 0.200 mm³.
4. two 0.06 / 0.003 mm³ trim chips dropped.

Residual 0.200 mm³ of interference is spread over 38 mm² of pad (≈0.005 mm mean),
below both the FDM resolution and the 0.05 mm tessellation tolerance used to
measure it. It is reported, not hidden.

---

## 10. Verdict

```text
RECONCILIATION PARTIAL — SPECIFIC OPENING STILL UNRESOLVED
```

All nine approved openings are now full through-openings in an exact B-rep, the
outer skin is provably unchanged, and no HARD FREEZE item was touched. What is
unresolved is **T1** (and to a lesser degree T3 and JOY):

* the frozen STEP's own AABB over-cut removed 16.80 mm² outside the approved T1
  opening, and cutting cannot restore it;
* as a result the T1 opening is 37 % larger than approved and its minimum
  surrounding ligament is **0.283 mm**, against 2.0–5.2 mm everywhere else.

That ligament is too thin to print or to carry a cap edge. Fixing it needs
material *added* back to the frozen STEP, which is outside what this Lab is
allowed to do and outside what "reconciliation by cutting" can achieve.

---

## 11. Renders

`thumb_inner_housing_lab/REV_C/08_renders/`

```text
01_APPROVED_LOWER15.png          matched camera
02_OLD_EXACT_FROZEN_STEP.png     matched camera
03_RECONCILED_REFERENCE.png      matched camera
04_section_JOY.png               axis section, all three walls overlaid
05_section_T2.png
06_section_T4.png
07_section_T6.png
08_section_T7.png
09_section_T8.png
10_housing_ORIGINAL.png          same section plane
11_housing_C01.png               same section plane
12_housing_C01R.png              same section plane
```
