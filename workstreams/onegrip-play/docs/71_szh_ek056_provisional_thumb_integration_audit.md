# 71 — SZH-EK056 provisional Thumb integration audit

## 1. Scope and freeze

이 감사는 `docs/70`의 Finger 8-button mechanical baseline 이후 **SZH_EK056_WEB_REFERENCE**를 현재 Thumb joystick datum에 배치한 coarse packaging audit다. 웹/사진 기반 approximate reference이므로 0.5 mm 미만 결과는 production 판정에 쓰지 않는다.

- production geometry edit: **0**
- Finger 8-button / M4-N3 trim / exterior: **HARD FROZEN / PRESERVED**
- full shell boolean: **0** (JaD/JfD는 한 번씩 local crop을 만든 뒤 local section만 사용)
- full production assembly / multiprocessing / brute force / STEP·STL export: **0**
- HW504-A/B: **REFERENCE / PLACEHOLDER OVERLAY ONLY**

## 2. Required final table

| item | result |
|---|---|
| SZH-EK056 REFERENCE QUALITY | **LOW** |
| GENERAL PACKAGING SUITABILITY | **CONDITIONAL** |
| MOUNTING ALIGNMENT | **ADAPTER REQUIRED** |
| JOYSTICK CENTER ERROR | **0.000000000 mm** |
| STATIC NON-REMOVABLE COLLISIONS | PCB↔N1.carrier GROSS depth≈1.600 mm / 36.145 mm³; PCB↔N1.switch_body GROSS depth≈1.600 mm / 30.914 mm³; PCB↔N1.T1 MODERATE depth≈0.903 mm / 0.903 mm³; PCB↔N1.T2 SMALL depth≈0.245 mm / 0.031 mm³; PCB↔N1.T3 GROSS depth≈1.090 mm / 0.784 mm³; PCB↔N1.T4 MODERATE depth≈0.732 mm / 0.271 mm³; PCB↔N2.carrier GROSS depth≈1.600 mm / 24.593 mm³; PCB↔N2.switch_body GROSS depth≈1.600 mm / 34.133 mm³; PCB↔N2.T1 GROSS depth≈1.003 mm / 0.875 mm³; PCB↔N2.T2 SMALL depth≈0.158 mm / 0.011 mm³; PCB↔N2.T3 GROSS depth≈1.077 mm / 0.884 mm³; PCB↔N2.T4 MODERATE depth≈0.669 mm / 0.211 mm³; PCB↔local_shell.JaD GROSS depth≈1.600 mm / 69.457 mm³; PCB↔local_shell.JfD GROSS depth≈1.600 mm / 111.677 mm³; CENTER_GIMBAL↔N1.switch_body SMALL depth≈0.241 mm / 0.066 mm³; CENTER_GIMBAL↔N1.T4 GROSS depth≈1.180 mm / 0.931 mm³; CENTER_GIMBAL↔N2.carrier SMALL depth≈0.186 mm / 0.068 mm³; CENTER_GIMBAL↔N2.switch_body MODERATE depth≈0.632 mm / 1.613 mm³; CENTER_GIMBAL↔N2.T1 MODERATE depth≈0.735 mm / 0.287 mm³; CENTER_GIMBAL↔N2.T2 MODERATE depth≈0.681 mm / 0.224 mm³; CENTER_GIMBAL↔N2.T3 SMALL depth≈0.218 mm / 0.018 mm³; CENTER_GIMBAL↔N2.T4 SMALL depth≈0.192 mm / 0.024 mm³; BOTTOM_SWITCH↔N1.carrier SMALL depth≈0.028 mm / 0.000 mm³; BOTTOM_SWITCH↔N1.switch_body MODERATE depth≈0.583 mm / 1.224 mm³; BOTTOM_SWITCH↔N1.T1 SMALL depth≈0.214 mm / 0.028 mm³; BOTTOM_SWITCH↔N1.T2 MODERATE depth≈0.915 mm / 1.170 mm³; SHAFT↔local_shell.JaD SMALL depth≈0.005 mm / 5.276 mm³; SHAFT↔local_shell.JfD SMALL depth≈0.005 mm / 6.549 mm³ |
| TRIMMABLE PIN/HEADER COLLISIONS | NONE |
| UNKNOWN COLLISIONS | HEADER_PLASTIC↔local_shell.JaD GROSS depth≈2.600 mm / 18.139 mm³; HEADER_PLASTIC↔local_shell.JfD GROSS depth≈2.600 mm / 51.768 mm³ |
| N1 STATIC FIT | **HOLD** |
| N2 STATIC FIT | **HOLD** |
| STOCK HEADER CONFIGURATION | **HOLD** |
| DIRECT-SOLDER/TRIM CONFIGURATION | **HOLD** |
| MOVING ENVELOPE | **HOLD** |
| N1 WIRING DEPARTURE | **BLOCKED** (side) |
| N2 WIRING DEPARTURE | **BLOCKED** (shell_wall_following) |
| THUMB ORIGINAL REUSE | **90.0 %** |
| EXTERIOR | **PRESERVED** |

## 3. Reference quality and geometry classes

Reference quality는 **LOW**다. PCB plan/mounting pattern은 판매처·정사영 사진에 근거하지만, gimbal/pot Z envelope, pivot 높이, shaft, 25° moving sweep는 추정값이다. General packaging과 gross conflict 선별에는 쓸 수 있으나 sub-0.5 mm production tuning에는 쓸 수 없다.

| feature | class | removable? | trimmable? | electrically required? | mechanically required? |
|---|---|---|---|---|---|
| PCB structural outline / pads | A | NO | NO | YES | YES |
| center gimbal / pivot / shaft | A | NO | NO | FUNCTIONAL | YES |
| X potentiometer body | A | NO | NO | YES / VRx | YES |
| Y potentiometer body | A | NO | NO | YES / VRy | YES |
| bottom push-switch body | A | NO | NO | YES / SW | YES |
| mounting-hole functional regions | A | NO | NO | NO | YES |
| external knob/cap | B | POTENTIALLY | NO | NO | USER INTERFACE / MAY BE REPLACED |
| 1x5 distal pin length | B | POTENTIALLY | YES | ROOT YES / DISTAL LENGTH NO | NO IF STRAIN RELIEF PROVIDED |
| 1x5 header plastic | C | UNKNOWN | NO | NO | UNKNOWN / VERIFY ANCHOR |
| PCB pads + solder roots GND/+5V/VRx/VRy/SW | A | NO | NO | ALL FIVE YES | SOLDER/STRAIN RELIEF |

제품 라벨 사진 기준 1×5 전기 연결은 **GND / +5V / VRx / VRy / SW**다. 5개 신호는 전체 joystick 기능에 모두 필요하므로 unused electrical pin은 없다. 다만 PCB pad/root를 유지한 직접 납땜 구성에서는 긴 distal pin은 절단 가능성이 있다. Header insulator depopulation의 기계적 안전성은 실물 확인 전 **CLASS C / CONDITIONAL**이다.

## 4. Mounting alignment

Shaft pivot center와 nominal axis를 승인 opening datum에 맞췄으므로 center error는 **0.000000000 mm**, axis error는 **0.000000°**다. Opening/exterior는 이동하지 않았다.

- original pattern: **26.150000 × 19.700000 mm**
- SZH web reference: **26.500000 × 19.450000 mm**
- pitch difference: **0.350000 / 0.250000 mm**
- maximum in-plane corner residual: **0.652111 mm**
- mean mounting-plane offset: **1.800000 mm**
- hole diameter: original ≈3.2 mm / web reference 3.0 mm

| hole | in-plane residual mm | axial plane offset mm |
|---|---:|---:|
| H1 | 0.223594 | 1.800000 |
| H2 | 0.436045 | 1.800000 |
| H3 | 0.533955 | 1.800000 |
| H4 | 0.652111 | 1.800000 |

따라서 **ADAPTER REQUIRED**다. 현재 Backplate의 직접 bolt-on은 성립하지 않으며 small shell-side/backplate adapter가 필요하다. 이번 단계에서는 adapter를 생성하지 않았다.

### Axial datum sensitivity

웹 모델의 `pivot Z=11.5 mm`가 LOW-confidence 추정값이므로, pivot을 3D point로 일치시킨 본 배치 외에 shaft **centerline/axis는 그대로 유지**하고 module을 축 방향으로 **1.800000 mm** 이동시켜 original mounting plane을 맞춘 한 번의 민감도 검사도 수행했다. 이는 candidate search나 production placement가 아니라, 낮은 신뢰도의 pivot 높이 하나 때문에 architecture를 과도하게 기각하지 않기 위한 check다.

| sensitivity feature | target | severity | depth proxy mm | penetration mm³ |
|---|---|---|---:|---:|
| PCB | N1.switch_body | SMALL | 0.383459 | 0.361636 |
| PCB | N1.T1 | SMALL | 0.299730 | 0.049690 |
| PCB | N1.T2 | MODERATE | 0.898810 | 0.902871 |
| PCB | N1.T4 | GROSS | 1.108381 | 0.813273 |
| PCB | N2.switch_body | SMALL | 0.432489 | 0.528325 |
| PCB | N2.T1 | MODERATE | 0.534712 | 0.176018 |
| PCB | N2.T2 | SMALL | 0.481231 | 0.155608 |
| PCB | N2.T3 | SMALL | 0.018295 | 0.000011 |
| CENTER_GIMBAL | N1.T4 | SMALL | 0.058636 | 0.000334 |
| BOTTOM_SWITCH | N1.T2 | MODERATE | 0.550501 | 0.179104 |

Pivot-coincident pose의 PCB/carrier gross overlap은 이 축 이동에서 사라진다. 남는 것은 주로 switch/terminal 주변 local overlap이므로 최종 architecture는 `MAJOR PACKAGING CONFLICT`가 아니라 **local internal/adapter adaptation 필요**로 분류한다. 정확한 축 방향 위치는 실물 pivot/shaft/PCB Z 측정 전 확정하지 않는다.

## 5. Component-specific static audit

| SZH feature | target | class | severity | depth proxy mm | penetration mm³ | disposition |
|---|---|---|---|---:|---:|---|
| PCB | N1.carrier | A | GROSS | 1.600000 | 36.144726 | COARSE PACKAGING EVIDENCE |
| PCB | N1.switch_body | A | GROSS | 1.600000 | 30.914191 | COARSE PACKAGING EVIDENCE |
| PCB | N1.T1 | A | MODERATE | 0.902562 | 0.902900 | COARSE PACKAGING EVIDENCE |
| PCB | N1.T2 | A | SMALL | 0.245025 | 0.031120 | PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED |
| PCB | N1.T3 | A | GROSS | 1.090196 | 0.783867 | COARSE PACKAGING EVIDENCE |
| PCB | N1.T4 | A | MODERATE | 0.731979 | 0.270835 | COARSE PACKAGING EVIDENCE |
| PCB | N2.carrier | A | GROSS | 1.600000 | 24.592768 | COARSE PACKAGING EVIDENCE |
| PCB | N2.switch_body | A | GROSS | 1.600000 | 34.133454 | COARSE PACKAGING EVIDENCE |
| PCB | N2.T1 | A | GROSS | 1.003020 | 0.874917 | COARSE PACKAGING EVIDENCE |
| PCB | N2.T2 | A | SMALL | 0.158222 | 0.011351 | PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED |
| PCB | N2.T3 | A | GROSS | 1.076831 | 0.884426 | COARSE PACKAGING EVIDENCE |
| PCB | N2.T4 | A | MODERATE | 0.669481 | 0.211010 | COARSE PACKAGING EVIDENCE |
| PCB | local_shell.JaD | A | GROSS | 1.600000 | 69.457418 | COARSE PACKAGING EVIDENCE |
| PCB | local_shell.JfD | A | GROSS | 1.600000 | 111.677457 | COARSE PACKAGING EVIDENCE |
| CENTER_GIMBAL | N1.switch_body | A | SMALL | 0.240819 | 0.065717 | PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED |
| CENTER_GIMBAL | N1.T4 | A | GROSS | 1.180020 | 0.930752 | COARSE PACKAGING EVIDENCE |
| CENTER_GIMBAL | N2.carrier | A | SMALL | 0.185820 | 0.068302 | PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED |
| CENTER_GIMBAL | N2.switch_body | A | MODERATE | 0.632489 | 1.613478 | COARSE PACKAGING EVIDENCE |
| CENTER_GIMBAL | N2.T1 | A | MODERATE | 0.734712 | 0.287140 | COARSE PACKAGING EVIDENCE |
| CENTER_GIMBAL | N2.T2 | A | MODERATE | 0.681231 | 0.223742 | COARSE PACKAGING EVIDENCE |
| CENTER_GIMBAL | N2.T3 | A | SMALL | 0.218295 | 0.017581 | PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED |
| CENTER_GIMBAL | N2.T4 | A | SMALL | 0.192272 | 0.024083 | PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED |
| BOTTOM_SWITCH | N1.carrier | A | SMALL | 0.028455 | 0.000148 | PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED |
| BOTTOM_SWITCH | N1.switch_body | A | MODERATE | 0.583459 | 1.223685 | COARSE PACKAGING EVIDENCE |
| BOTTOM_SWITCH | N1.T1 | A | SMALL | 0.214096 | 0.027608 | PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED |
| BOTTOM_SWITCH | N1.T2 | A | MODERATE | 0.915360 | 1.170467 | COARSE PACKAGING EVIDENCE |
| SHAFT | local_shell.JaD | A | SMALL | 0.005035 | 5.275598 | PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED |
| SHAFT | local_shell.JfD | A | SMALL | 0.005035 | 6.548519 | PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED |
| REMOVABLE_KNOB | local_shell.JaD | B | GROSS | 3.618825 | 205.622099 | COARSE PACKAGING EVIDENCE |
| REMOVABLE_KNOB | local_shell.JfD | B | GROSS | 3.637957 | 216.485863 | COARSE PACKAGING EVIDENCE |
| HEADER_PLASTIC | local_shell.JaD | C | GROSS | 2.600000 | 18.139294 | COARSE PACKAGING EVIDENCE |
| HEADER_PLASTIC | local_shell.JfD | C | GROSS | 2.600000 | 51.767565 | COARSE PACKAGING EVIDENCE |

`overlapDepthProxyMm`는 common solid를 SZH local U/V/axis로 투영한 최소 span이다. mm³만으로 severity를 정하지 않았다. **0.5 mm 미만 collision/clearance는 모두 `PROVISIONAL — ACTUAL PART MEASUREMENT REQUIRED`**이며 frozen Finger/Thumb 수정 근거가 아니다.

## 6. Stock vs direct-solder/trim what-if

- CONFIG A stock: header insulator와 full distal pin length 유지. 결과 **HOLD**.
- CONFIG B direct-solder/trim proxy: PCB-side 3.15 mm electrical root/pad envelope 유지, header plastic과 distal pin portion만 audit proxy에서 제외. 결과 **HOLD**.
- 실제 header depopulation, pad 열손상, pull strength, strain relief는 실물 테스트 전 **CONDITIONAL**이다.
- production joystick geometry에는 어떤 trim도 적용하지 않았다.

## 7. N1/N2 wiring departure

각 active terminal 뒤에 Ø1.6 mm solder envelope, 1.3 mm wire, 7 mm initial bend envelope를 배치했다. N1은 T1/T2/T3/T4, N2는 T1/T3만 사용했다.

| button | route | stock status | stock min mm | direct/trim status | direct/trim min mm |
|---|---|---|---:|---|---:|
| N1 | direct_rear | BLOCKED | 0.000000 | BLOCKED | 0.000000 |
| N1 | side | BLOCKED | 0.000000 | BLOCKED | 0.000000 |
| N1 | shell_wall_following | BLOCKED | 0.000000 | BLOCKED | 0.000000 |
| N2 | direct_rear | TIGHT | 0.280625 | BLOCKED | 0.000000 |
| N2 | side | BLOCKED | 0.000000 | BLOCKED | 0.000000 |
| N2 | shell_wall_following | BLOCKED | 0.000000 | BLOCKED | 0.000000 |

이 형상은 공간 probe일 뿐 production wire/channel이 아니다. 최종 route는 actual module envelope, 실제 AWG/피복, 납땜 fillet 측정 후 확정한다.

장착면을 맞춘 축 방향 sensitivity에서도 N1 최선 route는 **BLOCKED**, N2는 **BLOCKED**다. 따라서 header trim만으로는 final wiring space가 확보되지 않는다.

## 8. Moving envelope

25° all-azimuth conservative sweep 결과는 **HOLD**다. 충돌 수는 **2**개다. 이 sweep 자체가 web-inferred이므로 collision이 없더라도 final PASS로 승격하지 않는다. Center / ±X / ±Y 실물 max-travel 측정이 필요하다.

## 9. Reuse and final verdict

Original Thumb 20부품 중 기존 8 caps + 8 PushBtn + Small joystick attachment + Backplate/shell-side adaptation을 유지하는 기존 산식으로 **18/20 = 90.0%**다. HW504 두 exact solids만 SZH candidate/adapter 검토 대상으로 바뀐다.

**ARCHITECTURE WITH SZH-EK056 = NEEDS LOCAL INTERNAL ADAPTATION**

해석: opening center, 외부 형상, 8-button Finger baseline은 유지 가능하지만, web reference만으로 direct mounting과 sub-0.5 mm clearance를 확정할 수 없다. 필요한 다음 입력은 actual SZH-EK056 실물 치수/최대 가동 envelope다.

## 10. Outputs and stop gate

- lightweight JSON: `build123d_workbench\out\szh_ek056_provisional_thumb_integration_audit\szh_ek056_provisional_thumb_integration_audit.json`
- renders: `renders\szh_ek056_provisional_thumb_integration_audit` (11 PNG)
- production STEP / STL / full assembly: **없음**

**STOP. N1/N2 재설계, Thumb production adapter, final wire channel, fastening, MCU placement으로 진행하지 않는다.**
