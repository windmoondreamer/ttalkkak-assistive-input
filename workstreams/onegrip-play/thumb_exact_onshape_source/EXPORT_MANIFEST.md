# OneGrip Play — exact approved LOWER15 Onshape export manifest

Export date: 2026-08-24 (Asia/Seoul)  
Mode: **EXPORT ONLY / immutable Onshape Version / no geometry modification**

## Exact source

| Field | Value |
|---|---|
| Document | `OneGrip_Play_V1` |
| DID | `a21e64f36bc61df760d4587c` |
| Version | `THUMB_LOWER15_HOUSING_V1` |
| VID | `50dfe4e752e447375b95493a` |
| Part Studio | `Joystick` |
| EID | `425d9199b59cfb1efd9ddc35` |
| Configuration | `default` |
| Source URL | `https://cad.onshape.com/documents/a21e64f36bc61df760d4587c/v/50dfe4e752e447375b95493a/e/425d9199b59cfb1efd9ddc35` |

## Exported parts

| Onshape part name | Part ID | Role |
|---|---|---|
| `Joystick_1` | `JaD` | approved exact shell half |
| `Joystick_2` | `JfD` | approved exact shell half |

Each part was exported individually from the immutable `/v/50dfe...` Version
page. The current mutable workspace was not used.

## Files

| Part | Format | Filename | Bytes | SHA256 |
|---|---|---|---:|---|
| JaD | STEP AP242 Edition 2 | `JaD_THUMB_LOWER15_APPROVED.step` | 817,422 | `622adb3b1b1d6095435aac624bb11042080fc8b7399b0c920becde708fa54e86` |
| JfD | STEP AP242 Edition 2 | `JfD_THUMB_LOWER15_APPROVED.step` | 1,446,528 | `d75f62e04df15b1150ea10eeb8da1aaa0aae7ca7c31862cea42823a0929ea340` |
| JaD | Parasolid text (`.x_t`) | `JaD_THUMB_LOWER15_APPROVED.x_t` | 1,049,588 | `2cfd9cd3d323cf45d57f59b4528eb364b5b5ab1bceb0a20692b0292a75eb2453` |
| JfD | Parasolid text (`.x_t`) | `JfD_THUMB_LOWER15_APPROVED.x_t` | 1,719,570 | `5c50f3aa199223f673eee6a9439e5c42c77a082ad9bafd9b5bcfcdcdb00155f5` |

Exact local paths:

```text
C:\Users\User\Desktop\OneGrip-Play\thumb_exact_onshape_source\JaD_THUMB_LOWER15_APPROVED.step
C:\Users\User\Desktop\OneGrip-Play\thumb_exact_onshape_source\JfD_THUMB_LOWER15_APPROVED.step
C:\Users\User\Desktop\OneGrip-Play\thumb_exact_onshape_source\JaD_THUMB_LOWER15_APPROVED.x_t
C:\Users\User\Desktop\OneGrip-Play\thumb_exact_onshape_source\JfD_THUMB_LOWER15_APPROVED.x_t
```

## STEP geometry validation

Validation mode: import-as-is, no healing, no cleaning, no transform, no
boolean and no geometry rewrite.

| Check | JaD | JfD |
|---|---:|---:|
| Import succeeds | YES | YES |
| Valid solid | YES | YES |
| Solid count | 1 | 1 |
| Face count | 190 | 507 |
| Edge count | 548 | 1,557 |
| Vertex count | 368 | 1,040 |
| Volume (mm³) | 47,672.950429 | 50,150.498071 |
| BBox min XYZ (mm) | `[-0.000004649,-61.431944125,-73.878508549]` | `[-38.779769754,-61.431944125,-73.878508549]` |
| BBox max XYZ (mm) | `[38.779769754,62.428314496,78.256783504]` | `[0.000000100,62.428314494,78.256783504]` |
| BBox size XYZ (mm) | `[38.779774404,123.860258621,152.135292053]` | `[38.779769854,123.860258619,152.135292053]` |

Separate valid solids: **PASS** — JaD and JfD are separate files and each
imports as exactly one valid solid.

## Approved opening validation

The imported STEP solids were tessellated in memory and sampled along the
already-audited frozen Thumb control axes. A control passes only when the axis
column is open, the connected open region has nontrivial area, and its centroid
remains close to the control axis. No geometry was healed or modified.

| Control | Through-opening | Sampled open area (mm²) | Centroid offset (mm) |
|---|---:|---:|---:|
| JOY | PASS | 173.2275 | 1.0387 |
| T1 | PASS | 48.1275 | 0.2448 |
| T2 | PASS | 63.2025 | 0.2693 |
| T3 | PASS | 48.1050 | 0.5959 |
| T4 | PASS | 62.1450 | 0.2249 |
| T5 | PASS | 63.2025 | 0.2693 |
| T6 | PASS | 62.1450 | 0.6716 |
| T7 | PASS | 68.4225 | 0.2541 |
| T8 | PASS | 67.0050 | 0.3951 |

**JOY + T1–T8 through-opening gate: PASS (9/9).**

Machine-readable validation: `EXPORT_VALIDATION.json`.

## Limitations / API note

- Both requested formats exported successfully through the authenticated
  Onshape Version UI.
- The API-key route remains quota-blocked with HTTP 402 `API limit exceeded`;
  it was not used for these files.
- Parasolid files have the expected text Parasolid signature. STEP files
  declare AP242 Edition 2 and both import successfully.
- No Onshape features, configuration, transforms or production files were
  modified.

