# 70 — Finger 8-button mechanical baseline checkpoint

## 1. Checkpoint status

이 문서는 docs/62~69 승인 결과를 하나의 **production-intent mechanical checkpoint**로 고정한다. 이번 단계에서 production geometry 수정은 없다.

- **FINGER 8-BUTTON MECHANICAL INTEGRATION = COMPLETE / HARD FROZEN**
- all 8 button mechanisms = **ACCEPT**
- carrier-to-carrier penetration = **0.000000000 mm³**
- I2/I3 ↔ I4 carrier clearance = **0.444805280 mm**
- ALL-8 FULL unintended penetration = **0.000000000 mm³**
- M4 T2 ↔ N3 T3 penetration = **0.000000000 mm³**
- serviceability = **PASS**
- exterior = **PRESERVED**
- actual Thumb joystick integration = **WAITING FOR SZH-EK056 REFERENCE / PHYSICAL MEASUREMENT**
- N1/N2 final wiring route = **WAITING FOR ACTUAL JOYSTICK ENVELOPE**

HW504-A/B는 `REFERENCE / PLACEHOLDER GEOMETRY`일 뿐이며 이 checkpoint의 production-hard datum이 아니다. HW504 관련 clearance는 Finger geometry 수정 근거로 사용하지 않는다.

## 2. Frozen eight-button list

| button | carrier/service group | mechanism result | terminal state |
|---|---|---|---|
| N1 | N1/N2 shared | ACCEPT / motion, hard stop, return, service PASS | T1/T2/T3/T4 unchanged; actual joystick fit provisional |
| N2 | N1/N2 shared | ACCEPT / short U-shaped rear cradle / motion PASS | T1/T3 active; T2/T4 unused trimmed |
| I2 | I2/I3 shared | ACCEPT / independent motion PASS | T1/T2/T3/T4 unchanged |
| I3 | I2/I3 shared | ACCEPT / independent motion PASS | T1/T2/T3/T4 unchanged |
| M4 | M4/N3 shared | ACCEPT / independent motion PASS | T2 unused, external trim; T1/T3/T4 active unchanged |
| N3 | M4/N3 shared | ACCEPT / independent motion PASS | T3 unused, external trim; T1/T2/T4 active unchanged |
| I4 | standalone | ACCEPT / motion PASS | T1/T2/T3/T4 unchanged |
| M3 | standalone | ACCEPT / motion PASS | T1/T2/T3/T4 unchanged |

Finger exterior center, cap exterior, cap orientation, travel axis, switch pose, direct actuation, guide, retention, rear reaction and hard-stop architecture는 전부 frozen이다.

## 3. Canonical carrier sources

아래 STEP이 이 checkpoint의 canonical carrier geometry다. 상위 단계의 이전 STEP은 설계 이력이며 현재 carrier source가 아니다.

| carrier | canonical STEP | SHA-256 | note |
|---|---|---|---|
| N1/N2 shared | `build123d_workbench/out/n1_production_intent_mechanism/N1_N2_SHARED_CARRIER_N1_LOCAL.step` | `2485e34f8716395459f1f7b10384fd73a33695472f9aae689cf321d583830756` | docs/62 N2 short-U cradle 위에 docs/63 N1 승인 영역을 통합한 최종본 |
| I2/I3 shared | `build123d_workbench/out/i2_i3_production_intent_mechanism/I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step` | `1aa49477668d26d0617814e89c6dc25eca0564b12f927d9481d93896513aa92b` | docs/64 승인본; 이후 형상 변경 없음 |
| M4/N3 shared | `build123d_workbench/out/m4_n3_production_intent_mechanism/M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step` | `246b309ac3550d4c0f9e82e77f298e884077ef83ed763c863658f3e589a9bca3` | docs/65 승인본; docs/69에서는 terminal leg만 별도 변경 |
| I4 standalone | `build123d_workbench/out/real_integration_conflict_resolution/I4_CARRIER_LOCAL_MANUFACTURING_RELIEF.step` | `90b0002f3c3d1bdd95fc157809891351ad8f9cd5bb8cdcdb9a260fa9c33dcfe7` | docs/66 carrier에 docs/68 I4-only 비기능 외곽 relief 적용 |
| M3 standalone | `build123d_workbench/out/i4_m3_production_intent_mechanisms/M3_CARRIER_PRODUCTION_INTENT_LOCAL.step` | `021363afb7b761456b436d6252d12a3d786003ea19bef6acb908651708d44786` | docs/66 승인본; 이후 형상 변경 없음 |

I2/I3/I4 carrier를 더 수정하지 않는다. M4/N3 carrier도 terminal 문제를 이유로 수정하지 않는다.

## 4. Approved mechanism and cap sources

| button | approval lineage | generator source | canonical cap STEP | cap SHA-256 |
|---|---|---|---|---|
| N2 | docs/60 architecture + docs/62 rear support | `build123d_workbench/n2_production_intent_mechanism.py`; `build123d_workbench/n2_rear_reaction_support_redesign.py` | `build123d_workbench/out/n2_production_intent_mechanism/N2_PRODUCTION_INTENT_CAP.step` | `7f88cf6abfb8bea9a792e81b1def3ffa4ee96e2259f628ecb18d20f76ca5238c` |
| N1 | docs/63 | `build123d_workbench/n1_production_intent_mechanism.py` | `build123d_workbench/out/n1_production_intent_mechanism/N1_PRODUCTION_INTENT_CAP_LOCAL.step` | `5f7574f90682f7e511067aaac1d514274bb75a0ffeaeaae7e8a45b3502e1d6a5` |
| I2 | docs/64 | `build123d_workbench/i2_i3_production_intent_mechanism.py` | `build123d_workbench/out/i2_i3_production_intent_mechanism/I2_PRODUCTION_INTENT_CAP_LOCAL.step` | `57f272b308af329655239f408c3d992f5c8f947476a4d794d93caab675bafbf9` |
| I3 | docs/64 | `build123d_workbench/i2_i3_production_intent_mechanism.py` | `build123d_workbench/out/i2_i3_production_intent_mechanism/I3_PRODUCTION_INTENT_CAP_LOCAL.step` | `8c478ffcdabb136400c12ff661c4fdc857de79d4849c678b3dd75c1a1f1abe38` |
| M4 | docs/65 + docs/69 terminal resolution | `build123d_workbench/m4_n3_production_intent_mechanism.py`; `build123d_workbench/m4_n3_terminal_redundancy_resolution.py` | `build123d_workbench/out/m4_n3_production_intent_mechanism/M4_PRODUCTION_INTENT_CAP_LOCAL.step` | `d5c7542eece5d83abebd282a211263584c11b422e58fbbc533eee062f786a9ff` |
| N3 | docs/65 + docs/69 terminal resolution | `build123d_workbench/m4_n3_production_intent_mechanism.py`; `build123d_workbench/m4_n3_terminal_redundancy_resolution.py` | `build123d_workbench/out/m4_n3_production_intent_mechanism/N3_PRODUCTION_INTENT_CAP_LOCAL.step` | `d64032eb88a596a7da234b08d0b89bba97b7d4fd8bec6b072b651bfb72b6a6ec` |
| I4 | docs/66 + docs/68 carrier relief | `build123d_workbench/i4_m3_production_intent_mechanisms.py`; `build123d_workbench/real_integration_conflict_resolution.py` | `build123d_workbench/out/i4_m3_production_intent_mechanisms/I4_CAP_PRODUCTION_INTENT_LOCAL.step` | `ed0ab57a4b7b22fef0e421a7dbd3c3efab182f38fd4fdfc79f668eb5bbec46c0` |
| M3 | docs/66 | `build123d_workbench/i4_m3_production_intent_mechanisms.py` | `build123d_workbench/out/i4_m3_production_intent_mechanisms/M3_CAP_PRODUCTION_INTENT_LOCAL.step` | `996e6338961ecbbfe33e743d6b619c29335b0351880daf0c9d04b4fd265614d4` |

### Generator source hash guard

| source | SHA-256 |
|---|---|
| `build123d_workbench/n2_production_intent_mechanism.py` | `4402848c98dd1883f50abe096eacbf76f023558e0d9e9c44bfa576a8e59f9038` |
| `build123d_workbench/n2_rear_reaction_support_redesign.py` | `09ae6ff17601f4e1257499d0ff0cbe4f692afc821beb35d2ff25ed5c17bc00fd` |
| `build123d_workbench/n1_production_intent_mechanism.py` | `815ceb40df97f177485474014edc866925cc9883ae72202deccb4c3bc383126b` |
| `build123d_workbench/i2_i3_production_intent_mechanism.py` | `d62577fd138f85efb9ca096999825c727979f91d9511d40fc16b62055fe96342` |
| `build123d_workbench/m4_n3_production_intent_mechanism.py` | `f583ccf6b5f488f458d2bda6da519bfdb1a0cefd3270116a8aaa7e3f8a820f2d` |
| `build123d_workbench/i4_m3_production_intent_mechanisms.py` | `c6bfd2509133d17a1380d576328128dec6b3ed077d81a14765a2ee1b4f9fbcd8` |
| `build123d_workbench/real_integration_conflict_resolution.py` | `295bb1f34b31ee33ea74c3f66ba43da18a73a4e5c7a66ffbb690f5ba44a1b8de` |
| `build123d_workbench/m4_n3_terminal_redundancy_resolution.py` | `819983f61c2205c47a7e6164c82b4668bdf27303147f39493357112caf4e1500` |

Source를 수정하거나 canonical STEP의 SHA-256가 달라지면 이 checkpoint를 자동 상속하지 않는다. 명시적 unfreeze와 해당 subsystem regression이 필요하다.

## 5. Terminal requirements

### N2

- electrical Node A = T1/T2, Node B = T3/T4
- T1/T3 = active
- T2/T4 = unused external trimmed terminals
- plastic housing/internal leadframe 수정 금지
- 기존 physical sample에서 T2/T4 절단 후 T1↔T3 switching과 actuator return 정상 확인
- N1/N2 terminal-to-joystick clearance와 최종 solder/wire departure는 actual SZH-EK056 envelope까지 **PROVISIONAL**

### M4/N3 accepted trim overlay

Canonical terminal reference:

- `build123d_workbench/out/m4_n3_terminal_redundancy_resolution/M4_N3_TRIMMED_TERMINALS_LOCAL_REFERENCE.step`
- SHA-256: `2a97fdb65f5ccbf1483172bfcf97268bc618626b13bbd3de609e41c5e7b8417b`

| terminal | electrical role | selected external trim | remaining external stub | housing intrusion |
|---|---|---:|---:|---|
| M4 T2 | UNUSED / redundant Node A; T1 remains active | 1.758428 mm | 0.300 mm | NO |
| N3 T3 | UNUSED / redundant Node B; T4 remains active | 1.758428 mm | 0.300 mm | NO |

- old penetration = 0.283393028 mm³
- new penetration = 0.000000000 mm³
- conservative service-envelope clearance = 0.262733122 mm
- active terminal geometry change = 0
- active terminal solder access = PASS
- M4/N3 terminal geometry를 더 최적화하지 않는다.

N1, I2, I3, I4, M3의 terminal은 전부 원형 유지다. M4 T1/T3/T4와 N3 T1/T2/T4도 원형 유지다.

## 6. Physical-test conditional items

다음은 checkpoint를 무효화하는 CAD HOLD가 아니라 실물 production 검증 항목이다.

1. ITS-1105 continuity topology는 실물 sample에서 확인했다. 평상시 Node A(T1/T2)와 Node B(T3/T4)는 분리되고 누르면 연결된다.
2. N2 T2/T4 절단 후 switching/return은 sample test에서 확인했다. 다만 production 반복 절단 공정의 housing 보호, burr, 열손상 및 실제 SZH-EK056 인접 clearance는 실물 fixture에서 재확인한다.
3. M4 T2/N3 T3의 0.300 mm external stub는 CAD production-intent로 ACCEPT했다. 실제 절단 공차, burr/변형 및 housing 손상 여부는 첫 제작품에서 검사한다. 이는 현재 mechanical baseline의 HOLD가 아니다.
4. FDM 재료 수축, guide/bore 실제 fit, 0.350 mm travel 및 return-force 전달은 첫 통합 시제품에서 확인한다. CAD mechanism architecture는 재설계하지 않는다.
5. Wire OD 1.0~1.3 mm는 기존 공간 seed일 뿐 최종 AWG/피복 규격이 아니다.

## 7. Frozen dimensions and regression metrics

### Common mechanism dimensions

- cap tail = Ø4.5 mm
- guide bore = Ø4.8 mm
- nominal radial clearance = 0.15 mm
- shoulder = 6.5 mm square
- retention cavity = 6.8 mm square
- nominal lateral clearance = 0.15 mm
- central actuator contact = Ø3.0 mm
- nominal travel = 0.350 mm
- hard-stop residual REST/MID/FULL = 0.350 / 0.175 / 0.000 mm
- return = ITS internal return; separate spring 없음
- critical wall gate = ≥1.20 mm
- I4 relief 후 local wall = 1.280 mm; global critical wall = 1.200 mm

### Integration regression

| metric | frozen value | result |
|---|---:|---|
| carrier-to-carrier maximum penetration | 0.000000000 mm³ | PASS |
| I2/I3 ↔ I4 carrier clearance | 0.444805280 mm | PASS |
| I2/I3 combined FULL penetration | 0.000000000 mm³ | PASS |
| I2 ↔ I3 FULL cap gap | 2.141672 mm | PASS |
| M4 ↔ N3 minimum cap gap | 3.132654 mm | PASS |
| I3 REST ↔ I4 FULL cap clearance | 3.248773 mm | PASS |
| M4 ↔ M3 FULL cap clearance | 4.847042 mm | PASS |
| M4 T2 ↔ N3 T3 penetration after trim | 0.000000000 mm³ | PASS |
| ALL-8 FULL unintended penetration | 0.000000000 mm³ | PASS |
| serviceability | — | PASS |
| exterior geometry/centers/orientations | change 0 | PRESERVED |

docs/68 I4 relief와 docs/69 terminal trim은 material-removal-only 변경이며, 기존 ALL-8 motion envelope에 새 침투를 만들지 않는다. 두 단계의 local regression과 입력 hash guard도 PASS다.

## 8. Items waiting for actual SZH-EK056

현재 workspace에는 SZH-EK056의 controlled drawing, exact STEP 또는 실물 측정 registry가 없다. nominal 판매처 치수로 production geometry를 만들지 않는다.

필요한 controlled measurements:

1. PCB X/Y/Z
2. mounting-hole X/Y pitch와 hole diameter
3. PCB datum 기준 joystick center
4. X potentiometer envelope
5. Y potentiometer envelope
6. bottom push-switch envelope
7. shaft/pivot height와 center
8. connector/header envelope와 실제 사용 방향
9. joystick maximum moving envelope
10. solder joint, wire bend 및 connector mating/service envelope

측정 전 확정하지 않는 항목:

- actual joystick ↔ N1/N2 switch/body/terminal/carrier clearance
- Thumb support/mounting interface의 production fit
- N1/N2 final wire channel
- joystick maximum-motion envelope를 지나는 모든 local wire route
- global wiring trunk production geometry
- joystick 인접 fastening/MCU 배치

## 9. Next integration order

1. **SZH-EK056 실물 또는 신뢰 가능한 exact reference 확보**
2. 실물 측정 checklist를 controlled registry에 기록하고 실제 joystick local reference 생성
3. actual joystick ↔ frozen Thumb/N1/N2 local integration audit
4. joystick maximum moving envelope를 기준으로 N1/N2 final wiring route 확정
5. five service group의 global wiring trunk 검토
6. carrier fastening bosses와 shell reaction/load path 설계
7. MCU placement 및 connector/service clearance 설계
8. subsystem regressions 승인 후에만 full assembly production STEP / 필요한 shell boolean 검토
9. 최종 승인 이후 STL / print plate 생성

## 10. Explicitly deferred / forbidden at this gate

현재 생성하거나 수정하지 않는다.

- N1/N2 final wire channel
- global wiring trunk production geometry
- carrier fastening bosses
- MCU placement
- full assembly production STEP
- full shell boolean
- STL / print plate

**Production geometry edit = 0. Finger 8-button mechanical baseline checkpoint를 기록하고 STOP한다.**
