C07 INDEPENDENT FDM PRINTABILITY RESULT:

C07 SOURCE VERIFIED = YES

C07 STEP = `C:\Users\User\Desktop\OneGrip-Play\thumb_inner_housing_lab\REV_I_SOURCE_FAITHFUL_THUMB_PROTOTYPE\07_prototype\C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step`

C07 STL = `C:\Users\User\Desktop\OneGrip-Play\thumb_inner_housing_lab\REV_I_SOURCE_FAITHFUL_THUMB_PROTOTYPE\07_prototype\C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.stl`

SOURCE = `10_scripts\i10_c07_refine.py` → direct `export_step` / `export_stl`, with `07_prototype\i10_c07.json` metadata

LATEST MODIFIED = STEP and STL: 2026-08-25 10:57:53 KST; builder: 2026-08-25 10:56:22 KST

C07 LINEAGE CONFIDENCE = HIGH — export names, STEP product name, builder calls, metadata, timestamps, and hashes agree

STEP VALID = PASS

STL VALID = PASS

BEST PRINT ORIENTATION = `JOY_AXIS_UP`, `(0.000181854, 0.598493369, 0.801127739)`

JOY_AXIS_UP CONFIRMED = YES

BED CONTACT = **953.733 mm² exact coplanar BRep face**, one connected annular footprint; 0.20 mm layer section ≈ 964.08 mm² and one component. Bed span ≈ 29.76 × 42.69 mm. The projected center of mass is 1.62 mm outside the contact convex hull, 8.27 mm above the bed, so adhesion/brim quality matters despite the large area.

PART HEIGHT = **22.894 mm**

TERMINAL SLOTS PRINTABLE = **16/16**

SWITCH SEATS PRINTABLE = **8/8**, with accessible top-surface stair-step cleanup likely on the most tilted seats

THIN / OMITTED FEATURE RISK = **MARGINAL, not structural** — no interior raster area below 1.20 mm at 0.20 mm pitch, but many tiny boundary BRep facets (some 0.04–0.40 mm wide) will be quantized or omitted by a slicer. Verified load-path dimensions remain substantially larger: 1.545 mm minimum outer slot ligament, 3.895 mm inner slot web, 2.6 mm walls/slab minimum, 3.0 mm deck, and 5.6 mm structural bridges.

BRIDGE RISK = **HIGH at one re-entrant region; otherwise support-required/manageable** — the main slab underside is not a harmless 5.6 mm bridge. Its largest connected downward region is 716.28 mm², spans 33.42 mm, and is 10.22 mm above the bed. The 5.6 mm number is the in-plane width of connective members, not the unsupported ceiling span.

SUPPORT RISK = **HIGH** — 836.33 mm² of actual >45° downward surface (11.84%); projected support footprint ≈ 813.0 mm². About 778.5 mm² projects directly to the bed, 19.44 mm² would conventionally base on the joystick-deck top, and 15.06 mm² on other model surfaces.

TRAPPED SUPPORT = **1 region / 14.607 mm² / 7.443 mm maximum span**. The region is about 14.08 mm above the bed at print-local `(x, y) ≈ (7.61, 4.05)`. At several surface probes it had 0/16 clear horizontal rays, 0/48 clear downward-hemisphere rays, and no direct downward path to the bed. Its outward normal is approximately `(0.269, -0.032, -0.963)` in print coordinates, so it is a shallow downward ceiling, not a self-supporting wall. The 7.4 mm scale and builder construction make it consistent with a re-entrant standoff/pad-relief surface; that identification is an inference, while the surface and access measurements are direct.

FUNCTIONAL FACE SUPPORT CONTACT = **POSSIBLE** — 0/8 switch-seat bearing faces need support, but 19.44 mm² of projected conventional support bases coincide with the joystick-deck top. A tree/build-plate-only strategy may avoid this, but no true slicer preview was available to prove it.

LAYER-STRENGTH RISK = **LOW for button press, MODERATE for lateral joystick/standoff loading** — switch axes are 1.84–9.38° from print-up, so button loads are predominantly through-layer compression. The five 2.6 mm vertical deck links and standoff roots remain the likely interlayer shear/peel locations under lateral handling; no delamination-critical button slab region was found.

POST-PROCESS ACCESS = **MANAGEABLE overall; TRAPPED / UNACCEPTABLE at the 14.607 mm² region**. Slab underside, seats, and through-slots are accessible. The deck-top support-base area lies in the roughly 7.22 mm gap below the slab and is difficult to flatten without marking the bearing plane.

CLAUDE 27/0 RESULT INDEPENDENTLY SUPPORTED = **PARTIAL**

PRE-EXISTING SZH PACKAGING ISSUE = **SEPARATE / UNCHANGED / NOT USED TO FAIL C07 PRINTABILITY**

C07 FDM-SPECIFIC BLOCKER = **YES — the inaccessible 14.607 mm² downward region creates a forced choice between trapped support and an unverified unsupported shallow ceiling on a pad/relief-scale functional area.**

## VERDICT

**C — C07 HAS A REAL FDM BLOCKER BEFORE PRINTING**

## Independent integrity results

| Check | Independent result |
|---|---:|
| STEP import | PASS; OCCT/build123d `Solid` |
| STEP solids / shells / faces | 1 / 1 / 333 |
| STEP validity | valid |
| STEP volume | 7378.019745 mm³ |
| STL triangles / vertices | 2032 / 962 welded at 1 µm |
| STL connected components | 1 |
| Open / non-manifold edges | 0 / 0 |
| Bad shared-edge orientation | 0 |
| Degenerate triangles | 0 |
| Stored-normal mismatches | 0 |
| Self-intersection pairs detected | 0 |
| STL signed volume | +7378.040811 mm³ |
| STEP ↔ STL volume difference | 0.021066 mm³ / 0.000286% |
| STEP ↔ STL maximum bbox difference | 0.00000156 mm |
| Tiny detached fragments | none |

SHA-256:

```text
STEP    45BB7E3076692CC162359FC36B9CD30B0CD1A3197E2A99F906CDDA1DAA17E024
STL     50E962F471940CF0D3973E6714E6FFA6BA0B1C23C0143430E0E1D8B160C37A76
BUILDER 8101D6A5E09608DA0BFE739EEDBB539C10F71515D811818B3A7B5837A1CBF01C
```

## Orientation comparison

The side candidates were derived from principal in-plane axes of the actual STL, not copied from the prior audit. A search over 240 substantial surface-normal candidates independently converged to `(0.000000, 0.598238, 0.801319)`, within about 0.02° of `JOY_AXIS_UP`.

| Orientation | Height mm | Exact bed mm² | Support mm² | Support % | Practical result |
|---|---:|---:|---:|---:|---|
| JOY_AXIS_UP | 22.89 | 953.70 STL / 953.733 STEP | 836.33 | 11.84 | best, but support blocker remains |
| inverted | 22.89 | 0 coplanar | 1798.78 | 25.46 | seat faces downward; unstable contacts |
| major side A | 61.41 | 0 coplanar | 688.79 | 9.75 | tall, point/edge contact, poor cleanup and load orientation |
| major side A inverted | 61.41 | 4.38 | 661.72 | 9.37 | 1.75 × 3.00 mm contact, severe tipping |
| major side B | 42.69 | 0 coplanar | 1061.60 | 15.02 | point/edge contact and more support |
| major side B inverted | 42.69 | 5.97 | 1054.44 | 14.92 | tiny contact and poor functional surfaces |

The earlier 977.4 mm² bed / 812.6 mm² support pair is not reproduced under a strict contact definition. Its 0.40 mm bed band classifies approximately 23.7 mm² of low sloped surface as bed contact. Exact coplanar contact is 953.733 mm²; assigning those low slopes to support raises the downward surface total to 836.33 mm². The discrepancy is definitional, not STEP/STL damage.

## First layer and bed realism

- The exact bed face is one coherent annular joystick-deck underside, not islands. A 0.15 mm raster produced one 953.73 mm² dominant component plus a 0.11 mm² sampling artefact; exact triangle and BRep connectivity are both one component.
- None of the three shell standoffs reaches the bed plane. The joystick deck alone defines the intended bed. No lower pad or accidental protrusion was found.
- At 0.20 mm above the bed, the part is still one connected 964.08 mm² section.
- The deck perimeter is deliberately only about 0.35 mm from the shell authority. Normal elephant foot can consume much of that clearance. The outer deck edge and central aperture are reachable for deburring after bed removal.
- The 1.62 mm negative free-standing COM margin gives a small peel moment toward the button slab. The footprint area is generous, but a clean plate, normal brim, and controlled first layer are prudent.

## Terminal slots and switch seats

All 16 openings were sampled from the actual STL in each frozen seat frame, 0.8 mm below the bearing plane:

- width: 1.30 mm on 15 slots and 1.31 mm on one raster sample;
- length: 6.38 mm sampled versus 6.40 mm nominal;
- clear at all 80 depth samples per slot over 0.1–8.0 mm;
- inner wall between slot pair: 3.895–3.900 mm;
- minimum outer ligament to the 9.6 mm seat column: 1.545–1.550 mm.

A 1.30 mm through-opening is representable by a normal 0.4 mm nozzle, but extrusion swell and support-interface expansion can reduce it. All slots are open from the bearing side and can be reached with a 1.2 mm file or a 1.5 mm drill turned by hand. Minor reaming is realistic; aggressive powered drilling is not.

All eight bearing surfaces remain upward-facing and unsupported. A 0.10 mm actual-mesh sampling measured about 23.40 mm² of material in each 6.02 × 6.04 mm footprint; the sampling result is consistent across all eight. At 0.16–0.24 mm layers, the 9.36–9.38° T1/T3 planes produce roughly 0.97–1.46 mm terrace pitch and up to one-layer height quantization. The faces are accessible from above for light flat sanding. T7/T8 are only 1.84° off the bed plane and have much wider terrace spacing.

## Joystick deck

- The 3.0 mm deck underside is the bed face; it needs no support and should print flat.
- The outer wall is vertical in the chosen frame and the deck-to-wall roots are continuous.
- The actual central aperture is a **12 × 12 mm square**, because the builder uses a box cut. It is not the Ø16 mm hole described in `HAND_FINISH_MAP.md`. This documentation/hand-finish inconsistency is not used as an SZH packaging failure, but any aperture enlargement instruction must be treated cautiously.
- The provisional joystick can only be trial-fitted to the printed deck after the separate SZH PCB/cavity issue is resolved. That packaging issue is outside this verdict.
- Conventional vertical support projection places about 19.44 mm² of support base on the deck top. This surface is accessible only through the shallow deck-to-slab space and may be difficult to restore perfectly flat.

## Support, bridges, and removal

The actual >45° downward surface divides into nine edge-connected regions. The principal regions are:

| Downward region | Area mm² | Maximum plan span mm | Mean height above bed mm | Access result |
|---|---:|---:|---:|---|
| slab underside | 716.28 | 33.42 | 10.22 | open; up to 15/16 horizontal and 48/48 downward rays clear |
| pad/ledge | 47.72 | 7.44 | 5.34 | open |
| pad/ledge | 32.86 | 7.55 | 16.45 | open, narrower access |
| low perimeter | 16.91 | 12.34 | 0.26 | bed-adjacent and open |
| **re-entrant ceiling** | **14.61** | **7.44** | **14.08** | **0/16 horizontal, 0/48 downward, no bed path** |

The 716 mm² slab region is not intended to bridge unsupported; it requires normal support and is broadly reachable with pliers/flush cutters. The 14.61 mm² region is different: support cannot be given a straight removal path, while suppressing it leaves a 7.44 mm, about 15.7°-from-horizontal ceiling. The face also sits at the same scale as the claimed standoff skirt.

The builder's claimed 45° standoff skirt is not literally constructed as a taper: it unions a 7.4 × 7.4 mm full box with a nested 5 × 5 mm box. The larger prism dominates rather than producing a frustum. This does not invalidate the whole solid, but it agrees with the presence of pad-scale downward/concave faces and prevents accepting the “self-supporting pad” claim on code intent alone.

No installed headless slicer CLI was usable. Bambu Studio's GUI executable is installed, but `--help` produced no console interface or profile-driven slice output. Therefore support quantities and contacts above are geometry-based, not a true G-code preview. That limitation makes the inaccessible region a pre-print blocker rather than something that can be waived on an assumed slicer result.

## Layer strength and likely failure modes

Concrete failure modes found:

1. **Trapped support or inaccessible sag:** the 14.61 mm² re-entrant ceiling is the decisive blocker.
2. **Support welding to the deck top:** approximately 19.44 mm² under conventional vertical projection; tree/build-plate-only behavior is unverified.
3. **Bed peel / detachment:** the COM projection is 1.62 mm beyond the contact hull despite 953.7 mm² contact.
4. **Elephant-foot interference:** deck perimeter clearance to the shell is only about 0.35 mm, and the central square aperture can close slightly.
5. **Slot closure:** 1.30 mm is printable but likely to need 0.1–0.2 mm reaming after support cleanup.
6. **Bearing-plane stair stepping:** T1/T3 are shallow upper slopes and may need accessible flat sanding.
7. **Layer seam at narrow load paths:** lateral joystick handling can peel/shear 2.6 mm vertical links or standoff roots; normal button press does not create the same risk.

No evidence was found for STL opening, non-manifoldness, inverted normals, self-intersection, floating debris, structural sub-nozzle interior walls, or a button-seat support interface.

## Hand-finish realism cross-check

| Map item | Independent classification | Reason |
|---|---|---|
| H1 cap profile | out of C07-core scope | applies to separate printed caps, not this core |
| H2 terminal slots | REALISTIC | all 16 are through-open and reachable by hand file/reamer |
| H3 deck rim removal | QUESTIONABLE | reachable, but up to 3 mm near five wall landings is load-path-sensitive and depends on real SZH hardware |
| H4 joystick mounting holes | REALISTIC, conditional | accessible with the real PCB as a drill template; proximity limits matter |
| H5 solder-tail aperture | QUESTIONABLE | the actual aperture is 12 × 12 square, not the map's Ø16 starting condition |
| H6 standoffs | QUESTIONABLE overall; NOT PRACTICAL at the re-entrant face | exposed pad faces can be filed, but the measured inaccessible region cannot |
| H7 slab-underside support | MANAGEABLE in bulk; NOT PRACTICAL at one region | main slab is open; 14.61 mm² region is trapped by straight-path tests |
| H8 first-layer cleanup | REALISTIC | deck underside and perimeter are exposed after bed removal |

## Concrete blocker/cautions only

- **Blocker:** one 14.607 mm², 7.443 mm-span re-entrant downward face cannot accept removable conventional support and is not self-supporting at its measured slope.
- **Caution:** conventional support projection can base on 19.44 mm² of the joystick deck's functional top surface.
- **Caution:** the bed footprint is large but slightly cantilevered; the COM is 1.62 mm beyond its convex hull.
- **Caution:** expect light slot reaming, bearing-face sanding, and deck-perimeter elephant-foot cleanup.

No C07, REV_I, `docs/`, or `docs/101` source file was modified. All audit scripts, JSON, and six images are isolated under `codex_audits\C07_FDM_PRINTABILITY`.
