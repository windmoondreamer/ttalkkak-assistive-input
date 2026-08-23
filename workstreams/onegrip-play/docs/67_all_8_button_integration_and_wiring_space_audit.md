# 67 — All 8 Button Integration and Wiring-Space Audit

## 1. 결론

8개 승인 버튼과 5개 carrier service group을 **서로 union하지 않은 원래 생산 의도 좌표**에서 감사했다. 생산 형상 수정, carrier cut, wire solid, full shell boolean, assembly STEP/STL export는 수행하지 않았다.

- ALL 8 MECHANICAL BASELINES = **PRESERVED**
- HW504-A / HW504-B = **REFERENCE / PLACEHOLDER GEOMETRY**
- HW504-DEPENDENT RESULTS = **PROVISIONAL — ACTUAL JOYSTICK REQUIRED**
- SZH-EK056 EXACT GEOMETRY = **NEEDS PHYSICAL MEASUREMENT**
- CARRIER-TO-CARRIER INTEGRATION = **PASS**
- CARRIER-CARRIER PENETRATION = **0.000000000 mm³ max**
- MIN INTER-CARRIER CLEARANCE = **0.104805 mm**
- SWITCH / TERMINAL CROSS-COLLISION = **HOLD — M4 T2 ↔ N3 T3; HW504 findings provisional**
- ALL-8 MOTION ENVELOPE = **PASS**
- ALL-8 FULL PENETRATION = **0.000000000 mm³**
- SERVICEABILITY = **PASS**
- TERMINAL ACCESS = **HOLD — M4/N3 terminal interface; N1/N2 vs HW504 provisional**
- WIRING SPACE = **PROVISIONAL — ACTUAL JOYSTICK REQUIRED**
- RECOMMENDED ELECTRICAL TOPOLOGY = **8 signals + common GND**
- RECOMMENDED GROUND STRATEGY = **2-button carrier-local daisy-chain + five service-group returns**
- RECOMMENDED WIRING TRUNK = **split JaD/JfD half-trunks**
- FASTENING SPACE = **TIGHT**
- EXTERIOR = **PRESERVED**
- PEAK PYTHON RSS = **534.7 MB**
- OVERALL = **HOLD — THIS INTEGRATION INTERFACE NEEDS REDESIGN (M4 T2 ↔ N3 T3)**

## 2. Freeze / 방법

docs/62~66의 cap, switch, guide, hard stop, rear support, functional carrier geometry 및 exterior를 read-only 입력으로 사용했다. 5개 carrier, 8개 cap STEP와 승인 JSON/MD의 SHA-256를 작업 전후 비교했다. Exact 계산은 단일 Python process와 단일 OCC operation 흐름으로 실행했다. AABB가 분리된 쌍은 penetration이 불가능하므로 보수적 분리 하한으로 screen했고, 겹치거나 가까운 쌍만 serial OCCT exact를 실행했다.

HW504-A/B는 최종 구매품이 아니라 **REFERENCE / PLACEHOLDER GEOMETRY**다. 따라서 N2 body/T1/T2↔HW504-A, N1/N2 wiring↔HW504 및 모든 carrier↔HW504 clearance는 **PROVISIONAL — ACTUAL JOYSTICK REQUIRED**로 재분류했다. 이 값들은 Finger/N1/N2 production geometry 수정 근거로 사용하지 않는다.

HW504와 무관한 승인 회귀 reference(I2/I3 FULL cap gap 2.14 mm 이상, M4/N3 minimum cap gap 3.132654 mm, I4↔I3 3.248773 mm, M3↔M4 4.847042 mm, critical wall 1.20 mm 이상)는 입력 STEP/JSON 해시 무변경과 production geometry edit 0으로 보존됐다.

## 3. Carrier-to-carrier exact 10쌍

| pair | exact distance mm | penetration mm³ | gate |
|---|---:|---:|---|
| N1_N2<->I2_I3 | 7.127319 | 0.000000000 | PASS |
| N1_N2<->M4_N3 | 31.010128 | 0.000000000 | PASS |
| N1_N2<->I4 | 8.845497 | 0.000000000 | PASS |
| N1_N2<->M3 | 30.533602 | 0.000000000 | PASS |
| I2_I3<->M4_N3 | 12.373789 | 0.000000000 | PASS |
| I2_I3<->I4 | 0.104805 | 0.000000000 | PASS |
| I2_I3<->M3 | 12.216827 | 0.000000000 | PASS |
| M4_N3<->I4 | 12.121880 | 0.000000000 | PASS |
| M4_N3<->M3 | 0.400000 | 0.000000000 | PASS |
| I4<->M3 | 12.385517 | 0.000000000 | PASS |

최접 interface는 **I2_I3<->I4**, exact distance **0.104805 mm**다. Carrier penetration이 발생하면 `THIS INTEGRATION INTERFACE FAILED`로 판정하도록 했으며, 이번 carrier 결과는 **PASS**다.

## 4. Switch / terminal cross audit

- total checked rows: **1078**
- serial OCCT exact rows: **73**
- conservative AABB-separated rows: **1005**
- failed cross interfaces: **4**

| interface | penetration mm³ | method | production classification |
|---|---:|---|---|
| N2 body<->HW504_A | 0.015188570 | OCCT_EXACT | PROVISIONAL — ACTUAL JOYSTICK REQUIRED |
| N2.T1<->HW504_A | 0.031265583 | OCCT_EXACT | PROVISIONAL — ACTUAL JOYSTICK REQUIRED |
| N2.T2<->HW504_A | 0.021290636 | OCCT_EXACT | PROVISIONAL — ACTUAL JOYSTICK REQUIRED |
| M4.T2<->N3.T3 | 0.283393028 | OCCT_EXACT | HW504-INDEPENDENT / VALID INTEGRATION FINDING |

HW504와 무관한 유효 integration failure는 **M4 T2 ↔ N3 T3 = 0.283393028 mm³** 한 건이다. 이는 `THIS INTEGRATION INTERFACE NEEDS REDESIGN`이지만 8-button exterior 불가 판정은 아니다. 나머지 HW504 관련 세 건은 실제 SZH-EK056 측정 전 production failure로 세지 않는다. N1 terminal 4개와 N2 T1/T3 active + T2/T4 trimmed conditional 상태는 그대로이며 새 trim/bend는 없다.

## 5. Motion envelope

| state | FULL buttons | verdict | failed interface count |
|---|---|---|---:|
| ALL_REST | - | PASS | 0 |
| N1_FULL | N1 | PASS | 0 |
| N2_FULL | N2 | PASS | 0 |
| I2_FULL | I2 | PASS | 0 |
| I3_FULL | I3 | PASS | 0 |
| I4_FULL | I4 | PASS | 0 |
| M3_FULL | M3 | PASS | 0 |
| M4_FULL | M4 | PASS | 0 |
| N3_FULL | N3 | PASS | 0 |
| I2_I3_FULL | I2, I3 | PASS | 0 |
| M4_N3_FULL | M4, N3 | PASS | 0 |
| I4_I3_FULL | I3, I4 | PASS | 0 |
| M3_M4_FULL | M3, M4 | PASS | 0 |
| N1_N2_FULL | N1, N2 | PASS | 0 |
| ALL_8_FULL | I2, I3, I4, M3, M4, N1, N2, N3 | PASS | 0 |

각 FULL은 0.350 mm다. Own cap-guide/actuator/hard-stop contact는 intentional이고 docs/62~66 exact baseline을 그대로 상속한다. 본 감사에서는 cap ↔ foreign carrier/switch 및 cap ↔ cap을 분리해 unintended penetration만 판정했다.

## 6. Service path

| service group | direction | translation mm | rotation deg | verdict |
|---|---|---:|---:|---|
| N1_N2 | [-1.0, 0.0, 0.0] | 15.0 | 0.0 | PASS |
| I2_I3 | [-1.0, 0.0, 0.0] | 15.0 | 0.0 | PASS |
| M4_N3 | [1.0, 0.0, 0.0] | 15.0 | 0.0 | PASS |
| I4 | [1.0, 0.0, 0.0] | 15.0 | 0.0 | PASS |
| M3 | [-1.0, 0.0, 0.0] | 15.0 | 0.0 | PASS |

기본 순서는 `shell open → 해당 carrier group release → 해당 group switch service`다. I4/M3는 각 standalone carrier를 먼저 빼고 ITS를 서비스한다. 다른 carrier를 먼저 제거해야 하는 종속성은 만들지 않는 것을 기준으로 했다.

## 7. Wiring-space / terminals

| button | usable terminals | trimmed | solder access | bend/tool keepout |
|---|---|---|---|---|
| N1 | T1, T2, T3, T4 | - | PROVISIONAL — ACTUAL JOYSTICK REQUIRED | PROVISIONAL — ACTUAL JOYSTICK REQUIRED |
| N2 | T1, T3 | T2, T4 | PROVISIONAL — ACTUAL JOYSTICK REQUIRED | PROVISIONAL — ACTUAL JOYSTICK REQUIRED |
| I2 | T1, T2, T3, T4 | - | TIGHT | TIGHT |
| I3 | T1, T2, T3, T4 | - | TIGHT | TIGHT |
| I4 | T1, T2, T3, T4 | - | TIGHT | TIGHT |
| M3 | T1, T2, T3, T4 | - | TIGHT | TIGHT |
| M4 | T1, T2, T3, T4 | - | TIGHT | TIGHT |
| N3 | T1, T2, T3, T4 | - | TIGHT | TIGHT |

전기 baseline은 GPIO가 충분할 때 **8 independent signals + common GND**를 추천한다. 물리 harness는 shared two-button carrier 내부에서만 local ground daisy-chain하고, I4/M3는 독립 return을 유지한 뒤 5개 service-group return을 후단에서 합치는 안을 추천한다. 8개 전체 ground chain은 service dependency 때문에 추천하지 않는다.

Wire OD **1.0~1.3 mm**는 공간 seed일 뿐이며 최종 AWG가 아니다. 기존 HW504 placeholder에 대한 N1/N2 BLOCKED 판정은 **PROVISIONAL — ACTUAL JOYSTICK REQUIRED**다. Candidate 2 **split JaD/JfD half-trunks**를 개념 기준안으로 유지하지만, 실제 SZH-EK056 측정 전 production wiring clearance는 확정하지 않는다. Carrier cut과 wire solid는 없다.

## 8. SZH-EK056 actual-part measurement checklist

로컬 workspace에는 SZH-EK056 전용 controlled drawing, exact STEP 또는 실물 측정 registry가 없다. docs/55의 `34.5 × 26 × 38 mm` 판매처 envelope와 유사 모듈 문서의 `34.0 × 26.3 × 1.6 mm` PCB/Ø3 mm 홀은 참고용 nominal일 뿐 생산 CAD datum이 아니다. 판정은 **NEEDS PHYSICAL MEASUREMENT**다.

먼저 PCB top plane, 두 직교 PCB edge, neutral shaft axis를 측정 datum으로 지정하고 다음을 기록한다.

| # | measurement | method / datum | record required |
|---:|---|---|---|
| 1 | PCB X / Y / Z | caliper; PCB edge-to-edge and board thickness | length, width, thickness; max/min across samples |
| 2 | mounting-hole X/Y pitch | hole-center coordinates from selected PCB corner datum | all four X/Y coordinates and opposite/diagonal pitches |
| 3 | mounting-hole diameter | pin gauges or caliper; distinguish plating/countersink | diameter of each hole |
| 4 | joystick center relative to PCB | neutral shaft axis to both PCB edges and hole pattern | center X/Y and concentricity/offset |
| 5 | X potentiometer envelope | axis-aligned bbox from PCB datums | min/max X/Y/Z, housing center, tabs/lead protrusions |
| 6 | Y potentiometer envelope | axis-aligned bbox from PCB datums | min/max X/Y/Z, housing center, tabs/lead protrusions |
| 7 | bottom push-switch envelope | bottom-view bbox and shaft-axis relation | min/max X/Y/Z, body/lead protrusion, push travel |
| 8 | shaft / pivot height | PCB top plane to pivot center and neutral shaft endpoints | pivot Z, exposed shaft length, cap interface diameter/shape |
| 9 | connector envelope | PCB datum bbox | header X/Y/Z, pin pitch, orientation, mating-plug projection |
| 10 | maximum moving envelope | sweep at max ±X, ±Y, diagonal tilt and axial push | union bbox/radial envelope including shaft and intended knob |

권장 기록에는 측정 sample 수, 보드 revision/실크, 판매처/lot, 정면·측면·하부 사진과 측정 공구 분해능도 포함한다. Moving envelope는 cap/knob을 포함한 최대 X/Y tilt와 axial push 전후 모두 측정한다.

## 9. Fastening-space audit

| group | owner | shell-side area | access | reason |
|---|---|---|---|---|
| N1_N2 | JfD | TIGHT | TIGHT | frozen N1/N2 service corridor remains tight; the HW504-adjacency portion is PROVISIONAL — ACTUAL JOYSTICK REQUIRED |
| I2_I3 | JfD | AVAILABLE | AVAILABLE | shared carrier has broad shell-side rail area, subject to future boss verification |
| M4_N3 | JaD | AVAILABLE | AVAILABLE | shared carrier has broad shell-side rail area, subject to future boss verification |
| I4 | JaD | AVAILABLE | AVAILABLE | standalone carrier has a direct shell-open approach, subject to future boss verification |
| M3 | JfD | AVAILABLE | AVAILABLE | standalone carrier has a direct shell-open approach, subject to future boss verification |

Fastener, boss, captured nut, heat-set insert는 모델링하지 않았다. 이 결과는 shell-side 면적/접근 방향의 다음 단계 가능성 감사이며, 전체 판정은 **TIGHT**다.

## 10. Required renders

1. `renders/all_8_button_integration_wiring_space_audit/01_all_8_caps_exterior_overview.png`
2. `renders/all_8_button_integration_wiring_space_audit/02_transparent_all_8_internal.png`
3. `renders/all_8_button_integration_wiring_space_audit/03_isolated_color_coded_carrier_groups.png`
4. `renders/all_8_button_integration_wiring_space_audit/04_carrier_closest_interfaces.png`
5. `renders/all_8_button_integration_wiring_space_audit/05_switches_and_terminals_only.png`
6. `renders/all_8_button_integration_wiring_space_audit/06_thumb_hw504_vs_finger_internals.png`
7. `renders/all_8_button_integration_wiring_space_audit/07_service_removal_directions.png`
8. `renders/all_8_button_integration_wiring_space_audit/08_wire_departure_arrows.png`
9. `renders/all_8_button_integration_wiring_space_audit/09_candidate_wiring_trunks.png`
10. `renders/all_8_button_integration_wiring_space_audit/10_all_8_full_envelope.png`
11. `renders/all_8_button_integration_wiring_space_audit/11_n1_n2_terminal_hw504_conditionals.png`

Render 06/09/11의 HW504 형상과 수치는 모두 placeholder reference visualization이다.

## 11. STOP

production assembly, wire solid, fastening feature, MCU/PCB, full shell, STL/print plate 단계로 자동 확장하지 않는다. 사용자 검토를 받고 STOP한다.
