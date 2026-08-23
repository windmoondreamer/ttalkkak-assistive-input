# OneGrip Play — cross-session final handoff

Handoff ID: `ONEGRIP_EXTERIOR_FIRST_MAX_LOWERED_THUMB_2026-08-22`  
Date: 2026-08-22  
Workspace: `C:\Users\User\Desktop\OneGrip-Play`

## 0. 가장 중요한 현재 상태

현 시점의 최종 기준은 **최신 Finger 8 + 최대 하강 Thumb를 결합한 외관 검토본**이다.

이 상태는:

- **EXTERIOR REVIEW MOCKUP = READY**
- **USER EXTERIOR APPROVAL = 아직 별도 확정되지 않음**
- **INTERNAL DESIGN = DEFERRED**
- **PRODUCTION / PRINT APPROVAL = NOT EVALUATED**

이다.

즉, 다음 세션은 이 외관을 기준으로 이어가야 하지만 이를 바로 출력 가능한 production
CAD라고 선언하면 안 된다.

## 1. Authoritative visual baseline

사용자가 확인해야 할 현 시점 외관 source-of-truth는 다음 두 파일이다.

1. 전체 외관 contact sheet  
   `renders/integrated_exterior_lowered_thumb_v1/00_contact_sheet.png`

2. Thumb 하우징만 표시한 close-up  
   `renders/integrated_exterior_lowered_thumb_v1/08_thumb_housing_shell_only.png`

두 번째 렌더에서 다음이 반드시 보여야 한다.

- maximum-lowered circular joystick recess
- 원형 recess 중앙의 split joystick opening
- lowered Thumb button opening 8개
- original Thumb 위치의 중복 opening 없음

Joystick opening은 처음 visual patch N 범위가 너무 얕아 누락됐으나, 최종적으로 local
N mask를 `[-8,+40] mm`로 확장해 실제 `THUMB_LOWER15_HOUSING_V1` 외피에서 복구했다.
이전의 조이스틱 구멍 누락 렌더는 폐기한다.

## 2. Frozen exterior intent

### Finger exterior

허용되는 최신 Finger control은 다음 8개뿐이다.

`I2, I3, I4, M3, M4, N1, N2, N3`

금지/폐기된 legacy Finger 흔적:

- I1
- M1
- M2
- 이전 partial opening 및 breakthrough
- N1 뒤 대형 mechanism through relief
- V3 외부 boss, tube, barrel, bracket 및 fastening fixture

### Thumb exterior

Original Thumb cluster의 rigid transform:

`(ΔX, ΔY, ΔZ) = (0.00, +12.25, -21.00) mm`

외부 배치에서 상대 geometry를 변경하지 않는다.

- original Thumb button caps: 8
- joystick exterior: circular recess + central split opening
- old/original-position Thumb opening: 제거
- lowered position만 유지

## 3. Source roles — 혼동 금지

### A. Clean exact-shell source

`build123d_workbench/integrated_exterior_clean_v1.py`

역할:

- old Thumb opening exact surface restoration
- latest Finger 8 opening 적용
- legacy/V3 external geometry 제거

### B. Exterior-first exact review STEP builder

`build123d_workbench/integrated_exterior_lowered_thumb_v1.py`

역할:

- clean exact JaD/JfD에서 시작
- maximum-lowered external controls 위치 적용
- 9개 localized user-facing opening envelope 적용
- internal parts와 external fastening은 포함하지 않음

출력:

- `JAD_EXTERIOR_LOWERED_THUMB_V1.step`
- `JFD_EXTERIOR_LOWERED_THUMB_V1.step`
- `EXTERIOR_LOWERED_THUMB_V1_COMBINED_REFERENCE.step`

주의: 이 STEP set의 Thumb opening은 **0.80 mm localized envelope review geometry**다.
실제 historical lower-15 opening surface의 완전한 exact transfer는 아니다.

### C. Actual lower-15 visual exterior

`build123d_workbench/render_integrated_exterior_lowered_thumb_v1.py`

역할:

- patch 밖: `FINAL EXTERIOR CLEAN V1` exact-shell tessellation
- patch 안: actual `THUMB_LOWER15_HOUSING_V1` STL exterior
- rear/opposite Finger surface는 patch 대상에서 제외
- corrected circular joystick opening 포함

Visual reference:

`build123d_workbench/out/integrated_exterior_lowered_thumb_v1/EXTERIOR_FIRST_LOWERED_THUMB_VISUAL_REFERENCE.stl`

주의: regional mesh graft이므로 **외관 검토용**이며 print 승인본이 아니다.

## 4. Current gates

| Gate | Result |
|---|---:|
| LATEST FINGER 8 EXTERIOR | **PRESERVED** |
| MAXIMUM-LOWERED THUMB EXTERIOR | **APPLIED** |
| OLD THUMB OPENINGS | **REMOVED** |
| THUMB MECHANISM THROUGH CUTTER | **0** |
| EXTERNAL FASTENING GEOMETRY | **0** |
| JaD valid single watertight exact review shell | **PASS** |
| JfD valid single watertight exact review shell | **PASS** |
| EXTERIOR REVIEW MOCKUP | **READY** |
| USER EXTERIOR APPROVAL | **PENDING** |
| INTERNAL DESIGN | **DEFERRED** |
| PRODUCTION / PRINT APPROVAL | **NOT EVALUATED** |

Exact review shell metrics:

| Shell | Solids | Shells | Faces | Edges | Vertices | Volume (mm³) | Small solids |
|---|---:|---:|---:|---:|---:|---:|---:|
| JaD | 1 | 1 | 93 | 277 | 192 | 46,254.477265 | 0 |
| JfD | 1 | 1 | 95 | 286 | 198 | 47,287.239941 | 0 |

Finger 8 cutter residual과 Thumb 9 opening-tool residual은 모두 `0 mm³`다.

## 5. Visual patch registry

Thumb local patch mask:

- U: `[-23.5,+23.5] mm`
- V: `[-34.0,+28.0] mm`
- N: `[-8.0,+40.0] mm`
- opposite/rear Finger surface rejection: `true`

| Half | Clean triangles removed | Lower-15 triangles inserted | Hybrid triangles |
|---|---:|---:|---:|
| JaD | 2,142 | 3,094 | 14,673 |
| JfD | 1,949 | 2,974 | 13,102 |

이 N 범위를 다시 `16 mm` 이하로 축소하면 circular joystick recess가 사라지므로 금지한다.

## 6. Internal geometry policy

현재 exterior reference에는 다음 internal geometry를 포함하지 않았다.

- Backplate
- PushBtn bodies
- HW504 mechanism bodies
- Finger/Thumb carrier 및 seat
- terminal/wiring
- screw/boss/internal fastening

외관 승인을 받은 이후 별도로 검토할 항목:

1. Thumb Backplate seating
2. HW504 mechanism clearance
3. PushBtn actuation/travel
4. Finger/Thumb internal interference
5. carrier와 assembly path
6. wiring path
7. internal fastening
8. print orientation, support, tolerance 및 physical test

내부 문제가 생겨도 외관에 새 boss, lump, tube 또는 N1 뒤 through-window를 임의로
추가하면 안 된다. 외관 변경이 필요하면 먼저 사용자 승인 대상으로 분리한다.

## 7. Obsolete / do not resume

다음 상태를 최신본으로 사용하지 않는다.

- `finger_thumb_integrated_v3`의 external boss/fastening architecture
- `finger_thumb_exterior_clean_v4`
- `integrated_exterior_clean_v1` 단독 외관: lowered Thumb opening이 없는 중간 HOLD 상태
- 조이스틱 circular opening이 누락된 초기 lower-15 patch render
- N1 뒤 대형 localized HW504 through cutter
- legacy lower-15 shell 전체를 그대로 사용해 old Finger opening을 재도입하는 방식

## 8. Reproduction commands

PowerShell, workspace root에서 실행:

```powershell
& '.venv-build123d\Scripts\python.exe' -m build123d_workbench.integrated_exterior_lowered_thumb_v1
& '.venv-build123d\Scripts\python.exe' -m build123d_workbench.render_integrated_exterior_lowered_thumb_v1
```

첫 명령은 clean exact shell부터 다시 계산하므로 약간 오래 걸릴 수 있다. Onshape 호출은
발생하지 않는다.

## 9. Key output checksums

| File | SHA-256 |
|---|---|
| `integrated_exterior_clean_v1.py` | `2494b6a98a32c4f9589e0acf2b56cc82970ab7e1a3fc01d302c481de3b689dc2` |
| `integrated_exterior_lowered_thumb_v1.py` | `57ea6600118faf0d509f9ee4c5fc35704953d65ab162eaa499716513c4be75e3` |
| `render_integrated_exterior_lowered_thumb_v1.py` | `9f97f77fa0f21804e4efbd929ff994c73fb94476333de31904f23264530fb76d` |
| `JAD_EXTERIOR_LOWERED_THUMB_V1.step` | `b223757ee25fdd5eddf710b8666bcd388d4221235d8d876f620eb0005d5b75b6` |
| `JFD_EXTERIOR_LOWERED_THUMB_V1.step` | `d1bf68b105dce11374ab1f89981ee503a5591d2ff7fa5175777432171855bf7f` |
| `EXTERIOR_LOWERED_THUMB_V1_COMBINED_REFERENCE.step` | `95abe90a4a5f866c31834b24c3d5ad00556788513a9d162fd2b3615347419609` |
| `EXTERIOR_FIRST_LOWERED_THUMB_VISUAL_REFERENCE.stl` | `8be75b89bcb30dc4fd375c744be3dd08f63bf599223f48e9d5acc9d10046a8c7` |
| `00_contact_sheet.png` | `87da5e7057117735a171384fd4ca132845b5809907fa0e78a94a7f41e03dc916` |
| `08_thumb_housing_shell_only.png` | `7c6d76e3c46c054b98a9d7923e893b5b485c6416eef2481de745cf9da8031e97` |

Full machine-readable registry:

`build123d_workbench/out/integrated_exterior_lowered_thumb_v1/cross_session_handoff.json`

## 10. Exact production continuation requirement

다음 세션이 visual mockup을 production exact STEP으로 승격하려면 사용자의 외관 승인을
먼저 받아야 한다. 그 다음 `THUMB_LOWER15_HOUSING_V1`의 exact JaD/JfD shell STEP을
Onshape GUI에서 수동 export해 제공하는 방법이 가장 안전하다.

현재 로컬 lower-15 source는 STL이므로 actual opening surface는 시각적으로 정확하지만
exact editable B-rep source는 아니다. 이를 무시하고 visual STL을 STEP으로 단순 변환해
production baseline으로 선언하면 안 된다.

## 11. Ready-to-paste next-session prompt

아래 블록을 새 세션에 그대로 붙여 넣는다.

```text
OneGrip Play 작업을 다음 handoff 기준으로 이어간다.

먼저 반드시 읽을 파일:
C:\Users\User\Desktop\OneGrip-Play\docs\54_cross_session_final_handoff.md

Machine registry:
C:\Users\User\Desktop\OneGrip-Play\build123d_workbench\out\integrated_exterior_lowered_thumb_v1\cross_session_handoff.json

현재 기준:
- latest Finger 8 = I2/I3/I4/M3/M4/N1/N2/N3
- maximum-lowered Thumb translation = (0,+12.25,-21) mm
- circular joystick recess + central split opening 존재
- N1 뒤 through cutter = 폐기
- external V3 fastening/boss = 폐기
- EXTERIOR REVIEW MOCKUP = READY
- USER EXTERIOR APPROVAL = PENDING
- INTERNAL DESIGN = DEFERRED
- PRINT APPROVAL = NOT EVALUATED

이전 V3/V4나 조이스틱 구멍 누락본을 최신본으로 사용하지 마라.
현재 visual source-of-truth는:
renders/integrated_exterior_lowered_thumb_v1/00_contact_sheet.png
renders/integrated_exterior_lowered_thumb_v1/08_thumb_housing_shell_only.png
이다.

내부 구조를 수정하기 전에 이 handoff의 source 역할과 제한을 요약해 보고하라.
사용자 지시 없이 외관 변경, Onshape write 또는 출력 승인 선언을 하지 마라.
```

## 12. Handoff decision

**CURRENT EXTERIOR HANDOFF = COMPLETE**  
**NEXT SESSION BASELINE = EXTERIOR-FIRST MAX-LOWERED THUMB V1**  
**INTERNAL / PRODUCTION FINALIZATION = NOT STARTED**

