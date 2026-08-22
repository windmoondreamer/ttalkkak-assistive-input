# OneGrip Play — Finger Controls V2 Internal Design

## 1. Result

The user-approved external eight-button layout from `docs/45` was treated as
immutable input. All geometry work was performed locally with build123d 0.11.1
and OCCT against the immutable AP242 clean-shell references.

```text
ONSHAPE API CALL = 0
ONSHAPE BROWSER AUTOMATION = 0
ONSHAPE CAD WRITE = 0

EXTERNAL LAYOUT = FROZEN / PRESERVED
8-SWITCH INTERNAL FIT = PASS
N2 SEAM = PASS
CARRIER ARCHITECTURE = PASS
WIRING = PASS
FDM PRINTABILITY = PASS
LOCAL FINGER V2 = PASS
```

The final physical set is `I2 I3 I4 M3 M4 N1 N2 N3`. `I1 M1 M2` remain
removed and were not recreated.

## 2. Immutable source and local source of truth

- clean JaD: `local_cad/reference/JAD_CLEAN_PRE_FINGER.step`
- clean JfD: `local_cad/reference/JFD_CLEAN_PRE_FINGER.step`
- original thumb: `local_cad/reference/THUMB_ORIGINAL_PRE_FINGER_REFERENCE.step`
- approved exterior transforms: `build123d_workbench/finger_layout_reset.py`
- new parametric mechanism: `build123d_workbench/finger_controls_v2.py`
- exact validation: `build123d_workbench/validate_finger_controls_v2.py`
- render-only consumer: `build123d_workbench/render_finger_controls_v2.py`

The clean STEP files were imported but never overwritten. Generated shell,
carrier, cap, print-plate and validation artifacts are isolated under
`build123d_workbench/out/finger_controls_v2/`.

## 3. Approved external layout preservation

All eight approved center coordinates were read directly from the marker source.
The final center delta is `0.000000 mm` for every button. Cap size remains
7.60 mm with 1.00 mm nominal exposure. Standard openings are 8.00 mm; N2 uses
an 8.40 mm seam-relieved opening while keeping the approved center unchanged.

The final-to-approved wireframe overlay is
`renders/finger_controls_v2/10_approved_overlay.png`.

## 4. Surface, axis and switch placement

`axis` is the common cap-travel and ITS actuator axis. Roll describes the ITS
housing frame relative to the exterior marker frame; the circular actuator lets
this internal roll change without changing the approved cap center.

| ID | center XYZ mm | owner | local shell normal | final actuation axis | mismatch deg | roll deg | switch rear depth mm | nearest | clearance mm | exposure mm |
|---|---|---|---|---|---:|---:|---:|---|---:|---:|
| I2 | (-15.971, -26.210, 8.999) | JfD | (-0.472400, -0.736800, -0.483800) | (-0.433985, -0.756924, -0.488593) | 2.500 | -15.649 | 8.96 | I3 | 1.423 | 1.0 |
| I3 | (-5.496, -29.325, 9.000) | JfD | (-0.038300, -0.955600, -0.292100) | (-0.081691, -0.952023, -0.294922) | 2.500 | -1.450 | 9.36 | I2 | 1.423 | 1.0 |
| I4 | (5.496, -29.325, 9.000) | JaD | (0.038300, -0.955600, -0.292100) | (0.038301, -0.955619, -0.292106) | 0.000 | -179.329 | 9.36 | I3 | 3.704 | 1.0 |
| M3 | (-6.891, -13.717, -11.118) | JfD | (-0.224260, -0.771794, -0.595014) | (-0.224260, -0.771794, -0.595014) | 0.000 | -9.809 | 8.76 | M4 | 3.950 | 1.0 |
| M4 | (7.379, -13.575, -11.116) | JaD | (0.224859, -0.772793, -0.593489) | (0.287837, -0.744171, -0.602793) | 4.000 | -166.876 | 8.36 | N3 | **1.359** | 1.0 |
| N1 | (-10.990, -35.800, 25.000) | JfD | (-0.076466, -0.872459, -0.482667) | (-0.076466, -0.872459, -0.482667) | 0.000 | -2.422 | 8.36 | N2 | 4.518 | 1.0 |
| N2 | (0.000, -35.765, 25.000) | JfD | (-0.043168, -0.859399, -0.509479) | (-0.043168, -0.859399, -0.509479) | 0.000 | -1.466 | 8.36 | N1 | 4.518 | 1.0 |
| N3 | (17.487, -6.664, -11.125) | JaD | (0.737273, -0.507790, -0.445621) | (0.692159, -0.560207, -0.455064) | 4.000 | -150.653 | 9.16 | M4 | **1.359** | 1.0 |

I2/I3 use symmetric 2.5 degree internal tilts and M4/N3 use symmetric 4.0
degree tilts. This moves the inward switch housings apart without moving their
exterior centers. The worst exact B-rep switch distance is 1.358719 mm and the
worst analytical OBB SAT is 1.358709 mm, both above the 1.30 mm preferred gate.

## 5. Opening and structural results

The long opening tools for I2/I3 and M4/N3 intersect only after they have left
the local shell material. The final exterior cap/opening test therefore uses
the cap-face SAT plus exact common-tool intersection with the original shell
material, rather than treating a deep cutter intersection in internal air as an
external opening failure.

| gate | result |
|---|---:|
| minimum approved-cap ligament | 2.862192 mm |
| N1/N2 conservative pocket divider | 4.297855 mm |
| carrier functional wall | 1.60 mm |
| absolute functional-wall gate | 1.20 mm |
| minimum screw keep-out clearance | 4.022163 mm |
| minimum original-thumb clearance | 10.746084 mm |
| switch/shell hard intersection | 0 mm3 |
| carrier/shell hard intersection | 0 mm3 |

The M3 and M4/N3 carriers are trimmed 0.20 mm from their respective sides of
the nominal X=0 split, enforcing 0.40 mm total carrier-to-carrier split
clearance. N2 is deliberately excluded from this trim and has its own seam
architecture and gate.

## 6. N2 seam solution

N2 remains at the approved `X = 0` center. It is not moved to avoid the seam.

- shell/carrier owner: JfD
- closure/capture side: JaD
- opening: split, seam-relieved 8.40 mm
- cap: unchanged 7.60 mm
- nominal cap clearance: 0.40 mm per side
- allocated relative shell-closure error: 0.20 mm
- residual margin after closure budget: 0.20 mm per side
- carrier-to-opposite-shell clearance: 1.532542 mm
- carrier/opposite-shell intersection: 0 mm3
- retention: broad N1/N2 C-channel and JaD shell closure; no seam tab or hook

The switch is guided by its one-piece carrier. It is not guided by two shell
edges simultaneously, so shell closure tolerance does not set the actuator
axis. The switch loads laterally from the seam side before JaD closure and is
serviceable after reopening the two shells.

```text
N2 CURRENT POSITION = PASS
```

## 7. Carrier architecture

Five carrier solids support eight switches:

1. `N1_N2_shared_carrier` — JfD side, N1 outer-load and N2 seam-load
2. `I2_I3_shared_carrier` — JfD side, opposite-end switch loading
3. `M4_N3_shared_carrier` — JaD side, opposite-end switch loading
4. `I4_carrier` — independent JaD C-channel
5. `M3_carrier` — independent JfD C-channel

Each cradle has a 6.40 x 6.40 mm parameterized pocket around the conservative
6.18 x 6.12 x 3.56 mm ITS housing, 1.60 mm walls and a broad rear plate.
The open side permits switch preload; the adjacent shell wall supplies the
fourth lateral restraint after assembly.

```text
0.7 mm hook = 0
0.8 mm rail dependency = 0
tiny snap finger = 0
independent spacer = 0
tangent-only carrier connection = 0
```

All five carrier STEP bodies are valid single solids. Exact pairwise carrier
intersection after split trim is zero.

## 8. Terminals and wiring

Each switch has four conservative fixed-root reliefs. The distal leads remain
one-time formable and direct pre-solder wiring remains allowed. A 4.00 x 3.20 mm
straight service envelope exits behind every rear plate. Shared-carrier bridges
are placed on a broad outer rail and the complete root/wire voids are re-cut
after union.

Final exact intersections are:

```text
fixed root / carrier = 0 mm3
wire envelope / carrier = 0 mm3
wire envelope / JaD = 0 mm3
wire envelope / JfD = 0 mm3
```

## 9. Assembly and service path

Validated sequence:

1. Print/deburr the five carriers and eight caps.
2. Pre-form distal ITS-1105 leads and pre-solder insulated wires.
3. Load both switches into each shared carrier from opposite open ends while
   the carrier is outside the shell; load I4 and M3 in the same way.
4. Route fixed roots and wires through the rear service exits.
5. Translate preloaded JfD modules from the open central seam along global +X;
   translate JaD modules along global -X.
6. Push the caps onto the 3.35 mm actuators from the exterior.
7. Close JaD/JfD so the shell walls provide broad lateral capture.
8. Verify 0.35 mm usable travel, return and continuity before final screws.

The switch preload sweep was checked at 0–12 mm and the module seam-insertion
sweep at 0–14 mm. Maximum hard intersection is 0 mm3. Cap motion was checked
from 0 to 0.35 mm; shell, carrier and housing hard intersection is 0 mm3.

## 10. FDM and fragment gate

Recommended orientation:

- carriers: broad rear plate on the bed, C-channel opening upward
- N1/N2 carrier: use the N1 average frame for the bed orientation
- caps: 7.60 mm exterior pad face on the bed, actuator socket upward

The print plate contains 13 valid solids: five carriers and eight caps. It is
one STL with non-overlapping, deliberately spaced components.

| item | result |
|---|---:|
| valid printable parts | 13 / 13 |
| print plate solid count | 13 |
| print plate valid | PASS |
| exported STL triangles | 15,180 |
| exported STL connected components | 13 |
| exported STL bounding size | 102.80 x 28.47 x 10.63 mm |
| exported STL degenerate triangles | 0 |
| exported STL non-finite coordinates | 0 |
| unexpected orphan solid | 0 |
| unexpected sliver | 0 |
| leftover cutter | 0 |
| tangent-only attached component | 0 |

## 11. Generated shell and carrier inventory

| part | solids | valid | volume mm3 |
|---|---:|---|---:|
| JAD_FINGER_V2 | 1 | PASS | 45,917.34 |
| JFD_FINGER_V2 | 1 | PASS | 47,000.70 |
| N1_N2_shared_carrier | 1 | PASS | 587.18 |
| I2_I3_shared_carrier | 1 | PASS | 500.07 |
| M4_N3_shared_carrier | 1 | PASS | 530.38 |
| I4_carrier | 1 | PASS | 266.68 |
| M3_carrier | 1 | PASS | 264.56 |

## 12. Visual QC

Generated under `renders/finger_controls_v2/`:

1. `01_final_cap_view.png`
2. `02_transparent_shell_all_switches.png`
3. `03_left_oblique_internal.png`
4. `04_right_oblique_internal.png`
5. `05_carrier_exploded.png`
6. `06_n1_n2_seam_closeup.png`
7. `07_n3_closeup.png`
8. `08_wiring_concept.png`
9. `09_assembly_service_view.png`
10. `10_approved_overlay.png`
11. `00_contact_sheet.png`

The final overlay shows all eight final cap centers on the approved docs/45
marker centers. Internal-axis optimization did not move an external center.

## 13. Exact output set

Primary files:

- `build123d_workbench/out/finger_controls_v2/JAD_FINGER_V2.step`
- `build123d_workbench/out/finger_controls_v2/JFD_FINGER_V2.step`
- five carrier STEP/STL pairs
- eight cap STEP/STL pairs
- `build123d_workbench/out/finger_controls_v2/FINGER_V2_PRINT_PLATE.stl`
- `build123d_workbench/out/finger_controls_v2/FINGER_V2_ASSEMBLY_REFERENCE.step`
- `build123d_workbench/out/finger_controls_v2/finger_controls_v2_source_manifest.json`
- `build123d_workbench/out/finger_controls_v2/finger_controls_v2_validation.json`

The validation JSON records each output path, byte size and SHA-256. Obsolete
individual carrier exports from the initial seven-carrier trial were removed;
only the final five-carrier output set remains.

## 14. Final numerical gates

- `externalLayoutFrozenPreserved` = **PASS**
- `axisMismatch` = **PASS**
- `switchSeparation` = **PASS**
- `hardShellCollision` = **PASS**
- `screwClearance` = **PASS**
- `thumbCollision` = **PASS**
- `switchCarrierClearance` = **PASS**
- `terminalRootClearance` = **PASS**
- `wiringPath` = **PASS**
- `openingOverlap` = **PASS**
- `carrierCarrierCollision` = **PASS**
- `structuralWall` = **PASS**
- `divider` = **PASS**
- `switchAssemblyPath` = **PASS**
- `carrierAssemblyPath` = **PASS**
- `capTravel` = **PASS**
- `validPrintableParts` = **PASS**
- `oneSolidPerPrintablePart` = **PASS**
- `shellValidity` = **PASS**
- `fragmentGate` = **PASS**
- `N2CurrentPosition` = **PASS**

```text
EXTERNAL LAYOUT = FROZEN / PRESERVED
8-SWITCH INTERNAL FIT = PASS
N2 SEAM = PASS
CARRIER ARCHITECTURE = PASS
WIRING = PASS
FDM PRINTABILITY = PASS
LOCAL FINGER V2 = PASS
```
