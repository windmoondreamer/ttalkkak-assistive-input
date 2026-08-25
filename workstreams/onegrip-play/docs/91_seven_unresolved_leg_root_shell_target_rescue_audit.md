# 91 — 7-unresolved-leg root / shell-target placement rescue audit

MODE = **LOCAL 7-LEG RESCUE / DOCS90 RESOLVED LEGS FROZEN / PRODUCTION 0**

## Required unresolved-leg table

| Button | Leg | docs/90 status | Root shift | Shell-target shift | Final tilt | Full footprint | Min shell | Result |
|---|---|---|---:|---:|---:|---|---:|---|
| N2 | +U | unresolved ≤30° | N/A | N/A | N/A | NO | N/A | FAIL — NO USABLE SIDE-REGION SHELL LANDING |
| N2 | +V | unresolved ≤30° | N/A | N/A | N/A | NO | N/A | FAIL — NO USABLE SIDE-REGION SHELL LANDING |
| N2 | -V | unresolved ≤30° | N/A | N/A | N/A | NO | N/A | FAIL — NO USABLE SIDE-REGION SHELL LANDING |
| I3 | +U | unresolved ≤30° | N/A | N/A | N/A | NO | N/A | FAIL — NO USABLE SIDE-REGION SHELL LANDING |
| I3 | -U | unresolved ≤30° | N/A | N/A | N/A | NO | N/A | FAIL — NO USABLE SIDE-REGION SHELL LANDING |
| I4 | +U | unresolved ≤30° | N/A | N/A | N/A | NO | N/A | FAIL — NO USABLE SIDE-REGION SHELL LANDING |
| N3 | +V | unresolved ≤30° | 0.400 mm | 1.993 mm | 14.601° | YES / 100% | 1.201986 | RESCUED |

## Required button summary

| Button | docs/90 | New result | Max tilt | Min clearance | Min shell | Rear assembly |
|---|---|---|---:|---:|---:|---|
| N2 | FAIL | FAIL — NO USABLE SIDE-REGION SHELL LANDING | N/A | N/A | N/A | NOT RUN — INCOMPLETE FOUR-LEG SET |
| I3 | FAIL | FAIL — NO USABLE SIDE-REGION SHELL LANDING | N/A | N/A | N/A | NOT RUN — INCOMPLETE FOUR-LEG SET |
| I4 | FAIL | FAIL — NO USABLE SIDE-REGION SHELL LANDING | N/A | N/A | N/A | NOT RUN — INCOMPLETE FOUR-LEG SET |
| N3 | FAIL | RESCUED | 19.000° | 0.158116 | 1.201986 | PASS |

## Numeric result

- RESCUED LEGS = **1/7**
- STILL UNRESOLVED = **6/7**
- rescued buttons = **1/4**
- legs requiring >30° = **0**
- maximum selected tilt = **14.601°**
- corner-post solutions = **0**
- shell/exterior redesigns = **0**
- bounded exact candidate evaluations = **1354**, global optimizer = **NO**

## Unresolved failure evidence

| Button | leg | shell targets | exact ≤30° | exact 30–45° | best footprint | limiting reason | best remaining shell |
|---|---|---:|---:|---:|---:|---|---:|
| N2 | +U | 0 | 0 | 0 | N/A | NO_SHELL_TARGET | N/A |
| N2 | +V | 56 | 160 | 120 | 9/9 | INSUFFICIENT_REMAINING_SHELL | -1.239956 |
| N2 | -V | 56 | 162 | 118 | 9/9 | INSUFFICIENT_REMAINING_SHELL | 1.079642 |
| I3 | +U | 32 | 150 | 10 | 1/9 | INCOMPLETE_SLOT_FOOTPRINT | N/A |
| I3 | -U | 78 | 371 | 19 | 9/9 | INSUFFICIENT_REMAINING_SHELL | 1.119667 |
| I4 | +U | 32 | 153 | 7 | 9/9 | INSUFFICIENT_REMAINING_SHELL | -3.329115 |

## Search policy and structural proof

Every target starts from an exact-W shell material map on its assigned side. Reported shell-target shift is the
local UV displacement from the final root's straight-W projection to the selected slot floor. Root tangent shift is bounded to
±0.40 mm, leaving shared cross width ≥1.20 mm. Endpoint tangent coordinate is bounded to ±3.00 mm and the
radial coordinate remains on the assigned side; no candidate uses a corner-only root. Candidates ≤30° are
exhausted first. Only unresolved legs enter the 30–45° diagnostic band.

Final candidates use the original 3,530-facet PushBtn body/T1–T4/corner/bottom authority and the measured
D3.35×2.44 actuator. A rescue requires 9/9 footprint support, remaining shell ≥1.20 mm, one fused valid solid,
STEP reimport=1 solid, root neck/effective FDM section ≥1.20 mm, positive volumetric roots and 5-state rear
assembly PASS. Existing docs/90 resolved legs are reconstructed from their frozen root/floor/direction data.

## ALL-8 status

ALL-8 COMPLETE HARNESS SET AVAILABLE = **NO**.
The ALL-8 build gate was not opened because at least one FAIL button remained unresolved.

M3–M4 0.032405 mm was not optimized. New candidates were checked only for added penetration against frozen
neighbor harnesses.

## Renders / outputs / freeze

- [01_all7_unresolved_locations_overview.png](../renders/seven_unresolved_leg_root_shell_target_rescue_audit/01_all7_unresolved_locations_overview.png)
- [02_n2_rescue_geometry.png](../renders/seven_unresolved_leg_root_shell_target_rescue_audit/02_n2_rescue_geometry.png)
- [03_i3_rescue_geometry.png](../renders/seven_unresolved_leg_root_shell_target_rescue_audit/03_i3_rescue_geometry.png)
- [04_i4_rescue_geometry.png](../renders/seven_unresolved_leg_root_shell_target_rescue_audit/04_i4_rescue_geometry.png)
- [05_n3_rescue_geometry.png](../renders/seven_unresolved_leg_root_shell_target_rescue_audit/05_n3_rescue_geometry.png)
- [06_tightest_rescued_clearance.png](../renders/seven_unresolved_leg_root_shell_target_rescue_audit/06_tightest_rescued_clearance.png)
- [07_worst_shell_landing.png](../renders/seven_unresolved_leg_root_shell_target_rescue_audit/07_worst_shell_landing.png)

- `build123d_workbench/out/seven_unresolved_leg_root_shell_target_rescue_audit/seven_unresolved_leg_root_shell_target_rescue_audit.json`
- `build123d_workbench/out/seven_unresolved_leg_root_shell_target_rescue_audit/N3_RESCUED_FOUR_EDGE_HARNESS_AUDIT_ONLY.step`


production modification=0; frozen shell modification=0; button pose modification=0; I2 authority modification=0;
physical coupon=0. Protected docs/90 and prior authority hashes preserved: **True**.
STOP after rescue classification.
