# THUMB / INDEX / MIDDLE ergonomic and fragment read-only audit

## 0. Scope and source

- CAD mutation: **0**. Feature 생성/수정/삭제/suppress와 version/workspace 변경을 하지 않았다.
- source Part Studio: `Joystick` / `425d9199b59cfb1efd9ddc35`
- source version: `ITS1105_SAME_SKU_8BTN_FINAL` / `e05a9ff0fa5a7bd51eb848a7`
- right-hand mirror version: `ITS1105_RIGHT_HAND_8BTN_FINAL` / `f24e655bc9b1b5dc97189a55`
- configuration: `default`
- 이번 GET에서 final version의 records는 `32 = 30 solid + 2 wire`로 재확인했다.
- Onshape가 이후 GET에 daily quota `429`와 약 8시간의 `Retry-After`를 반환했다. immutable version의 기존 final audit와 Onshape에서 이미 export한 right-hand final 30-part STL을 사용했다. 오른손판은 `X -> -X`만 적용하므로 volume, connected-component, thickness, pure-Z clearance 판정은 좌측 source와 동일하다.
- ergonomic reach는 CAD에 anthropometric hand model이 없으므로 **visible control-center distance와 control/holder envelope clearance를 reach proxy**로 사용했다. 최종 인체공학 확정은 hand mock-up 또는 physical grip test가 필요하다.

## 1. Current thumb ↔ INDEX/MIDDLE relation

Thumb rigid cluster는 다음을 함께 이동하는 것으로 해석했다.

- `RYDD` Backplate
- original thumb caps 8개: `RAED/RAEH/RAEL/RBED/RBEH/RBEL/RDED/RDEH`
- `RHED` Small_joystick_attachment
- assembly의 HW504 thumb joystick 두 solid occurrence(`JFH`, `JFD`; 서로 겹친 별도 조이스틱 2개가 아니라 동일 module의 두 solid)

현재 가장 가까운 thumb control center는 `Button_corner_2 ↔ I1/M1`이다.

| metric | INDEX | MIDDLE |
|---|---:|---:|
| nearest control-center distance | 37.868 mm | 52.275 mm |
| four finger centers의 nearest-thumb 평균 | 41.654 mm | 53.706 mm |
| actual thumb geometry ↔ finger cap envelope | 21.535 mm | 35.870 mm |
| Backplate ↔ conservative holder envelope | 14.632 mm | 27.770 mm |

MIDDLE가 INDEX보다 thumb cluster에서 약 12–15 mm 더 멀다. 따라서 사용자가 본 “엄지와 finger controls가 멀다”는 인상은 CAD 좌표에서도 확인된다.

## 2. Pure -Z candidate comparison

Center distance는 external reach proxy이며, holder gap은 Backplate와 conservative integrated-holder envelope 사이의 최소 Euclidean clearance다. HW504 gap은 실제 assembly transform을 적용한 module AABB로 계산한 보수값이다.

| ΔZ | nearest center: INDEX | nearest center: MIDDLE | mean: INDEX | mean: MIDDLE | Backplate→INDEX holder | Backplate→MIDDLE holder | HW504→INDEX holder | screw B gap | result |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 37.868 | 52.275 | 41.654 | 53.706 | 14.632 | 27.770 | 21.773 | 9.469 | current |
| -6 | 33.066 | 46.374 | 36.585 | 47.889 | 9.819 | 21.938 | 15.773 | 4.958 | best feasible seed |
| -10 | 30.104 | 42.455 | 33.290 | 44.038 | 6.961 | 18.059 | 11.773 | 1.951 | mechanically marginal |
| -14 | 27.407 | 38.553 | 29.943 | 40.216 | 4.311 | 14.247 | 7.773 | **-1.057** | FAIL: screw B collision |

All dimensions are mm. `screw B gap < 0` means volumetric cylinder/Backplate interference.

### Shell seating result

Pure -Z is not a valid direct Transform even at -6 mm. The shell widens and its local normal rotates below the current thumb panel. With the rigid cap pattern translated only in Z, the cap centers sit inward of the target outer shell:

| ΔZ | cap-center to target shell mismatch | intact-region normal change | required approximate +Y correction | additional observation |
|---:|---:|---:|---:|---:|
| -6 | 4.049…7.165 mm | about 15…16° on intact side samples | about +5.5 mm mean | side controls additionally need radial X accommodation of about 2.9…4.1 mm |
| -10 | 9.159…11.613 mm on resolved samples | about 24.6…25.1° | about +9 mm | both wide-control rays fall through existing opening/void regions |
| -14 | 11.743…16.971 mm | about 39.7…49.0° on side samples | about +10.5 mm | strong shell-width mismatch plus screw B collision |

Direct wall-ray values at some center/split locations were 0.0–0.9 mm or missing because the ray passes through an existing thumb/finger opening, not because that value is a valid printable wall. Adjacent intact target regions are nominally about 3.0 mm at -6 and -10. Therefore old openings must be closed and the new Backplate perimeter/interface must be regenerated before wall thickness can be certified.

## 3. Recommended translation

The recommended **design-study seed**, not an approved CAD Transform, is:

`ΔX = 0 mm, ΔY ≈ +5.5 mm, ΔZ = -6 mm`

Reasons:

1. It reduces the nearest INDEX/MIDDLE center distance by 4.80/5.90 mm and the row-average proxy by 5.07/5.82 mm.
2. It retains 9.819 mm to INDEX holder, 21.938 mm to MIDDLE holder, and a conservative 15.773 mm HW504-to-INDEX-holder gap.
3. Screw B retains 4.958 mm under pure -Z; the approximate +Y correction moves the Backplate away from screw B rather than toward it.
4. -10 mm buys only another 2.96/3.92 mm center improvement but reduces INDEX-holder and screw-B margins to 6.961/1.951 mm.
5. -14 mm is a hard FAIL at screw B and has the largest shell-normal/width mismatch.

The +Y value is only a first rigid-panel seating correction. Because the shell grows laterally at lower Z, a single XYZ translation cannot put every button directly on the existing shell. The Backplate must remain the common rigid datum and receive a redesigned shell flange/adapter around its perimeter.

## 4. Expected modification range if thumb movement is later approved

The move is not a one-feature Transform. A safe implementation would have to change together:

1. Backplate, eight caps, Small_joystick_attachment, HW504 mechanism and their assembly mates as one rigid cluster.
2. Eight old shell openings and the old joystick opening: close/rebuild them without leaving plug bodies or thin patches.
3. New common Backplate perimeter cut, positive-overlap mounting flange and local shell blends.
4. Backplate screw/mount datums. Screw B is fixed and becomes the governing obstacle as ΔZ increases.
5. Thumb wiring exit and strain-relief volume. The current model has no wire-gauge, insulation-OD or solder-fillet envelope, so wiring is not certified by the geometric gap alone.
6. Joystick shaft opening and mechanism service path. Internal HW504-to-Backplate relationships remain unchanged under rigid motion; only shell/holder/screw relationships change.
7. Final shell wall: require at least the existing nominal 3 mm away from openings, plus a separately declared minimum bridge/web gate around the new perimeter.
8. Assembly order: pre-wire thumb parts, insert rigid cluster, fasten Backplate, then install finger switches/spacers/retainers. The -6 seed preserves more tool and wire access than -10/-14.

## 5. INDEX vs MIDDLE architecture by row

`n0/n` below means visible cap/opening surface normal. `F2/a` means the physical switch/actuator axis.

| row | shell ownership | switch center mm | F2 / switch axis | roll | seat architecture | holder architecture | terminal channel | rear support | retainer concept | surrounding obstacles | reason for difference |
|---|---|---|---|---:|---|---|---|---|---|---|---|
| I1 | JfD | (-22.224, -17.494, 9.000) | (-0.847668, -0.506167, -0.158916) | 0° | 6.4 seat, switch front 5.3, rear seat 11.5; 8.0 opening stays on `n0` | 12.4 pre-union blank, F2 axis; separate front trim on `n0` | four rigid-root channels, 0.20 knee overlap; open rear | independent 2.4403 spacer | shared `RWID` for I1–I3 | I2, side wall, RWID ear/boss, screw B region | strong side angle requires F2-axis holder while visible opening stays on shell normal |
| I2 | JfD | (-15.970, -26.208, 9.000) | (-0.387542, -0.574231, -0.721158) | 0° | same 6.4/F2 seat; 8.0 `n0` opening | same 12.4 blank; neighbor seats pre-cleared | four channels; open rear | independent 2.4403 spacer | shared `RWID` | I1/I3 convergence, shared service relief and wiring slot | converging F2 axes make common retainer preferable to per-button hooks |
| I3 | JfD | (-5.496, -29.325, 9.000) | (-0.068454, -0.997610, 0.009410) | 90° | same | 12.4 blank, **split-clipped**, front trim on `n0` | four channels rotated 90°; open rear | independent 2.4403 spacer | shared `RWID` | X=0 split, I2, I4/RZKD, RWID service envelope | split ownership removes one side of generic holder material |
| I4 | JaD | (5.496, -29.325, 9.000) | (0.024161, -0.968017, -0.249718) | 90° | same | 12.4 blank, **split-clipped** | four channels rotated 90°; open rear | independent 2.4400 spacer | separate `RZKD` | split, I3, screw B, shared RWID exclusion zone | opposite shell and service path prohibit sharing I1–I3 retainer |
| M1 | JfD | (-19.835372, -0.614992, -11.125) | (-0.837519, -0.499950, -0.220481) | 90° | 6.4 axis seat, front 5.2796, rear 8.8396; 8.4 guided opening on surface normal | 10.0 support ring + two continuous side beams/hooks, shell-first union | four rigid-root channels with 0.20 knee overlap | integrated beams/hooks + independent 2.44 spacer | no separate retainer | M2, I1 envelope, side wall | lower-profile switch can use integrated snap support and shorter body depth |
| M2 | JfD | (-12.899418, -8.744828, -14.125) | (-0.601521, -0.782846, -0.159135) | 90° | same | standard ring/beams/hooks | four channels, roll 90° | integrated + 2.44 spacer | no separate retainer | M1/M3, I2; row low point Z=-14.125 | joint axis/center optimization uses a 3 mm local Z drop to keep body/web clearance |
| M3 | JfD | (-3.537874, -14.413709, -11.125) | (0.320429, -0.733473, -0.599452) | 0° | same | split-trimmed ring, asymmetric local `shellAnchor`, beams/hooks | four channels, roll 0° | integrated + 2.44 spacer | no separate retainer | split, M2/M4, INDEX/RWID keep-outs | positive shell anchor is required after split trim; generic symmetric ring would not own JfD robustly |
| M4 | JaD | (7.444328, -13.569623, -11.125) | (0.224859, -0.772793, -0.593489) | 0° | surface normal and switch axis coincide | split-trimmed ring with shifted negative-side rail/hook | four channels, roll 0° | integrated + 2.44 spacer | no separate retainer | split, M3, I4/RZKD, JaD wall | opposite-shell split and nearby INDEX geometry require asymmetric support placement |

## 6. Differences that must remain

These are acceptable internal differences:

- each row's physical switch axis and selected terminal roll;
- INDEX deeper 12.4 pre-union holder versus MIDDLE 10.0 ring/beam system;
- terminal exit direction and open-rear routing;
- INDEX shared/separate removable retainers versus MIDDLE integrated snap beams/hooks;
- I3/I4 and M3/M4 split-side trims;
- M3 shell anchor and M4 asymmetric rail/hook;
- independent rear spacer thickness and service access tied to actual local body depth.

Removing these differences merely for visual symmetry would regress proven body, divider, split-wall, screw or service clearances.

## 7. Differences that can and should be unified

The current external values are not the same product language:

| visible item | INDEX | MIDDLE | assessment |
|---|---:|---:|---|
| nominal visible cap width | 7.6 mm | 8.0 mm | unwanted 0.4 mm mismatch |
| shell opening | 8.0 mm | 8.4 mm | unwanted 0.4 mm mismatch |
| cap proud/exposure datum | about 1.4 mm | about 0.2 mm | unwanted 1.2 mm mismatch |
| adjacent center pitches | 10.726 / 10.928 / 10.992 mm | 11.100 / 11.348 / 11.015 mm | already visually compatible |
| nominal visible edge gaps | 3.126 / 3.328 / 3.392 mm | 3.100 / 3.348 / 3.015 mm | already compatible within 0.38 mm |
| rear retention | RWID/RZKD | integrated hooks | internal only; keep different |

Recommended common external language for the next controlled redesign:

1. Use one shared visible cap top profile, provisionally `7.6 × 7.6 mm` because it preserves the tighter INDEX divider. MIDDLE can shrink outward without reducing its 10.0 support ring.
2. Use one `8.0 × 8.0 mm` visible opening/reveal (`0.2 mm` per side to a 7.6 cap). Keep MIDDLE's internal stem bore and stop lugs hidden below that datum.
3. Set one visible exposure target, provisionally `1.0 ± 0.1 mm`; tune the hidden stem/stop lengths separately to preserve actuation travel.
4. Use the same corner/chamfer language and no arbitrary external positive boss. Any holder ring must remain below the shell outer surface.
5. Preserve the current near-11 mm pitch. Do not move centers merely to chase a perfectly straight world-Z row.
6. Fit both visible rows to perceptually parallel shell-projected curves. M2's 3 mm Z drop may remain internally, but the cap/stem can decouple the visible top datum from the switch axis if visual review still shows a dip.

## 8. Fragment / sliver / orphan-solid inventory

### Final printable-solid result

- source solids: **30**
- STL triangle components: **30**
- multi-component part files: **0**
- unexpected disconnected solids: **0**
- boundary-edge parts: **0**
- non-manifold-edge parts: **0**
- degenerate-triangle parts: **0**
- whole-part bbox minimum dimension below 0.3 mm: **0**
- leftover boolean-tool solids: **0**; every solid maps to a declared shell, Backplate, thumb cap, attachment, INDEX cap/retainer/spacer or MIDDLE cap/spacer role.

Therefore there is no suspect orphan geometry requiring a `partId / featureId / volume / bbox / connected target` defect row. The suspect table is empty.

### Small bodies that can look like fragments but are intentional

These eight 3.6 mm diameter rear spacers are intentionally independent service parts. They must **not** be unioned into a shell or retainer.

| partId | feature reference | volume from final STL | bbox min → max mm | intended target/interface |
|---|---|---:|---|---|
| RmND | INDEX I1 `its1105Index/SPACER` | 24.831 mm³ | [11.690,-14.562,8.631] → [15.669,-10.222,12.573] | I1 body rear ↔ RWID |
| RqND | INDEX I2 `its1105Index/SPACER` | 24.831 mm³ | [9.931,-22.594,14.143] → [14.196,-18.245,18.396] | I2 body rear ↔ RWID |
| RuND | INDEX I3 `its1105Index/SPACER` | 24.831 mm³ | [2.927,-20.611,7.094] → [6.685,-17.927,10.717] | I3 body rear ↔ RWID |
| RyND | INDEX I4 `its1105Index/SPACER` | 24.828 mm³ | [-7.081,-21.200,9.470] → [-3.424,-17.935,13.565] | I4 body rear ↔ RZKD |
| R4PD | `MmpBMYK4r3YQubx6n` | 24.828 mm³ | [9.405,2.245,-10.932] → [13.416,6.583,-6.882] | M1 body rear ↔ integrated hooks |
| RkRD | `Mg4CS9ouVxzcPvhDU` | 24.828 mm³ | [4.677,-2.945,-14.495] → [9.020,1.205,-10.553] | M2 body rear ↔ integrated hooks |
| RaTD | `M5mAoLzCamzWWTulC` | 24.828 mm³ | [4.665,-9.153,-7.267] → [8.857,-4.917,-2.923] | M3 body rear ↔ integrated hooks |
| RLVD | `MPFPMgIUS7WLdMWzv` | 24.828 mm³ | [-7.211,-7.881,-7.328] → [-3.154,-3.711,-2.982] | M4 body rear ↔ integrated hooks |

The immutable local cache did not retain the four generated INDEX tree feature IDs, so their exact IDs are not invented here; their creating FeatureScript stage and partIds are exact. They are not suspect geometry.

### Tessellation sliver sanity check

Fine STL triangulation contains 1,419 narrow facets with altitude below 0.01 mm, mainly on JaD/JfD, RWID and the guided MIDDLE caps. These are tessellation facets, not separate solids:

- every file is one closed component;
- all boundary/non-manifold/degenerate counts are zero;
- no part has a near-zero whole-body bbox dimension;
- JaD and JfD are each one manifold component, so no duplicate holder fragment is present.

The narrow facets therefore do not justify deleting CAD bodies. Raw tessellation shape must remain a sanity check, not a B-rep identity gate.

### Positive-union/tangent prevention already present

- INDEX holder blank overlaps its shell by `FUSE = 0.20 mm` before shell-first union.
- INDEX and MIDDLE rigid-root channel knees overlap by `0.20 mm`; no zero-length butt joint is used.
- MIDDLE ring, beams and hooks overlap volumetrically; M3 has a dedicated 1.6 × 1.6 mm shell anchor across depth 1.2…3.6 mm.
- Each side beam/hook cluster is unioned separately to the owning shell, preventing a disconnected tool from being hidden in a broad multi-body boolean.

These rules satisfy the requirement that face-only or edge-only contact is FAIL.

## 9. Fragment removal/prevention plan for future writes

1. Keep the current intended 30-solid manifest as an allow-list and fail any write that adds an unnamed solid.
2. After each thumb move sub-step, export individual solids and require one closed component per part, boundary/non-manifold/degenerate count zero.
3. Close old thumb openings by editing/rebuilding the owning shell volume; do not add separate patch plugs.
4. Union the new Backplate flange with at least 0.20 mm declared positive overlap, then verify actual B-rep body count remains unchanged.
5. Build left/right flange tools separately and union each only to its intended shell. Never use one broad boolean across both identities.
6. Delete/consume every temporary boolean tool inside its atomic feature; a tool body appearing in the parts list is immediate HOLD.
7. Keep eight spacers explicitly named and packaged; in print layouts, label them so they are not mistaken for scrap.
8. Add explicit wire/solder/heat-shrink envelopes before certifying the thumb/finger shared interior volume.

## 10. Final decision

- recommended thumb Z candidate: **-6 mm**
- recommended feasibility seed: **(ΔX, ΔY, ΔZ) = (0, +5.5, -6) mm**
- pure `(0,0,-6)` direct Transform: **FAIL / not seated to shell**
- -10 mm: **HOLD / marginal screw and shell interface**
- -14 mm: **FAIL / screw B collision**
- INDEX/MIDDLE internal architecture: **different by necessity**
- INDEX/MIDDLE external UX: **cap/opening/exposure unification required**
- unexpected fragment/sliver/orphan solid: **0**
- current final printable-solid integrity: **PASS**
- CAD WRITE recommendation: **HOLD**

HOLD is caused by the thumb shell/interface and missing explicit wiring envelope, not by fragment geometry. The next safe step is a non-production branch/mock-up of the Backplate interface around the `(0,+5.5,-6)` seed, followed by wall, screw, wiring and hand-fit gates before any approved final CAD write.
