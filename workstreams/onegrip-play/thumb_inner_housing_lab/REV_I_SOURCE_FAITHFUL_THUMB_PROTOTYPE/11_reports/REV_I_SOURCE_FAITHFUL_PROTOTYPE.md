# REV_I — source-faithful Thumb prototype

Date 2026-08-25 · local build123d / OCCT · Onshape API 0 · production writes 0
Shell authority: exact Onshape `THUMB_LOWER15_HOUSING_V1`, hashes re-verified against
the REV_D baseline (`622ADB3B…`, `D75F62E0…`). REV_A…REV_H untouched, 279 files hashed.

JOY / T1–T8 / N1 / N2 / exterior: **HARD FREEZE, not moved.**

Companion documents: `PREVIOUS_WORK_REUSE_MAP.md` (§24),
`ORIGINAL_THUMB_ARCHITECTURE_SPEC.md` (§25), `HAND_FINISH_MAP.md` (§30).

---

## 1. The finding that drove the revision

REV_H measured only what happens inside the shell. Measuring the **external**
stack (§5) changed the whole picture:

```text
ORIGINAL caps protrude   +1.066 .. +1.459 mm above the local skin   (mean 1.264)
INHERITED caps sit       -4.116 .. -7.179 mm BELOW it               (deficit 5.58-8.38)
ORIGINAL knob top        +7.607 mm
INHERITED knob top       -1.732 mm                                  (deficit 9.34)
```

The inherited caps are the original caps rigidly translated by `THUMB_DELTA`,
whose −9.49 mm component along the surface normal took them below a skin that was
never re-lofted. **Nothing frozen is wrong — the caps were simply never
re-derived.** A button recessed 4–7 mm inside a hole cannot be pressed, so the
inherited cap position could not be the datum for the seat.

§9 says the CAP / SWITCH stack controls seat depth and the original protrusion is
a functional requirement. So each cap was slid **along its own frozen press axis**
— which changes nothing that is frozen — until its top reached the original law.

```text
axial shift outward   5.573 .. 8.378 mm      (mean 6.869)
seat plane moves from  14.158-16.639 mm below the skin   (REV_H)
                to      8.261- 8.585 mm below the skin   (REV_I)
```

**That single change fixed both of REV_H's open problems at once.**

| REV_H problem | REV_H | REV_I |
|---|---:|---:|
| T7 / T8 seat bearing area | **0.00 / 0.00 mm²** | **23.79 / 23.79 mm²** |
| T7 / T8 vs the SZH 25° moving envelope | 229.08 / 242.08 mm³ | **0.0000 / 0.0000 mm³** |
| T7 / T8 terminal depth (3.654 needed) | 3.465 — 0.189 short | **11.84 mm** |
| carrier-to-shell minimum gap | 7.630 mm | **0.240 mm** |
| carrier area within 3 mm of the shell | 0.00 mm² | 9.50 % of the core surface within **1.0 mm** |

The seats were never in the joystick's way. They were 8 mm too deep.

## 2. The original architecture (§3, §25)

One conformal ~2.0 mm plate carries everything. No boss, no shoulder, no recess.

```text
BUTTON CAP -> ACTUATOR -> SWITCH BODY -> FLAT 2.003 mm PLATE -> SLOTS -> CAVITY
JOYSTICK KNOB -> SHAFT -> HW504 MODULE -> the same plate, 0.011 mm contact
```

Controlling numbers: cap underside → plate top **4.759 mm**; bearing **6.02 × 6.04 mm**
flat; two **1.30 × 6.40 mm** slots at **±2.60 mm**; knob top **+7.607 mm**, standing
**6.556 mm** above the tallest cap; plate-to-shell contact band **6.39 %** of area.

That last number matters for §21: the original did not rely on continuous contact.
It relied on a stiff plate with a few broad landings.

## 3. What was built

`07_prototype/C06_SOURCE_FAITHFUL_THUMB_CORE.step` / `.stl`

| metric | value |
|---|---|
| solids / valid | **1 / True** |
| volume / faces | 5285.473 mm³ / 542 |
| eight seat islands | 9.0 × 9.0 × 2.003 mm, on each restored plate plane |
| structural webs | 20 |
| joystick deck | cavity-shaped, r 13.6–24.8 mm, 2.5 mm thick, **23.993 mm below the skin** |
| deck links | 5 |
| terminal slots | **16 of 16** cut at the original 1.30 × 6.40 / ±2.60 |
| switch pocket relief | 172.007 mm³ |
| confident-static relief | 116.559 mm³ (original shell screw 2 only) |
| standoffs to the shell | 2 |
| interference with the exact shell | **0.000000 mm³** |

The joystick deck reproduces the original relationship — the module bottom bears
on the plate, exactly as the HW504 did — at 23.993 mm depth against the original
19.043 mm. **The SZH simply needs about 5 mm more depth than the HW504**, and §10
allows that as long as the external relationship is preserved, which it is: the
knob top target stays +7.607 mm, reached by a custom knob with 10.239 mm of
adapter travel over the provisional shaft.

## 4. Validation — 26 PASS / 1 FAIL (§29)

**Buttons** — all eight identical by construction:

| ctrl | bearing | of 6.04² | slots | protrusion | terminal free depth |
|---|---:|---:|---:|---:|---:|
| T1–T8 | **23.79 mm²** | **65.2 %** | **2** | 1.066–1.459 | 11.84–36.32 |

PASS: all eight bear · 16/16 slots open · **T7 and T8 retained** · terminal escape
(worst 11.84 vs 3.654 needed) · protrusion follows the original law · press travel
available · mechanism clear of the shell (0.0334 mm³) · bodies and actuators clear
of the core (**0.0000 mm³**).

**Joystick** — reported by class, nothing cut (§13):

```text
CONFIDENT STATIC                     0.0000 mm3   PASS
PROVISIONAL STATIC                   8.8920 mm3   SZH_pcb        reported, not cut
REMOVABLE HARDWARE                  19.2649 mm3   SZH_header     CLASS C
PROVISIONAL MOVING                   0.0000 mm3
PROVISIONAL MOVING ENVELOPE       1728.6636 mm3   reported, NOT subtracted
N1 / N2 EXTERNAL SUBSYSTEM           0.0000 mm3   REVALIDATE AFTER FINGER FREEZE
```

**Structure** — single valid solid, zero shell interference, one plan component,
2 standoffs, min gap 0.240 mm. **One gate fails**, below.

**Assembly** — switches installable down their own bore (0.000 mm³ obstruction
over 12 mm), caps drop into their frozen bores, joystick lifts out of the deck,
16/16 slots open into the cavity.

### The one failing gate

```text
FAIL  minimum thickness   interior area below 1.20 mm = 27.36 mm2
                          (plan 1795.0 mm2, so 1.5 % of it; p25/p50/p75 = 2.500/2.500/3.183)
```

Twelve clusters, largest 3.76 mm², thinnest 0.319 mm. Every one is a **rim wedge
where a tilted 2.0 mm plate is cut by a plane or meets a web**. None is under a
bearing face, none is in a standoff, and the nearest is 7.3 mm from the shell —
the load-path columns measure 2.5–3.3 mm. Shrinking the islands from 11.0 to
9.0 mm (which removed a real overlap problem) changed this by only 1.0 mm², so it
is not island overlap.

**Classified CLASS B**, and recorded in the hand-finish map: it is a print-quality
defect on non-structural rims, not unsafe structural thickness. The permanent fix
is a rim cleanup pass, which is not worth a redesign under §27. **Flagging it
explicitly so the call can be overridden.**

## 5. Issue classification (§18)

### CLASS A — must be solved in CAD

| issue | measurement | why it is CLASS A, and why it is blocked |
|---|---:|---|
| **SZH PCB outline vs the cavity** | **175.9–181.1 mm³** overlap with the shell, at both the as-placed and the raised position | This is not a rub. But it is measured on **PROVISIONAL web geometry** that overlaps the shell *independently of anything REV_I built* — the same 181 mm³ exists in the REV_A placement. §11 makes the received hardware the authority, so this is **blocked on measuring the real module**, not on more CAD. Mitigated: the deck is derived from the **cavity**, not from the PCB, so the prototype does not depend on the PCB outline being right. |

Everything else that could have been CLASS A came out clear: no confident-static
collision, no shell interference, no seat-to-seat interference, switches seat and
install, actuators clear, travel available, core is one valid solid.

### CLASS B — hand-finishable

| issue | measurement |
|---|---|
| cap side profile in the current bore | 0.89–9.47 mm³ per cap (reference: the ORIGINAL cap in the ORIGINAL bore is already 0.56–1.20 mm³). T2 and T5 are **at or below** the reference. Fix in CAD first — the cap is a printed part and is **not** frozen — then file the residual |
| terminal slot width | nominal 1.30 mm, FDM will close it slightly |
| joystick deck rim and mount holes | deliberately **SACRIFICIAL** (§19) — drill and trim to the real module |
| standoff pad height | 0.35 mm design clearance is below one layer of positional error |
| thin rim wedges | 27.36 mm², 0.32–0.89 mm, non-structural |

### CLASS C — hardware-modifiable (§12)

| item | overlap | action |
|---|---:|---|
| SZH stock knob | 404.0 mm³ | **replace.** Required anyway: at r 7.007 mm it does not pass the current 6.555 mm JOY bore, and it cannot reach +7.607 mm |
| SZH header | 19.3–21.0 mm³ | remove the plastic and solder directly, or clip the pins flush |

## 6. Renders (§28)

`08_renders/`

```text
01 ORIGINAL button external stack, sectioned on the T8 true axis
02 ORIGINAL joystick external stack, sectioned on the JOY true axis
03 ORIGINAL full internal architecture -- one conformal plate carries everything
04 ORIGINAL button / joystick relationship
05 CURRENT frozen shell with the full internal core
06 T1-T8 seats and the joystick together (section 15)
07a / 07b matched ORIGINAL vs CURRENT external protrusion
08 internal transparent view
09 joystick moving envelope against the core (reported, not cut)
10 core-to-shell load path
```

## 7. Verdict

```text
SOURCE-FAITHFUL THUMB PROTOTYPE PARTIAL — SPECIFIC CLASS-A ISSUE REMAINS
```

The original architecture is retained, not approximated: the same 4.759 mm stack,
the same 2.003 mm plate, the same 6.02 × 6.04 mm flat bearing, the same two
1.30 × 6.40 mm slots at ±2.60, the same "module bottom bears on the plate"
joystick mount, and the same external protrusion law for both the caps and the
knob. The core is one valid printable solid with zero shell interference, all
eight seats bearing, all sixteen slots open, and a load path that reaches the
shell — none of which REV_H had.

The single CLASS-A item is the **SZH PCB outline against the cavity**, and it is
CLASS A only in the sense that filing cannot fix it. It is a **provisional-geometry
question that must be closed by measuring the received SZH-EK056**, and the
prototype was deliberately built so that it does not depend on that answer.

Not called FAILED: no CLASS-A issue arises from the original architecture itself,
and per §33 CLASS-B and CLASS-C items alone do not warrant it.

## 8. Concurrency (§22)

The Finger / N1 / N2 subsystem is **actively in flux** — `docs/90`–`docs/93` were
written during this session and report 6 of 7 legs still unresolved on N2 / I3 / I4.
The `N1_N2_SHARED_CARRIER` keep-out used here dates from 2026-08-23 16:55.

```text
core vs N1/N2 keep-out = 0.000000 mm3   ->   REVALIDATE AFTER FINGER FREEZE
```

Nothing in that subsystem was modified.

## 9. Measurement corrections made during this revision

Recorded because several produced confident, wrong answers first.

1. **Skin reference.** Binning shell surface samples and keeping the outermost per
   bin picks points on the **far side** of the grip; it reported caps protruding
   8.4 mm and insertion depths of −4.56 mm. Ray-casting inward from outside cannot
   pick a far-side surface. Then a fixed 5.6–9.5 mm annulus straddled the
   **neighbouring openings** — adjacent cap centres are 10.3 mm apart and the caps
   are 7.6 mm wide, so the free ring is ~1.4 mm — and rays through a neighbour's
   hole dragged the reference 3–6 mm inward. Fixed with a per-cap ring and a p90.
2. **Lateral clearance.** `ray_intervals` pairs crossings and returns None on an
   odd count, so a radial probe that starts **inside** the cap is discarded —
   four of eight buttons returned no samples. Sector min/max then compared the
   closest shell point and the furthest cap point at **different angles**, and a
   square cap's radius swings 3.80 → 5.37 mm, so every button came out negative.
   Fixed with a nearest-neighbour query restricted to the same depth band.
3. **Bore profile.** Taking the closest shell sample in a slab perpendicular to
   the axis measures the curved **outer skin**, not the bore: it reported the two
   corner buttons' holes as 2.59–3.01 mm half-width, narrower than the cap that
   demonstrably passes through them.
4. **Cap overlap — the control that mattered.** A polar clearance metric declared
   five buttons CLASS A at −1.73 mm. Run on the **ORIGINAL cap in the ORIGINAL
   shell**, an assembly that works, the same metric reports −0.51, −1.07,
   −1.65 mm. A metric that condemns the known-good reference is measuring itself.
   The exact boolean control gave A = 0.56–1.20, B = 0.00–0.07, C = 0.89–9.47 mm³.
5. **Slot openness.** Testing a whole column marks a slot closed because a web or
   the deck lies far below it — 8 of 16 "closed" slots were all open. Restricted
   to the plate band: 16 of 16.
6. **Embedded mechanism.** 571.6 mm³ of "switch inside the core" was entirely the
   terminal **bounding envelope** (7.568 × 4.632 mm), which must cross the plate
   between two 1.30 mm slots. Body and actuator were 0.0000 on all eight.
7. **Insertion direction.** Switches enter from **outside, down their own bore**,
   landing on a plate whose top face looks outward. Sweeping them inward drove
   them through the plate and reported 555 mm³ of obstruction no assembly step
   would ever meet.

Two of these were geometry faults, not measurement faults, and were fixed in CAD:

8. **Deck links** were centred on the seat plate plane and pushed 1.3 mm up into
   every switch body. Hung below the plane instead, like the webs.
9. **The deck sized to the provisional PCB** was 41.3 × 36.0 mm, half-diagonal
   27.4 mm, in a cavity whose narrowest radius at that depth is 14.03 mm. The
   shell guard sawed the core into four pieces. The deck outline now comes from
   the cavity.

**The recurring lesson:** when a gate fails, check whether the metric expresses
the physics before changing the geometry. Five of the seven failures above were
the metric.

---

Stopped here per §33: no production apply, no Onshape write, no N1/N2 redesign,
no exterior change, no HARD FREEZE change, and JOY / T1–T8 were not moved.
