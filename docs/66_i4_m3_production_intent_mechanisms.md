# 66 — I4/M3 PRODUCTION-INTENT MECHANISMS

## 결론

I4와 M3를 서로 독립적인 기존 carrier로 유지한 채 production-intent mechanism을 완성했다. 두 버튼의 exterior center/cap/orientation, switch position 및 0° cap-switch-shell mapping은 변경하지 않았다.

I4의 unrelieved guide는 local shell에 **0.164960 mm³** 침범했다.

**THIS INTERNAL CANDIDATE FAILED**

I4 guide의 shell-facing 비기능 corner만 local relief해 최종 penetration을 0으로 만들었다. M3 straight guide는 초기부터 shell penetration 0이므로 relief 없이 유지했다.

## I4

| field | result |
|---|---|
| ARCHITECTURE | ACCEPT |
| CAP ↔ SWITCH ALIGNMENT | 0.000000° |
| CAP ↔ SHELL ALIGNMENT | 0.000000° |
| ACTUATION TYPE | DIRECT / central offset 0.000000000 mm |
| REAR SUPPORT TYPE | terminal-window flat reaction frame |
| REACTION AREA | 24.906933 mm² / 1 connected patch |
| CONTACT SPAN | 6.180 × 6.120 mm / diagonal 8.698 mm |
| TERMINAL MIN SHELL CLEARANCE | 4.779411 mm |
| MIN WALL | 1.200 mm |
| MOTION | PASS |
| HARD STOP | residual 0.350 / 0.175 / 0.000 mm |
| RETURN | ITS internal return only |
| SERVICE | PASS — cap independently exits +cap-U; ITS exits current open channel after removing its own standalone carrier from opened shell; other cap removal not required |

### Motion

| travel mm | cap-guide pen mm³ | cap-shell pen mm³ | contact gap mm | hard-stop residual mm |
|---:|---:|---:|---:|---:|
| 0.000 | 0.000000000 | 0.000000000 | 0.000000000 | 0.350 |
| 0.175 | 0.000000000 | 0.000000000 | 0.000000000 | 0.175 |
| 0.350 | 0.000000000 | 0.000000000 | 0.000000000 | 0.000 |

Nearest frozen cap at FULL: **I3**, clearance **3.248773 mm**. Frozen cap/body/carrier penetration is 0 in REST/MID/FULL.

### Terminals

| terminal | own carrier mm | local shell mm | nearest frozen carrier mm | treatment |
|---|---:|---:|---:|---|
| T1 | 0.000000 | 5.801556 | 8.017611 | 유지 |
| T2 | 0.000000 | 4.779411 | 8.018992 | 유지 |
| T3 | 0.000000 | 5.359844 | 0.955668 | 유지 |
| T4 | 0.000000 | 5.791031 | 0.951042 | 유지 |

T1/T2/T3/T4는 conservative 0.12 mm service envelope로 개별 검사했으며 전부 무절단 유지한다.


## M3

| field | result |
|---|---|
| ARCHITECTURE | ACCEPT |
| CAP ↔ SWITCH ALIGNMENT | 0.000000° |
| CAP ↔ SHELL ALIGNMENT | 0.000000° |
| ACTUATION TYPE | DIRECT / central offset 0.000000000 mm |
| REAR SUPPORT TYPE | terminal-window flat reaction frame |
| REACTION AREA | 24.906933 mm² / 1 connected patch |
| CONTACT SPAN | 6.180 × 6.120 mm / diagonal 8.698 mm |
| TERMINAL MIN SHELL CLEARANCE | 5.055321 mm |
| MIN WALL | 1.200 mm |
| MOTION | PASS |
| HARD STOP | residual 0.350 / 0.175 / 0.000 mm |
| RETURN | ITS internal return only |
| SERVICE | PASS — cap independently exits -cap-U; ITS exits current open channel after removing its own standalone carrier from opened shell; other cap removal not required |

### Motion

| travel mm | cap-guide pen mm³ | cap-shell pen mm³ | contact gap mm | hard-stop residual mm |
|---:|---:|---:|---:|---:|
| 0.000 | 0.000000000 | 0.000000000 | 0.000000000 | 0.350 |
| 0.175 | 0.000000000 | 0.000000000 | 0.000000000 | 0.175 |
| 0.350 | 0.000000000 | 0.000000000 | 0.000000000 | 0.000 |

Nearest frozen cap at FULL: **M4**, clearance **4.847042 mm**. Frozen cap/body/carrier penetration is 0 in REST/MID/FULL.

### Terminals

| terminal | own carrier mm | local shell mm | nearest frozen carrier mm | treatment |
|---|---:|---:|---:|---|
| T1 | 0.000000 | 5.102123 | 8.100058 | 유지 |
| T2 | 0.000000 | 5.194797 | 8.108160 | 유지 |
| T3 | 0.000000 | 5.126915 | 1.144644 | 유지 |
| T4 | 0.000000 | 5.055321 | 1.193175 | 유지 |

T1/T2/T3/T4는 conservative 0.12 mm service envelope로 개별 검사했으며 전부 무절단 유지한다.


## I4 + M3 simultaneous FULL

- I4 + M3 FULL PENETRATION = **0.000000000 mm³**
- I4 NEAREST CAP CLEARANCE = **3.248773 mm** (I3)
- M3 NEAREST CAP CLEARANCE = **4.847042 mm** (M4)

두 carrier는 새 shared carrier로 묶지 않았다.

## Previous 6-button frozen regression

- exact file hash: **PASS**
- STEP volume / solid count / bbox / center fingerprint: **PASS**
- cap datum center/axis transform change: **0**
- N2 HW504-A / B / T1-T3: **0.304180346 / 1.360983710 / 2.119093040 mm**
- I2/I3 FULL penetration / cap gap: **0.000000000 mm³ / 2.141672 mm**
- M4/N3 tested penetration / FULL cap gap: **0.000000000 mm³ / 3.132654 mm**
- PREVIOUS 6 BUTTON BASELINES = **PRESERVED**

## Outputs

- `renders\i4_m3_production_intent_mechanisms\01_current_i4_internal.png`
- `renders\i4_m3_production_intent_mechanisms\02_i4_exploded.png`
- `renders\i4_m3_production_intent_mechanisms\03_i4_rest_full_section.png`
- `renders\i4_m3_production_intent_mechanisms\04_i4_rear_support_terminal_map.png`
- `renders\i4_m3_production_intent_mechanisms\05_current_m3_internal.png`
- `renders\i4_m3_production_intent_mechanisms\06_m3_exploded.png`
- `renders\i4_m3_production_intent_mechanisms\07_m3_rest_full_section.png`
- `renders\i4_m3_production_intent_mechanisms\08_m3_rear_support_terminal_map.png`
- `renders\i4_m3_production_intent_mechanisms\09_i4_full_m3_full.png`
- `renders\i4_m3_production_intent_mechanisms\10_all_8_button_overview.png`
- `renders\i4_m3_production_intent_mechanisms\11_previous_6_frozen_regression.png`

- `build123d_workbench\out\i4_m3_production_intent_mechanisms\i4_m3_production_intent_mechanisms.json` — lightweight exact JSON
- `build123d_workbench\out\i4_m3_production_intent_mechanisms\I4_CARRIER_PRODUCTION_INTENT_LOCAL.step` / `build123d_workbench\out\i4_m3_production_intent_mechanisms\M3_CARRIER_PRODUCTION_INTENT_LOCAL.step` — two independent local carriers
- `build123d_workbench\out\i4_m3_production_intent_mechanisms\I4_CAP_PRODUCTION_INTENT_LOCAL.step` / `build123d_workbench\out\i4_m3_production_intent_mechanisms\M3_CAP_PRODUCTION_INTENT_LOCAL.step` — local cap components
- full shell boolean / full assembly STEP / STL / print plate / multiprocessing: **생성하지 않음**

## FINAL / STOP

- I4 ARCHITECTURE = **ACCEPT**
- I4 MOTION = **PASS**
- I4 TERMINALS = **PASS**
- I4 SERVICE = **PASS**
- M3 ARCHITECTURE = **ACCEPT**
- M3 MOTION = **PASS**
- M3 TERMINALS = **PASS**
- M3 SERVICE = **PASS**
- PREVIOUS 6 BUTTON BASELINES = **PRESERVED**
- EXTERIOR = **PRESERVED**

I4/M3에서 STOP한다. Wiring architecture, shell fastening, electronics placement로 진행하지 않았다.
