# C09 — Independent Continuous Curved Carrier Thumb Architecture

Date: 2026-08-26  
Scope: isolated feasibility, full 8-button candidate, docs/101 integration, assembly, FDM, and C07.1 comparison  
Production status: **not applied**

## Outcome

```text
TWO-BUTTON FEASIBILITY = PASS

B — C09 WORKS BUT DOES NOT CLEARLY IMPROVE ON C07.1
```

C09 proves the requested architecture: one continuous, curved, open ladder carrier lies below the Thumb row; eight broad supports rise from it; and each support terminates in a flat switch seat normal to its frozen press axis. It is not the C08 shell-conformal collar system and it is not the C07/C07.1 remote slab.

The decisive C08 failure is resolved. The complete C09 core can be inserted as one piece along `-U` into the open JaD half with **0.000000 mm³** sweep interference over 30 mm. The alternate `+U`/JfD path has a small real block (maximum 0.226183 mm³), so the valid assembly direction is one-sided and explicit.

C09 does not earn verdict A because it exchanges C07.1's slab for a clearer load path but increases B-rep complexity and support area. It also retains a reduced, pre-existing SZH web-model overlap. C07.1 remains the safer practical baseline.

## 1. Isolation and authority

All generated files are under:

`codex_work/C09_CONTINUOUS_CURVED_CARRIER/`

Read-only integration authority:

- docs/101 JaD and JfD frozen shell STEP files
- docs/101 combined reference
- docs/101 all-eight detailed Finger switch placement
- REV_I frozen Thumb seat, cap, press-axis, and JOY metadata
- C07.1 STEP/STL/report and REV_K C08 report as comparison references

No production file, C07.1 file, C08 file, docs/101 geometry, or Claude REV folder was modified.

## 2. Architecture built

The lower carrier is one connected curved ladder:

- 3 longitudinal curved rails, 4.40 mm wide × 2.20 mm thick
- 3 broad cross ties, 4.60 mm wide × 2.20 mm thick
- 8 upward supports, nominal 7.00 mm × 7.00 mm
- 8 frozen flat seats, 9.60 mm square × 2.60 mm thick
- 2 side deck walls, 3.40 mm thick, positioned outside the central SZH corridor
- source-faithful JOY deck, 3.00 mm thick, Ø12.00 mm aperture

The load path is:

```text
button / switch
  -> flat frozen-axis seat
  -> broad upward support
  -> continuous curved ladder carrier
  -> two side walls
  -> source-faithful JOY deck
```

There are no per-opening conformal shell collars and no shell-curvature hooks.

### Actual shell/carrier spacing

The sketch's approximately 1 mm-class relationship was treated as an initial intent, not forced. The actual carrier-to-shell surface spacing is:

| metric | spacing |
|---|---:|
| minimum | 4.621 mm |
| p05 | 6.280 mm |
| median | 8.066 mm |
| p95 | 10.331 mm |

Moving the carrier outward toward 1 mm would place it above the frozen seat system or recreate the C08 opening-by-opening interlock. The deeper offset preserves the frozen button stack, terminal escape, printability, and one-piece assembly.

## 3. First feasibility gate

Cases were selected from the prior measured site survey:

- EASY: T2
- HARD: T8, nearest JOY/SZH region

| gate | T2 EASY | T8 HARD |
|---|---:|---:|
| valid connected solid | PASS | PASS |
| frozen centre / axis | 0 mm / 0° | 0 mm / 0° |
| bearing area | 23.40 mm² | 23.40 mm² |
| terminal slots | 2 × 1.30 × 6.40 mm | 2 × 1.30 × 6.40 mm |
| terminal free depth | 35.589 mm | 11.839 mm |
| source protrusion law | 1.066 mm | 1.211 mm |
| shell interference | 0.000000 mm³ | 0.000000 mm³ |
| docs/101 Finger interference | 0.000000 mm³ | 0.000000 mm³ |
| confident-static SZH interference | 0.000000 mm³ | 0.000000 mm³ |
| local one-piece sweep | PASS both split directions | PASS both split directions |
| trapped support regions | 0 | 0 |

The provisional 25° moving-envelope overlap at T8 is 352.521 mm³. It is reported separately and did not fail the gate.

`h03_placement` represents all possible terminal material as one 7.568 × 4.632 mm rectangular envelope, not two physical terminals. That conservative envelope intersects every correct flat seat by about 82 mm³ and is not a collision gate. The actual gates are the two measured slots, free depth, and zero body/actuator intersection.

## 4. Full button function

All eight frozen seat planes have normal error 0°. All seats provide 23.40 mm² sampled bearing area. All sixteen slots measure 1.30 × 6.40 mm.

| button | bearing | terminal free depth | source protrusion law |
|---|---:|---:|---:|
| T1 | 23.40 mm² | 35.989 mm | 1.385 mm |
| T2 | 23.40 mm² | 35.589 mm | 1.066 mm |
| T3 | 23.40 mm² | 35.731 mm | 1.459 mm |
| T4 | 23.40 mm² | 34.271 mm | 1.291 mm |
| T5 | 23.40 mm² | 36.293 mm | 1.166 mm |
| T6 | 23.40 mm² | 34.161 mm | 1.338 mm |
| T7 | 23.40 mm² | 11.845 mm | 1.200 mm |
| T8 | 23.40 mm² | 11.839 mm | 1.211 mm |

The frozen cap-underside-to-seat distance remains exactly 4.759 mm. Because centre, axis, cap and seat datums are unchanged, the REV_J docs/101 measured protrusion range of approximately 1.053–1.424 mm is unchanged; the table shows the original source law values used by the build metadata.

## 5. docs/101 integration

Shell interference is zero against both halves:

| shell | C09 intersection |
|---|---:|
| JaD | 0.000000 mm³ |
| JfD | 0.000000 mm³ |

Per-Finger pocket, body, actuator and terminal intersections are all 0.0000 mm³:

| Finger | pocket | actual switch | minimum clearance | service corridor |
|---|---:|---:|---:|---:|
| N1 | 0.0000 | 0.0000 | **0.5216 mm** | 431.29 mm³ blocked |
| N2 | 0.0000 | 0.0000 | 2.3146 mm | 44.47 mm³ blocked |
| I2 | 0.0000 | 0.0000 | 7.9784 mm | 0.00 mm³ |
| I3 | 0.0000 | 0.0000 | 10.2004 mm | 0.00 mm³ |
| I4 | 0.0000 | 0.0000 | 10.2345 mm | 0.00 mm³ |
| M3 | 0.0000 | 0.0000 | 23.5480 mm | 0.00 mm³ |
| M4 | 0.0000 | 0.0000 | 23.3807 mm | 0.00 mm³ |
| N3 | 0.0000 | 0.0000 | 19.4507 mm | 0.00 mm³ |

The approved order remains Finger switches first, C09 core second, opposite shell half last. N1/N2 are assembly-order constraints, not static collisions.

## 6. One-piece assembly

Exact B-rep sweep against one open half, sampled every 1 mm for 30 mm:

| path | sum interference | maximum | first block | result |
|---|---:|---:|---:|---|
| `-U` into open JaD | **0.000000 mm³** | **0.000000 mm³** | none | **PASS** |
| `+U` into open JfD | 1.659682 mm³ | 0.226183 mm³ | 1 mm | FAIL |

The one-piece architecture therefore has one valid realistic split-shell insertion/removal direction. C08 had no clear direction and its best path still accumulated 505.2 mm³; C09 removes that architectural lock.

## 7. Joystick coordination

| check | result |
|---|---:|
| JOY centre / axis change | 0 |
| JOY axis blocked by C09 | 0.0000 mm |
| deck height delta | 0.0000 mm |
| deck top below skin | 23.993 mm |
| deck thickness / aperture | 3.00 mm / Ø12.00 mm |

Confident-static web-model overlaps are reported, not hidden:

| SZH item | C07.1 | C09 | interpretation |
|---|---:|---:|---|
| PCB | 43.298 mm³ | **15.391 mm³** | pre-existing model issue, reduced 64.4% |
| removable header | 14.273 mm³ | **2.044 mm³** | removable item, reduced 85.7% |
| gimbal / pots / push switch / shaft | 0 | 0 | clear |

The provisional moving-envelope overlap is 1664.811 mm³ and remains outside the static verdict. Actual SZH hardware measurement is still the correct authority before production.

## 8. FDM manufacturability

Intended orientation: `JOY_AXIS_UP`, 0.4 mm nozzle-class prototype.

| metric | C09 |
|---|---:|
| STEP solid / valid | 1 / yes |
| STL connected components | 1 |
| STL open / non-manifold edges | 0 / 0 |
| degenerate triangles | 0 |
| bed contact | 975.504 mm², 1 component |
| print height | 17.625 mm |
| support-required area | 846.392 mm² (11.780%) |
| trapped support regions | **0** |
| feature-normal minimum | **1.55 mm**, terminal-slot outer ligament |
| rail / tie / seat / deck / wall | 2.20 / 2.20 / 2.60 / 3.00 / 3.40 mm |

The 1.55 mm minimum passes the 1.20 mm requirement but misses the preferred 1.60 mm target by 0.05 mm.

A JOY-axis column raster reports 0.84 mm² below 1.20 mm. `C09_THIN_PROBE.json` localizes all 21 cells to one inclined terminal-slot edge. This is a diagonal chord through a full 1.55 mm feature-normal ligament, not a feather wall. It remains recorded for slicer review.

No trapped or inaccessible support cavity was found. The remaining support surfaces are externally accessible, but C09 needs more support than C07.1.

## 9. C07.1 vs C09

| metric | C07.1 | C09 | outcome |
|---|---:|---:|---|
| one-piece assembly | PASS, two split directions | PASS, one split direction | C07.1 stronger |
| shell collision | 0 | 0 | tie |
| Finger collision | 0 | 0 | tie |
| N1 clearance | 0.5225 mm | 0.5216 mm | effectively unchanged; C07.1 slightly higher |
| volume | 6694.168 mm³ | **6047.075 mm³** | C09 −9.67% |
| B-rep faces | **247** | 372 | C09 +50.6% |
| major structural members | 13 | 16 | C07.1 fewer |
| support-required area | **708.430 mm²** | 846.392 mm² | C09 +19.5% |
| support fraction | **10.474%** | 11.780% | C07.1 lower |
| trapped support | 0 | 0 | tie |
| minimum feature thickness | p1 1.298 mm sampled | 1.55 mm feature-normal | C09 stronger nominal ligament |
| button seats | 8/8 | 8/8 | tie |
| terminal slots | 16/16 | 16/16 | tie |
| joystick | integrated frozen deck | integrated frozen-height deck | tie; C09 reduces SZH overlap |
| load path | seat → slab/bridges → wall → deck | seat → support → curved ladder → side walls → deck | C09 clearer |

The C09 architecture is conceptually clearer and lighter, and it solves C08's lock. Its exact B-rep is nevertheless more complex than C07.1 and its FDM support burden is worse. Its N1 margin does not materially improve.

## 10. Deliverables and hashes

Primary files:

- `outputs/C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.step`
- `outputs/C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.stl`
- `outputs/C09_CONTINUOUS_LOWER_CURVED_CARRIER.step`
- `validation/C09_FEASIBILITY_GATE.json`
- `validation/C09_VALIDATION.json`
- `validation/C07_1_VS_C09_COMPARISON.json`
- `validation/C09_THIN_PROBE.json`
- `C07_1_VS_C09_COMPARISON.md`
- `renders/01_gate_T2.png` through `renders/08b_C09_same_camera.png`

SHA-256:

| file | hash |
|---|---|
| C09 STEP | `125F7C0AA264DCD56364077B9328A8FA30CAA2F9A319B9847512B1C35FE2B2BF` |
| C09 STL | `22DEA5F9C1F8A7480F6596FA062E45E3AA42CD3CD96741FE79EC0EEE6E77A4BE` |
| validation JSON | `D835104F40A83D009296C0C581AE73A5B1227709FD6D848E2C0BE88D5DC1D0BC` |
| builder | `B45FD231ADFE38B7BF12D147B950F402F9DAC8040AEA1285FB75801C597BDCB0` |
| validator | `682D209081A304E0089EB41B27292CF0EAC2256982933A2CEDD20D11F86D3BB0` |

The validation/builder hashes above are refreshed in the final inventory after this report is written; the JSON itself also embeds the geometry and script hashes used by its run.

## Final verdict

```text
TWO-BUTTON FEASIBILITY = PASS

B — C09 WORKS BUT DOES NOT CLEARLY IMPROVE ON C07.1
```

C09 is a valid independent architecture and a useful design branch. It is one-piece assembleable, collision-free against the frozen shell and all docs/101 Finger geometry, functionally complete at all eight seats, and FDM-plausible without trapped support. It should not replace C07.1 yet because support area and exact geometry complexity are worse, only one split-shell direction is clear, the preferred 1.60 mm ligament is missed by 0.05 mm, and physical SZH confirmation remains outstanding.

No production apply was performed.

