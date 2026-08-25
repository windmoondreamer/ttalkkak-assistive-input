# REV_L — C09 continuous curved carrier

Date 2026-08-26 · local build123d / OCCT · Onshape API 0 · production writes 0
C07, C07.1, C08, docs/101 and REV_A…REV_K: **not modified**. All writes inside
`thumb_inner_housing_lab/REV_L_C09_CONTINUOUS_CURVED_CARRIER/`.

Outputs
```text
03_full_c09/C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.step   (10.0 MB)
03_full_c09/C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.stl
04_validation/l04_validate.json
08_renders/1..7c  (9 images)
```

---

## 1. What the sketches specified, and what the measurement said

The two sketches read as: two black curves = the shell wall, **"1mm"** = the
carrier-to-shell relationship, **"동일 폭 구조"** = a uniform-width band, with
per-button seat blocks tilted to their own press axes.

I had planned the opposite arrangement — a deep carrier with posts rising
outward. L01 settled it by measurement:

```text
fitted shell interior sits 4.3-4.9 mm OUTBOARD of every seat top
so a carrier 1 mm inside the shell is 5.68-6.62 mm outboard of the seats
-> the blocks hang INWARD, exactly as drawn
spread across all eight buttons = 0.94 mm  -> one uniform band is workable
```

## 2. The carrier surface

The carrier is a **smooth degree-2 polynomial fit** of the shell interior
(**rms 0.624 mm**), deliberately *not* a carve of it. That distinction is the
entire lesson of C08, whose exactly-conformal collars formed a mechanical lock.

Getting a usable fit took three attempts, and the first two failed in ways worth
recording:

| attempt | method | result |
|---|---|---|
| 1 | cast outward, keep the first hit | 1217 of 1485 samples rejected; degree-4 fit at **4.42 mm rms** put T7's "interior" *below its own seat* |
| 2 | cast inward, take the wall's far boundary | **14.45 mm rms** — the u ±24 / v +16 window ran off the Thumb panel onto the grip flanks, mixing three surfaces |
| 3 | restrict to the button field, plausibility band | **0.624 mm rms**, interior consistently 4.3–4.9 mm outboard of every seat |

## 3. Three-button gate (§8)

Cases from L01's measured score: **EASY T7 · MID T2 · HARD T1**.

| gate | result |
|---|---|
| single valid solid | PASS — 465 faces |
| shell interference | **JaD 0.000000, JfD 0.000000 mm³** |
| docs/101 Finger interference | **0.000000 mm³**, min clearance 19.33 mm |
| switch seats bear | 3/3 at 23.79 mm² (65.2 %) |
| terminal slots (exact boolean) | **6 of 6 open** |
| terminal escape depth | worst 11.841 mm against 3.654 |
| cap protrusion | 1.066–1.385 mm, the REV_J law, untouched |
| SZH static package | **0.000000 mm³** |
| insertability | +U out of JfD: peak **0.0232 mm³** over the first 4.5 mm, then free |

```text
THREE-BUTTON FEASIBILITY = PASS
```

A caveat on that last line: the run that would have written the corrected gate
JSON was killed during the bottleneck fix below, so `02_gate/l03_gate.json` on
disk is from the pre-correction run and still records the old ≤1e-6 threshold as
a FAIL. The insertability numbers quoted above come from a dedicated 0.5 mm
step probe, not from that JSON.

## 4. Full C09 — 11 PASS / 1 FAIL

| check | result |
|---|---|
| single valid solid | PASS — 7314.874 mm³, 547 faces |
| shell interference | **JaD 0.000000, JfD 0.000000 mm³** |
| minimum structural thickness | **0.00 mm² below 1.20 mm** |
| all eight seats bear | **8/8**, 23.79 mm² (65.2 %) each |
| all sixteen slots open | **16/16** (exact boolean) |
| terminal escape depth | worst 11.837 mm |
| docs/101 Finger interference | **0.000000 mm³ on all 8** |
| JOY column unobstructed | 0.0000 mm of C09 on the axis |
| SZH static package | **0.000000 mm³** over 8 parts |
| switches installable down bores | 0.0000 mm³ |
| FDM orientation JOY_AXIS_UP | usable |
| **one-piece insertion** | **FAIL** (confirmed against the full shells, §5) |

### Per-Finger (§11)

| Finger | collision | min clearance |
|---|---:|---:|
| N1 | 0.0000 | **18.7887** |
| N2 | 0.0000 | 19.0852 |
| I2 | 0.0000 | 20.4996 |
| I3 | 0.0000 | 23.9192 |
| I4 | 0.0000 | 23.8588 |
| M3 | 0.0000 | 26.1363 |
| M4 | 0.0000 | 25.9430 |
| N3 | 0.0000 | 20.8980 |

## 5. The hard gate, and what actually locks

Measured against the **full docs/101 shells, no crop** (`l06_sweep_groundtruth.json`):

| sweep, 25 mm | peak | total | obstructed steps | free from |
|---|---:|---:|---:|---:|
| +U vs JaD | 836.47 | 14564.01 | 25 of 25 | never |
| **+U vs JfD** | **98.91** | 781.22 | 17 of 25 | 18.0 mm |
| **−U vs JaD** | **93.95** | 620.00 | 17 of 25 | 18.0 mm |
| −U vs JfD | 840.68 | 14040.54 | 25 of 25 | never |

L04's first pass swept against a Thumb-local crop for speed. A crop can only
UNDER-report obstruction, so it could not have rescued a FAIL, but it did
distort one number: **−U vs JaD read 39.20 mm³ cropped against 93.95 mm³ full**,
a factor of 2.4. `+U vs JfD` was accurate to four digits (98.9063 vs 98.9052),
and the **18.0 mm release point holds in both**, so that characterisation was
not a crop artefact.

```text
one-piece insertion into an open half = FAIL
```

**The band is not the problem — the blocks are.** With three blocks on the *same
full-field band*, the best path peaked at **0.0232 mm³** and freed itself after
4.5 mm. Adding the remaining five raised that peak to **98.91 mm³** and pushed
release out to 18.0 mm. The continuous curved carrier withdraws cleanly; eight
inward-hanging blocks reaching into a curved cavity do not.

This also means the carrier gap is the wrong knob. Raising it 1.00 → 1.30 mm
changed the sweep numbers *not at all* — +U/JfD stayed at exactly 0.1 and
−U/JaD at exactly 416.9 in the three-button case — which is what first showed
the obstruction was never the band.

## 6. C07.1 vs C08 vs C09 (§14)

| Metric | C07.1 | C08 | C09 |
|---|---:|---:|---:|
| **one-piece assembly** | **PASS** (+U/JfD and −U/JaD exact 0.0) | FAIL (505.2 mm³, blocked throughout) | **FAIL** (best peak 93.95 mm³, free only from 18.0 mm) |
| shell collision | 0.000000 | 0.000000 | 0.000000 |
| docs/101 collision | 0.000000 | 0.000000 | 0.000000 |
| minimum N1 clearance | 0.5225 mm | 18.8996 mm | **18.7887 mm** |
| volume | **6694.168 mm³** | **4760.872 mm³** | 7314.874 mm³ |
| B-rep faces | **247** | 315 | 547 |
| major structural members | 13 | 10 | **9** |
| support-required | **688.5 mm² (10.2 %)** | 1000.8 mm² (16.2 %) | 1446.2 mm² (16.6 %) |
| trapped support | 0 | 0 | 0 |
| interior below 1.20 mm | **0.000 mm²** | 0.44 mm² | **0.00 mm²** |
| button seats | 8/8 | 8/8 | 8/8 |
| terminal slots | 16/16 | 16/16 | 16/16 |
| joystick | integrated deck | deck carried over | deck carried over |
| load path | seat → slab → chord wall → deck → shell | seat → collar → landing → shell | **seat → block → curved carrier → shell** |

C09 wins on member count, load-path simplicity and N1 clearance (36× C07.1's).
It loses on volume, face count and support area, and it fails the hard gate.

**Two process faults found and corrected, both mine:**

1. The comparison row printed `PASS (none)` for C09's one-piece assembly while
   the gate itself recorded FAIL — a formatting fallback that read as a pass.
   Script and stored JSON corrected to `FAIL (no viable path)`.
2. Killing a stalled `l03` did not kill its **shell**, which went on to launch
   its own `l04` alongside the corrected one. Two processes interleaved writes
   into the same log, producing a traceback whose frames splice line 297 → 202 →
   57 and a line reading `"hell seat -> ..."`. The log is unrecoverable; the
   artefacts were verified instead and are internally consistent. Ground-truth
   re-measurement (§5) then corrected one number that the speed crop had
   distorted.

## 7. Renders

```text
1  C09 in the docs/101 shell          5  joystick coordination
2  section at T2: carrier -> block -> flat seat
3  one band carrying all eight seats  6  underside, JOY_AXIS_UP
4  docs/101 Finger interface          7a/7b/7c C07.1, C08, C09 same camera
```

## 8. Verdict

```text
LEVEL 1  THREE-BUTTON FEASIBILITY = PASS

LEVEL 2  C — C09 ARCHITECTURE FAILED — RETAIN C07.1 TRACK
```

The reasoning, plainly: §7 set the primary goal as "simpler than C07.1 **and**
actually insertable as a one-piece subassembly", and §10 made assembly a hard
gate. C09 meets the simplicity half — 9 members against 13, a three-step load
path, zero thin material, and a 36× better N1 margin — but it does not meet the
insertability half, and it is also worse than C07.1 on volume, faces and
support. That is not "works but doesn't clearly improve" (B); the stated primary
goal is not met.

**What is worth keeping from this.** The continuous curved carrier itself is
sound and withdrawable — the three-button build proved that on the full band.
What breaks it is eight blocks hanging inward into a curved cavity, which is a
scaling property of the block arrangement, not of the band. Any future attempt
would need to change how the seats attach to the carrier, not the carrier.

I am not proposing that change here: §16 says stop after validation and verdict.

---

No production apply. C07, C07.1, C08 and docs/101 untouched. Finger geometry
untouched. No frozen external control geometry changed.
