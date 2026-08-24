# FINAL SOURCE AUDIT

## 1. FOUND / NOT FOUND

**EXACT APPROVED ONSHAPE SOURCE FOUND**

## 2. BEST SOURCE

```text
Document: OneGrip_Play_V1
DID: a21e64f36bc61df760d4587c

Workspace / Version: Main / THUMB_LOWER15_HOUSING_V1
WID / VID: ef6a7b3ccc45186203e4d2ca / 50dfe4e752e447375b95493a

Microversion: UNKNOWN — UI does not expose it; API GET quota returned HTTP 402

Element / Part Studio: Joystick
EID: 425d9199b59cfb1efd9ddc35
Element type: Part Studio

Parts:
  Joystick_1 / JaD
  Joystick_2 / JfD
Supporting rigid cluster:
  Backplate / RYDD
  8 original cap solids / RAED, RAEH, RAEL, RBED, RBEH, RBEL, RDED, RDEH

Configuration: default
Geometry type: C — Part Studio containing multiple exact native solids
```

Version URL:

`https://cad.onshape.com/documents/a21e64f36bc61df760d4587c/v/50dfe4e752e447375b95493a/e/425d9199b59cfb1efd9ddc35`

## 3. WHAT IT CONTAINS

```text
Approved outer skin: YES
Inner wall: YES
JOY opening: YES
T1-T8 openings: YES — all eight
Both shell halves: YES
Exact BRep: YES
```

`JaD/JfD` are complete native solid shell halves, not surface-only patches.
The saved Part Studio also contains the original Backplate and eight moved cap
solids. Local derived meshes are each one-component and watertight; the native
feature lineage moves the original 36 opening faces rather than rebuilding the
openings from approximate cutters.

## 4. EXPORT

```text
Direct Parasolid export possible: YES
Direct STEP export possible: YES
```

The authenticated part context menu exposed both PARASOLID (versions 25.0–37.1)
and STEP (AP242/AP214/AP203) for individual `JaD` and `JfD` parts. No export was
executed during this audit, so no translation job or CAD write was submitted.

## 5. LINEAGE

```text
OneGrip_Play_V1 exact native Part Studio
→ Main workspace lower-15 write
→ THUMB_LOWER15_HOUSING_V1 (VID 50dfe4e752e447375b95493a)
→ exact JaD/JfD solid shell halves with original openings moved rigidly
→ GET-only JaD/JfD STL tessellation
→ regional LOWER15 Thumb visual graft
→ user-approved Maximum-Lowered Thumb exterior
```

## 6. CONFIDENCE

**HIGH**

The immutable version name, VID, transform, feature IDs, 202-feature/30-solid
inventory, `JaD/JfD` partIds, exact-solid UI classification, local exporter,
mesh fingerprints and nine-opening measurement all converge on the same source.
Only the optional MID remains unavailable; this does not weaken the immutable
VID authority.

## 7. NEXT ACTION

**USE EXACT ONSHAPE SOURCE AS REV_D AUTHORITY**

Stop here. Do not rebuild, recut, patch, transform, or apply anything to
production in this audit.

