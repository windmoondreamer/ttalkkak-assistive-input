# 63 — N1 PRODUCTION-INTENT BUTTON MECHANISM

## 결론

N1은 승인 외형과 현재 ITS 자세를 그대로 유지한 **direct-actuation production-intent architecture**로 완성했다. N1은 캡/액추에이터가 이미 동축·평행이므로 tilt/clocking을 추가하지 않았다. 내부 캡에는 6.5 mm positive shoulder, Ø4.5 tail, Ø3.0 중앙 접점을 적용했고, 고정측에는 Ø4.8 bore의 N1 전용 C-guide와 0.350 mm structural hard stop을 적용했다.

N1 guide 원형은 JfD local shell과 0.121714 mm³ 겹쳤다. 외형이나 shell을 바꾸지 않고 개방측 전면 립 두 곳의 비기능 코너만 합계 **0.712500 mm³** relief하여 penetration 0, shell minimum clearance **0.018974 mm**를 만들었다. 6.8 mm cavity, 6.5 mm shoulder, closed guide rail 1.25 mm와 양 stop plane의 기능 치수는 유지된다.

## 1. Current N1 exact audit

- cap center: `[-10.990443464183823, -35.80002827761031, 25.0]` mm
- cap plane normal / travel axis: `[-0.07646638594200623, -0.8724593951000031, -0.48266706509011453]`
- ITS actuator top center: `[-10.809982793360689, -33.741024105174304, 26.13909427361267]` mm
- cap ↔ actuator lateral center offset: **0.000000000 mm**
- cap plane ↔ switch top plane: **0.000000000°**
- switch axis ↔ cap travel axis: **0.000000000°**
- switch body ↔ HW504 A/B: **0.000000000 / 3.805390 mm**, penetration 0
- frozen carrier ↔ HW504 A/B: **0.304180 / 1.360984 mm**
- cap ↔ local shell: **0.200000 mm**
- switch body ↔ local shell: **1.637122 mm**

## 2. N1 mechanism

- load path: `finger → cap → Ø3.0 central contact → ITS actuator/body → short U cradle → shared carrier/shell`
- cap retention: 6.5 mm square positive shoulder; closed shell에서는 외부 이탈 불가, shell-open 상태에서 C-guide 개방측으로 서비스 가능
- guide: Ø4.5 tail / Ø4.8 bore, radial clearance 0.15 mm; 6.8 mm square cavity / shoulder lateral clearance 0.15 mm
- hard stop: carrier guide rear stop at 0.350 mm; ITS housing은 structural stop으로 사용하지 않음
- return: 별도 spring 없이 ITS internal return이 actuator와 central contact를 통해 cap으로 전달
- rear support: **SHORT U-SHAPED REACTION CRADLE**, all-terminal-safe three-zone plastic-body reaction
- unique support area: **13.524 mm²**
- support contact span: **4.890 mm**
- minimum structural wall: **1.200 mm**
- floating solid: **없음**; frozen carrier에서 제거한 부피 **0.000000000 mm³**

## 3. N1 terminal exact map

N2 T1/T3 전기 전략을 복사하지 않았다. N1은 CAD penetration이 없으므로 T1/T2/T3/T4를 모두 무절단 유지한다.

| terminal | HW504 A mm | HW504 B mm | local shell mm | carrier mm | 처리 |
|---|---:|---:|---:|---:|---|
| T1 | 0.000270 | 8.780298 | 4.611143 | 0.230000 | 유지 |
| T2 | 0.000000 | 5.659790 | 4.651590 | 0.530000 | 유지 |
| T3 | 0.482136 | 4.481009 | 4.808959 | 0.000000 | 유지 |
| T4 | 0.765709 | 2.482639 | 4.848436 | 0.530000 | 유지 |

최소 terminal ↔ HW504 clearance는 **0.000000000 mm**다. Exact CAD penetration은 0이지만 T2/HW504-A가 사실상 tangent이므로, 실물 공차를 확인하기 전 production fit은 **CONDITIONAL**이다. 임의 terminal trim은 하지 않았다.

## 4. Exact N1 motion

| travel mm | cap-guide pen mm³ | cap-shell pen mm³ | cap-actuator gap mm | hard-stop residual mm |
|---:|---:|---:|---:|---:|
| 0.000 | 0.000000000 | 0.000000000 | 0.000000000 | 0.350 |
| 0.175 | 0.000000000 | 0.000000000 | 0.000000000 | 0.175 |
| 0.350 | 0.000000000 | 0.000000000 | 0.000000000 | 0.000 |

각 상태에서 switch/carrier, 모든 terminal/carrier 및 terminal/HW504, carrier/HW504의 unintended penetration은 0이다. FULL에서 shoulder가 carrier guide rear stop에 닿고 residual이 0.000 mm가 된다.

## 5. N2 frozen regression

- carrier ↔ HW504 A: **0.304180346 mm** (approved 0.304180346)
- carrier ↔ HW504 B: **1.360983710 mm** (approved 1.360983710)
- N2 T1/T3 ↔ HW504 B: **2.119093040 mm** (approved 2.119093040)
- N2 REST/MID/FULL: **PASS**
- N2 hard stop: **PASS**
- approved short U-cradle: **UNCHANGED**
- frozen N2 carrier removed volume: **0.000000000 mm³**
- N1 addition ↔ N2 protected keep-outs penetration: **0**

## 6. Required outputs

- `renders\n1_production_intent_mechanism\01_current_n1_internal_structure.png`
- `renders\n1_production_intent_mechanism\02_n1_exploded.png`
- `renders\n1_production_intent_mechanism\03_n1_terminal_exact_map.png`
- `renders\n1_production_intent_mechanism\04_n1_rest_section.png`
- `renders\n1_production_intent_mechanism\05_n1_full_0p350_section.png`
- `renders\n1_production_intent_mechanism\06_n1_rear_reaction_support_closeup.png`
- `renders\n1_production_intent_mechanism\07_n1_n2_shared_carrier_transparent.png`
- `renders\n1_production_intent_mechanism\08_n1_vs_hw504_clearance.png`
- `renders\n1_production_intent_mechanism\09_n2_frozen_region_regression.png`

- `build123d_workbench\out\n1_production_intent_mechanism\n1_production_intent_mechanism.json` — lightweight exact result
- `build123d_workbench\out\n1_production_intent_mechanism\N1_PRODUCTION_INTENT_CAP_LOCAL.step` — N1 cap local component STEP only
- `build123d_workbench\out\n1_production_intent_mechanism\N1_N2_SHARED_CARRIER_N1_LOCAL.step` — N1/N2 local shared-carrier STEP only
- STL / print plate / full shell / production full assembly STEP: **생성하지 않음**

## 7. Required report fields

- N1 CAP ↔ SWITCH ALIGNMENT = **COAXIAL / PARALLEL / 0.000000 mm lateral offset**
- N1 ACTUATION = **DIRECT**
- N1 REAR SUPPORT TYPE = **SHORT U-SHAPED REACTION CRADLE**
- N1 SUPPORT AREA = **13.524 mm²**
- N1 HW504 MIN CLEARANCE = **0.000000000 mm**
- N1 TERMINAL MIN CLEARANCE = **0.000000000 mm**
- N1 MIN WALL = **1.200 mm**
- N1 MOTION = **PASS**
- N1 HARD STOP = **PASS**
- N1 RETURN = **PASS**
- N1 SERVICE = **PASS**
- N2 REGRESSION = **PASS**
- EXTERIOR = **PRESERVED**

## 8. FINAL VERDICT / STOP

- N1 ARCHITECTURE = **ACCEPT**
- N1 MOTION = **PASS**
- N1 REAR SUPPORT = **PASS**
- N1 TERMINALS = **CONDITIONAL**
- N1 SERVICEABILITY = **PASS**
- N2 FROZEN BASELINE = **PRESERVED**
- EXTERIOR = **PRESERVED**

N1만 완료하고 STOP한다. I2/I3/I4/M3/M4/N3에는 확장하지 않았다.
