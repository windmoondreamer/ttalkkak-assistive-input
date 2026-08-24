# 81 — I2 parallel-W four-edge-leg revalidation audit

MODE = **AUDIT-ONLY / I2 / FROZEN SWITCH ORIENTATION + FOUR ROOTS / LEG TILT = 0**

FINAL VERDICT = **C — FIXED-ROOT 90-DEGREE PARALLEL-W LEVEL-0 IS IMPOSSIBLE ON THE CURRENT FROZEN I2 SHELL**

## 1. Direct answer

The current docs/80 I2 candidate is **not** normal to the harness U-V plane and its four legs are **not**
mutually parallel.  Their off-W angles are 11.866° to 22.653°; the maximum pairwise direction difference is
**36.870°**.

The requested Level-0 rebase was therefore tested without changing the frozen switch datum or any root:
all four directions were set exactly to +W, then exactly to -W, with only individual probe/floor length allowed.
Neither common direction produces four valid direct-shell blind-slot legs.  Consequently this audit exports
**diagnostic probes only, not a Level-0 candidate**.

## 2. Current direction check

Tolerance for the explicit exact-direction test: **0.010°**.

| leg | stored local direction U,V,W | angle to +W | angle to U-V plane | exactly 90° to U-V |
|---|---|---:|---:|---|
| +U | 0.183236, 0.276583, 0.943359 | 19.376° | 70.624° | False |
| -U | -0.385171, 0.000000, 0.922845 | 22.654° | 67.346° | False |
| +V | 0.000000, 0.205641, 0.978627 | 11.867° | 78.133° | False |
| -V | 0.000000, -0.233445, 0.972370 | 13.500° | 76.500° | False |

All normal: **False**.  All mutually parallel:
**False**.

## 3. Fixed-root exact shell proof

Each slot footprint is 3.00 mm tangent by 1.60 mm (+U) or 2.00 mm (others), including 0.20 mm clearance per
side.  It was tested with a 3×3 exact B-rep ray grid.  A valid blind slot requires all 9 rays to have an
inner/outer pair and a common planar floor that supplies 1.20 mm engagement while retaining at least 1.20 mm
shell beyond the floor.

| direction | leg | center shell pairs | footprint pairs | paired shell thickness mm | effective minimum shell remaining mm | pass | numeric reason |
|---|---|---:|---:|---:|---:|---|---|
| +W | +U | 0 | 3/9 | 3.040…3.071 | 0.000 | False | NO CENTER INNER/OUTER SHELL PAIR |
| +W | -U | 0 | 4/9 | 3.190…3.328 | 0.000 | False | NO CENTER INNER/OUTER SHELL PAIR |
| +W | +V | 1 | 5/9 | 3.007…3.050 | 0.000 | False | SLOT FOOTPRINT PARTLY OVER APERTURE (5/9 supported) |
| +W | -V | 0 | 4/9 | 3.009…3.059 | 0.000 | False | NO CENTER INNER/OUTER SHELL PAIR |
| -W | +U | 0 | 0/9 | N/A | 0.000 | False | NO CENTER INNER/OUTER SHELL PAIR |
| -W | -U | 0 | 0/9 | N/A | 0.000 | False | NO CENTER INNER/OUTER SHELL PAIR |
| -W | +V | 2 | 9/9 | 2.404…5.933 | -1.149 | False | PLANAR FLOOR LEAVES -1.149 mm MINIMUM SHELL (< 1.20 mm) |
| -W | -V | 0 | 0/9 | N/A | 0.000 | False | NO CENTER INNER/OUTER SHELL PAIR |

An effective remainder of **0.000 mm** means at least one footprint ray has no shell inner/outer pair, so no
physical planar floor exists there; it is not a claim that a valid shell wall was measured as zero-thickness.

The +W option fails all four roots because 4–6 of the 9 footprint rays lie in the button aperture even where
parts of the rectangle reach shell material.  The -W option has no shell pair at +U, -U, or -V.  Its +V root
does reach a deeper shell region at all 9 points, but inner-face curvature forces a planar floor to
**8.837 mm**; the earliest
outer exit is closer than that floor, producing **-1.149 mm**
minimum remaining material.  It therefore breaks through rather than retaining 1.20 mm.

## 4. Collision and neighboring-clearance proof

These boxes use the frozen roots and exact ±W only.  Where no complete shell target exists, 12.00 mm is a
bounded search probe, not a proposed leg.  `uncut shell overlap` is the material a valid slot would have to
remove; terminal, pusher and neighbor penetration are true collision volumes.

| direction | leg | probe length mm | uncut shell overlap mm³ | terminal distance / penetration | pusher distance / penetration | nearest neighbor distance / penetration |
|---|---|---:|---:|---:|---:|---:|
| +W | +U | 12.000 | 1.644 | 0.620 / 0.000000 | 0.000 / 0.568336 | 0.309 / 0.000000 (I3) |
| +W | -U | 12.000 | 5.747 | 0.600 / 0.000000 | 0.000 / 0.400618 | 7.464 / 0.000000 (I3) |
| +W | +V | 7.619 | 2.648 | 1.729 / 0.000000 | 0.684 / 0.000000 | 3.234 / 0.000000 (I3) |
| +W | -V | 12.000 | 5.113 | 1.659 / 0.000000 | 0.000 / 0.450668 | 3.467 / 0.000000 (I3) |
| -W | +U | 12.000 | 0.000 | 0.600 / 0.000000 | 6.138 / 0.000000 | 0.000 / 0.003471 (I3) |
| -W | -U | 12.000 | 0.000 | 0.600 / 0.000000 | 6.746 / 0.000000 | 7.433 / 0.000000 (I3) |
| -W | +V | 8.837 | 10.124 | 1.736 / 0.000000 | 6.766 / 0.000000 | 3.161 / 0.000000 (I3) |
| -W | -V | 12.000 | 0.000 | 1.667 / 0.000000 | 6.741 / 0.000000 | 3.505 / 0.000000 (I3) |

Neighbor scope is the other seven frozen measured ITS body and actuator envelopes.  A zero distance is
interpreted together with penetration volume; zero penetration means tangent/contact without volumetric collision.
The shell-support failure above is decisive even when neighboring and mechanism clearances are positive.

## 5. Frozen authority and non-propagation

- switch center: `[-15.97116502911469, -26.20981698837403, 8.99880711855274]`;
- local +W / approved press axis: `[-0.43398514194613513, -0.7569241977430389, -0.48859252495412786]`;
- four roots: `{'+U': [3.74, 0.0, 0.0], '-U': [-4.04, 0.0, -0.6], '+V': [0.0, 4.175, -0.6], '-V': [0.0, -4.005, -0.6]}`;
- root change = 0; switch orientation change = 0; leg tilt used = 0;
- production modification = 0; shell boolean = 0; eight-button propagation = 0;
- docs/79, docs/80 and protected production artifacts hash-preserved: **True**.

## 6. Evidence renders

- [01_current_i2_direction_revalidation.png](../renders/i2_parallel_w_four_edge_leg_revalidation_audit/01_current_i2_direction_revalidation.png)
- [02_+w_parallel_fixed_root_probes.png](../renders/i2_parallel_w_four_edge_leg_revalidation_audit/02_+w_parallel_fixed_root_probes.png)
- [04_+w_footprint_36_ray_coverage.png](../renders/i2_parallel_w_four_edge_leg_revalidation_audit/04_+w_footprint_36_ray_coverage.png)
- [03_-w_parallel_fixed_root_probes.png](../renders/i2_parallel_w_four_edge_leg_revalidation_audit/03_-w_parallel_fixed_root_probes.png)
- [05_-w_footprint_36_ray_coverage.png](../renders/i2_parallel_w_four_edge_leg_revalidation_audit/05_-w_footprint_36_ray_coverage.png)
- [06_minus_w_plus_v_planar_floor_breakthrough.png](../renders/i2_parallel_w_four_edge_leg_revalidation_audit/06_minus_w_plus_v_planar_floor_breakthrough.png)

## 7. Outputs

- `build123d_workbench/out/i2_parallel_w_four_edge_leg_revalidation_audit/i2_parallel_w_four_edge_leg_revalidation_audit.json`
- `build123d_workbench/out/i2_parallel_w_four_edge_leg_revalidation_audit/I2_PLUS_W_PARALLEL_LEG_FEASIBILITY_PROBES_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_parallel_w_four_edge_leg_revalidation_audit/I2_MINUS_W_PARALLEL_LEG_FEASIBILITY_PROBES_AUDIT_ONLY.step`
- `docs/81_i2_parallel_w_four_edge_leg_revalidation_audit.md`

No parallel-leg candidate STEP was emitted because neither ±W family passes all four roots.
