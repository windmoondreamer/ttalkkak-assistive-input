# OneGrip Play — LOCAL-FIRST MIDDLE shell docking

## 결론

이번 재시작 구간은 **LOCAL-FIRST / PHASE 1**까지만 수행했다.

- ONSHAPE API CALL = **0**
- ONSHAPE BROWSER AUTOMATION = **0**
- ONSHAPE CAD WRITE = **0**
- APPROVED MIDDLE BUILD123D BASELINE = **PASS / 유지**
- LOCAL SHELL DOCKING = **STOP — 필수 JaD/JfD shell STEP 부재**
- 적용된 STOP 조건 = **A**

PHASE 2 이후의 docking geometry, modified shell STEP, print STL 및 visual QC는 생성하지
않았다. mesh를 억지로 B-rep으로 간주해 제조 형상을 만드는 것은 이 문서의 PASS가 아니다.

## 1. Local reference inventory

재현 가능한 inventory source:

- `build123d_workbench/inventory_local_references.py`

생성 manifest:

- `local_cad/manifests/local_reference_manifest.json`

manifest 요약:

| 항목 | 결과 |
|---|---:|
| inventory entries | 67 |
| STEP/STP | 22 |
| STL | 45 |
| exact B-rep entries | 22 |
| immutable mesh-only entries | 32 |
| JaD shell STEP | **MISSING** |
| JfD shell STEP | **MISSING** |
| approved MIDDLE B-rep | **FOUND** |
| separate screw B-rep | MISSING (analytic keep-out 데이터는 별도 존재) |

저장소의 22개 STEP은 승인된 MIDDLE 결과, build123d carrier extension, lower-adapter
reference/output이다. `JaD_RZKD_carrier_extension.step` 및
`JfD_RWID_carrier_extension.step`은 작은 carrier helper이며 shell 전체 STEP이 아니다.

## 2. Preferred local shell mesh references

현재 발견된 가장 최근 JaD/JfD local shell 계열은 다음 두 파일이다.

| role | path | size | modified | SHA256 |
|---|---|---:|---|---|
| JaD shell mesh | `exports/thumb_lower15_housing_mockup/OneGrip_lower15_housing_Joystick_1_JaD.stl` | 941,984 B | 2026-08-21 19:34:33 KST | `43cb0a9972e0153afe49341a3e29df130b9e966bbff40a1114cee3919c1b50cb` |
| JfD shell mesh | `exports/thumb_lower15_housing_mockup/OneGrip_lower15_housing_Joystick_2_JfD.stl` | 987,084 B | 2026-08-21 19:34:35 KST | `29050592a316c16b64211276ed0ce2bbfafd7bb0b833d954db7b305cee677677` |

Mesh audit:

| role | triangles | connected components | watertight | approximate volume | bounding box min | bounding box max |
|---|---:|---:|---|---:|---|---|
| JaD | 18,838 | 1 | true | 47,667.801514 mm³ | (0.000, -61.427456, -73.878510) | (38.734715, 62.427490, 78.248428) |
| JfD | 19,740 | 1 | true | 50,128.558180 mm³ | (-38.734715, -61.427456, -73.878510) | (0.000, 62.427490, 78.248428) |

이는 출력/시각 reference로는 정상이다. 그러나 build123d `import_stl`의 OCCT 결과는
두 파일 모두 다음과 같다.

| shell | imported OCCT type | valid | solids | shells | faces |
|---|---|---:|---:|---:|---:|
| JaD STL | Face | false | 0 | 0 | 1 |
| JfD STL | Face | false | 0 | 0 | 1 |

따라서 이 STL만으로는 다음을 신뢰성 있게 수행할 수 없다.

- shell wall에 positive-volume union되는 docking rail/land 생성
- 8.0 mm opening 및 switch pocket exact subtraction
- minimum wall 1.20/1.60 mm exact 측정
- tangent-only union, near-zero wedge 및 sliver 검출
- 결과 shell의 valid/watertight OCCT solid STEP export
- carrier insertion swept-volume 대 shell B-rep 검증

## 3. Approved MIDDLE baseline integrity

MIDDLE 쪽 exact geometry는 정상이다.

| artifact | size | solids | valid | volume | SHA256 |
|---|---:|---:|---:|---:|---|
| `M1_M2_M3_shared_carrier.step` | 828,325 B | 1 | true | 690.454636 mm³ | `94dffd43d1aac44ec75183dee6e2e88a10bc6f468654d61ede07b6b2976de4d1` |
| `M4_single_carrier.step` | 212,978 B | 1 | true | 177.034240 mm³ | `65be438f06f20ed2f5fa815eadc4542e03d057c209d6f71a4b528ba8615b96a1` |
| `MIDDLE_reference_with_ITS1105.step` | 1,566,742 B | 10 | true | 2,351.491840 mm³ | `b9b11e010b2dff318cd33aefa597bc2c4349ecd7fb4f171867e5a6450c950002` |

`MIDDLE_reference_with_ITS1105.step`의 10 solids는 carrier 2, cap 4, ITS-1105
reference 4의 의도된 구성이다. 승인 수치도 그대로 유지한다.

- M1~M4 axis mismatch = 0°
- minimum switch SAT = 1.389 mm
- minimum divider = 1.123 mm
- minimum INDEX holder clearance = 6.025 mm
- minimum screw clearance = 5.738 mm
- unexpected fragment/orphan = 0

기존 0.7 mm hook, 0.8 mm rail, 개별 spacer, M2 dogleg, M3 half-ring 구조로 돌아가지
않는다.

## 4. PROBLEM

**필수 local JaD/JfD shell STEP/STP가 repository에 없다.**

현재 shell 데이터는 watertight STL뿐이고, exact OCCT solid shell baseline이 아니다.
승인 MIDDLE carrier는 있지만 carrier가 결합되어야 할 shell contact surface와 wall solid가
없으므로 manufacturing docking geometry를 완결할 수 없다.

## 5. WHY LOCAL IS INSUFFICIENT

이 문제는 build123d 기능 부족이 아니라 입력 형식 경계다. STL을 삼각망 상태로 사용하면
충돌 sanity check와 render는 가능하지만, 이번 단계가 요구하는 production STEP boolean,
wall-thickness gate, positive-volume shell anchor, service sweep를 exact하게 증명할 수 없다.

STL reverse-engineering 또는 자동 surface fitting으로 shell을 재구성하는 선택도 가능하지만,
원본 곡률/공차를 새로 근사하는 major upstream shell reconstruction이 된다. 이는 승인되지
않은 대규모 변경이며 immutable baseline 정책에도 맞지 않는다.

## 6. WHAT MUST CHANGE UPSTREAM

필수 변경은 geometry redesign이 아니라 **reference delivery**다.

1. current intended baseline의 `Joystick_1 / JaD` full shell을 STEP 또는 STP로 제공
2. 같은 baseline의 `Joystick_2 / JfD` full shell을 STEP 또는 STP로 제공
3. unit = millimetre, geometry = AP242 또는 AP214 exact solids
4. 두 shell의 assembly coordinates를 유지하고 Y-up 변환을 적용하지 않음
5. 가능하면 RWID, RZKD 및 screw/boss geometry도 같은 좌표계의 별도 solids로 포함

파일은 repository 내부 예시 위치에 넣는다.

- `local_cad/reference/JaD_SHELL_BASELINE.step`
- `local_cad/reference/JfD_SHELL_BASELINE.step`

## 7. RECOMMENDED ONSHAPE ACTION

자동 접근은 하지 않는다. 사용자가 필요하다고 판단할 때만 원본 Onshape Part Studio에서
JaD/JfD를 **수동 STEP export**하여 위 repository 경로에 넣는 것을 권장한다.

권장 export 조건:

- STEP AP242
- millimetre
- current intended configuration 명시
- global assembly coordinates 유지
- JaD와 JfD 각각 full solid body
- mesh/STL export가 아니라 STEP export

두 STEP이 들어오면 다음 로컬 작업만 재개한다.

1. manifest 재생성 및 SHA256 고정
2. OCCT solid/valid/volume/BBox 확인
3. M1~M3 broad keyed/captured docking 설계
4. M4 separate docking 설계
5. insertion/removal/wiring sweep
6. `JaD_LOCAL_MODIFIED.step`, `JfD_LOCAL_MODIFIED.step` 생성
7. fragment 0 및 visual QC

## 8. Gate status

| gate | status |
|---|---|
| LOCAL-FIRST policy | PASS |
| immutable baseline policy | PASS |
| approved MIDDLE exact B-rep | PASS |
| JaD shell exact B-rep | **HOLD / MISSING** |
| JfD shell exact B-rep | **HOLD / MISSING** |
| M1~M3 shell docking | NOT STARTED |
| M4 shell docking | NOT STARTED |
| local modified shell STEP | NOT GENERATED |
| local print STL | NOT GENERATED |
| visual QC | NOT STARTED |
| STOP condition | **A** |

최종 판정:

- **MIDDLE BUILD123D DESIGN = PASS**
- **LOCAL MIDDLE SHELL DOCKING = HOLD**
- **LOCAL CAD EXECUTION = STOP CONDITION A**
- **ONSHAPE RETURN = 자동 실행 금지 / 수동 STEP reference 제공만 권장**

