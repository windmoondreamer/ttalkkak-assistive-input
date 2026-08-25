# HAND_FINISH_MAP — REV_I source-faithful Thumb prototype

> **Updated for C07.** The candidate is now
> `C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step`, rebuilt for FDM.
> Two entries below changed because C07 removed the problem outright:
> **H3 deck rim** is now thick, cavity-shaped stock instead of a 2.5 mm ledge,
> and **the thin-rim entry is deleted** — interior area below 1.20 mm went from
> 27.36 mm² to **0.00 mm²**. See `C07_FDM_CLEANUP.md`.

Every region where the printed prototype is expected to need physical adjustment,
plus every deliberately sacrificial area (§17, §19, §30).

Classification follows §18. A **CLASS A** item is never listed here as
hand-finishable — those go in the report as CAD work.

---

## H1 — button cap side profile

| field | value |
|---|---|
| location | all eight caps, in the guided part of their frozen bores, 0.2–3.7 mm below the skin |
| predicted conflict | restored cap overlaps the current bore by **0.89–9.47 mm³** per cap |
| reference | the ORIGINAL cap in the ORIGINAL bore already overlaps by **0.56–1.20 mm³**, so ~1 mm³ is normal contact, not a fault |
| per button | T2 0.89 and T5 0.92 are **at or below** the reference; T1 3.28, T4 3.21, T7 2.74; T3 7.31, T6 9.47, T8 6.31 |
| classification | **CLASS B**, and only after the CAD fix below |
| CAD fix first | the cap is a printed part and is **not** frozen — its profile is re-cut against the current bore with the original 0.20 mm clearance. Do this in CAD, not by filing |
| expected removal | ~0.2–0.4 mm on one or two faces of T3 / T6 / T8 after printing |
| maximum safe removal | **0.60 mm per face.** Beyond that the cap loses its 0.2 mm guided fit and will rattle |
| tool | flat needle file, or 400-grit paper on a flat block |
| structural relevance | none — the cap carries no structural load, it transfers a fingertip press to the actuator |
| test afterwards | cap drops into the bore under its own weight, does not bind at any rotation, and returns freely when pressed |

## H2 — terminal escape slots

| field | value |
|---|---|
| location | 16 slots, 2 per seat, 1.30 × 6.40 mm at ±2.60 mm from each axis |
| predicted conflict | nominal slots against real switch legs; FDM tends to close a 1.30 mm slot slightly |
| classification | **CLASS B** |
| expected removal | 0.1–0.2 mm on the slot walls |
| maximum safe removal | widen to **1.80 mm**. The web between a slot and the seat edge is what holds the bearing face; past 1.80 mm the bearing area starts dropping |
| tool | 1.2 mm needle file, or a 1.5 mm drill run by hand |
| structural relevance | low, but the slot edge is inside the bearing footprint — do not chase it sideways |
| test afterwards | switch seats flat with both legs clear, and the body still contacts the plate around its whole 6.02 × 6.04 mm underside |

## H3 — joystick deck rim (SACRIFICIAL STOCK)

```text
HAND-FINISH / SACRIFICIAL STOCK
```

| field | value |
|---|---|
| location | the whole outer rim of the joystick deck, 24.0 mm below the skin |
| C07 change | deck is now **3.0 mm** thick (was 2.5) and its outline is the cavity, r 13.61–24.81 mm. The rim is solid printable stock, not a ledge |
| why sacrificial | the deck outline is derived from the **cavity**, not from the SZH PCB, because the provisional PCB overlaps the shell by 176–181 mm³ and therefore cannot be a datum (§11) |
| predicted conflict | the real SZH PCB will not match the web model; some rim will be in the way and some will be missing |
| classification | **CLASS B** |
| expected removal | up to ~3 mm of rim locally, wherever the real PCB or its solder tails land |
| maximum safe removal | keep **≥ 6 mm of rim width** where the **five vertical walls** meet the deck. Those are the load path and they also carry the slab during printing. Everything between walls may be removed entirely |
| tool | rotary tool with a cylindrical burr, then a flat file |
| structural relevance | **high at the five link landings, none between them** |
| test afterwards | PCB sits flat with no rock; deck links still attached; core still one piece |

## H4 — mounting holes for the joystick (SACRIFICIAL STOCK)

```text
HAND-FINISH / SACRIFICIAL STOCK
```

| field | value |
|---|---|
| location | joystick deck rim |
| why | the SZH mount-hole positions are PROVISIONAL. Printing holes at guessed positions is worse than printing solid stock and drilling to the real part |
| classification | **CLASS B** |
| expected work | drill 2–4 × Ø2.2 mm through the rim, using the real PCB as the template |
| maximum safe removal | no hole closer than **3 mm** to a deck link landing or to the rim edge |
| tool | 2.2 mm twist drill, hand-held or pillar |
| structural relevance | moderate — holes near a link landing weaken the load path |
| test afterwards | PCB bolts down flat; the core is still one piece; the shaft still centres in the JOY opening |

## H5 — solder-tail relief hole

| field | value |
|---|---|
| location | Ø16 mm hole in the centre of the joystick deck |
| predicted conflict | none expected — the SZH gimbal, both pots and the push switch all sit **above** the PCB, so the deck under it needs no module clearance. The hole exists only for solder tails and wiring |
| classification | **CLASS B** if it needs opening at all |
| maximum safe removal | Ø24 mm. Beyond that the rim narrows below 6 mm at the link landings |
| tool | rotary burr |
| structural relevance | low until Ø24 |
| test afterwards | wires exit without strain; no tail touches the shell |

## H6 — core standoffs

| field | value |
|---|---|
| location | the standoff pads that reach the shell |
| predicted conflict | 0.35 mm design clearance is below one FDM layer of positional error; a pad may print proud and preload the shell |
| classification | **CLASS B** |
| expected removal | 0.1–0.3 mm off a pad face |
| maximum safe removal | **1.0 mm.** Past that the pad no longer reaches the shell and the load path at that point is gone |
| tool | flat file |
| C07 change | pads are now **5.0 mm with a 1.2 mm 45° chamfer skirt**, and both ends are constrained above the bed plane so no pad becomes the part's lowest point |
| structural relevance | **high — this is the load path.** Take material off the pad face, never off the chamfer skirt or the slab behind it |
| test afterwards | the core sits in the shell without springing it open, and the shell halves still close on their own screws |

---

## Hardware modifications (CLASS C, §12) — not hand-finishing of the print

| item | overlap with the shell | action |
|---|---:|---|
| SZH stock knob (`REMOVABLE_CAP_NOMINAL_ENVELOPE`) | 404.0 mm³ | **replace.** A new knob is required anyway: the stock one cannot reach the original +7.607 mm knob top, and its 7.007 mm radius does not pass the current 6.555 mm JOY bore |
| SZH header (insulator + 5 pins) | 21.0 mm³ | **remove the plastic and solder directly**, or clip the pins flush |

## Not hand-finishable — see the report

| item | why it is CLASS A |
|---|---|
| SZH PCB outline vs the cavity | 176–181 mm³ of overlap is not a rub. It is measured on PROVISIONAL web geometry, so it is **blocked on measuring the real module**, not on filing |
| SZH 25° moving envelope | provisional. Must be measured on the real module before any geometry is cut against it (§13) |
| N1 / N2 adjacency | owned by the concurrent Finger workflow — **REVALIDATE AFTER FINGER FREEZE** (§22) |


---

## H7 — support removal from the slab underside (C07, new)

| field | value |
|---|---|
| location | the flat underside of the button slab, which overhangs the five vertical walls like a table top over its legs |
| predicted work | **812.6 mm²** of slicer support across 151 regions, up to **16.62 mm** tall, standing on the bed |
| accessibility | **0 trapped regions.** Every region was probed on 16 horizontal bearings; the three largest score 11/16, 7/16 and 16/16 clear |
| classification | **CLASS B** — expected, planned support, not a defect |
| what it must NOT touch | nothing critical is exposed to it: **0 support faces** land on a bearing face, a slot wall, the deck top or a pad contact face |
| tool | flush cutters, then a flat file on the slab underside only |
| structural relevance | none — the slab underside is a free internal surface in the assembled part |
| test afterwards | all 16 terminal slots still pass a 1.30 mm gauge; the core still drops into the shell without springing it |

## H8 — first-layer check (C07, new)

| field | value |
|---|---|
| location | the joystick deck underside, **977.4 mm²** flat on the bed |
| why it matters | this is the whole part's adhesion, and the deck carries the joystick load path |
| classification | **CLASS B** |
| expected work | deburr the first-layer elephant foot around the deck perimeter |
| maximum safe removal | 0.3 mm off the deck underside. The deck is 3.0 mm thick and must stay ≥ 2.5 mm |
| tool | deburring blade or 400-grit on a flat block |
| test afterwards | the deck sits flat on a surface plate with no rock, and the SZH module bears without a gap
