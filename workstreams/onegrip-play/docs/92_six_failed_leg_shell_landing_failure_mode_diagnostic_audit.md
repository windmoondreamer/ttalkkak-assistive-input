# 92 — Six failed-leg shell-landing failure-mode diagnostic audit

## Authority and scope

- Latest rescue authority: `docs/91` and its exact best-failure evidence.
- Scope: only N2 +U/+V/-V, I3 +U/-U, and I4 +U.
- Mode: **failure classification and measurement only**. No endpoint optimization, no slot, shell, harness, or assembly solution was generated.
- Frozen controls: original detailed switch orientation, four edge roots, existing 26/32 viable legs, N3 +V rescue, shell halves, exterior, apertures, seam, and production files.
- Production modification count: **0**.

## Required headline

```text
6 failed-leg diagnostic result:

NO-USABLE-LAND = N2 +U, I3 +U
MICRO/SMALL-THICKNESS = N2 -V, I3 -U
MAJOR-LOCAL-THICKNESS = NONE
NONLOCAL/ARCHITECTURE-LEVEL = N2 +V, I4 +U
```

## Group A — footprint occupancy and nearest land

The nearest-land scan is measurement-only. It probes the unchanged BRep with a straight-W 1.90 x 1.60 mm rectangular footprint, first at 0.25 mm spacing and then at 0.05 mm refinement. A usable land must have 9/9 inner/outer pairs and leave at least 1.20 mm after a 1.20 mm common-depth blind slot. It does not generate a moved slot.

| Button | leg | owner footprint | missing | missing-sample occupancy | nearest usable owner shift (mm) | assigned side kept | nearest usable opposite-half shift (mm) | classification |
|---|---:|---:|---:|---|---:|---:|---:|---|
| N2 | +U | 0/9 (0.0%) | 9/9 (100.0%) | {"opposite shell half": 3, "button-opening void": 6} | N/A | FALSE | 1.050000 | no usable land / incomplete footprint |
| I3 | +U | 5/9 (55.6%) | 4/9 (44.4%) | {"owning-shell material": 5, "button-opening void": 4} | 4.550000 | FALSE | 5.008992 | no usable land / incomplete footprint |

## Group B — exact docs/91 thickness map

The slot floor is the docs/91 common floor: deepest inner hit + 1.20 mm. The reinforcement footprint estimate is deliberately minimal and diagnostic: full 1.90 x 1.60 mm footprint plus 0.60 mm margin on all sides = 3.10 x 2.80 mm (8.68 mm²). It is not a proposed part or shell edit.

| Button | leg | shell min/max/mean (mm) | min remaining (mm) | inner-depth span (mm) | <0.50-mm slivers | failure geometry | inward add (mm) | min patch (mm) | add volume (mm³) | class |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| N2 | +V | 0.031925 / 3.174220 / 2.176108 | -1.239956 | 2.929729 | 3/9 | footprint straddles an opening/shell edge; short hit pairs are grazing shell slivers | 2.439956 | 3.10 x 2.80 | 21.179 | D |
| N2 | -V | 2.376585 / 3.196912 / 2.910653 | 1.079642 | 0.473205 | 0/9 | continuous local wall; common-floor curvature/thickness deficit | 0.120358 | 3.10 x 2.80 | 1.045 | B |
| I3 | -U | 2.319667 / 3.055058 / 2.956788 | 1.119667 | 0.706884 | 0/9 | continuous local wall; common-floor curvature/thickness deficit | 0.080333 | 3.10 x 2.80 | 0.697 | B |
| I4 | +U | 0.020469 / 3.050970 / 1.454295 | -3.329115 | 3.300190 | 3/9 | footprint straddles an opening/shell edge; short hit pairs are grazing shell slivers | 4.529115 | 3.10 x 2.80 | 39.313 | D |

## Leg-by-leg judgment

- **N2 +U: A** — no usable land / incomplete footprint; CONDITIONAL ONLY: the straight member is structurally direct, but the current endpoint has no continuous reaction land.
- **N2 +V: D** — opening/edge-straddling or architecture-level landing; CONDITIONAL ONLY: the straight member is structurally direct, but the current endpoint has no continuous reaction land.
- **N2 -V: B** — micro/small local shell-thickness deficit; YES, conditional on sufficient continuous shell material; the straight leg axis itself is not the failure.
- **I3 +U: A** — no usable land / incomplete footprint; CONDITIONAL ONLY: the straight member is structurally direct, but the current endpoint has no continuous reaction land.
- **I3 -U: B** — micro/small local shell-thickness deficit; YES, conditional on sufficient continuous shell material; the straight leg axis itself is not the failure.
- **I4 +U: D** — opening/edge-straddling or architecture-level landing; CONDITIONAL ONLY: the straight member is structurally direct, but the current endpoint has no continuous reaction land.

## Four required decisions

1. **Thickness-only future candidates:** N2 -V and I3 -U. Their continuous 9/9 wall needs only 0.120359 mm and 0.080334 mm additional inward thickness respectively. This is a diagnostic classification, not authorization to modify the shell.
2. **Root/target research:** N2 +U and I3 +U are the only no-land cases, but repeating the same bounded docs/91 side-region search is not justified: docs/91 exhausted that search. Any future endpoint study must first relax or replace the same-side/edge reaction architecture. N2 +V and I4 +U are not endpoint-placement-only failures.
3. **Existing four-edge architecture without exterior redesign:** only the two Class-B legs have a credible reinforcement-only path in principle. The audit does not claim a production solution.
4. **Architecture issue:** the strict Class-D legs are N2 +V and I4 +U because their footprints straddle an opening/shell edge and use grazing shell slivers rather than one continuous wall. The two Class-A legs are also architecture constraints if their frozen assigned-side identity remains mandatory.

## Cross-sections

One exact diagnostic section was generated per failed leg (six total). Red is the failed docs/91 footprint envelope, grey is the owning shell, cyan is the opposite shell half when intersected, and yellow is the frozen failed-leg axis. These are evidence views, not solution geometry.

- `renders/six_failed_leg_shell_landing_failure_mode_diagnostic_audit/01_n2_plus_usection.png`
- `renders/six_failed_leg_shell_landing_failure_mode_diagnostic_audit/02_n2_plus_vsection.png`
- `renders/six_failed_leg_shell_landing_failure_mode_diagnostic_audit/03_n2_minus_vsection.png`
- `renders/six_failed_leg_shell_landing_failure_mode_diagnostic_audit/04_i3_plus_usection.png`
- `renders/six_failed_leg_shell_landing_failure_mode_diagnostic_audit/05_i3_minus_usection.png`
- `renders/six_failed_leg_shell_landing_failure_mode_diagnostic_audit/06_i4_plus_usection.png`

## Preservation

- Protected-file hash equality: **TRUE**.
- Protected files checked: 206.
- New STEP solution artifacts: **0**.
- Shell/exterior/harness/assembly modifications: **0**.
