# REV_J — docs/101 × latest Thumb holder revalidation

Date 2026-08-25 · local build123d / OCCT · Onshape API 0 · production writes 0
Measurement only. No geometry was created or modified anywhere.

```text
DOCS/101 × LATEST THUMB HOLDER REVALIDATION RESULT:

LATEST THUMB CANDIDATE = C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED
DOCS/101 FINGER BASE USED = YES

THUMB EXTERIOR CHANGED = NO
FINGER GEOMETRY CHANGED = NO
THUMB GEOMETRY CHANGED IN THIS PASS = NO

COORDINATE REGISTRATION = PASS   (transform = IDENTITY, confidence HIGH)

JOY ALIGNMENT = PASS

T1–T8 ALIGNMENT = 8/8

THUMB CORE ↔ DOCS/101 SHELL = 0.000000 mm³ penetration (JaD 0.000000, JfD 0.000000)
                              expected contact 5.16 % of the core surface within 0.60 mm

THUMB CORE ↔ FINGER POCKETS = 0.0000 mm³ on all 8

THUMB CORE ↔ ACTUAL FINGER SWITCHES = 0.0000 mm³ on all 8
                              (body, actuator and terminals each measured separately)

MINIMUM FINGER/THUMB CLEARANCE = 0.5217 mm at N1

PRE-EXISTING THUMB/SZH ISSUE = UNCHANGED — provisional SZH PCB envelope vs cavity,
                              175.8813 mm³, identical to the REV_I value, blocked on
                              measuring the received SZH-EK056

NEW DOCS/101-INDUCED ISSUE = NONE structural.  One ASSEMBLY-ORDER constraint:
                              N1 and N2 must be seated before the Thumb core.

JOYSTICK HOLDER = REUSE AS-IS
THUMB BUTTON CARRIER = REUSE AS-IS

ASSEMBLY = PASS   (Sequence A valid)
FDM REGRESSION = PASS

VERDICT = A — THUMB CANDIDATE REUSABLE AS-IS ON DOCS/101
```

---

## 1. Latest Thumb candidate (§4)

```text
LATEST THUMB CANDIDATE = C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED
SOURCE FILE            = REV_I .../10_scripts/i10_c07_refine.py
STEP                   = REV_I .../07_prototype/C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step
                         sha256 45BB7E307669…  2026-08-25 10:57
STL                    = REV_I .../07_prototype/C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.stl
VALIDATION REPORT      = REV_I .../08_validation/i08_validate.json  (27 PASS / 0 FAIL)
FDM CLEANUP REPORT     = REV_I .../11_reports/C07_FDM_CLEANUP.md
```

Why it is the latest, from files rather than from names in older reports: C07 is
the newest STEP in `07_prototype` (10:57 against C06 at 04:02); the validation
JSON (10:58), thin map (10:58), orientation audit (10:59) and reports (11:01) all
postdate it; and its recorded volume 7378.020 mm³ / 333 faces matches
`i10_c07.json`, so the validation and the STEP are the same build. C06 was not
used.

## 2. Coordinate registration (§7)

```text
THUMB CANDIDATE TRANSFORM APPLIED = NONE (identity)
REASON = the docs/101 chain is built FROM this lab's frozen authority, and the
         Thumb region measures identically on both shells
COORDINATE REGISTRATION CONFIDENCE = HIGH
```

**Provenance.** `lower15_true_bare_finger_base_recovery.py` reads
`thumb_exact_onshape_source/{JaD,JfD}_THUMB_LOWER15_APPROVED.step` — the same two
files this lab froze. Both still hash to the REV_D baseline
(`622ADB3B…`, `D75F62E0…`). The bare base hashes match the values docs/101 records
as its own authority (`90074760…`, `CD70562A…`), its validation declares
`lower15ThumbPreserved = true` / `thumbOpeningsPreserved = true`, and docs/101's
own `thumbAfterCut` passes 9 of 9 Thumb controls.

**Independent geometry**, five checks that do not use the provenance at all:

| check | result |
|---|---|
| Thumb-region material bounding box, 78 617 points | **delta 0.000000 mm** |
| exact ray first-hit on the outer skin, 736 parallel probes | **p50 0.000000000 mm**, exactly zero on 72.88 % |
| same probe, structurally comparable columns only | max **9.064 mm** — against a control of **9.109 mm** |
| skin reference on the 9 Thumb control axes | 4 of 9 identical to 1e-9; worst 0.034 mm |
| every moved axis boundary | 0.9–13.6 mm from a frozen Finger centre, all at t = −24…−40 mm |

Two measurement traps were hit and corrected here, both of which produced a
confident wrong answer first:

* A nearest-neighbour query between two independent surface **samplings** measures
  sample spacing, not surface displacement. Run against the docs/101 **bare base**
  — a shell whose own validation certifies the Thumb region untouched — it still
  reported p50 0.090 / p90 0.190 / max 9.18 mm. Replaced with exact ray-triangle
  intersection.
* The remaining tail then looked alarming (p99 10.09 mm) until the same control
  was applied: the certified-unchanged base gives **9.109 mm** where docs/101
  gives **9.064 mm**. The tail is probes grazing a Thumb opening rim under a
  different tessellation (52 206 vs 32 316 triangles), not a shift.

## 3. Shell collision (§8)

| quantity | value |
|---|---:|
| C07 ∩ docs/101 JaD | **0.000000 mm³** |
| C07 ∩ docs/101 JfD | **0.000000 mm³** |
| **UNINTENDED PENETRATION** | **0.000000 mm³** |
| EXPECTED CONTACT | 5.16 % of the core surface within 0.60 mm — the three designed standoff landings |
| minimum gap | 0.1108 mm |
| gap p05 / p50 | 0.5859 / 5.1460 mm |

C07 was built with a 0.35 mm shell guard, so contact inside that band is the
intended load path, not interference.

## 4. Table A — per-Finger collision (§9, §10)

| Finger | Core ↔ pocket | Core ↔ switch | Core ↔ terminal/actuator | Minimum clearance | Result |
|---|---:|---:|---:|---:|---|
| N1 | 0.0000 | 0.0000 | 0.0000 | **0.5217** | MINOR LOCAL ADJUSTMENT |
| N2 | 0.0000 | 0.0000 | 0.0000 | 2.3157 | MINOR LOCAL ADJUSTMENT |
| I2 | 0.0000 | 0.0000 | 0.0000 | 8.0192 | PASS |
| I3 | 0.0000 | 0.0000 | 0.0000 | 10.4671 | PASS |
| I4 | 0.0000 | 0.0000 | 0.0000 | 10.4839 | PASS |
| M3 | 0.0000 | 0.0000 | 0.0000 | 26.0864 | PASS |
| M4 | 0.0000 | 0.0000 | 0.0000 | 25.9192 | PASS |
| N3 | 0.0000 | 0.0000 | 0.0000 | 22.0389 | PASS |

Five volumes were tested per button because they fail differently: the switch
body, the Ø3.35 actuator, the four terminals, the pocket envelope (body grown by
the docs/101 0.2 mm per side), and a 12 mm service corridor along the press axis.
**Every static volume is 0.0000 mm³ on every button.** The two MINOR flags are
the service corridor only — N1 425.0015 mm³, N2 44.4554 mm³ — which is an
assembly-order question, not a collision.

**A labelling quirk in the docs/101 export, worth passing back:** inside
`ALL8_DETAILED_SWITCH_PLACEMENT.step` every leaf in all eight groups is stamped
`N3_…`. The button identity lives only on the parent group label. Keying a dict
by leaf label collapses eight buttons into one, and an audit written that way
silently covers a single button. This audit keys off the group label.

## 5. Table B — T1–T8 and JOY registration (§11)

Measured against the **docs/101 skin**, not the authority skin.

| ctrl | opening open | axis error | protrusion | vs original law | cap→plate | result |
|---|---|---:|---:|---:|---:|---|
| JOY | YES (0.0000 blocked) | 0.0000° | — | — | — | PASS |
| T1 | YES | 0.0000° | 1.358 | −0.0268 | 4.759 | PASS |
| T2 | YES | 0.0000° | 1.053 | −0.0126 | 4.759 | PASS |
| T3 | YES | 0.0000° | 1.424 | −0.0349 | 4.759 | PASS |
| T4 | YES | 0.0000° | 1.287 | −0.0037 | 4.759 | PASS |
| T5 | YES | 0.0000° | 1.135 | −0.0307 | 4.759 | PASS |
| T6 | YES | 0.0000° | 1.330 | −0.0073 | 4.759 | PASS |
| T7 | YES | 0.0000° | 1.200 | +0.0002 | 4.759 | PASS |
| T8 | YES | 0.0000° | 1.210 | −0.0011 | 4.759 | PASS |

Centres and axes were not moved, so both errors are 0 by construction. The
protrusions land at **1.053–1.424 mm** above the docs/101 skin against the
original law's 1.066–1.459, worst deviation 0.035 mm — well inside the 0.30 mm
tolerance. The **obsolete buried cap positions (−4.116 to −7.179 mm) were not
restored**, as §6 requires, and cap-underside-to-plate-top holds at 4.759 mm on
every button to twelve decimal places.

## 6. Table C — joystick (§12)

| SZH part (PROVISIONAL) | vs docs/101 shell | vs Finger switches |
|---|---:|---:|
| SZH_pcb | **175.8813** | 0.0000 |
| SZH_gimbal | 0.0000 | 0.0000 |
| SZH_x_pot / y_pot / push_switch | 0.0000 | 0.0000 |
| SZH_shaft | 0.0000 | 0.0000 |
| SZH_cap (REMOVABLE) | 404.0403 | 0.0000 |
| SZH_header (REMOVABLE) | 20.9681 | 0.0000 |
| SZH 25° moving envelope (reported, not cut) | 1235.1700 | **0.0000** |

Deck 23.993 mm below the skin, cavity-shaped r 13.61–24.81 mm, JOY column open
through docs/101, knob target +7.607 mm unchanged.

```text
JOYSTICK HOLDER = REUSE AS-IS
```

**Nothing in the joystick region touches Finger geometry — every value is
0.0000 mm³.** The shell numbers are the pre-existing REV_I values, unchanged.

## 7. Table D — assembly sequences (§16)

Core placement into one **open** half, swept 30 mm:

| direction | vs JaD shell | JaD switches | vs JfD shell | JfD switches |
|---|---:|---:|---:|---:|
| +U | 17802.96 | 0.0000 | **0.0000** | **0.0000** |
| −U | **0.0000** | **0.0000** | 18538.63 | 0.0000 |
| +N outward | 7268.20 | 0.0000 | 8569.10 | 0.0000 |
| −N inward | 8653.08 | 687.68 | 9295.99 | 1118.53 |
| ±V | 10692–12605 | 0.0000 | 15661–16844 | 0.0000 |

Finger switch insertion along its own press axis, core already installed:

| button | owner half | corridor obstruction | first block |
|---|---|---:|---:|
| I2, I3, I4, M3, M4, N3 | — | **0.0000** | never |
| N1 | JfD | **425.0015** | 1.0 mm |
| N2 | both | **44.4554** | 5.0 mm |

```text
SEQUENCE A  Finger switches epoxied -> core laid into the open half -> close = VALID
SEQUENCE B  core installed -> Finger switches inserted                       = BLOCKED at N1, N2

VALID ASSEMBLY SEQUENCE = A
ASSEMBLY BLOCKER = NONE
```

The order is forced but nothing is impossible: with JfD removed the core lifts
straight out along +U with **zero** obstruction from JaD's shell *and* from JaD's
installed switches, and symmetrically along −U out of JaD.

A first attempt declared both sequences blocked, and both verdicts were artefacts
of how the motion was posed — Sequence A swept the core straight down into a
*closed* cavity, which is not how a split shell is assembled. Section 16
anticipates exactly this.

## 8. FDM regression (§18)

| check | value |
|---|---|
| STEP reimport | 1 solid, BRep valid |
| volume | 7378.020 mm³, delta **0.000154 mm³** from the build record |
| faces | 333 |
| interior area below 1.20 mm | **0.00 mm²** |
| plan components | 1 |
| thickness p25 / p50 | 3.000 / 3.000 mm |
| new feather edges, tangent-only or zero-thickness contacts | none |
| intended print orientation JOY_AXIS_UP | still usable — docs/101 adds no material inside the core envelope |

```text
FDM REGRESSION = PASS
```

C07's validated manufacturing state is intact and was not touched.

## 9. Table E — pre-existing vs new

| issue | pre-existing (REV_I) | after docs/101 | induced by docs/101? |
|---|---:|---:|---|
| SZH PCB envelope vs cavity | 175.881–181.1 mm³ | **175.8813 mm³** | **NO** — identical, blocked on measuring the real module |
| SZH stock knob vs shell | 404.04 mm³ | 404.0403 mm³ | NO — CLASS C, knob is replaced anyway |
| SZH header vs shell | 20.97 mm³ | 20.9681 mm³ | NO — CLASS C, header removed |
| SZH 25° moving envelope | 1235–2562 mm³ reported | 1235.1700 mm³ reported | NO — provisional, never cut |
| N1/N2 keep-out (old, pre-docs/101) | 0.0000 after relief | superseded by real geometry | resolved |
| **N1/N2 switch service corridor** | did not exist | 425.00 / 44.46 mm³ | **YES — assembly ORDER only, no geometry change** |
| Thumb core ↔ Finger pockets / switches | did not exist | **0.0000 mm³ ×8** | NO |
| Thumb core ↔ shell | 0.000000 mm³ | **0.000000 mm³** | NO |

## 10. Renders (§20)

`08_renders/`

```text
01 docs/101 shell + C07 assembled         06 N1 / N2 region
02 interior overview, both subsystems     07 JOY holder / deck close-up
03 core + all 8 pocket envelopes          08 T1–T8 carrier overview
04 core + actual detailed switches        09 JaD / JfD closure
05 closest interface, N1 sectioned        10 N1 service corridor — the only finding
```

## 11. Verdict

```text
A — THUMB CANDIDATE REUSABLE AS-IS ON DOCS/101
```

Every static integration measurement is zero: the core does not touch either
docs/101 shell half, nor any of the eight pockets, switch bodies, actuators or
terminals. All nine Thumb controls remain registered, all eight protrusions hold
the REV_I source-faithful law to within 0.035 mm, and the C07 manufacturing state
survives the STEP round trip unchanged.

The only thing docs/101 introduces is an **assembly-order constraint** — N1 and
N2 must be seated and epoxied before the Thumb core goes in — which requires no
change to any part. Per §21 the pre-existing provisional SZH issue does not
downgrade this verdict, and per §16 a single failing sequence does not fail
assembly when a valid one exists.

No geometry was modified. Stopping here for review, as §19 and §24 require.
