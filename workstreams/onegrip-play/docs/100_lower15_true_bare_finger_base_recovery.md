# 100 — Exact LOWER15 + true-bare Finger shell recovery

## Result

```text
LOWER15 + TRUE-BARE FINGER BASE RECOVERY RESULT:

TRUE BARE COMPLETE V2 BASE = CONFIRMED

LOWER15 THUMB PRESERVED = YES
THUMB JOY + T1–T8 PRESERVED = YES

FINGER BARE REGIONS = 8/8
LEGACY LARGE FINGER OPENINGS = 0/8
LEGACY INTERNAL FINGER HOLDERS = 0/8

JaD/JfD SPLIT CHANGED = NO
MANUAL SURFACE RECONSTRUCTION USED = NO
ACTUATOR HOLES CREATED = 0
SWITCH SOCKETS CREATED = 0
```

Exact Onshape state/workspace/version used = independent public audit copy
`OneGrip_Play_V1 - LOWER15 TRUE BARE FINGER RECOVERY AUDIT` / document `833105eac3cd2f21ce45b5b6` /
workspace `Main` `7a525ad6dbfc948540a7b602` / element `eff7a35a10ea134186c35d06`,
copied exactly from immutable source version `THUMB_LOWER15_HOUSING_V1`
`50dfe4e752e447375b95493a`.

Finger features suppressed = **78** total
(77 newly suppressed in the audit copy plus the already-suppressed stale
`INDEX_switch_pockets`).  LOWER15 features retained =
`Fu0ngE5n5Mmnjfd_25` and `F54ht3HFsoh1AxM_25`; both computed, unsuppressed, and error-free.
Onshape `:errors` result = **0 / 202**.  Part count changed 30 → **12**.

## Feature dependency classification

| Feature group | Count | Affects Finger? | Affects Thumb? | Affects JaD/JfD split? | Safe/decision |
|---|---:|---|---|---|---|
| `oneGripIndexButtons` | 4 | YES | NO | NO | SUPPRESS |
| `idxHolderAtomic` | 34 | YES | NO | NO | SUPPRESS |
| `assignVariable` | 6 | YES | NO | NO | SUPPRESS WITH CONTIGUOUS FINGER RANGE |
| `oneGripIndexRetainer` | 12 | YES | NO | NO | SUPPRESS |
| `oneGripI4Retainer` | 6 | YES | NO | NO | SUPPRESS |
| `its1105Index` | 12 | YES | NO | NO | SUPPRESS |
| `its1105Middle` | 4 | YES | NO | NO | SUPPRESS |

All suppressed rows are earlier than the two retained LOWER15 features.  A filtered-tree
selection was rejected after its elided placeholder caused an Onshape UI error; no geometry
changed in that attempt.  The successful suppression used the actual unfiltered continuous
feature range `INDEX_construction → ITS1105_M4_actual` in the independent copy.

## Finger bare-region gate

| Button | Large opening absent | Exterior skin continuous | Internal holder absent | Boss/wall absent | Bare | Skin coverage | Center-axis W hits (mm) |
|---|---|---|---|---|---|---:|---|
| N1 | YES | YES | YES | YES | YES | 1.000 | [0.06947843615188454, 3.0694350694757553] |
| N2 | YES | YES | YES | YES | YES | 1.000 | [0.0063100869673178295, 3.0067819498364727] |
| I2 | YES | YES | YES | YES | YES | 1.000 | [0.0, 3.0035197524701402] |
| I3 | YES | YES | YES | YES | YES | 1.000 | [5.329070518200751e-15, 3.003330723220806] |
| I4 | YES | YES | YES | YES | YES | 1.000 | [1.7763568394002505e-15, 3.000002284808609] |
| M3 | YES | YES | YES | YES | YES | 1.000 | [0.0, 2.999864104699615] |
| M4 | YES | YES | YES | YES | YES | 1.000 | [0.0, 3.005629398490967] |
| N3 | YES | YES | YES | YES | YES | 1.000 | [0.0014472392837880932, 3.016360120223176] |

Skin coverage is an exact BRep ray audit over 37 points per button within the frozen local
button patch.  The center/axis values are not recovered from legacy geometry; they are kept
separately in `build123d_workbench/out/lower15_true_bare_finger_base/finger_button_frozen_datums.json`.  N3 local material differs from historical Start due
to the retained LOWER15 Thumb lineage, not a Finger feature; feature-history provenance and
continuous local skin are the authority there.

## LOWER15 Thumb exact gate

- retained Onshape LOWER15 features: **unchanged / computed / unsuppressed / error-free**
- immutable 0.15 mm opening-grid equality: **9/9 exact**
- JOY/T1–T8 open area, centroid, boundary-point count, axis-column state, pitch, and wall band:
  **all numeric deltas = 0**
- broad legacy Thumb-mask symmetric difference (diagnostic only): JaD
  **10892.059494 mm³**,
  JfD **12054.712733 mm³**.
  This rectangular mask contains suppressed Finger-history geometry and is therefore not a
  valid Thumb-only equality gate for the recovered bare shell.

| Thumb control | Exists | Through/open | Position unchanged |
|---|---|---|---|
| JOY | YES | YES | YES |
| T1 | YES | YES | YES |
| T2 | YES | YES | YES |
| T3 | YES | YES | YES |
| T4 | YES | YES | YES |
| T5 | YES | YES | YES |
| T6 | YES | YES | YES |
| T7 | YES | YES | YES |
| T8 | YES | YES | YES |

## Solid and split gate

| Check | JaD | JfD |
|---|---:|---:|
| imported STEP valid / solids | True / 1 | True / 1 |
| faces | 62 | 60 |
| volume (mm³) | 46574.937385 | 47848.523386 |
| STEP reimport valid / solids | True / 1 | True / 1 |

JaD/JfD remain two independent one-solid STEP bodies.  Their common-volume check is
**0.000000000 mm³** and no transform, split edit, or reconstructed
surface was applied.

## Outputs

- `build123d_workbench/out/lower15_true_bare_finger_base/LOWER15_TRUE_BARE_FINGER_JaD.step`
- `build123d_workbench/out/lower15_true_bare_finger_base/LOWER15_TRUE_BARE_FINGER_JfD.step`
- `build123d_workbench/out/lower15_true_bare_finger_base/LOWER15_TRUE_BARE_FINGER_COMBINED_REFERENCE.step`
- `build123d_workbench/out/lower15_true_bare_finger_base/finger_button_frozen_datums.json`
- `build123d_workbench/out/lower15_true_bare_finger_base/onshape_recovery_feature_manifest.json`
- `build123d_workbench/out/lower15_true_bare_finger_base/lower15_true_bare_finger_base_validation.json`
- `renders/lower15_true_bare_finger_base/01_recovered_jad_exterior.png`
- `renders/lower15_true_bare_finger_base/02_recovered_jfd_exterior.png`
- `renders/lower15_true_bare_finger_base/03_assembled_recovered_shell_exterior.png`
- `renders/lower15_true_bare_finger_base/04_all8_bare_finger_regions_exterior.png`
- `renders/lower15_true_bare_finger_base/05_all8_bare_finger_regions_interior.png`
- `renders/lower15_true_bare_finger_base/06_i2_bare_cross_section.png`
- `renders/lower15_true_bare_finger_base/07_lower15_thumb_exterior_openings.png`
- `renders/lower15_true_bare_finger_base/08_jad_jfd_vertical_seam.png`

Existing production/source overwrite = **0**.  Original Onshape document/version mutation =
**0**.  All source hashes listed in the validation JSON remained unchanged.

Generated: 2026-08-25T10:28:08.941628+00:00
