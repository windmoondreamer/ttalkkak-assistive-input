# REV_G — Backplate-driven Thumb freeze test

Date 2026-08-25 · local build123d / OCCT · Onshape API 0 · production writes 0
Shell authority: exact Onshape `THUMB_LOWER15_HOUSING_V1` export.
REV_A…REV_F read-only. Backplate never deformed — 6-DOF rigid search only.

---

## 1. Headline

The Backplate-driven pose **returns the Thumb cluster to where it started**.

| control | moves from OLD layout | lands from ORIGINAL pre-lowering layout |
|---|---:|---:|
| JOY | 25.264 mm | 2.482 mm |
| T1 | 25.110 | 0.852 |
| T2 | 25.099 | 0.943 |
| T3 | 24.916 | 0.676 |
| T4 | 25.205 | 1.020 |
| T5 | 25.004 | 0.734 |
| T6 | 24.994 | 0.868 |
| T7 | 25.287 | 1.259 |
| T8 | 25.134 | 1.151 |
| **mean** | **25.113 mm** | **1.109 mm** |

Net displacement from the ORIGINAL position after solving: **1.209 mm**, against
a `THUMB_DELTA` magnitude of 24.312 mm.

```text
THE SOLVE UNDOES 95.0 % OF THE APPROVED LOWERING
```

That is not a numerical accident. The original Backplate conforms to the grip
shell only where it was designed to sit. Letting it drive the layout necessarily
drags the Thumb cluster back up the grip.

## 2. Trade-off sweep — is there a usable middle ground?

`f` = fraction of the approved lowering retained. At each `f` the rotation and
±3 mm of tangential slack were optimised against the same objective.

| f | lowering kept | gap p25 | p50 | p75 | general in 0.8–1.6 | LEFT contact | RIGHT contact | interference |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.00 | 24.31 mm | 6.572 | 8.349 | 10.742 | 0.3 % | 0.41 | 2.89 | 37.50 |
| 0.90 | 21.88 | 5.021 | 6.596 | 7.743 | 0.7 % | 3.85 | 3.02 | 59.08 |
| 0.80 | 19.45 | 4.574 | 5.610 | 6.178 | 0.6 % | 2.47 | 2.61 | 41.21 |
| 0.70 | 17.02 | 3.387 | 4.746 | 5.788 | 0.7 % | 5.36 | 3.57 | 58.66 |
| 0.60 | 14.59 | 2.649 | 3.819 | 4.717 | 2.3 % | 6.19 | 5.63 | 61.69 |
| 0.50 | 12.16 | 2.058 | 3.030 | 3.893 | 5.6 % | 9.22 | 8.25 | 71.72 |
| 0.35 | 8.51 | 1.381 | 1.904 | 2.261 | 21.2 % | 7.29 | 6.19 | 59.35 |
| 0.20 | 4.86 | 0.434 | 0.721 | 0.964 | 21.5 % | 43.69 | 35.50 | 143.17 |
| 0.10 | 2.43 | 0.554 | 0.977 | 1.365 | **49.2 %** | 59.91 | 9.66 | 128.76 |
| 0.00 | 0.00 | 0.395 | 0.710 | 0.975 | 19.4 % | 35.61 | 18.16 | 191.92 |

**Reference — the original Backplate against its OWN shell, measured through the
identical pipeline:** gap p25/p50/p75 = **0.853 / 1.281 / 1.505**, general
in-band **64.1 %**, LEFT contact **66.40 mm²**, RIGHT **15.79 mm²**,
interference **2.47 mm²**.

The curve is monotone. Nothing at f ≥ 0.35 gets the general clearance band above
21 %, and everything at f ≤ 0.20 costs 129–192 mm² of interference — fifty to
eighty times the reference. There is no usable middle ground.

### Pipeline control test

Before trusting any of the above, the same code was run on the case whose answer
is already known — the original Backplate against the original shell. It
reproduced gap p25/p50/p75 = 0.853 / 1.281 / 1.505 against the independently
measured 0.796 / 1.230 / 1.443, and LEFT 66.40 vs 71.69. The pipeline is sound,
so the failure above is geometric, not instrumental.

## 3. Why it fails even at f = 0

Returning the Backplate to the original position still gives 191.92 mm² of
interference and only 19.4 % of the plate in the 0.8–1.6 mm band, against 2.47
and 64.1 % for the original pair.

The approved shell is the **lowered** design. Onshape rebuilt the Thumb region:
the old openings are closed and the interior follows the new control placement.
The cavity at the old location is therefore no longer the cavity the Backplate
was designed against. So the original Backplate matches the approved shell
**nowhere** — not lowered, not original, not in between.

## 4. Solved pose, recorded for information only

```text
rotation      (-1.5185, -0.4253, -0.3515) deg
translation   (-0.0003, -12.1401, +22.2040) mm   relative to THUMB_DELTA
world 4x4     [ 0.999954  0.006330 -0.007258   0.478908]
              [-0.006135  0.999629  0.026544  -1.217174]
              [ 0.007423 -0.026498  0.999621   0.727649]
              [ 0        0         0           1       ]
```

At that pose: gap p25/p50/p75 = 0.178 / 0.316 / 0.654 mm, LEFT contact
85.87 mm², RIGHT 36.08 mm² — both above the original targets — but **213.97 mm²
interferes**, only 66.4 % of the plate has shell above it, and the general
clearance collapses to 2.6 % in band. It buys contact by pressing the whole
plate against the shell, which §6 explicitly rules out.

New control centres and axes are in `01_pose/g01_solve_pose.json` under
`newControls`. They are **not** a freeze proposal.

## 5. Gates

| gate | result |
|---|---|
| one rigid pose | found, but it undoes 95.0 % of the approved lowering |
| original thickness retained | yes — never deformed |
| shell relation ≈ original law | **FAIL** — in-band ≤ 49.2 % at any f, vs 64.1 % reference |
| load transfer LEFT / RIGHT | reachable only at f ≤ 0.20, i.e. with the lowering abandoned |
| interference trimmable | **FAIL** — 128.76–191.92 mm² where contact is achieved, vs 2.47 reference |
| new JOY / T1–T8 openings | not generated — the pose gate failed first |
| N1/N2, harness, SZH | not evaluated — gated behind the pose |

Per §17, `NEW_THUMB_HARD_FREEZE_SPEC.md` was **not** produced: the structural
gates did not pass, so there is nothing to freeze.

## 6. Renders

`08_renders/` — matched cameras.

```text
01_EXTERNAL_OLD_layout.png              approved shell + OLD controls
02_EXTERNAL_NEW_layout.png              approved shell + Backplate-driven controls
03_EXTERNAL_OVERLAY.png                 both, same camera   <- the decisive image
04_SECTION_backplate_OLD_pose.png       u = 0, gap 8.349 mm, no contact
05_SECTION_backplate_NEW_pose.png       u = 0, gap 0.316 mm, 213.97 mm2 interference
06_INTERNAL_transparent_both_poses.png  both poses inside the shell
```

`03_EXTERNAL_OVERLAY.png` shows it plainly: the Backplate-driven cluster sits
about 25 mm higher up the grip, with the joystick near the top of the Thumb face.

## 7. Verdict

```text
BACKPLATE-DRIVEN THUMB FREEZE FAILED — DO NOT REPLACE OLD FREEZE
```

Two independent reasons, either sufficient:

1. **It cancels the design.** The best Backplate-driven pose puts the controls
   1.109 mm from the original pre-lowering layout — 95.0 % of the approved
   24.312 mm lowering undone. Adopting it would replace the maximum-lowered
   Thumb with the original Thumb.
2. **Even then the fit is poor.** Against the approved shell the original
   Backplate never reproduces its own design law. Best case is 49.2 % of the
   plate in the 0.8–1.6 mm band with 128.76 mm² of interference, against 64.1 %
   and 2.47 mm² for the original pair.

The old JOY/T1–T8 freeze should stand. If the intent behind this direction was
to recover the original load path, the blocker is not the opening layout — it is
that the approved lowered cavity has a different shape from the one the original
Backplate was built for. That is addressed by designing an inner housing for
this cavity, not by relocating the controls to suit an old part.

Stopped. No production apply, no shell modification, no SZH carrier, no N1/N2
change, and no new hard-freeze specification issued.
