# 25° 단일 경사 + 랩 스커트 — 최종

**형상 재설계 0건.** 시각 감사 / 측정기 수정 / 제조 export 만 수행했다.
Onshape API 호출 0건.

---

## 1. 시각·기하 감사 — 실제 void 0

렌더는 믿지 않았다. 앞서 **실제 구멍을 렌더 아티팩트로 오판한 전력**이 있어서
이번에는 SIDE 방향 **광선 투영**으로 판정했다.

방법: (u, h) 격자마다 X 방향 광선을 쏴 재료 유무를 채우고,
**격자 바깥에서 flood fill** 한 뒤 남는 빈칸을 내부 void 로 본다.

```
격자            159 x 59  @ 2.5 mm
내부 void 칸    0
```

하우징 ↔ 팔받침, 하우징 ↔ 측면 스커트, 하우징 ↔ 후방 스커트 경계 전부
의도하지 않은 빈 곳이 **없다**.

> 참고: 이 감사가 필요했던 이유. 이전 라운드에서 (Y ≈ −33, Z −57~−116) 에
> 실제 재료 없는 구간이 있었는데 렌더만 보고 아티팩트로 판단했다.
> 원인은 동결 코어의 앞부분이 지면 근처 스커트뿐이고 덱 높이 몸통은
> Y ≥ −30 에서만 있다는 것이었다. 광선 판정이 그걸 잡아냈다.

## 2. 측정기 수정 — `wrist_area_mm2` 폐기

기존 `wrist_area_mm2` 는 **7° 패드 평면 face** 를 찾는 방식이라 25° 단일 경사
구조에서는 구조적으로 0 이 나온다. 폐기하고 새 지표로 대체했다.

### `ARM_SUPPORT_SURFACE_AREA`

위를 향하는 면(법선 · 월드수직 > 0.70) 중 팔받침 구간(u < −50, 지면 위 3 mm 이상).

```
ARM_SUPPORT_SURFACE_AREA        11,631.33 mm2
PROJECTED_ARM_SUPPORT_AREA      10,269.93 mm2
평균 경사                            28.00 deg
u 범위                          -228.7 ~ -50.1
삼각형                                2,578
```

**이전에 보고한 31,685 mm² 는 틀린 값이다.** 그 지표는 모델 **전체**의
위를 향한 면(u −216 ~ +133)을 세서 덱과 후방 외피까지 포함했다.
새 값 11,631 mm² 는 경사면 길이 173 mm × 폭 약 70 mm ≈ 12,100 mm² 와 일치하고,
평균 경사 28.0° 도 25° 설계 + 어깨 라운드를 반영한 값으로 타당하다.

## 3. 캐리어 인출 — DIRECT BREP

```
dz    0 mm : 충돌 0.000000 mm3
dz   20 mm : 충돌 0.000000 mm3
dz   40 mm : 충돌 0.000000 mm3
dz   60 mm : 충돌 0.000000 mm3
dz   80 mm : 충돌 0.000000 mm3
dz  100 mm : 충돌 0.000000 mm3
```

**측방 여유 실측** (캐리어를 옆으로 밀어 처음 닿는 거리):

```
+-0.3 mm : 무충돌
+-0.5 mm : 4방향 모두 접촉 (예 dx +0.5, dz 0 -> 201.856 mm3)
```

즉 실제 여유는 **0.3 < clearance ≤ 0.5 mm** 로, 스커트를 자를 때 준
설계 여유 0.5 mm 와 정확히 일치한다.

> 최종화 스크립트가 처음 보고한 `min_horizontal_clearance = 0.0042 mm` 는
> **측정 방식이 틀린 값**이다. 캐리어의 **bbox** 로 쟀는데 실제 외형이 bbox 보다
> 작아서, 그 모서리 빈 공간에 있는 하우징 재료를 침범으로 잡았다.
> 위 측방 이동 방식이 실제 여유를 준다.

## 4. 구조 수치

| 항목 | 값 |
|---|---|
| L / W / H | **365.760 / 133.600 / 140.524 mm** |
| 부피 | 934,074 mm³ |
| 질량 (인필 25% 가정) | **289.6 g** |
| 팔 지지면 | 11,631 mm² (투영 10,270) |
| 접지 면적 | **11,173 mm²** |
| 최전방 지지 u | −227.18 |
| 최후방 접지 u | **+162.18** |
| 도심 u | +30.87 |
| **후방 지지팔** | **131.31 mm** |

랩 스커트 효과가 여기서 드러난다 — 접지 면적 3,017 → **11,173 mm² (3.7배)**,
후방 지지팔 65.8 → **131.3 mm (2.0배)**.

## 5. STL 제조 acceptance

`BRepTools.Clean_s` 로 기존 tessellation 을 제거한 뒤 재생성 (tol 0.015 / ang 0.08).

```
삼각형            62,368
boundary edges         0
non-manifold edges     0
degenerate triangles   0
watertight          True
단위                  mm
```

## 6. 23게이트 검증 — PASS 23 / FAIL 0

| 게이트 | 결과 |
|---|---|
| 그립 방향 불변량 | PASS |
| 기준면 vs 수평 | **20.000000000°** |
| 그립 중립축 ⟂ 기준면 | **90°** |
| HAND_REF / 피벗 / 스톡 Base / 캐리어 위치 | 무변경 |
| 덱→HAND_REF / 지면→HAND_REF | **55.8785 / 161.0208** |
| 동결 코어 보존 (`NEW & FROZEN_HOUSING`) | 코어 전체 포함 |
| 스톡 돌출 | **0.0000 mm** |
| 캐리어 −Z 인출 0–100 mm (DIRECT BREP) | PASS |
| 9자세 모션 (`motion_configs_gripfix.npz`) | 전부 0 / 20,130 점 |
| 새 외피가 **추가한** 나사 간섭 | **0.000000 mm³** |
| BREP validity | PASS |

모션은 **TRANSFORMED / CACHED MOTION ENVELOPE CHECK** 다 (DIRECT 아님).
동결 코어가 이미 갖고 있던 M3 나사 머리 간섭 **138.2772 mm³** 는 범위 밖 NOTE 로 유지.

검증기가 아직 출력하는 `wrist_area_mm2 = 0` 은 **폐기된 지표**다 (§2 참조).
유효한 값은 `ARM_SUPPORT_SURFACE_AREA = 11,631.33 mm²` 이다.

## 7. BREP

```
solid 1   shells 1   faces 572   valid True
volume 934,121.25 mm3
bbox 133.6000 x 365.7597 x 154.5807
```

## 8. 산출물

```
export/step/ERGO_HOUSING_25_WRAP_FINAL.step        2.88 MB   설계 마스터
export/brep/ERGO_HOUSING_25_WRAP_FINAL.brep        6.22 MB
export/stl/ERGO_HOUSING_25_WRAP_FINAL.stl          2.97 MB   제조용 (watertight)

export/step/BOTTOM_CARRIER_FINAL.step              0.18 MB   동결 STEP 그대로
export/stl/BOTTOM_CARRIER_FINAL.stl                1.12 MB   watertight

export/step/ONEGRIP_25_WRAP_FINAL_PREVIEW.step    30.54 MB   부품 분리 유지 (fuse 안 함)
    ERGO_HOUSING_25_WRAP_FINAL / BOTTOM_CARRIER / ONEGRIP(180도 교정) /
    STOCK_GIMBAL / ELECTRONICS

preview/FINAL25_{SIDE,ISOMETRIC,TOP,FRONT,REAR,BOTTOM,CUTAWAY}.png
reports/10_25wrap_final.json
```

이전 산출물(`ERGO_HOUSING_W2*.step`, `PRINT_FINAL`, `TOPDROP_*`, `GROUND_*`,
`SLOPE20/25/28/30*`) 은 전부 보존했다.

## 9. 이번 단계에서 고친 것

1. **`wrist_area_mm2` 폐기 → `ARM_SUPPORT_SURFACE_AREA` 신설.**
   이전에 보고한 31,685 mm² 는 모델 전체의 위를 향한 면을 세서 덱·후방까지
   포함한 값이라 틀렸다. 실제 팔받침은 **11,631 mm²** 다.
2. **캐리어 여유 측정 방식 교정.** bbox 기준은 0.0042 mm 라는 무의미한 값을 냈다.
   캐리어를 실제로 옆으로 밀어 재니 **0.3 < clearance ≤ 0.5 mm** 로
   설계값과 일치한다.
3. **CUTAWAY 절단 방식 교정.** 삼각형 중심으로 자르면 절단면을 걸친 삼각형이
   뾰족하게 튀어나온다. 세 정점이 모두 한쪽인 것만 남기도록 바꿨다.

## 10. 미착수 (지시대로)

M3 나사 재설계 / 전장 / 배터리 / 버튼 / 상부 손가락 형상.
최종 형상에 새 설계 변경은 넣지 않았다.
