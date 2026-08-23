# P1S 2분할 제조 모델 — PRINT ENGINEERING

`ERGO_HOUSING_25_WRAP_FINAL_V4` 를 Bambu Lab P1S 출력용으로 2분할한 파생 모델.
**원본 V4 는 읽기만 했고 수정/덮어쓰기 0건.** G-code 미생성.

---

## 1. MAIN / ARMREST P1S bbox

CUT FACE DOWN 으로 실제 BREP 를 변환해 측정. 두 부품은 **각각 별도 print job** 기준.

| | 원본 bbox | 회전 | print bbox (W×D×H) | P1S 256 마진 |
|---|---|---|---|---|
| **MAIN** | 133.600 × 233.800 × 154.583 | Rx **+90°** | **133.600 × 154.583 × 233.800** | 122.4 / 101.4 / **22.2** |
| **ARMREST** | 126.749 × 159.685 × 74.960 | Rx **−90°** | **126.749 × 74.960 × 159.685** | 129.3 / 181.0 / 96.3 |

둘 다 목표 235 mm 이하. **PASS.**

> MAIN 의 절단면 법선은 −Y, ARMREST 는 +Y 라 회전 부호가 반대다.

## 2. bed contact area / slenderness

| | bed contact | slenderness H/√A |
|---|---|---|
| MAIN | **1,520.4 mm²** | **6.00** |
| ARMREST | 1,371.4 mm² | 4.31 |

MAIN 은 39×39 mm 상당 접지로 233.8 mm 를 세운다. **brim 을 넓게 쓸 것을 권장** —
brim 은 Z 높이에 영향이 없으므로 22.2 mm 마진을 잠식하지 않는다.

## 3. support true trapped 여부 — **0**

### 3-1. 1차 판정 (수평 8방향 광선) — 보수적 오판

```
MAIN     E TRAPPED 47 face / 3,041.1 mm2   (짐벌 공동 2,175 / 캐리어 포켓 560)
ARMREST  E TRAPPED  0
```

### 3-2. 확정 판정 (voxel connectivity)

support 체적을 복셀 2.0 mm 로 잡아 chunk 로 분리하고, **removal opening 4종**까지
3D flood fill 로 연결성을 봤다. 좁은 목은 침식 반경으로 정량화했다.

```
removal opening (print 좌표, grip -> print 는 (x,y,z)->(x,-z,y-z0))
  1) 덱 개구부 92.9 x 89.8   grip +Z -> print -Y 면
  2) carrier 하방 인출 통로   grip -Z -> print +Y 면
  3) 하우징 하부 개방부       동일    -> print +Y 면
  4) joint 분할 개방면        grip Y=-140 -> print z=0 (베드면)
```

| 파트 | support 체적 | chunk | TRUE TRAPPED |
|---|---|---|---|
| MAIN | 1,178.3 cm³ | 12 | **0** |
| ARMREST | 73.5 cm³ | 6 | **0** |

지정 영역별:

| 영역 | 1차 E | 확정 판정 |
|---|---|---|
| **A. stock gimbal / ±15° cavity** | 2,175 mm² | **REMOVABLE THROUGH DECK OPENING** — 최대 chunk 990.2 cm³, 측지 **2.5 mm** |
| **B. carrier pocket** | 560 mm² | **REMOVABLE THROUGH SPLIT/LOWER OPENING** — chunk 각 ~12 cm³, 측지 80.0 mm |
| deck underside / screw·insert / doubler / rib | 0 | 해당 없음 |

전 chunk 목반경 ≥ 2 mm. 예외는 `chunk #7` (0.50 cm³, 목반경 0 mm) 하나이며
X ±53 에 걸친 0.5 cm³ = 두께 0.1 mm 수준의 **얇은 틈**이라 실제 support 가 필요 없다.

**1차 판정이 틀린 이유:** 수평 등고면 8방향 탈출만 봐서 사선·꺾인 경로를 놓쳤다.
이 방향에서 덱 개구부는 print −Y 를 향하는데 그 경로가 등고면 위에 없었다.

## 4. 추천 print orientation

**두 파트 모두 CUT FACE DOWN 유지.** TRUE TRAPPED 가 0 이므로 대안 orientation
비교는 불필요하다.

```
MAIN     Rx +90deg   절단면(Y=-140)을 베드에
ARMREST  Rx -90deg   절단면(Y=-112)을 베드에
```

## 5. 추천 support 방식 (Bambu Studio / P1S)

### face 분류 결과

| | A self-sup | B bridge | C from plate | D removable | E trapped |
|---|---|---|---|---|---|
| MAIN | 195,885.9 | 94.3 | 14,270.1 | 10,070.0 | **0** |
| ARMREST | 57,799.1 | 62.6 | 2,925.9 | 87.0 | **0** |

(단위 mm²)

### 권장값

**MAIN**
```
support type      normal / snug   (tree 불필요 — organic 외피가 없다)
support on        build plate only 로는 부족.
                  C 14,270 mm2 는 plate 에서 올라가지만
                  D 10,070 mm2 는 파트 위에 얹혀야 한다
                  -> "everywhere" + painted 로 외부 팔접촉면만 제외
제거 방향         짐벌 공동 990 cm3 -> 덱 개구부 (측지 2.5mm)
                  나머지 -> 분할면/베드 쪽
```

**ARMREST**
```
support type      normal / snug
support on        **build plate only 로 충분**  (D 가 87 mm2 뿐)
제거 방향         73.8 cm3 -> carrier/lower 쪽 (측지 37.5mm)
                   6.8 cm3 -> 분할면/베드 쪽 (10.0mm)
```

**외부 25° 팔접촉면**: MAIN 기준 C 28 mm² 뿐이고 ARMREST 는 U-channel 내부가
A 38,545 mm² 로 **전량 self-supporting** 이다 (절단면을 아래로 놓으면 채널 벽이
수직이 된다). painted support 로 그 면을 빼기 쉽다.

`SUPPORT_MAP_MAIN.png` / `SUPPORT_MAP_ARMREST.png` — 초록 = no support,
노랑 = bridge/conditional, 빨강 = support required, 화살표 = 측지 제거 방향.

## 6. joint strength

### joint 사양

```
overlap        28.0 mm  (Y -140 .. -112)
랩 평면        상판 밑면에서 7.0 mm (램프 평행)
internal doubler  14.0 mm,  X[-63,63],  Y[-146,-106]
리브           X ±12,  5.0 x 2.5 mm,  Y[-137,-115]  종방향
clearance      0.275 mm per side
M4 x4          X ±40,  Y -133 / -119  (좌 2 / 우 2)
```

### 단면 성질 (조립 상태 실측)

| | Y | A (mm²) | I (mm⁴) | c (mm) |
|---|---|---|---|---|
| lap 앞끝 | −140 | 1,199.2 | 460,429 | 47.34 |
| lap 중앙 | −126 | 1,275.6 | 604,455 | 51.63 |
| lap 뒤끝 | −112 | 1,351.2 | 774,835 | 55.87 |

### 하중별 (팔 하중을 팔받침 앞끝 Y=−272 집중 — 분포하중 대비 보수적)

| | 20 N | 50 N PROOF | 100 N | 허용 |
|---|---|---|---|---|
| lap 모멘트 | 2.920 N·m | 7.300 | 14.600 | — |
| 단면 굽힘 | 0.249 MPa | 0.623 | **1.247** | 25.0 |
| doubler 굽힘 | 0.823 | 2.057 | **4.114** | 25.0 |
| 랩 전단 (3,528 mm²) | 0.0057 | 0.0142 | 0.0283 | 8.0 (층간) |
| 리브 전단 (220 mm²) | 0.0909 | 0.2273 | 0.4545 | 15.0 |
| 인장측 합력 | 57.9 N | 144.8 N | 289.7 N | — |
| **M4 1개 인장** | 14.5 N | 36.2 N | **72.4 N** | 항복 약 2,400 N |

**최대 사용률 16 %** (100 N 에서 doubler 굽힘 4.114 / 25.0).

**lap/root 모멘트비 0.77** — joint 가 root(Y −81.8)보다 23 % 낮은 모멘트 위치에 있다.
root 회피가 수치로 확인된다.

### 하중 분담 — 요구 구조와 일치

```
랩면 3,528 mm2 + 리브 220 mm2   ->  전단
doubler + 단면                  ->  굽힘
M4 x4                           ->  clamp (인장측 합력만)
insert pull-out 방향            ->  랩 평면 법선 = 상판 법선, 축방향 인발
```

**M4 는 primary shear pin 이 아니다.**

> 정정: 첫 계산은 우력 팔길이를 나사 간격 14 mm 로 잡아 M4 인장 **521 N** 을 냈다.
> 압축을 랩 접촉면이 받으므로 틀린 모델이다. 인장측 합력 `T = M/I × Q_tension`
> 으로 다시 계산해 **72.4 N** 을 얻었다. 단면 굽힘이 1.2 MPa 인데 나사만 수백 N 을
> 받는 건 앞뒤가 안 맞았다.

## 7. assembly reconstruction 결과

MAIN + ARMREST 를 nominal mating transform(제자리)으로 재조립.

```
V4       947,875.754 mm3
MAIN     853,277.769
ARMREST  155,578.523
조립     1,008,856.292   solids 2  <- clearance 0.275 로 두 조각이 안 닿는다 (정상)
```

### A. joint 영역 밖 — 차이 0

```
점 표본 60,000개 멤버십 비교 (joint 영역 Y[-148,-104])
  [OUTSIDE joint]  공통 6,835   V4에만 0 (0.0 mm3)   조립본에만 0 (0.0 mm3)
  참고 부피        V4 891,741.176  vs  조립 891,741.176   (완전 일치)
```

**external geometry difference = 0, internal cavity difference = 0. PASS.**

### B. joint 영역 안 — 의도된 차이만

```
  [INSIDE joint]   V4에만    755.4 mm3   = clearance + 나사 구멍
                   조립본에만 116,454.3 mm3 = internal doubler
```

> 측정기 정정: 처음엔 OCC 부울 교집합을 썼는데 V4·조립본 부피가 891,741.176 으로
> 소수 3자리까지 같은데도 교집합이 **102,013** 으로 나왔다. 크고 복잡한 solid
> 끼리의 부울 실패다. **점 표본 멤버십**으로 바꿔 정확히 0 을 얻었다.

## 8. 23 gates / ±15° motion

게이트 검증에는 clearance 0 의 **nominal 조립본**(`base − 나사구멍`, 단일 solid,
vol 1,010,693.663)을 썼다. MAIN+ARMREST 원본은 2 solid 라 검증기에 그대로 못 넣는다.

### 23 gates — **PASS 23 / FAIL 0**

```
[PASS] BOTTOM_CARRIER 무변경          90,177.998830 mm3
[PASS] 기준면 vs 월드 수평             20.000000000 deg
[PASS] 그립 중립축 ⟂ 기준면            90.000000 deg
[PASS] 캐리어 -Z 인출 0..100 mm        무충돌
       W / L / H         133.6000 / 365.7597 / 140.5240
       deck -> HAND_REF   55.8785        ground -> HAND_REF 161.0208
       stock protrusion    0.0000
```

### ±15° motion — 전항목 PASS

```
neutral / Pitch ±15 / Roll ±15 / corner (±15,±15) 4개   전부 간섭 0 / 12,000점
24방향 azimuth cone @15도                              합계 0
24방향 square boundary @15도                           합계 0
최소 최초접촉각 15.88도 (방위 45/315)   여유 +0.88도
포락선 기하 여유 1.5 mm 는 별개
```

### void 감사

```
앞 부각10/20/30도, 측면   전부 0.0 mm2
앞 0도 / 반대쪽 0도       3.9 mm2  <- V4 와 동일값, 해상도 의존 래스터 아티팩트
```

분할 전 V4 와 **모든 불변량이 동일**하다.

## 9. STL 품질

| | BREP | STL |
|---|---|---|
| HOUSING_V4_MAIN_PRINT | solid 1 / shell 1 / valid | tri 22,170 · 경계 0 · 비다양체 0 · degen 0 · **watertight True** |
| HOUSING_V4_ARMREST_PRINT | solid 1 / shell 1 / valid | tri 6,844 · 경계 0 · 비다양체 0 · degen 0 · **watertight True** |
| JOINT_FIT_COUPON | solid 1 / shell 1 / valid | tri 3,202 · 경계 0 · 비다양체 0 · degen 0 · **watertight True** |

단위 mm.

## 10. 최종 출력용 경로

```
export/step/HOUSING_V4_MAIN_PRINT.step
export/stl/HOUSING_V4_MAIN_PRINT.stl

export/step/HOUSING_V4_ARMREST_PRINT.step
export/stl/HOUSING_V4_ARMREST_PRINT.stl

export/step/HOUSING_V4_SPLIT_ASSEMBLED.step     (게이트 검증용 nominal 조립본)
export/stl/HOUSING_V4_SPLIT_ASSEMBLED.stl
```

원본 `ERGO_HOUSING_25_WRAP_FINAL_V4.*` 및 V3 이하 산출물은 **전부 무손상 보존**.

### preview

```
SPLIT_SIDE.png            SPLIT_ISOMETRIC.png       SPLIT_EXPLODED.png
MAIN_PRINT_ORIENTATION.png   ARMREST_PRINT_ORIENTATION.png
SUPPORT_MAP_MAIN.png      SUPPORT_MAP_ARMREST.png
JOINT_DETAIL.png          JOINT_SECTION.png
```

`JOINT_SECTION.png` 에 6 mm 원본 상판 / 14 mm internal doubler / 28 mm overlap /
랩 평면 / M4 관통·카운터보어 / heat-set insert 5.6×8 이 전부 주기와 함께 보인다.

## 11. JOINT_FIT_COUPON

```
export/stl/JOINT_FIT_COUPON.stl
export/step/JOINT_FIT_COUPON.step

bbox 65.00 x 28.00 x 16.00 mm   solid 1 / shell 1   [PASS] 50~80mm 이내
insert pilot   5.2 / 5.3 / 5.4 / 5.5 / 5.6 mm   축 **수평**, 깊이 8.0
clearance      0.20 / 0.25 / 0.275 / 0.30 / 0.35 mm per side
식별 노치      pilot = (d-5.1)x10 개,   clearance = 순번
```

**layer orientation 을 재현했다.** 대형 파트가 CUT FACE DOWN 이므로 print 좌표에서
insert 축은 **수평**, 리브는 **수직으로 길고 수평 돌출**이 된다. 쿠폰도 같은 관계다.

## 12. MECHANICAL_HARDWARE_CONFIRMATION_REQUIRED

확정 전까지 대형 파트 치수를 **변경하지 않는다.**

| 항목 | 현재값 | 상태 |
|---|---|---|
| M4 heat-set insert OD | ⌀5.6 × 8.0 | **provisional** — 쿠폰으로 5.2~5.6 확정 |
| joint clearance | 0.275 mm/side | **provisional** — 쿠폰으로 0.20~0.35 확정 |
| **M4 screw head** | 카운터보어 ⌀8.0 × **3.0** | **CONFIRMATION REQUIRED** |

M4 socket-cap(DIN 912 / ISO 4762)의 표준 head 는 **⌀7.0 × height 4.0 mm** 다.
현재 카운터보어 깊이 3.0 mm 로는 **1.0 mm 부족**하다. 지름은 ⌀8.0 로 충분하다.

실제 사용할 나사 제원이 확정되면 카운터보어 깊이를 재검토해야 한다. 아래 판이
6.0 mm 이므로 깊이 4.0 으로 늘려도 잔여 2.0 mm 는 확보된다. **자동 적용하지 않았다.**

나사 길이도 provisional: 머리 3.0 + 아래판 잔여 3.0 + insert 8.0 → **M4 × 12~14**.

## 13. 작업 중 발견·수정 (기록)

| # | 증상 | 원인 | 조치 |
|---|---|---|---|
| 1 | joint 가 butt 절단, 나사 부피 변화 0 | 팔받침을 17.5 mm 통짜로 오독. 실제는 **6 mm 상판 + 65 mm 측벽 U 채널**. 지면 평행 랩 평면이 슬래브보다 43 mm 아래를 지남 | 램프 평행 랩 평면 + internal doubler |
| 2 | MAIN 3 solid (219 mm³ ×2) | doubler 를 측벽 안쪽 면에 **정확히 맞닿게** 끝내 융합 실패 | `X ±63` 으로 물림 |
| 3 | MAIN 3 solid (440 mm³ ×2) + FRONT 내부 공동 2개 | `Plane(z_dir)` 자동 x_dir 로 리브 축이 뒤바뀌고 `.moved()` 가 **상대 이동**이라 리브가 Y −249 로 날아가 살 속에 파묻힘 | 축 명시 Box + 절대 좌표 |
| 4 | support_map 이 venv 에서 죽음 | **venv 에 matplotlib 없음 / 시스템 python 에 build123d 없음** | routes(venv) / draw(시스템) 2단계 분리 |
| 5 | 쿠폰 96 mm, orientation 불일치 | tongue 을 수직 돌출로 만듦 | 65 mm 로 축소 + 수평 돌출 |
| 6 | M4 인장 521 N | 우력 팔길이를 나사 간격으로 잡음 | 인장측 합력 `T = M/I × Q` → 72.4 N |
| 7 | §10 교집합 102,013 | 크고 복잡한 solid 끼리 OCC 부울 실패 | 점 표본 멤버십 |

**검증을 코드에 박은 것이 이번 라운드에서 결정적이었다** — doubler 부착량 < 100 mm³,
나사 절삭량 < 10 mm³, shells ≠ 1 을 경고로 출력하게 하자 1·2·3번이 즉시 드러났다.

## 14. STOP

G-code 미생성. 대형 파트의 insert hole / clearance 최종값은 쿠폰 실물 테스트
전까지 변경하지 않는다.

---

# 개정 (REV B) — tapered doubler + MAIN CUT FACE UP

승인 사항 2건을 반영하고 A~H 를 전부 재검증했다.

## A. TAPERED DOUBLER — 숄더 돌출 수정

**결함:** `DBL_X = 63.0` 상수였는데 V4 외곽 반폭은 **앞으로 갈수록, 그리고 위로
갈수록** 좁아진다. joint 앞쪽에서 팔이 닿는 라운드 숄더를 최대 **7.2 mm** 뚫고
나왔다. 원인은 `DBL_X = 58` 에서 융합이 안 되자 **바깥으로 키워서** 해결한 것.

**수정:** X 광선으로 잰 실측 프로파일을 따라 테이퍼.

```
V4 외곽 최소 반폭(상판 밑면 기준)  Y -148 -> 55.81   Y -108 -> 60.30   (0.11225 mm/mm)
doubler 반폭 = 각 Y 최솟값 - 2.0
  DBL_W0 (Y=-146)  54.035        DBL_W1 (Y=-106)  58.525
DBL_TOP_OVER 1.0   <- 융합은 바깥이 아니라 **상판 안쪽 1mm 겹침**으로
```

깊이 방향은 가장 좁은 off0 값을 전 두께에 적용해 어느 깊이에서도 안 뚫는다.

**검증 (tessellation 0.005 / ang 0.05):**

```
전체 실루엣 델타   SIDE / TOP / FRONT / OBLIQUE SHOULDER   전부 0.000000 mm
X 광선 외곽 반폭   최대 초과 +0.0020 mm @ Y -136 깊이 4
[PASS] visible external protrusion = 0
```

> tol 0.04 에서는 +0.0240 mm 였다. 8배 조밀하게 하니 12배 줄었다 —
> **해상도에 비례해 줄면 메시 잡음**이다. joint 구간 한정 실루엣 지표는 폐기했다:
> Y 창 안의 정점 bbox 를 비교하는데 조립본은 절단면·doubler 의 **내부 정점**이
> 그 창에 추가되어 실루엣 비교가 아니다.

## B. STRENGTH RECHECK — 실제 BREP 단면

lap 면적을 **사다리꼴 실면적**으로 정정했다 (`max(W0,W1)` 사용은 과대평가).

```
lap 면적  3,528 -> 3,152 mm2  (-10.7%)
```

| | 20 N | 50 N | 100 N | 허용 |
|---|---|---|---|---|
| 단면 굽힘 | 0.249 | 0.623 | 1.247 | 25.0 |
| doubler 굽힘 | 0.886 | 2.214 | **4.428** | 25.0 |
| 랩 전단 | 0.0063 | 0.0159 | 0.0317 | 8.0 |
| 리브 전단 | 0.0909 | 0.2273 | 0.4545 | 15.0 |
| M4 1개 인장 | 14.48 N | 36.21 N | 72.42 N | 약 2,400 N |

**최대 사용률 17.7 %** (100 N, doubler). 기존 허용 기준 유지 → **PASS.**

## C. MAIN = CUT FACE UP

```
                      CUT FACE DOWN      CUT FACE UP (채택)
print bbox            133.6 x 154.6 x 233.8  (동일)
아래보기 면적          27,475 mm2    ->   29,159 mm2   (+6.1%)
bed contact            1,520 mm2    ->    8,955 mm2   (5.9배)
slenderness             6.00        ->     2.47
C build plate 지지     14,270 mm2    ->   16,949 mm2   (+19%)
D 파트 위 support      10,070 mm2    ->    9,192 mm2   (-9%)
```

ARMREST 는 CUT FACE DOWN 유지 (Rx −90; 절단면 법선이 +Y 라 같은 회전에서 아래를 향한다).

## D. SUPPORT AUDIT — 새 orientation 에서 재실행

이전 결과 재사용 없음. opening 라벨도 회전 부호에 맞춰 고쳤다.

```
Rx -90 에서   덱 -> print +Y,  캐리어 -> -Y,  절단면 -> z=max (위)
```

```
support chunk 14개
  #4  999.69 cm3  목반경 >= 2mm   #2  160.06   #8/#10 10.17 x2   #3 1.98
  #7/#9/#11 <1cm3  NARROW (<2mm neck)
[PASS] TRUE TRAPPED chunk 0개 / 0.00 cm3
```

**영역별 1차 E 비교 — 짐벌 공동이 사실상 해소됐다**

| 영역 | CUT FACE DOWN | CUT FACE UP |
|---|---|---|
| stock gimbal / ±15° cavity | 2,175 mm² | **14 mm²** |
| carrier pocket | 560 | 629 |
| deck underside / screw / doubler / rib | 0 | 0 |

이 방향에서 덱 개구부가 위(+Y)로 열리기 때문이다. **CUT FACE UP 최종 승인.**

## E. JOINT SURFACE QUALITY

mating joint 가 위를 향하므로 대부분 support-contact-free 다.

| 면 | 총면적 | 아래보기 | 비율 |
|---|---|---|---|
| MAIN lap mating plane | 3,608.5 | 25.0 | **0.7 %** |
| MAIN rib | 499.2 | 25.0 | 5.0 % |
| **MAIN insert pilot** | 627.8 | 143.4 | **22.8 %** |
| ARMREST lap mating plane | 3,735.9 | 89.8 | 2.4 % |
| ARMREST rib | 527.7 | 27.8 | 5.3 % |
| **ARMREST screw seating** | 391.7 | 103.7 | **26.5 %** |

**주의 2곳 — 치수 영향 가능:**

1. **MAIN insert pilot 22.8 %** — ⌀5.6 구멍 축이 수평이라 상단은 브리지, 하단은
   아래보기가 된다. support 가 들어가면 **heat-set insert 삽입 전 제거·리밍 필요.**
   쿠폰으로 파일럿 지름을 정할 때 이 영향을 함께 봐야 한다.
2. **ARMREST screw seating 26.5 %** — ⌀8 카운터보어 바닥. 나사 머리 안착면이라
   평탄도가 중요하다. painted support 로 제외하거나 조립 전 면치기 권장.

lap 면과 리브의 25~90 mm² 는 원통·모서리 하단 스침이라 실질 영향 없음.

## F. SUPPORT STRATEGY

```
MAIN     plate-only 16,967.6 mm2 (기둥 96.2 cm3) / 파트 위 12,253.7 mm2 (1,103.9 cm3)
         커버율 58.1%  ->  **everywhere 필요**
ARMREST  plate-only  2,829.6 mm2 (41.2 cm3) / 파트 위    180.1 mm2 (1.5 cm3)
         커버율 94.0%  ->  **build-plate-only 로 충분**
```

- type: **normal / snug**. tree 는 이점 없음 (organic 외피 없음)
- MAIN: `everywhere` + **painted 로 외부 팔접촉면과 mating 면 제외**
- ARMREST: `build plate only`
- 제거 경로 (측지): MAIN 992.7 cm³ → CARRIER/LOWER 5.0 mm,
  ARMREST 80.7 cm³ → SPLIT/BED 10.0 mm

## G. BED STABILITY / BRIM

```
MAIN     접지 볼록껍질 8,925 mm2  둘레 384 mm
  brim  5mm -> 10,844 (+21.5%)   8mm -> 11,996 (+34.4%)   10mm -> 12,764 (+43.0%)
ARMREST  접지 8,125 mm2  둘레 381 mm
  brim  5mm -> 10,031 (+23.5%)
```

접지 8,925 mm² (95×95 mm 상당) + 세장비 2.47 이므로 **brim 5 mm 로 충분**.
8~10 mm 는 제거 수고만 늘린다. CUT FACE DOWN(1,520 mm²)이었으면 10 mm 가 필요했다.

## H. FINAL REVALIDATION — 전항목 PASS

```
BREP        MAIN / ARMREST / COUPON  전부 solid 1 / shell 1 / valid True
조립        joint 밖 부피 V4 891,741.176 = 조립 891,741.176,  점 표본 차이 0
            joint 안 doubler +58,668 mm3 (테이퍼로 116,454 -> 절반)
            nominal 조립본 1,007,928.642  solids 1 shells 1
23 gates    PASS 23 / FAIL 0
            W/L/H 133.6000 / 365.7597 / 140.5240
            deck->HAND_REF 55.8785  ground->HAND_REF 161.0208  stock_protrusion 0.0000
            캐리어 -Z 인출 0..100mm 무충돌
±15도       9자세(코너 포함) + 콘24 + 사각경계24 전부 0 / 12,000점
            최소 최초접촉각 15.88도 (방위 45/315)  여유 +0.88도
void        부각10/20/30, 측면 전부 0.0 mm2
STL         MAIN tri 22,386 / ARMREST 6,982 / COUPON 3,202
            경계 0 · 비다양체 0 · degenerate 0 · watertight True · mm
```

## REV B 산출물

```
export/step|stl/HOUSING_V4_MAIN_PRINT.*        (tapered doubler)
export/step|stl/HOUSING_V4_ARMREST_PRINT.*
export/step|stl/HOUSING_V4_SPLIT_ASSEMBLED.*
export/step|stl/JOINT_FIT_COUPON.*             (변경 없음)
preview/  9종 전부 재생성 (MAIN 은 CUT FACE UP 기준)
reports/  16_shoulder_orient.json / 16_shoulder_check.json / 16_joint_qc.json
```

## REV B 에서 고친 측정기 결함

| # | 증상 | 원인 | 조치 |
|---|---|---|---|
| 1 | 돌출 측정에 nan / 음수 | 정점 샘플 — 큰 평면 내부에 정점이 없다 | X 광선 |
| 2 | 돌출 +0.024 로 FAIL | tessellation 0.04 잡음 | 0.005 로 재측정 → 0.002 |
| 3 | joint 구간 실루엣 FAIL | Y 창 안 **내부 정점**까지 비교 — 실루엣이 아니다 | 지표 폐기, 광선 사용 |
| 4 | lap 면적 과대 | 테이퍼인데 `max(W0,W1)` | 사다리꼴 실면적 |
| 5 | opening 라벨 오류 | Rx 부호가 바뀌면 opening 면이 뒤집힌다 | 부호별 분기 |
| 6 | 프리뷰 제목 오류 | 두 파트 다 "CUT FACE DOWN" | 절단면 법선별 라벨 |

## 변경하지 않은 것

`MECHANICAL_HARDWARE_CONFIRMATION_REQUIRED` 그대로 유지:
M4 socket-cap(DIN 912) 표준 head 는 **⌀7.0 × 4.0 mm** 이고 현재 카운터보어는
⌀8.0 × **3.0** 이라 깊이가 1.0 mm 부족하다. 쿠폰 실물 결과 전까지
insert hole / clearance 와 함께 **변경하지 않았다.**

G-code 미생성.
