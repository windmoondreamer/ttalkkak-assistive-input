# 31. 실제 보유 6×6 / L=6 tactile switch fit audit

- 일자: 2026-08-20
- frozen CAD: `INDEX_FINAL_VALIDATED` / `03ede76e83b5c865d9a69c35`
- Part Studio configuration: `default` frozen cache
- hardware source of truth: 사용자가 첨부한 4-pin 6×6 tactile switch 도면, `L=6.0` 선택 variant
- 실행 경계: **로컬 READ-ONLY audit / Onshape CAD WRITE 0건 / MIDDLE CAD 생성 0건**
- 최종 판정: **INDEX GRADE 2 / INDEX CAD modification YES / NEXT CAD WRITE HOLD**

이 문서에서 “도면 worst”는 일반공차 `±0.3 mm`를 독립적으로 쌓은 보수 envelope다. 실제 보유 lot의
실측 합격/불합격과 동일한 뜻이 아니다. 반대로 nominal PASS도 FDM pocket fit, 단자 굽힘, 납땜 열영향을
자동 승인하지 않는다.

---

## A. 실제 도면 geometry 해석

도면의 `L=6.0`은 6×6×6 solid cube의 깊이가 아니다. 액추에이터 상단부터 본체 후면까지의 전체
mechanical height다.

| 구역 | nominal 해석 |
|---|---:|
| top body footprint | 6.0 × 6.0 mm |
| body/lower-base axial envelope | 3.6 mm |
| overall height `L` | 6.0 mm |
| body 위 actuator projection | `6.0 - 3.6 = 2.4 mm` |
| actuator | Ø3.5 mm |
| travel | 0.25 ±0.10 mm, 즉 0.15…0.35 mm |
| terminal pattern | 6.5 ±0.2 × 4.5 ±0.2 mm |
| terminal metal | 약 0.3 × 0.7 mm |
| body 후면 이후 terminal 길이 | 3.5 mm |
| factory-formed 첫 구간 | 1.8 mm |
| terminal 포함 최대 외폭 | 7.9 ±0.3 mm |

도면에서 body와 lower base의 세부 단차는 별도 완전 치수화되어 있지 않으므로, 충돌 계산에는 둘을
합친 6×6×3.6 mm housing envelope를 사용했다. `1.8 mm` 구간은 사용자가 허용한 임의 distal bend
구간으로 넣지 않고, body 출구부터 최대 외폭을 만드는 공장 성형 **FIXED ROOT ZONE**으로 보수 처리했다.
나머지 `3.5 - 1.8 = 1.7 mm`만 bendable distal 후보로 보았다. 공식 최소 bend radius는 도면에 없으므로
만들어내지 않았다.

도면 회로는 `1-2`가 한 내부 공통군, `3-4`가 다른 내부 공통군이고, 누르면 두 공통군이 연결되는
normally-open 구조다.

## B. 기존 6×6×6 proxy와 차이

기존 proxy는 depth 5.3…11.3 mm의 단일 6×6×6 cuboid였다. 실제 switch를 현재 front seat에
착좌시키면 다음처럼 분리된다.

| datum | legacy proxy | 실제 nominal |
|---|---:|---:|
| body/front face | 5.3 | 5.3 |
| actuator free top | 별도 모델 없음 | 2.9 |
| body rear face | 11.3 | **8.9** |
| fixed root | 없음 | 8.9…10.7 |
| distal terminal tip | 없음 | 12.4 |

즉 overall `L=6.0`이라는 숫자는 같아도 실제 housing rear는 proxy보다 2.4 mm 앞에 있다. 기존 proxy는
actuator, 7.9 mm terminal splay, fixed root와 distal terminal을 모두 누락했고, retainer 접촉면을
실제보다 2.4 mm 뒤로 놓았다.

## C. pocket nominal clearance

현재 pocket 6.4 mm와 nominal body 6.0 mm 사이의 diametral clearance는 0.4 mm, **측당 0.20 mm**다.

## D. drawing worst-case clearance

6.0 mm body에 일반공차 `+0.3 mm`가 적용되는 보수 조건에서는 body max가 6.3 mm이고, 6.4 pocket의
측당 clearance는 **0.05 mm**다. 이는 P1S 출력공정의 removable-fit 승인이 아니다.

최종 제작 전 실제 보유 lot으로 6.4 / 6.5 / 6.6 / 6.7 mm pocket coupon을 출력해 삽입력, 유격,
반복 탈착과 출력 방향 영향을 확인해야 한다. 이번 실행에서는 coupon CAD를 생성하지 않았다.

## E. INDEX actual body SAT

center와 F2 axis는 그대로 두고 housing만 교체해 full 15-axis OBB SAT를 다시 계산했다.

| pair | legacy 6×6×6 | actual nominal 6×6×3.6 | drawing worst 6.3×6.3×3.9 |
|---|---:|---:|---:|
| I1-I2 | 1.347591 | 1.443121 | 1.023677 |
| I2-I3 | 1.348986 | 1.348986 | **0.937248** |
| I1-I3 | 4.669695 | 6.661942 | 6.176579 |
| I3-I4 | 3.931356 | 4.158761 | 3.830997 |
| **minimum** | **1.347591** | **1.348986 PASS** | **0.937248 FAIL** |

nominal은 목표 `≥1.20 mm`를 통과한다. drawing-worst는 I2-I3에서 0.262752 mm 부족하므로 실제 lot
6.0 mm footprint 측정 전에는 tolerance-robust PASS로 올릴 수 없다.

## F. actuator / bore

- actuator Ø3.5 vs bore Ø4.5: nominal radial clearance **0.50 mm**
- actuator에 일반공차 +0.3을 적용한 Ø3.8 worst: radial clearance **0.35 mm**
- actuator와 bore는 동일 F2 axis를 사용하므로 bore 자체의 coaxial passage는 nominal/worst 모두 PASS
- cap은 구형 surface normal로 움직이고 switch는 F2 axis이므로 cap-normal 편차는 I1/I2/I3
  17.2059°, I4 2.6572°다.

I1/I2/I3의 cap underside 교차점 lateral offset은 약 0.805 mm, I4는 0.121 mm다. Ø3.5 actuator와
7.6 mm cap underside 범위 안이므로 lateral contact 자체는 가능하지만, 아래 G의 stroke가 부족하다.

## G. cap travel

현재 cap underside는 old-normal depth 2.6 mm, holder front trim은 2.8 mm다. 따라서 cap 외곽이 holder에
닿기 전 이동량은 **0.20 mm**뿐이다.

| | nominal free gap | 0.15 travel까지 필요한 cap 이동 | nominal 0.25 | 0.35 max | 판정 |
|---|---:|---:|---:|---:|---|
| I1 | 0.170219 | 0.313506 | 0.409031 | 0.504556 | FAIL |
| I2 | 0.170219 | 0.313506 | 0.409030 | 0.504555 | FAIL |
| I3 | 0.170218 | 0.313505 | 0.409030 | 0.504555 | FAIL |
| I4 | 0.296882 | 0.446721 | 0.546613 | 0.646506 | FAIL |

최소 travel만 보아도 현재 stop보다 I1-I3는 0.1135 mm, I4는 0.2467 mm 더 필요하다. 현재 flat cap은
충분히 actuate하기 전에 holder front에 멈춘다.

`L`과 body height에 general tolerance를 독립 적용한 actuator free-gap stack은 I1-I3
`-0.403…+0.743 mm`, I4 `-0.302…+0.896 mm`다. 음수 쪽은 상시 preload, 양수 쪽은 cap 미접촉
가능성을 뜻한다. 이 넓은 범위는 실제 lot에서 `L`, body height, free-position을 직접 측정해야 한다는
gate이지 확률 예측이 아니다.

## H. RWID / RZKD rear contact

현재 front seat 착좌 기준 actual rear face는 nominal 8.9 mm, drawing range 8.6…9.2 mm다.

| 항목 | 값 |
|---|---:|
| current RWID/RZKD pad front | 11.15 mm |
| nominal rear gap | **2.25 mm** |
| body-height max에서도 gap | **1.95 mm** |
| nominal 0.15 preload용 pad front | 8.75 mm |

따라서 current pad는 actual switch rear에 닿지 않으며 retention/preload는 FAIL이다.

pad만 8.75 mm까지 연장하는 단순안도 service gate를 통과하지 않는다.

| | current | pad-front 8.75 가정 |
|---|---:|---:|
| shared bore 완전 이탈 | 1.57 | **4.34** |
| shared service +0.50 | 2.07 | **4.84** |
| frozen final verified travel | 2.09 | 요구보다 **2.75 부족** |
| I4 required | 1.35 | **3.75** |
| I4 service +0.50 | 1.85 | **4.25** |

RWID/RZKD를 그대로 두고 pad만 늘리는 것은 승인할 수 없다. alternative는 actual rear를 current pad에
맞추는 2.4 mm axial seat/spacer와 cap plunger를 함께 설계하는 방법이지만, 이것도 명백한 holder/cap
재설계이며 이번 audit에서 CAD로 만들지 않았다.

## I. I1 fixed-root clearance

- 0…179° 전수: **clear 0 / 180**
- 모든 자세에서 네 fixed-root segment가 current 6.4 passage 밖의 own-holder solid에 들어감
- nominal minimum hard collision score: 4
- own-root relief만 가정했을 때 외부 gate를 통과하는 sampled orientation은 11개지만, 아직 holder
  subtraction과 실제 bend path가 없으므로 PASS가 아니다.

## J. I2 fixed-root clearance

- 0…179° 전수: **clear 0 / 180**
- own-holder 네 segment + neighbor-holder 최소 두 segment 충돌
- nominal/worst 모두 own-holder relief만으로 clear orientation **0개**
- minimum hard collision score: 6

## K. I3 fixed-root clearance

- 0…179° 전수: **clear 0 / 180**
- nominal은 own-holder 네 segment + neighbor-holder 최소 한 segment 충돌
- worst는 neighbor-holder 최소 두 segment 충돌
- own-holder relief만으로 clear orientation **0개**

## L. I4 fixed-root clearance

- 0…179° 전수: **clear 0 / 180**
- own-holder 네 segment + neighbor-holder 최소 한 segment 충돌
- own-root relief 이후의 외부 gate 후보는 nominal 40개 / worst 28개지만, current geometry clear는 0개

I1-I4 공통 원인은 terminal 포함 외폭 7.9 mm가 pocket 6.4 mm보다 1.5 mm 크고, 최대 외폭을 만드는
factory-formed 구간이 body rear 8.9…10.7 mm에서 아직 holder passage 안에 있기 때문이다. distal
terminal bending은 이 root collision을 해결하지 않는다.

## M. 각 switch 권장 terminal rotation

### INDEX current geometry

| | 승인 rotation |
|---|---|
| I1 | **NONE** |
| I2 | **NONE** |
| I3 | **NONE** |
| I4 | **NONE** |

fixed-root clear orientation이 하나도 없으므로 제조용 preferred rotation을 지정하지 않는다. 진단상
minimum-collision 자세는 nominal I1 138°, I2 148°, I3 35°, I4 32°였지만 모두 고체 충돌이 남아
있으며 **제작 지시값이 아니다**.

### MIDDLE seed

아직 생성하지 않은 terminal-aware holder에서는 M1/M2/M3/M4 모두 local 0°를 seed로 쓸 수 있다.
이때 terminal long-pitch 방향=`local u`, common-group row 방향=`local v`다. frozen INDEX/RWID/RZKD
충돌은 0이고 root-pair SAT는 nominal 최소 0.264974 mm, drawing-worst 최소 0.128496 mm로 양수다.
다만 future holder에는 처음부터 root channels를 넣어야 하며, 0.128 mm를 제조 여유 PASS로 부르지는
않는다.

## N. bendable terminal routing

사용자의 원칙대로 **fixed root가 clear한 orientation만** distal routing을 승인해야 한다. INDEX는 그
전제가 실패했으므로 아래는 Grade-2 redesign용 조건부 architecture일 뿐 current PASS가 아니다.

| button | no-bend root | 조건부 bend 시작 | 조건부 bend 방향 | solder 위치 | wire exit |
|---|---|---|---|---|---|
| I1 | depth 8.9…10.7 | ≥10.7 | local -v | terminal tip 약 12.4 뒤 | RWID -v slot |
| I2 | depth 8.9…10.7 | ≥10.7 | local +v | terminal tip 약 12.4 뒤 | RWID +v slot |
| I3 | depth 8.9…10.7 | ≥10.7 | local -v | terminal tip 약 12.4 뒤 | RWID -v slot |
| I4 | depth 8.9…10.7 | ≥10.7 | local -v | terminal tip 약 12.4 뒤 | RZKD -v notch |

- body를 잡고 root에 하중이 전달되지 않도록 distal을 pliers로 한 번만 성형한다.
- 공장 성형 1.8 mm 구간은 펴거나 재성형하지 않는다.
- bend radius는 공식값으로 선언하지 않으며 actual sample bend test 항목으로 남긴다.
- terminal 간격, solder fillet, insulation OD가 확보되지 않으면 해당 route는 폐기한다.

## O. solder / wiring access

도면 회로상 필요한 전기 단자는 두 개뿐이다. 반드시 서로 다른 공통군에서 하나씩 골라야 한다.

- 가능 예: `1+3`, `1+4`, `2+3`, `2+4`
- 불가: `1+2` 또는 `3+4` - 같은 내부 공통군이라 눌러도 상태가 변하지 않음
- 기본 기계정책: **네 terminal 모두 유지**, 절단 승인 안 함

현 구조에서 retainer가 설치된 뒤 terminal tip에 인두를 넣는 방식은 승인할 수 없다. 현실적인 순서는
`sample continuity 확인 -> distal 1회 성형 -> 두 active terminal 선납땜 -> 개별 절연/heat-shrink ->
holder 삽입 -> wire를 slot으로 인출 -> retainer 체결`이다.

다만 distal 유효길이가 약 1.7 mm뿐이고 wire gauge, insulation OD, solder fillet, heat-shrink OD가
미확정이다. current slot 2.5×1.5 mm가 실제 두 solder joint/두 wire를 수용한다는 증거가 없으므로 wiring
access는 HOLD다. unused terminal도 인접 terminal/retainer와 닿지 않게 개별 절연해야 한다.

## P. serviceability

승인 가능한 목표 절차는 다음과 같다.

1. shell open
2. upstream connector 또는 harness 분리
3. RWID/RZKD screw 해제
4. retainer를 service travel만큼 disengage하고 제거
5. wire를 edge-open slot에서 해제
6. terminal relief를 따라 switch를 뒤로 꺼냄
7. terminal을 다시 펴지 않고 replacement 교환

current INDEX는 root가 holder solid를 관통하고 rear pad도 접촉하지 않으므로 6단계까지 갈 수 없다.
향후 relief는 body rear부터 holder rear까지 열린 연속 channel이어야 하며, bent terminal이나 solder joint가
side slot에 걸려 switch를 영구 captive하게 만들면 FAIL이다. service를 위해 terminal을 다시 펴는 순서는
반복 굽힘 금지 원칙과 충돌하므로 승인하지 않는다.

## Q. INDEX modification grade

### **GRADE 2**

단순 terminal notch 한 개의 GRADE 1로 닫히지 않는다.

1. I2/I3는 own-holder relief만으로 neighbor-holder hard collision이 남는다.
2. current cap stroke는 네 버튼 모두 부족하다.
3. current pad는 actual rear face에서 nominal 2.25 mm 떨어져 있다.
4. pad 연장안은 shared service 요구를 4.84 mm로 늘려 frozen 2.09 mm path를 무효화한다.
5. drawing-worst body SAT는 0.937 mm로 robustness gate를 실패한다.

center/F2 axis까지 바꿔야 한다는 GRADE 3 증거는 없다. 우선순위는 `axial seat/spacer + controlled cap
plunger/stops + terminal-aware holder passages + compatible rear retention/service`의 holder-level
재설계다.

## R. INDEX CAD modification 필요 YES / NO

### **YES**

current INDEX geometry 그대로 실제 switch를 삽입·고정·작동·서비스할 수 없다. 이번 실행에서는 어떤
CAD feature도 생성/수정/삭제/suppress하지 않았다.

## S. MIDDLE feasibility

docs/29의 H3.5 branch를 actual housing 3.6 mm와 drawing-worst 3.9 mm로 다시 평가했다.

| gate | actual nominal 6.0×3.6 | drawing worst 6.3×3.9 |
|---|---:|---:|
| body SAT min | **1.506315 PASS** | **1.152128 FAIL** |
| pocket divider min | 1.034066 PASS | 0.981542 PASS |
| split wall min | 1.513915 PASS | 1.513915 PASS |
| screw clearance min | 7.682136 PASS | 7.482957 PASS |
| actual front lip min | **0.500000 PASS 경계** | **0.427368 FAIL** |
| frozen INDEX clearance | **0.513070 PASS** | **0.456588 FAIL** |
| frozen INDEX intersection | 0 | 0 |

결론은 **같은 switch의 nominal MIDDLE geometry는 가능하지만 tolerance-robust candidate는 아직 미확정**이다.
low-profile 전용 switch가 필수라는 증거는 없다. actual lot body/L 측정과 terminal-aware holder를 포함한
재최적화가 선행되어야 한다.

## T. MIDDLE row displacement

재평가 seed는 docs/29 `h3p1_w1` branch다.

```text
common row Δ = (+1.500, +3.125, -5.125) mm
norm         = 6.187184 mm
per button   = M1 6.333 / M2 9.849 / M3 6.706 / M4 7.236 mm
max          = 9.849244 mm (M2)
```

이 값은 actual switch nominal의 geometry seed이며 ergonomic approval나 continuous global optimum 증명이
아니다.

## U. MIDDLE terminal feasibility

- local 0° seed에서 frozen INDEX/RWID/RZKD fixed-root collision 0
- external hard-clear rotation count nominal: M1 180, M2 150, M3 180, M4 180 / 각 180
- drawing-worst: M1 180, M2 110, M3 180, M4 180 / 각 180
- 0° root-pair SAT: nominal min 0.264974, drawing-worst min 0.128496 mm
- holder outer half-width 6.2 vs terminal worst half-width 4.1이므로 aligned root channel 뒤 outer ligament는
  약 2.1 mm를 시작점으로 잡을 수 있음

따라서 MIDDLE terminal architecture는 **feasible conditional**이다. future holder에 6.4 pocket만 뚫고
단자를 나중에 굽혀 해결하는 방식은 금지하며, factory root 7.9/8.2 envelope용 four-channel과 rear solder
cavity를 처음부터 넣어야 한다.

## V. 동일 switch로 INDEX + MIDDLE 통일 가능 YES / NO

### **YES - redesign target으로는 가능, current production approval은 아님**

INDEX nominal body separation과 MIDDLE nominal full gate가 모두 성립하므로 별도 low-profile SKU를 지금
도입할 필요는 없다. 다만 INDEX GRADE 2 redesign, MIDDLE worst-envelope 재최적화, actual-lot coupon과
wiring prototype을 통과해야 통일 SKU가 확정된다.

## W. EVQP0E07K 폐기 여부

### **finger-button 기본안 / mechanical source of truth에서 제외**

EVQP0E07K를 위해 INDEX를 재설계하지 않는다. 부품 자체를 물리적으로 폐기하라는 뜻은 아니며, 문서상
non-baseline fallback/reference로만 보관한다. 실제 설계 우선순위는 사용자가 보유한 이 6×6 / L=6
switch다.

## X. 다음 CAD WRITE GO / HOLD

### **HOLD**

HOLD 사유:

1. INDEX fixed-root clear rotation 0/180, I2/I3는 own-only relief로도 해가 없음
2. cap minimum/nominal/max travel 모두 current 0.20 mm stop를 초과
3. RWID/RZKD rear contact 없음, pad-extension service path도 불충분
4. INDEX drawing-worst body SAT <1.20
5. MIDDLE drawing-worst SAT/front-lip/robust INDEX-clearance 미확정
6. actual lot body/L/free-height, wire gauge, insulation OD, solder envelope, prototype bend radius 미측정

다음 CAD WRITE gate는 `actual-lot 실측 + 6.4…6.7 coupon + wire/solder BOM + INDEX axial-seat/cap/terminal/
retainer architecture 선택 + MIDDLE worst-envelope rerun`이다. 그 전까지 INDEX_FINAL_VALIDATED는 freeze를
유지한다.

---

## 재현 파일

- `cad_dump/stock_6x6x6_switch_actual_fit_audit.json`
- `scripts/audit_stock_6x6_switch.py`

스크립트는 frozen local meshes만 읽으며 HTTP/Onshape client와 mutation code가 없다.
