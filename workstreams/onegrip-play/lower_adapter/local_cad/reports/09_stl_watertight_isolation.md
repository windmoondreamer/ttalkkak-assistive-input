# FINAL STL watertight 원인 격리

**결론: 원인은 `GROUND_TRANSITION` R1.0 필렛이다.**
§6 규칙에 따라 그 필렛을 끈 형상을 제조용 최종으로 채택했다.
형상 재설계·치수 재최적화는 하지 않았다. R1.0 제거 외 변경 0건.

---

## 1. A/B 테스트

형상 차이가 `GROUND_TRANSITION` 필렛 하나뿐인 두 복사본을 만들었다.
`PAD_PERIMETER` R3.0 은 양쪽 모두 유지, `FRONT_LIP` 은 양쪽 모두 미적용(§9).

| | F1 (R1.0 유지) | F0 (R1.0 OFF) |
|---|---|---|
| solid / shells | 1 / 1 | 1 / 1 |
| faces | **428** | **409** |
| edges | 1,180 | 1,143 |
| BRepCheck valid | True | True |
| volume [mm³] | 732,081.2860 | 732,223.7555 |
| bbox | 133.6000 × 227.4551 × 146.0911 | 133.6000 × 227.6362 × 146.0911 |

부피 차 **−142.4695 mm³**, face 차 **+19** — 필렛이 깎아낸 분량 그대로다.

## 2. 판정 — 동일 조건에서만 갈렸다

**첫 비교는 잘못된 결론("둘 다 watertight")을 냈다.** 원인은 비교 조건이 섞인 것이다:

- `test_f1f0.py` 가 BREP 지표는 STEP 에서, STL 지표는 **`ergo_shell` 이 build 결과에서
  바로 만든 파일**에서 읽었다. 두 경로가 섞여 동일 조건이 아니었다.
- 같은 이유로 F1 의 `edges` 가 1,180 이 아니라 **165,939** (삼각형 수의 1.5배)로 나왔다.
  **STEP 을 쓰기 전에 tessellation 을 지우지 않아 STEP 파일에 메시가 섞여 들어간 것**이다.
  -> `export_all` 의 `BRepTools.Clean_s` 를 STL 직전에서 **STEP 이전으로** 옮겨 고쳤다.

두 모델을 모두 **STEP 왕복 → `Clean_s` → 동일 tolerance(0.015 / 0.08)** 로 다시
export 하니 명확히 갈렸다:

| | 삼각형 | 경계 edge | 비다양체 edge | watertight |
|---|---|---|---|---|
| **F1** (R1.0 유지) | 110,849 | **1** | **1** | **False** |
| **F0** (R1.0 OFF) | 67,722 | **0** | **0** | **True** |
| `GROUND_B` (=F1 형상) | 110,849 | 1 | 1 | False |

결함 위치는 **(22.19, −130.09, −121.58), u −80.66, h 12.58** 로
`GROUND_TRANSITION` 필렛 대상 모서리(c = (±20.45, −131.94, −123.07), h[5.01, 16.11])와
정확히 겹치고, 좌측(−X)에는 결함이 없다 — 비대칭이라는 점도 국소 필렛 원인과 일치한다.

**따라서 원인 = `GROUND_TRANSITION` R1.0 필렛으로 확정한다.**

## 3. 제조용 최종 — `ERGO_HOUSING_W2_PRINT_FINAL`

`GROUND_TRANSITION` 필렛만 OFF. 그 외 전부 동일.

```
solid 1   shells 1   faces 409   edges 1143   BRepCheck valid = True
volume 732,223.7555 mm3
bbox 133.6000 x 227.6362 x 146.0911
```

### STL acceptance (§7) — 전항목 통과

```
삼각형        67,722
경계 edge     0
비다양체 edge  0
degenerate    0
watertight    True
단위          mm
tolerance     0.015 / angular 0.08
```

STEP 도 `edges 1143` 으로 깨끗하다 (메시 오염 없음).

## 4. 기계 검증 재실행 (§8) — 23 PASS / 0 FAIL 유지

| 항목 | PRINT_FINAL | 요구 |
|---|---|---|
| **first ground contact u** | **−68.1086** | ≈ −68.11 ✓ |
| **floating span [mm]** | **13.7814** | ≈ 13.78 ✓ |
| 앞끝 u [mm] | −81.8900 | 불변 ✓ |
| 접지 면적 [mm²] | 3,017.4800 | 불변 ✓ |
| W / H(월드) [mm] | 133.6000 / 139.8569 | 불변 ✓ |
| L [mm] | 227.6362 | 필렛 제거로 +0.181 (필렛 전 원형값) |
| 덱→HAND_REF / 지면→HAND_REF | 55.8785 / 161.0208 | 불변 ✓ |
| 손목 지지 [mm²] | 4,910.5954 @ 7.0° | 불변 ✓ |
| 스톡 돌출 [mm] | 0.0000 | ✓ |
| 캐리어 −Z 인출 0–100 mm | PASS (DIRECT BREP) | ✓ |
| 9자세 모션 | 전부 0 / 20,130 점 | TRANSFORMED / CACHED ✓ |
| 그립 방향 불변량 | PASS | ✓ |
| 새 외피가 추가한 나사 간섭 | **0.000000 mm³** | ✓ |
| 20° / 90° | 20.000000000° / 90° | ✓ |

동결 코어의 기존 M3 나사 머리 간섭 **138.2772 mm³** 는 범위 밖 NOTE 로 유지한다.

최소 살두께는 신규 스커트 **중앙 5.257 mm**, 최소 0.487 mm (지면 접촉선).
near-tangent 접근의 필연적 결과이며 §7(이전 라운드)에서 설명한 것과 동일하다.

## 5. 산출물

```
export/step/ERGO_HOUSING_W2_PRINT_FINAL.step    ← 제조용 설계 마스터
export/brep/ERGO_HOUSING_W2_PRINT_FINAL.brep
export/stl/ERGO_HOUSING_W2_PRINT_FINAL.stl      ← 제조용 (watertight, 67,722 삼각형, mm)

export/step/BOTTOM_CARRIER_FINAL.step           동결 STEP 그대로 (부피 90,177.998830 일치)
export/stl/BOTTOM_CARRIER_FINAL.stl             watertight True
```

A/B 테스트 산출물 `ERGO_HOUSING_W2_TEST_F1.*` / `..._F0.*` 도 남겨 뒀다.
이전 `ERGO_HOUSING_W2_FINAL.*`, `ERGO_HOUSING_W2.step`, `GROUND_A/B.*`,
`TOPDROP_A/B.*` 전부 보존.

## 6. 이번 작업에서 하지 않은 것

- **`FRONT_LIP` 필렛** — §9 대로 미적용 상태 그대로 뒀다 (이면각 78~83°,
  R2.0/1.5/1.0 전부 실패, 이분분할 시 OCC segfault).
- **프리뷰 / 조립 프리뷰 갱신** — 기존 `FINAL_B_*.png` 와
  `ONEGRIP_FINAL_LOCAL_PREVIEW.step` 은 필렛이 있던 `ERGO_HOUSING_W2_FINAL` 기준이다.
  두 형상의 차이는 `GROUND_TRANSITION` R1.0 필렛 하나(부피 142.47 mm³)뿐이라
  실루엣상 구분이 되지 않는다. 필요하면 갱신하겠다.
- 형상 재설계 / 치수 재최적화 0건.
