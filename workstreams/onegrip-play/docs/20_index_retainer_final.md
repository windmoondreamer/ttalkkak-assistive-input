# INDEX retainer — 국소 나사 B relief 적용 및 최종 검증

- 일자 2026-08-19
- 승인 근거: docs/19 service-disengagement 분석 승인 + "3.00 mm 국소 relief 적용" 지시
- 체크포인트: **`RETAINER_pre_relief`** (`2c90c9810a362680c1dfc8fa`) — 적용 직전 생성
- 적용 피처: **`INDEX_retainer_service_relief`** (`F2M3epnJT0bImz7_16`), stage = RELIEF

---

## A. 3 mm relief 적용 — **PASS**

```
나사 B 보스 원통 (r = 3.5 + fit 0.25 = 3.75, X ∈ [-22, +1])
  -> 삽입방향 w 로 0.5 mm x 6 = 3.00 mm sweep (opPattern + union)
  -> SUBTRACT, target = retainer body ONLY
```

- 컴파일 OK, 피처 상태 **OK**
- 전체 feature **169개, ERROR 0, WARNING 0, isComplete true**

> 실행 직후 runner 가 `state=ERROR` 로 표시했으나, 이는 **POST 응답이 재생성 완료 전 상태**를
> 담기 때문이다. `/features` 재조회 결과 실제 상태는 **OK** 였다.
> (앞으로 POST 직후 상태만 보고 판단하지 말 것)

## B. RWID single body — **PASS**

| 항목 | 결과 |
|---|---|
| retainer body | **`RWID` 1개** |
| 연결성분 (복셀 0.5 mm) | **1** (15,270 복셀) |
| body split / fragment | **0 / 0** |
| `JaD` = Joystick_1 / `JfD` = Joystick_2 | 각 1 body, 정상 |
| solid 총수 | 19 |

## C. removed volume

| | 부피 |
|---|---|
| relief 전 | 2,028 mm³ |
| **relief 후** | **1,909.5 mm³** |
| **제거량** | **118.5 mm³ (5.8 %)** |

docs/19 예측 **119 mm³** 와 사실상 일치.

## D. 실제 무충돌 인출 거리 — **2.93 mm (PASS)**

최종 B-rep tessellation 에서 retainer 전체를 −w 로 이동시키며 JfD(쉘+홀더 전체)와 광선 검사:

| | 값 |
|---|---|
| **최대 무충돌 이동** | **2.93 mm** |
| 요구 (d_service) | 2.07 mm → **+0.86 mm 여유** |
| 목표 (docs/19 예측) | 2.97 mm → 실측 2.93 (오차 0.04) |
| 그 뒤 첫 장애 | face `SSICB` (국소 쉘면) |

스위치 몸체 간섭:

```
t = 0.00 : 37   <- 의도된 pad-switch preload 접촉 (허용)
t = 0.20 : 0
t = 1.00 : 0
t = 2.07 : 0
```

## E. d_I1 / d_I2 / d_I3 재측정

최종 geometry 에서 **retainer 전체가 네 보어에서 완전히 이탈하는 거리 = 1.56 mm**
(docs/19 해석값 1.57 mm 와 일치, 오차 0.01)

## F. t = 2.07 mm 에서 pad disengagement — **PASS**

| | 보어 겹침 복셀 |
|---|---|
| I1 | **0** |
| I2 | **0** |
| I3 | **0** |
| I4 | 0 |

→ **PAD_I1 / PAD_I2 / PAD_I3 fully disengaged.**

## G. structural web — **1.54 mm (PASS, 목표 미달)**

| 연결 | relief 전 | **relief 후** |
|---|---|---|
| I1-I2 | 2.28 | **1.54 mm** |
| I2-I3 | 1.91 | **1.54 mm** |
| I1-I3 | 1.91 | **1.97 mm** |
| **최소** | 1.91 | **1.54 mm** |

- 성공 기준 **≥ 1.50 mm 충족** (여유 +0.04 mm)
- 목표였던 "기존 1.91 mm 유지" 는 **달성하지 못했다**
- docs/19 시뮬레이션은 1.91 유지를 예측했으나, 실제 CAD 의 원통 sweep(0.5 mm 간격 6회)이
  해석 모델(0.1 mm 간격 연속)보다 I1-I2 / I2-I3 목 부근을 조금 더 깎았다

> **여유가 0.04 mm 뿐이므로 이 값은 주시 대상이다.**
> 개선하려면 fit clearance 를 0.25 → 0.20 으로 줄이거나 sweep 을 2.07 mm 로 되돌리면 되지만,
> 둘 다 승인 파라미터 변경이므로 **임의로 하지 않았다.**

## §10. pad / wiring 무변화 검증

### pad 접촉면 (스위치 뒷면 3.6 × 3.6, 225 표본)

| | relief 전 | relief 후 | 변화 |
|---|---|---|---|
| I1 | 182 | 182 | **무변화** |
| **I2** | 194 | **191** | **−3 (−1.3 %)** |
| I3 | 183 | 183 | **무변화** |

pad 돌출 구간(11.15~12.5) 단면: I1/I3 무변화, **I2 −16/243 (−6.6 %)**.
I2 가 유일하게 줄어든 것은 나사 B 보스가 I2 에 가장 가깝기 때문이다.
남은 접촉면 **85 %** 로, 6 × 6 스위치를 수 N 으로 누르기에 충분하다.

### 배선 슬롯 (I1 −v / I2 +v / I3 −v, 2.5 × 1.5)

```
I1  180/180 -> 180/180   무변화
I2  180/180 -> 180/180   무변화
I3  180/180 -> 180/180   무변화
```

**세 슬롯 전부 완전 무변화.**

---

## H. EAR_A / EAR_B — **위치 재검증 완료, 구현 미착수**

현재 geometry 에서 승인 후보를 재검증했다.

| | 위치 | 쉘 안 | 포켓 거리 | 나사 B | X |
|---|---|---|---|---|---|
| **EAR_A** (I1 축 −u 8.0, 깊이 9.5) | (−18.19, −5.85, +10.52) | 아니오(자유) | **4.80 mm** | **11.71 mm** | < 0 ✔ |
| **EAR_B** (I3 축 −v 8.0, 깊이 9.5) | (−4.83, −19.87, +0.98) | 아니오(자유) | **4.80 mm** | **19.25 mm** | < 0 ✔ |

두 후보 모두 **승인값 그대로 유효**하다.

## I. fastening geometry — 제원 산출 완료

| | 앵커에서 쉘까지 | 앵커에서 retainer 본체까지 |
|---|---|---|
| EAR_A | **1.80 mm** | 3.04 mm |
| EAR_B | **0.46 mm** | 3.29 mm |

**더 나은 위치도 찾았다** (retainer 본체에 직접 붙고 보스 높이만 필요):

| | 위치 | 쉘까지 | retainer까지 |
|---|---|---|---|
| EAR_A' (off 7.5, 깊이 14.0) | (−14.11, −4.03, +11.24) | **2.37 mm** | **0.00 mm** |
| EAR_B' (off 7.0, 깊이 14.0) | (−4.52, −15.38, +1.97) | **2.51 mm** | **0.00 mm** |

→ ear 는 retainer 본체에서 바로 자라고, 쉘 보스는 **2.4 ~ 2.5 mm** 만 세우면 된다.
기존 `Screw_holes` 는 건드리지 않는다. **아직 구현하지 않았다.**

## J. fastening 후 service path — **미검증** (fastening 미구현)

## K. I4 retainer — **미구현**

## L. printability — 기존 분석 유지

최적 베드 법선 (−0.4734, −0.8350, −0.2805) 에서 세 pad 면 경사 30.08° → 서포트 불필요.
최소 벽: web **1.54 mm** (0.4 노즐 약 4 lines). relief 로 얇아졌으므로
출력 시 이 부위를 확인할 것.

## M. JaD / JfD / assembly — **PASS**

```
solid 19            retainer RWID 단일
Joystick_1 = JaD    Joystick_2 = JfD   (각 1 body, split 0)
feature 169         OK 169 / ERROR 0 / WARNING 0 / INFO 4(원본)
isComplete true     assembly 25 / 25
```

**SUBTRACT target 은 이번에도 retainer body 하나뿐이었다.**
나사 B / JaD / JfD / holder / shell 은 tool·reference 로만 사용했다.

## N. INDEX FINAL SUCCESS — **HOLD**

§16 의 14개 조건 중:

| # | 조건 | 상태 |
|---|---|---|
| 1 | F2 holder FINAL PASS | **PASS** |
| 2 | regeneration ERROR 0 | **PASS** |
| 3 | switch SAT ≥ 1.20 mm | **PASS** (1.3476) |
| 4 | pocket divider ≥ 0.80 mm | **PASS** (0.8000) |
| 5 | actual seating 4/4 | **PASS** |
| 6 | **service disengagement ≥ 2.07 mm** | **PASS (2.93 mm)** |
| 7 | **retainer web ≥ 1.5 mm** | **PASS (1.54 mm)** |
| 8 | shared retainer fastening | **미구현** |
| 9 | I4 retainer | **미구현** |
| 10 | all switches removable | 8·9 미완으로 미검증 |
| 11 | wiring access 유지 | **PASS** |
| 12 | JaD/JfD 유지 | **PASS** |
| 13 | assembly 25/25 | **PASS** |
| 14 | 원본 엄지 geometry 무변화 | **PASS** |

→ **8 · 9 미구현으로 FINAL SUCCESS 보류.** 나머지는 전부 통과.

## O. MIDDLE — **HOLD** (§17 지시대로 미착수)

---

## 다음 실행 (승인 시)

1. **EAR_A' / EAR_B'** 를 retainer 에 ADD (본체에서 바로 자라므로 탭 길이 0)
2. 쉘에 보스 2개 union (신규 downstream feature, 높이 약 2.4 ~ 2.5 mm)
3. 나사 구멍 — 규격 미확정이므로 provisional parameter
4. ear 추가 후 **0 ~ 2.07 mm service path 재검사**
5. I4 단독 retainer (small cap/plate)
6. INDEX FINAL VALIDATION → MIDDLE

### 주시 항목

- **web 1.54 mm 는 기준선(1.50)과 0.04 mm 차이뿐이다.** ear 추가가 이 값을 더 낮추지 않는지
  반드시 재측정할 것
