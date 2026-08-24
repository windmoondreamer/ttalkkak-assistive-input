# 75 — Detailed PushBtn 8-button revalidation

> **STATUS CORRECTION — docs/76 source-detail dependency audit opened**  
> `BASELINE ARCHITECTURE REUSE = 100%` 및 아래 `CURRENT VALIDATION REUSE = 100.0%`는
> 삭제되지 않은 당시 결과이지만, production 확정 판정으로는 더 이상 사용하지 않는다.
> 현재 상태는 **PROVISIONAL — SOURCE-DETAIL DEPENDENCY RECHECK REQUIRED**다. 원본 PushBtn의
> 네 corner lug, 원본 pocket/seating datum, actual ITS 실물 feature, pusher/travel/hard-stop 및
> FDM tolerance dependency를 `docs/76`에서 다시 감사한다. 이 정정은 기존 수치와 산출물을
> 덮어쓰지 않으며 production geometry 변경을 뜻하지 않는다.

## 1. Authority / first-page verdict

- SWITCH NOMINAL CAD AUTHORITY = **ORIGINAL ONEGRIP PUSHBTN DETAILED 3,530-FACET MODEL**
- ACTUAL HARDWARE AUTHORITY = **MEASURED ITS-1105**
- ORIGINAL PUSHBTN ↔ ITS = **HYBRID REQUIRED**
- BODY AUTHORITY = **ORIGINAL DETAILED BODY NOMINAL + MAX(ORIGINAL, MEASURED ITS) CLEARANCE POLICY**
- ACTUATOR AUTHORITY = **MEASURED ITS-1105 OVERRIDE (2.44 mm projection)**
- TERMINAL AUTHORITY = **ACTUAL ITS-1105; CURRENT DRAWING-NOMINAL ENVELOPE UNTIL CONTROLLED ROOT METROLOGY**
- ALL 8 BUTTON MECHANISMS = **PASS WITH HYBRID SWITCH**
- ALL-8 FULL = **PASS**
- EXTERIOR = **PRESERVED**
- CURRENT VALIDATION REUSE = **100.0%**
- LOCAL REDESIGN REQUIRED = **NONE**
- FINAL VERDICT = **C. HYBRID SWITCH REFERENCE REQUIRED**
- PRODUCTION GEOMETRY MODIFICATION = **0**

원본 `mesh_PushBtn.json`의 **3,530개 facet을 그대로 sewing**하여 valid faceted BRep solid로 만들었다. bbox/box로 PushBtn을 대체하지 않았고 scale은 0건이다. 정렬은 actuator centre/axis와 plastic body-top datum으로 수행했다. 8개 centre, axis, depth, clocking은 기존 승인값 그대로다.

결론은 **C. HYBRID SWITCH REFERENCE REQUIRED**다. 원본 detailed body는 nominal language로 유효하지만, 원본 actuator projection은 **1.500 mm**로 실측 ITS **2.440 mm**보다 **0.940 mm 짧다**. current cap contact에서 원본 actuator만 쓰면 REST/MID/FULL 잔여 gap은 **0.940 / 0.765 / 0.590 mm**라 actuation이 성립하지 않는다. 따라서 actuator는 실측 ITS override가 필수다. 원본 terminal도 root/pitch/distal envelope가 다르므로 최종 packaging은 ITS terminal override를 사용한다.

## 2. Freeze / method

- exterior centre/orientation movement: **0.000 mm / 0.000°**
- shell / lowered Thumb / cap / carrier / switch pose production edit: **0건**
- full shell boolean / full production assembly boolean: **0건**
- multiprocessing / brute-force 3^8: **0건**
- selected local OCCT common + pairwise distance only
- body-facing guide/reaction은 frozen generator에서 재구성했고, shell-facing relief보다 재료가 더 많은 raw guide condition으로 보수 검사했다. 최종 production carrier STEP은 imported frozen 형상 그대로다.
- SZH-EK056 and docs/72: **not reopened / unchanged**
- peak Python RSS: **839.0 MB**

## 3. Original detailed vs actual ITS

| item | original PushBtn | measured ITS-1105 | authority result |
|---|---:|---:|---|
| body transverse maximum | 6.310 mm skirt / 6.010 mm main | 6.12 × 6.05 mm | original detailed nominal + actual measured override |
| plastic housing height | 3.500 mm | 3.560 mm | near-equivalent; actual rear datum controls |
| actuator diameter | 3.500 mm | 3.350 mm | near-equivalent diameter |
| actuator projection | 1.500 mm | 2.440 mm | **different / actual override required** |
| actuator travel clue | none; rigid imported solid | 0.15–0.35 mm, nominal 0.25 | actual hardware authority |
| terminal external length | ~3.519 mm | physical not supplied; 1.800 mm drawing-nominal envelope | **different / hybrid required** |

Original detailed 6.31 mm skirt와 6.40 mm seat 사이 nominal 최소 측면 여유는 **0.045 mm/side**다. 기하학적 penetration은 없지만 tolerance-sensitive이므로 original-only body fit은 `RECHECK`로 남겼다. 실제 구매품 body 기준 여유는 U/V **0.140 / 0.175 mm/side**다.

## 4. Per-button survival table

| button | SWITCH BODY FIT | ACTUATOR ALIGNMENT | TRAVEL | HARD STOP | REAR SUPPORT | TERMINALS | SERVICE | CARRIER | VERDICT |
|---|---|---|---|---|---|---|---|---|---|
| N1 | RECHECK / HYBRID PASS | PASS WITH ACTUAL OVERRIDE | PASS WITH ACTUAL OVERRIDE | PASS / CARRIER FIRST | PASS WITH ACTUAL BODY HEIGHT | PASS WITH HYBRID SWITCH | PASS | PASS | **VALID WITH HYBRID SWITCH** |
| N2 | RECHECK / HYBRID PASS | PASS WITH ACTUAL OVERRIDE | PASS WITH ACTUAL OVERRIDE | PASS / CARRIER FIRST | PASS WITH ACTUAL BODY HEIGHT | PASS WITH HYBRID SWITCH | PASS | PASS | **VALID WITH HYBRID SWITCH** |
| I2 | RECHECK / HYBRID PASS | PASS WITH ACTUAL OVERRIDE | PASS WITH ACTUAL OVERRIDE | PASS / CARRIER FIRST | PASS WITH ACTUAL BODY HEIGHT | PASS WITH HYBRID SWITCH | PASS | PASS | **VALID WITH HYBRID SWITCH** |
| I3 | RECHECK / HYBRID PASS | PASS WITH ACTUAL OVERRIDE | PASS WITH ACTUAL OVERRIDE | PASS / CARRIER FIRST | PASS WITH ACTUAL BODY HEIGHT | PASS WITH HYBRID SWITCH | PASS | PASS | **VALID WITH HYBRID SWITCH** |
| I4 | RECHECK / HYBRID PASS | PASS WITH ACTUAL OVERRIDE | PASS WITH ACTUAL OVERRIDE | PASS / CARRIER FIRST | PASS WITH ACTUAL BODY HEIGHT | PASS WITH HYBRID SWITCH | PASS | PASS | **VALID WITH HYBRID SWITCH** |
| M3 | RECHECK / HYBRID PASS | PASS WITH ACTUAL OVERRIDE | PASS WITH ACTUAL OVERRIDE | PASS / CARRIER FIRST | PASS WITH ACTUAL BODY HEIGHT | PASS WITH HYBRID SWITCH | PASS | PASS | **VALID WITH HYBRID SWITCH** |
| M4 | RECHECK / HYBRID PASS | PASS WITH ACTUAL OVERRIDE | PASS WITH ACTUAL OVERRIDE | PASS / CARRIER FIRST | PASS WITH ACTUAL BODY HEIGHT | PASS WITH HYBRID SWITCH | PASS | PASS | **VALID WITH HYBRID SWITCH** |
| N3 | RECHECK / HYBRID PASS | PASS WITH ACTUAL OVERRIDE | PASS WITH ACTUAL OVERRIDE | PASS / CARRIER FIRST | PASS WITH ACTUAL BODY HEIGHT | PASS WITH HYBRID SWITCH | PASS | PASS | **VALID WITH HYBRID SWITCH** |

## 5. Body fit / rear support

| button | original nominal pocket side clearance mm | actual U/V clearance mm | original rear gap mm | detailed rear footprint contact area mm² | contacts | span mm | hybrid |
|---|---:|---:|---:|---:|---:|---:|---|
| N1 | 0.045 | 0.140 / 0.175 | 0.060 | 16.543 | 3 | 4.805 | PASS |
| N2 | 0.045 | 0.140 / 0.175 | 0.060 | 16.543 | 3 | 4.805 | PASS |
| I2 | 0.045 | 0.140 / 0.175 | 0.060 | 22.908 | 5 | 7.128 | PASS |
| I3 | 0.045 | 0.140 / 0.175 | 0.060 | 22.908 | 5 | 7.128 | PASS |
| I4 | 0.045 | 0.140 / 0.175 | 0.060 | 22.908 | 5 | 7.128 | PASS |
| M3 | 0.045 | 0.140 / 0.175 | 0.060 | 22.908 | 5 | 7.128 | PASS |
| M4 | 0.045 | 0.140 / 0.175 | 0.060 | 22.908 | 5 | 7.128 | PASS |
| N3 | 0.045 | 0.140 / 0.175 | 0.060 | 22.908 | 5 | 7.128 | PASS |

원본 body height가 0.060 mm 짧으므로 current support plane과 nominal gap이 생긴다. 이것은 실제 ITS body height 3.56 mm override로 닫힌다. 원본 rear footprint를 실제 rear datum에 맞춰 별도 contact proxy로 검사한 결과 chamfer 때문에 지지 architecture가 사라지는 버튼은 없었다. 구조 하중은 current carrier hard stop이 먼저 받고 switch housing을 overtravel stop으로 쓰지 않는다.

## 6. Actuator / travel / hard stop

- cap contact centre offset: 모든 버튼 **≤ 0.000000000 mm**
- cap contact ↔ actuator angle: 모든 버튼 **0.000°**
- original-only: **HOLD at CAP ↔ ACTUATOR**
- hybrid measured actuator: **PASS** at REST / MID 0.175 / FULL 0.350
- FULL hard-stop residual: **0.000 mm**, current carrier rear stop remains structural stop

이번 결과는 `DETAILED SWITCH REVALIDATION FAILED AT CAP ↔ ORIGINAL ACTUATOR PROJECTION`이며 exterior 실패가 아니다. hidden reference를 measured actuator로 override하면 production geometry 변경 없이 해소된다.

## 7. Terminal-root comparison

Δ 순서는 functional `(U, V, inward depth)`이고 `original − current simplified`다.

| terminal | root ΔU/ΔV/Δdepth mm | root angle Δ deg | distal length Δ mm |
|---|---|---:|---:|
| T2 | +0.208, -0.295, +0.065 | 10.993 | +1.719 |
| T1 | +0.208, +0.295, +0.065 | 10.993 | +1.719 |
| T4 | -0.208, -0.295, +0.065 | 10.993 | +1.719 |
| T3 | -0.208, +0.295, +0.065 | 10.993 | +1.719 |

- original-terminal diagnostic collision count: **25** — final authority에 사용하지 않음
- hybrid terminal failed interface count: **0**
- terminal authority qualifier: **physical pin/root metrology not supplied; current override remains drawing-nominal plus existing physical trim tests**

### N2

- strategy: **T1/T3 active, T2/T4 unused external trim**
- T1/T3 solder access: **retained**
- T2/T4 housing/internal leadframe intrusion: **NO**
- existing physical sample after T2/T4 trim: switching/return **PASS**
- verdict: **VALID WITH HYBRID SWITCH**

### M4 / N3

- M4 T2 / N3 T3 selected trim: **1.758428 mm**
- remaining external stub: **0.300 mm**
- old penetration: **0.283393028 mm³**
- new penetration: **0.000000000 mm³**
- new clearance: **0.262733 mm**
- verdict: **VALID AS-IS**; physical first-article terminal metrology gate retained

## 8. Carrier-carrier regression

| pair | clearance mm | penetration mm³ | result |
|---|---:|---:|---|
| N1_N2<->I2_I3 | 7.127319 | 0.000000000 | PASS |
| N1_N2<->M4_N3 | 31.010128 | 0.000000000 | PASS |
| N1_N2<->I4 | 8.845497 | 0.000000000 | PASS |
| N1_N2<->M3 | 30.533602 | 0.000000000 | PASS |
| I2_I3<->M4_N3 | 12.373789 | 0.000000000 | PASS |
| I2_I3<->I4 | 0.444805 | 0.000000000 | PASS |
| I2_I3<->M3 | 12.216827 | 0.000000000 | PASS |
| M4_N3<->I4 | 12.121880 | 0.000000000 | PASS |
| M4_N3<->M3 | 0.400000 | 0.000000000 | PASS |
| I4<->M3 | 12.398746 | 0.000000000 | PASS |

- maximum carrier penetration: **0.000000000 mm³**
- minimum carrier clearance: **0.400000 mm** at `M4_N3<->M3`
- approved I2/I3 ↔ I4 relief reference: **0.444805280 mm**

## 9. Motion regression

| state | FULL buttons | max unintended penetration mm³ | result |
|---|---|---:|---|
| ALL_REST | - | 0.000000000 | PASS |
| N1_FULL | N1 | 0.000000000 | PASS |
| N2_FULL | N2 | 0.000000000 | PASS |
| I2_FULL | I2 | 0.000000000 | PASS |
| I3_FULL | I3 | 0.000000000 | PASS |
| I4_FULL | I4 | 0.000000000 | PASS |
| M3_FULL | M3 | 0.000000000 | PASS |
| M4_FULL | M4 | 0.000000000 | PASS |
| N3_FULL | N3 | 0.000000000 | PASS |
| N1_N2_FULL | N1, N2 | 0.000000000 | PASS |
| I2_I3_FULL | I2, I3 | 0.000000000 | PASS |
| M4_N3_FULL | M4, N3 | 0.000000000 | PASS |
| I4_I3_FULL | I3, I4 | 0.000000000 | PASS |
| M3_M4_FULL | M3, M4 | 0.000000000 | PASS |
| ALL_8_FULL | I2, I3, I4, M3, M4, N1, N2, N3 | 0.000000000 | PASS |

Brute-force 3^8은 수행하지 않았다. 사용자 지정 15개 state만 검사했다.

## 10. Serviceability

| carrier group | removal direction | travel mm | max unintended penetration mm³ | result |
|---|---|---:|---:|---|
| N1_N2 | [-1.0, 0.0, 0.0] | 15.0 | 0.000000000 | PASS |
| I2_I3 | [-1.0, 0.0, 0.0] | 15.0 | 0.000000000 | PASS |
| M4_N3 | [1.0, 0.0, 0.0] | 15.0 | 0.000000000 | PASS |
| I4 | [1.0, 0.0, 0.0] | 15.0 | 0.000000000 | PASS |
| M3 | [-1.0, 0.0, 0.0] | 15.0 | 0.000000000 | PASS |

Detailed original skirt는 audit nominal로 tolerance-sensitive지만 실제 ITS body 기준 insertion/removal 여유는 유지된다. Carrier removal과 terminal solder access architecture는 모두 재사용 가능하다.

## 11. Validation survival matrix

| baseline item | classification | basis |
|---|---|---|
| N1 mechanism | VALID WITH HYBRID SWITCH | body/guide/support survive; measured actuator override required |
| N2 mechanism | VALID WITH HYBRID SWITCH | short-U support and hard stop survive |
| I2/I3 | VALID WITH HYBRID SWITCH | shared carrier and independent motion rechecked |
| M4/N3 | VALID WITH HYBRID SWITCH | shared carrier survives; actual terminal overlay retained |
| I4 | RECHECKED AND PASS | docs/68 relief preserved; hybrid switch fit pass |
| M3 | RECHECKED AND PASS | standalone carrier fit and service pass |
| N2 terminal trim | VALID WITH HYBRID SWITCH | T1/T3 access and T2/T4 external trim retained |
| M4/N3 terminal trim | VALID WITH HYBRID SWITCH | 0.300-mm stubs preserve zero penetration |
| carrier clearances | RECHECKED AND PASS | minimum 0.400000 mm; penetration zero |
| all-8 motion | RECHECKED AND PASS | 15 requested states; all unintended penetration zero |
| serviceability | RECHECKED AND PASS | five group paths and actual-body insertion remain pass |

Architecture reuse 정의는 요청된 11개 baseline 항목 중 `LOCAL ADAPTATION REQUIRED` 또는 `SUPERSEDED`가 아닌 항목의 비율이다. 결과는 **11/11 = 100.0%**다. Reference authority는 hybrid로 바뀌지만 production mechanism architecture는 전부 살아남는다.

## 12. Deviation map

- GREEN area: **6.1%**
- YELLOW area: **20.1%**
- RED area: **73.8%**
- maximum sampled surface deviation: **2.029 mm**

RED는 주로 actuator tip과 original terminal distal legs다. Body corner/skirt는 GREEN/YELLOW 범위이며 positive seat clearance를 유지한다. 이 heat-map은 visualization metric이고 collision authority는 faceted BRep / measured envelope exact checks다.

## 13. Required renders

1. `renders/detailed_pushbtn_8_button_revalidation/01_original_pushbtn_detailed_isolated.png`
2. `renders/detailed_pushbtn_8_button_revalidation/02_legacy_simplified_its_isolated.png`
3. `renders/detailed_pushbtn_8_button_revalidation/03_measured_its1105_envelope.png`
4. `renders/detailed_pushbtn_8_button_revalidation/04_three_way_overlay.png`
5. `renders/detailed_pushbtn_8_button_revalidation/05_actuator_closeup.png`
6. `renders/detailed_pushbtn_8_button_revalidation/06_terminal_root_closeup.png`
7. `renders/detailed_pushbtn_8_button_revalidation/07_n1_detailed_switch_inside_carrier.png`
8. `renders/detailed_pushbtn_8_button_revalidation/08_n2_detailed_switch_inside_carrier.png`
9. `renders/detailed_pushbtn_8_button_revalidation/09_i2_i3_detailed_switches.png`
10. `renders/detailed_pushbtn_8_button_revalidation/10_m4_n3_detailed_switches_trimmed_relation.png`
11. `renders/detailed_pushbtn_8_button_revalidation/11_i4_m3_detailed_switches.png`
12. `renders/detailed_pushbtn_8_button_revalidation/12_transparent_all_8_detailed_switch_assembly.png`
13. `renders/detailed_pushbtn_8_button_revalidation/13_all_8_full_hybrid.png`
14. `renders/detailed_pushbtn_8_button_revalidation/14_deviation_heat_map.png`

## 14. Protected input hash guard

작업 전후 protected input SHA-256는 **IDENTICAL**이다.

| protected input | SHA-256 before |
|---|---|
| `docs/60_n2_production_intent_mechanism.md` | `b88ea6cfacee7b84781b464b842442b9bd216ce571115e5d11f40378844ba648` |
| `docs/61_n2_robustness_pass.md` | `6b59516bb149bb952febd4afffe11375e2054c5ac1d18d3f6a5b661a386facd5` |
| `docs/62_n2_rear_reaction_support_redesign.md` | `871378effa12c71f23b73e8d6ed5c0c849864ee3fb35deee7b65e28d7a3669dd` |
| `docs/63_n1_production_intent_mechanism.md` | `f3e481320321c683b3ffd64a361f91107b7e946b6679e64ed8dd2a4827b3bc0c` |
| `docs/64_i2_i3_production_intent_mechanism.md` | `65395a3f8d33bc5f4835ee908d786df489a5084761faeabe6773aed88981aad5` |
| `docs/65_m4_n3_production_intent_mechanism.md` | `450e257abf707adb9629aa537c4062fe86db1296be552cfd950cd5c89d0889ba` |
| `docs/66_i4_m3_production_intent_mechanisms.md` | `b6560657259aed36d44b66583512db0c1d20d15164bf2c499c71e13306864aed` |
| `docs/67_all_8_button_integration_and_wiring_space_audit.md` | `1eb8eb6084aba60798d134ee898927dd42c07d35e9311731aab484a01f1f2de5` |
| `docs/68_real_integration_conflict_resolution.md` | `df70ac5093b2042bd6220c88d214ff023512812bd880cf30e1273af37c79ee97` |
| `docs/69_m4_n3_terminal_redundancy_resolution.md` | `cf71c120556f37e8ded9ee572ba975ab5f888880edfac07ae86d8518d33d44a2` |
| `docs/70_finger_8_button_mechanical_baseline_checkpoint.md` | `bad77cd92f71dbd8dc027287facb9a983c12b78e94d544e0cac302fb37730719` |
| `build123d_workbench/out/n1_production_intent_mechanism/N1_N2_SHARED_CARRIER_N1_LOCAL.step` | `2485e34f8716395459f1f7b10384fd73a33695472f9aae689cf321d583830756` |
| `build123d_workbench/out/i2_i3_production_intent_mechanism/I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step` | `1aa49477668d26d0617814e89c6dc25eca0564b12f927d9481d93896513aa92b` |
| `build123d_workbench/out/m4_n3_production_intent_mechanism/M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step` | `246b309ac3550d4c0f9e82e77f298e884077ef83ed763c863658f3e589a9bca3` |
| `build123d_workbench/out/real_integration_conflict_resolution/I4_CARRIER_LOCAL_MANUFACTURING_RELIEF.step` | `90b0002f3c3d1bdd95fc157809891351ad8f9cd5bb8cdcdb9a260fa9c33dcfe7` |
| `build123d_workbench/out/i4_m3_production_intent_mechanisms/M3_CARRIER_PRODUCTION_INTENT_LOCAL.step` | `021363afb7b761456b436d6252d12a3d786003ea19bef6acb908651708d44786` |
| `build123d_workbench/out/n1_production_intent_mechanism/N1_PRODUCTION_INTENT_CAP_LOCAL.step` | `5f7574f90682f7e511067aaac1d514274bb75a0ffeaeaae7e8a45b3502e1d6a5` |
| `build123d_workbench/out/n2_production_intent_mechanism/N2_PRODUCTION_INTENT_CAP.step` | `7f88cf6abfb8bea9a792e81b1def3ffa4ee96e2259f628ecb18d20f76ca5238c` |
| `build123d_workbench/out/i2_i3_production_intent_mechanism/I2_PRODUCTION_INTENT_CAP_LOCAL.step` | `57f272b308af329655239f408c3d992f5c8f947476a4d794d93caab675bafbf9` |
| `build123d_workbench/out/i2_i3_production_intent_mechanism/I3_PRODUCTION_INTENT_CAP_LOCAL.step` | `8c478ffcdabb136400c12ff661c4fdc857de79d4849c678b3dd75c1a1f1abe38` |
| `build123d_workbench/out/m4_n3_production_intent_mechanism/M4_PRODUCTION_INTENT_CAP_LOCAL.step` | `d5c7542eece5d83abebd282a211263584c11b422e58fbbc533eee062f786a9ff` |
| `build123d_workbench/out/m4_n3_production_intent_mechanism/N3_PRODUCTION_INTENT_CAP_LOCAL.step` | `d64032eb88a596a7da234b08d0b89bba97b7d4fd8bec6b072b651bfb72b6a6ec` |
| `build123d_workbench/out/i4_m3_production_intent_mechanisms/I4_CAP_PRODUCTION_INTENT_LOCAL.step` | `ed0ab57a4b7b22fef0e421a7dbd3c3efab182f38fd4fdfc79f668eb5bbec46c0` |
| `build123d_workbench/out/i4_m3_production_intent_mechanisms/M3_CAP_PRODUCTION_INTENT_LOCAL.step` | `996e6338961ecbbfe33e743d6b619c29335b0351880daf0c9d04b4fd265614d4` |
| `build123d_workbench/out/finger_controls_v2/JAD_FINGER_V2.step` | `a477aa79e55ddb21fb2a45c7f616544f6eb4844b593f61cf7d45303476c5a762` |
| `build123d_workbench/out/finger_controls_v2/JFD_FINGER_V2.step` | `d457d5d9b305a4c7d77e21aab3cb7d33336d672d4d8bf031e6158de44c26ad50` |
| `build123d_workbench/out/m4_n3_terminal_redundancy_resolution/M4_N3_TRIMMED_TERMINALS_LOCAL_REFERENCE.step` | `2a97fdb65f5ccbf1483172bfcf97268bc618626b13bbd3de609e41c5e7b8417b` |
| `cad_dump/mesh_PushBtn.json` | `d9c7ed740332b636014c56e4bc8874d879704bc73f266f72fac62667226be9e7` |
| `cad_dump/its1105_physical_sample_reaudit.json` | `39b9bf58bb0a7b8148159603fe0e8574369ce60bd130e51c793b7153c39ac586` |
| `build123d_workbench/finger_controls_v2.py` | `ab902a423c2932a08864b5aaae5f3b03d92902ba8d8707fb546e28b6ee5466f3` |
| `build123d_workbench/n2_production_intent_mechanism.py` | `4402848c98dd1883f50abe096eacbf76f023558e0d9e9c44bfa576a8e59f9038` |
| `build123d_workbench/n2_rear_reaction_support_redesign.py` | `09ae6ff17601f4e1257499d0ff0cbe4f692afc821beb35d2ff25ed5c17bc00fd` |
| `build123d_workbench/n1_production_intent_mechanism.py` | `815ceb40df97f177485474014edc866925cc9883ae72202deccb4c3bc383126b` |
| `build123d_workbench/i2_i3_production_intent_mechanism.py` | `d62577fd138f85efb9ca096999825c727979f91d9511d40fc16b62055fe96342` |
| `build123d_workbench/m4_n3_production_intent_mechanism.py` | `f583ccf6b5f488f458d2bda6da519bfdb1a0cefd3270116a8aaa7e3f8a820f2d` |
| `build123d_workbench/i4_m3_production_intent_mechanisms.py` | `c6bfd2509133d17a1380d576328128dec6b3ed077d81a14765a2ee1b4f9fbcd8` |
| `build123d_workbench/real_integration_conflict_resolution.py` | `295bb1f34b31ee33ea74c3f66ba43da18a73a4e5c7a66ffbb690f5ba44a1b8de` |
| `build123d_workbench/m4_n3_terminal_redundancy_resolution.py` | `819983f61c2205c47a7e6164c82b4668bdf27303147f39493357112caf4e1500` |

## 15. Final verdict / STOP

**C. HYBRID SWITCH REFERENCE REQUIRED**

- nominal body language: original detailed PushBtn
- manufacturing body clearance: max(original detailed, measured ITS), with actual measured body recorded separately
- actuator: **measured ITS override required**
- terminals: **actual ITS authority; current drawing-nominal envelope until controlled physical root registry exists**
- production local redesign: **NONE**
- exterior: **PRESERVED**
- production geometry edit: **0**

Audit 결과를 기록하고 STOP한다. 사용자의 별도 승인 전에는 shell/cap/carrier/switch pose/Thumb/SZH fixture에 적용하지 않는다.
