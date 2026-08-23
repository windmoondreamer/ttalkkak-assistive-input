# Exterior-first maximum-lowered Thumb mockup

Date: 2026-08-22  
Mode: LOCAL build123d + OCCT / Onshape 0  
Priority: **exterior first; internal design deferred**

## Result

`FINAL EXTERIOR CLEAN V1`의 clean shell과 최신 Finger 8 배열을 유지하면서 최대 하강
Thumb 외관을 결합했다.

`Thumb translation = (0, +12.25, -21.00) mm`

| Gate | Result |
|---|---:|
| Latest Finger 8 exterior | **PRESERVED** |
| Maximum-lowered Thumb exterior | **APPLIED** |
| Old Thumb openings outside the new authorized region | **REMOVED** |
| Thumb mechanism through cutter | **0** |
| External fastening geometry | **0** |
| JaD/JfD exact review shells | **valid single watertight solids** |
| Exterior review mockup | **READY** |
| Internal design | **DEFERRED** |
| Production / print approval | **NOT EVALUATED** |

## Exterior construction

Exact review STEP은 clean JaD/JfD에서 시작해 다음 user-facing geometry만 적용한다.

- original Thumb button caps 8개
- `Small_joystick_attachment` 1개
- 각 control의 user-facing localized opening envelope
- opening clearance: 0.80 mm

다음은 shell/reference에 포함하지 않았다.

- Backplate
- PushBtn bodies
- HW504 mechanism bodies
- internal carrier / seat
- wiring
- boss / screw / fastening
- N1 뒤 mechanism through relief

따라서 내부 충돌이나 조립성은 이번 외관 gate의 차단 조건으로 사용하지 않았다.

## Actual lower-15 housing visual graft

외관 렌더에서는 추정 opening 형상보다 실제 historical housing을 우선하기 위해
`THUMB_LOWER15_HOUSING_V1` Onshape STL의 Thumb-facing surface patch를 사용했다.

Patch 밖은 `FINAL EXTERIOR CLEAN V1` tessellation이고, patch 안은 실제 lower-15
housing tessellation이다. local Thumb frame에서 다음 mask만 교체했다.

- U: `[-23.5, +23.5] mm`
- V: `[-34.0, +28.0] mm`
- N: `[-8.0, +40.0] mm`

N 범위가 반대편 rear surface를 제외하므로 lower-15 STL에 있던 과거 Finger opening은
visual composite로 들어오지 않는다. 후면 렌더에서 최신
`I2, I3, I4, M3, M4, N1, N2, N3`만 존재함을 확인했다.

| Half | Clean triangles removed | Lower-15 patch triangles inserted | Hybrid triangles |
|---|---:|---:|---:|
| JaD | 2,142 | 3,094 | 14,673 |
| JfD | 1,949 | 2,974 | 13,102 |

Thumb patch N 범위는 circular/split joystick opening 전체가 포함되도록 확장했다.
`08_thumb_housing_shell_only.png`에서는 조이스틱 부품을 숨긴 상태로 원형 recess와
중앙 split opening을 직접 확인할 수 있다.

이 regional mesh graft는 **외관 시각 검토용**이다. tessellation patch seam과 내부가 아직
production 기준으로 재구성되지 않았으므로 해당 combined STL을 출력 승인본으로 사용하면
안 된다.

## Exact shell metrics

| Shell | Valid | Solid | Shell | Faces | Volume (mm³) | Small solids |
|---|---:|---:|---:|---:|---:|---:|
| JaD | true | 1 | 1 | 93 | 46,254.477265 | 0 |
| JfD | true | 1 | 1 | 95 | 47,287.239941 | 0 |

9개 Thumb exterior opening tool은 모두 source shell과 positive-volume intersection을
가졌고, 최종 residual intersection은 전부 `0 mm³`다. 기존 Finger 8 cutter의 최종
residual도 전부 `0 mm³`다.

## Deferred internal review

외관 승인을 받은 뒤 다음 항목을 별도 작업으로 검토한다.

1. Backplate seating
2. HW504 mechanism clearance
3. PushBtn actuation/travel
4. Finger/Thumb internal interference
5. carrier와 assembly path
6. wiring path
7. internal fastening

## Outputs

Source:

- `build123d_workbench/integrated_exterior_lowered_thumb_v1.py`
- `build123d_workbench/render_integrated_exterior_lowered_thumb_v1.py`

Exact exterior review STEP:

- `build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JAD_EXTERIOR_LOWERED_THUMB_V1.step`
- `build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JFD_EXTERIOR_LOWERED_THUMB_V1.step`
- `build123d_workbench/out/integrated_exterior_lowered_thumb_v1/EXTERIOR_LOWERED_THUMB_V1_COMBINED_REFERENCE.step`
- `build123d_workbench/out/integrated_exterior_lowered_thumb_v1/exterior_lowered_thumb_v1_validation.json`

Actual lower-15 exterior visual composite:

- `build123d_workbench/out/integrated_exterior_lowered_thumb_v1/EXTERIOR_FIRST_LOWERED_THUMB_VISUAL_REFERENCE.stl`
- `build123d_workbench/out/integrated_exterior_lowered_thumb_v1/exterior_first_lowered_thumb_visual_manifest.json`

Render:

- `renders/integrated_exterior_lowered_thumb_v1/00_contact_sheet.png`
- `renders/integrated_exterior_lowered_thumb_v1/01_thumb_side.png`
- `renders/integrated_exterior_lowered_thumb_v1/02_thumb_oblique.png`
- `renders/integrated_exterior_lowered_thumb_v1/03_rear_latest_finger.png`
- `renders/integrated_exterior_lowered_thumb_v1/04_front_exterior.png`
- `renders/integrated_exterior_lowered_thumb_v1/05_full_oblique.png`
- `renders/integrated_exterior_lowered_thumb_v1/06_thumb_region_closeup.png`
- `renders/integrated_exterior_lowered_thumb_v1/07_clean_vs_lowered_openings.png`
- `renders/integrated_exterior_lowered_thumb_v1/08_thumb_housing_shell_only.png`

## Decision

**EXTERIOR REVIEW MOCKUP = READY**  
**INTERNAL DESIGN = DEFERRED**  
**PRODUCTION / PRINT APPROVAL = NOT EVALUATED**

다음 단계는 사용자의 외관 검토 결과를 받은 뒤에만 내부 구조를 수정한다.
