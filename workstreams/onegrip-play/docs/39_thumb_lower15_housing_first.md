# THUMB cluster additional −15 mm — housing-first design

Date: 2026-08-21  
Onshape document: `OneGrip_Play_V1 / Main / Joystick`  
Scope: shell and original THUMB external control module only

## Result

The original Backplate and eight original button-cap solids were kept as one
rigid cluster. The 36 original shell-opening faces were moved by the identical
transform. No replacement cap, pedestal, holder, or boolean tool body was
created.

| Item | Translation (mm) |
|---|---:|
| Validated Stage-D position from original | `(0, +5.50, −6.00)` |
| This revision, additional movement | `(0, +6.75, −15.00)` |
| This revision, total from original | `(0, +12.25, −21.00)` |

The extra +Y is a shell-curvature correction. A pure −15 mm Z translation
causes the module-to-shell relation to drift as it moves down the curved grip.
The selected +6.75 mm value is the minimum-score result of a 0.25 mm sweep that
preserves the existing eight-cap-to-shell radial relationship.

## Housing gate

- Onshape checkpoint before the write: `THUMB_LOWER15_PREWRITE`
- Onshape post-write housing version: `THUMB_LOWER15_HOUSING_V1`
- Part Studio regeneration: PASS
- Feature count after regeneration: **202**
- Solid-body count after regeneration: **30**
- Shell bodies `Joystick_1` and `Joystick_2`: present
- Original Backplate: present
- Original eight caps: present
- Rigid-cluster relative geometry: preserved
- Original opening faces: healed at the old location and relocated with the
  same transform
- New orphan/tool body: none created
- Visible feature error: none
- Sampled moved-Backplate-to-shell gap: **0.252456 mm**

This is a housing-first pass. It demonstrates that the two original shell
bodies regenerate with the lower opening set and that the original external
module can occupy the new position without adding a replacement housing body.

## Deliberately deferred to the next prompt

The following items were not redesigned or used as blockers in this pass:

- INDEX and MIDDLE holder/boss geometry
- finger-switch bodies and terminal routing
- screw and wiring envelopes
- HW504 joystick and PushBtn assembly-instance positions
- `Small_joystick_attachment` assembly-mate position
- full hardware interference and actuation verification

The current Assembly therefore must not be treated as a final hardware-position
validation. Its joystick and button hardware instances still use the preceding
Stage-D mate placement until the internal redesign stage synchronizes them to
the new Backplate root frame.

## Next internal-design target

Use the new Backplate/root-frame delta `(0, +6.75, −15.00) mm` as the single
source of truth. Rework the bulky INDEX/MIDDLE internal regions only where
positive-volume interference is proven. Preserve shell fastening, minimum wall
thickness, cap exposure, and serviceable wiring paths; do not move individual
THUMB controls relative to one another.

## Files

- CAD implementation: `cad/OneGrip_Thumb_Module_Reseat.fs`
- Housing sweep: `scripts/design_thumb_lower15_housing.py`
- Numeric study data: `cad_dump/thumb_lower15_housing_study.json`
- Position proof (Stage-D ghost versus lower-15 target):
  `renders/thumb_lower15_position_proof.png`

`renders/thumb_lower15_housing_seed.png` is an offline sweep seed made from the
pre-write Stage-D shell STL. It is not a final-CAD photograph and must not be
used to judge the relocated opening position.

## Final external-housing mockup export

The final Onshape workspace was exported as the two shell bodies only using
`configuration=default`:

- `exports/thumb_lower15_housing_mockup/OneGrip_lower15_housing_Joystick_1_JaD.stl`
- `exports/thumb_lower15_housing_mockup/OneGrip_lower15_housing_Joystick_2_JfD.stl`
- package: `exports/thumb_lower15_housing_mockup/OneGrip_lower15_external_housing_mockup_STL.zip`

Both files are single-component, watertight, consistently wound binary STL
meshes with zero non-two-manifold edges and zero degenerate triangles. The ZIP
also contains the clean assembled/exploded renders and exact mesh validation.
