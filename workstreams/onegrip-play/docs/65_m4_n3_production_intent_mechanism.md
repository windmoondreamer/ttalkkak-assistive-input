# 65 — M4/N3 PRODUCTION-INTENT BUTTON MECHANISMS

## 결론

M4/N3 exterior feasibility는 재평가하지 않았다. 승인된 center, cap exterior/orientation, switch position과 의도된 shell 대비 4°를 그대로 유지하고 기존 shared carrier에 내부 기능만 추가했다.

초기 9.3 mm unrelieved guide envelope는 M4 **0.533956 mm³**, N3 **1.576808 mm³**의 local-shell penetration이 있었다.

**THIS INTERNAL CANDIDATE FAILED**

shell 또는 exterior를 바꾸지 않고 guide의 shell-facing 비기능 corner만 exact local relief했다. 최종 guide-shell penetration과 relief-to-shoulder motion penetration은 모두 0이다.

## 1. Current exact local audit

| item | M4 | N3 |
|---|---:|---:|
| cap center | `[7.379332315763718, -13.575227245499876, -11.115547003937289]` | `[17.48689737236422, -6.664472046607768, -11.125]` |
| cap ↔ switch plane | 0.000000° | 0.000000° |
| cap ↔ local shell plane | 4.000000° | 4.000000° |
| actuator lateral offset | 0.000000000 mm | 0.000000000 mm |
| current rear reaction gap | 0.110000 mm | 0.110000 mm |
| body ↔ local shell | 1.327785 mm | 1.286709 mm |
| full 9.3 mm guide envelope ↔ shell pen | 1.970305 mm³ | 3.269239 mm³ |

4°는 의도된 internal-axis tilt이며 cap을 shell과 평행하게 재정렬하지 않았다. current shared carrier는 local shell과 penetration 0, M3 carrier와 0.400 mm, I4 carrier와 12.121880 mm 떨어져 있다.

## 2. Production-intent architecture

각 버튼의 독립 load path:

`finger → frozen exterior cap → Ø3.0 central contact → ITS actuator/body → terminal-window rear reaction frame → shared carrier/shell`

- positive retention: 6.5 mm square shoulder / 6.8 mm cavity
- guide: Ø4.5 tail / Ø4.8 bore, radial clearance 0.15 mm
- hard stop: carrier rear structural plane at 0.350 mm
- return: ITS internal return only; 별도 spring 없음
- body locating: 기존 6.4 mm pocket datum과 switch position 유지
- cap service: M4 `−cap-U`, N3 `+cap-U`; 두 경로 모두 이웃 cap 반대 방향이며 carrier/other cap/guide/body penetration 0
- switch service: 기존 switch-frame open side를 유지하고 other cap/guide/body penetration 0
- terminal service: 4.0 × 3.2 mm central wire window
- shell curvature response: 각 guide의 shell-facing corner만 local relief

### Rear reaction support

| item | M4 | N3 |
|---|---:|---:|
| contact area | 24.907 mm² | 24.907 mm² |
| connected contact patch | 1 | 1 |
| contact span U × V | 6.180 × 6.120 mm | 6.180 × 6.120 mm |
| diagonal span | 8.698 mm | 8.698 mm |
| minimum rail | 1.200 mm | 1.200 mm |

0.110 mm rear gap은 broad plastic-body frame으로 닫힌다. terminal root나 중앙 wire corridor를 반력면으로 사용하지 않는다.

## 3. Independent motion

### M4

| travel mm | cap-guide pen mm³ | cap-shell pen mm³ | contact gap mm | hard-stop residual mm |
|---:|---:|---:|---:|---:|
| 0.000 | 0.000000000 | 0.000000000 | 0.000000000 | 0.350 |
| 0.175 | 0.000000000 | 0.000000000 | 0.000000000 | 0.175 |
| 0.350 | 0.000000000 | 0.000000000 | 0.000000000 | 0.000 |

### N3

| travel mm | cap-guide pen mm³ | cap-shell pen mm³ | contact gap mm | hard-stop residual mm |
|---:|---:|---:|---:|---:|
| 0.000 | 0.000000000 | 0.000000000 | 0.000000000 | 0.350 |
| 0.175 | 0.000000000 | 0.000000000 | 0.000000000 | 0.175 |
| 0.350 | 0.000000000 | 0.000000000 | 0.000000000 | 0.000 |

REST/MID/FULL에서 cap-guide, cap-shell, cap-base-carrier, cap-actuator, other-guide/body unintended penetration은 0이고 contact gap은 0이다. hard-stop residual은 0.350 / 0.175 / 0.000 mm다.

### Combined states

| M4 travel mm | N3 travel mm | maximum cross pen mm³ | cap-cap gap mm | uncommanded M4/N3 mm |
|---:|---:|---:|---:|---:|
| 0.000 | 0.000 | 0.000000000 | 3.276888 | 0.000 / 0.000 |
| 0.175 | 0.000 | 0.000000000 | 3.252054 | 0.000 / 0.000 |
| 0.350 | 0.000 | 0.000000000 | 3.236040 | 0.000 / 0.000 |
| 0.000 | 0.175 | 0.000000000 | 3.238400 | 0.000 / 0.000 |
| 0.000 | 0.350 | 0.000000000 | 3.209006 | 0.000 / 0.000 |
| 0.350 | 0.350 | 0.000000000 | 3.132654 | 0.000 / 0.000 |
| 0.175 | 0.175 | 0.000000000 | 3.204771 | 0.000 / 0.000 |

## 4. Terminal map and service

T1/T2/T3/T4를 각각 conservative terminal + radial service 0.12 mm envelope로 검사했다. 8개 모두 무절단 유지한다.

### M4

| terminal | carrier mm | shell mm | other switch mm | other guide mm | 처리 |
|---|---:|---:|---:|---:|---|
| T1 | 0.000000 | 5.006141 | 3.119144 | 3.683295 | 유지 |
| T2 | 0.000000 | 4.968220 | 0.545958 | 3.052161 | 유지 |
| T3 | 0.000000 | 4.353551 | 7.946699 | 9.324299 | 유지 |
| T4 | 0.000000 | 4.525815 | 7.329591 | 7.794664 | 유지 |

### N3

| terminal | carrier mm | shell mm | other switch mm | other guide mm | 처리 |
|---|---:|---:|---:|---:|---|
| T1 | 0.000000 | 4.165658 | 7.430607 | 8.547592 | 유지 |
| T2 | 0.000000 | 3.755845 | 8.041928 | 9.218911 | 유지 |
| T3 | 0.000000 | 5.353496 | 0.832584 | 3.662485 | 유지 |
| T4 | 0.000000 | 5.466489 | 3.183548 | 3.762170 | 유지 |

각 terminal의 carrier/shell/other-button/neighbor-carrier penetration은 0이다. cap service, switch service, wire exit, wire envelope도 각 버튼별 독립 PASS다.

## 5. Shared carrier / local shell / FDM

- approved current carrier removed volume: **0.000000000 mm³**
- final solid count: **1**
- floating body: **False**
- final carrier ↔ local shell penetration: **0.000000000 mm³**
- final carrier ↔ M3 carrier: **0.400000 mm**, penetration 0.000000000 mm³
- critical functional wall: **1.200 mm** ≥ 1.20 mm
- preferred 1.60 mm는 base wall/cross-rail에 유지되며 guide annulus/reaction side rail은 functional minimum gate 1.20 mm를 만족한다.
- tiny snap / thin hook / tangent-only support / floating body: 없음

## 6. Frozen regression

- frozen files SHA-256 guard: **PASS**
- N1/N2 approved verdicts: **PASS**
- I2/I3 approved verdicts: **PASS**
- N2 carrier ↔ HW504-A: **0.304180346 mm** ≥ 0.304180 mm
- N2 carrier ↔ HW504-B: **1.360983710 mm** (6자리 반올림 **1.360984 mm**, 승인 baseline 보존)
- N2 T1/T3 ↔ HW504-B: **2.119093040 mm** ≥ 2.119093 mm
- I2/I3 rear reaction: **24.906933 / 24.906933 mm²**
- I2/I3 minimum combined cap gap: **2.141672 mm** ≥ 2.14 mm
- M4/N3 final carrier ↔ frozen N1/N2, I2/I3 penetration: **0 mm³**

## 7. Outputs

- `renders\m4_n3_production_intent_mechanism\01_m4_n3_current_structure.png`
- `renders\m4_n3_production_intent_mechanism\02_m4_n3_exploded.png`
- `renders\m4_n3_production_intent_mechanism\03_m4_n3_terminal_map.png`
- `renders\m4_n3_production_intent_mechanism\04_m4_rest_full_section.png`
- `renders\m4_n3_production_intent_mechanism\05_n3_rest_full_section.png`
- `renders\m4_n3_production_intent_mechanism\06_rear_reaction_contact.png`
- `renders\m4_n3_production_intent_mechanism\07_both_buttons_full.png`
- `renders\m4_n3_production_intent_mechanism\08_shared_carrier_transparent.png`
- `renders\m4_n3_production_intent_mechanism\09_shell_curvature_guide_closeup.png`
- `renders\m4_n3_production_intent_mechanism\10_frozen_regression.png`

- `build123d_workbench\out\m4_n3_production_intent_mechanism\m4_n3_production_intent_mechanism.json` — lightweight exact JSON
- `build123d_workbench\out\m4_n3_production_intent_mechanism\M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step` — M4/N3 local shared carrier only
- `build123d_workbench\out\m4_n3_production_intent_mechanism\M4_PRODUCTION_INTENT_CAP_LOCAL.step` / `build123d_workbench\out\m4_n3_production_intent_mechanism\N3_PRODUCTION_INTENT_CAP_LOCAL.step` — local cap components only
- full shell / full assembly / STL / print plate / multiprocessing: **생성하지 않음**

## 8. FINAL / STOP

- M4 ARCHITECTURE = **ACCEPT**
- N3 ARCHITECTURE = **ACCEPT**
- M4 MOTION = **PASS**
- N3 MOTION = **PASS**
- SHARED CARRIER = **PASS**
- M4 TERMINALS = **PASS**
- N3 TERMINALS = **PASS**
- N1/N2 FROZEN BASELINE = **PRESERVED**
- I2/I3 FROZEN BASELINE = **PRESERVED**
- EXTERIOR = **PRESERVED**

M4/N3에서 STOP한다. I4/M3로 자동 확장하지 않았다.
