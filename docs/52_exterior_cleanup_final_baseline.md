# FINAL EXTERIOR CLEAN V1 — cleanup / reset audit

Date: 2026-08-22  
Mode: **LOCAL build123d + OCCT only**  
Onshape use: **0**  
Onshape CAD write: **0**  
Internal carrier / wiring / fastening design: **0**

## 0. 결론

이번 결과는 **구형 외관을 제거한 exact-shell 진단본**까지는 성공했지만, 요청된
최대 하강 Thumb opening을 exact B-rep으로 재현할 로컬 기준이 부족하므로 최종
baseline으로 승인할 수 없다.

| Final gate | Result |
|---|---:|
| LATEST FINGER EXTERIOR | **PRESERVED** |
| LOWERED THUMB EXTERIOR | **FAIL** |
| OLD FINGER TRACES | **REMOVED** |
| OLD THUMB OPENINGS | **REMOVED** |
| DUPLICATED THUMB OPENINGS | **0** |
| EXTERNAL FASTENING GEOMETRY | **0** |
| UNAPPROVED EXTERIOR CHANGE | **0** |
| VALID SINGLE WATERTIGHT SHELLS | **PASS** |
| CLEAN FINAL EXTERIOR BASELINE | **HOLD** |

따라서 현재 STEP은 형상 복구와 Finger opening 검증을 위한 **HOLD 진단본**이다.
`FINAL EXTERIOR CLEAN V1` production baseline으로 동결하면 안 된다.

## 1. Clean rebuild source

난잡한 Integrated V3 shell을 역수술하지 않고 다음 exact source에서 다시 만들었다.

| Role | Exact source | SHA-256 |
|---|---|---|
| JaD clean pre-Finger shell | `local_cad/reference/JAD_CLEAN_PRE_FINGER.step` | `01f5708a29ca46b0f9f13b5c63b5f4d9b7b46bcf04fc8b0a55b806085f1ff4f0` |
| JfD clean pre-Finger shell | `local_cad/reference/JFD_CLEAN_PRE_FINGER.step` | `8d290891dd93f16f50789f24ef7d27c754b27b4250caa1ebb3cb587648475792` |
| Approved Finger layout | `build123d_workbench/out/finger_controls_v2/finger_controls_v2_source_manifest.json` | `2de88051c9c981a04f284b5dde48e4a15861606e5bae3f1376e2a7ef6539c5b2` |
| Lowered Thumb module reference | `build123d_workbench/out/finger_thumb_joint_feasibility/THUMB_TARGET_EXACT_MODULE.step` | `adc870ffaf55a9342d62df89f162827a744bdf1d43060c0fbb69f7c8e8089fe9` |

Construction policy:

- Integrated V3 shell import: **없음**
- V3 seat / boss / screw / carrier / wiring import: **없음**
- 새 exterior additive geometry: **0**
- 허용 subtract 영역: 최신 Finger 8 opening과 lowered Thumb target opening뿐
- JaD/JfD seam을 이동하는 작업: **없음**
- STL 또는 tessellated shell을 boolean source로 사용: **없음**

## 2. Removed legacy Finger features

Clean pre-Finger exact shell을 출발점으로 사용해 I1, M1, M2를 포함한 이전 Finger
opening, partial breakthrough, support scar, 중복 opening을 계승하지 않았다. 그 위에
승인된 다음 8개 opening만 다시 적용했다.

`I2, I3, I4, M3, M4, N1, N2, N3`

각 cutter에 대해 최종 shell과의 잔여 교차 체적이 모두 `0 mm³`인지 exact boolean으로
확인했다.

| Control | Frozen center (mm) | Cutter volume (mm³) | Residual after cut (mm³) |
|---|---|---:|---:|
| I2 | `(-15.971165, -26.209817, 8.998807)` | 194.333632 | 0 |
| I3 | `(-5.496017, -29.325426, 8.999870)` | 194.533139 | 0 |
| I4 | `(5.496017, -29.325426, 8.999870)` | 194.481247 | 0 |
| M3 | `(-6.890920, -13.716686, -11.118070)` | 192.732624 | 0 |
| M4 | `(7.379332, -13.575227, -11.115547)` | 193.103503 | 0 |
| N1 | `(-10.990443, -35.800028, 25.000000)` | 192.496958 | 0 |
| N2 | `(0.000000, -35.765119, 25.000000)` | 212.045171 | 0 |
| N3 | `(17.486897, -6.664472, -11.125000)` | 197.448723 | 0 |

특히 이전 Integrated V3의 N1 뒤 대형 관통 relief cutter는 source에서 비활성화됐고,
이 clean rebuild에도 import되지 않았다. 최신 Finger 8 외의 외부 finger 흔적은 없다.

## 3. Removed old Thumb openings and curvature restoration

### 3.1 Provenance

Clean pre-Finger shell에는 원래 위치의 Thumb opening이 남아 있었다. 역사적
FeatureScript의 original `Buttons` removal query와 대조한 결과 opening side face는
총 **36개**였다.

- JaD: 18 faces
- JfD: 18 faces
- 8 rectangular button openings: 32 side faces
- split joystick opening: 4 side faces

### 3.2 Exact restoration method

평평한 box/cylinder plug나 별도 patch body를 만들지 않았다. OCCT
`BRepAlgoAPI_Defeaturing`으로 opening side face를 제거하고 주변의 원래 analytic/
spline B-rep surface를 연장·trim해 shell을 heal했다.

| Restored shell | Valid | Solids | Shells | Faces | Volume (mm³) | Small solids |
|---|---:|---:|---:|---:|---:|---:|
| JaD | true | 1 | 1 | 51 | 47,746.887989 | 0 |
| JfD | true | 1 | 1 | 49 | 49,027.345156 | 0 |

- 제거된 original side faces: **36**
- flat patch body: **0**
- ridge/step를 만드는 별도 positive body: **0**

복원 과정에서 얻은 old-opening void와 최종 shell의 교차 체적으로 실제 fill을 다시
검증했다.

| Half | Recovered void solids | Void volume (mm³) | Final fill intersection (mm³) | Fill ratio |
|---|---:|---:|---:|---:|
| JaD | 6 | 1,014.599768 | 1,014.599598 | 0.9999998321 |
| JfD | 6 | 1,014.582810 | 1,014.582639 | 0.9999998321 |

따라서 **OLD THUMB OPENINGS = REMOVED**이고 original 위치의 shell 곡률 복원은
PASS다.

## 4. Lowered Thumb target — unresolved exact geometry

승인 target은 다음과 같다.

`(ΔX, ΔY, ΔZ) = (0, +12.25, -21.00) mm`

복원 중 회수한 exact old-opening void 12개를 이 translation으로 이동해 restored shell과
교차시켰다. 결과는 다음과 같다.

| Half | Moved target void ∩ restored shell (mm³) | Residual after attempted cut (mm³) |
|---|---:|---:|
| JaD | **0.0** | 0.0 |
| JfD | **0.0** | 0.0 |

즉, 원래 opening의 유한한 void/cutter 체적을 단순 강체 이동하면 새 위치의 굽은 shell에
도달하지 않는다. Onshape에서 성공했던 `opMoveFace`는 side face를 이동한 뒤 주변
surface까지 연장·trim해 새 B-rep을 만드는 direct edit이므로, 유한 plug를 옮기는 로컬
boolean과 동등하지 않다.

여기서 임의로 cutter를 깊게 늘이거나 box/cylinder로 관통시키면 opening의 실제 side
surface, shell 곡률 교차선, cap exposure를 추측하게 된다. 이는 flat patch 금지와
exact-curvature gate를 위반하므로 수행하지 않았다. Lowered Thumb module reference는
위치/시각 검증용으로만 combined STEP에 포함했으며, shell에는 새 Thumb opening이
생기지 않았다.

따라서:

- old Thumb opening restoration: **PASS**
- lowered Thumb opening reproduction: **HOLD**
- duplicated old/lowered void overlap: **0 mm³**
- LOWERED THUMB EXTERIOR: **FAIL**

### MISSING REFERENCE

`THUMB_LOWER15_HOUSING_V1` 상태의 **exact JaD/JfD shell STEP pair**가 로컬에 없다.
현재 로컬에 있는 lower-15 shell은 STL뿐이며 tessellated approximation이므로 exact B-rep
curvature와 opening side face를 복원하는 source로 사용할 수 없다. 해당 Onshape
versionId도 로컬 기록에서 확인되지 않는다.

### WHY EXACT RESTORATION IS NOT POSSIBLE

로컬 clean STEP으로 old hole을 정확히 heal할 수는 있지만, 새 위치에서 shell과 opening
side surface가 만드는 intersection/trim 결과를 정의할 exact historical B-rep이 없다.
회수한 opening void의 rigid translation은 양쪽 shell과 `0 mm³` 교차한다. 따라서 현재
자료만으로 관통 깊이와 새 boundary를 정하면 추정 형상이 된다.

### MANUAL ONSHAPE EXPORT NEEDED

사용자가 Onshape GUI에서 post-write version **`THUMB_LOWER15_HOUSING_V1`**을 연 뒤,
다음 두 shell body를 **STEP AP242 / millimeter / preprocessing none**으로 각각 내보내야
한다.

1. `Joystick_1` / JaD shell
2. `Joystick_2` / JfD shell

필요한 것은 STL, 전체 assembly, caps가 아니라 `opMoveFace`가 완료된 두 exact shell
body다. 이 STEP pair가 들어오면 현재 source의 restored clean shell과 비교해 lowered
Thumb opening faces만 exact transfer하거나 해당 shell을 clean base로 채택할 수 있다.
이번 작업에서는 지시대로 Onshape GUI/API를 열거나 자동 export하지 않았다.

## 5. Removed external fastening geometry

V3/V3.1 external boss, cylindrical barrel, screw tube, bracket, tab, rib, driver tube,
validation fixture를 하나씩 삭제하는 방식 대신 clean source에서 다시 시작했다. 따라서
그 body/feature는 construction graph에 존재하지 않는다.

- external additive geometry count: **0**
- external fastening protrusion count: **0**
- leftover cutter count: **0**
- associated V3 screw/counterbore/access cutter import: **0**
- replacement internal fastening design: **0**

기본 shell silhouette와 seam에는 additive modification을 하지 않았다. 승인 영역 밖에
새로 더해진 exterior body도 없다.

## 6. Final exact shell validation

Lowered Thumb gate가 해결되지 않은 상태에서 생성된 진단 shell의 exact topology는
다음과 같다.

| Final shell | Valid | Solids | Shells | Faces | Edges | Vertices | Volume (mm³) | Small solids |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| JaD | true | 1 | 1 | 67 | 190 | 136 | 47,048.319270 | 0 |
| JfD | true | 1 | 1 | 69 | 196 | 140 | 48,132.204340 | 0 |

Additional inventory:

- orphan solid: **0**
- sliver/small solid: **0**
- leftover cutter: **0**
- external fastening protrusion: **0**
- unapproved exterior additive body: **0**
- approved Finger cap inventory: **8/8**
- lowered Thumb target reference solids: **20** total / **12** user-facing

`LOWERED THUMB EXTERIOR = FAIL` 때문에 위 shell validity만으로 final baseline PASS를
선언하지 않는다.

## 7. Outputs

Source:

- `build123d_workbench/integrated_exterior_clean_v1.py`
- `build123d_workbench/render_integrated_exterior_clean_v1.py`

Exact diagnostic outputs:

- `build123d_workbench/out/integrated_exterior_clean_v1/JAD_EXTERIOR_CLEAN_V1.step`
- `build123d_workbench/out/integrated_exterior_clean_v1/JFD_EXTERIOR_CLEAN_V1.step`
- `build123d_workbench/out/integrated_exterior_clean_v1/EXTERIOR_CLEAN_V1_COMBINED_REFERENCE.step`
- `build123d_workbench/out/integrated_exterior_clean_v1/exterior_clean_v1_validation.json`

No STL / print plate was created.

Render set:

1. `renders/integrated_exterior_clean_v1/01_front_clean_exterior.png`
2. `renders/integrated_exterior_clean_v1/02_rear_clean_exterior.png`
3. `renders/integrated_exterior_clean_v1/03_left_clean_exterior.png`
4. `renders/integrated_exterior_clean_v1/04_right_clean_exterior.png`
5. `renders/integrated_exterior_clean_v1/05_left_oblique.png`
6. `renders/integrated_exterior_clean_v1/06_right_oblique.png`
7. `renders/integrated_exterior_clean_v1/07_thumb_region_closeup.png`
8. `renders/integrated_exterior_clean_v1/08_finger_region_closeup.png`
9. `renders/integrated_exterior_clean_v1/09_before_after_exterior.png`
10. `renders/integrated_exterior_clean_v1/10_removed_legacy_features.png`

Contact sheet: `renders/integrated_exterior_clean_v1/00_contact_sheet.png`

## 8. STOP decision

Legacy Finger 흔적, 원래 Thumb opening, N1 뒤 관통 relief, V3 external fastening은
제거됐다. 그러나 정확한 lowered Thumb opening이 shell에 존재하지 않으므로
**CLEAN FINAL EXTERIOR BASELINE = HOLD**다.

요청한 범위를 넘어 internal fastening/carrier/wiring 설계로 진행하지 않는다. exact
`THUMB_LOWER15_HOUSING_V1` JaD/JfD STEP pair가 제공될 때까지 여기서 STOP한다.
