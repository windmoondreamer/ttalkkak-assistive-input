# OneGrip Current Main — exterior handling mockup

Source of truth:

- Onshape document: `OneGrip_Play_V1`
- workspace: `Main`
- Part Studio: `Joystick`
- state: current Stage-D export
- source archive: `Joystick_Current_Main_StageD.zip`
- source solids: 30 STL files

No cached shell, mirrored STL, or pre-Stage-D mesh is used.

## Files

### `OneGrip_Current_Main_Exterior_Alignment_Check.stl`

Exact alignment/reference STL. It contains the 19 currently visible exterior
solids in their original Part Studio coordinates:

- `Joystick_1`, `Joystick_2`
- `Backplate`
- eight original THUMB caps
- INDEX I1-I4 caps
- MIDDLE M1-M4 caps

No part is translated, mirrored, scaled, or otherwise modified. This file is
the position and opening/cap alignment source of truth, but its moving controls
remain separate shells.

### `OneGrip_Current_Main_Exterior_Mockup_SlicerUnion.stl`

Non-functional one-file handling mockup. It contains the exact alignment mesh
plus 20 small closed bridge cylinders:

- three cross-seam shell bridges
- one Backplate-to-shell bridge
- one hidden bridge per THUMB/INDEX/MIDDLE cap

Each bridge penetrates its target by 1.2 mm. Source parts themselves are not
moved. The STL contains overlapping closed volumes rather than a CAD B-rep
boolean union, so enable **merge/union overlapping volumes** in the slicer.

## Suggested quick print

- scale: 100%
- units: millimetres
- place the broad handle base on the build plate
- layer height: 0.20-0.28 mm
- walls: 3
- infill: 12-18%
- supports: build-plate-only if required by the selected material/printer
- enable slicer union/merge overlapping volumes

This is only an ergonomic/exterior handling mockup. Every button is immobilized
by a sacrificial bridge and is not expected to operate.

## Intentional omission

`Small_joystick_attachment` is excluded. Its STL is at a remote Part Studio
staging position (`X approximately 96.5-110.5 mm`), while the actual location is
defined by an Assembly mate that is not encoded in this Part Studio ZIP.
Guessing that transform would repeat the previous mixed-coordinate error.

Exact selected-part audit, hashes, topology, proximity sanity values, and bridge
coordinates are recorded in `mockup_manifest.json`.
