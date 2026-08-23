# 68 — Real Integration Conflict Resolution

## 1. Final result

- M4 T2 collision region = **MID, DISTAL**
- N3 T3 collision region = **ROOT, MID, DISTAL**
- SELECTED TERMINAL SOLUTION = **NONE / HOLD**
- OLD TERMINAL PENETRATION = **0.283393028 mm³**
- NEW TERMINAL PENETRATION = **0.283393028 mm³**
- NEW TERMINAL CLEARANCE = **0.000000 mm**
- I2/I3 ↔ I4 OLD CLEARANCE = **0.104805 mm**
- NEW CLEARANCE = **0.444805 mm**
- RELIEF REMOVAL VOLUME = **6.299520 mm³**
- MINIMUM WALL = **1.200 mm global / 1.280 mm relieved corner**
- M4/N3 REGRESSION = **PASS**
- I2/I3/I4 REGRESSION = **PASS**
- EXTERIOR = **PRESERVED**

## 2. Scope / freeze

HW504, joystick, N1/N2↔joystick interaction 및 N1/N2 wiring은 로드하거나 평가하지 않았다. Cap center/orientation, switch position/orientation, travel axis, guide, retention, contact, reaction support와 hard stop은 변경하지 않았다. Terminal bend는 후보 검증만 했고 채택하지 않았다. 실제 local production edit는 I4 non-functional outer-corner relief 한 곳뿐이다.

## 3. ROOT / MID / DISTAL exact breakdown

분류는 housing rear 기준 ROOT(-0.30~+0.40 mm), MID(+0.40~+1.10 mm), DISTAL(+1.10~+2.00 mm external lead)다.

| terminal | region | penetration mm³ |
|---|---|---:|
| M4_T2 | ROOT | 0.000000000 |
| M4_T2 | MID | 0.134784301 |
| M4_T2 | DISTAL | 0.148608727 |
| N3_T3 | ROOT | 0.011038108 |
| N3_T3 | MID | 0.252796721 |
| N3_T3 | DISTAL | 0.019558199 |

M4 participating region은 **MID, DISTAL**, N3는 **ROOT, MID, DISTAL**다.

## 4. Terminal solution

Electrical pair topology는 CAD에서 추측하지 않았다. **ELECTRICAL REDUNDANCY = CONDITIONAL**이며 trim은 사용하지 않았다.

| candidate | terminal pen mm³ | clearance mm | future-wire pen mm³ | geometry |
|---|---:|---:|---:|---|
| A1_M4_T2_DISTAL_BEND | 0.251519632 | 0.000000 | 0.007596941 | FAIL |
| A2_N3_T3_DISTAL_BEND | 0.303443457 | 0.000000 | 0.023409546 | FAIL |
| B1_OPPOSITE_V_DEPARTURE | 0.067067520 | 0.000000 | 0.000000000 | FAIL |
| B2_OPPOSITE_OUTSIDE_U_DEPARTURE | 0.251643331 | 0.000000 | 0.000000000 | FAIL |

선택안은 **NONE / HOLD**다. 모든 A/B 후보에서 terminal root, ITS housing, switch position/clocking 변화는 0이었다. 그러나 ROOT 고정 조건에서 terminal pair 0.50 mm clearance와 carrier 무간섭을 동시에 달성하지 못했다. Candidate C trim은 continuity 미확인으로 검토/채택하지 않았다.

## 5. I4-only non-functional carrier relief

I4의 최접 외곽 코너만 U방향 **0.320 mm** relief했다. I2/I3 carrier는 변경하지 않았다.

| protected region | removed-material penetration mm³ | gate |
|---|---:|---|
| guide_retention_hard_stop | 0.000000000 | PASS |
| switch_locating | 0.000000000 | PASS |
| rear_reaction_support | 0.000000000 | PASS |
| terminal_bay | 0.000000000 | PASS |
| cap_service | 0.000000000 | PASS |
| switch_service | 0.000000000 | PASS |
| wire_exit | 0.000000000 | PASS |
| wire_envelope | 0.000000000 | PASS |

New clearance는 **0.444805 mm**, removal은 **6.299520 mm³**다. Global critical wall 1.20 mm와 local relieved wall 1.280 mm를 모두 만족한다.

## 6. Regression

- M4/N3 four states: REST/REST, FULL/REST, REST/FULL, FULL/FULL
- M4/N3 minimum cap gap: **3.132654 mm** (approved ≥3.132654 mm)
- reaction support / hard stop / service: **UNCHANGED / PASS**
- I2/I3/I4: each REST/MID/FULL foreign-carrier penetration 0
- I2/I3 combined FULL penetration: **0.000000000 mm³**
- I3 REST ↔ I4 FULL cap clearance: **3.248773 mm** (approved ≥3.248773 mm)
- Other approved button inputs: SHA-256 unchanged

## 7. Required renders

1. `renders/real_integration_conflict_resolution/01_m4_t2_n3_t3_current_collision.png`
2. `renders/real_integration_conflict_resolution/02_terminal_root_mid_distal_classification.png`
3. `renders/real_integration_conflict_resolution/03_selected_terminal_solution_before_after.png`
4. `renders/real_integration_conflict_resolution/04_terminal_future_wire_departure.png`
5. `renders/real_integration_conflict_resolution/05_m4_n3_full_regression.png`
6. `renders/real_integration_conflict_resolution/06_i2_i3_i4_current_interface.png`
7. `renders/real_integration_conflict_resolution/07_carrier_relief_before_after.png`
8. `renders/real_integration_conflict_resolution/08_final_carrier_clearance.png`
9. `renders/real_integration_conflict_resolution/09_i2_i3_i4_transparent_regression.png`

## 8. Final verdict

- M4/N3 TERMINAL INTEGRATION = **HOLD**
- I2/I3 ↔ I4 MANUFACTURING CLEARANCE = **PASS**
- ALL 8 BUTTON MECHANICAL BASELINES = **PRESERVED**
- HW504 / ACTUAL JOYSTICK = **NOT EVALUATED**
- SZH-EK056 = **NEEDS PHYSICAL MEASUREMENT**

STOP — wiring production geometry, fastening and electronics placement were not started.
