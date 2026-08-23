# P1S 2분할 제조 모델 — REV D (최종 제조 리비전)

joint hardware 값을 **전부 확정**한 최종 제조 리비전. 미확정 항목 없음.
REV B / REV C 는 덮어쓰지 않고 보존. G-code 미생성.

---

## 1. 이번 라운드 변경 — 2건

```
joint clearance   0.275 mm/side  PROVISIONAL              ->  0.30 mm/side  CONFIRMED
M4 counterbore    Ø8.0 x 3.0     CONFIRMATION_REQUIRED    ->  Ø8.0 x 4.2    CONFIRMED
```

### clearance 0.30 확정 근거

실물 clearance 쿠폰 추가 테스트 없이 확정.

- Bambu Lab P1S 의 일반적인 FDM 치수 편차
- joint 가 **M4 4개 clamp 체결** 구조
- press-fit 목적이 아니라 **조립성 + rib/lap 위치결정용** clearance
- male/female nominal total clearance = **0.60 mm**
- 0.30 mm/side 의 소량 유격은 M4 가 최종 clamp 하므로 허용

### counterbore Ø8.0 × 4.2 확정 근거

DIN 912 / ISO 4762 M4 socket-cap head = **Ø7.0 × 4.0 mm**.
기존 깊이 3.0 은 **1.0 mm 부족**했다 (지름 Ø8.0 은 원래 충분).
4.2 로 0.2 mm 여유를 두어 머리가 완전히 잠긴다.

## 2. 최종 joint hardware — 전부 CONFIRMED

| 항목 | 값 | 상태 |
|---|---|---|
| heat-set insert pilot | **Ø5.2 mm × 8.0** | CONFIRMED (REV C) |
| joint clearance | **0.30 mm/side** (total 0.60) | **CONFIRMED (REV D)** |
| M4 through hole | **Ø4.5 mm** | CONFIRMED |
| M4 counterbore | **Ø8.0 × 4.2 mm** | **CONFIRMED (REV D)** |
| fastener | **M4 DIN912 / ISO4762 socket-cap** | CONFIRMED |

**PROVISIONAL / CONFIRMATION_REQUIRED 항목 없음.**

### 파생값 — 나사 길이가 바뀐다

counterbore 심화로 필요 shank 가 달라졌다. 형상 변경이 아니라 조립 사양이다.

```
아래 판 두께               DBL_T - LAP_D = 7.0 mm
counterbore 4.2         -> 잔여 관통 구간  2.8 mm
insert 유효 깊이            8.0 mm
필요 shank                 2.8 + 8.0 = 10.8 mm

권장:  M4 x 10
```

> 기존 기록 `M4 x 12~14` 는 counterbore 3.0 기준이라 **무효**다.
> M4 × 12 는 1.2 mm 넘쳐 insert 바닥을 칠 수 있다.

## 3. 재빌드 결과

```
[joint] Y_UP -140.0 / Y_LO -112.0 / overlap 28.0 / lap_depth 7.0 / doubler 14.0 / clr 0.3

MAIN     solids 1  shells 1  valid True   vol 852,170.569 mm3
         bbox 133.600 x 233.800 x 154.583   Y[-140.00, 93.80]
ARMREST  solids 1  shells 1  valid True   vol 153,747.076 mm3
         bbox 126.743 x 159.660 x  74.949   Y[-271.96,-112.30]
부스러기 0 / 예상치 못한 공동 0
```

### 변경이 반영됐다는 검증

```
clearance 0.275 -> 0.30    틈  1,809.2 -> 1,973.7 mm3
counterbore 3.0 -> 4.2     FRONT 절삭  -840.2 -> -1,003.5 mm3
MAIN 부피                  852,170.569  변화 없음  (insert 만 있으므로 정상)
ARMREST 부피               154,074.915 -> 153,747.076
ARMREST bbox               126.749x159.685x74.960 -> 126.743x159.660x74.949
```

ARMREST bbox 가 clearance 증가분(0.025 mm/side)만큼 줄었다 — 절단면이 물러난 것과 정합.

## 4. 재검증 — 전항목 PASS

### joint strength (실제 REV D 단면)

| | 20 N | 50 N | 100 N | 허용 |
|---|---|---|---|---|
| 단면 굽힘 | 0.249 | 0.623 | **1.247** | 25.0 MPa |
| doubler 굽힘 | 0.886 | 2.214 | **4.428** | 25.0 |
| 랩 전단 (3,152 mm²) | 0.0063 | 0.0159 | 0.0317 | 8.0 (층간) |
| 리브 전단 (220 mm²) | 0.0909 | 0.2273 | 0.4545 | 15.0 |
| M4 1개 인장 | 14.48 N | 36.21 N | **72.42 N** | 항복 약 2,400 N |

**100 N PASS. 최대 사용률 17.7 %** (doubler 4.428 / 25.0).

clearance +0.025 와 counterbore +1.2 는 하중 경로에 영향이 없다 —
랩 접합 면적 3,152 mm² 와 doubler 단면이 그대로이기 때문이다.

### 조립 / 외부 차이

```
joint 밖 부피   V4 891,741.176  ==  조립 891,741.176
점 표본 60,000  V4에만 0 / 조립본에만 0
[PASS] visible external difference = 0
joint 안        doubler +58,164.2 / clearance·나사 -755.4   (의도된 차이)
nominal 조립본  1,007,872.282   solids 1  shells 1
```

### 23 gates — PASS 23 / FAIL 0

```
W / L / H              133.6000 / 365.7597 / 140.5240
deck -> HAND_REF        55.8785
ground -> HAND_REF     161.0208
stock protrusion         0.0000
캐리어 -Z 인출 0..100mm   무충돌
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
앞 0도 / 반대쪽 0도       3.9 mm2  (V4 와 동일, 해상도 의존 래스터 아티팩트)
```

### STL

| | BREP | 부피 | STL |
|---|---|---|---|
| MAIN | solid 1 / shell 1 / valid | 852,170.569 | tri 22,386 · 경계 0 · 비다양체 0 · degen 0 · **watertight True** |
| ARMREST | solid 1 / shell 1 / valid | 153,747.076 | tri 6,982 · 경계 0 · 비다양체 0 · degen 0 · **watertight True** |

단위 mm.

## 5. 출력 설정 (REV B 에서 확정, 변경 없음)

```
MAIN     CUT FACE UP   (Rx -90)   print bbox 133.600 x 154.583 x 233.800
         bed contact 8,955 mm2    slenderness 2.47
         support  everywhere + painted / normal·snug / brim 5 mm
         TRUE TRAPPED 0

ARMREST  CUT FACE DOWN (Rx -90)   print bbox 126.7 x 75.0 x 159.7
         support  build-plate-only / normal·snug / brim 5 mm
         TRUE TRAPPED 0

두 부품 각각 별도 print job.
```

### 조립 전 필수 조치

```
1. MAIN insert pilot 부위 support 제거
2. hole cleanup (Ø5.2 리밍 또는 드릴 정리)
3. **유효 지름 실측 확인**  <- 잔여물로 5.2 아래가 되면 insert 가 안 들어간다
4. ARMREST 나사 안착면(카운터보어 바닥) support 제거 / 필요시 면치기
```

insert pilot 아래보기 비율 21.9 % (607.2 mm² 중 133.2 mm²) — 구멍 축이 수평이라
상단은 브리지, 하단은 아래보기가 된다.

## 6. REV D 산출물

```
export/step/HOUSING_V4_MAIN_PRINT_REV_D.step         5.21 MB   <- 최종 제조
export/stl/HOUSING_V4_MAIN_PRINT_REV_D.stl           1.07 MB
export/step/HOUSING_V4_ARMREST_PRINT_REV_D.step      0.90 MB
export/stl/HOUSING_V4_ARMREST_PRINT_REV_D.stl        0.33 MB
export/step/HOUSING_V4_SPLIT_ASSEMBLED_REV_D.step    5.70 MB   (검증용 nominal 조립본)
```

`HOUSING_V4_*_PRINT.*` (접미사 없음) = 최신 = REV D 내용.

### 보존 (덮어쓰지 않음)

```
HOUSING_V4_*_PRINT_REV_B.*                REV B  (insert Ø5.6 / clr 0.275 / cbore 3.0)
HOUSING_V4_*_PRINT_REV_C.*                REV C  (insert Ø5.2 / clr 0.275 / cbore 3.0)
JOINT_FIT_COUPON.step / .stl              calibration artifact — 무수정 (160,184 bytes)
ERGO_HOUSING_25_WRAP_FINAL_V4.*           원본 — 읽기만
reports/15_p1s_split_print_engineering.md          REV B
reports/15_p1s_split_print_engineering_REV_C.md    REV C
```

## 7. 리비전 이력

| REV | insert pilot | clearance | counterbore | 비고 |
|---|---|---|---|---|
| B | Ø5.6 provisional | 0.275 provisional | Ø8.0 × 3.0 확인필요 | tapered doubler + MAIN CUT FACE UP |
| C | **Ø5.2 CONFIRMED** | 0.275 provisional | Ø8.0 × 3.0 확인필요 | 쿠폰 실물 결과 반영 |
| **D** | **Ø5.2** | **0.30 CONFIRMED** | **Ø8.0 × 4.2 CONFIRMED** | **미확정 0건, 최종 제조** |

## 8. STOP

최종 manufacturing revision 저장 완료. G-code 미생성.
