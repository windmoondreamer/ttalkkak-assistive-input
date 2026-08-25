# REV_F — original Backplate rigid-fit + trim test

Date 2026-08-25 · local build123d / OCCT · Onshape API 0 · production writes 0
Shell authority: exact Onshape `THUMB_LOWER15_HOUSING_V1` export.
REV_A…REV_E read-only. No deformation, no rebase, no generated conformal band.

---

## 1. Can one rigid pose fit the current openings?

**Yes, exactly — and it is already known.** The Thumb cartridge (Backplate,
caps, controls) was moved as ONE rigid body by `THUMB_DELTA = (0, +12.25,
−21.00)`. The pose that preserves the functional relationship to the nine frozen
controls is therefore that transform itself, with **zero residual**:

| pose | max lateral | max angular | axial shift |
|---|---:|---:|---:|
| **A — pure THUMB_DELTA** | **0.0000 mm** | **0.0000°** | **0.0000 mm** |
| B — +7.109 mm along the seat normal | 0.8931 mm | 0.0000° | 7.109 mm |
| D — best non-interfering pose | 4.7518 mm | **18.777°** | 6.848 mm |
| C — best fit to 1.0 mm | **24.995 mm** | 0.443° | 10.526 mm |

Per-control at pose A: centre/seat positional error 0.0000 mm, axis angular
error 0.0000°, seating-plane orientation error 0.0000° for JOY and T1–T8.

```text
RIGID POSE vs CURRENT CONTROLS = PASS (exact)
```

## 2. …but that pose is not at 1 mm standoff

Gap from the plate's outer face to the exact approved shell inner surface,
19,999 area-weighted samples over the 2196.57 mm² outer face:

| pose | p05 | p25 | **p50** | p75 | p95 | min | interfering |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A control-aligned** | +2.728 | +6.798 | **+9.153** | +10.816 | +11.695 | −28.49 | 2.1 % |
| B translation only | −4.537 | −0.450 | **+1.963** | +3.679 | +4.502 | −35.63 | 27.9 % |
| D non-interfering | +0.047 | +4.454 | **+8.389** | +10.875 | +14.092 | −20.70 | 4.7 % |
| C best fit | −0.425 | +0.120 | **+0.362** | +0.634 | +4.535 | −5.02 | 18.4 % |

The optimiser can reach a 0.36 mm median gap — but only by sliding the plate
**24.995 mm laterally**, i.e. onto a different part of the grip. Any pose that
keeps registration within ~1 mm is stuck at a 2–9 mm median gap.

```text
~1 mm SHELL STANDOFF AT A REGISTRATION-PRESERVING POSE = NOT ACHIEVABLE
```

Measurement note: a first pass sampled triangle vertices instead of the face
area and got only 540 points, which biased these statistics. All numbers above
are from the corrected area-weighted sampling.

## 3. Trim only what protrudes — at pose A this works well

Exact approved JaD/JfD used as a forbidden volume, grown by 1.00 mm clearance in
±u, ±v, ±n:

| | pose A | pose B |
|---|---:|---:|
| interference before trim | **217.84 mm³ (3.7 %)** | 654.99 mm³ (11.1 %) |
| volume surviving | **5396.58 mm³ = 91.5 %** | 4834.37 mm³ = 81.9 % |
| largest single piece | **5383.08 mm³ = 91.2 %** | 4755.39 mm³ = 80.6 % |
| surviving plan area | **1914.19 mm²** | 1704.94 mm² |
| interference after trim | **0.000000 mm³** | — |

Pose B is worse on every measure, so the extra 7.1 mm of translation is
counter-productive. **Pose A is the pose to use.**

Plate material present within 3 mm of each control centre after trim:
T1 78 %, T2 65 %, T3 78 %, T4 65 %, T5 64 %, T6 65 %, T7 67 %, T8 67 %,
JOY 0 % (correct — the joystick needs an aperture, not a plate).

## 4. Thickness is preserved; the trim boundary is not

| | p25 | p50 | p75 |
|---|---:|---:|---:|
| untrimmed Backplate | 1.910 | **2.003** | 2.028 |
| after rigid placement + trim | 1.931 | **2.004** | 2.035 |

**The original ~2.0 mm true thickness is retained exactly wherever material
remains.** This is the property C01/C02's along-axis band could not deliver.

But the trim itself creates an edge: 42.94 mm² below 1.20 mm, 66.88 mm² below
1.60 mm, minimum 0.0012 mm. **All of it is within 1 mm of the plate boundary —
0.00 mm² lies more than 1 mm inboard.** So it is purely a trim-boundary taper,
exactly the case §4 anticipated. Fixing it means pulling the trim boundary
inward to a printable termination; that has not been done in this test.

8 chips totalling 13.50 mm³ were dropped to leave one coherent solid
(5383.08 mm³, 91.2 % of the original, 91 faces, valid).

## 5. Load-transfer zones — material survives, contact does not

| zone | material surviving | footprint | original target | gap p50 | contact ≤0.30 mm |
|---|---:|---:|---:|---:|---:|
| LEFT | **101.50 mm²** | 150.56 | 71.69 | +3.935 | **0.00 mm²** |
| RIGHT | **36.50 mm²** | 54.69 | 23.38 | +2.983 | **0.00 mm²** |

Both zones retain more material than the original contact areas. But at pose A
the plate is 2.98–3.94 mm off the shell there, and the whole plate's minimum gap
after trim is **+1.285 mm**, so **contact ≤0.30 mm is 0.00 mm² everywhere**.

The zones survive as structure. They provide **no load transfer** at this pose.

## 6. Why — and it is a property of the approved geometry

Consistent across REV_D, REV_E and REV_F: relative to the frozen controls, the
approved lowered shell's cavity at the Thumb cluster is roughly **7.7 mm deeper**
than the original shell's was at the original location. The original Backplate
sat 1.230 mm off its own shell; the identical rigid body at the identical
relationship to its controls sits 9.029 mm off this one. Nothing was deformed,
mis-registered or badly reconstructed — the two cavities are simply different
depths.

## 7. Candidate

`02_candidate/C03_ORIGINAL_BACKPLATE_RIGID_FIT_TRIM.step` / `.stl`
Single valid solid, 5383.0758 mm³, 91 faces. Literally the original Backplate
B-rep, rigidly placed at `THUMB_DELTA` and trimmed by the exact approved shell.
No surface was regenerated.

C01 and C02 are untouched.

| | ORIGINAL | C01 | C02 | **C03 rigid-fit** |
|---|---:|---:|---:|---:|
| volume mm³ | 5899.53 | 3375.46 | 3375.32 | **5383.08** |
| true thickness p50 | 2.003 | 2.400* | 2.519* | **2.004** |
| gap p50 | +1.230 | +1.192 | +1.19 | **+9.029** |
| interference | ~0 | 0.0026 | 0.20 | **0.000000** |
| contact ≤0.30 mm | 95.06 mm² | 20.81 mm² | 17.00 mm² | **0.00 mm²** |
| area < 1.20 mm | — | 100.12 mm² | 17.31 mm² | **42.94 mm² (all at the trim edge)** |

\* C01/C02 thickness is along-n, not true-normal, at the plate rim — that is the
defect C03 avoids by construction.

## 8. Verdict

```text
ORIGINAL BACKPLATE RIGID-FIT REUSE PARTIAL — SPECIFIC TRIM/ALIGNMENT ISSUE
```

The plate itself reuses cleanly: one rigid pose with **exact** control
registration, only **8.5 %** trimmed away, **0.000000 mm³** residual
interference, and the original **2.004 mm** thickness preserved everywhere it
remains. That is a better structural substrate than either generated plate.

Two specific issues remain, both stated precisely:

1. **Standoff and registration are mutually exclusive under one rigid pose.**
   The registration-preserving pose leaves a **9.029 mm** median gap and
   therefore **zero** load transfer. Reaching ~1 mm costs either 24.995 mm of
   lateral registration or 11–28 % of the plate buried in the shell.
2. **The trim creates a 42.94 mm² sub-1.20 mm boundary taper** (min 0.0012 mm),
   all of it within 1 mm of the edge. It needs the boundary pulled inward to a
   printable termination, which this test did not do.

Issue 1 is the substantive one and it is not a defect in the plate — it is the
7.7 mm cavity-depth difference in the approved geometry. Closing it needs a
decision that is outside this test: either accept a deep-seated plate and carry
the load some other way, or add a local standoff feature, or re-open the switch
stack height. Not proposed here.

Stopped. No production apply, no shell modification, no SZH carrier, no HARD
FREEZE change, and no further generated conformal plate.
