# 32. ITS-1105-6mm primary finger-switch design audit

- 일자: 2026-08-20
- project primary switch: **ITS-1105-6mm**
- purchased quantity: **20**
- frozen CAD: `INDEX_FINAL_VALIDATED` / `03ede76e83b5c865d9a69c35`
- configuration: `default` frozen cache
- 실행: **READ-ONLY / Onshape CAD WRITE 0 / MIDDLE geometry 생성 0**
- 결론: **INDEX GRADE 1 / CASE B / NEXT CAD WRITE HOLD**

사용자가 제공한 ITS-1105 계열 drawing의 `L=6.0` variant를 mechanical reference로 사용했다. 판매처
nominal보다 실제 보유 lot 캘리퍼 측정값이 최종 CAD parameter에서 우선한다. 이번 계산은 drawing-derived
값과 physical-lot pending 값을 섞지 않았다.

이 문서는 `docs/31`의 Grade 2를 **Grade 1로 정정·후속 대체**한다. `docs/31`은 own-holder relief와
moving pad extension만 평가했지만, 이번에는 네 버튼 channel roll을 동시에 풀고 retainer와 함께 움직이지
않는 separate shim을 평가했다. 그 결과 center/axis/seat architecture를 바꾸지 않고 1.50 mm web을
보존하는 coordinated local-channel 해가 확인됐다.

---

## A. ITS-1105-6mm source-of-truth geometry

| 구역 | drawing-derived nominal |
|---|---:|
| body footprint | 6.0 × 6.0 mm |
| housing/lower-base envelope | 3.6 mm |
| overall `L` | 6.0 mm |
| actuator projection | 2.4 mm |
| actuator | Ø3.5 mm |
| travel | 0.25 ±0.10 mm |
| terminal | 4-pin THT |
| terminal pattern | 6.5 ±0.2 × 4.5 ±0.2 mm |
| terminal metal | 약 0.3 × 0.7 mm |
| body 후면 이후 terminal | 3.5 mm |
| no-bend fixed-root depth | 1.8 mm |
| terminal maximum outer width | 7.9 ±0.3 mm |

`L=6.0`은 actuator top에서 body rear까지의 전체 높이다. body/base의 세부 단차는 완전 치수화되지
않았으므로 6×6×3.6 housing envelope로 보수 처리했다. body 출구부터 1.8 mm factory-formed 구간은
FIXED ROOT, 나머지 약 1.7 mm는 BENDABLE DISTAL로 분리했다.

## B. drawing uncertainty

- 일반공차: ±0.3 mm, 별도 공차가 있는 6.5/4.5 pin pattern은 ±0.2 mm 우선
- drawing-worst body: 6.3×6.3×3.9 mm
- drawing-worst terminal outer width: 8.2 mm
- drawing-worst와 실제 보유 lot worst는 같지 않음
- bend radius가 없으므로 공식 최소값을 만들지 않고 prototype assumption으로 남김

`L`/housing-height 독립 stack은 cap free gap을 preload부터 미접촉까지 넓게 만들 수 있다. actual lot
측정 전에는 nominal만 보고 actuation PASS를 선언하지 않는다.

## C. 6×6×6 old proxy와 차이

| datum | old proxy | ITS nominal at current front seat |
|---|---:|---:|
| front/body datum | 5.3 | 5.3 |
| actuator free top | 없음 | 2.9 |
| rigid body rear | 11.3 | **8.9** |
| fixed root | 없음 | 8.9…10.7 |
| distal terminal tip | 없음 | 12.4 |

old proxy는 body rear를 2.4 mm 뒤에 놓고 actuator와 terminal을 생략했다. 따라서 같은 “6 mm”라는
표기만으로 rear pad와 cap을 재사용할 수 없다.

## D. current 6.4 pocket nominal fit

`(6.4 - 6.0) / 2 = 0.20 mm/side`. Nominal locating fit은 기하상 성립한다.

## E. drawing worst fit

body max 6.3을 적용하면 `(6.4 - 6.3) / 2 = 0.05 mm/side`다. P1S 0.4 mm nozzle 공정에서 removable
fit으로 인증된 값이 아니다. 6.4 / 6.5 / 6.6 / 6.7 coupon을 기록만 하며 이번에는 생성하지 않았다.

## F. INDEX nominal body SAT

| pair | SAT separation |
|---|---:|
| I1-I2 | 1.443121 |
| I2-I3 | 1.348986 |
| I1-I3 | 6.661942 |
| I3-I4 | 4.158761 |
| **minimum** | **1.348986 PASS** |

center와 F2 axis는 변경하지 않았다. nominal gate `≥1.20 mm`를 통과한다.

## G. INDEX worst body SAT

| pair | SAT separation |
|---|---:|
| I1-I2 | 1.023677 |
| I2-I3 | **0.937248** |
| I1-I3 | 6.176579 |
| I3-I4 | 3.830997 |

drawing-worst는 1.20 mm gate를 실패한다. 실제 lot body X/Y가 nominal 근처인지 측정하면 해소될 수
있는 항목이지만, 측정 전 tolerance를 무시해 PASS로 바꾸지 않는다.

## H. actuator / bore result

- Ø3.5 actuator vs Ø4.5 bore: nominal radial clearance **0.50 mm**
- Ø3.8 drawing-worst actuator: radial clearance **0.35 mm**
- bore와 actuator는 동일 F2 axis: coaxial passage PASS
- cap normal과 F2 axis 편차: I1/I2/I3 17.2059°, I4 2.6572°
- cap underside contact offset: I1/I2/I3 약 0.805 mm, I4 0.121 mm로 cap 면 안에 있음

## I. cap actuation result

현재 cap underside depth는 2.6 mm, holder first stop은 2.8 mm라 available stroke는 0.20 mm다.

| | nominal free gap | 0.15 actuation까지 | nominal 0.25 | max 0.35 | 현재 stop 대비 max 부족 |
|---|---:|---:|---:|---:|---:|
| I1 | 0.170219 | 0.313506 | 0.409031 | 0.504556 | 0.304556 |
| I2 | 0.170219 | 0.313506 | 0.409030 | 0.504555 | 0.304555 |
| I3 | 0.170218 | 0.313505 | 0.409030 | 0.504555 | 0.304555 |
| I4 | 0.296882 | 0.446721 | 0.546613 | 0.646506 | 0.446506 |

현재 cap은 actuator가 최소 travel에 도달하기 전에 holder에 닿는다. Grade-1 후보는 actual measured free
gap을 닫는 `cap underside contact boss`와 local stop recess다. free gap을 0으로 가정한 이론적 recess
하한은 I1-I3 약 0.134 mm, I4 약 0.150 mm지만, 실제 설계값은 의도한 free clearance를 더해 정한다.

## J. I1 rear pad result

- ITS rear: 8.9 mm nominal
- RWID pad front: 11.15 mm
- gap: **2.25 mm**, contact 없음

## K. I2 rear pad result

- ITS rear: 8.9 mm nominal
- RWID pad front: 11.15 mm
- gap: **2.25 mm**, contact 없음

## L. I3 rear pad result

- ITS rear: 8.9 mm nominal
- RWID pad front: 11.15 mm
- gap: **2.25 mm**, contact 없음

## M. I4 rear pad result

- ITS rear: 8.9 mm nominal
- RZKD pad front: 11.15 mm
- gap: **2.25 mm**, contact 없음

moving pad를 8.75 mm까지 연장하면 shared service 요구가 2.07→4.84 mm, I4가 1.85→4.25 mm로
늘어나므로 최소안에서 제외했다. 우선안은 **retainer와 함께 움직이지 않는 중앙 rear spacer/shim**이다.

- nominal spacer length: 2.4 mm
- drawing-stack parameter range: 2.1…2.7 mm
- central contact candidate: Ø3.6 mm
- body rear 8.9 + spacer 2.4 = legacy contact rear 11.3
- current pad front 11.15와 nominal 0.15 preload 관계를 복원
- RWID/RZKD pad와 기존 service path는 변경하지 않음

shim은 retainer 제거 후 따로 빠지는 service part로 설계해야 하며 actual rear 측정 뒤 길이를 확정한다.

## N. I1 fixed-root rotation

- current holder, 0…360°: **clear range 없음 / 0개**
- terminal channel nominal seed: 174° 또는 354°
- drawing-worst robust seed: **170° 또는 350°**

## O. I2 fixed-root rotation

- current holder, 0…360°: **clear range 없음 / 0개**
- terminal channel nominal seed: 178° 또는 358°
- drawing-worst robust seed: **0° 또는 180°**

## P. I3 fixed-root rotation

- current holder, 0…360°: **clear range 없음 / 0개**
- terminal channel nominal/worst seed: **92° 또는 272°**

## Q. I4 fixed-root rotation

- current holder, 0…360°: **clear range 없음 / 0개**
- terminal channel nominal seed: 84° 또는 264°
- drawing-worst robust seed: **80° 또는 260°**

4-pin pattern은 180° 회전 대칭이므로 exact 0…179° 결과를 180…359°에 대칭 확장했다. current clear
range가 없다는 결과는 1° 해상도 전수, coordinated channel seed는 2° bounded joint search다.

## R. terminal channel requirement

필요 channel architecture:

```text
6.4 locating seat
  -> body rear부터 factory fixed-root OBB만 통과하는 4개 local channel
  -> holder rear까지 edge-open/open-rear 연결
  -> 뒤쪽에서 distal terminal 1회 성형 및 wire exit
```

| gate | nominal optimized | drawing-worst optimized |
|---|---:|---:|
| governing channel/web lower bound | **1.994452** | **1.659048** |
| required web | 1.500 | 1.500 |
| conservative symmetric clearance/channel | 0.247226 | **0.079524** |
| result at zero/allowed clearance | PASS | PASS, 매우 경계 |

worst channel extra는 6.4 seat 밖으로 측당 0.90 mm다. optimized worst rolls는 I1 170°, I2 0°,
I3 92°, I4 80°다. 이 조합에서 outer/split web과 adjacent channel SAT lower bound를 동시에 평가했다.

channel은 body seat 앞쪽을 건드리지 않으므로 existing pocket divider 0.80 mm를 유지한다. rear channel
구간의 minimum web도 1.50 mm를 넘는다. 다만 worst에서 공정 clearance가 0.08 mm/channel뿐이므로,
실측 root envelope와 printed channel coupon 없이 CAD 값으로 freeze할 수 없다.

## S. bendable terminal routing

- fixed root: nominal depth 8.9…10.7 mm, bending 금지
- bend point: factory-formed 1.8 mm 뒤에서만 허용
- distal: 약 1.7 mm, pliers로 조립 전 1회 성형
- I1 exit: local -v / RWID slot
- I2 exit: local +v / RWID slot
- I3 exit: local -v / RWID slot
- I4 exit: local -v / RZKD notch
- bend radius: `PROTOTYPE ASSUMPTION`, 공식값 미선언

도면 회로는 1-2와 3-4가 각각 common이다. direct wiring은 서로 다른 common group에서 한 핀씩
선택한다. 유효 예는 1+3, 1+4, 2+3, 2+4이며 1+2 또는 3+4는 스위칭 pair가 아니다. 네 핀은 모두
유지하고 unused pin도 절연한다. 절단은 승인하지 않는다.

## T. recommended assembly / solder sequence

| option | 판정 |
|---|---|
| 1. switch 삽입 → bend → solder | 인두/pliers 접근과 root load 때문에 비권장 |
| 2. distal pre-form → wire pre-solder/절연 → switch 삽입 | **권장** |
| 3. switch 삽입 → retainer 전 solder | channel 완성 후 조건부 가능, 공통절차로는 비권장 |

권장 공통 순서:

1. 실제 switch continuity와 pin group 확인
2. jig로 distal terminal 한 번만 pre-form
3. 서로 다른 common group의 두 핀에 wire pre-solder
4. 각 joint 절연/heat-shrink, unused terminal 절연
5. wire부터 open channel/slot으로 통과
6. switch body를 6.4 locating seat에 삽입
7. measured rear spacer 삽입
8. RWID/RZKD 체결
9. free stroke와 electrical actuation 확인

wire gauge, insulation OD, solder fillet envelope는 아직 없어 최종 solder-access PASS는 physical prototype
pending이다.

## U. INDEX modification grade

### **GRADE 1 / CASE B**

coordinated channel 계산으로 center/axis/layout이나 holder seat 전체를 바꿀 필요가 없음이 확인됐다.
Grade-1 범위는 terminal channel, separate rear shim, cap underside boss/local stop relief, tiny wire relief다.

## V. INDEX minimum modification plan

1. I1/I2/I3/I4 centers, F2 axes, openings, 6.4 locating seat를 freeze
2. actual measured root profile + `c_channel` parameter로 four local terminal channels 생성
3. robust seed roll `170° / 0° / 92° / 80°`에서 B-rep web ≥1.50 재검증
4. actual body rear 기준 non-moving central shim 길이 parameter화
5. measured actuator free height 기준 cap boss와 max-travel stop relief parameter화
6. 기존 RWID/RZKD pad, fastening, service direction은 먼저 보존
7. wire/solder envelope와 실제 조립 순서를 prototype으로 검증

이번 audit에서는 이 형상을 생성하지 않았다.

## W. MIDDLE same-switch feasibility

**YES, nominal geometry feasible / drawing-worst reoptimization pending.** 별도 low-profile switch가 필요하다는
증거는 없다.

| gate | nominal 6.0×3.6 | drawing-worst 6.3×3.9 |
|---|---:|---:|
| body SAT | 1.506315 PASS | 1.152128 FAIL |
| divider | 1.034066 PASS | 0.981542 PASS |
| split wall | 1.513915 PASS | 1.513915 PASS |
| screw | 7.682136 PASS | 7.482957 PASS |
| actual front lip | 0.500000 PASS 경계 | 0.427368 FAIL |
| frozen INDEX clearance | 0.513070 PASS | 0.456588 FAIL |
| frozen INDEX intersection | 0 | 0 |

## X. MIDDLE candidate row / axis

```text
common row Δ = (+1.500, +3.125, -5.125) mm
norm         = 6.187184 mm
per button   = 6.333 / 9.849 / 6.706 / 7.236 mm
```

| | center XYZ | candidate axis |
|---|---|---|
| M1 | `(-19.835372,-0.614992,-11.125000)` | `(-0.837519,-0.499950,-0.220481)` |
| M2 | `(-12.899418,-8.744828,-14.125000)` | `(-0.601521,-0.782846,-0.159135)` |
| M3 | `(-3.537874,-14.413709,-11.125000)` | `(+0.320429,-0.733473,-0.599452)` |
| M4 | `(+7.444328,-13.569623,-11.125000)` | `(+0.224859,-0.772793,-0.593489)` |

이는 CAD 승인이나 ergonomic 승인값이 아니라 actual-ITS rerun seed다.

## Y. MIDDLE terminal feasibility

- future holder는 처음부터 fixed-root four-channel과 open rear solder cavity를 포함해야 함
- local 0° seed의 frozen INDEX/RWID/RZKD root collision: 0
- external clear rotations nominal: M1 180 / M2 150 / M3 180 / M4 180, 각 180
- drawing-worst: M1 180 / M2 110 / M3 180 / M4 180, 각 180
- root-pair SAT: nominal min 0.264974, worst min 0.128496 mm

terminal implementation은 조건부 가능하지만 worst pair gap이 작아 MIDDLE channel/roll은 새 holder와 함께
재최적화해야 한다.

## Z. INDEX + MIDDLE same SKU

### **YES - ITS-1105-6mm를 공통 primary로 유지**

INDEX는 Grade-1 local modification, MIDDLE은 nominal candidate와 terminal-aware 신규 holder로 진행할 수
있다. physical-lot 측정과 worst-envelope rerun 전 production approval은 아니다.

## AA. EVQP0E07K finger primary exclusion

```text
FINGER_BUTTON_PRIMARY = false
```

EVQP0E07K에 맞춰 INDEX geometry를 재설계하지 않는다. EVQ는 여분 또는 다른 입력부 후보로만 남긴다.

## AB. physical measurements required before WRITE

Registry 파일은 이번 실행에서 수정하지 않았으며 다음 plan만 확정한다.

```text
PART:   ITS-1105-6mm
ROLE:   INDEX + MIDDLE PRIMARY FINGER SWITCH
STATUS: SELECTED / PHYSICAL LOT MEASUREMENT PENDING
QTY:    20
```

`MEASURE-02` 추가 항목:

- body X / body Y
- housing height / overall L
- actuator diameter / actuator projection
- fixed-root 시작점·factory profile·최대 외폭
- pin spacing / pin width / pin thickness
- 선택 표본의 free-position과 실제 actuation stroke

각 치수는 최소 여러 개 표본의 min/nominal/max를 기록하고, channel과 shim/cap parameter를 그 값으로
override한다.

## AC. NEXT CAD WRITE

### **HOLD**

CASE B의 최소 수정 경로는 확정했지만 다음 조건이 남았다.

1. actual lot body/root/actuator measurement 없음
2. drawing-worst channel clearance allowance가 0.080 mm/channel로 경계
3. pocket coupon과 terminal-channel coupon 미실시
4. wire gauge/insulation/solder envelope 미정
5. MIDDLE drawing-worst SAT/front-lip/INDEX robust clearance 미통과
6. 사용자의 명시적 CAD WRITE 승인 전

INDEX_FINAL_VALIDATED는 계속 freeze한다.

---

## 재현 파일

- `cad_dump/its1105_primary_switch_design_audit.json`
- `cad_dump/stock_6x6x6_switch_actual_fit_audit.json`
- `scripts/audit_its1105_primary_switch.py`
- `scripts/audit_stock_6x6_switch.py`

모든 계산은 frozen local tessellation과 analytic OBB/SAT를 사용했다. Onshape mutation path는 없다.
