# 64 — I2/I3 PRODUCTION-INTENT BUTTON MECHANISMS

## 결론

I2/I3의 exterior feasibility는 재평가하지 않았다. 두 cap의 승인 center/orientation과 의도된 shell 대비 2.5°를 그대로 유지하고, 기존 shared carrier에 내부 기능만 추가했다.

초기 unrelieved 9.3 mm C-guide candidate는 I2에서 **0.265878 mm³**, I3에서 **0.013526 mm³** local-shell penetration이 있었다.

**THIS INTERNAL CANDIDATE FAILED**

외형 대신 guide의 shell-facing 비기능 front/corner material만 exact local relief했다. 최종 guide-shell penetration은 둘 다 0이며, 6.5 mm shoulder, 6.8 mm cavity, Ø4.5/Ø4.8 guide pair, independent service slot, 0.350 mm hard stop은 유지된다.

## 1. Current exact audit

| item | I2 | I3 |
|---|---:|---:|
| cap ↔ switch top | 0.000000° | 0.000000° |
| cap ↔ local shell plane | 2.500000° | 2.500000° |
| cap ↔ actuator lateral offset | 0.000000000 mm | 0.000000000 mm |
| current rear reaction gap | 0.110000 mm | 0.110000 mm |
| cap ↔ local shell | 0.200000 mm | 0.200000 mm |
| body ↔ local shell | 1.600522 mm | 2.081731 mm |

2.5°는 오류가 아니라 승인된 internal-axis tilt다. cap을 shell과 평행하게 재정렬하지 않았다.

## 2. Production-intent architecture

두 버튼 공통 load path:

`finger → frozen exterior cap → Ø3.0 central contact → ITS actuator/body → terminal-window flat reaction frame → shared carrier/shell`

- retention: 6.5 mm square positive shoulder
- guide: Ø4.5 tail / Ø4.8 bore, radial clearance 0.15 mm
- rotation/rock control: 6.5 mm shoulder / 6.8 mm cavity, lateral clearance 0.15 mm
- return: ITS internal return only; 별도 spring 없음
- hard stop: guide rear structural plane at 0.350 mm
- service: open C-guide + lateral switch service + central 4.0 × 3.2 mm terminal/wire window
- stationary I2/I3 guide overlap은 shared carrier material로 fuse되며 각 cap의 타 guide motion envelope penetration은 0

### Rear reaction

| item | I2 | I3 |
|---|---:|---:|
| type | terminal-window flat frame | terminal-window flat frame |
| plastic-body contact area | 24.907 mm² | 24.907 mm² |
| minimum wall | 1.200 mm | 1.200 mm |
| connected contact patch | 1 | 1 |

기존 0.110 mm rear gap을 frame이 메우며 ITS terminal envelope를 구조적으로 누르지 않는다. tangent-only point support가 아니라 각 버튼 **24.907 mm²**의 broad rear plastic contact다.

## 3. Independent exact motion

### I2

| travel mm | cap-guide pen mm³ | cap-shell pen mm³ | contact gap mm | hard-stop residual mm |
|---:|---:|---:|---:|---:|
| 0.000 | 0.000000000 | 0.000000000 | 0.000000000 | 0.350 |
| 0.175 | 0.000000000 | 0.000000000 | 0.000000000 | 0.175 |
| 0.350 | 0.000000000 | 0.000000000 | 0.000000000 | 0.000 |

### I3

| travel mm | cap-guide pen mm³ | cap-shell pen mm³ | contact gap mm | hard-stop residual mm |
|---:|---:|---:|---:|---:|
| 0.000 | 0.000000000 | 0.000000000 | 0.000000000 | 0.350 |
| 0.175 | 0.000000000 | 0.000000000 | 0.000000000 | 0.175 |
| 0.350 | 0.000000000 | 0.000000000 | 0.000000000 | 0.000 |

각 상태에서 cap/guide, cap/shell, cap/base carrier, cap/actuator 및 타 버튼 guide/body의 unintended penetration은 0이다. FULL에서 각 shoulder가 자기 carrier hard stop에 도달하며 타 cap/switch 이동량은 0이다.

### Combined states

| I2 travel mm | I3 travel mm | maximum cross penetration mm³ | cap-cap distance mm |
|---:|---:|---:|---:|
| 0.350 | 0.000 | 0.000000000 | 2.244120 |
| 0.000 | 0.350 | 0.000000000 | 2.224042 |
| 0.350 | 0.350 | 0.000000000 | 2.141672 |

## 4. Terminal map

T1/T2/T3/T4는 electrical pair를 가정하지 않고 각각 보수적인 **실물 terminal + radial service 0.12 mm envelope**로 검사했다. 8개 모두 무절단 유지한다.

### I2

| terminal | carrier mm | shell mm | other switch mm | other guide mm | 처리 |
|---|---:|---:|---:|---:|---|
| T1 | 0.000000 | 4.217987 | 7.551163 | 8.029795 | 유지 |
| T2 | 0.000000 | 3.027104 | 7.262719 | 7.065530 | 유지 |
| T3 | 0.000000 | 5.437997 | 0.884017 | 3.324839 | 유지 |
| T4 | 0.000000 | 4.991460 | 0.216587 | 2.116486 | 유지 |

### I3

| terminal | carrier mm | shell mm | other switch mm | other guide mm | 처리 |
|---|---:|---:|---:|---:|---|
| T1 | 0.000000 | 5.035588 | 0.873031 | 2.959363 | 유지 |
| T2 | 0.000000 | 5.706720 | 1.039899 | 4.051643 | 유지 |
| T3 | 0.000000 | 5.582112 | 7.628299 | 7.242535 | 유지 |
| T4 | 0.000000 | 5.115023 | 7.516416 | 8.372979 | 유지 |

## 5. Shared carrier / FDM

- current approved I2/I3 carrier removed volume: **0.000000000 mm³**
- final carrier solid count: **1**
- floating body: **False**
- local shell penetration: **0.000000000 mm³**
- critical minimum wall: **1.200 mm**
- tiny snap/hook: 없음

## 6. N1/N2 hard-freeze regression

- frozen file SHA-256 guard: **PASS**
- N1 approved mechanism: **PASS**
- N2 carrier ↔ HW504-A: **0.304180346 mm** ≥ 0.304180346
- N2 carrier ↔ HW504-B: **1.360983710 mm** ≥ 1.360983710
- N2 T1/T3 ↔ HW504-B: **2.119093040 mm** ≥ 2.119093040
- I2/I3 carrier ↔ frozen N1/N2 carrier penetration: **0.000000000 mm³**

## 7. Outputs

- `renders\i2_i3_production_intent_mechanism\01_i2_i3_current_structure.png`
- `renders\i2_i3_production_intent_mechanism\02_i2_i3_exploded.png`
- `renders\i2_i3_production_intent_mechanism\03_i2_rest_full_section.png`
- `renders\i2_i3_production_intent_mechanism\04_i3_rest_full_section.png`
- `renders\i2_i3_production_intent_mechanism\05_rear_reaction_supports.png`
- `renders\i2_i3_production_intent_mechanism\06_i2_i3_terminal_map.png`
- `renders\i2_i3_production_intent_mechanism\07_both_buttons_full.png`
- `renders\i2_i3_production_intent_mechanism\08_shared_carrier_transparent.png`
- `renders\i2_i3_production_intent_mechanism\09_n1_n2_frozen_regression.png`

- `build123d_workbench\out\i2_i3_production_intent_mechanism\i2_i3_production_intent_mechanism.json` — lightweight exact JSON
- `build123d_workbench\out\i2_i3_production_intent_mechanism\I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step` — I2/I3 local shared carrier only
- `build123d_workbench\out\i2_i3_production_intent_mechanism\I2_PRODUCTION_INTENT_CAP_LOCAL.step` / `build123d_workbench\out\i2_i3_production_intent_mechanism\I3_PRODUCTION_INTENT_CAP_LOCAL.step` — local cap components only
- full shell / full assembly / STL / print plate: **생성하지 않음**

## 8. FINAL / STOP

- I2 ARCHITECTURE = **ACCEPT**
- I3 ARCHITECTURE = **ACCEPT**
- I2 MOTION = **PASS**
- I3 MOTION = **PASS**
- SHARED CARRIER = **PASS**
- I2 TERMINALS = **PASS**
- I3 TERMINALS = **PASS**
- N1/N2 FROZEN BASELINE = **PRESERVED**
- EXTERIOR = **PRESERVED**

I2/I3에서 STOP한다. M4/N3/I4/M3로 자동 확장하지 않았다.
