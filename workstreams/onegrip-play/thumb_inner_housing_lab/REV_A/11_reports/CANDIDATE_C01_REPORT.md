# CANDIDATE_C01_REPORT — `C01_SOURCE_FAITHFUL_REBASE`

Build: `a13_c01_build.py` → `a14_c01_finalise.py`
Geometry: `09_exports/C01_SOURCE_FAITHFUL_REBASE.step` / `.stl`
Data: `07_candidates/c01_build.json`, `07_candidates/c01_evaluation.json`

---

## 1. Intent

Project the **original** OneGrip inner-housing design law (measured in A11) onto
the **frozen** shell inner surface, rather than rigidly transplanting the original
part. Nothing about the exterior is touched.

Inherited from the original:

* one plate spanning the whole Thumb cluster, no per-button parts
* constant nominal thickness ≈ 2 mm
* outer face rides ~1.2 mm off the shell inner surface
* crosses the split seam, captured by shell closure

## 2. Construction — exact booleans only

The outer face is derived from the frozen shell itself, so it is conformal by
construction rather than by fitting.

```text
S_a  = frozen shell translated inward along -n by 1.20
S_b  = frozen shell translated inward along -n by 1.20 + 2.40
band = S_b - S_a          -> the slab [wall_inner - 3.60, wall_inner - 1.20]
C01  = band  ∩  plan window
       - shell translated ±u, ±v by 1.20      (lateral standoff)
       - 9 control apertures swept on each control's own axis, +0.60 mm
       - keep-outs (SZH static + 25° moving, N1/N2 carrier, 3× M3), 0.50/1.00 mm
```

Four earlier constructions were tried and rejected **on evidence**, recorded so
they are not retried:

| attempt | result |
|---|---|
| `Shape.offset_3d(1.2)` on the shell crop | OCC `offset Error` |
| `blank − dilate(shell, r)` and pick the cavity | the blank also contains the air *outside* the grip (connected through the Thumb openings), so the "cavity" was 74,591 mm³ of mixed inside/outside air and the skin came out on the blank's top face |
| `c1 − c2` (nested erosions) | `Null TopoDS_Shape` — c1 and c2 share the blank's own faces exactly |
| explicit 7-copy dilation fuse | did not finish in 10 minutes |

## 3. Result

| metric | C01 | ORIGINAL law | CURRENT |
|---|---:|---:|---:|
| solids | **1** | 1 | 1 |
| volume | 3,374.98 mm³ | 5,899.53 mm³ | 5,899.53 mm³ |
| B-rep faces | 291 | 85 | 85 |
| **conformal gap p25 / p50 / p75** | **+1.176 / +1.196 / +1.201 mm** | +0.829 / +1.292 / +1.500 | +5.0 / **+9.027** / — |
| gap min / max | +0.163 / +3.595 mm | −0.022 / +4.789 | −28.5 / +14.8 |
| **intersection with frozen shell** | **0.000000 mm³** | (4 columns) | 217.84 mm³ (docs/54) |
| thickness p05 / p50 / p95 | 1.193 / 2.400 / 2.411 mm | 1.626 / 2.004 / 2.026 | same as original |
| columns below 1.20 mm wall | 282 of 5,603 (5.03 %) | — | — |
| keep-out residual | **0.000000 mm³ for every item** | — | — |

Material removed by each stage:

| stage | mm³ |
|---|---:|
| lateral standoff | 10.70 → 0.00 intersection |
| apertures T1…T8 | 49.2 / 156.6 / 46.1 / 122.7 / 81.9 / 118.7 / 199.8 / 199.5 |
| aperture joystick | 34.7 |
| SZH knob keep-out | 174.7 |
| SZH 25° moving envelope | 223.8 |
| N1/N2 carrier, 3× M3 screws | 0.00 (no contention at this depth) |

## 4. Checklist (brief §18)

| item | result |
|---|---|
| frozen exterior changed | **NO** — 0 production writes; C01 ∩ shell = 0.000000 mm³ |
| joystick centre / axis preserved | YES — C01 derives from `DATUM_P`, never moves it |
| joystick static envelope | clear, 0.50 mm |
| joystick 25° moving envelope | clear, 0.50 mm (envelope is PROVISIONAL) |
| shaft / PCB / potentiometer clearance | not resolved by C01 — see §5 |
| N1/N2 external centre + press axis | untouched |
| N1/N2 harness keep-out | respected, residual 0.000000 mm³ |
| shell-inner conformity | **restored**: median +1.196 mm vs original +1.292 mm |
| unwanted penetration | 0.000000 mm³ |
| structural continuity | single solid, 1 piece |
| wall thickness | p50 2.400 mm; 5.03 % of columns below 1.20 mm, all at the plan boundary and aperture edges |
| load-transfer region | present — gap min 0.163 mm, comparable to the original p01 of 0.123 mm |
| wiring | not addressed |
| assembly / insertion | not addressed |
| FDM manufacturability | nominal 2.40 mm ≥ preferred 1.60 mm; boundary slivers must be trimmed before printing |

## 5. What C01 deliberately does NOT do

**Button seats are not generated.** Two upstream items must close first:

1. the Thumb switch is still an open question in `CLAUDE.md` §3 (`PushBtn` vs
   ITS-1105), so no seat pocket dimension is defensible;
2. A09 shows the frozen exterior currently gives T2 / T7 / T8 **0.0 %** clear
   path and T4 / T6 ≤ 3.9 %, so no seat height could be validated even if the
   switch were chosen. Building seats now would be inventing numbers.

**The SZH mount is not generated.** §6 of `KEEPOUT_DEFINITION.md`: the SZH PCB
plane is at n ≈ −11.5 to −13.1 while the Thumb wall inner surface is at n ≈ +11
to +14, and the opposite wall inner surface is at n ≈ −12.9. A plate sitting
1.2 mm under the Thumb wall is ~23 mm away from where the joystick PCB has to be.
The original single-plate architecture worked because HW504 needed only 12.25 mm
below the pivot. That is a genuine architecture question for C02, not something
to bolt onto C01.

## 6. Verdict

```text
C01 CONFORMAL SUBSTRATE  = PROMISING
    conformity restored to the original design law, exact, single solid,
    zero interference, all keep-outs respected

C01 AS A COMPLETE THUMB INNER HOUSING = INCOMPLETE BY DESIGN
    seats and joystick mount deferred on stated upstream blockers
```
