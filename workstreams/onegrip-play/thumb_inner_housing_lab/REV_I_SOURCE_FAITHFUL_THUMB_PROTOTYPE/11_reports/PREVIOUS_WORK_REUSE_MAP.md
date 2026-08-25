# PREVIOUS_WORK_REUSE_MAP — what REV_I inherits from REV_A…REV_H

REV_I is a continuation, not a restart. Nothing in REV_A…REV_H was modified;
`i01_inventory.py` hashed all 279 files and they stay where they are.

**Shell authority gate: PASS.** Both exact Onshape exports still hash to the
REV_D baseline (`622ADB3B…8FA54E86`, `D75F62E0…29EA340`), so every inherited
measurement taken against them is still valid. All 15 upstream references resolve.

Classification uses the four §24 buckets.

---

## REUSE DIRECTLY — geometry and numbers REV_I builds on unchanged

| artifact | what REV_I takes | why it survives |
|---|---|---|
| `thumb_exact_onshape_source/{JaD,JfD}_THUMB_LOWER15_APPROVED.step` | the shell, full stop | exact Onshape `THUMB_LOWER15_HOUSING_V1`; 9/9 through-openings verified in REV_D |
| **REV_H** `03_placement/H03_SEAT_UNITS_PLACED.step` `27A3F2EF…` | all 8 seat transforms | built on the frozen axes by construction — centre error 0.0000 mm, axis error 0.0000° |
| **REV_H** `03_placement/h03_placement.json` | per-button `capUndersideWorld`, `axisWorld`, `plateTopWorld` | the registration REV_I must not re-derive |
| **REV_H** `04_carrier/C05_SEAT_FIRST_CARRIER.step` `E66B9965…` | starting carrier geometry | §14 — modify, do not regenerate from nothing |
| **REV_H** `01_seat_audit/h02_stack.json` | the whole internal stack | measured from exact B-rep, one common frame |
| **REV_H** `10_scripts/h03_placement.py::seat_solids` | the seat generator | the mechanism itself, parameterised |
| **REV_B** `01_axis_authority/b03_axis_authority.py::true_axis` | TRUE press axis per cap | REV_A's version picked the largest face and gave one wrong common 4.00° |
| **REV_A** `06_keepouts/THUMB_KEEPOUT_ASSEMBLY.step` `88F370D3…` | keep-out set | **but see the split below** |
| `labutil.py` / `labrender.py` | frame, ray-parity, occupancy, renderer | includes the (V,U,−N) handedness fix |

### Inherited constants REV_I treats as given

```text
CAP UNDERSIDE -> PLATE TOP   4.759 mm      the dimension that sets seat depth
PLATE THICKNESS              2.003 mm
BODY BEARING                 6.02 x 6.04 mm, flat, no boss/shoulder/recess
BODY HEIGHT                  3.144 mm      body sits +0.051 mm off the plate
ACTUATOR                     3.51 dia, 1.909 mm above the body top
TERMINAL SLOTS               2 x (1.30 x 6.40) at +-2.60 mm
TERMINAL DROP BELOW PLATE    1.651 mm  (3.654 mm below the plate top face)
```

## REUSE AS REFERENCE — evidence REV_I reasons from but does not import

| artifact | what it proves | how REV_I uses it |
|---|---|---|
| **REV_D** `d02_housing_vs_exact.json` | original shell-gap and load-transfer behaviour of the ORIGINAL Backplate | the §21 load-path **principle**, not the contact coordinates |
| **REV_A** `a11_original_backplate_anatomy.json` | plate thickness p50 **2.0036 mm**, conformal gap p50 1.292 mm, contact-band fraction **6.39 %** | tells REV_I how much of the original plate ever touched the shell |
| **REV_A** `02_reference_copies/ORIGINAL_THUMB_BACKPLATE.step` `39C6647D…` | the original core, 5899.528 mm³, 85 faces | source for the §7 internal-core reference; **not** to be rigidly inserted |
| **REV_E** `e01_probe.json`, `e03_validate.json` | an along-axis band loses true thickness on oblique walls (`t·\|m·n\|`) | REV_I must never size a wall along an axis on a sloped surface |
| **REV_F** `f01_rigid_fit.json` + `C03_*` | rigid whole-plate reuse keeps thickness exactly but cannot reach the shell | closes the "just move the original plate" option |
| **REV_G** `g01_solve_pose.json`, `g02_tradeoff.json` | opening relocation undoes 95.0 % of the lowering | closes the "move the openings" option |
| **REV_B** `b06_docs71_recheck.json` | docs/71 recheck against the true axes | background for the SZH questions |
| **REV_A** `a12_keepouts.json` | SZH placement origin + `szhReferenceQuality = PROVISIONAL / WEB / docs71 quality LOW` | the reason §13 exists |
| all REV_A…REV_H renders (57 PNG) | visual record | not regenerated |

### The keep-out set must be split before use

`THUMB_KEEPOUT_ASSEMBLY.step` contains 15 items, and REV_H's mistake was
treating them as one class. REV_I splits them:

```text
CONFIDENT STATIC     ORIGINAL_SCREW_1/2/3, FROZEN_CONTROL_AXES
PROVISIONAL STATIC   SZH_pcb, SZH_gimbal, SZH_x_pot, SZH_y_pot,
                     SZH_push_switch, SZH_shaft, SZH_cap, SZH_MOUNT_HOLE_CENTRES
REMOVABLE HARDWARE   SZH_header                    (§12 — may be cut off)
PROVISIONAL MOVING   SZH_MOVING_ENVELOPE           (§13 — NOT a destructive cutter)
EXTERNAL SUBSYSTEM   N1_N2_SHARED_CARRIER          (§22 — REVALIDATE AFTER FINGER FREEZE)
```

## SUPERSEDED GEOMETRY — correct when made, no longer the architecture

| artifact | superseded by | note |
|---|---|---|
| **REV_A** `C01_SOURCE_FAITHFUL_REBASE.step` `396D70C7…` | REV_H seat-first carrier | C01/C02 must not be the primary architecture (§0) |
| **REV_A** `C01_stage1/stage3` intermediates | — | build intermediates |
| **REV_E** `C02_C01_EXACT_REFINED.step` `E1E5A3B1…` | REV_H | keep the *finding*, drop the *candidate* |
| **REV_C** `*_RECONCILED_REFERENCE.step` (3 files) | the exact Onshape export | REV_D §2 ended shell reconstruction |
| **REV_A** `02_reference_copies/*_FROZEN_THUMB_CROP.step` | exact export | derived from the legacy reconstructed shell |
| **REV_C** `C01R_RECONCILED_SOURCE_FAITHFUL.step` `A774DBFB…` | REV_H | §0 says do not repeat C01R's inward-shifted pads |
| **REV_F** `C03_POSE_A/POSE_B/RIGID_FIT_TRIM.step` | — | kept as the proof, not as a candidate |

## DO NOT USE

| artifact | reason |
|---|---|
| `build123d_workbench/out/integrated_exterior_lowered_thumb_v1/{JAD,JFD}_EXTERIOR_LOWERED_THUMB_V1.step` | **legacy defective reconstruction.** Its openings fail two independent ways: translated void plugs stop 1.67–3.66 mm short, and world-axis AABB cutters sized to the cap stop 0.10–1.23 mm short. Never a shell authority. |
| REV_A's original `press_axis` (largest-face) | returns one common 4.00° for all eight; the true tilts are 0.00 / 1.84 / 4.00 / 7.06 / 7.07 / 9.36 / 9.38° |
| REV_H's use of `SZH_MOVING_ENVELOPE` as a boolean cutter | destroyed the T7/T8 bearing surfaces (504.101 mm³). §13 forbids carrying this forward. |
| REV_G pose transform | relocates the frozen controls |

---

## What REV_I actually changes

Exactly four things, all inside REV_I:

1. **Restore T7/T8.** Rebuild the carrier without the moving envelope as a
   cutter, and report static vs moving collisions separately (§13).
2. **Add the joystick.** REV_H had none. §15 requires every carrier revision to
   show it, so the core is re-evaluated as one package (§6, §10).
3. **Add the external stack.** REV_H measured only inside the shell. §5 and §9
   make cap protrusion a functional requirement, which can move the seat depth —
   so this must be measured before the carrier is final.
4. **Add the load path.** REV_H ended with the carrier 7.63–12.70 mm from the
   shell and no structure crossing that gap (§20, §21).

Everything else is inherited.
