# OneGrip Play — build123d-first MIDDLE carrier redesign

Date: 2026-08-21  
Scope: M1~M4 redesign / local build123d geometry / Onshape CAD WRITE 0  
Frozen reference: `FINGER_SIMPLIFIED_CARRIER_V1` / `f51e9d9a868db9ef0fcd4b06`

## Decision

- **build123d local geometry gates: PASS**
- **printability: PASS WITH LOCAL SUPPORT**
- **Onshape production implementation: HOLD**
- **Onshape CAD WRITE: 0**

HOLD is not caused by a failed new solid. The authenticated current Onshape
B-rep/feature tree could not be re-read: API returned HTTP 402 and the browser
session was at sign-in. The exact new shell opening/captive-carrier interface
therefore remains intentionally unwritten. Current JaD/JfD, INDEX, RWID/RZKD,
screw and THUMB geometry were not changed.

## Design result

The previous MIDDLE implementation was not repaired or copied. A new
parameterized OCC model was created in
`build123d_workbench/middle_redesign.py`.

- M1/M2/M3: one removable three-switch carrier, one exact solid
- M4: one independent carrier, one exact solid
- caps: four identical external-language parts
- independent MIDDLE service parts: 6
- tiny spacer/hook/rail/anchor parts: 0
- unexpected fragments/slivers/orphan solids: 0
- switch axes: coincident with each local shell normal
- external target: 7.6 mm cap / 8.0 mm opening / 1.0 mm exposure

The carrier uses a 1.6 mm front frame and corner columns, two broad rear
support bars, and an open rear wiring side. All four fixed terminal roots are
cut as conservative clearance volumes. Bendable distal pins and direct-solder
wires exit on the side opposite the backbone.

The cap is a single FDM part with a broad 3.8 mm contact, a 1.4 mm continuous
skirt and two 1.2 mm shell-captive tabs. It uses no stop lug, 0.7 mm hook or
0.8 mm rail. At the maximum 0.35 mm press probe, both skirt-to-housing and
tab-to-carrier axial clearance are 0.25 mm; tab-to-housing radial clearance is
0.51 mm.

## M1~M4 datums

All units are millimetres. `axis = shell normal`, so every mismatch is 0°.

| Unit | Center XYZ | Actuation axis / shell normal | Mismatch | Roll | Owner |
|---|---|---|---:|---:|---|
| M1 | (-20.441892, 4.808880, -11.125000) | (-0.992161, -0.028542, -0.121659) | 0.000° | 90° | JfD |
| M2 | (-17.213380, -7.084496, -11.125000) | (-0.716360, -0.528358, -0.455704) | 0.000° | 90° | JfD |
| M3 | (-6.893459, -13.725680, -11.125000) | (-0.224260, -0.771794, -0.595014) | 0.000° | 0° | JfD |
| M4 | (7.383061, -13.587450, -11.125000) | (0.224859, -0.772793, -0.593489) | 0.000° | 0° | JaD |

All four centers use `Z = -11.125`; the former M2-only 3 mm dogleg is removed.
Arc stations are `-32.0, -19.5, -7.0 | +7.5 mm`. M4 remains separated because
it belongs to JaD and retains a separate carrier.

Center displacement from the previous implementation:

| Unit | Displacement |
|---|---:|
| M1 | 5.4577 mm |
| M2 | 5.5106 mm |
| M3 | 3.4254 mm |
| M4 | 0.0638 mm |

## Numeric gates

| Gate | Required | Result | Status |
|---|---:|---:|---|
| minimum switch-switch SAT | ≥ 1.20 mm | 1.3891 mm | PASS |
| minimum divider | ≥ 0.80 mm | 1.1227 mm | PASS |
| M3 JfD split ownership | ≥ 1.50 mm | 1.5042 mm | PASS |
| M4 JaD split ownership | ≥ 1.50 mm | 1.9900 mm | PASS |
| minimum cap-to-cap gap | > 0 | 3.7843 mm | PASS |
| axis mismatch | ≤ 5° target | 0.000° | PASS |
| carrier wall | ≥ 1.20 / prefer 1.60 mm | 1.60 mm | PASS |
| cap retention minimum | ≥ 1.20 mm | 1.20 mm | PASS |
| pocket side clearance X/Y | parameterized | 0.11 / 0.14 mm | PASS |
| minimum INDEX holder clearance | no collision | 6.0249 mm | PASS |
| minimum INDEX switch clearance | no collision | 11.1648 mm | PASS |
| minimum screw clearance | ≥ 2.50 mm | 5.7379 mm | PASS |
| cached INDEX shell keepout | collision 0 | 0 / 2.1803 mm min | PASS |
| cached RWID | collision 0 | 0 / 0.9909 mm min | PASS |
| cached RZKD | collision 0 | 0 / 9.7169 mm min | PASS |
| frozen THUMB components | collision 0 | 0 | PASS |
| switch-carrier OCC intersection | 0 mm³ | 0 mm³ | PASS |
| rigid terminal-root intersection | 0 mm³ | 0 mm³ | PASS |
| sampled straight insertion interference | 0 mm³ | 0 mm³ | PASS |
| cap vs carrier/housing at 0.35 mm | 0 mm³ | 0 mm³ | PASS |
| printable part solid count | 1 each | 1 each | PASS |
| unexpected fragment count | 0 | 0 | PASS |

Adjacent switch SAT values are M1-M2 1.5645, M2-M3 1.3891 and M3-M4
3.6417 mm. Divider values are 1.2810, 1.1227 and 3.3942 mm.

## Exact part inventory

| Part | Solids | Volume | Faces | Print mesh components |
|---|---:|---:|---:|---:|
| M1-M3 shared carrier | 1 | 690.455 mm³ | 186 | 1 |
| M4 carrier | 1 | 177.034 mm³ | 53 | 1 |
| M1 cap | 1 | 214.849 mm³ | 30 | 1 |
| M2 cap | 1 | 214.849 mm³ | 30 | 1 |
| M3 cap | 1 | 214.849 mm³ | 30 | 1 |
| M4 cap | 1 | 214.849 mm³ | 30 | 1 |

Every carrier connection has positive volume. No tangent-only union, leftover
boolean tool body or disconnected rear stop remains.

## Printability

The six parts were automatically oriented independently, then placed on one
70.09 × 30.80 × 15.32 mm STL plate with a 5.0 mm XY gap. The plate contains
exactly six disconnected printable components, as intended.

| Part | Print size XYZ | Build-plate contact | Downward >45° area | Requirement |
|---|---|---:|---:|---|
| shared carrier | 27.82 × 16.15 × 15.32 mm | 35.23 mm² | 14.71% | local/tree support |
| M4 carrier | 11.67 × 10.21 × 7.55 mm | 51.20 mm² | 6.31% | small local support |
| each cap | about 7.6~7.9 × 9.6~9.7 × 5.25 mm | 57.76 mm² | 2.10% | normally support-free |

The shared carrier is not claimed to be completely support-free. Its supports
are confined to a separately printable/serviceable part rather than the shell
interior. Functional 6.4 mm pockets, rear stops and terminal channels must be
kept free of dense support; use painted local/tree support under the outer
backbone only.

Recommended sequence:

1. Print caps external face down.
2. Print M4 on the keyed-stop/backbone side.
3. Print the shared carrier in the generated print-ready orientation and paint
   local supports only under downward backbone spans.
4. Deburr the 6.4 mm pockets without widening their parameterized fit.

## Assembly sequence

1. Insert each cap from the shell interior and push its 7.6 mm pad through the
   future 8.0 mm opening.
2. Pre-form and optionally pre-solder the selected ITS-1105 distal leads.
3. Insert M1~M3 switches straight into the shared carrier until the broad rear
   stops; no separate spacer is installed.
4. Route wires through the open rear side opposite the backbone.
5. Mount/capture the carrier in JfD.
6. Repeat with the independent M4 carrier in JaD.
7. Close the existing shell and verify 0.25 mm actuation and return.

Steps 5~7 are local feasibility results, not a production shell sign-off. The
exact shell docking/captive interface must be cut against the restored current
Onshape B-rep before any write is authorized.

## Visual QC

- [Exterior perspective](../renders/middle_redesign_build123d/01_exterior_perspective.png)
- [INDEX/MIDDLE comparison](../renders/middle_redesign_build123d/02_index_middle_comparison.png)
- [Transparent shell/internal](../renders/middle_redesign_build123d/03_transparent_internal.png)
- [M1-M3 exploded](../renders/middle_redesign_build123d/04_m1_m3_shared_carrier_exploded.png)
- [M4 exploded](../renders/middle_redesign_build123d/05_m4_carrier_exploded.png)
- [Finger-facing](../renders/middle_redesign_build123d/06_finger_facing.png)

Visual conclusions:

- M2 no longer forms a separate dropped row.
- M3 has no half-ring, auxiliary anchor or external exception boss.
- all four MIDDLE user-facing pads use the same nominal size and exposure.
- no small orphan-like pieces are visible; each carrier and cap is one solid.
- the exterior view is an overlay on the frozen shell reference. It does not
  falsely claim that the new 8.0 mm openings have already been written.

## OLD vs NEW

| Item | OLD MIDDLE | NEW build123d design |
|---|---|---|
| service parts | 4 caps + 4 spacers = 8 | 4 caps + 2 carriers = 6 |
| retention | 0.7 mm hooks / 0.8 mm rails | 1.2 mm captive tabs / 1.6 mm carrier walls |
| spacer | one tiny part per switch | integrated rear stops; 0 spacers |
| cap stop | small stop lugs | none |
| M3 exception | half-ring + auxiliary anchor | none |
| row | M2 about 3 mm lower | common Z continuous row |
| axis mismatch | 20.94° / 21.83° / 24.71° / 0° | 0° / 0° / 0° / 0° |
| print strategy | shell-integrated difficult internal support | independent orientation and local support |
| assembly | four fiddly holder/spacer stacks | one three-switch subassembly + one M4 subassembly |
| serviceability | many tiny parts | six robust parts; M4 remains independently replaceable |
| external language | 8.0 cap / 8.4 opening / low exposure | 7.6 cap / 8.0 opening / 1.0 exposure |

## Files

- Parameterized source: `build123d_workbench/middle_redesign.py`
- Exact validation/export: `build123d_workbench/validate_middle_redesign.py`
- Render generator: `build123d_workbench/render_middle_redesign.py`
- Print orientation/plate: `build123d_workbench/prepare_middle_print_stl.py`
- Numeric audit: `build123d_workbench/out/middle_redesign/middle_redesign_validation.json`
- Print audit: `build123d_workbench/out/middle_redesign/middle_redesign_printability.json`
- Six-part print STL: `build123d_workbench/out/middle_redesign/MIDDLE_6_parts_one_plate_print_ready.stl`
- STEP assembly reference: `build123d_workbench/out/middle_redesign/MIDDLE_reference_with_ITS1105.step`

## HOLD details and next gate

**PROBLEM**  
Current Onshape B-rep/feature tree and the exact future shell docking interface
are not available in the authenticated read path.

**CAUSE**  
API HTTP 402 and browser sign-in state prevented the mandatory current-model
recheck. Cached meshes can certify collision envelopes but cannot authorize a
production FeatureScript/shell write.

**MINIMAL FIX**  
Restore an authenticated current-version read, or export JaD/JfD plus RWID and
RZKD as current STEP/Parasolid references. Re-run the same datums and carrier
against those exact B-reps.

**ALTERNATIVE**  
Import the user-exported current STEP references into build123d and finish the
keyed/captive shell interface there before reproducing it in Onshape.

**RECOMMENDATION**  
Keep **Onshape CAD WRITE = HOLD**. After the B-rep recheck passes, implement
atomic phases M1-M3 carrier → JfD openings/interface → cap actuation → M4
carrier → JaD opening/interface → full wiring/service audit. JaD/JfD target
identity must remain first in every positive union.
