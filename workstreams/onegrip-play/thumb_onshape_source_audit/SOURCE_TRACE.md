# SOURCE TRACE — approved Maximum-Lowered Thumb

Audit date: 2026-08-24 (Asia/Seoul)  
Mode: local archaeology + authenticated Onshape UI read-only inspection  
Onshape writes: **0**

## Recovered lineage

```text
OneGrip_Play_V1
  DID a21e64f36bc61df760d4587c
    → Main workspace
      WID ef6a7b3ccc45186203e4d2ca
        → Joystick Part Studio
          EID 425d9199b59cfb1efd9ddc35
          configuration default
            → lower-15 features
              Fu0ngE5n5Mmnjfd_25
              "THUMB B housing-first total translation (0,+12.25,-21)"
              F54ht3HFsoh1AxM_25
              "THUMB D lower15 shell openings relocated"
            → saved immutable version
              THUMB_LOWER15_HOUSING_V1
              VID 50dfe4e752e447375b95493a
                → exact native solid shell parts
                  Joystick_1 / partId JaD
                  Joystick_2 / partId JfD
                → GET-only STL export at the source workspace state
                  scripts/export_thumb_lower15_housing.py
                → exports/thumb_lower15_housing_mockup/*.stl
                → regional visual graft
                  build123d_workbench/render_integrated_exterior_lowered_thumb_v1.py
                → approved visual exterior
```

## Local source archaeology

- `docs/39_thumb_lower15_housing_first.md` records the pre-write checkpoint
  `THUMB_LOWER15_PREWRITE`, the post-write version
  `THUMB_LOWER15_HOUSING_V1`, the total rigid transform
  `(0,+12.25,-21.00) mm`, 202 features, 30 solids, and zero new orphan bodies.
- `cad_dump/thumb_lower15_housing_validation.json` records the post-write
  regeneration at 2026-08-21 19:15 +09:00 and the same 202-feature/30-solid
  inventory.
- `cad/OneGrip_Thumb_Module_Reseat.fs` proves that the source operation used
  native solid queries. It transforms the original Backplate + eight cap
  solids as a nine-solid rigid set and moves the original shell opening faces
  by the identical transform. It does not create a mesh or replacement shell.
- `scripts/export_thumb_lower15_housing.py` is GET-only and identifies the
  source DID/WID/EID, `configuration=default`, and shell partIds `JaD`/`JfD`.
- Git commit `15be4594c392573bf056eb4c2444e387be1c24c5` is the first repository
  checkpoint containing the LOWER15 documentation, exporter and manifest.

## Onshape UI observations

The authenticated UI showed:

- saved version `THUMB_LOWER15_HOUSING_V1`, created 2026-08-21 19:15 KST;
- version URL VID `50dfe4e752e447375b95493a`;
- explicit read-only version banner;
- `Joystick` Part Studio with 202 features and 30 native parts;
- `Joystick_1` data-id/partId `JaD` and `Joystick_2` data-id/partId `JfD`;
- both shells use the native solid-part icon;
- the two active lower-15 features and their exact feature IDs;
- individual shell part export offers PARASOLID and STEP, among other formats.

The selected version description is:

> Housing-first additional 15 mm THUMB rigid cluster drop. Total from original
> (0,+12.25,-21) mm. Backplate + 8 caps and original openings moved identically.
> 202 features / 30 solids regenerated. INDEX/MIDDLE internals and Assembly
> hardware synchronization deferred.

## Local derived mesh fingerprints

| Asset | SHA-256 | Role |
|---|---|---|
| `OneGrip_lower15_housing_Joystick_1_JaD.stl` | `43CB0A9972E0153AFE49341A3E29DF130B9E966BBFF40A1114CEE3919C1B50CB` | derived tessellation of exact JaD shell |
| `OneGrip_lower15_housing_Joystick_2_JfD.stl` | `29050592A316C16B64211276ED0CE2BBFAFD7BB0B833D954DB7B305CEE677677` | derived tessellation of exact JfD shell |

Each mesh is one connected, consistently wound, watertight component. These
files are evidence and the approved visual input, but they are not the highest
authority: the immutable native Onshape version above is.

## Opening lineage

The native feature source queries the faces created by original feature
`F9tZ4ezI7riogDz_2`. The stored implementation audit resolves those 36 faces as
the eight original button openings plus the joystick opening, then applies the
same `(0,+12.25,-21)` transform. The derived LOWER15 meshes independently show
nonzero openings for `JOY`, `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, and `T8`.

## Identifier gap

The immutable VID was recovered from the authenticated UI. The MID is not
displayed in the UI and the API-key GET path returned HTTP 402 `API limit
exceeded`; therefore the MID is reported as unknown rather than invented.

