# OneGrip lower-15 external housing mockup

Source: Onshape `OneGrip_Play_V1 / Main / Joystick`  
Saved CAD version: `THUMB_LOWER15_HOUSING_V1`  
Configuration: `default`  
Unit: millimetre

## Print parts

- `OneGrip_lower15_housing_Joystick_1_JaD.stl`
- `OneGrip_lower15_housing_Joystick_2_JfD.stl`

These are the two complete external shell bodies only. Buttons, Backplate,
joystick hardware, INDEX/MIDDLE switch parts, retainers, wiring, and all other
internal components are excluded.

Import both STL files into the slicer as separate objects with scaling disabled.
Do not merge overlapping meshes: the two files are the mating shell halves.
Each shell occupies approximately `38.735 × 123.855 × 152.127 mm` in the source
coordinate frame, so rotate each half to suit the printer's usable volume and
support strategy.

## Mesh gate

Both STL files passed:

- one connected component per file
- watertight mesh
- consistent winding
- non-two-manifold edges: 0
- degenerate triangles: 0

See `mesh_validation.json` for exact counts, bounds, and volume.

This package is for external-form and shell-assembly mockup verification. The
internal hardware and INDEX/MIDDLE redesign are deliberately deferred.

