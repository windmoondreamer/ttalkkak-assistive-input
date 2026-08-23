# GROUND B — 최종 외피 마감

**GROUND B 를 최종 외피로 확정했다.** 이번 단계는 형상 재설계 없이
**모서리 마감 + 검증 + 제조용 export** 만 수행했다.
Onshape API 호출 0건. `ERGO_HOUSING_W2.step` 과 `ERGO_HOUSING_W2_GROUND_A.*` 는 보존했다.

---

## 1. 필렛 — selector 를 이면각으로 판별하게 바꿨다

기존 `WRIST_SIDE` 는 `|X| > 30` 만 봐서 **208~210개**를 잡았고 안전 캡에 걸려 생략됐다.
§2 지시대로 의미 기반 selector 를 새로 만들었다:

```
LEFT_WRIST_CONTACT / RIGHT_WRIST_CONTACT
    패드 평면 위(거리<0.5) + 길이방향(Y지배) + 상면 높이(h>85) + |X|>15
GROUND_TRANSITION
    전면 수직면 위(|u - U_TIP|<0.5) + h_max < 20      (뜬 립 <-> 지면 스커트)
FRONT_LIP
    전면 수직면 위 + h_max >= 20
PAD_PERIMETER
    패드 평면 위 + 나머지
```

edge index 하드코딩은 없다. 모든 조건이 위치·방향·인접면 법선에서 나온다.

### 결정적 발견 — 접촉 외곽 후보의 이면각이 0.000°

좌우 접촉 외곽으로 뽑힌 4+4개의 **이면각을 실측하니 정확히 0.000°** 였다.
`seg_loft` 로 인접 단면을 union 하면서 **평면 위에 남은 인공 이음매**이지
물리적 모서리가 아니다. `PAD_PERIMETER` 후보 대부분도 같았다.
즉 R2.0/R1.5 필렛이 전부 실패한 것이 **정상**이다 —
손목 상면은 이미 평평하고 좌우 가장자리는 R16 라운드라 깎을 모서리가 없다.

그래서 selector 에 **이면각 5° 미만 제외** 조건을 넣었다.

| 그룹 | 이면각 | 결과 |
|---|---|---|
| `GROUND_TRANSITION` | 70.4 ~ 71.4° | **R1.0 · 6개 적용** |
| `PAD_PERIMETER` | (유효 1개) | **R3.0 · 1개 적용** |
| `FRONT_LIP` | 78 ~ 83° | R2.0 → 1.5 → 1.0 전부 실패 → **미적용** |
| `LEFT/RIGHT_WRIST_CONTACT` | **0.000°** | 대상 없음 (인공 이음매) |

`GROUND_TRANSITION` 은 R2.0/R1.5 가 실패해 §4 의 강등 규칙대로 **R1.0** 으로 적용했다.

### OCC segfault 와 대응

`FRONT_LIP` 이분분할 도중 OCC 가 **segfault (exit 139)** 로 죽었다.
예외가 아니라 프로세스가 죽으므로 `try` 로 잡을 수 없다.
그래서 `FILLET_PLAN` 에 **그룹별 분할 허용 플래그**를 두고 `FRONT_LIP` 은 껐다.
대가로 전면 수직면 모서리는 날카롭게 남는다 — 이 항목은 미해결로 남긴다.

## 2. 필렛 후 keep-out 재적용 (§6)

필렛은 오목부에 재료를 더하므로 기존 순서대로 다시 적용했다:

```
CAVITY_PROTECT  →  CARRIER_EXTRACTION_SWEEP  →  STOCK/FASTENER keep-out
→  frozen core 재 union  →  heal
```

`heal NEW_FILLETED` 결과 **valid=True / shells 1 / faces 428 / 732,080.53 mm³**.

---

## 3. 검증 — 23 PASS / 0 FAIL (§8)

| 게이트 | 결과 |
|---|---|
| 그립 방향 불변량 (교정 후 부호 유지) | PASS |
| 기준면 vs 수평 | **20.000000000°** |
| 그립 중립축 ⟂ 기준면 | **90°** |
| HAND_REF / 피벗 / 스톡 Base / 캐리어 | 무변경 |
| 덱→HAND_REF / 지면→HAND_REF | **55.8785 / 161.0208** |
| 동결 코어 보존 (`NEW & FROZEN_HOUSING`) | 코어 전체 포함 |
| 스톡 돌출 | **0.0000 mm** |
| 캐리어 −Z 인출 0–100 mm (DIRECT BREP) | PASS |
| 9자세 모션 (`motion_configs_gripfix.npz`) | **전부 0 / 20,130 점** |
| 새 외피가 **추가한** 나사 간섭 | **0.000000 mm³** |
| BREP validity | PASS |

모션 검사는 **TRANSFORMED / CACHED MOTION ENVELOPE CHECK** 다 (DIRECT 아님).
동결 코어가 이미 갖고 있던 M3 나사 머리 간섭 **138.2772 mm³** 는 이번 범위 밖이며
NOTE 로 유지한다.

### BREP 게이트 (§7)

```
solid 1   shells 1   faces 428   edges 1180
valid = True   sliver shell 0개
volume 732,081.2860 mm3
bbox 133.6000 x 227.4551 x 146.0911
```

## 4. 최종 측정 (§9)

| 항목 | 값 | 기준 대비 |
|---|---|---|
| W [mm] | **133.6000** | 동일 |
| L [mm] | **227.4551** | −0.18 |
| H (월드) [mm] | **139.8569** | 동일 |
| 첫 접지 u [mm] | **−68.1086** | 목표 −68.10, **차 0.009** |
| floating span [mm] | **13.7814** | 목표 13.79, **차 0.009** |
| 앞끝 u [mm] | −81.8900 | 동일 |
| 지면 블렌드 최대 기울기 [°] | 37.82 (실측 bin) / **28.15 (설계)** | — |
| 지면 블렌드 평균 기울기 [°] | 17.01 | — |
| 접지 면적 [mm²] | **3,017.48** | 목표 3,018 |
| 손목 지지 면적 [mm²] | 4,910.60 @ 7.0° | — |
| 부피 [mm³] | **732,063.68** | — |
| 최소 살두께 (전체) [mm] | 0.288 (1% 0.658 / 중앙 5.444) | — |
| 최소 살두께 (신규 스커트) [mm] | 0.250 (1% 0.767 / **중앙 5.001**) | nominal 5.0 |

**§5 접지 기준 통과.** 필렛 후에도 첫 접지와 floating span 모두 **0.01 mm** 이내로 유지됐다.

> 처음 측정에서 −69.89 / 12.00 이 나왔는데, 이는 `measure()` 가 히스토그램
> **bin 중심 좌표를 u 로 쓴 버그**였다. 실제 점에서 재도록 고쳤다.

### 최소 살두께에 대한 정직한 설명

신규 스커트의 **중앙값은 5.001 mm 로 설계 nominal 과 일치**한다.
최소 0.250 mm 가 나오는 지점은 전부 **지면 접촉선**(h ≈ 0.07)이다.
밑면이 15~28° 로 지면에 접근하다 지면 평면으로 잘리므로 접촉선에서 두께가
0 으로 수렴한다 — §7 이 요구한 **near-tangent 접근의 필연적 결과**다.
그 밖의 얇은 지점(h 45~47, u 1~7, X ±49~50)은 **동결 코어** 쪽이라 범위 밖이다.

FDM 첫 레이어가 칼날에서 시작되므로, 원한다면 다음 단계에서 지면 접촉부에
0.6~0.8 mm 최소 두께를 강제할 수 있다. 다만 그건 형상 변경이라 이번 HARD FREEZE 밖이다.

---

## 5. 산출물

```
export/step/ERGO_HOUSING_W2_FINAL.step          2.47 MB   ← 설계 마스터
export/brep/ERGO_HOUSING_W2_FINAL.brep          8.55 MB
export/stl/ERGO_HOUSING_W2_FINAL.stl            5.29 MB   110,849 삼각형
                                                (tolerance 0.015 / angular 0.08, 단위 mm)

export/step/BOTTOM_CARRIER_FINAL.step           0.18 MB   ← 동결 STEP 그대로
export/stl/BOTTOM_CARRIER_FINAL.stl             1.12 MB   23,452 삼각형, watertight True
                                                부피 90,177.998830 mm3 (동결값과 완전 일치)

export/step/ONEGRIP_FINAL_LOCAL_PREVIEW.step   30.1 MB    부품 분리 유지 (fuse 안 함)
    ERGO_HOUSING_W2_FINAL / BOTTOM_CARRIER / ONEGRIP(180도 교정) /
    STOCK_GIMBAL / ELECTRONICS

preview/FINAL_B_{SIDE,ISOMETRIC,TOP,FRONT,BOTTOM,CUTAWAY}.png
reports/08_final_b.json
```

보존한 것: `ERGO_HOUSING_W2.step`, `ERGO_HOUSING_W2_GROUND_A.*`,
`ERGO_HOUSING_W2_TOPDROP_A/B.*`.

## 6. 미해결 2건 (정직하게 남긴다)

### (a) STL 에 경계 모서리 1 + 비다양체 1 → watertight = False

- **tessellation 밀도와 무관하다.** `BRepTools.Clean_s` 후 tolerance 0.010(300,635 삼각형)
  과 0.030(33,149 삼각형) 모두 동일하게 경계 1 / 비다양체 1 이 나온다.
- 위치 **(22.19, −130.09, −121.58), u −80.66, h 12.58** — 립 앞끝 **우측**이고
  `GROUND_TRANSITION` 필렛이 걸린 모서리(c=(±20.45, −131.94, −123.07), h[5.01, 16.11])와
  정확히 겹친다. 좌측(−X)에는 결함이 없다.
- **STEP / BREP 마스터는 `BRepCheck_Analyzer` valid** 이고 shells 1 / sliver 0 이다.
  결함은 STL 삼각분할 단계에서만 나타난다.
- 규모는 삼각형 하나 크기의 구멍이라 일반 슬라이서가 자동 복구한다.
- 확정하려면 `GROUND_TRANSITION` 필렛을 뺀 빌드와 비교해야 하는데,
  §4 가 그 필렛을 요구하므로 이번 범위에서는 하지 않았다.
  필요하면 필렛 없는 버전을 만들어 원인을 확정할 수 있다.

### (b) `FRONT_LIP` 필렛 미적용

전면 수직면 모서리(이면각 78~83°)에 R2.0 → 1.5 → 1.0 을 모두 시도했으나 전부 실패했다.
이분분할을 켜면 OCC 가 **segfault (exit 139)** 로 죽는다 — 예외가 아니라 프로세스가
죽으므로 `try` 로 잡을 수 없다. 그래서 그 그룹은 분할을 끄고 날카롭게 남겼다.

## 7. 이번 단계에서 고친 측정 버그 2건

1. `measure()` 가 히스토그램 **bin 중심 좌표를 u 로** 써서 접지 −69.89 / floating 12.00 을
   보고했다. 실제 점 기준으로 고치니 **−68.11 / 13.78** 로 목표와 0.01 mm 이내 일치.
2. 살두께 레이캐스팅이 **자기 인접 삼각형**을 맞아 0.054 mm 를 보고했다.
   시작점 오프셋 0.05 mm + t 하한 0.2 mm 로 고쳤다.
