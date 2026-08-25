# C07.1 Conservative FDM Simplification Report

Date: 2026-08-25  
Scope: isolated manufacturing-geometry simplification of validated C07 only  
Candidate: `C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED`  
Production status: **not applied**

## Outcome

C07.1 preserves the frozen C07 button, joystick, cap/seat, and docs/101 integration datums while replacing the ad-hoc connector system with a smaller explicit load graph and one continuous joystick-deck chord wall. The three non-datum dynamic standoff pads were removed. This eliminates the independently audited 14.607 mm² trapped-support region and reduces predicted support contact on the critical joystick-deck functional surface from 19.4375 mm² to 0.0000 mm².

The final STEP and STL each contain one connected, valid solid. No detached fragment is present in either export. A 6.840 mm³ fragment created transiently by the shell-guard Boolean is discarded before export by deterministic main-solid selection; the exported topology is independently rechecked below.

## Authority and isolation

Read-only C07 authority:

- STEP SHA-256: `45BB7E3076692CC162359FC36B9CD30B0CD1A3197E2A99F906CDDA1DAA17E024`
- STL SHA-256: `50E962F471940CF0D3973E6714E6FFA6BA0B1C23C0143430E0E1D8B160C37A76`
- `i10_c07_refine.py` SHA-256: `8101D6A5E09608DA0BFE739EEDBB539C10F71515D811818B3A7B5837A1CBF01C`

Post-work hashes match the independent pre-work audit. C07 was not overwritten.

C07.1 isolated exports:

- STEP: `outputs/C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED.step`
  - SHA-256: `0A02857CEE5A31ECBC59A4D2D7D67E55FF3DFD9B5FE185D1A80641A01F189116`
- STL: `outputs/C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED.stl`
  - SHA-256: `2B1CFC95E8E482A3C0CF30DD4CA15564F464F8BC03E57921742B2663210E2502`

All candidate code, validation, and images remain under `codex_work/C07_1_FDM_SIMPLIFICATION`.

## Structural changes

| Element | C07 | C07.1 |
|---|---:|---:|
| Carrier bridge graph | 16 generated connections | 10 explicit broad bridges |
| Joystick deck walls | 5 short radial walls | 1 continuous 2.60 mm chord wall |
| Dynamic shell standoffs | 3 | 0 |
| New structural minimum | nominal 2.60 mm | 2.60 mm |
| Deck thickness | 3.00 mm | 3.00 mm, unchanged |
| Deck aperture | 12.00 mm | 12.00 mm, unchanged |

The ten explicit bridge pairs are T1–T5, T5–T3, T4–T2, T2–T6, T7–T8, T1–T4, T5–T2, T3–T6, T4–T7, and T6–T8. They form three readable longitudinal rails plus cross ties. The longest center-to-center bridge distance is 16.293 mm at T7–T8.

## Frozen function validation

| Requirement | Result |
|---|---:|
| Switch seats | 8/8 printable and preserved |
| Terminal slots | 16/16 open |
| Minimum measured slot width | 1.300 mm |
| Minimum measured slot length | 6.380 mm |
| T7 bearing area | 23.400 mm² |
| T8 bearing area | 23.400 mm² |
| Switch-body intersections, T1–T8 | 0.0000 mm³ each |
| Actuator intersections, T1–T8 | 0.0000 mm³ each |
| Cap underside → seat | 4.759 mm, unchanged |
| JOY axis maximum component delta | 0.000000 mm |
| Joystick deck-plane delta | 0.000000 mm |
| Joystick deck usable BRep area | 939.029 → 949.885 mm² |

All compared frozen metadata—print axis/origin, bed and slab planes, eight seat planes, deck top, deck thickness, aperture, SZH raise, and source-faithful deck-to-skin height—has exactly zero numerical delta.

## docs/101 and assembly revalidation

| Check | C07.1 result |
|---|---:|
| JaD shell interference | 0.000000 mm³ |
| JfD shell interference | 0.000000 mm³ |
| Eight Finger pocket collisions | 0.0000 mm³ each |
| Eight Finger body collisions | 0.0000 mm³ each |
| Eight Finger actuator collisions | 0.0000 mm³ each |
| Eight Finger terminal collisions | 0.0000 mm³ each |
| N1 clearance | 0.522545 mm (C07: 0.521657 mm) |
| N2 clearance | 2.322125 mm (C07: 2.315730 mm) |
| Valid split-normal placement paths | `+U / JfD` and `-U / JaD` |
| Required Sequence A | PASS |
| Already-invalid reverse Sequence B | remains blocked only by N1/N2 service corridors |

The approved order remains: Finger switches installed/epoxied → shell half open → Thumb core placed → opposite shell half closes.

## FDM validation — JOY_AXIS_UP

| Metric | C07 | C07.1 | Change/result |
|---|---:|---:|---:|
| Connected STEP solids | 1 | 1 | PASS |
| STEP valid | yes | yes | PASS |
| STL open/non-manifold edges | 0 / 0 | 0 / 0 | PASS |
| STL self-intersections | 0 | 0 | PASS |
| Exact coplanar bed area | 953.733 mm² | 969.540 mm² | +1.66% |
| Print height | 22.894 mm | 17.625 mm | −23.01% |
| Support-required surface | 836.326 mm² | 708.430 mm² | −15.29% |
| Support-required fraction | 11.836% | 10.474% | improved |
| Non-removable support | 14.607 mm² / 1 region | 0.000 mm² / 0 regions | target met |
| Critical deck support landing | 19.4375 mm² | 0.0000 mm² | target met |
| Other-model support landing | 15.0625 mm² | 1.1875 mm² | reduced |
| First-layer components | 1 | 1 | PASS |
| Sampled interior area below 1.20 mm | — | 0.000 mm² | PASS |
| Sampled thickness, 1st percentile | — | 1.298 mm | above absolute target |

The worst remaining overhang is the broad, flat carrier underside: 669.634 mm², 31.434 mm maximum region span, approximately 10.22 mm above its support landing. It still requires support, but all sampled approach/downward paths are open and post-process accessible. No measured support region is trapped. Support prediction is geometry-based at 45° and is not a substitute for a printer/material-specific slicer preview.

## Complexity comparison

| Metric | C07 | C07.1 | Change |
|---|---:|---:|---:|
| Volume | 7378.020 mm³ | 6694.168 mm³ | −9.27% |
| BRep faces | 333 | 247 | −25.83% |
| BRep edges | 1039 | 756 | −27.24% |
| Edges shorter than 0.40 mm | 102 | 45 | −55.88% |
| Faces smaller than 0.25 mm² | 35 | 15 | −57.14% |

Exact Boolean comparison gives 6296.757 mm³ common volume, 1081.263 mm³ removed, and 397.412 mm³ added. Added material is concentrated in the coherent chord-wall/load-path replacement; removed material is the redundant web, wall, and standoff system.

## Evidence files

- `validation/C07_1_FDM_VALIDATION.json` — STEP/STL, orientation, first layer, support access, slots and seats
- `validation/C07_VS_C07_1_COMPARISON.json` — frozen-datum, function, docs/101, FDM, and complexity comparison
- `validation/docs101/j02_collision.json` — docs/101 collision/clearance results
- `validation/assembly/j05_assembly_sequences.json` — required assembly-sequence result
- `renders/01_full_core.png` through `renders/08_docs101_n1_interface.png` — eight same-camera comparisons

The known provisional SZH web-model packaging issue is unchanged and remains outside this FDM verdict; actual SZH hardware remains the authority.

## Verdict

**A — C07.1 SIMPLIFICATION PASSED — READY FOR INDEPENDENT SLICER REVIEW**

Work stops at the isolated candidate, comparison, validation, renders, and verdict. No production apply was performed.
