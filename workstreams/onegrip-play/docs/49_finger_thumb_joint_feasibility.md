# OneGrip Play — Finger V2 + maximum-lowered thumb joint feasibility

## 1. 결론

이번 LOCAL build123d/OCCT feasibility 결과는 **NO / HOLD**이다.

승인된 Finger V2 외부 8-button center와 cap은 그대로 유지할 수 있었고, 원본
thumb control cluster에도 scale 또는 상대 형상 변경을 가하지 않았다. 그러나
원본 thumb를 `(0,+12.25,-21.00) mm`까지 강체 이동한 target은 다음 독립
blocker 때문에 실제 제작 가능한 joint로 닫히지 않는다.

1. target thumb와 고정 screw 1/2가 각각 관통한다.
2. 1.60 mm 저상형 individual carrier로 바꿔도 N1 terminal root가 thumb와
   `0.074884210 mm³` 관통한다.
3. N2 formed wiring의 thumb 최소 여유가 `0.139748324 mm`뿐이다.
4. N1/N2 새 carrier 사이 여유가 `1.138354070 mm`로 1.20 mm 기준에 미달한다.
5. N2 carrier와 opposite shell seam 여유가 `0.204599960 mm`뿐이다.
6. lower-15 shell의 기존 sampled seating gap도 `0.252455756 mm`로 robust하지
   않으며, 새 analytic thumb interface는 production CAD에 작성하지 않았다.

따라서 현재 carrier 충돌만으로 전체 FAIL을 선언한 것이 아니다. 허용된 범위에서
새 carrier/wiring architecture를 직접 prototype한 뒤에도 target gate가 닫히지
않는 것을 확인한 결과다.

## 2. 작업 경계와 source

- mode: LOCAL build123d/OCCT feasibility branch
- Onshape access/write: **0**
- production `finger_controls_v2.py` 수정: **0**
- production STEP/STL overwrite: **0**
- physical validation coupon/plate 재생성: **0**
- 보존 상태: `DIGITAL PRINTABILITY = PASS`, `PHYSICAL VALIDATION KIT = READY`
- exact assembly reference:
  `lower_adapter/local_cad/reference/ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step`
- assembly SHA-256:
  `deb2f78838b41ab125247bd4068d7c0d08b5bddf780b449534b716fe35dc0ed4`
- Finger source: immutable `build_finger_controls_v2()` result
- target coordinate recovery: assembly `Joystick_1` inverse location을 적용해
  Part Studio 좌표계로 정규화

Exact assembly에서 읽은 target joint source는 backplate 1, thumb caps 8,
push buttons 8, exact HW504_B solids 2, small joystick attachment 1, fixed M3
screws 3, assembly shells 2이다.

## 3. Hard freeze

| 항목 | 결과 |
|---|---:|
| thumb target translation | `(0.000,+12.250,-21.000) mm` |
| I2 center movement | `0.000 mm` |
| I3 center movement | `0.000 mm` |
| I4 center movement | `0.000 mm` |
| M3 center movement | `0.000 mm` |
| M4 center movement | `0.000 mm` |
| N1 center movement | `0.000 mm` |
| N2 center movement | `0.000 mm` |
| N3 center movement | `0.000 mm` |
| thumb rigid shape/scale change | 없음 |
| maximum switch axis adjustment | `0.000°` |

## 4. Target thumb vs current Finger V2 collision matrix

아래 `joint envelope`는 switch body, actuator, four terminal roots, 기존 wiring
envelope를 함께 비교한 값이다. 비관통 row에는 minimum clearance를, 관통 row에는
OCCT exact boolean penetration volume과 intersecting pair 수를 기록했다. OCCT
distance는 관통 상태에서 `0`을 반환하므로 임의의 bounding-box penetration depth를
exact depth처럼 보고하지 않았다.

| Button | joint minimum clearance mm | penetration volume mm³ | intersecting pairs | current verdict |
|---|---:|---:|---:|---|
| I2 | 3.499534493 | 0 | 0 | compatible |
| I3 | 6.490709362 | 0 | 0 | compatible |
| I4 | 6.543420513 | 0 | 0 | compatible |
| M3 | 11.608111007 | 0 | 0 | compatible |
| M4 | 12.018305400 | 0 | 0 | compatible |
| N1 | 0 | 30.630485923 | 4 | incompatible |
| N2 | 0 | 20.567520809 | 7 | incompatible |
| N3 | 10.851022157 | 0 | 0 | compatible |

전체 target thumb와 current Finger carriers의 exact 결과는 clearance `0`,
penetration `71.642203157 mm³`, intersecting carrier pairs `2`이다. 따라서:

`CURRENT FINGER V2 INTERNALS = REDESIGN REQUIRED`

### N1/N2 current decomposition

| Region | N1 | N2 |
|---|---:|---:|
| switch body penetration mm³ | 0.003728493 | 0.001053047 |
| actuator clearance mm | 3.926724282 | 3.890443779 |
| terminal-root penetration mm³ | 0.692490150 | 0.562617469 |
| wiring penetration mm³ | 29.934267280 | 20.003850292 |
| current shared carrier penetration mm³ | 71.642203157 | 71.642203157 |
| external cap clearance mm | 4.677532130 | 4.664046750 |

External cap은 충돌하지 않는다. 문제는 승인된 외부 center/cap이 아니라 그 뒤의
switch depth, terminal root, wiring, shared rear-plate carrier다.

## 5. Prototype internal redesign

Prototype architecture는 기존 `N1_N2_shared_carrier`를 제거하고 다음으로 바꿨다.

- N1 individual low-profile C-collar
- N2 individual low-profile C-collar, JfD split side trim
- front depth `3.20 mm`
- carrier wall `1.60 mm`
- rear plate와 N1/N2 bridge 없음
- axis adjustment `0.00°`
- four leads/switch, distal one-bend forming
- local solder envelope 후 insulated tangent route
- 나머지 I2/I3, I4, M3, M4/N3 carrier 4개 유지

새 총 carrier 수는 **6개**이다. N1/N2 carrier는 둘 다 valid single solid다.

### Redesigned N1 exact target metrics

| Element | minimum clearance mm | penetration mm³ |
|---|---:|---:|
| switch body | 1.469958909 | 0 |
| actuator | 2.479011796 | 0 |
| terminal roots | 0 | 0.074884210 |
| carrier | 0.219110191 | 0 |
| formed/soldered wiring | 0.628240301 | 0 |

### Redesigned N2 exact target metrics

| Element | minimum clearance mm | penetration mm³ |
|---|---:|---:|
| switch body | 1.422264749 | 0 |
| actuator | 5.356460852 | 0 |
| terminal roots | 0.640232324 | 0 |
| carrier | 0.362644092 | 0 |
| formed/soldered wiring | 0.139748324 | 0 |

Joint 전체의 minimum thumb-to-switch-body clearance는 `1.422264749 mm`이다.
switch body 자체는 target에 들어가지만 terminal/wiring/service와 carrier가 robust
gate를 넘지 못한다.

| Redesign cross-check | result | gate | verdict |
|---|---:|---:|---|
| minimum thumb ↔ proposed carrier | 0.219110191 mm | 0.80 mm service target | HOLD |
| minimum thumb ↔ proposed wiring | 0.139748324 mm | 0.80 mm service target | HOLD |
| N1 ↔ N2 switch body separation | 4.571309551 mm | 1.20 mm | PASS |
| N1 ↔ N2 carrier separation | 1.138354070 mm | 1.20 mm | HOLD |
| N2 carrier ↔ opposite shell seam | 0.204599960 mm | robust closure | HOLD |
| critical carrier wall | 1.60 mm | 1.20 min / 1.60 preferred | PASS |
| max switch axis adjustment | 0.00° | 3° preferred / 5° max | PASS |

따라서 `REDESIGNED INTERNALS = HOLD`이다. 더 깊은 carrier는 target thumb 여유를
더 감소시키므로 feasibility seed에는 가장 얕은 제조 가능 collar를 사용했다.

## 6. Fixed screw audit and lowering sweep

Target에서 전체 thumb와 exact fixed screws의 결과는 clearance `0`, total
penetration `12.094078064 mm³`, intersecting pairs `2`이다.

| Fixed screw | target clearance mm | penetration mm³ | result |
|---|---:|---:|---|
| screw 1 | 0 | 2.863144738 | HOLD |
| screw 2 | 0 | 9.230933326 | HOLD |
| screw 3 | 26.352484683 | 0 | PASS |

관통 상대는 screw 1 ↔ joystick mechanism, screw 2 ↔ backplate이다. thumb caps,
push buttons, small attachment는 screw와 관통하지 않는다.

Sweep은 original과 target 사이에서 exact relative geometry를 사용했다. 큰 thumb
module을 반복 복제하는 대신 screws를 inverse translation한 것은 동일한 상대거리
계산이다.

| t | translation XYZ mm | minimum screw clearance mm |
|---:|---|---:|
| 0.00 | `(0,0,0)` | 2.536521222 |
| 0.25 | `(0,+3.0625,-5.2500)` | 0.173046955 |
| 0.50 | `(0,+6.1250,-10.5000)` | 0 |
| 0.75 | `(0,+9.1875,-15.7500)` | 0 |
| 1.00 | `(0,+12.2500,-21.0000)` | 0 |

2.50 mm screw gate 경계의 refined 결과:

- robust fraction: `t = 0.0029296875` (`0.29296875%`)
- maximum robust translation: **`(0,+0.035888672,-0.061523438) mm`**
- boundary clearance: `2.508712209 mm`

Original Finger V2의 prior original-thumb clearance는 `10.746084 mm`였으므로 이
아주 작은 interval에서는 Finger side보다 screw gate가 선행 제한한다. User target의
실질적인 lowering을 허용하는 값은 아니다.

## 7. Shell, seam, wiring and assembly

### Shell/interface

Clean historical shell과 Finger V2 shell은 original thumb opening/interface를
갖고 있어 target interface로 사용할 수 없다. 과거 lower-15 watertight shell mesh의
moved-backplate sampled gap은 `0.252455756 mm`, penetration `0`이지만 robust seating
여유로 인정하지 않았다. 이 값은 local analytic target shell B-rep의 full-face
clearance가 아니라 기존 lower-15 mesh 연구의 sampled evidence다.

Feasibility interface seed는 0.80 mm non-seating service clearance, three seating
pads, continuous local flange `1.60 mm`이지만 이번 금지 범위 때문에 실제 production
shell boolean은 작성하지 않았다. 따라서 요구된 minimum thumb↔shell의 유일한
직접 수치는 `0.252455756 mm sampled / HOLD`이며 새 interface는 미검증 상태다.

### Wiring

제안 path는 다음 연속 envelope를 갖는다.

`terminal root → 2.80 mm formed lead → solder envelope → 10 mm insulated tangent route`

Path topology는 연속이지만 N1 root 관통과 N2 wire `0.139748324 mm` 때문에
`WIRING = HOLD`이다.

### Assembly sequence checked

1. I2/I3, I4, M3, M4/N3 module을 먼저 preload하고 wire를 아래로 routing한다.
2. N1과 N2를 seam에서 각각 low-profile collar로 load한다.
3. N1/N2 distal lead를 한 번 성형하고 pre-solder한다.
4. target flange 위치에 rigid thumb module을 설치한다.
5. JaD/JfD를 닫으며 opposite shell이 N2 collar를 capture한다.
6. 2.50 mm screw keep-out이 성립할 때만 unchanged screws를 체결한다.

6번 조건이 target에서 성립하지 않고 seam/service clearance도 부족하므로
`ASSEMBLY = HOLD`이다.

## 8. Required final numbers

| Required item | final value |
|---|---|
| THUMB TARGET | `(0,+12.25,-21.00) mm` |
| Finger centers moved | all `0.000 mm` |
| thumb ↔ each Finger joint | I2 3.499534; I3 6.490709; I4 6.543421; M3 11.608111; M4 12.018305; N1 penetration 30.630486 mm³; N2 penetration 20.567521 mm³; N3 10.851022 mm |
| minimum thumb ↔ redesigned switch body | `1.422264749 mm` |
| minimum thumb ↔ redesigned carrier | `0.219110191 mm` |
| minimum thumb ↔ screw | `0 mm`, penetration `12.094078064 mm³` |
| minimum thumb ↔ shell | `0.252455756 mm sampled`, not robust |
| N2 seam clearance | `0.204599960 mm` |
| minimum wall | `1.60 mm` |
| maximum Finger switch axis adjustment | `0.00°` |
| new carrier count | `6` |
| MAX ROBUST THUMB LOWERING | `(0,+0.035888672,-0.061523438) mm` |

## 9. Final gates

| Gate | Verdict |
|---|---|
| FINGER EXTERNAL LAYOUT | **PRESERVED** |
| THUMB TARGET `(0,+12.25,-21.00)` | **HOLD** |
| CURRENT FINGER INTERNALS | **REDESIGN REQUIRED** |
| REDESIGNED INTERNALS | **HOLD** |
| WIRING | **HOLD** |
| ASSEMBLY | **HOLD** |
| FDM | **HOLD** |
| MAX ROBUST THUMB LOWERING | **`(0,+0.035888672,-0.061523438) mm`** |

최종 질문:

> Finger 외부 8버튼 위치를 그대로 유지하고, 원본 thumb control cluster도 형태
> 그대로 유지하면서, thumb를 `(0,+12.25,-21.00)`까지 내린 실제 제작 가능한
> 구조를 만들 수 있는가?

**NO.** 기존 screws와 frozen target을 동시에 유지하는 조건에서 성립하지 않으며,
N1/N2 저상형 내부 재설계만으로도 해결되지 않는다.

## 10. Feasibility-only outputs

- numeric audit:
  `build123d_workbench/out/finger_thumb_joint_feasibility/finger_thumb_joint_feasibility.json`
- current collision audit:
  `build123d_workbench/out/finger_thumb_joint_feasibility/current_collision_audit.json`
- exact target module:
  `build123d_workbench/out/finger_thumb_joint_feasibility/THUMB_TARGET_EXACT_MODULE.step`
- joint reference:
  `build123d_workbench/out/finger_thumb_joint_feasibility/FINGER_THUMB_JOINT_FEASIBILITY_REFERENCE.step`
- N1/N2 prototype carriers: isolated STEP/STL in the same output directory
- N1/N2 formed wiring: isolated STEP in the same output directory
- required renders:
  `renders/finger_thumb_joint_feasibility/01...09_*.png`
- contact sheet:
  `renders/finger_thumb_joint_feasibility/00_contact_sheet.png`

These are feasibility/reference artifacts only. They are not production-ready CAD or a
print-validation kit.
