# 원본 버튼 메커니즘 분석 (READ ONLY)

- 대상: Onshape `Joystick` 문서 / Part Studio **Joystick** (`212ec93359aad06aa2bd2fad`)
- 방법: 익명 GET으로 받은 피처 트리(`cad_dump/features_Joystick.json`, 89 features) 로컬 분석
- 조회일 2026-08-18 / **CAD 수정 0건.** Feature 생성·수정·삭제·Sketch 변경 없음
- 좌표 단위: mm. 스케치 원시값(m)을 ×1000 변환
- 재현: `python scripts/inspect_feature.py Joystick --sketch Buttons`

---

## 1. Executive Summary

원본 버튼 8개는 **하나의 스케치(`Buttons`) 안에 전부 들어 있고, 압출 한 번(`Extrude 2`)으로 동시에 뚫린다.**
버튼 1개당 독립 피처 세트가 있는 구조가 **아니다.** Pattern도 쓰지 않았다.
좌우 대칭은 스케치 내부 mirror 구속(`*.MirrorCS` 엔티티)으로 처리된다.

8개 버튼 개구부, 8개 스위치 포켓, 엄지 조이스틱 구멍(d=15mm)이
**모두 같은 평면(`Buttons_plane`) 위, 그립 전면 상단 한 구역**에 몰려 있다.
조이스틱 구멍은 그립 최상단에서 6.5mm 아래, 버튼 3개 행은 그 아래 24~48mm 구간에 있다.

가장 중요한 구조적 제약 두 가지:

1. **분할면 = 미러면.** `Mirror 1`의 미러 평면은 `Joystick_side_profile` / `Screw_holes`와
   같은 평면(`JEC`)이다. LEFT/RIGHT 쉘은 이 평면 기준 완전 대칭이다.
2. **`Buttons` 스케치의 x=0 이 곧 그 분할면이다.** 그래서 원본 버튼 8개는
   좌 3 / 우 3 / **분할면을 걸치는 중앙 2개**로 나뉜다. 좌우 비대칭 배치가 아니다.

우리가 목표로 하는 **LEFT 3 + RIGHT 1**은 이 미러 대칭 구조로는 만들 수 없다.
따라서 기존 버튼 피처를 복제/패턴하는 방식(Option A)은 부적합하고,
**기존 치수 체계와 마스터 변수를 재사용하되 피처는 트리 끝에 새로 붙이는 방식(Option B)**을 추천한다.

---

## 2. 기존 PushBtn x8 위치 분석

### 2.1 논리 명칭 매핑 (분석 문서 전용 — 실제 CAD 이름은 변경하지 않음)

`Buttons` 스케치 좌표계(`Buttons_plane`) 기준. `front_y`는 그립 전면 프로파일 좌표로 환산한 값
(환산식 `front_y = 2.557 − buttons_y`, `Joystick_front_profile`의 동일 원(r=8, x=±7)으로 교차 검증됨).

| 논리 명칭 | 개구부 중심 (x, y) | 개구부 크기 | front_y | 그립 최상단에서 | 추정 cap part | 소속 쉘 |
|---|---|---|---|---|---|---|
| ORIGINAL_THUMB_BTN_1 | (−11.000, −26.176) | 8 × 8 | 28.733 | 47.56 mm | Button_corner_1 | LEFT |
| ORIGINAL_THUMB_BTN_2 | (0.000, −26.176) | 8 × 8 | 28.733 | 47.56 mm | Button_middle_1 | **분할면 걸침** |
| ORIGINAL_THUMB_BTN_3 | (+11.000, −26.176) | 8 × 8 | 28.733 | 47.56 mm | Button_corner_2 | RIGHT |
| ORIGINAL_THUMB_BTN_4 | (−11.000, −37.176) | 8 × 8 | 39.733 | 36.56 mm | Button_side_1 | LEFT |
| ORIGINAL_THUMB_BTN_5 | (0.000, −37.176) | 8 × 8 | 39.733 | 36.56 mm | Button_middle_2 | **분할면 걸침** |
| ORIGINAL_THUMB_BTN_6 | (+11.000, −37.176) | 8 × 8 | 39.733 | 36.56 mm | Button_side_2 | RIGHT |
| ORIGINAL_THUMB_BTN_7 | (−8.157, −49.676) | 10 × 7 | 52.233 | 24.06 mm | Button_wide_1 | LEFT |
| ORIGINAL_THUMB_BTN_8 | (+8.157, −49.676) | 10 × 7 | 52.233 | 24.06 mm | Button_wide_2 | RIGHT |
| (참고) thumb joystick | (0.000, −67.268) | ⌀15 | 69.825 | 6.47 mm | HW504_B | **분할면 걸침** |

> cap part 이름 대응(corner=1행 / side=2행 / wide=3행)은 **추정**이다.
> 근거: 3행만 10×7(=`#switch_width`×`#switch_height`)로 "wide"에 부합하고,
> 1행 경계(y=−30.176)에만 r=8 라운드 원이 있어 "corner"에 부합한다.
> partId ↔ feature 매핑은 `/parts` 401로 확인 불가 → **UNKNOWN**.

### 2.2 조사 항목별 결과

| 항목 | 결과 |
|---|---|
| Button ID | 개구부는 개별 ID 없음. `Buttons` 스케치(`F9tZ4ezI7riogDz_2`의 소스) 내부 엔티티일 뿐 |
| 해당 Part / Assembly | 개구부는 `Joystick_1`/`Joystick_2`에, 캡은 독립 8개 part, 스위치는 `PushBtn` x8 (Joystick assembly) |
| X / Y 위치 | 위 표 (스케치 평면 2D 좌표, 확정) |
| Z 위치 | **UNKNOWN** — `Buttons_plane`은 `Projected curve 2` 기반 cPlane(LINE_ANGLE, offset 25mm). 전역 3D 좌표는 401로 미확인 |
| 눌림 방향 | `Buttons_plane` 법선 방향, 그립 안쪽으로. `Extrude 2` = REMOVE / BLIND 10mm / oppositeDirection 없음 |
| 어느 shell | 위 표. **좌 3 / 우 3 / 분할면 걸침 2** |
| 인접 버튼 거리 | 행 내 피치 11.0mm (셀 8 + 갭 3) / 1행↔2행 피치 11.0mm / 2행↔3행 12.5mm / 3행 내 피치 16.314mm |
| thumb joystick과 상대 위치 | 조이스틱 중심에서 3행 24.1mm↓ · 2행 30.1mm↓ · 1행 41.1mm↓ (모두 같은 평면, 같은 면) |
| 버튼 cap 형상 | `Buttons_cover` 스케치. 개구부 윤곽에서 사방 0.2mm 축소 (7.6×7.6 / 9.6×6.6 / r=7.8), 높이 4mm |
| 실제 switch body 위치 | `Buttons_backplate_holes`의 6.4×6.4mm 관통 포켓 8개. 중심이 개구부 중심과 **완전 일치** |

### 2.3 "엄지 영역"이라고 판단하는 근거

**판정: PARTIAL (강한 정황 근거 있음, 3D 확증은 불가)**

찬성 근거 (전부 실측):

1. 8개 버튼과 엄지 조이스틱 구멍이 **같은 스케치, 같은 평면**에 있다. 설계 의도상 한 덩어리다.
2. 조이스틱은 그립 최상단에서 **6.5mm** 아래 — 명백히 엄지 위치다.
   버튼 3개 행은 그 바로 아래 24.1 / 30.1 / 41.1mm에 연속 배치된다. 중간에 끊김이 없다.
3. 8개 전부가 하나의 backplate(`Sweep 1` + `Mirror 2`)와 하나의 지지 리브 세트를 공유한다.
   구조적으로 분리된 두 클러스터가 아니다.
4. 그립 전체 길이는 126.562mm(`Joystick_front_profile` 중심선 (0,−50.266)→(0,76.295)).
   버튼 클러스터는 상단 24~48mm 구간, 즉 **상단 38% 안**에 들어간다.
5. 원본 참고 이미지가 `thrustmaster-simtask-farmstick`(플라이트 스틱)이다.
   이 계열은 상단 전면에 엄지 클러스터를 두는 것이 관례다.

반대/유보 근거:

- 최하단 행(ORIGINAL_THUMB_BTN_1~3)은 그립 최상단에서 47.6mm다. 엄지 도달 범위의 바깥일 수 있고,
  검지가 닿는 위치일 가능성을 배제할 수 없다.
- 그립이 로프트 곡면이라 평면상 47.6mm가 표면 측지거리로는 더 길다.
- 손 크기·파지 자세 데이터가 없다.

**확증에 필요한 것:** assembly definition(부품 3D 배치) 또는 massproperties bounding box → 둘 다 현재 401.

---

## 3. 기존 버튼 Feature Tree

`Joystick` Part Studio 89개 피처 중 버튼에 관여하는 것 전부.

| # | Feature name | Type | Feature ID | 역할 | 의존 | Mirror/Pattern | 직접 수정 위험도 |
|---|---|---|---|---|---|---|---|
| 1–16 | `###name = #value` × 16 | assignVariable | — | 마스터 변수 (버튼 관련 8개) | 없음 | — | 낮음 (값만) |
| 18 | Joystick_front_profile | newSketch | `FA1E7prY4E8ZkNv_0` | 전면 프로파일. **버튼 그리드가 이미 여기 그려짐** | 없음 | 스케치 내부 mirror | **매우 높음** (loft 소스) |
| 52 | Projected curve 2 | projectCurves | `FKyIBGTkOnBcIt6_2` | 버튼 평면용 3D 곡선 | 프로파일 2종 | — | 높음 |
| 53 | Buttons_plane | cPlane | `FM3zBHeyugNm67b_2` | 버튼 기준 평면 (LINE_ANGLE, offset 25mm) | Projected curve 2 | — | 높음 |
| 54 | **Buttons** | newSketch | `FIQL6iSqO0uhklX_2` | **개구부 8개 + 조이스틱 구멍 정의** | Buttons_plane | 스케치 내부 mirror | **매우 높음** |
| 55 | Extrude 2 | extrude | `F9tZ4ezI7riogDz_2` | 개구부 8개 동시 절삭 (REMOVE / BLIND 10mm) | Buttons | — | **매우 높음** |
| 56 | Backplate | newSketch | `F5pLe9ocjnEyLMf_4` | backplate 단면 (스플라인 3개) | — | — | 높음 |
| 57 | Sweep_guide | newSketch | — | sweep 경로 | — | — | 높음 |
| 58 | Sweep 1 | sweep | `FR1RGAmsfokIVzQ_4` | backplate 본체 생성 (NEW) | Backplate, Sweep_guide | — | 높음 |
| 59 | Mirror 2 | mirror | `FqYBXB9oEf4GDTk_5` | backplate 좌우 대칭 (PART / ADD) | Sweep 1 | **PART mirror** | 높음 |
| 60 | Extrude 3 | extrude | `FVIwzKdg6rReWam_5` | REMOVE / BLIND 6mm | — | — | 중간 |
| 61 | Extrude 4 | extrude | `FjQBbAOMy3p7jmx_5` | REMOVE / BLIND 6mm | — | — | 중간 |
| 62 | Extrude 5 | extrude | `FyEMM0DlzInYIq9_5` | ADD / BLIND 5.7mm | — | — | 중간 |
| 63 | Extrude 6 | extrude | `FSFJLfpX5cKnT2y_5` | ADD / BLIND 5.7mm | — | — | 중간 |
| 64 | Buttons_backplate_holes | newSketch | `FPOlu64eiMvEwWP_5` | **스위치 포켓 8개(6.4×6.4) + 조이스틱 포켓(25×21)** | Buttons_plane | 스케치 내부 mirror | **매우 높음** |
| 65 | Extrude 7 | extrude | `FR1oMTVgCnv7429_5` | 포켓 관통 절삭 (REMOVE / THROUGH_ALL) | 위 스케치 | — | **매우 높음** |
| 66 | Buttons_backplate_supports | newSketch | `FyEk1VDHUroqDzu_5` | 지지 리브 단면 | Buttons_plane | — | 높음 |
| 67 | Extrude 8 | extrude | `Fei0eYh0brIsddG_5` | 리브 (ADD / BLIND 10mm) | 위 스케치 | — | 높음 |
| 68 | Extrude 9 | extrude | `FWt0ybcVGVkjdyh_5` | 리브 (ADD / BLIND 10mm) | 위 스케치 | — | 높음 |
| 69 | Sketch 1 | newSketch | `FeCHIo0LQRwkgrd_5` | 폭 25mm 참조선 1개 | — | — | 중간 |
| 70 | Extrude 10 | extrude | `Ft8KiawnCXKP8M0_5` | ADD / BLIND 2mm | Sketch 1 | — | 중간 |
| 71–73 | Extrude 11 / 12 / 13 | extrude | `FM9Yi…` / `Fj0R5…` / `F5wz3…` | ADD / UP_TO_SURFACE | Sketch 1 | — | 중간 |
| 74 | **Buttons_cover** | newSketch | `FyXEyaypbs8fSEd_5` | **버튼 캡 윤곽 (개구부 −0.2mm)** | Buttons_plane | — | **매우 높음** |
| 75 | Extrude 17 | extrude | `FN60hLJrErylbKr_5` | 캡 본체 (NEW / UP_TO_SURFACE / 4mm) | Buttons_cover | — | **매우 높음** |
| 76 | Extrude 23 | extrude | `F5f2Bqv3P4yttCY_8` | 캡 추가 본체 (NEW / UP_TO_SURFACE) | — | — | 높음 |
| 77 | Extrude 24 | extrude | `FhTqxuAvjIWGQgW_11` | 캡 추가 본체 (NEW / UP_TO_VERTEX) | — | — | 높음 |

엄지 조이스틱 계통(참고, 변경 금지 대상):

| # | Feature | Type | ID | 역할 |
|---|---|---|---|---|
| 78–79 | Sketch 2 → Extrude 25 | extrude | `FTcXnBBgATAer7g_13` | `Small_joystick_attachment` (깊이 `#small_joystick_pin_height+1mm`) |
| 80–82 | Sketch 3 → Extrude 26, 27 | extrude | `FszioMwCHKbkH1V_14`, `FX1biKSVGvdUNFj_15` | 0.5mm / 2mm |
| 83–84 | Fillet 1 / Fillet 2 | fillet | `FHMQIxjG91YQrEe_14`, `FLzhMM7PAvd2ObX_14` | r=1.5mm / r=0.5mm |
| 85–87 | Sketch 4 → Extrude 28, 29 | extrude | `Fh6pnpzd9rQ96DB_14`, `Fr1CQKO6PQOi6Oj_14` | ADD 6mm |
| 88–89 | Sketch 5 → Extrude 30 | extrude | `FA0tsuQ7KJ8w7IL_14` | REMOVE / UP_TO_SURFACE |

### 3.1 세 가지 질문에 대한 답

1. **버튼 하나를 만든 뒤 Pattern/Mirror로 복제했는가?** → **아니다.**
   feature-level Pattern은 트리에 하나도 없다. `Mirror 1`(쉘), `Mirror 2`(backplate)뿐이고
   둘 다 PART mirror이지 버튼 패턴이 아니다.
2. **각 버튼이 독립 Sketch/Feature를 갖는가?** → **아니다.**
   8개 전부 `Buttons` 스케치 하나에 있고 `Extrude 2` 한 번에 잘린다.
   포켓 8개도 `Buttons_backplate_holes` 하나 + `Extrude 7` 한 번이다.
3. **여러 형태의 버튼이 공통 구조를 공유하는가?** → **그렇다.**
   8mm 셀 / 3mm 갭 / 6.4mm 포켓 / 0.2mm 클리어런스 / 4mm 캡 높이 —
   4종(corner/side/wide/middle) 전부 같은 마스터 변수에서 나온다.
   좌우 대칭은 스케치 내부 mirror 구속(`*.MirrorCS`)으로만 처리된다.

---

## 4. 버튼 1개 생성 과정 (실제 Feature Chain)

원본에는 "버튼 1개"만 만드는 독립 체인이 없다. 아래는 **8개가 한 묶음으로** 만들어지는 실제 순서다.

```text
Button implementation chain (실측)

[1] 마스터 변수 (feature 1~16, assignVariable)
    #button_width=8 / #button_gap=3 / #button_module_width=6
    #button_tolerance=0.2 / #button_support_thickness=4 / #button_cover_height=4
    #switch_width=10 / #switch_height=7
        |
[2] Joystick_front_profile  (feature 18, newSketch, plane 'JCC')
    그립 전면 프로파일에 버튼 그리드를 미리 작도 (8mm 셀 + 3mm 갭)
        |
[3] Loft 2 → Enclose 1 → Extrude 1 → Boolean 1 → Shell 1(두께 3mm)
    → Mirror 1 (PART/NEW, 미러면 'JEC')  ...... LEFT/RIGHT 쉘 2개 확정
        |
[4] Projected curve 2 (feature 52) → cPlane Buttons_plane (feature 53)
    LINE_ANGLE, offset 25mm — 곡면 위 버튼 기준 평면
        |
[5] Sketch 'Buttons' (feature 54)
    개구부 8개 (8×8 ×6, 10×7 ×2) + 조이스틱 구멍 ⌀15
    x=0 구속선 기준 스케치 내부 mirror
        |
[6] Extrude 2 (feature 55)  ...... SHELL OPENING
    REMOVE / BLIND 10mm  → 쉘 두 짝에 개구부 8개 동시 관통
        |
[7] Sketch Backplate + Sweep_guide → Sweep 1 (NEW) → Mirror 2 (ADD)
    Extrude 3,4 (REMOVE 6mm) / Extrude 5,6 (ADD 5.7mm)
    ...... BACKPLATE 본체
        |
[8] Sketch Buttons_backplate_holes → Extrude 7  ...... SWITCH POCKET
    REMOVE / THROUGH_ALL → 6.4×6.4 포켓 8개 (개구부 중심과 정렬)
        |
[9] Sketch Buttons_backplate_supports → Extrude 8, 9  ...... HOLDER / RETAINER
    ADD / BLIND 10mm → 지지 리브
        |
[10] Sketch 1 → Extrude 10 (2mm), 11/12/13 (UP_TO_SURFACE)
     ...... 보강 / 마감
        |
[11] Sketch Buttons_cover → Extrude 17  ...... BUTTON CAP
     NEW / UP_TO_SURFACE / 4mm, 개구부 대비 사방 0.2mm 축소
     Extrude 23 (NEW/UP_TO_SURFACE), Extrude 24 (NEW/UP_TO_VERTEX) 추가 캡 본체
        |
[12] PushBtn part studio에서 스위치 본체를 assembly에서 삽입 (x8)
```

핵심: **쉘 개구부 → backplate → 포켓 → 리브 → 캡** 순서다.
캡은 쉘이 아니라 **backplate와 쉘 개구부 사이에 갇히는 별도 부품**이다.

---

## 5. Shell hole 구조

| 항목 | 값 | 출처 |
|---|---|---|
| 개구부 크기 (1·2행) | 8.000 × 8.000 mm | `Buttons` 스케치 실측 = `#button_width` |
| 개구부 크기 (3행) | 10.000 × 7.000 mm | 실측 = `#switch_width` × `#switch_height` |
| 개구부 간 갭 | 3.000 mm | 실측 = `#button_gap` |
| 행 내 피치 | 11.000 mm (1·2행) / 16.314 mm (3행) | 실측 |
| 행 간 피치 | 11.000 mm (1↔2) / 12.500 mm (2↔3) | 실측 |
| 라운드 | r = 8.000 mm 원 2개, 중심 (±7, −30.176) | `Buttons` 스케치. 1행 바깥 모서리 라운드로 추정 |
| 절삭 방식 | REMOVE / BLIND / depth 10 mm | `Extrude 2` |
| shell wall 두께 | **3 mm** | `Shell 1` thickness |
| fillet / chamfer | 개구부 자체에는 **없음**. `Fillet 1`(r=1.5), `Fillet 2`(r=0.5)는 조이스틱 계통 | 트리 순서 |
| tolerance | 개구부에는 미적용. 클리어런스는 캡 쪽에서 0.2mm 확보 | `Buttons_cover` |

절삭 깊이 10mm > 벽 두께 3mm → 곡면 벽을 확실히 관통시키기 위한 여유값이다.

---

## 6. Switch holder 구조

| 항목 | 값 / 판정 |
|---|---|
| switch 수납 공간 | **6.400 × 6.400 mm** 관통 포켓 8개 (`Buttons_backplate_holes`) |
| 산출 근거 | `#button_module_width`(6) + 2 × `#button_tolerance`(0.2) = 6.4 ✔ 실측 일치 |
| 포켓 중심 | (−11, −26.176) (0, −26.176) (11, −26.176) / (−11, −37.176) (0, −37.176) (11, −37.176) / (−8.157, −49.676) (8.157, −49.676) |
| 개구부와의 정렬 | 8개 모두 **중심 완전 일치** (오차 0) |
| 조이스틱 포켓 | 25.000 × 21.000 mm, 중심 (0, −67.268) — HW504_B 모듈 자리 |
| 절삭 방식 | REMOVE / THROUGH_ALL / oppositeDirection (`Extrude 7`) |
| 고정 방식 | backplate 관통 포켓에 스위치를 끼우고, 리브(`Extrude 8`,`9`, ADD 10mm)로 뒤에서 받침 |
| 리브 치수 | backplate supports 스케치: 25 × 19mm 프레임 + 4.5mm 연장 |
| snap fit 여부 | **UNKNOWN** — 스냅 후크로 볼 만한 얇은 캔틸레버 형상이 스케치에 없음 |
| captive 구조 | **부분적으로 YES** — 포켓이 관통형이라 스위치는 backplate가 조립되면 갇힌다 |
| 별도 holder part | **없음.** backplate 자체가 holder다 (BOM에 `Backplate` x1) |
| adhesive 필요 여부 | **UNKNOWN** |
| 조립 방향 | backplate 법선 방향, 그립 안쪽에서 바깥쪽으로 (Extrude 7의 oppositeDirection 기준) |
| 별도 지지 두께 | `#button_support_thickness` = 4 mm |

---

## 7. Button cap / plunger 구조

| 항목 | 값 / 판정 |
|---|---|
| 별도 부품 여부 | **YES.** BOM에 8개 독립 part (`Button_corner_1` … `Button_wide_2`) |
| 생성 피처 | `Buttons_cover` 스케치 → `Extrude 17` (NEW / UP_TO_SURFACE / **4mm**) + `Extrude 23`, `Extrude 24` |
| 높이 | 4.000 mm = `#button_cover_height` |
| 외곽 (1·2행) | 8.000 × 8.000 (개구부와 동일) |
| 내곽 (1·2행) | 7.600 × 7.600 → **사방 0.2mm 단차** |
| 외곽 / 내곽 (3행) | 10.000 × 7.000 → 9.600 × 6.600 → 사방 0.2mm |
| 라운드 캡 | r = 8.000 → r = 7.800 (0.2mm) |
| clearance | **0.2 mm 균일** = `#button_tolerance` |
| shell에 captive 되는가 | **YES (추정).** 캡 외곽이 개구부와 동일 치수이고 안쪽에 0.2mm 단차가 있어, backplate가 뒤를 막으면 바깥으로 빠지지 않는다 |
| travel 제한 구조 | **UNKNOWN** — 스트로크를 제한하는 별도 스톱 형상을 스케치 수준에서 특정하지 못함 |
| switch 접촉부 | **UNKNOWN** — 캡 뒷면 plunger 돌기 여부는 3D 형상 필요 |
| 탈락 방지 | 단차 + backplate 조합으로 판단되나 **3D 확인 필요** |

---

## 8. 관련 주요 치수 (전부 실측)

### 8.1 마스터 변수 (Joystick Part Studio)

| 변수 | 값 | 확인된 용도 |
|---|---|---|
| `#button_width` | 8 mm | 1·2행 개구부 한 변 ✔ 스케치 일치 |
| `#button_gap` | 3 mm | 개구부 간 간격 ✔ 스케치 일치 |
| `#button_module_width` | 6 mm | 스위치 모듈 폭 (포켓 = 6 + 2×0.2) ✔ |
| `#button_tolerance` | 0.2 mm | 캡 클리어런스 · 포켓 여유 ✔ |
| `#button_support_thickness` | 4 mm | 지지 두께 |
| `#button_cover_height` | 4 mm | 캡 높이 ✔ Extrude 17 일치 |
| `#switch_width` | 10 mm | 3행 개구부 폭 ✔ |
| `#switch_height` | 7 mm | 3행 개구부 높이 ✔ |
| `#joystick_hole_diameter` | 15 mm | 조이스틱 구멍 ✔ 실측 d=15.000 |
| `#small_joystick_top_diameter` | 14 mm | 조이스틱 캡 |
| `#small_joystick_pin_height` | 8 mm | Extrude 25 깊이식에 사용 ✔ |
| `#screw_diameter` | 3 mm | 쉘 체결 M3 |
| `#screw_head_width` | 5 mm | 나사 머리 |

### 8.2 그립 본체

| 항목 | 값 | 출처 |
|---|---|---|
| 그립 전체 길이 | **126.562 mm** | `Joystick_front_profile` 중심선 (0,−50.266)→(0,76.295) |
| 하단 폭 | 39.996 mm (±19.998 @ y=−50.266) | 실측 |
| 상단 폭 | 28.858 mm (±14.429 @ y=74.939) | 실측 |
| 버튼 구간 폭 | 약 34.3~34.6 mm (±17.138 @ y=43.733, ±17.300 @ y=32.733) | 실측 |
| **버튼 클러스터 폭** | **30.000 mm** (x −15 … +15) | 실측 → 전면 폭의 약 87% 점유 |
| 벽 두께 | 3 mm | `Shell 1` |
| 쉘 체결 나사 | M3×0.50 ×16, 3개 | Joystick assembly BOM |
| 나사 위치 (side plane 'JEC') | (−41.863, 45.981) / (−14.441, 23.064) / (15.801, −21.354) | `Screw_holes` |
| 나사 홀 단면 | r=1.35 / 1.75 / 3.0 / 3.5 (4중 원) | 실측 — 관통·머리·보스 |
| Pitch 결합부 | 21.072 × 25.672 mm 사각 | `Attachment` 스케치 |

---

## 9. Mirror / Pattern 관계

| Feature | Type | patternType | operationType | 미러 평면 | 대상 |
|---|---|---|---|---|---|
| `Mirror 1` (`FfyGpppYw8McLsz_2`) | mirror | PART | **NEW** | `'JEC'` | 쉘 본체 → **Joystick_1 / Joystick_2 생성** |
| `Mirror 2` (`FqYBXB9oEf4GDTk_5`) | mirror | PART | **ADD** | `'RVDG'` | backplate |
| (스케치 내부) `Buttons` | 구속 mirror | — | — | x=0 구속선 | 개구부 좌우 대칭 |
| (스케치 내부) `Joystick_front_profile` | 구속 mirror | — | — | x=0 구속선 | 전면 프로파일 좌우 대칭 |
| feature-level **Pattern** | — | — | — | — | **트리에 존재하지 않음** |

### 결정적 사실

`Mirror 1`의 미러 평면 `'JEC'`는 다음과 동일한 평면이다:

- `Joystick_side_profile`의 스케치 평면 → `'JEC'`
- `Screw_holes`의 스케치 평면 → `'JEC'`

즉 **쉘 분할면 = 측면 프로파일 평면 = 나사 배치 평면**이며,
`Buttons` 스케치의 x=0 대칭선이 바로 이 평면 위에 놓인다.

결과적으로 원본 버튼 배치는:

```
        LEFT shell        분할면        RIGHT shell
1행:    BTN_1 (x=-11)   BTN_2 (x=0)    BTN_3 (x=+11)
2행:    BTN_4 (x=-11)   BTN_5 (x=0)    BTN_6 (x=+11)
3행:    BTN_7 (x=-8.157)      —        BTN_8 (x=+8.157)
        ---------         ---------    ---------
합계:      3개              2개            3개
```

중앙 2개(BTN_2, BTN_5)는 x −4…+4 를 차지하므로 분할면을 **양쪽으로 4mm씩 걸친다.**
스위치 포켓도 x −3.2…+3.2로 걸친다. 조이스틱 포켓(25mm 폭)도 마찬가지다.

**→ 원본은 "LEFT n개 + RIGHT m개" 형태의 비대칭 배치를 애초에 지원하지 않는 구조다.**

---

## 10. 기존 구조 재사용 가능성

### Option A — 기존 버튼 Feature를 Copy/Pattern 후 위치만 변경

| 평가 항목 | 판정 |
|---|---|
| 원본 파라메트릭 보존성 | **나쁨.** `Buttons`, `Buttons_backplate_holes`, `Buttons_cover` 세 스케치를 편집해야 하는데, 기존 8개 버튼이 같은 스케치 안에 있다 → "기존 버튼 건드리지 말 것" 조건 위반 위험 |
| 수정 난이도 | 높음. 스케치 내부 mirror 구속을 부분 해제해야 3+1 비대칭이 가능 |
| 오류 가능성 | **매우 높음.** 스케치 구속 하나가 깨지면 `Extrude 2`/`Extrude 7`가 동시에 실패하고 버튼 8개 전부 영향 |
| 위치 조정 편의성 | 나쁨. 새 버튼과 기존 버튼이 같은 평면에 묶임 → 검지/중지 위치로 못 내려감 |
| shell 형상 변화 대응 | 보통 |
| API/FeatureScript 자동화 | 어려움. 기존 스케치 엔티티·구속을 in-place 편집해야 함 |
| **결론** | **부적합** |

### Option B — 기존 구조를 reference로 삼고 새 독립 Feature 생성

| 평가 항목 | 판정 |
|---|---|
| 원본 파라메트릭 보존성 | **매우 좋음.** 기존 피처를 전혀 건드리지 않고 트리 끝(현재 rollbackIndex 89 이후)에 append |
| 수정 난이도 | 보통. 새 cPlane + 새 스케치 + 새 Extrude 세트를 만들면 됨 |
| 오류 가능성 | **낮음.** 실패해도 기존 8개 버튼은 영향 없음 (선행 피처이므로) |
| 위치 조정 편의성 | **매우 좋음.** 신규 변수(`#index_button_*`, `#middle_button_*`)로 독립 제어 가능 |
| shell 형상 변화 대응 | 좋음. 곡면 참조를 UP_TO_SURFACE로 잡으면 따라감 |
| API/FeatureScript 자동화 | 보통. `POST .../features`로 append만 하면 되고 기존 엔티티 편집 불필요 |
| 검증된 치수 재사용 | **가능.** 8/3/6.4/0.2/4mm 체계를 그대로 상속 |
| **결론** | **추천** |

### Option C — Derived / SuperDerive로 기존 geometry 재사용

| 평가 항목 | 판정 |
|---|---|
| 원본 파라메트릭 보존성 | 좋음 (원본 미변경) |
| 수정 난이도 | **높음.** Joystick Studio는 이미 `superDerive 1`로 Base를 가져오고 있어 derive 체인이 2중이 됨 |
| 오류 가능성 | 중간~높음. derive 소스가 바뀌면 하류 전체가 흔들림 (Base→Joystick 종속과 동일한 위험) |
| 위치 조정 편의성 | 나쁨. derive된 형상은 위치 재배치가 부자연스러움 |
| shell 형상 변화 대응 | 나쁨 |
| API 자동화 | 어려움 |
| 적합한 용도 | 버튼 캡·스위치 홀더를 **별도 Part Studio로 모듈화**해서 재사용할 때는 유효 |
| **결론** | 주 방식으로는 부적합. 캡/홀더 모듈화 한정으로 검토 가치 있음 |

### 추천

**Option B.** 단, 다음 조건을 붙인다.

1. 신규 변수는 원본 값을 초기값으로 복사하되 이름을 분리한다
   (`#index_button_width = #button_width` 형태로 시작 → 나중에 독립 조정 가능).
2. 모든 신규 피처는 **트리 최하단에 append**한다. 기존 피처 사이에 끼워 넣지 않는다.
3. `Mirror 1` 이후 단계이므로 LEFT/RIGHT 쉘이 이미 분리돼 있다.
   → **비대칭(3+1) 배치를 feature mirror 없이 직접 작도할 수 있다.**
4. 신규 버튼용 backplate/리브는 기존 backplate를 확장하지 말고 **별도 body**로 만든다.

---

## 11. 검지 후보 영역

```text
INDEX candidate zone
- usable area          : 전면, front_y 약 0 ~ 22 mm 구간 (기존 버튼 하단 24.733 아래)
                         폭 방향 약 ±17 mm (전면 폭 약 34~38 mm)
- screw boss interference : 나사 #2 @ side-plane y = 23.064 → 구간 상단 경계에 바로 인접. 
                            나사 홀 최대 r=3.5 (⌀7) + 보스 필요
- minimum wall thickness  : 3 mm (Shell 1) — 스위치 포켓 6.4 mm 를 벽 안에 넣을 수 없음.
                            기존과 동일하게 별도 backplate/리브 구조 필요
- internal clearance      : UNKNOWN (bodydetails / massproperties 401)
```

근거: 기존 버튼 클러스터 최하단이 front_y 24.733. 그립 하단은 front_y −50.266.
나사 #2가 y=23.064로 클러스터 바로 아래에 있어, 실질 시작선은 front_y 약 22mm 이하다.

## 12. 중지 후보 영역

```text
MIDDLE candidate zone
- usable area          : 전면, front_y 약 −18 ~ 0 mm 구간 (검지 영역 아래)
                         폭 방향 약 ±18~20 mm (하단으로 갈수록 넓어짐, 최대 ±19.998)
- screw boss interference : 나사 #3 @ side-plane y = −21.354 → 구간 하단 경계 부근
- minimum wall thickness  : 3 mm (동일)
- internal clearance      : UNKNOWN. 특히 Pitch attachment(21.072 × 25.672 mm)와
                            배선 경로가 그립 하부를 지나갈 가능성이 높음 → 확인 필요
```

근거: 나사 #2(y=23.064)와 나사 #3(y=−21.354) 사이 약 44mm 구간이 방해물이 가장 적다.
이 구간을 검지·중지가 나눠 쓰는 배치가 가장 현실적이다.

> 두 영역 모두 **정확한 곡면 형상과 내부 여유는 확인하지 못했다.**
> 현재 근거는 2D 스케치 좌표뿐이며, 3D 검증에는 API 키가 필요하다.

---

## 13. 예상 간섭 요소

| # | 간섭 요소 | 위치 / 값 | 영향 | 확실성 |
|---|---|---|---|---|
| 1 | 쉘 체결 나사 #2 | side-plane (−14.441, 23.064), 홀 ⌀7 | 검지 영역 상단 경계 침범 | **확정** |
| 2 | 쉘 체결 나사 #3 | side-plane (15.801, −21.354), 홀 ⌀7 | 중지 영역 하단 경계 침범 | **확정** |
| 3 | 쉘 분할면 (`'JEC'`) | 전면 중앙 x=0 | 중앙에 버튼을 두면 두 쉘에 걸침 | **확정** |
| 4 | 벽 두께 3mm vs 포켓 6.4mm | — | 벽만으로 스위치 수납 불가, 내부 구조 필수 | **확정** |
| 5 | 기존 backplate 하단 | Buttons_plane y ≈ −22.976 (front_y ≈ 25.5) | 신규 영역과 경계 접함 | **확정** |
| 6 | Pitch attachment | 21.072 × 25.672 mm | 그립 하부 내부 점유 | 위치 **UNKNOWN** |
| 7 | 배선 경로 | Joystick Studio에 명시 피처 없음 | 기존 8버튼 + 조이스틱 배선이 하부를 지나갈 것 | **UNKNOWN** |
| 8 | 로프트 곡률 | `Loft 2` 4단면 SURFACE 로프트 | 평면 스케치를 곡면에 투영해야 함 | **확정** |
| 9 | 나사 #1 | side-plane (−41.863, 45.981) | 기존 버튼 2행·3행 사이 — 신규 영역과 무관 | **확정** |

---

## 14. 추천 재사용 방식

**Option B (새로운 독립 Feature) + 기존 치수 체계 상속.**

구체적 실행 계획 (아직 실행하지 않음):

1. 사용자 소유 사본 문서 확보 (원본은 Adam Simon 소유 → 수정 불가)
2. 신규 변수 블록을 트리 최하단에 추가 — 초기값은 원본과 동일
   - `#finger_button_width = 8mm`, `#finger_button_gap = 3mm`
   - `#finger_button_module_width = 6mm`, `#finger_button_tolerance = 0.2mm`
   - `#finger_button_cover_height = 4mm`, `#finger_button_support_thickness = 4mm`
3. 검지용 / 중지용 cPlane 신규 생성 (기존 `Buttons_plane`과 동일한 LINE_ANGLE 방식)
4. **LEFT 쉘용 스케치**(버튼 3개)와 **RIGHT 쉘용 스케치**(버튼 1개)를 **분리 작성** —
   mirror 구속을 걸지 않는다. 이것이 3+1 비대칭의 핵심
5. 개구부 REMOVE → 신규 backplate/리브 ADD → 포켓 REMOVE → 캡 NEW 순서로
   원본 체인을 그대로 모사
6. 각 단계마다 조회 → 확인 → 다음 (한 번에 하나)

FeatureScript 자동화는 4단계(곡면 위 평면 정의)가 가장 어렵다.
초기 배치는 Onshape UI에서 잡고, 이후 파라미터 조정만 API로 자동화하는 편이 안전하다.

---

## 15. 아직 확인되지 않은 사항 (UNKNOWN)

**401로 막힌 것 (API Read 키 필요):**

- 버튼 8개의 전역 3D 좌표 → 엄지 영역 확정 판단
- `Buttons_plane`의 3D 위치·법선 → 버튼 눌림 방향의 절대 방향
- assembly mate 관계 → 캡/스위치/backplate가 어떻게 구속되는지
- 그립 bounding box / 무게중심
- Joystick_1 / Joystick_2 각각의 body 형상 → 어느 버튼이 실제로 어느 쉘에 속하는지 최종 확인
- `Roll_holder` / `Roll_holder_2` 역할 분담

**데이터가 있어도 형상 해석이 필요한 것:**

- 버튼 캡의 travel 제한 구조와 plunger 형상
- 스위치 고정이 snap fit인지 단순 끼움인지
- adhesive 필요 여부
- 배선 경로 (Joystick Studio에 명시적 피처 없음)
- `Pitch attachment`의 그립 내부 점유 범위
- cap part 이름(corner/side/wide/middle) ↔ 행 대응의 최종 확정
- HW504_B가 assembly에 2개인 이유

**설계 결정 대기:**

- 검지/중지 버튼의 정확한 위치 (사용자 손 치수 필요)
- 신규 버튼도 원본과 같은 8mm 각형 캡을 쓸 것인지
- LEFT 3개의 배열 방향 (세로 1열 / 가로 1열 / 2+1)
- 신규 backplate를 기존 것과 통합할지 완전 분리할지
