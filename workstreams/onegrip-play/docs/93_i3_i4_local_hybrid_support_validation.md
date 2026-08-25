# 93 — I3 / I4 local hybrid support validation

```text
I3 / I4 hybrid-support result:

I4 = PASS
I3 = FAIL

I4 mechanical slots = 3/4
I4 local contact feet = 1/4

I3 mechanical slots = 3/4
I3 local contact feet = 1/4

REMOTE/THUMB-WALL SUPPORT USED = NO

7-BUTTON COMPLETE SET AVAILABLE = NO
```

## Required result table

| Button | Mechanical slots | Contact feet | Contact-foot side | Contact area (mm²) | Full-seat gap (mm) | Remote wall | Side identity | Min neck (mm) | Min effective (mm) | Min static clearance (mm) | Rear assembly | Adhesive dependency | Final class |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| I3 | 3 | 1 | +U | 2.080153 | 0.000000 | NO | YES | 1.300000 | 1.240615 | 0.000000 | FAIL | NO | FAIL — REAR ASSEMBLY IMPOSSIBLE |
| I4 | 3 | 1 | +U | 2.079980 | 0.000000 | NO | YES | 1.300000 | 1.280250 | 0.142461 | PASS | NO | PASS — HARDENING REQUIRED |

## Direct answers

- Does each contact foot carry normal press load by direct compression into local shell? **YES**. I3 foot reaction fraction = 0.256464; I4 = 0.254467 under the documented centered unit-load statics model.
- Does either solution depend on adhesive as the primary press-load structure? **NO**. Adhesive compressive strength is set to zero; direct leg/foot/shell contact still closes the load path.
- Did I3 -U require only genuinely micro-local shell thickening? **YES**.
- Did either leg leave its original local +U side region? **NO**.
- Did either solution reach any Thumb-related wall? **NO**. Remote/Thumb/opposite/neighbor wall search count = 0.

## I3 -U micro-thickening

```text
Original remaining shell = 1.119667 mm
Required minimum = 1.200000 mm
Added inward thickness = 0.150000 mm
Final effective remaining shell = 1.269667 mm
Reinforcement footprint = 3.100 x 2.800 mm
Added volume = 0.987792 mm³
Distance beyond slot footprint = 0.600 mm
Broad/nonlocal reinforcement = NO
```

The exact 0.080333 mm deficit receives a 0.150000 mm inward addition, leaving 0.069667 mm practical margin. The outer hit depths remain unchanged; no exterior surface was changed.

## Contact locality and seat

- I3 endpoint UV = `[4.5, 2.0]`, distance from original +U region = **2.065242 mm**, owner = **JfD**.
- I4 endpoint UV = `[4.5, -1.0]`, distance from original +U region = **1.124822 mm**, owner = **JaD**.
- Both: side identity YES; local finger-button shell region YES; remote wall NO; positive finite-area shell-matched contact YES; point/edge/tangent-only contact NO.
- Foot face versus local shell face angle = **0°** by exact shell-matched subtraction. Leg-axis versus local shell normal: I3 **15.334688°**, I4 **6.568671°**.

## Mechanical restraint, load path, and adhesive independence

Three non-collinear blind slots provide translation and rotation restraint. The +U contact completes the four-point support polygon. Both computed +U reaction fractions are positive, so normal press moves neither foot away from the shell. Glue is retention/anti-slip/anti-rattle only.

Load path: ORIGINAL detailed PushBtn body bottom → one-piece harness seat → three mechanically slotted legs + one straight +U compression leg/foot → each button's local shell inner surface.

## Manufacturing / assembly / static

- Both audit STEP artifacts reimport as one valid solid with connected components 1 and zero-thickness/tangent-only roots 0. I3 nevertheless fails the complete manufacturing system gate because its rear/static gates fail.
- Original detailed 3,530-facet PushBtn body, T1–T4, exact corner/bottom features, and measured D3.35 / 2.44 mm actuator were used for the final clearance and five-state verdicts.
- I4 rear states START / 25% / 50% / 75% / FULL SEAT pass with PushBtn motion 0, elastic deformation NO, unintended penetration 0, and contact only at FULL SEAT.
- I3 bounded complete-candidate screen: 13 evaluated; rear-entry PASS = 0; zero I2 penetration = 0; one-solid = 8; all-gate PASS = 0.
- The retained I3 diagnostic candidate contacts shell before FULL SEAT: intermediate shell penetration = 0.000140463 / 0.004949602 / 0.007011563 mm³. It also penetrates frozen I2 harness by 7.229763108 mm³. It is evidence of FAIL, not a manufacturing solution.
- 7-button simultaneous set is **not available** because I3 failed. N2 remains excluded; existing M3–M4 geometry was not optimized or changed.

## Outputs / scope

- `renders/i3_i4_local_hybrid_support_validation/01_i4_plus_u_local_contact_region_before.png`
- `renders/i3_i4_local_hybrid_support_validation/02_i4_complete_three_slot_one_foot_harness.png`
- `renders/i3_i4_local_hybrid_support_validation/03_i4_foot_shell_contact_closeup.png`
- `renders/i3_i4_local_hybrid_support_validation/04_i3_plus_u_local_contact_region_before.png`
- `renders/i3_i4_local_hybrid_support_validation/06_i3_complete_three_slot_one_foot_harness.png`
- `renders/i3_i4_local_hybrid_support_validation/07_i3_foot_shell_contact_closeup.png`
- `renders/i3_i4_local_hybrid_support_validation/05_i3_minus_u_micro_thickened_slot_section.png`

- `build123d_workbench/out/i3_i4_local_hybrid_support_validation/I3_COMPLETE_3SLOT_1LOCAL_FOOT_HARNESS_AUDIT_ONLY.step`
- `build123d_workbench/out/i3_i4_local_hybrid_support_validation/I4_COMPLETE_3SLOT_1LOCAL_FOOT_HARNESS_AUDIT_ONLY.step`
- `build123d_workbench/out/i3_i4_local_hybrid_support_validation/i3_i4_local_hybrid_support_validation.json`

N2 geometry search = 0; N2 seam analysis = 0; N2 redesign = 0. Global optimizer = 0; full-eight search = 0. Production geometry modification = 0. Protected authority hashes preserved = **True**.
