# P1S 2분할 제조 모델 — REV C (제조 확정)

`JOINT_FIT_COUPON` 실물 테스트 결과를 반영한 **제조 확정 기록**.
REV B (`15_p1s_split_print_engineering.md`) 는 덮어쓰지 않고 그대로 보존.

**이번 라운드 변경: M4 heat-set insert pilot Ø5.6 → Ø5.2 mm, 그 하나뿐이다.**
G-code 미생성.

---

## 1. 변경 내용

```
MAIN  M4 heat-set insert pilot   Ø5.6  ->  Ø5.2 mm   (깊이 8.0 유지)
```

`split_build.py` 의 `D_INSERT` 한 값만 바꿨다.

### 변경이 실제로 반영됐다는 검증

절삭량이 기하학적 예상치와 **정확히** 일치한다.

```
Ø5.6 : 4 x pi x 2.8^2 x 8 = 788.2 mm3      (REV B 실측 -788.2)
Ø5.2 : 4 x pi x 2.6^2 x 8 = 679.6 mm3      (REV C 실측 -679.6)
MAIN 부피  852,061.995 -> 852,170.569       (+108.6 = 788.2 - 679.6)
```

### 유지된 항목 (변경 금지 대상 전부)

```
joint clearance      0.275 mm/side          M4 through hole   Ø4.5
counterbore          Ø8.0 x 3.0             tapered doubler   W0 54.035 / W1 58.525
overlap              28 mm                  rib / groove      X ±12, 5.0 x 2.5
MAIN                 CUT FACE UP (Rx -90)   ARMREST           CUT FACE DOWN (Rx -90)
외형 / V4 core / ±15도 cavity               전부 그대로
```

## 2. 하드웨어 상태

| 항목 | 값 | 상태 |
|---|---|---|
| **M4 heat-set insert pilot** | **Ø5.2 mm × 8.0** | **CONFIRMED** |
| joint clearance | 0.275 mm/side | **STILL PROVISIONAL** |
| M4 counterbore | Ø8.0 × 3.0 mm | **MECHANICAL_HARDWARE_CONFIRMATION_REQUIRED** |

### insert pilot 확정 근거

```
기존 Galaxy Tab housing 에서 약 Ø5.15 mm 사용
동일 M4 heat-set insert
JOINT_FIT_COUPON 실물 출력 확인
-> Ø5.2 mm 채택
```

### counterbore 미확정 사유

DIN 912 / ISO 4762 M4 socket-cap 의 표준 head 는 **Ø7.0 × height 4.0 mm** 다.
현재 깊이 3.0 mm 로는 **1.0 mm 부족**하다 (지름 Ø8.0 은 충분).
아래 판이 6.0 mm 이므로 깊이 4.0 으로 늘려도 잔여 2.0 mm 는 확보되지만,
**이번 라운드에서는 지시대로 변경하지 않았다.**

## 3. MAIN 재빌드 검증

```
MAIN     solids 1   shells 1   valid True   vol 852,170.569 mm3
         bbox 133.600 x 233.800 x 154.583   Y[-140.00, 93.80]
         unexpected fragment 0 / unexpected void 0
ARMREST  solids 1   shells 1   valid True   vol 154,074.915 mm3
```

### ARMREST 무변경 증명

```
부피          154,074.915  ==  154,074.915        (REV B 와 동일)
STL sha256    2578357020df32e1  ==  2578357020df32e1
```

insert 는 MAIN 에서만 절삭되므로(`m2 = main_p - ins`) ARMREST 는 바이트 단위로 동일하다.

## 4. SUPPORT 재확인 — insert pilot 부위만

CUT FACE UP 유지.

| | Ø5.6 (REV B) | **Ø5.2 (REV C)** |
|---|---|---|
| insert pilot 총면적 | 627.8 mm² | **607.2 mm²** |
| 아래보기 면적 | 143.4 | **133.2** |
| 비율 | 22.8 % | **21.9 %** |

면적 −3.3 %, 비율은 거의 동일. **구멍 축이 수평이라 상단은 브리지 / 하단은
아래보기가 되는 구조는 변하지 않는다.**

### heat-set insert 삽입 전 조치 — 필요 (강화)

```
1. support 제거
2. hole cleanup (Ø5.2 리밍 또는 드릴 정리)
3. **실측 확인 필수**
```

파일럿이 0.4 mm 작아졌으므로 **잔여물 허용폭이 그만큼 줄었다.** 정리 후 유효 지름이
5.2 아래로 내려가면 insert 가 들어가지 않는다. REV B 때보다 이 확인이 더 중요하다.

### 다른 mating 면 — 변화 없음

```
MAIN     lap mating plane 0.7 %   rib 5.0 %
ARMREST  lap mating plane 2.4 %   rib 5.3 %   screw seating 26.5 %
```

### support 전략 — 변경 없음

```
MAIN     everywhere + painted / normal·snug / brim 5 mm   (plate-only 커버율 58.1 %)
ARMREST  build-plate-only     / normal·snug / brim 5 mm   (커버율 94.0 %)
```

## 5. ASSEMBLY / MOTION 재검증 — 전항목 PASS

```
조립 재구성
  joint 밖 부피   V4 891,741.176  ==  조립 891,741.176
  점 표본 60,000  V4에만 0 / 조립본에만 0          -> visible external difference = 0
  joint 안        doubler +58,667.8 / clearance·나사 -755.4  (의도된 차이)
  nominal 조립본  1,008,037.216   solids 1  shells 1

23 gates        PASS 23 / FAIL 0
  W / L / H              133.6000 / 365.7597 / 140.5240
  deck -> HAND_REF        55.8785
  ground -> HAND_REF     161.0208
  stock protrusion         0.0000
  캐리어 -Z 인출 0..100mm   무충돌

±15도 motion
  neutral / Pitch ±15 / Roll ±15 / corner 4개    전부 간섭 0 / 12,000점
  24방향 azimuth cone @15도                      합계 0
  24방향 square boundary @15도                   합계 0
  최소 최초접촉각 15.88도 (방위 45/315)   여유 +0.88도

void 감사
  앞 부각10/20/30도, 측면   전부 0.0 mm2
  앞 0도 / 반대쪽 0도       3.9 mm2  (V4 와 동일, 해상도 의존 래스터 아티팩트)
```

## 6. STL 품질

| | BREP | 부피 | STL |
|---|---|---|---|
| HOUSING_V4_MAIN_PRINT | solid 1 / shell 1 / valid | 852,170.569 | tri 22,386 · 경계 0 · 비다양체 0 · degen 0 · **watertight True** |
| HOUSING_V4_ARMREST_PRINT | solid 1 / shell 1 / valid | 154,074.915 | tri 6,982 · 경계 0 · 비다양체 0 · degen 0 · **watertight True** |

단위 mm.

## 7. REV C 산출물

```
export/step/HOUSING_V4_MAIN_PRINT_REV_C.step          5.21 MB   <- 제조 확정
export/stl/HOUSING_V4_MAIN_PRINT_REV_C.stl            1.07 MB
export/step/HOUSING_V4_ARMREST_PRINT_REV_C.step       0.90 MB   (형상 REV B 와 동일)
export/stl/HOUSING_V4_ARMREST_PRINT_REV_C.stl         0.33 MB
export/step/HOUSING_V4_SPLIT_ASSEMBLED_REV_C.step     5.70 MB   (검증용 nominal 조립본)
```

### 보존 (덮어쓰지 않음)

```
export/step|stl/HOUSING_V4_MAIN_PRINT_REV_B.*         REV B
export/step|stl/HOUSING_V4_ARMREST_PRINT_REV_B.*      REV B
export/step|stl/JOINT_FIT_COUPON.*                    calibration artifact — 무수정
export/step|stl/ERGO_HOUSING_25_WRAP_FINAL_V4.*       원본 — 읽기만
reports/15_p1s_split_print_engineering.md             REV B 보고서
```

`HOUSING_V4_*_PRINT.*` (rev 접미사 없음) 는 최신 = REV C 내용이다.

## 8. 남은 미확정 사항

```
CONFIRMED
  M4 heat-set insert pilot = Ø5.2 mm

STILL PROVISIONAL
  joint clearance = 0.275 mm/side
    -> 쿠폰의 0.20 / 0.25 / 0.275 / 0.30 / 0.35 tongue-groove 쌍으로 확정 필요

MECHANICAL_HARDWARE_CONFIRMATION_REQUIRED
  M4 counterbore = Ø8.0 x 3.0 mm
    -> DIN912 M4 사용 시 head height 4.0 mm 이므로 깊이 +1.0 mm 수정 가능성
    -> 실제 사용할 나사 제원 확정 후 재검토
  M4 나사 길이 = M4 x 12~14 (provisional)
    -> 머리 3.0 + 아래판 잔여 3.0 + insert 8.0
```

**이번 라운드에서 위 둘은 수정하지 않았다.**

## 9. STOP

Ø5.2 반영 / 재검증 / REV C 산출 완료. G-code 미생성.
