# Finger layout baseline reset — LOCAL-FIRST gate

- 감사일: 2026-08-22 (KST)
- project root: `C:\Users\User\Desktop\OneGrip-Play`
- **Onshape API call: 0**
- **Onshape CAD write: 0**
- **Onshape automated browser access: 0**
- local de-feature / surface patch / guessed reconstruction: **0**

## 1. Gate result

```text
LOCAL CLEAN BASELINE: NOT FOUND
SELECTED FILE: NONE
NEXT: MANUAL ONSHAPE EXPORT
```

로컬에는 pre-finger 상태를 입증하는 JaD/JfD **테셀레이션 스냅샷**이 있지만,
production shell boolean에 필요한 exact OCCT solid STEP/B-rep은 없다. exact STEP으로 존재하는
full assembly는 이미 INDEX/MIDDLE finger geometry가 통합된 current-stage shell이다.

따라서 어떤 파일도 clean immutable production baseline으로 승격하지 않았다. 현재 셸을
de-feature하거나 곡면을 추측 복원하지 않고 이 단계에서 HOLD한다.

## 2. Repository inventory

`local_cad/manifests/local_reference_manifest.json`과 repository 전체의 `*.step`, `*.stp`,
reference/export/backup/checkpoint 경로 및 Git history를 로컬에서 재검사했다.

- STEP/STP: **22 files**
- clean full JaD shell STEP: **0**
- clean full JfD shell STEP: **0**
- Git history의 삭제/과거 clean shell STEP: **0**
- archive 안의 STEP/STP: **0**
- exact full-grip candidate: 1개, 아래 사유로 **REJECTED**
- clean pre-finger mesh evidence: JaD/JfD 2개, 아래 사유로 **REFERENCE ONLY**

carrier extension, MIDDLE carrier/cap/switch STEP, conformal core, ergo housing, stock gimbal STEP은
shell baseline이 아니므로 파일명에 JaD/JfD 또는 reference가 들어가더라도 제외했다.

## 3. Clean pre-finger evidence — mesh only

| item | JaD | JfD |
|---|---:|---:|
| file | `cad_dump/mesh_Joystick_1_baseline.json` | `cad_dump/mesh_Joystick_2_baseline.json` |
| partId | `JaD` | `JfD` |
| triangles | 17,478 | 16,374 |
| tessellation volume | 46,617.428802 mm3 | 47,914.465075 mm3 |
| source-note cross-check | original nominal 46,658 mm3 | original nominal 47,925 mm3 |
| SHA-256 | `758c03a37499dc11616c8c3de3bca50a25d7bb72f3e719d0d1887e9653ae18fe` | `490db1bc7ce0394cb987b5fd4f7974b4442eb935b59fef92aa0bfcacacb9a5f7` |

`docs/06_index_button_cad_implementation.md`는 이 baseline을 원본 89-feature 상태로 기록한다.
따라서 신규 I1~I4와 M1~M4가 생성되기 전 shell surface를 확인하는 reference로는 유효하다.

그러나 두 파일은 Onshape on-demand tessellation JSON이다. exact faces/edges, analytic curvature,
wall solid, boolean topology가 없으므로 다음을 증명할 수 없다.

- production STEP opening/pocket boolean
- exact wall thickness
- positive-volume carrier anchor
- fragment/orphan solid = 0
- service/insertion sweep의 exact collision

또한 두 파일에는 독립된 original thumb cap/switch와 screw solids가 들어 있지 않다. 따라서
mesh-to-solid 변환, surface fitting 또는 임의 patch로 production baseline을 복원하지 않는다.

## 4. Exact full-assembly STEP candidate — rejected

```text
FILE:
lower_adapter/local_cad/reference/ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step

SHA-256:
deb2f78838b41ab125247bd4068d7c0d08b5bddf780b449534b716fe35dc0ed4

SOLIDS:
172

ASSEMBLY CONTENT:
grip + original thumb components + stock gimbal + bearings + electronics + screws
```

이 파일은 좌표계와 원본 hardware reference로는 유효하지만 clean shell은 아니다. assembly
transform을 고려해 확인한 두 full-height shell solid는 다음과 같다.

| identified shell | exact STEP volume | local current lower-15 STL volume | clean mesh volume |
|---|---:|---:|---:|
| JaD | 47,672.949772 mm3 | 47,667.801514 mm3 | 46,617.428802 mm3 |
| JfD | 50,150.497392 mm3 | 50,128.558180 mm3 | 47,914.465075 mm3 |

exact STEP의 shell volume/BBox는 사용자가 출력·검토했던 current lower-15 housing STL과
일치하는 계열이며, clean pre-finger mesh와는 JaD 약 +1,055.5 mm3, JfD 약 +2,236.0 mm3
차이가 난다. local source notes와 current shell reference를 함께 대조하면 기존 INDEX/MIDDLE
opening/holder 변화가 이미 shell body에 통합된 상태다.

따라서 original thumb와 screw가 보존됐다는 장점만으로 이 파일을 clean baseline으로
선택할 수 없다. 특히 I1/M1/M2를 지우기 위해 이 STEP을 역수정하는 것은 이번 지시의
금지된 local de-feature에 해당한다.

## 5. Mandatory baseline fields

선택 가능한 exact clean baseline이 없으므로 아래 YES/NO는 **clean mesh evidence pair**의
내용을 기준으로 기록하고, 괄호에 production baseline 적격성을 구분한다.

```text
LOCAL CLEAN BASELINE: NOT FOUND

SELECTED FILE:
NONE

BASELINE CONTENT:
clean pre-finger JaD/JfD surface evidence exists as tessellation JSON only;
no exact solid STEP containing clean shells + complete thumb + screw geometry

I1 present?
NO in clean mesh evidence

M1 present?
NO in clean mesh evidence

M2 present?
NO in clean mesh evidence

finger controls present?
NO in clean mesh evidence / YES in the rejected exact full-assembly STEP

THUMB preserved?
NO as a complete selectable baseline
(thumb-related shell geometry exists, but independent original thumb solids are not in the clean mesh pair)

SCREW geometry preserved?
NO as a complete selectable baseline
(shell interface geometry exists, but independent screw solids are not in the clean mesh pair)

NEXT:
MANUAL ONSHAPE EXPORT
```

## 6. Manual Onshape GUI export required

Codex는 Onshape에 접속하거나 API를 호출하지 않는다. 사용자가 GUI에서 다음을 직접 수행한다.

1. `OneGrip_Play_V1`을 열고 History/Version에서 finger controls 추가 이전 상태로 이동한다.
2. 다음 시각/수치 기준을 함께 확인한다.
   - Joystick Part Studio 원본 **89 features**
   - `Joystick_1 / JaD` 약 **46.658 cm3**
   - `Joystick_2 / JfD` 약 **47.925 cm3**
   - original thumb geometry 존재
   - screw/interface geometry 존재
   - I1~I4 및 M1~M4 신규 finger geometry 없음
3. JaD/JfD를 millimetre, **STEP AP242**로 export한다. AP242가 불가능하면 AP214를 사용한다.
4. assembly coordinates를 유지하고 Y-up 등 임의 좌표 변환을 적용하지 않는다.
5. 아래 중 한 방식으로 저장한다.

```text
C:\Users\User\Desktop\OneGrip-Play\local_cad\reference\JAD_CLEAN_PRE_FINGER.step
C:\Users\User\Desktop\OneGrip-Play\local_cad\reference\JFD_CLEAN_PRE_FINGER.step
```

또는 complete clean assembly export라면:

```text
C:\Users\User\Desktop\OneGrip-Play\local_cad\reference\ONEGRIP_CLEAN_PRE_FINGER_REFERENCE.step
```

combined export에는 clean JaD/JfD, original thumb controls, screw/interface geometry를 포함하고
부품 분리를 유지한다. 확실하지 않은 versionId는 제안하지 않는다. 위 형상과 원본 부피를
GUI에서 확인하는 것을 선택 기준으로 삼는다.

## 7. Stop condition

clean STEP이 들어오기 전까지 다음 작업은 시작하지 않는다.

- N1/N2/N3 marker 또는 pocket
- I2/I3/I4/M3/M4 recreation
- shell cut
- holder/carrier/retention
- terminal/wiring routing
- current shell de-feature/patch

사용자가 파일을 저장한 뒤 `계속 진행`이라고 지시하면 manifest/SHA256/OCCT validity를 먼저
검증하고, 그 다음 external marker-only layout으로 진행한다.

