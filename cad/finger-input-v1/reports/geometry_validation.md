# Finger input V1 geometry validation

Generated: `2026-08-13T23:16:46+09:00`

**Overall: PASS** — 903 passed, 0 failed.

## Artifact round-trip

| Format | Files | Readable | Valid |
|---|---:|---:|---:|
| 3MF | 103 | 103 | 103 |
| STEP | 103 | 103 | 103 |
| STL | 73 | 73 | 73 |

Cross-format STL/STEP/3MF dimension comparisons: **103/103 passed** (maximum allowed delta 0.10 mm).

## Mechanism states

Volumes, clearances, and nearest-point coordinates are exact OpenCascade B-rep results. Side-key shell results remove only the two intentional pivot-ear bearing envelopes.

| Preset | State | Minimum key-key clearance | Maximum prohibited key-shell volume |
|---|---|---:|---:|
| index | neutral | 0.636019 mm | 0.00000000 mm³ |
| index | left | 0.558574 mm | 0.00000000 mm³ |
| index | center | 0.636019 mm | 0.00000000 mm³ |
| index | right | 0.558574 mm | 0.00000000 mm³ |
| middle | neutral | 0.637239 mm | 0.00000000 mm³ |
| middle | left | 0.572250 mm | 0.00000000 mm³ |
| middle | center | 0.637239 mm | 0.00000000 mm³ |
| middle | right | 0.572250 mm | 0.00000000 mm³ |
| ring | neutral | 0.636502 mm | 0.00000000 mm³ |
| ring | left | 0.574645 mm | 0.00000000 mm³ |
| ring | center | 0.636502 mm | 0.00000000 mm³ |
| ring | right | 0.574645 mm | 0.00000000 mm³ |
| pinky | neutral | 0.634474 mm | 0.00000000 mm³ |
| pinky | left | 0.573230 mm | 0.00000000 mm³ |
| pinky | center | 0.641761 mm | 0.00000000 mm³ |
| pinky | right | 0.573230 mm | 0.00000000 mm³ |

## Side follower evidence

| Preset | Side | Lateral cam offset | Neutral cam contact distance | Full cam contact distance |
|---|---|---:|---:|---:|
| index | left | 0.041974 mm | 0.00000000 mm | 0.00000000 mm |
| index | right | 0.041974 mm | 0.00000000 mm | 0.00000000 mm |
| middle | left | 0.041974 mm | 0.00000000 mm | 0.00000000 mm |
| middle | right | 0.041974 mm | 0.00000000 mm | 0.00000000 mm |
| ring | left | 0.041974 mm | 0.00000000 mm | 0.00000000 mm |
| ring | right | 0.041974 mm | 0.00000000 mm | 0.00000000 mm |
| pinky | left | 0.041974 mm | 0.00000000 mm | 0.00000000 mm |
| pinky | right | 0.041974 mm | 0.00000000 mm | 0.00000000 mm |

## Adjustment and integration interfaces

- Wedge slopes: -8deg=-8.000000°, +0deg=-0.000000°, +8deg=8.000000°.
- Mount usable slot travel: 16.000 mm; clamp angle: 7.993023°.
- Fixture module-hole/carrier-slot alignment: PASS.
- Array/rail attachment: PASS.

## A/C comparator state checks

- variant_a: neutral=PASS, left=PASS, center=PASS, right=PASS.
- variant_c: neutral=PASS, left=PASS, center=PASS, right=PASS.

## Failures

None.

## Scope boundary

This report validates digital file structure, imported B-rep validity, nonempty dimensions/volume, cross-format consistency, and nominal CAD kinematics. It does not establish printed tolerance, fatigue life, switch force variation, user comfort, or clinical suitability; those require the documented physical test protocol.
