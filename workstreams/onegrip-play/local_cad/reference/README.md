# Immutable reference policy

현재 저장소에서 발견된 주 shell reference는 다음 STL이다.

- `exports/thumb_lower15_housing_mockup/OneGrip_lower15_housing_Joystick_1_JaD.stl`
- `exports/thumb_lower15_housing_mockup/OneGrip_lower15_housing_Joystick_2_JfD.stl`

두 파일은 원본을 덮어쓰지 않는 immutable mesh reference다. 둘 다 watertight한 단일
mesh이지만 OCCT solid가 아니므로 production shell boolean의 baseline으로 승격하지
않는다.

필수 보완 reference:

- JaD shell STEP/STP (millimetre, current intended baseline)
- JfD shell STEP/STP (millimetre, current intended baseline)

추가 권장 reference:

- screw/boss exact B-rep 또는 screw center/axis/radius/depth registry
- original THUMB rigid module STEP

새 reference가 들어오면
`build123d_workbench/inventory_local_references.py`를 다시 실행해 manifest를 갱신한다.

