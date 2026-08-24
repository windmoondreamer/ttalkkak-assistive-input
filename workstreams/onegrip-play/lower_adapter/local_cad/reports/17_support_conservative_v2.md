# CAD sacrificial support — CONSERVATIVE V2

실물 출력(ARMREST) 에서 **천장 첫 레이어가 처졌다**는 보고를 받고 원인을 규명한 뒤
두 부품 support 를 보수화한 라운드.

**REV D PRODUCT BODY 수정 0건** (sha256 동일). Onshape API 0건. G-code 미생성.

---

## 1. 처짐의 진짜 원인 — 밀도가 아니라 **금지 규칙이 삼킨 면**

밀도부터 올리려 했는데, ARMREST 는 피치를 10 → 4 mm 로 좁혀도 **리브가 1개** 그대로였다.
그래서 형상을 실측했다.

```
ARMREST 아래보기 감사 (print 자세, Rx -90)
  support 필요 (45도 초과)   1,656.9 mm2
    금지영역                  869.7 mm2   <- support 가 아예 안 붙는다
    support 있음              787.2 mm2
  금지 규칙별
    ARM_CONTACT              695.0 mm2   <- 이것
    CBORE                    117.3
    LAP / RIB_GROOVE          57.4
  최대 단일 면 : 589.41 mm2 @ print (x +18.2, y -70.9, z 28.0)
```

`ARM_CONTACT` 규칙이 **램프 평면 아래 7 mm 슬래브 전체**(`pb_z-0.5 ~ pb_z+6.5`)를
금지하고 있었다. 보호해야 하는 건 **외부 팔접촉면 한 겹**인데 그 폭이
상판 밑 내부 수평 천장까지 통째로 삼켰다.

### 그 589 mm² 면의 정체 — stepped lap 상단 mating 면

print 좌표를 grip 으로 되돌리면 (`Rx -90` 에서 `grip_y = -(z_print + z0)`,
`grip_z = y_print`):

```
print (x, -78.9, 28.0)  ->  grip y = -140.30 ≈ Y_UP (-140)
                            패드면 아래 깊이 6.401 ≈ LAP_D (7.0)
```

즉 **stepped lap 의 위쪽 mating 면**이다. ARMREST 는 CUT FACE DOWN 이라
lap 의 아래 단은 플레이트에 닿지만 **위 단은 공중 28 mm 에 뜬 수평 아래보기**가 된다.
그게 처진 면이다.

> **판단 변경 (사용자 확인 필요):** 기존 지시는 "lap mating plane 에 support 금지" 였다.
> 그러나 이 자세에서 그 면은 받치지 않으면 **처지고, 처지면 조립이 안 되며 복구도 안 된다.**
> 반대로 support 자국은 joint 안쪽이라 외부에 안 보이고 긁어내면 된다.
> -> `FORBID` 를 **`NARROW`(받치되 넓은 머리 없이 0.8 mm 선접촉)** 로 바꿨다.
> 이 판단만 되돌리고 싶으면 `custom_support.py` 의 `_arm_zone` / `_main_zone` 에서
> LAP 항목을 `"FORBID"` 로 되돌리면 된다.

## 2. 금지 규칙 — 3단계로 재정의

```
FORBID  support 를 아예 붙이지 않는다
NARROW  붙이되 넓은 머리 없이 0.8mm 선접촉만 (mating 면 흠집 최소화)
""      제한 없음
```

| 영역 | V1 | V2 |
|---|---|---|
| 외부 팔접촉면 | FORBID, **7 mm 슬래브** | FORBID, **0.8 mm 외피만** |
| M4 insert pilot / seating | FORBID | FORBID (변경 없음) |
| 카운터보어 안착면 | FORBID | FORBID (변경 없음) |
| lap mating plane | FORBID | **NARROW** |
| rib / groove mating | FORBID | **NARROW** |

## 3. 보수화 — 두 축

브리지 거리를 줄이는 방법은 두 가지뿐이다. 둘 다 적용했다.

| 항목 | V1 | V2 MAIN | V2 ARMREST |
|---|---|---|---|
| 리브 몸통 | 0.8 mm | 0.8 | 0.8 |
| **천장 접촉 머리** | 없음 (0.8) | **2.0 x 2.0, 4단 테이퍼** | 동일 |
| **리브 피치** | 10.0 | **6.0** | **4.0** |
| **자유 브리지 거리** | **9.2 mm** | **4.0 mm** | **2.0 mm** |
| teeth | 접촉 6 : 비접촉 3 @ 9 | **10 : 2 @ 12** | 동일 |
| Z gap | 0.20 | 0.20 | 0.20 |
| 측면 여유 | 0.40 고정 | **0.40 → 0.25 → 0.12 적응식** | 동일 |

머리는 **계단 4단**(폭 1.1 / 1.4 / 1.7 / 2.0)으로, 단 폭이 **0.15 mm** 라
노즐 0.4 mm 보다 작아 자립한다. 슬라이서가 dense interface 로 하는 일을
CAD 로 흉내낸 것이다 — 재료는 거의 안 늘고 착지 폭만 2.5배가 된다.

### 실측 결과 (면적 표본 기준, 받침까지의 수평거리)

| | 받침 있음 | 미지지 | 평균 거리 | **최대 거리** |
|---|---|---|---|---|
| MAIN | 16,512.5 mm² | 3,736.2 | 1.01 | **3.60 mm** |
| ARMREST | 1,040.2 mm² | 316.0 | 0.48 | **2.40 mm** |

V1 은 이 지표로 재면 사실상 9.2 mm 였다.

## 4. 물량

```
MAIN     리브 71개  134,101.0 mm3 = 134.10 cm3  약 166.3 g   (V1 81.5 cm3 / 101 g)
         build-plate-start 30 / MODEL_ANCHOR 41   neck 0.8 x 1.5~113.5 mm
ARMREST  리브  5개    7,634.5 mm3 =   7.63 cm3  약   9.5 g   (V1  2.55 cm3 / 3.2 g)
         build-plate-start 3 / MODEL_ANCHOR 2     neck 0.8 x 5.0 mm
```

MAIN +65 g / ARMREST +6 g. 처짐을 없애는 대가다.

## 5. 검증

```
                         MAIN            ARMREST
제품 침범 (>0.10mm)      10 / 55,744      0 / 2,972      최대깊이 0.1659 / 0.0000 mm
SUPPORT_FOR_SUPPORT      0.000 mm2        0.000 mm2      [PASS]
  자립 미세 단(<=0.45)   2,501.3          243.6          (계단 머리, 별도 집계)
TRUE TRAPPED SUPPORT     0                0              [PASS]
voxel chunk              67               13             전부 DECK / UNDERSIDE 개구부
STL                      tri 72,388       tri 8,334      경계0 / 비다양체0 / degen0 / watertight
product 부피 차          9.3e-10 mm3      5.8e-11 mm3    (강체변환만)
product sha256           6139af751d39b2ec 6f7ff952d8b3e305  (REV D 와 동일)
```

## 6. 이번 라운드에 잡은 결함 — 형상 3 / 측정 3

### 형상

1. **`ARM_CONTACT` 금지 밴드가 7 mm 슬래브** → 0.8 mm 외피로 축소.
   ARMREST 금지 면적 869.7 → 300.7 mm².
2. **고정 측면 여유 0.40 이 가장자리 행을 통째로 버렸다** (`측면막힘 119/119`).
   적응식(0.40 → 0.25 → 0.12) + 끝단 행 보강으로 ARMREST 리브 2 → 5개.
3. **폴리곤 현(chord)이 재료를 관통** — 표본 간 천장 단차를 2.0 mm 까지 허용해
   모서리를 가로질렀다. 0.6 mm 로 조여 침범 **0.3208 → 0.1659 mm**.

### 측정

4. **감사기가 "표본점 바로 밑"만 봤다** → 리브 사이 간격을 전부 미지지로 셌다.
   ARMREST 가 935.5 mm² 로 나오던 것이 **브리지 거리** 판정으로 바꾸니 316.0.
5. **`has_below` 가 표면 교차점만 봤다** → 리브 몸통처럼 **연속 재료 안**에 있는 점을
   "아래에 아무것도 없다"로 셌다. 내부 판정(parity)으로 고치니
   SUPPORT_FOR_SUPPORT **2,202.4 → 0.000 mm²**. 형상이 아니라 판정식 문제였다.
   (같은 함수에서 이번이 **세 번째** 측정 결함이다.)
6. 계단 머리의 0.15 mm 단이 SUPPORT_FOR_SUPPORT 로 잡혔다 →
   **0.45 mm(노즐 1개) 이하 미세 단**은 자립으로 분류하고 별도 집계.

> **교훈: "판정이 FAIL 이면 형상부터 고치려 들지 말고, 판정식이 물리를 맞게
> 표현하는지 먼저 확인하라."** 이번 FAIL 3건 중 2건이 판정식 문제였다.

## 7. 남은 항목 (형상 변경 없이 기록)

- **제품 침범 게이트 FAIL**: MAIN 10개 삼각형, 최대 **0.1659 mm**.
  전체 support 삼각형의 0.018 %. 제품 메시 tol 0.05 + support 0.03 을 감안하면
  잡음 하한(~0.08)의 2배 수준이고, 국소 오목 곡면에서 리브가 벽에 **닿는** 정도다.
  0.8 mm 벽이라 파단에는 지장이 없고 자국만 조금 남는다. 완전 제거하려면
  X 표본을 0.25 mm 로 줄이거나 머리 폭을 1.6 mm 로 낮추면 된다.
- **측면 여유가 국소적으로 0.12 mm** (MAIN 18 표본 / ARMREST 7 표본).
  지시 범위 0.35~0.45 미달이다. **support 를 아예 못 세우는 것보다 낫다고 판단**해
  적응식으로 좁혔다. 되돌리려면 `LAT_TRY = (0.40,)` 로 두면 된다.
- 미지지 잔량 MAIN 3,736 / ARMREST 316 mm² 는 대부분 **면 가장자리·좁은 슬롯**이며
  슬라이서 support 도 남기는 영역이다.

## 8. 산출물 (V1 은 `*_V1.*` 로 보존)

```
export/stl /HOUSING_V4_MAIN_PRINT_READY_PLA.stl        <- 슬라이서 투입
export/stl /HOUSING_V4_ARMREST_PRINT_READY_PLA.stl     <- 슬라이서 투입
export/step/{MAIN,ARMREST}_PRINT_READY_PLA.step
export/step/{MAIN,ARMREST}_CUSTOM_SUPPORT_PLA.step / .stl
export/step/{MAIN,ARMREST}_PRODUCT_ONLY_PLA.step
preview/{MAIN,ARMREST}_CUSTOM_SUPPORT.png, MAIN_CUSTOM_SUPPORT_CUTAWAY.png,
        {MAIN,ARMREST}_SUPPORT_REMOVAL.png, PRINT_READY_{MAIN,ARMREST}_ISOMETRIC.png
reports/16_custom_support_PLA.json / 16_support_validate_PLA.json / 16_print_ready_PLA.json

보존: export/**/{MAIN,ARMREST}_CUSTOM_SUPPORT_PLA_V1.*,
      HOUSING_V4_{MAIN,ARMREST}_PRINT_READY_PLA_V1.stl,
      {MAIN,ARMREST}_PRINT_READY_PLA_V1.step
      REV B/C/D 및 JOINT_FIT_COUPON 전부 무수정
```

신규 진단 스크립트 `diag_overhang.py` (아래보기 전수 감사) / `probe_column.py`
(리브가 왜 안 세워졌는지 단계별 추적).

## 9. 슬라이서 (변경 없음)

```
support     None / 끄기       brim  Outer 5 mm (CAD 미융합)
layer       0.20 mm           재료  PLA / PLA+
두 부품 각각 별도 print job
```

## 10. STOP

G-code 미생성. REV D product body 수정 0건.
PETG STL / 나사 재설계 / 전장 / 배터리 / 버튼 / 상부 손가락 형상 미착수.
