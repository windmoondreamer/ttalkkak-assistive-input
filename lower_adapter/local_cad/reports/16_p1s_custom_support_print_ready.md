# P1S CAD-INTEGRATED SACRIFICIAL SUPPORT — PRINT_READY (PLA)

Bambu Studio 에서 support painting 을 하지 않고 바로 슬라이싱할 수 있도록,
REV D 제조 형상에 **CAD 로 만든 희생 support 를 별도 solid 로** 얹은 파생 모델.

**REV D PRODUCT BODY 수정 0건.** G-code 미생성. Onshape API 호출 0건.

---

## 0. 소스 동결 증명

support 는 제품 body 를 한 번도 건드리지 않았다. 강체 회전(Rx −90)과 바닥 정렬
평행이동만 적용했고, 그 결과 부피가 소수점 이하까지 보존된다.

```
MAIN     HOUSING_V4_MAIN_PRINT_REV_D.step     sha256[:16] 6139af751d39b2ec
         HOUSING_V4_MAIN_PRINT_REV_D.stl                  577688df782cc23b
         부피  852,170.568896  ->  852,170.568896   차 9.313e-10 mm3

ARMREST  HOUSING_V4_ARMREST_PRINT_REV_D.step   sha256[:16] 6f7ff952d8b3e305
         HOUSING_V4_ARMREST_PRINT_REV_D.stl                ecfc2855ff7d97c3
         부피  153,747.075565  ->  153,747.075565   차 5.821e-11 mm3
```

joint / 확정 하드웨어(insert Ø5.2×8.0, clearance 0.30/side, 관통 Ø4.5,
카운터보어 Ø8.0×4.2) 전부 무변경. support 는 부울로 융합하지 않은 **분리 solid** 다.

## 1. 출력 자세 — 변경 없음

```
MAIN     CUT FACE UP   (Rx -90)   print bbox 133.600 x 154.583 x 233.800   바닥 z=0.000003
ARMREST  CUT FACE DOWN (Rx -90)   print bbox 126.743 x  74.949 x 159.660   바닥 z=-0.000003
```

두 부품 각각 별도 print job. P1S 256³ 이내.

## 2. support 구조 — 수직 리브 벽

solid block 을 쓰지 않았다. **print X 방향으로 달리는 얇은 수직 벽**을 print Y 로
등간격 배치한다. 리브가 수직벽이라 **자기 자신을 지지할 필요가 구조적으로 없다**
(§9 의 SUPPORT_FOR_SUPPORT = 0 이 이 선택의 직접 결과다).

| 항목 | 값 | 비고 |
|---|---|---|
| 리브 두께 = 접촉 rail 폭 | **0.8 mm** | 벽 0.6~0.8 / rail 0.8~1.2 를 한 값으로 동시 충족 |
| 리브 간격 | **10.0 mm** | 요구 8~12 의 중앙 |
| 천장 Z gap (PLA) | **0.20 mm** | 0.2 mm 레이어 = 정확히 1층 |
| 측면 clearance | **0.40 mm** | 요구 0.35~0.45. 리브 중심선 ±(0.4+0.4) 광선으로 강제 |
| teeth | 접촉 **6.0** : 비접촉 **3.0** @ 주기 9.0 mm, 노치 깊이 1.2 | 천장 접촉을 끊어 파단시킨다 |
| 아래보기 기준 | 45.0° (`nz < −0.7071`) | Bambu 기본 임계와 동일 |
| 최소 리브 높이 | 1.2 mm | 이보다 낮은 틈은 support 없이 브리지 |

X 표본 0.5 mm 로 천장·바닥을 추종하고, **바닥이 0.8 mm 이상 튀거나 천장이 2.0 mm
이상 튀면 리브를 끊는다.** 이 두 규칙이 §11 의 결함 2건을 해소한 핵심이다.

## 3. MAIN — support 물량과 앵커

```
리브 43개 (= solid 43개)   부피 81,493.8 mm3 = 81.49 cm3   PLA 약 101.1 g
리브 길이 1.0 ~ 113.0 mm   총 접촉 길이 1,664 mm   리브 높이 2.3 ~ 158.2 mm

build-plate-start   16개   (빌드플레이트에서 시작 — 최우선)
MODEL_ANCHOR        27개   (내부 면에서 시작)
```

### 앵커 neck 치수 (§5 요구)

모든 앵커의 neck 은 **리브 두께 그대로 0.8 mm 폭**이고, 접촉 길이만 다르다.

| y (print) | x 범위 | neck | z 범위 |
|---|---|---|---|
| −161.0 | −56.3 ~ +56.7 | 0.8 × 113.0 | 7.5 → 131.1 |
| −81.0 | −52.8 ~ +52.7 | 0.8 × 105.5 | 113.7 → 199.6 |
| −71.0 | −48.3 ~ +48.7 | 0.8 × 97.0 | 117.6 → 199.6 |
| −81.0 | −40.8 ~ +41.2 | 0.8 × 82.0 | 16.1 → 114.6 |
| −101.0 | −34.3 ~ +30.2 | 0.8 × 64.5 | 20.8 → 104.4 |
| −111.0 | −32.8 ~ +28.7 | 0.8 × 61.5 | 20.8 → 103.6 |

(전체 27개는 `reports/16_custom_support_PLA.json` 의 `ribs[]` 에 있다.)

neck 이 0.8 mm 단일 벽이라 라디오펜치로 비틀면 그 선에서 끊어진다.
앵커면은 전부 **비가시 내부면**이다 — 금지영역 판정을 천장뿐 아니라 **바닥에도**
적용했고, 그 결과 금지면에 앉은 앵커는 0개다.

### 금지영역 (support 미생성)

```
external arm-contact surface    lap mating plane        rib / groove mating
M4 insert pilot Ø5.2 내부       insert seating region
```

배제된 표본 14개. **insert pilot 은 CAD support 를 넣지 않았다** — 구멍 축이
수평이라 상단은 브리지로 뽑고, 출력 후 Ø5.2 리밍으로 정리하는 쪽이 낫다
(REV C/D 에서 확정한 방침 유지).

## 4. ARMREST — 최소 support

```
리브 1개   부피 2,553.5 mm3 = 2.55 cm3   PLA 약 3.2 g
길이 116.5 mm   높이 27.8 mm
build-plate-start 1개 / MODEL_ANCHOR 0개
```

**앵커가 하나도 없다.** 유일한 리브가 빌드플레이트에서 올라온다.
카운터보어 Ø8.0×4.2 안착면을 포함해 금지영역 표본 22개를 배제했으므로
**나사 머리 안착면은 support 가 닿지 않는다.**

## 5. 인출 검증 (§8) — TRUE TRAPPED SUPPORT = 0

1.5 mm 복셀 free-space 연결성 + EDT 위드스트-패스 병목으로 판정했다.

| | MAIN | ARMREST |
|---|---|---|
| 복셀 chunk | 28개 (8 mm³ 이상 23개) | 1개 |
| 인출 개구부 | **전부 DECK_OPENING** | **UNDERSIDE_OPEN** |
| 인출 방향 (print) | **+Y** | **+Y** |
| 최소 통과 여유 (전체) | **1.2 mm** | **5.6 mm** |
| 최소 통과 여유 (≥500 mm³ chunk) | **4.4 mm** | 5.6 mm |
| **TRUE TRAPPED** | **0** | **0** |

주요 chunk (복셀 부피 / bbox / 통과 여유):

```
17,118 mm3   94.5 x 1.5 x 147.0   DECK_OPENING  +Y   20.0 mm
12,940       106.5 x 1.5 x  85.5  DECK_OPENING  +Y   14.8
11,678        82.5 x 1.5 x  97.5  DECK_OPENING  +Y   20.0
 7,661        60.0 x 1.5 x  85.5  DECK_OPENING  +Y   20.0
 7,580        61.5 x 1.5 x  82.5  DECK_OPENING  +Y   20.0
 7,452        40.5 x 1.5 x 123.0  DECK_OPENING  +Y   20.0
 7,449        40.5 x 1.5 x 123.0  DECK_OPENING  +Y   20.0
 6,733        28.5 x 1.5 x 157.5  DECK_OPENING  +Y   20.0
 2,055 / 2,025 / 1,995 / 1,995     DECK_OPENING  +Y   14.0~15.6
 1,154 / 1,154 / 1,046 / 1,043     DECK_OPENING  +Y    4.4~13.2
```

통과 여유 1.2 mm 는 **10 mm³(복셀 1칸) 짜리 조각 하나**뿐이다. 0.8 mm 벽의
1.5 mm 복셀화 잔여물이며 손으로 집을 크기도 아니다.

> 복셀 합계 91,607 mm³ 가 BREP 부피 81,494 mm³ 보다 큰 것은 정상이다 —
> 0.8 mm 벽을 1.5 mm 복셀로 재면 폭이 과대평가된다. 물량은 BREP 값을 쓴다.

## 6. SUPPORT_FOR_SUPPORT (§9)

support 자체의 아래보기 면 중 **바로 아래에 재료(제품·support·플레이트)가 없는**
면적을 잰다.

```
MAIN     0.441 mm2   (z 20.7 한 높이, y −70.8 한 줄)
ARMREST  0.000 mm2
```

MAIN 의 0.441 mm² 는 리브 밑면이 곡면 바닥을 따라갈 때 0.5 mm 표본 사이에
생기는 미세 계단이며, 기준 1.0 mm² 미만 → **PASS**. 실질적으로 0 이다.

## 7. 제품 침범 (§11 내부 기능 차이)

```
MAIN     support 삼각형 중심 6,464개 중 제품 내부 52개   최대 깊이 0.0983 mm
         0.10 mm 초과(실침범)  0     [PASS]
ARMREST  0 / 220              최대 깊이 0.0000 mm       [PASS]
```

0.1 mm 미만은 tessellation 잡음이다 (이 프로젝트에서 이미 두 번 확인된 현상 —
`shoulder_check` 의 0.0240 mm → tol 정밀화 시 0.0020 mm).
**설계 gap 0.20 mm 보다 작아서 실제 접촉조차 아니다.**

## 8. body-only 검증 (§11)

support 를 제거하면 REV D 제품이 그대로 남는다. 이번 라운드에서 다시 돌렸다.

```
조립 재구성   joint 밖 부피  V4 891,741.176  ==  조립 891,741.176
              점 표본 60,000  V4에만 0 / 조립본에만 0
              -> visible external difference = 0   [PASS]

23 gates      PASS 23 / FAIL 0
              deck -> HAND_REF     55.8785
              ground -> HAND_REF  161.0208
              stock protrusion      0.0000
              캐리어 -Z 인출 0..100mm  무충돌

±15도 motion  9자세(코너 4개 포함) + 콘24 + 사각경계24  전부 간섭 0
              최소 최초접촉각 15.88도 (방위 45/315)  여유 +0.88도
```

support 형상은 위 게이트에서 **제외**했다 (지시대로). 제품 body 가 바이트 단위로
동일하므로 REV D 결과와 동일하게 나오는 것이 정합이다.

## 9. STL 품질 (§12)

PRINT_READY 는 multi-shell 이 정상이고 shell 1 을 강제하지 않았다.
각 shell 은 아래 조건을 만족한다.

| 파일 | 삼각형 | 경계 | 비다양체 | degenerate | watertight |
|---|---|---|---|---|---|
| HOUSING_V4_MAIN_PRINT_READY_PLA.stl | 23,108 | 0 | 0 | 0 | **True** |
| HOUSING_V4_ARMREST_PRINT_READY_PLA.stl | 5,582 | 0 | 0 | 0 | **True** |

단위 mm. tolerance 0.03 / angular 0.2.

## 10. 슬라이서 설정

```
support type        None / 끄기        <- CAD support 가 이미 들어 있다
brim                Outer brim 5 mm    <- CAD 에 융합하지 않았다. 슬라이서 설정으로만
layer               0.20 mm            <- interface gap 0.20 = 정확히 1층
material            PLA / PLA+
두 부품 각각 별도 print job
```

**brim 을 CAD 에 넣지 않은 이유**: brim 을 solid 로 붙이면 body-only 대조가
깨지고 첫 레이어 압출 보정을 슬라이서가 못 한다. mouse-ear 가 필요하면 별도
STL 로 추가하되 base PRINT_READY 모델에는 넣지 않는다 (§10 지시 그대로).

### 출력 후 순서

```
1. MAIN 을 +Y 로 눕혀 DECK_OPENING 쪽에서 리브를 뽑는다 (23 chunk 전부 이 방향)
2. 앵커 neck 0.8 mm 를 비틀어 파단  -> 내부면에 0.8 mm 자국만 남는다
3. ARMREST 는 플레이트에서 리브 1개만 떼면 끝
4. M4 insert pilot Ø5.2 리밍 + **유효 지름 실측**   <- CAD support 없음, 브리지 출력
5. ARMREST 카운터보어 바닥 확인 (support 미접촉이지만 육안 확인)
```

## 11. 이번 라운드에서 잡은 결함 3건

전부 **리브 폴리곤의 x 방향 이음** 문제였고, 검증기가 잡았다.

1. **표본 건너뛰기 이음** — 유효하지 않은 x 표본을 건너뛰고 폴리곤을 이어서
   직선이 재료를 관통했다. → 끊고 서브 폴리곤으로 분할.
2. **천장 급락 관통 (12.5 mm)** — x 0.5 mm 사이에서 천장이 15.7→161.9 / 15.7→123.8
   로 **38 mm 급락**하는데 바닥이 같아 run 이 이어졌고, 리브 윗면 대각선이
   재료를 뚫었다. 실침범 삼각형 2개의 정점 3개가 전부 **바깥**이라 정점 검사로는
   안 잡히고 **중심 검사**로만 드러났다. → `|Δb| > 2.0` 이면 run 을 끊는다.
3. **측정기 버그 — 표면에 얹힌 면을 "떠 있다"고 셌다.** `zp < p[2] − 1e-3` 로
   아래를 찾으면 리브가 정확히 얹힌 바닥(z 동일)이 제외돼 746 mm² 가 나왔다.
   → `zp <= p[2] + 0.05` 로 바꾸니 0.441 mm². **형상 결함이 아니라 판정식 결함**이었다.

> 교훈: 삼각형이 재료를 관통하는지 볼 때 **정점만 검사하면 놓친다.**
> 세 정점이 전부 바깥이어도 삼각형 내부는 관통할 수 있다.

## 12. 산출물

```
export/step/MAIN_PRINT_READY_PLA.step               12.61 MB  product + support (solid 분리)
export/stl /HOUSING_V4_MAIN_PRINT_READY_PLA.stl      1.16 MB  <- 슬라이서 투입
export/step/MAIN_CUSTOM_SUPPORT_PLA.step             6.86 MB  support 단독
export/stl /MAIN_CUSTOM_SUPPORT_PLA.stl              0.32 MB
export/step/MAIN_PRODUCT_ONLY_PLA.step               5.46 MB  body-only 대조군

export/step/ARMREST_PRINT_READY_PLA.step             1.16 MB
export/stl /HOUSING_V4_ARMREST_PRINT_READY_PLA.stl   0.28 MB  <- 슬라이서 투입
export/step/ARMREST_CUSTOM_SUPPORT_PLA.step          0.21 MB
export/stl /ARMREST_CUSTOM_SUPPORT_PLA.stl           0.01 MB
export/step/ARMREST_PRODUCT_ONLY_PLA.step            0.94 MB

preview/MAIN_CUSTOM_SUPPORT.png            preview/MAIN_CUSTOM_SUPPORT_CUTAWAY.png
preview/MAIN_SUPPORT_REMOVAL.png           preview/ARMREST_CUSTOM_SUPPORT.png
preview/ARMREST_SUPPORT_REMOVAL.png        preview/PRINT_READY_MAIN_ISOMETRIC.png
preview/PRINT_READY_ARMREST_ISOMETRIC.png

reports/16_custom_support_PLA.json    리브·앵커 전체 목록
reports/16_support_validate_PLA.json  chunk 별 인출 판정
reports/16_print_ready_PLA.json       조립·STL 품질
```

신규 스크립트: `build123d/custom_support.py` (생성), `support_validate.py` (검증),
`print_ready.py` (조립), `support_preview.py` (렌더), `diag_intrusion.py` (진단).

**REV B / REV C / REV D 및 `JOINT_FIT_COUPON` 전부 무수정 보존.**

## 13. PETG

`custom_support.py` 의 `MATERIAL` 에 `PETG: gap_z 0.28` 로 파라미터화해 두었다.
`python build123d/custom_support.py PETG` 로 생성 가능하나 **이번에 STL 은
만들지 않았다** (지시대로).

## 14. 남은 판단 항목 (형상 변경 아님)

- support 물량 **MAIN 101.1 g** 은 적지 않다. 리브 간격을 허용 상한 12 mm 로
  올리면 약 −17 % 다. 안정성을 택해 10 mm 를 썼다. 바꿀지는 사용자 판단.
- 통과 여유 1.2 mm 짜리 10 mm³ 조각 1개 — 복셀화 잔여물이라 실물에서는
  큰 리브의 일부다. 별도 조치 불필요로 판단.

## 15. STOP

PRINT_READY 형상 + 프리뷰 생성 완료. **G-code 미생성. REV D product body 수정 0건.**
M3/M4 나사 재설계 / 전장 / 배터리 / 버튼 / 상부 손가락 형상 미착수.
