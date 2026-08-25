# REV_K — C08 local conformal switch receiver

Date 2026-08-26 · local build123d / OCCT · Onshape API 0 · production writes 0
C07, Codex C07.1, docs/101 and REV_A…REV_J: **not modified**. All writes are inside
`thumb_inner_housing_lab/REV_K_C08_LOCAL_CONFORMAL_RECEIVER/`.

---

## 1. Two-button feasibility gate

```text
TWO-BUTTON FEASIBILITY = PASS   (28 gates, 28 PASS / 0 FAIL)
```

### Case selection (§8), from measurement not intuition

`k01_site_survey.py` measured, per button, the shell inner surface at five radii,
the transition length to the flat seat, and the room to the nearest Finger
switch, Thumb neighbour and SZH part.

| | button | room score | why |
|---|---|---:|---|
| **CASE EASY** | **T2** | 10.891 mm | most room of all eight; nearest Finger I4 at 28.874 mm, nearest Thumb T6 at 10.891 mm, SZH static 11.005 mm |
| **CASE HARD** | **T8** | 8.735 mm | least room of all eight, and the binding constraint is the **SZH static package at 8.735 mm**; it also sits nearest JOY, and its provisional SZH moving-envelope distance is 1.102 mm |

The survey also produced the number that justifies the whole architecture:

```text
transition, shell inner surface (r 5.6) -> flat seat = 3.886 to 4.747 mm, mean 4.252
```

That is the entire C08 load path. C07 carries the same load through a remote slab.

### Gate results

Both receivers: **1 valid solid, 39 faces, ~700 mm³**, landing width 3.400 mm.

| gate | T2 (EASY) | T8 (HARD) |
|---|---|---|
| frozen centre / press axis | 0.0000 mm / 0.0000° | 0.0000 mm / 0.0000° |
| switch bearing area | 23.79 mm² (65.2 %) | 23.79 mm² (65.2 %) |
| terminal escape | 2 of 2 slots, 35.612 mm free | 2 of 2 slots, 11.837 mm free |
| cap protrusion preserved | column blocked 0.0000 mm | column blocked 0.0000 mm |
| shell unintended penetration | 0.000000 mm³ | 0.000000 mm³ |
| docs/101 Finger interference | 0.000000 mm³, nearest 23.994 mm | 0.000000 mm³, nearest 19.060 mm |
| N1 / N2 clearance | 26.445 / 26.103 mm | 19.060 / 19.347 mm |
| SZH **static** interference | 0.000000 mm³ | 0.000000 mm³ |
| SZH **provisional moving** | 0.0000 mm³ *(reported only)* | 238.4462 mm³ *(reported only)* |
| switch installable down its bore | 0.0000 mm³ | 0.0000 mm³ |
| FDM, JOY_AXIS_UP | support 111.4 mm² (12.2 %) | support 58.6 mm² (6.5 %) |
| structural thickness (interior) | p2 2.339 mm, **0.0 %** below 1.20 | p2 2.176 mm, **0.0 %** below 1.20 |

Per §18 the provisional moving-envelope overlap on T8 is reported and was **not**
used to condemn the receiver.

### Two real findings the gate caught

1. **The terminal slots were 90° out.** `i02.frame(w)` and `h01.axis_frame(w)`
   differ by **90.0592°** about the press axis, and the whole REV_H/REV_I slot
   convention is written in `axis_frame`. Building the slots in the other frame
   put them across the seat instead of along it — "0 of 2 slots open" on both
   buttons. Genuine geometry defect, fixed.
2. **The thickness gate was reading clipped edges.** A column along the press
   axis clips the tapered collar at its outer rim. Interior-only columns give
   p2 = 2.18–2.34 mm with **0.0 %** below 1.20 mm; the raw figure including rim
   columns was 14.3–14.6 %. Metric defect, fixed.

## 2. Full C08

`03_full_c08/C08_LOCAL_CONFORMAL_SWITCH_RECEIVER_CORE.{step,stl}`

| metric | value |
|---|---|
| volume / faces | 4760.87 mm³ / 315 |
| solids | 1 (`valid` True as built; see §5) |
| receivers | 8, each an independent local collar |
| natural fusion | **T1–T6 fuse on their own**, no material added |
| ribs added | **2** (T6–T8, T4–T7) — §16 outcome **B** |
| collar half-size | 5.35 mm, landing width 2.15 mm |

The collar half-size is derived, not chosen: at 10.30 mm neighbour spacing,
5.35 makes neighbours overlap 0.40 mm so they fuse without a tangent union,
while a neighbour still clears this button's cap column by 0.75 mm, its pocket by
1.75 mm and its slot edge by 1.70 mm.

### Validation, 10 PASS / 4 FAIL

| check | result |
|---|---|
| shell unintended penetration | **JaD 0.000000, JfD 0.000000 mm³** |
| all eight seats bear | **8/8**, min 23.79 mm² (65.2 %) |
| terminal escape depth | worst 11.837 mm against 3.654 needed |
| minimum structural thickness | 0.44 mm² below 1.20 mm |
| **docs/101 Finger interference** | **0.000000 mm³ on all 8** |
| JOY column unobstructed | 0.0000 mm of C08 on the JOY axis |
| SZH static package | **0.000000 mm³** over 8 confident-static parts |
| C07 joystick deck carried over | **0.000000 mm³** against the 2954.7 mm³ deck slice |
| Finger switch corridors | none blocked — Finger switches can still go in first |
| single valid solid | **FAIL** — `valid=False` on STEP reimport |
| all sixteen terminal slots open | **FAIL** as gated — but see §5 |
| switches installable down their bores | **FAIL** — 341.4467 mm³ |
| core placeable into an open half | **FAIL** — no clear path |

### Per-Finger table (§19)

| Finger | C08 ↔ pocket | C08 ↔ switch | minimum clearance |
|---|---:|---:|---:|
| N1 | 0.0000 | 0.0000 | **18.8996** |
| N2 | 0.0000 | 0.0000 | 19.3361 |
| I2 | 0.0000 | 0.0000 | 20.6929 |
| I3 | 0.0000 | 0.0000 | 23.3031 |
| I4 | 0.0000 | 0.0000 | 23.2462 |
| M3 | 0.0000 | 0.0000 | 26.1366 |
| M4 | 0.0000 | 0.0000 | 25.9431 |
| N3 | 0.0000 | 0.0000 | 20.9740 |

**C08 improves the docs/101 margin dramatically: the tightest Finger clearance
goes from C07's 0.5217 mm to 18.8996 mm**, because the receivers stay next to
their own openings instead of reaching across the cavity.

## 3. C07 vs C08 (§22)

| Metric | C07 | C08 |
|---|---:|---:|
| T1–T8 functional seats | 8 / 8 | 8 / 8 |
| terminal openings | 16 / 16 | 16 / 16 *(99 %+ open, see §5)* |
| shell collision | 0.000000 mm³ | 0.000000 mm³ |
| docs/101 collision | 0.000000 mm³ | 0.000000 mm³ |
| **N1 minimum clearance** | 0.5217 mm | **18.8996 mm** |
| JOY package compatibility | integrated deck | deck carried over, 0.000000 mm³ |
| minimum structural thickness | 0.00 mm² below 1.20 | 0.44 mm² below 1.20 |
| support-required area | **812.6 mm² (11.5 %)** | 1000.8 mm² (16.2 %) |
| trapped support | 0 | 0 |
| **total volume** | 7378.02 mm³ | **4760.87 mm³ (−35.5 %)** |
| B-rep faces | 333 | 315 |
| **major structural members** | 1 slab + 16 bridges + 1 deck + 5 walls + 3 pads = **26** | 8 receivers + 2 ribs = **10** |
| hand-finish burden | slab underside support, deck rim, pads | collar rims, slot slivers |
| **load-path complexity** | seat → slab → wall → deck → standoff → shell (6) | **seat → short collar → conformal landing → shell (4)** |
| **removable as one piece** | **+U out of JfD = 0.0 mm³** | **no clear path; best 505.2 mm³** |

## 4. The decisive finding — conformal landings interlock

| sweep, 25 mm | C07 | C08 |
|---|---:|---:|
| +U vs JfD | **0.0** | 505.2 |
| −U vs JaD | **0.0** | 190.4 |
| −JOY (inward, off the shell) | 7433 / 8231 | 963 / 2042 |
| +JOY (outward) | 7044 / 8351 | 2899 / 3867 |

C07 lifts cleanly out of either open half. **C08 does not — every direction is
blocked.** This is the direct consequence of the architecture working as
intended: each collar is pressed into its own patch of local shell curvature, so
the eight of them fused into one body form a shape that cannot be slid out along
any single direction. Individually the receivers install fine (0.0000 mm³ down
each bore); collectively they interlock.

That is an architectural consequence, not a modelling defect, and it is the
single most important result of this experiment.

## 5. Residual issues, honestly separated

| issue | measurement | status |
|---|---|---|
| **cannot be assembled as one piece** | best path 505.2 mm³ over 25 mm | **real, architectural** |
| terminal slot residue | exact boolean: **0.0196–0.2679 mm³** of a 21.6 mm³ slot, i.e. 0.1–1.2 % | real but minor; the "12 of 16" gate reading is **noise** — T1 at 0.0202 mm³ was called closed while T2 at 0.0196 mm³ was called open |
| `valid=False` on reimport | k04 reports `valid True` as built, k05 reports `False` after the STEP round trip | unexplained; flagged, not diagnosed |
| switch insertion 341.4467 mm³ | across all eight, 12 mm sweep | not root-caused |
| support 16.2 % vs C07's 11.5 % | 1000.8 vs 812.6 mm² | real, C08 is worse |

The two-button gate is unaffected by any of these: each receiver on its own is a
clean single valid solid that passes all 14 checks.

## 6. Renders (§23)

```text
1  EASY T2 receiver in place        6  transparent shell with the full core
2  EASY T2 section on its axis      7  joystick coordination
3  HARD T8 receiver in place        8  docs/101 Finger interface
4  HARD T8 section on its axis      9  underside, print orientation
5  all eight receivers             10a/10b C07 vs C08, same camera
```

## 7. Verdict

```text
TWO-BUTTON FEASIBILITY = PASS

B — C08 WORKS BUT DOES NOT CLEARLY IMPROVE ON C07
```

The architecture is sound and in several ways better: the load path drops from
six steps to four and from a remote slab to a 4.25 mm local collar, volume falls
35.5 %, major members fall from 26 to 10, and the tightest docs/101 Finger
clearance improves by a factor of 36 (0.52 → 18.90 mm). Every static integration
number is zero, and the HARD case — the button hemmed in by the SZH package —
passed every gate.

It is **not** a clear improvement because the assembled eight-receiver body
**cannot currently be installed or removed as one piece**, where C07 can, and it
needs more support area, not less. Those are integration-level problems, not
conceptual ones, but they are exactly the criteria §21 says must decide this.

Not **A**, because §21 forbids declaring success on geometric function alone.
Not **C**, because nothing about the local conformal receiver concept failed —
the gate passed 28/28 including the hardest button.

**The obvious next question, not acted on here:** whether relaxing the landing's
conformity slightly, or splitting C08 into two or three sub-assemblies that each
install along their own axes, removes the interlock while keeping the short load
path. That is a geometry change and §26 says stop.

---

No production apply. C07 and Codex C07.1 untouched. docs/101 untouched. Finger
geometry untouched. No frozen external control geometry changed.
