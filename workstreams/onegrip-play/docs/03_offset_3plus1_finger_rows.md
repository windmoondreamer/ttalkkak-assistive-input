# 오프셋 3+1 검지/중지 Row 배치 분석 (READ ONLY)

- 조회일 2026-08-18 / **CAD 수정 0건.** Sketch·Extrude·Boolean·Hole·Mirror·Split·Screw·Feature 전부 미변경
- 재현: `python scripts/row_layout.py`
- 기반 데이터: `cad_dump/features_Joystick.json` (익명 GET), 로프트 단면 `Joystick_part_2` / `part_3`

---

## 1. Updated ergonomic assumption

### 이전 전제 (폐기)

> 4버튼 row는 그립 전면 중앙에 놓인다. → 중앙 분할면에서는 자연히 2+2가 된다.
> 큰 surface angle은 접근성 저하다.

### 새 전제 (본 분석의 기준)

이 컨트롤러는 **한 손으로 그립을 감싸 잡는** 구조다.
검지·중지의 fingertip / distal phalanx는 그립 정중앙이 아니라 **한쪽 shell 쪽으로 치우쳐** 놓인다.

- `button row center ≠ grip center`
- `button row center = finger resting zone`
- **의도적 한쪽 offset은 설계 오류가 아니라 핵심 설계 변수다**
- 큰 surface angle 자체를 실패 조건으로 쓰지 않는다.
  손가락이 그 면을 감고 있다면 큰 각도는 오히려 자연스러운 접촉면이다

### 평가 기준 변경

접근성은 "전면 중앙에서의 거리"나 "각도 크기"가 아니라 다음으로 판단한다:

1. 감싸 잡을 때 손가락이 감기는 방향
2. fingertip resting position
3. 작은 lateral slide
4. finger roll
5. distal phalanx의 shell 표면 궤적
6. 각 버튼까지의 실제 finger travel (호길이)

### 성공 조건

> 한 손으로 자연스럽게 감아 잡았을 때, 검지·중지의 실제 resting zone과 movement arc 위에
> 4개 버튼이 **연속된 1-row**로 놓이는가.

---

## 2. Dominant shell concept

원본 shell split(정중앙, `Mirror 1` 미러면 `'JEC'`)을 **그대로 유지**한다.
B안(split plane 이동 / `Mirror 1` 폐기 / upstream loft 재설계 / screw 재배치)은 **보류**한다.

### 호길이 좌표계 `s`

```
   DOMINANT_SHELL          분할면          OPPOSITE_SHELL
        s < 0                s = 0              s > 0
   I1    I2    I3        ┊ gap ┊         I4
   M1    M2    M3        ┊ gap ┊         M4
```

- `s = 0` : 분할면 = 그립 전면 중앙. 접선각 0°
- `s < 0` : **DOMINANT_SHELL** — 손가락이 감겨 들어가는 쪽. INDEX 3개 + MIDDLE 3개
- `s > 0` : **OPPOSITE_SHELL** — 손가락을 펴서 닿는 쪽. INDEX 1개 + MIDDLE 1개
- 그립이 분할면 기준 미러 대칭이므로 `s<0` 구간은 `s>0` 구간의 거울상이다

### 배치 규칙

**I3/I4 경계(= 버튼 사이 gap의 중앙)를 분할면 s=0에 정확히 맞춘다.**
M3/M4도 동일.

이 규칙의 직접적 이득:

> **신규 버튼 중 분할면을 걸치는 것이 하나도 없다.**
> 원본 엄지 버튼은 BTN_2·BTN_5가 분할면을 걸치고 있다(각 쉘에 4mm씩).
> 신규 row는 gap이 분할면 위에 오므로 모든 버튼이 한쪽 쉘에 온전히 속한다.
> 개구부·포켓·캡이 두 파트로 쪼개지지 않는다 → 제작·조립 모두 유리.

---

## 3. INDEX row offset analysis

- 탐색 높이: 그립축 `y = +10 ~ +14` → **y = +12.0 채택**
- 단면: `Joystick_part_2`(y≈16.44) 93.3% + `Joystick_part_3`(y=−50.266) 6.7% 보간
- 해당 높이 한쪽 half arc = **78.33 mm** (필요량 대비 매우 여유)

### 접선각 프로파일 (y = +12)

| 분할면에서 호길이 | 접선각 |
|---|---|
| 5 mm | 3.73° |
| 10 mm | 9.88° |
| 15 mm | 20.56° |
| 20 mm | 40.94° |
| 25 mm | 67.08° |
| 30 mm | 81.63° |

### LAYOUT A 기준 (cap 8 / gap 3, row 41.00 mm)

| 항목 | 값 |
|---|---|
| ROW_START | s = **−31.500 mm** |
| FINGER_REST_CENTER | s = **−11.000 mm** |
| ROW_END | s = **+9.500 mm** |
| **row center offset from grip center** | **−11.000 mm** |
| DOMINANT 측 점유 | 31.5 mm / 78.33 mm (40.2%) |
| OPPOSITE 측 점유 | 9.5 mm / 78.33 mm (12.1%) |

---

## 4. MIDDLE row offset analysis

- 탐색 높이: `y = −4 ~ −8` → **y = −6.0 채택**
- 단면: part_2 66.4% + part_3 33.6% 보간
- half arc = **74.47 mm**

### 접선각 프로파일 (y = −6)

| 호길이 | 접선각 | INDEX 대비 |
|---|---|---|
| 5 mm | 6.60° | +2.87° |
| 10 mm | 14.91° | +5.03° |
| 15 mm | 27.09° | +6.53° |
| 20 mm | 47.95° | +7.01° |
| 25 mm | 69.56° | +2.48° |
| 30 mm | 81.76° | +0.13° |

**중지 행이 검지 행보다 곡률이 크다** (같은 호길이에서 각도가 최대 7° 더 큼).
그립이 아래로 갈수록 둥글어지기 때문이다. → **INDEX 좌표를 그대로 복제하면 안 된다.**
단, offset 값 자체(−11.0 mm)는 두 행 모두 동일하게 쓸 수 있다.
호길이 기준 배치가 같으면 finger travel도 같고, 각도만 달라진다.

---

## 5. Button center coordinates

`s` = 분할면 기준 호길이 (음수 = DOMINANT). `x` = 분할면에서의 측방 거리.
`depth`는 단면 로컬 좌표이며 단면마다 원점이 달라 **행 간 절대 비교 불가**(참고용).
`height`는 그립축 좌표로 절대값이다.

### INDEX row — LAYOUT A (y = +12.0)

| 버튼 | s [mm] | x [mm] | depth [mm] | height [mm] | 접선각 | shell |
|---|---|---|---|---|---|---|
| I1 | **−27.500** | −22.729 | +14.783 | +12.0 | **75.63°** | DOMINANT |
| I2 | **−16.500** | −16.159 | +22.094 | +12.0 | **25.35°** | DOMINANT |
| I3 | **−5.500** | −5.477 | +23.912 | +12.0 | **4.19°** | DOMINANT |
| I4 | **+5.500** | +5.477 | +23.912 | +12.0 | **4.19°** | OPPOSITE |

### MIDDLE row — LAYOUT A (y = −6.0)

| 버튼 | s [mm] | x [mm] | depth [mm] | height [mm] | 접선각 | shell |
|---|---|---|---|---|---|---|
| M1 | **−27.500** | −21.733 | +13.326 | −6.0 | **76.60°** | DOMINANT |
| M2 | **−16.500** | −15.837 | +16.932 | −6.0 | **32.12°** | DOMINANT |
| M3 | **−5.500** | −5.501 | +17.166 | −6.0 | **7.38°** | DOMINANT |
| M4 | **+5.500** | +5.501 | +17.166 | −6.0 | **7.38°** | OPPOSITE |

I3/I4 및 M3/M4는 분할면 기준 완전 대칭이므로 x·depth·각도가 부호만 다르다.

---

## 6. Surface angle / normal analysis

각도 크기를 실패 조건으로 쓰지 않고 **입력 종류**로 분류한다.

| 분류 | 접선각 범위 |
|---|---|
| fingertip front press | < 20° |
| fingertip diagonal press | 20 ~ 45° |
| fingertip side press | 45 ~ 70° |
| distal phalanx side press | > 70° |

### LAYOUT A

| 버튼 | 접선각 | 버튼면 각폭 | 입력 종류 |
|---|---|---|---|
| I1 | 75.63° | 23.8° | **distal phalanx side press** |
| I2 | 25.35° | 29.2° | fingertip diagonal press |
| I3 | 4.19° | 8.3° | fingertip front press |
| I4 | 4.19° | 8.3° | fingertip front press |
| M1 | 76.60° | 19.9° | **distal phalanx side press** |
| M2 | 32.12° | 30.4° | fingertip diagonal press |
| M3 | 7.38° | 12.1° | fingertip front press |
| M4 | 7.38° | 12.1° | fingertip front press |

### 해석

- **I3·I4는 분할면을 사이에 두고 거의 같은 방향(±4°)을 본다.**
  사용자 관점에서 이 둘은 완전히 연속된 한 쌍이다. 분할선만 그 사이를 지난다
- I2는 대각 접촉, I1은 측면 접촉으로 자연스럽게 이행한다.
  손가락이 그립을 감아 들어가는 궤적과 방향이 일치한다
- I1 / M1의 버튼면 각폭이 20~24°로 넓다 → 캡 표면이 곡면을 따라 기울어진다.
  **캡을 평면으로 만들면 한쪽 모서리가 들뜬다. 캡 상면을 접선에 맞춰 기울여야 한다**
- **I1/M1은 측방 하중 입력이 된다.** 택트 스위치는 축방향 하중이 정상 동작 조건이므로,
  캡이 측방 입력을 축방향으로 변환해야 한다 (캡 형상 설계 과제, 쉘 과제가 아님)

---

## 7. Finger travel analysis

FINGER_REST_CENTER는 row의 기하 중심에 둔다 — 이 위치가 최대 travel을 최소화한다.
LAYOUT A에서 rest는 s = −11.0, 즉 **I2와 I3 사이**다 (사용자 예상과 일치).

| 이동 | 호길이 travel | 손가락 동작 |
|---|---|---|
| REST → I1 | **16.50 mm** | 굴곡 (finger flexion, 감아 들어감) |
| REST → I2 | **5.50 mm** | 소폭 굴곡 |
| REST → I3 | **5.50 mm** | 소폭 신전 |
| REST → I4 | **16.50 mm** | 신전 (finger extension, 펴서 앞으로) |

MIDDLE row도 호길이 배치가 동일하므로 travel 값이 같다 (16.50 / 5.50 / 5.50 / 16.50).

### 평가

- 최대 travel **16.5 mm**. 손가락을 들지 않고 굴곡/신전만으로 도달 가능한 범위 안이다
- 방향이 명확히 갈린다: **굴곡 → I1 쪽, 신전 → I4 쪽.** rest에서 양방향 대칭
- 호길이 간격이 11.0 mm로 **균일**하다 → 버튼 간 이동 감각이 일정하다.
  각도는 제각각이지만 **손가락 이동량 기준으로는 완전히 균일한 1-row**다.
  이것이 "연속된 한 줄로 느껴지는가"의 실질 조건을 충족한다
- rest를 I2쪽(s≈−16.5)으로 옮기면 I4까지 22.0 mm가 되어 불균형해진다 → 기하 중심 권장

---

## 8. Layout A / B / C

| 항목 | **LAYOUT A** | LAYOUT B | LAYOUT C |
|---|---|---|---|
| cap 폭 | 8.0 mm | 7.0 mm | 7.5 mm |
| gap | 3.0 mm | 2.5 mm | 2.75 mm |
| pitch | 11.0 mm | 9.5 mm | 10.25 mm |
| **row total width** | **41.00 mm** | 35.50 mm | 38.25 mm |
| **required offset** (row center) | **−11.00 mm** | −9.50 mm | −10.25 mm |
| ROW_START / END | −31.50 / +9.50 | −27.25 / +8.25 | −29.38 / +8.88 |
| I1 각도 | 75.63° | 61.64° | 69.59° |
| I2 각도 | 25.35° | 18.56° | 21.80° |
| I3 / I4 각도 | 4.19° | 3.46° | 3.85° |
| M1 각도 | 76.60° | 65.25° | 71.53° |
| M2 각도 | 32.12° | 24.83° | 28.23° |
| M3 / M4 각도 | 7.38° | 6.29° | 6.82° |
| **max finger travel** | **16.50 mm** | 14.25 mm | 15.38 mm |
| **3+1 shell ownership** | **충족** | 충족 | 충족 |
| 분할면 걸치는 버튼 | **0개** | 0개 | 0개 |
| screw boss 간섭 | 없음 (§10) | 없음 | 없음 |
| 엄지 컨트롤 간섭 | 없음 (수직 이격) | 없음 | 없음 |
| holder 공간 (포켓 6.4 + 리브) | 원본과 동일 | 원본과 동일 | 원본과 동일 |
| **cap shoulder** (opening − pocket)/2 | **0.80 mm** | **0.30 mm** | 0.55 mm |
| **manufacturability (FDM)** | **양호 — 원본 검증치 그대로** | **위험 — 0.30mm 숄더는 FDM 하한 이하** | 보통 |
| 신규 tolerance 검증 필요 | **불필요** | 필요 | 필요 |
| ergonomics | travel 최대, 각도 최대 | travel 최소, 각도 최소 | 중간 |

### 판정

- **LAYOUT B는 제작 관점에서 위험하다.** cap 7.0 mm에 포켓 6.4 mm면 캡을 잡아주는
  숄더가 편측 0.30 mm뿐이다. FDM 최소 피처(약 0.4~0.8 mm) 이하이므로 캡 탈락 위험이 크다.
  스위치 포켓 6.4 mm(`#button_module_width` 6 + 2×0.2)가 절대 하한이므로 이보다 더 줄일 수 없다
- **LAYOUT A는 원본에서 이미 검증된 치수(8/3/6.4/0.2/4)를 그대로 쓴다.**
  새로 검증해야 할 공차가 없다. 숄더 0.80 mm로 원본과 동일
- LAYOUT C는 절충이지만 숄더 0.55 mm로 신규 공차 검증이 필요하고,
  travel 이득은 1.12 mm에 불과하다

---

## 9. Right-hand / left-hand mirroring feasibility

**판정: 가능. 파라미터 1개로 처리할 수 있다.**

근거:

- 그립 쉘 자체가 분할면 기준 완전 대칭이다 (`Mirror 1`, PART / NEW)
- 원본 엄지 버튼·조이스틱도 분할면 기준 대칭 배치다
  → **손 방향을 바꿔도 엄지 영역은 전혀 영향받지 않는다**
- 신규 버튼 위치가 전부 호길이 `s` 하나로 정의된다

따라서:

```
RIGHT_HAND_CONFIGURATION :  s_btn = +1 × [−27.5, −16.5, −5.5, +5.5]
LEFT_HAND_CONFIGURATION  :  s_btn = −1 × [−27.5, −16.5, −5.5, +5.5]
                                   = [+27.5, +16.5, +5.5, −5.5]
```

- `#hand_sign = ±1` 변수 하나로 DOMINANT/OPPOSITE가 뒤집힌다
- 두 쉘의 소재 형상이 이미 서로의 미러이므로, 버튼 가공 전 단계까지는 완전히 공용이다
- 좌/우 버전은 **버튼 피처만 반전된 별개 파생**이 된다

주의: 이는 **설계 구조상 가능하다는 판정**이다. Onshape configuration을 지금 만들지 않는다.
실제 구현 시 `s` → 3D 위치 변환이 `#hand_sign`에 선형적으로 반응하는지 확인이 필요하다.

---

## 10. Interference risks

### 확정된 것 (실측 근거)

| # | 요소 | 위치 | INDEX(y=+12) 여유 | MIDDLE(y=−6) 여유 | 판정 |
|---|---|---|---|---|---|
| 1 | 나사 #2 보스 | 분할면 s≈0, y = 23.064, ⌀7 (보스 y 19.56~26.56) | row 상단 y=16 → **3.56 mm** | — | 통과, 여유 작음 |
| 2 | 나사 #3 보스 | 분할면 s≈0, y = −21.354, ⌀7 (보스 y −24.85~−17.85) | — | row 하단 y=−10 → **7.85 mm** | 통과 |
| 3 | 기존 엄지 backplate 하단 | front_y ≈ 25.5 | row 상단 y=16 → **9.5 mm** | — | 통과 |
| 4 | 두 row 간 | — | row 하단 y=8 ↔ row 상단 y=−2 → **10.0 mm** | | 통과 |
| 5 | 분할면 걸침 | — | **0개** (gap이 분할면 위) | 0개 | 문제 없음 |

> **나사가 분할면 안에 있다는 점이 중요하다.** `Screw_holes`는 평면 `'JEC'`(=분할면) 위에 있고
> 나사 축이 분할면에 수직, 즉 **측방(호길이 방향)으로 뻗는다.**
> 따라서 나사 보스는 s≈0 부근에서 좌우로 ±3.5 mm 점유한다 — 바로 I3/I4가 있는 구역이다.
> 다행히 **높이가 갈려서** 간섭하지 않는다. 행 높이를 옮기면 즉시 문제가 된다.

**행 높이 안전 범위 (LAYOUT A, cap 8mm 기준):**

- INDEX row: `y ≤ +15.5` (나사 #2 보스 하단 19.56 − cap 반폭 4.0)
- MIDDLE row: `y ≥ −13.8` (나사 #3 보스 상단 −17.85 + cap 반폭 4.0)
- 두 행 간격: 최소 11 mm 권장 (cap 8 + gap 3)
- **채택값 y = +12 / y = −6 은 두 조건을 모두 만족하고 서로 18 mm 떨어져 있다**

### UNKNOWN (3D 데이터 필요)

| # | 요소 | 위험 |
|---|---|---|
| 6 | 신규 backplate/리브(약 10 mm 내향)와 나사 보스의 **내부** 충돌 | 중 |
| 7 | 기존 엄지 backplate 리브가 아래로 얼마나 내려오는지 | 중 |
| 8 | 배선 경로 (Joystick Studio에 명시 피처 없음) | 중 |
| 9 | Pitch attachment(21.072 × 25.672)의 그립 내부 점유 범위 | 중 |
| 10 | s=−27.5 (I1/M1) 위치의 내부 벽 두께 및 리브 확보 가능성 | **높음** |

10번이 가장 큰 미확인 위험이다. I1/M1은 그립 최대폭(x≈±23.9) 근처에 있어
외형상 여유는 있어 보이나, 내부에 무엇이 지나가는지 확인되지 않았다.

---

## 11. Recommended layout

### **LAYOUT A 권장** (cap 8.0 mm / gap 3.0 mm / row 41.00 mm / offset −11.00 mm)

선정 이유:

1. **원본에서 검증된 치수를 100% 상속한다.** 8/3/6.4/0.2/4 mm 전부 원본과 동일.
   신규로 검증할 공차가 없고, 캡 숄더 0.80 mm도 원본과 같다
2. LAYOUT B는 숄더 0.30 mm로 FDM 하한 이하 → 캡 탈락 위험. 채택 불가
3. LAYOUT C는 숄더 0.55 mm로 신규 검증이 필요한데 travel 이득이 1.12 mm뿐 → 비용 대비 이득 부족
4. LAYOUT A의 단점인 travel 16.5 mm는 손가락 굴곡/신전 범위 안이며,
   rest 기준 양방향 대칭이라 방향 혼동이 없다

### 최종 배치값

```text
                DOMINANT_SHELL                 ┊  OPPOSITE_SHELL
INDEX (y=+12)   I1        I2        I3         ┊  I4
   s [mm]     −27.50    −16.50    −5.50        0  +5.50
   angle       75.6°     25.4°     4.2°        ┊   4.2°
   press      distal    diagonal  front        ┊  front

MIDDLE (y=−6)   M1        M2        M3         ┊  M4
   s [mm]     −27.50    −16.50    −5.50        0  +5.50
   angle       76.6°     32.1°     7.4°        ┊   7.4°

row center offset = −11.00 mm       finger rest = s −11.00 (I2~I3 사이)
max finger travel = 16.50 mm        분할면 걸치는 버튼 = 0개
```

### 부가 설계 요구

- **I1 / M1 캡은 상면을 접선에 맞춰 기울여야 한다** (버튼면 각폭 20~24°)
- **I1 / M1은 측방 하중 입력**이므로 캡이 이를 축방향으로 변환해야 한다.
  원본 캡 형상을 그대로 쓰면 스위치에 측방 하중이 걸린다
- 나머지(I2~I4, M2~M4)는 원본 캡 구조를 거의 그대로 재사용 가능

---

## 12. Remaining unknowns

**401로 막힌 것 (Onshape Read API 키 필요):**

- s = −27.5 지점의 **내부 여유** — I1/M1 holder/리브 확보 가능 여부 (최대 위험)
- 나사 보스의 실제 3D 점유 부피
- 기존 엄지 backplate 리브의 하단 도달 높이
- 배선 경로
- Pitch attachment의 내부 점유 범위
- 그립 bounding box, 무게중심

**근사에 의존한 것:**

- 단면 높이(part_2 y≈16.44, part_3 y=−50.266)는 `Joystick_side_profile` 자취선 매칭 **추정치**
- 행 높이 사이 단면은 두 단면의 **선형 보간**이다.
  실제 로프트는 4단면 스플라인 보간이므로 곡률이 다를 수 있다.
  INDEX row(part_2에서 4.4 mm)는 오차가 작고, MIDDLE row(22.4 mm)는 상대적으로 크다
- `depth` 좌표는 단면 로컬값이라 행 간 절대 비교 불가

**설계 결정 대기:**

- 오른손 / 왼손 확정 (구조상 `#hand_sign` 1개로 처리 가능하나 초판 방향은 결정 필요)
- 실제 사용자 손 치수 기준 rest 위치 미세 조정
- I1/M1 캡의 각도 보정 형상
- 8개 버튼 기능 매핑

---

## 13. Next CAD modification step

**아직 실행하지 않는다.** 승인 후 아래 순서로 진행한다.

**선행 조건 (미충족 시 진행 불가):**

1. Onshape **Read 권한 API 키** → §12의 내부 여유 검증, 특히 I1/M1 위치
2. 사용자 소유 **사본 문서** (원본은 Adam Simon 소유, 수정 불가)
3. 원본 라이선스 조건 확인

**작업 순서 (전부 트리 최하단 append, 기존 피처 무수정):**

| 단계 | 내용 | 검증 |
|---|---|---|
| 1 | 신규 변수 블록 추가 (`#finger_button_*`, `#hand_sign`, 행 높이·offset) | 값 조회 |
| 2 | INDEX row용 cPlane 생성 (원본 `Buttons_plane`과 동일한 LINE_ANGLE 방식) | 평면 위치 확인 |
| 3 | DOMINANT 3개 + OPPOSITE 1개 개구부 스케치 — **mirror 구속 걸지 않음** | 형상 조회 |
| 4 | 개구부 REMOVE 압출 | 관통 확인 |
| 5 | 신규 backplate / 리브 ADD (기존 backplate와 **분리된 별도 body**) | 간섭 확인 |
| 6 | 스위치 포켓 6.4 mm REMOVE | 정렬 확인 |
| 7 | 버튼 캡 NEW (I1은 각도 보정 형상) | 클리어런스 0.2 확인 |
| 8 | MIDDLE row에 대해 2~7 반복 (**좌표 복제 금지**, 곡률이 다름) | |

각 단계마다 **조회 → 확인 → 다음**. 한 번에 여러 피처를 만들지 않는다.
