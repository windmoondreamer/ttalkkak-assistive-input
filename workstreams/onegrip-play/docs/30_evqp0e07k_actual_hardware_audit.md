# Panasonic EVQP0E07K actual-hardware physical-fit audit

- 감사일: 2026-08-20
- 실제 switch source of truth: **Panasonic EVQP0E07K**
- 동결 기준: **INDEX_FINAL_VALIDATED** (`03ede76e83b5c865d9a69c35`), `configuration=default`
- 실행 모드: **READ-ONLY / Onshape CAD WRITE 0건**
- 최종 판정: **INDEX AS-IS = FAIL / INDEX MODIFICATION REQUIRED = YES / MIDDLE CAD WRITE = HOLD**

## 0. 범위와 source integrity

이번 감사에서는 기존 `6 x 6 x 6 mm` OBB를 설계용 proxy로만 취급하고 실제 부품 판정에서
제외했다. 공식 source는 다음과 같다.

- [Panasonic EVQP0E07K 제품 페이지](https://industry.panasonic.com/ap/en/products/control/switch/light-touch/number/evqp0e07k)
- [Panasonic EVQP0 Over Travel 공식 도면/카탈로그, ANCTB36E 202507](https://mediap.industry.panasonic.eu/assets/imported/industrial.panasonic.com/ac/cdn/e/control/switch/light-touch/catalog/sw_lt_eng_over.pdf)
- 로컬 보존본: [`references/hardware/Panasonic_EVQP0_Over_Travel_ANCTB36E_202507.pdf`](../references/hardware/Panasonic_EVQP0_Over_Travel_ANCTB36E_202507.pdf)
- [Panasonic 공식 CAD 검색 결과](https://industry.panasonic.com/ap/en/downloads?part_no=EVQP0E07K&small_g_cd=203&tab=cad)

공식 CAD 검색에는 `evqp0-de-07k`, `3D CAD (STEP)`, 적용 부품 `EVQP0D07K / EVQP0E07K`가
존재한다. 그러나 다운로드가 이메일·성명·회사·전화번호·거주지와 개인정보 동의를 요구하므로
사용자 개인정보를 임의 입력하지 않았고 STEP은 내려받지 않았다. 따라서 이번 terminal 검사는
공식 2D 도면의 최대 envelope를 사용한다. 제3자 `PushBtn.SLDPRT`는 사용하지 않았다.

Panasonic은 구매 전에 최신 기술 사양을 확인하라고 도면에 명시한다. 아래 결과는 확보한
2025-07 공식 도면 기준이다.

## A. Official EVQP0E07K dimensions

| 항목 | 공식 값 | 이번 감사 적용 |
|---|---:|---:|
| body X/Y | `6.2 +/- 0.1 mm` | nominal 6.2 / maximum 6.3 |
| body height excluding push plate | `6.7 mm` | nominal 6.7 / conservative maximum 6.9 |
| free-position overall height | `Max. 7.45 mm` | maximum free height 7.45 |
| operating position | `7.0 +/- 0.2 mm` | 별도 stroke datum으로 유지 |
| actuator top | `diameter 3.0 mm`, side width 2.5 mm | nominal diameter 3.0 |
| general dimension tolerance | `+/- 0.2 mm` | 별도 공차 없는 6.7/3.0 치수에 보수 적용 |
| operating direction | top push | switch axis 방향 |
| operating force | max 0.74 N | force source of truth |
| operating life | 5,000,000 cycles | 참고 |

`6.9 mm` body height는 도면 하단의 general tolerance를 별도 공차가 붙지 않은 `6.7 mm`에
적용한 보수 envelope다. actuator projection은 독립 치수로 주어지지 않는다. nominal body top을
기준으로 한 파생 최대값은 `7.45 - 6.7 = 0.75 mm`이고, operating-position 파생 nominal은
`7.0 - 6.7 = 0.30 mm`다. 이 두 파생값을 독립 exact tolerance처럼 사용하지 않았다.

## B. Terminal dimensions

| 항목 | 공식 값 |
|---|---:|
| terminal 수 | 2, DIP / through-hole |
| terminal center pitch | `5.08 +/- 0.20 mm` |
| body mounting datum 아래 projection | `3.5 +/- 0.2 mm` |
| terminal section 1 | `0.8 +/- 0.1 mm` |
| terminal section 2 | `0.3 +/- 0.1 mm` |
| formed shoulder height | `1.8 mm` |
| formed offset | `0.75 mm` |
| body-side detail | `0.9 mm`, `Max. 0.3 mm` |
| reference PWB holes | `2 x diameter 1.00 +/- 0.05 mm` |
| reference PWB hole pitch | `5.0 +/- 0.1 mm` |

최악 envelope에는 pitch `5.28 mm`, section `0.9 x 0.4 mm`, projection `3.7 mm`를 썼다.
도면의 굽힘 형상을 직육면체 pin envelope로 보수 단순화했으며, STEP 없이 보이지 않는 내부
형상을 만들지 않았다.

## C. Actuator / travel

| 항목 | 공식 값 |
|---|---:|
| actuator | top push, nominal `diameter 3.0 mm` |
| pre-travel | max `0.5 mm` |
| movement differential | max `0.12 mm` |
| over-travel | min `0.2 mm` |
| returning force | min `0.1 N` |

현재 `4.5 mm` stem bore는 FeatureScript상 원형이 아니라 **4.5 x 4.5 mm square bore**다.
actuator가 bore와 동축이면 nominal lateral clearance는 `(4.5 - 3.0)/2 = 0.75 mm/side`,
actuator에 general `+0.2 mm`를 적용해도 `0.65 mm/side`다. 따라서 bore 자체는 PASS다.

그러나 현재 INDEX cap은 `7.6 x 7.6 x 4.0 mm` 단순 cuboid다. 각 cap volume도 정확히
`231.04 mm3 = 7.6 x 7.6 x 4.0`이고, 후면 stem/plunger가 없다. cap underside는 cap-normal
depth `2.6 mm`, holder front trim은 `2.8 mm`라 cap은 holder에 닿기 전 **0.2 mm**만 움직인다.

공식 최대 free height 7.45를 써서 actuator를 가능한 한 cap에 가깝게 놓아도 flat-cap underside와
actuator 사이 최소 간격은 다음과 같다.

| Button | cap normal - switch axis | 최소 free gap | holder stop 전 cap travel | first-contact shortfall | PT max까지 필요한 총 travel | OT min 포함 총 travel |
|---|---:|---:|---:|---:|---:|---:|
| I1 | 17.2059 deg | 1.7464 | 0.2000 | **1.5464** | 2.2698 | 2.4792 |
| I2 | 17.2059 deg | 1.7464 | 0.2000 | **1.5464** | 2.2698 | 2.4792 |
| I3 | 17.2059 deg | 1.7464 | 0.2000 | **1.5464** | 2.2698 | 2.4792 |
| I4 | 2.6572 deg | 1.9451 | 0.2000 | **1.7451** | 2.4456 | 2.6459 |

결론은 상시 과압이 아니라 **접촉 자체가 되지 않는 insufficient press**다. bore PASS가 cap/actuation
PASS를 의미하지 않는다. cap plunger와 hard stop을 실제 free/operating/over-travel에 맞춰 새로
정의해야 한다.

## D. Current 6.4 pocket nominal clearance

```
(6.4 - 6.2) / 2 = 0.10 mm/side
```

네 INDEX pocket 모두 nominal arithmetic fit은 성립한다. body front datum `5.3 mm`는 유지되고,
6.3 mm maximum body 기준 front-lip minimum도 I1/I2/I3/I4 각각
`1.0142 / 1.2430 / 1.2455 / 2.3100 mm`라 front seating lip은 남는다.

## E. Worst-case pocket clearance

```
(6.4 - 6.3) / 2 = 0.05 mm/side
```

P1S 공식 자료는 기본 nozzle이 0.4 mm임은 명시하지만 완성된 내부 pocket의 보편적 치수 공차를
보증하지 않는다. [Bambu Lab P1S 공식 사양](https://us.store.bambulab.com/collections/3d-printer/products/p1s)
상에도 특정 소재·방향·slicer 설정을 아우르는 hole/pocket tolerance가 없다. 따라서 0.05 mm/side를
`P1S에서 탈착 가능`으로 인증할 수 없다. 같은 소재·방향·설정의 6.4/6.5/6.6/6.7 gauge coupon과
실물 switch 측정 없이는 6.4를 service fit으로 승인하지 않는다.

| pocket | nominal per side | 6.3 body worst per side | frozen INDEX min divider | frozen INDEX min split-side wall |
|---:|---:|---:|---:|---:|
| 6.4 | 0.10 | **0.05** | 0.8000 | 1.4301 |
| 6.5 | 0.15 | 0.10 | 0.6628 | 1.3803 |
| 6.6 | 0.20 | 0.15 | 0.5255 | 1.3304 |
| 6.7 | 0.25 | **0.20** | 0.3883 | 1.2805 |

6.7은 `maximum body 6.3 + established service clearance 0.2/side`를 보존하는 치수지만, frozen
INDEX에 폭만 올리면 I1-I2/I2-I3 divider를 크게 훼손한다. 따라서 INDEX의 `6.4 -> 6.7` 단순
parameter bump는 금지다.

## F. INDEX I1 fit

- body/pocket: nominal 0.10, worst 0.05 mm/side; arithmetic fit, P1S service fit 미인증.
- front lip at 6.3 body: 1.0142 mm, PASS.
- nearest body SAT: I1-I2 nominal 1.0738, worst 0.9369 mm; 충돌은 아니나 기존 1.20 mm robustness gate FAIL.
- rear: body rear nominal/worst 12.0/12.2 mm, holder rear 12.5 mm; rear land 0.5/0.3 mm.
- retainer: 실제 body가 RWID pad와 충돌.
- terminal: 0..179 deg 도면-envelope sweep에서 collision-free rotation 0개; 최소 두 terminal prism이 RWID/JfD envelope와 충돌.
- cap: actuator first-contact shortfall 1.5464 mm; actuation FAIL.
- worst body-to-screw-B clearance: 6.6494 mm, PASS.

## G. INDEX I2 fit

- body/pocket: nominal 0.10, worst 0.05 mm/side; arithmetic fit, P1S service fit 미인증.
- front lip at 6.3 body: 1.2430 mm, PASS.
- I1/I3 양쪽이 지배 pair다: nominal minimum 1.0745 mm, worst 0.9372 mm; 충돌은 아니나 1.20 gate FAIL.
- retainer: 실제 body가 RWID pad와 충돌.
- terminal: 180개 회전 표본 모두 FAIL; 최소 두 terminal prism 충돌.
- cap: actuator first-contact shortfall 1.5464 mm; actuation FAIL.
- worst body-to-screw-B clearance: 5.0753 mm, PASS.

## H. INDEX I3 fit

- body/pocket: nominal 0.10, worst 0.05 mm/side; arithmetic fit, P1S service fit 미인증.
- front lip at 6.3 body: 1.2455 mm, PASS.
- I2-I3 nominal/worst SAT 1.0745/0.9372 mm; I3-I4는 3.6655/3.5467 mm.
- retainer: 실제 body가 RWID pad와 충돌.
- terminal: 180개 회전 표본 모두 FAIL; 최소 두 terminal prism 충돌.
- cap: actuator first-contact shortfall 1.5464 mm; actuation FAIL.
- worst body-to-screw-B clearance: 7.7531 mm, PASS.

## I. INDEX I4 fit

- body/pocket: nominal 0.10, worst 0.05 mm/side; arithmetic fit, P1S service fit 미인증.
- front lip at 6.3 body: 2.3100 mm, PASS.
- I3-I4 nominal/worst SAT 3.6655/3.5467 mm, body-neighbor PASS.
- retainer: 실제 body가 RZKD pad와 충돌.
- terminal: 180개 회전 표본 모두 FAIL; 어느 회전에서도 최소 한 terminal prism이 JaD/RWID/RZKD 중 하나와 충돌.
- cap: actuator first-contact shortfall 1.7451 mm; actuation FAIL.
- worst body-to-screw-B clearance: 5.3209 mm, PASS.

## J. Actual-SKU INDEX SAT

동일 center, 동일 F2 axes, 동일 full 15-axis OBB SAT를 썼다.

| envelope | I1-I2 | I2-I3 | I1-I3 | I3-I4 | minimum |
|---|---:|---:|---:|---:|---:|
| legacy 6 x 6 x 6 proxy | 1.3476 | 1.3490 | 4.6697 | 3.9314 | **1.3476** |
| EVQP nominal 6.2 x 6.2 x 6.7 | 1.0738 | 1.0745 | 3.9311 | 3.6655 | **1.0738** |
| conservative 6.3 x 6.3 x 6.9 | 0.9369 | 0.9372 | 3.6863 | 3.5467 | **0.9369** |

body-body collision은 없다. 하지만 nominal과 worst 모두 기존 `SAT >= 1.20 mm` robustness gate를
I1-I2/I2-I3에서 통과하지 못한다. 과거 1.3476 mm를 실제 SKU 값으로 재사용할 수 없다.

## K. INDEX retainer / preload impact

현재 공용 RWID와 I4 RZKD는 모두 proxy rear `11.3 mm`를 기준으로 pad front를
`11.3 - 0.15 = 11.15 mm`에 둔다.

| 항목 | nominal body | conservative max body |
|---|---:|---:|
| actual switch rear | 12.00 | 12.20 |
| holder rear | 12.50 | 12.50 |
| rear land | 0.50 | 0.30 |
| current pad front | 11.15 | 11.15 |
| current body-pad overlap | **0.85** | **1.05** |
| 0.15 preload용 pad front | 11.85 | 12.05 |

RWID는 I1/I2/I3 body와, RZKD는 I4 body와 실제 mesh-envelope 교차가 확인된다. retainer 나사를
정상 위치까지 체결할 수 없으므로 기존 preload/service PASS는 무효다. 6.7 nominal만 따라 pad
front를 0.70 mm rearward 이동하면 I4의 단순 축방향 disengagement 요구량은 기존 1.35에서
0.65 mm로 줄지만, body 높이 공차 0.4 mm peak-to-peak를 rigid pad 하나가 동시에 흡수하지 못한다.
compliant pad, spring, shim 또는 measured-select 조립 정의가 필요하다.

body 자체의 screw-B clearance는 worst에서도 최소 5.0753 mm라 screw B가 직접 병목은 아니다.
다만 pad/terminal relief가 바뀐 뒤 RWID service sweep과 RZKD service path를 다시 검증해야 한다.

## L. INDEX terminal / wiring impact

terminal rear tip datum은 다음과 같다.

```
nominal: 5.3 + 6.7 + 3.5 = 15.5 mm
worst:   5.3 + 6.9 + 3.7 = 15.9 mm
holder rear: 12.5 mm
projection beyond holder rear: 3.0 nominal / 3.4 worst
```

공용 slot은 depth 12.5..14.0 mm의 1.5 mm cut이고 한쪽 edge 방향이며, 실제 terminal은 worst
15.9 mm까지 간다. 두 terminal center는 worst `+/-2.64 mm`라 central 3.6 mm pad와 별개로
**두 pin 전용 통로**가 필요하다. I4 notch도 한쪽 edge-open 구조라 두 terminal을 모두 보장하지
않는다.

공식 최대 terminal envelope를 switch axis 주위로 1 deg 간격 180회 회전시켜 frozen
JaD/JfD/RWID/RZKD mesh와 검사했다. I1/I2/I3은 collision-free rotation 0, I4도 0이다. 따라서
terminal relief 없이 실제 부품을 삽입할 수 없다.

solder fillet, wire gauge, insulation OD, bend radius, strain relief는 Panasonic 부품 도면에 정의되지
않으며 wiring BOM도 아직 없다. terminal 자체가 이미 FAIL이므로 solder/wire는 추가 수치를
추측하지 않고 **NOT VERIFIED / HOLD**로 둔다.

## M. MIDDLE best row displacement

actual nominal `6.2 x 6.2 x 6.7`, pocket `6.7`, holder width `12.7`, front lip 2.3을 대상으로
기록된 bounded center/free-axis search에서 얻은 **best nominal certified candidate**는 다음이다.

```
row translation = (+1.25, +5.25, -7.45) mm
translation norm = 9.199320627 mm
maximum individual displacement = 12.486443 mm (M2)
nearest smaller tested failure norm = 9.094361 mm
holder rear nominal = 13.20 mm
holder rear for 6.9 worst body + 1.2 rear land = 13.40 mm
```

| Button | center X/Y/Z | optimized axis X/Y/Z |
|---|---|---|
| M1 | -19.761163 / +1.772271 / -13.450000 | -0.811000 / -0.551510 / -0.195233 |
| M2 | -13.352299 / -6.897458 / -16.250000 | -0.642550 / -0.752005 / -0.147033 |
| M3 | -3.824834 / -12.691743 / -13.450000 | +0.327648 / -0.702131 / -0.632186 |
| M4 | +7.371680 / -11.851408 / -13.450000 | +0.178538 / -0.811689 / -0.556134 |

최대 local-normal deviation은 26.5292 deg다. `best`는 기록된 bounded search의 최선이며 연속
전역최적 증명은 아니다.

## N. MIDDLE SAT

| 항목 | nominal 6.2 x 6.2 x 6.7 | same axes, worst 6.3 x 6.3 x 6.9 | gate |
|---|---:|---:|---:|
| minimum body SAT | **1.4261** | **1.3071** | >=1.20 PASS |
| minimum pocket divider | 0.8310 | 0.8310 | >=0.80 PASS |
| minimum split wall | 1.5215 | **1.4858** | >=1.50: worst FAIL |
| minimum actual front lip | 0.5132 | **0.4901** | >=0.50: worst FAIL |
| minimum screw clearance | 3.1243 | 3.0007 | >=2.50 PASS |

nominal geometry는 PASS다. 동일 axes에 conservative tolerance envelope를 적용하면 body SAT는
여전히 PASS지만 split wall과 front lip이 각각 0.0142/0.0099 mm 부족하다. worst envelope를
직접 넣은 추가 axis search에서도 norm 9.199/9.444/9.760 범위에서 compatible four-axis 조합을
인증하지 못했다. 이는 불가능 증명이 아니라 **tolerance-robust candidate 미확정**이다.

## O. MIDDLE - frozen INDEX clearance

nominal 후보의 exact triangle-to-OBB 결과:

- minimum holder-to-frozen-INDEX clearance: **0.853578 mm**, M4 holder vs frozen shell
- INDEX/RWID/RZKD intersection count: **0**
- conservative all-rotation terminal bundle vs frozen INDEX minimum: **4.915406 mm** (M3 vs RWID)
- neighboring terminal-bundle minimum SAT: **0.448911 mm**, collision 없음

따라서 MIDDLE의 terminal envelope가 frozen INDEX를 직접 침범하는 것이 현재 병목은 아니다.
하지만 MIDDLE 자체 holder rear land 12.2..13.4 mm에는 두 terminal pass-through가 필요하고,
worst terminal tip 15.9 mm 뒤쪽의 solder/wire bend 공간을 별도로 설계해야 한다.

## P. Recommended pocket width

**권장 기계 치수 기준은 6.7 x 6.7 mm**다.

근거는 `maximum body 6.3 + 2 x 0.20 service clearance = 6.7 mm`다. P1S의 실제 소재·방향·설정에
대해서는 반드시 coupon으로 확인한다. 6.6은 worst 0.15 mm/side, 6.5는 0.10, 6.4는 0.05다.

- MIDDLE: 6.7 pocket 기준 nominal optimized divider 0.8310 mm라 candidate가 성립한다.
- frozen INDEX: 6.7로 폭만 키우면 divider 0.3883 mm가 되어 허용할 수 없다.
- INDEX 대안: holder/axis 구조를 함께 재설계하거나, 6.4/6.5 coupon 결과에 따라 controlled
  post-process와 go/no-go gauge를 공정으로 정의한다. 무검증 6.4 direct print는 승인하지 않는다.

## Q. INDEX modification required YES / NO

### **YES**

그러나 범위는 `작은 pocket/retainer 수정`만이 아니다.

1. service-fit pocket 또는 제조 후가공 공정
2. 실제 6.7/6.9 body에 맞는 compliant rear retention
3. 두 DIP terminal용 통로와 solder/wire strain-relief 공간
4. 실제 actuator에 닿는 cap plunger와 free/PT/OT hard stops
5. actual-SKU I1-I2/I2-I3 robustness 재검증

현재 INDEX_FINAL_VALIDATED의 기능적 동결 상태를 깨지 않고는 EVQP0E07K를 정상 작동시킬 수 없다.
이번 감사에서는 그 어떤 CAD feature도 수정하지 않았다.

## R. MIDDLE modification strategy

1. EVQP0E07K를 유지한다. 현재 결과만으로 다른 switch 또는 low-profile 전용 SKU가 필요하다는
   근거는 없다.
2. 기본 pocket은 6.7, holder outer width는 12.7, worst-case rear datum은 최소 13.4에서 시작한다.
3. nominal candidate `(1.25, 5.25, -7.45)`를 seed로 쓰되 6.3 x 6.3 x 6.9 worst envelope에서
   split >=1.50, actual lip >=0.50을 동시에 만족하도록 center/axis를 다시 푼다.
4. terminal pair는 pitch 5.28 worst, section 0.9 x 0.4, depth 12.2..15.9를 keep-out으로 둔다.
   rear land에는 twin through-slots를 만들고 retainer는 terminal/solder 영역을 덮지 않게 한다.
5. cap은 flat cuboid를 복사하지 않고 actuator-axis contact plunger, PT 0.5 max, OT 0.2 min,
   body hard-stop을 함께 설계한다.
6. wire gauge, insulation OD, solder method, bend radius를 BOM에서 확정한 뒤 마지막 wiring sweep을 한다.

docs/29의 `low-profile 전용 SKU 불필요` 결론은 유지한다. 다만 6 x 6 x 6 proxy branch를 actual
EVQP0E07K CAD WRITE에 재사용하지 않는다.

## S. CAD WRITE GO / HOLD

### **CAD WRITE = HOLD**

HOLD 사유:

1. INDEX current 6.4 pocket은 worst 0.05 mm/side라 P1S removable fit 미인증.
2. actual body가 RWID/RZKD pad와 0.85 nominal / 1.05 worst 겹친다.
3. 실제 DIP terminals의 collision-free INDEX orientation이 없다.
4. flat INDEX caps는 actuator에 닿기 전에 holder front에 멈춘다.
5. actual INDEX SAT가 기존 1.20 robustness gate를 통과하지 못한다.
6. MIDDLE nominal candidate는 있으나 worst tolerance split/lip gate가 아직 미확정이다.
7. solder/wire envelope가 BOM에 없다.

## A-S decision summary

| Decision | 결과 |
|---|---|
| A. INDEX current geometry 그대로 사용 | **NO** |
| B. INDEX 수정 | **YES; pocket/retainer뿐 아니라 cap/terminal relief 필요** |
| C. MIDDLE EVQP0E07K 사용 | **nominal geometry 가능, tolerance-robust design 미확정** |
| D. MIDDLE 다른 switch 필요 | **NO — 현재 근거 없음** |
| INDEX modification required | **YES** |
| MIDDLE strategy | EVQP0E07K 유지 + worst-envelope 재최적화 + terminal/cap-aware architecture |
| CAD WRITE | **HOLD** |

## Reproducibility

- 계산 데이터: [`cad_dump/evqp0e07k_actual_hardware_audit.json`](../cad_dump/evqp0e07k_actual_hardware_audit.json)
- local GET-free 계산 스크립트: [`scripts/audit_evqp0e07k_hardware.py`](../scripts/audit_evqp0e07k_hardware.py)
- frozen inventory 근거: [`cad_dump/index_final_body_inventory_audit.json`](../cad_dump/index_final_body_inventory_audit.json)

스크립트는 로컬 tessellation과 수치 계산만 사용하며 HTTP client와 Onshape mutation path가 없다.
