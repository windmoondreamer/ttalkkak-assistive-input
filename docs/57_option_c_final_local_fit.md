# 57 — Option C final local fit

## 결론

`OPTION C FINAL LOCAL FIT = HOLD`

Carrier의 0.005690 mm³ 간섭은 **0.18 mm margin의 비기능 모서리 micro-relief**로 완전히 제거했다. 그러나 실제 ITS-1105 고정 단자를 유지한 N2는 4개 cardinal clocking 모두 HW504 B를 피하지 못했다. 가장 좋은 180°도 exact penetration **0.320370 mm³**가 남는다. Cap과 actuator engagement를 보존하는 범위의 custom pose로도 해소할 수 없어 N2 pose 변경은 채택하지 않았다.

## N2 switch clocking / engagement

- `N2 SWITCH CLOCKING = CUSTOM` — 현재 승인된 -5.000°를 유지; 180°는 비교상 최선이지만 미채택
- `N2 AXIS CHANGE = 0.000°`
- `N2 EXTERNAL CENTER CHANGE = 0.000 mm`
- ITS-1105 topology: pins 1–2 common / pins 3–4 common, 네 고정 단자 모두 유지
- 0/90/180/270 zero-distance fixed-root 수: **1 / 2 / 1 / 2**
- 180° exact: **0.000000 mm / 0.320370 mm³**
- 최종 유지 pose: **0.000000 mm / 0.401337 mm³**
- Cap socket radial allowance: **0.050 mm**; engagement-compatible tilt upper bound: **1.174°**

## Carrier micro-relief

- 기존 exact intersection: **0.005690328 mm³**
- Carrier 제거량: **0.088915090 mm³**
- HW504 A 추가 trim 대안: **0.392464446 mm³**
- 선택: **carrier relief** — A 대안보다 작고 approved HW504-A trim을 확대하지 않음
- 보수적 잔여 wall: **1.314848 mm** (minimum 1.20 mm PASS)
- Locating datum / exterior / solid count change: **0 / 0 / 3→3**

## Final local exact gate

| Gate | Clearance | Penetration | Result |
|---|---:|---:|---|
| HW504 A ↔ carrier | 0.004964 mm | 0.000000000 mm³ | PASS |
| HW504 B ↔ carrier | 2.401754 mm | 0.000000000 mm³ | PASS |
| HW504 B ↔ N2 fixed roots | 0.000000 mm | 0.401336507 mm³ | HOLD |
| HW504 B ↔ N2 body | 0.867511 mm | 0.000000000 mm³ | PASS |
| N1 ↔ N2 | 2.391916 mm | 0.000000000 mm³ | PASS |
| carrier ↔ local shell | 1.113872 mm | 0.000000000 mm³ | PASS |

## Freeze / reuse

- `HW504 A PROTECTED REMOVAL = 0`
- `HW504 B CHANGE = 0`
- Joystick center / pivot axes / travel / Thumb relative geometry change = **0**
- `ORIGINAL THUMB RETAINED = 19/20`
- `THUMB REUSE = 95.0%`
- Finger exterior = **PRESERVED**; exterior shell = **UNCHANGED**

## Final verdict

- `OPTION C FINAL LOCAL FIT = HOLD`
- `N2 TERMINAL FIT = HOLD`
- `CARRIER FIT = PASS`
- `HW504 B EXACT REUSE = PASS`
- `JOYSTICK KINEMATICS = PASS`
- `FINGER EXTERIOR = PRESERVED`
- `EXTERIOR = UNCHANGED`

## Outputs / STOP

- `build123d_workbench/out/option_c_final_local_fit/option_c_final_local_fit.json`
- `build123d_workbench/out/option_c_final_local_fit/OPTION_C_FINAL_LOCAL_FIT.step`
- `renders/option_c_final_local_fit/01_n2_terminal_before_after.png`
- `renders/option_c_final_local_fit/02_n2_clocking_comparison.png`
- `renders/option_c_final_local_fit/03_carrier_micro_relief_closeup.png`
- `renders/option_c_final_local_fit/04_final_transparent_local_crop.png`

Production geometry에는 반영하지 않았다. 이 local fit 결과에서 STOP한다.
