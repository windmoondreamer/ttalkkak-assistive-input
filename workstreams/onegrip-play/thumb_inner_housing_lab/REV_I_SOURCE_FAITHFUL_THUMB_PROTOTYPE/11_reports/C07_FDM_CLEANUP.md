# C07 — C06 rebuilt for FDM manufacturability

Date 2026-08-25 · local build123d / OCCT · Onshape API 0 · production writes 0
Shell authority unchanged and re-verified. JOY / T1–T8 / N1 / N2 / exterior: **HARD FREEZE, not moved.**

Builder `i10_c07_refine.py` · orientation audit `i11_print_orientation_audit.py`
· validation `i08_validate.py --cand C07…` · thin map `i08b_thin_locator.py`

Exports
```text
07_prototype/C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step
07_prototype/C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.stl
```

---

## 1. Print orientation, chosen before the geometry

```text
PRINT_UP = the JOY axis, outward = (0.000182, 0.598493, 0.801128)
BED      = perpendicular to it, at the joystick deck underside
```

The JOY axis turns out to be exactly the Thumb datum normal, and the eight seat
planes lie only **1.84–9.38°** off it. So in this orientation every bearing face
and every terminal-slot wall points up or runs vertical, and the slab underside
becomes one flat plane instead of eight tilted tiles.

Four orientations were measured on the finished C07, not assumed:

| orientation | height | bed contact | support | support % | trapped | on critical faces |
|---|---:|---:|---:|---:|---:|---:|
| **JOY_AXIS_UP (chosen)** | **22.89** | **977.4 mm²** | **812.6 mm²** | **11.5 %** | **0** | **0** |
| JOY_AXIS_DOWN (flipped) | 22.89 | 22.8 | 1776.0 | 25.1 % | 1 | **128** |
| THUMB_NORMAL_UP | 22.89 | 977.4 | 812.6 | 11.5 % | 0 | 0 |
| IN_PLANE (on edge) | 60.79 | 30.3 | 657.1 | 9.3 % | 0 | 2 |

`IN_PLANE` is the only rival on raw support area — 657 vs 813 mm², a 19 % saving.
It is rejected anyway: 30.3 mm² of bed contact under a **60.8 mm** tall part is a
tipping risk, the seat bearing faces end up near-vertical so the press load would
cross layer lines, and it still puts support on 2 critical faces. Chosen
orientation wins on every measure that cannot be recovered after printing.

**Press-load direction:** the press axes sit 1.84–9.38° off PRINT_UP, so a button
press is carried as compression **through** the layers, never as interlayer
tension. The slab lies in the layer plane, so its bending stress is in-plane.

## 2. What changed, and why each change was necessary

| C06 feature | why it was bad for FDM | C07 replacement |
|---|---|---|
| eight 9 × 9 mm plate tiles, each tilted 0–9.4° to its neighbour | union of tilted planes leaves feather edges — 27.36 mm², thinnest **0.319 mm**, well under a 0.4 mm nozzle | **one slab**: flat bottom ⟂ PRINT_UP, top faceted onto the eight seat planes, so every step between seats is a vertical face |
| 20 tilted webs | wedge ends, inconsistent thickness | **16 bridges** in the same prism, 5.6 mm wide, capped 0.60 mm below the lower neighbour |
| 5 inclined links to the deck | undersides at 58° overhang | **5 vertical walls**, 2.6 mm, faces parallel to PRINT_UP → self-supporting from the bed |
| 4 × 4 mm square standoff pads | vertical cliffs off the slab; one pad hung 5.25 mm **below** the deck and stole the first layer | **chamfered pads**, 5.0 mm with a 1.2 mm 45° skirt, and both ends constrained above the bed |
| nominal 2.003 mm plate | feathered to 0.32 mm at every joint | **2.60 mm minimum**, 7.19 mm at the highest seat; p25/p50/p75 = **3.000 / 3.000 / 4.792** |
| deck 2.5 mm, aperture Ø12 | thin for a part that carries the joystick | **3.0 mm**, cavity-shaped r 13.61–24.81, aperture Ø12 for solder tails |

## 3. C06 → C07

| metric | C06 | C07 |
|---|---:|---:|
| validation gates | 26 PASS / **1 FAIL** | **27 PASS / 0 FAIL** |
| interior area below 1.20 mm | **27.36 mm²** | **0.00 mm²** |
| thinnest interior column | 0.319 mm | none below 1.20 |
| thickness p25 / p50 / p75 | 2.500 / 2.500 / 3.183 | **3.000 / 3.000 / 4.792** |
| B-rep faces | 542 | **333** |
| bed contact in the print orientation | 0.0 mm² | **977.4 mm²** |
| support area | 1905.4 mm² (31.1 %) | **812.6 mm² (11.5 %)** |
| support regions | 250 | **151** |
| support on switch / joystick interfaces | **12 faces** | **0** |
| trapped support | 0 | 0 |
| dropped fragments during build | yes | **none** |
| volume | 5285.5 mm³ | 7378.0 mm³ |

The volume rise is deliberate: the slab is thicker everywhere and the tilted-tile
voids are gone. On FDM this is largely infill, not solid material.

## 4. Everything functional is preserved

| gate | result |
|---|---|
| all eight seats bear | **23.79 mm² = 65.2 %** of the 6.04 × 6.04 footprint, identical on all eight |
| terminal slots | **16 of 16** open, at the original 1.30 × 6.40 mm / ±2.60 mm |
| T7 / T8 retained | 23.79 / 23.79 mm² (REV_H had 0.00 / 0.00) |
| terminal escape | worst free depth 11.837 mm against 3.654 mm needed |
| cap protrusion | restored to 1.066–1.459 mm, the original law |
| press travel | 1.07 mm of sink before the cap top reaches the skin, against 0.25 mm of travel |
| switch bodies and actuators clear of the core | **0.0000 mm³** |
| switches installable | 0.000 mm³ obstruction withdrawing 12 mm out of the bore |
| joystick deck | 23.993 mm below the skin, module bears on it as the HW504 did |
| knob height | +7.607 mm target, 10.239 mm of adapter reach |
| shell interference | **0.000000 mm³** |
| load path | min gap **0.162 mm**, 8.41 % of the core surface within 1.0 mm, 3 standoffs |
| single coherent solid | 1 solid, BRep valid, no floating debris |

Keep-outs, still reported and not cut where provisional (§13):

```text
CONFIDENT STATIC                       0.0000 mm3
N1 / N2 EXTERNAL SUBSYSTEM             0.0000 mm3   (4.41 mm3 relieved in CAD)
PROVISIONAL STATIC   SZH_pcb          56.2517 mm3   reported, not cut
REMOVABLE HARDWARE   SZH_header       18.3030 mm3   CLASS C
PROVISIONAL MOVING ENVELOPE         2562.1050 mm3   reported, NOT subtracted
```

## 5. Support strategy

812.6 mm² over 151 regions, **0 trapped**, max height 16.62 mm. Every region
carries an accessibility score from 16 horizontal probe bearings; the three
largest are 243.2 mm² (11/16 clear), 160.4 mm² (7/16) and 124.7 mm² (16/16).

All of it lands on the **slab underside** — a flat, non-critical, outward-facing
surface in the assembled part. Nothing lands on a bearing face, a slot wall, the
deck top or a pad contact face. The slab overhangs the vertical walls the way a
table top overhangs its legs, and that overhang is open on every side.

## 6. Renders

```text
11a  C06 before the rebuild        11b  C07 after, same camera
12   C07 in the print orientation, bed marked
13   C07 sectioned along the seat row, slab thickness visible
14   C07 with switches, caps and joystick installed
```

## 7. Errors found and fixed during the rebuild

Four were ordering mistakes of the same kind, and are worth stating as one rule.

1. **Clearances ran before the additive stages.** The first C07 cut the switch
   and cap relief and the terminal slots at stage 3–4, then added walls, pads and
   keep-out relief. The later additions put **26.06 mm³** back inside switch
   bodies and re-covered one of T2's slots (15 of 16). Moved to the end.
2. **Keep-out relief ran before the standoff pads.** Same failure: the pads put
   **26.55 mm³** straight back into the N1/N2 keep-out. Moved after the pads.
3. **A standoff pad hung 5.25 mm below the deck.** Filtering only the pad's
   contact point was not enough — a downward-pointing pad reaches further at its
   far end. Now both ends are constrained above the bed. This is what made bed
   contact read **0.0 mm²** on a part with a flat 1100 mm² underside.
4. **The orientation audit measured its own artefacts.** Bed faces were
   classified by triangle centroid, so one low pad disqualified the real bed
   face; and support regions were clustered by centroid, so a flat 85 mm²
   underside made of two big triangles reported `span 0.00 mm`. Fixed by
   requiring the whole triangle in the first-layer band and by rasterising
   triangle **area** with barycentric samples.

**Rule:** in a boolean build, every stage that ADDS material must run before
every stage that guarantees clearance. Three separate defects in this session
came from breaking that order.

## 8. Verdict

```text
C07 FDM CLEANUP PASSED — READY FOR SLICER / PRINT REVIEW
```

One valid solid, no floating debris, no sliver below 1.20 mm anywhere in the
interior, no knife-edge termination, no tangent-only structural contact, every
side wall self-supporting, 977 mm² of flat bed contact, 11.5 % support with zero
trapped regions and zero support on a switch or joystick interface — while all
27 functional gates still pass and every source-faithful dimension is unchanged.

**Carried forward, unchanged from the REV_I report and not a printability issue:**
the SZH PCB outline against the cavity remains CLASS A and blocked on measuring
the received SZH-EK056, and the N1/N2 adjacency is marked
**REVALIDATE AFTER FINGER FREEZE** — that subsystem was still being edited by the
concurrent workflow during this session.

No production apply, no Onshape write, no exterior change, no HARD FREEZE change.
