# OneGrip Play — Finger Controls V2 Physical Validation Kit

## 1. Scope and status

이 문서는 Finger Controls V2의 **FDM 현물 검증용 로컬 build123d 키트**를 기록한다.

- Onshape read/write: **0건**
- production Finger V2 geometry/parameter 변경: **0건**
- source: 검증 완료된 production STEP/STL을 read-only reference로 사용
- digital printability: **PASS**
- physical validation kit: **READY**
- physical Finger V2: **NOT YET VALIDATED**
- production Finger V2 freeze: **PENDING USER FDM RESULTS**

`DIGITAL PRINTABILITY PASS`는 형상 유효성, 간섭, 운동 범위, STL 유한성 및 배치 검사를 통과했다는 뜻이다. 실제 프린터의 수축, elephant foot, 압출 편차, 표면 거칠기와 조립 감각은 포함하지 않는다.

## 2. Production baseline protection

검증 키트는 `build123d_workbench/out/finger_controls_v2/`의 production 산출물을 불러와 별도 폴더에 파생 생성한다. production 파일과 설계 파라미터를 덮어쓰지 않는다.

검증 gate:

- production source PASS 유지
- production parameter unmodified
- 최종 키트 형상 valid solid
- unexpected fragment 0
- switch pocket 내부 support-free
- cap guide 내부 support-free

## 3. Kit inventory

### Kit A — ITS-1105 pocket fit coupon

파일:

- `ITS_POCKET_FIT_COUPON.stl`
- `ITS_POCKET_FIT_COUPON.step`

한 개의 평판 위에 6.30 / 6.35 / 6.40 / 6.45 / 6.50 mm 포켓을 배치했다. 각 포켓에 치수를 양각 표기했고, production nominal인 6.40 mm에는 프레임을 추가했다.

목적:

- 실제 ITS-1105 실물의 삽입력 확인
- 프린터별 XY 치수 편차 확인
- production 치수 변경 전 가장 적절한 포켓 선택

### Kit B — I4 one-button function coupon

파일:

- `ONE_BUTTON_I4_JAD_SHELL.stl`
- `ONE_BUTTON_I4_JFD_CLOSURE.stl`
- `KIT_I4_carrier.stl`
- `KIT_I4_cap.stl`
- `ONE_BUTTON_FUNCTION_COUPON.step`
- `ONE_BUTTON_FUNCTION_COUPON.stl` — 조립 상태 visual/reference mesh

production I4 주변 외피를 실제 곡률과 개구부가 남도록 잘라 만든 최소 기능 쿠폰이다. 스위치 삽입, 캐리어 장착, 캡 이동, click, return을 가장 적은 출력량으로 확인한다.

### Kit C — N2 seam function coupon

파일:

- `N2_SEAM_JAD_SHELL.stl`
- `N2_SEAM_JFD_SHELL.stl`
- `KIT_N1_N2_shared_carrier.stl`
- `KIT_N2_cap.stl`
- `N2_SEAM_FUNCTION_COUPON.step`
- `N2_SEAM_FUNCTION_COUPON.stl` — 조립 상태 visual/reference mesh

N2 중심을 기준으로 양쪽 production shell interface를 모두 포함한다. 실제 N1/N2 shared carrier와 N2 cap을 사용해 seam closure, cap rubbing, 조립 순서와 배선 접근성을 확인한다.

### Kit D — cropped 1:1 eight-button functional section

파일:

- `FINGER_V2_SECTION_JAD_SHELL.stl`
- `FINGER_V2_SECTION_JFD_SHELL.stl`
- `KIT_*.stl` carrier 5개
- `KIT_*_cap.stl` cap 8개
- `FINGER_V2_FUNCTIONAL_SECTION.step`
- `FINGER_V2_FUNCTIONAL_SECTION.stl` — 조립 상태 visual/reference mesh

전체 하우징 대신 Finger V2의 I2, I3, I4, M3, M4, N1, N2, N3 구간만 1:1로 잘랐다. 외피 곡률, 8개 개구부, 모든 캐리어/캡, 실제 ITS-1105 envelope를 유지한다. 실제 조립에는 ITS-1105 8개가 필요하다.

## 4. Digital motion audit

모든 버튼을 production local axis 방향으로 검사했다.

| Button | REST | PARTIAL | FULL | shell / carrier / housing / adjacent-cap intersection |
|---|---:|---:|---:|---:|
| I2 | 0.000 mm | 0.175 mm | 0.350 mm | 0 mm³ |
| I3 | 0.000 mm | 0.175 mm | 0.350 mm | 0 mm³ |
| I4 | 0.000 mm | 0.175 mm | 0.350 mm | 0 mm³ |
| M3 | 0.000 mm | 0.175 mm | 0.350 mm | 0 mm³ |
| M4 | 0.000 mm | 0.175 mm | 0.350 mm | 0 mm³ |
| N1 | 0.000 mm | 0.175 mm | 0.350 mm | 0 mm³ |
| N2 | 0.000 mm | 0.175 mm | 0.350 mm | 0 mm³ |
| N3 | 0.000 mm | 0.175 mm | 0.350 mm | 0 mm³ |

REST에서 스위치 액추에이터까지의 nominal pre-contact gap은 약 0.050 mm다. PARTIAL 및 FULL 상태에서는 접촉 거리 0이며 hard-body 관통은 없다. 이 결과는 형상 운동 가능성을 의미하며 출력 표면 마찰과 스위치 click 감각은 현물로 확인해야 한다.

## 5. FDM tolerance probe

분석은 가장 불리한 상관 오차인 `cavity shrink + mating part growth`를 가정한다.

### ITS pocket versus switch body

Nominal:

- pocket: 6.40 mm
- BODY_X: 6.18 mm → diametral 0.22 mm / per-side 0.11 mm
- BODY_Y: 6.12 mm → diametral 0.28 mm / per-side 0.14 mm

| Correlated error | Pocket | BODY_X / BODY_Y | X/Y diametral clearance | Result |
|---:|---:|---:|---:|---|
| ±0.00 mm | 6.40 | 6.18 / 6.12 | 0.22 / 0.28 | PASS |
| ±0.10 mm | 6.30 | 6.28 / 6.22 | 0.02 / 0.08 | MARGINAL |
| ±0.20 mm | 6.20 | 6.38 / 6.32 | -0.18 / -0.12 | INTERFERENCE |

따라서 6.40 mm는 nominal CAD에서 유효하지만 프린터 보정값 없이 production 치수로 고정할 수 없다. Kit A 결과를 먼저 사용한다.

### Cap versus opening

| Interface | Nominal diametral / per-side | ±0.10 worst | ±0.20 worst |
|---|---:|---:|---:|
| standard 8.0 / 7.6 mm | 0.40 / 0.20 | 0.20 / 0.10 PASS | 0.00 / 0.00 MARGINAL |
| N2 8.4 / 7.6 mm | 0.80 / 0.40 | 0.60 / 0.30 PASS | 0.40 / 0.20 PASS |

N2는 seam 대응 여유가 유지된다. 표준 opening은 누적 ±0.20 mm에서 nominal gap이 소진되므로 실제 rubbing 검사가 필요하다.

## 6. Printability audit

- nozzle assumption: 0.4 mm
- carrier wall: 1.6 mm
- minimum functional wall: 1.2 mm
- final plate components: 20
- plate envelope: 189.21 × 106.66 × 25.04 mm
- nominal inter-part gap: 6.0 mm
- STL triangles: 35,138
- non-finite coordinates: 0
- unexpected disconnected fragments: 0

| Validation part | Orientation | Support | Critical support / bridge / overhang | Minimum wall / feature | Primary sensitivity |
|---|---|---|---|---|---|
| Kit A fit coupon | flat base on bed, pockets vertical | NO | downward overhang 0%; open pocket tops bridge 없음 | base 2.4 mm; pocket tower wall은 후보 간 동일 | pocket lower edge elephant foot, XY hole shrink |
| Kit B I4 JaD crop | packed broad crop face on bed | YES, exterior local only | packed mesh downward overhang 약 27.65%; shell exterior crop perimeter만 지지 | production shell wall 유지; 기능부 최저 1.2 mm | opening/guide 안쪽 support 접촉 금지 |
| Kit B I4 JfD closure | broad cut face on bed | NO | downward overhang 0% | production shell wall 유지 | mating face first-layer burr |
| Kit C N2 JaD crop | broad cut face on bed | NO 또는 극소 local | downward overhang 약 0.25% | production shell wall 유지; 기능부 최저 1.2 mm | seam edge와 N2 opening |
| Kit C N2 JfD crop | broad cut face on bed | YES, exterior local only | downward overhang 약 2.85% | production shell wall 유지; 기능부 최저 1.2 mm | seam edge와 opposite-shell clearance |
| Kit D JaD shell section | packed crop face on bed | YES, exterior only | downward overhang 약 17.91% | production shell wall 유지; 기능부 최저 1.2 mm | 8개 guide/opening 내부 support 금지 |
| Kit D JfD shell section | packed crop face on bed | YES, exterior only | downward overhang 약 20.25% | production shell wall 유지; 기능부 최저 1.2 mm | carrier seat와 seam 내부 support 금지 |
| carriers 5개 | broad rear plate on bed, C-channel upward | NO 또는 local bridge only | 개별 packed overhang 약 0.13–16.35%; pocket 내부 지지 금지 | wall 1.6 mm; 기능부 최저 1.2 mm | pocket lower edge와 terminal-channel stringing |
| caps 8개 | external pad face on bed, socket upward | NO | measured downward overhang 0% | production cap/actuator feature 유지 | actuator socket elephant foot/stringing |

표의 overhang 비율은 자동 선택된 `VALIDATION_PRINT_PLATE.stl` orientation에서 STL 삼각형 면적으로 계산했다. 수치가 큰 shell crop도 support를 기능성 포켓/guide 안쪽에 넣는 허가를 의미하지 않는다. support는 잘라낸 외부 둘레에서만 허용한다.

권장 방향:

- fit coupon: 평평한 바닥을 bed에 배치, support 없음
- caps: 외부 누름면을 bed에 배치, socket가 위를 향하게, support 없음
- carriers: 넓은 rear plate를 bed에 배치, C-channel이 위, support 없음 또는 bridge 부위만 국부 적용
- shell crops: 가능한 한 opening axis를 위로 두고 절단 외곽에만 support 적용

금지:

- switch pocket 내부 support
- cap guide/opening 내부 support
- actuator socket 내부 support

Elephant-foot 민감 부위는 switch pocket 하단, cap guide/opening edge, cap actuator socket이다. 첫 층 horizontal expansion 보정을 하지 않은 상태에서는 fit coupon 결과를 우선한다.

## 7. Print and validation order

1. Kit A만 먼저 출력한다.
2. 식힌 뒤 서포트·brim 잔여물을 제거하되 포켓을 줄로 확장하지 않는다.
3. 같은 ITS-1105 샘플을 6.50부터 6.30 방향으로 시험한다.
4. 가장 작은 `손으로 삽입 가능하며 흔들림이 과하지 않은` 포켓을 기록한다.
5. Kit B를 출력해 click/return/rubbing을 확인한다.
6. Kit C로 N2 seam을 닫아 확인한다.
7. Kit A–C가 허용되면 Kit D를 출력하고 ITS-1105 8개를 장착한다.
8. 실제 터미널은 body 바로 옆 root를 비틀지 말고 distal pin만 필요 시 1회 성형한다.
9. 결과를 `docs/48_finger_v2_physical_test_sheet.md`에 기록한다.

## 8. Final gate

- **DIGITAL PRINTABILITY = PASS**
- **PHYSICAL VALIDATION KIT = READY**
- **PHYSICAL FINGER V2 = NOT YET VALIDATED**
- **PRODUCTION FINGER V2 FREEZE = PENDING USER FDM RESULTS**

현물 결과가 들어오기 전 production pocket, cap, opening, carrier 치수는 변경하거나 확정하지 않는다.
