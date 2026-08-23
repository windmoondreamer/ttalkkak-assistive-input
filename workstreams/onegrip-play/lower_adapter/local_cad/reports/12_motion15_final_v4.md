# ±15° 내부 모션 클리어런스 — 최종 V4

`ERGO_HOUSING_25_WRAP_FINAL_V3` 에서 **동결 코어 내부 공동벽의 ±15° 모션
클리어런스 절삭만** 수행한 버전이다. 외부 형상은 V3 와 완전히 동일하다.
Onshape API 호출 0건.

V3 및 이전 산출물은 **덮어쓰지 않았다.**

---

## 1. 각도 세 값 — 섞지 말 것

| 구분 | 값 | 근거 |
|---|---|---|
| **DOCUMENTED DESIGN ANGLE** | **15°** | `cad_dump/features_Base.json` 마스터 변수 `#joystick_angle = 15 deg`. 클리어런스가 여기 연동됨 (`#offset_around_pitch = 0.2mm × 15 + 1mm = 4.0mm`) |
| **STOCK GIMBAL MECHANICAL LIMIT** | **≈15° (부분 확인)** | 고정부(Base/Roll_holder×2/Spacer) 대비 이동부(Roll/Pitch/Spring_holder) 회전. Y 축은 14°까지 접촉수 33 으로 완전 평탄, **15°부터 증가**. X 축 결과는 무효 — 2축 카르단을 강체 회전시킨 것이라 한 축에만 유효하다 |
| **V4 HOUSING CLEARANCE LIMIT** | **15.88°** | 24방위 최초 접촉각의 최소값 (방위 45/315°) |

**실사용 허용각은 가장 작은 값이 지배한다.** 현재 셋 중 최소는 스톡/문서의 15° 이고,
하우징은 15.88° 로 그보다 **+0.88°** 여유가 있다.

> **별개 마진:** 포락선 자체에 기하 여유 **1.5 mm** 가 들어 있다. 위 각도 여유와
> 독립된 마진이다.

## 2. 이전 하우징의 모션 기준 = ±10°

하부 어댑터 전체가 Onshape 단계에서 **±10° 9자세 캐시**로 설계·검증됐다
(`motion_configs_gripfix.npz`: neutral / X±10 / Y±10 / 코너 4). 동결 코어
`CONFORMAL_HOUSING` 의 공동도 그 포락선으로 파였다.

그 결과 V3 에서 그립이 **X− 12° / Y± 14° / X+ 16°** 에서 코어에 닿았다.

**충돌은 덱 개구부가 아니다.**

```
깊이별 ±15도 요구 vs 현재 개구부(92.9 x 89.8)
  dz  0 / -2 / -4   ->  충분  (여유 1.2~2.5mm)
  dz -6 / -8 / -10  ->  부족  +1.95 / +2.78 / +4.65 mm

실제 충돌 위치
  X -12도   Y +73.0~74.1        dz -14.8 ~ -11.6   ← 코어 후방 공동벽
  Y ±15도   |X| 49.1~50.4       dz -17.6 ~ -14.4   ← 코어 측면 공동벽
```

**덱 아래 12~18 mm 의 동결 코어 내부 공동벽**이다.

### 내 외피는 무죄

동결 코어 단독과 V3 전체의 각도별 충돌 점 수가 **완전히 동일**했다
(10°: 0/0, 12°: 67/67, 14°: 148/148, 15°: 179/179, 16°: 208/208).
25° 팔받침 / 랩 스커트 / 폭 블렌드는 모션을 1° 도 제한하지 않는다.

## 3. 포락선 방식 — 6번 고쳤다

| # | 방식 | 제거량 | 판정 |
|---|---|---|---|
| 1 | 축정렬 bbox 밴드 (원뿔) | 15,906.6 | **REJECTED** — 0.4mm 리브 발생 |
| 2 | 볼록껍질 다각형 (원뿔) | 7,556.4 | **REJECTED** — 코너 4자세 FAIL |
| 3 | 다각형 프리즘 적층 (정사각 9×9) | 25,444.7 | **REJECTED** — 0.8mm 계단 턱 |
| 4 | 로프트 (정사각 13×13) | 32,353.7 | **REJECTED** — 1mm 박판 잔류 |
| 5 | 로프트 + smear 2mm | 36,654.8 | **REJECTED** — 박판 0.027mm 잔존 |
| 6 | **로프트 + smear 4mm** | **44,885.1** | **ADOPTED** |

### 3-1. bbox → 볼록껍질

축정렬 사각형은 **둥근 포락선의 대각선을 최대 40 % 과다 절삭**한다.
실제 충돌은 축 방향 3곳뿐인데 사방을 다 파서 살이 0.55 mm 까지 얇아지고,
`(51.52, −20.83, −75.63)` 에 **0.4 mm 리브**가 남았다 (+Y 광선 교차 −21.6 / −21.2).

### 3-2. 원뿔 → 정사각형 (핵심)

스톡 짐벌은 Roll·Pitch 독립 2축 카르단이라 도달 집합이 **정사각형**
`|roll| ≤ 15 ∧ |pitch| ≤ 15` 다. 코너 (15,15)의 합성 편향은

```
cos θ = cos15° · cos15° = 0.9330  →  θ = 21.06°
```

로 반각 15° 원뿔 **밖**이다. 원뿔 포락선은 코너 4자세에서 48~129 점 간섭을 남겼다.
기존 ±10° 캐시가 코너 4자세(`X+10Y+10` 등)를 포함한 것도 같은 이유다.

→ 13×13 그리드(169 자세, 2.5° 간격)로 교체.

### 3-3. 적층 → 로프트

1 mm 밴드를 Z 로 `PROT_EPS = 0.1` 만큼 부풀려 쌓으면
`1.0 − 2×0.1 = 0.800 mm` 짜리 계단 턱이 사방에 남는다. `min_wall` 이 정확히
0.800 을 반복 출력한 것이 그것이다.

→ 밴드를 **반경 32각형**으로 정점 수를 통일하고 인접 밴드끼리 ruled loft.
결과적으로 face 수가 1541 → 1312 로 줄었다.

### 3-4. 아래로 4 mm smear

코어 후방 선반(`Z −90.00 ~ −80.02`, 두께 10.0 mm, 밑면이 정확한 평면, 아래는 공동)을
절삭면이 **중간에서 끊어** 1.02 mm 캔틸레버 박판을 남겼다 (73.5 × 9.0 mm).

절삭면은 곡면이라 그 평면에 **접선으로 접근**한다. smear 2 mm 로는 접점이 옮겨갈
뿐이었다 (박판 0.027 mm 로 더 얇아짐). **평면을 완전히 관통**해야 끝난다 → smear 4 mm.

밴드 풀링을 `[i−1, i+1]` → `[i−1, i+4]` 로 바꿔 위 밴드의 큰 껍질을 아래로 번지게 했다.
임의 박스 하드코딩이 아니라 **규칙 자체를 고친 것**이라 다른 위치의 같은 계단도 함께 막힌다.

## 4. §2 DIRECT 모션 수용 — PASS 11/11

실제 stock Pitch/Roll 축 변환(`Rx(roll) @ Ry(pitch)`, 피벗 (0, 27.269160, DECK−52.9823))
으로 이동 solid 12,000 점을 검사했다.

```
[PASS] neutral               간섭 0 / 12000
[PASS] Pitch +15 / -15       0 / 0
[PASS] Roll  +15 / -15       0 / 0
[PASS] corner (+15,+15)      0
[PASS] corner (+15,-15)      0
[PASS] corner (-15,+15)      0
[PASS] corner (-15,-15)      0
[PASS] 24방향 azimuth cone @15도      합계 0
[PASS] 24방향 square boundary @15도   합계 0
```

## 5. §3 각도 여유

방위 24개 각각 coarse sweep → binary search (tol 0.05°). **정사각형 기준**
(`max(|roll|,|pitch|) = 1` 정규화)이라 나오는 값이 곧 축당 각도다.

```
최소 최초접촉각        15.88 도
최소가 나오는 방위     45 / 315 도  (코너 방향, roll = ±pitch)
nominal 15도 대비 여유  +0.88 도
방위별 범위            15.88 ~ 17.4 도
```

코너가 가장 빡빡한 것은 합성 편향이 21.06° 로 가장 크기 때문이며 기하적으로 당연하다.

> 이전 라운드의 `13.53° (여유 −1.47°)` 는 **비단조 오측**이었다. 9×9 그리드
> 사이 각도에서 점이 다른 Z 밴드로 넘어가 껍질 밖으로 삐져나온 것이고,
> 2.5° 그리드 + 밴드 병합 + 로프트로 해소됐다.

## 6. §5 절삭 검증 — PASS

```
V3 volume        992,760.8691 mm3
V4 volume        947,875.7535 mm3
removed           44,885.1156 mm3
```

```
[PASS] external bbox delta        0.000000000 mm
[PASS] external SIDE  silhouette delta  0.000000 mm
[PASS] external TOP   silhouette delta  0.000000 mm
[PASS] external FRONT silhouette delta  0.000000 mm
```

**내부 절삭 외 외부 형상 변화 0.** 절삭 체적은 교집합(`V3 ∩ envelope`)으로도
독립 추출해 **44,885.1146 mm³** 를 얻었다 (감사값과 0.001 이내 일치).

## 7. §6 살두께 — PASS

판정은 **원시 카운트가 아니라 군집 성격**으로 한다. 이 지표는 두 면이 접선으로
만나는 자리를 함께 세고, 접선에서는 살이 연속적으로 0 에 수렴하므로 작은 값이
필연이다. V3(전 게이트 통과 + STL watertight)도 `deck/opening 0.121 mm`,
`wrap-skirt 0.800 mm` 를 원래 갖고 있다.

얇은 지점을 3 mm 격자로 군집화해 확장 형상으로 분류한다 — 한 방향으로만 길면
접선(선형), 두 방향이 넓으면 면적형(리브).

```
rib(area-type) clusters    V3 0   ->   V4 0
sliver solids                              0
원시 슬랩 <1.5mm            V3 123 / V4 139   (차이 16개는 전부 접선선)
원시 슬랩 <2.5mm            V3 397 / V4 423
```

영역별 최소 (축 광선 재료 슬랩, 접선 스침 `|n·d| ≥ 0.35` 필터):

| 영역 | V3 최소 | V4 최소 | 위치 (V4) |
|---|---|---|---|
| deck/opening | 0.121 | 0.121 | (42.20, −15.96, −62.02) |
| rear cavity wall | ≥2.5 | 0.343 | (−40.30, 69.54, −80.19) |
| left cavity wall | ≥2.5 | 0.343 | (−40.30, 69.54, −80.19) |
| right cavity wall | ≥2.5 | 0.147 | (45.20, −6.96, −80.09) |
| wrap-skirt junction | 0.800 | 0.800 | (−50.80, −23.50, −144.96) |
| carrier surround | 1.502 | 1.502 | (−52.75, 24.54, −146.46) |

전체 최소 0.121 mm / 슬랩 5퍼센타일 0.200 mm — **V3 와 동일**.
**0 두께 / knife edge / paper-thin rib / disconnected sliver = 0.**

## 8. §7 BREP 게이트 — PASS

```
solid count      1
shell count      1
BRepCheck valid  True
sliver solids    0
unexpected internal shells  0
faces 1312   edges 3271
volume 947,875.7535 mm3
bbox   133.6000 x 365.7597 x 154.5833
```

## 9. §8 전체 게이트 — PASS 23 / FAIL 0

```
[PASS] 코어 절삭이 ±15도 모션 포락선 안에만 있음 (승인된 예외)
       코어 손실 44,885.11 / 포락선 안 손실 44,885.11 -> 포락선 밖 -0.0001 mm3
[PASS] 기준면 vs 월드 수평          20.000000000 deg
[PASS] 그립 중립축 ⟂ 기준면          90.000000 deg
[PASS] 그립 방향 불변량
[PASS] BOTTOM_CARRIER 무변경        90,177.998830 mm3
[PASS] 캐리어 -Z 인출 0..100 mm      무충돌
[PASS] 9자세 모션 (TRANSFORMED/CACHED)
[PASS] 새 외피가 추가한 나사 간섭     0.000000 mm3
       deck -> HAND_REF    55.8785 mm   (무변경)
       ground -> HAND_REF 161.0208 mm   (무변경)
       stock protrusion     0.0000 mm
       W / L / H  133.6000 / 365.7597 / 140.5240
```

기존 동결 코어의 M3 나사 머리 간섭 **138.2772 mm³** 는 기존 NOTE 그대로 유지.

V3 에서 해결했던 항목도 유지:
- 팔받침 ↔ 조이스틱 블록 초승달 슬릿 = **0**
- 외부 의도치 않은 void = **0**

## 10. §9 void 감사 — PASS

메모리 문제를 고친 감사기로 재실행 (정수 인코딩 스택, px 1400 → 800).

```
앞 부각10도 / 20도 / 30도   전부 0.0 mm2
측면 0도                   0.0 mm2
앞 0도 / 반대쪽 0도         3.9 mm2
```

남은 3.9 mm² 는 **V3 와 동일값**이고 1×3 / 0×3 / 1×1 mm 짜리다.
px 1400 에서는 5.2 mm² 였다 — **해상도에 따라 변하므로 실루엣 래스터 아티팩트**다.
실제 관통이면 해상도와 무관하게 같은 면적이 나온다. 덱 개구부는 의도된 개구부라
결함으로 세지 않는다.

## 11. §10 STL 제조 acceptance — PASS

```
삼각형              25,044
edges               37,566
boundary edges           0
non-manifold edges       0
degenerate triangles     0
watertight            True
단위                    mm
```

tolerance 는 V3 에서 watertight 가 검증된 값(0.030 / ang 0.15)을 그대로 썼다.

## 12. 산출물

```
export/step/ERGO_HOUSING_25_WRAP_FINAL_V4.step        5.58 MB   설계 마스터
export/brep/ERGO_HOUSING_25_WRAP_FINAL_V4.brep        4.42 MB
export/stl/ERGO_HOUSING_25_WRAP_FINAL_V4.stl          1.19 MB   제조용
export/step/ONEGRIP_25_WRAP_FINAL_V4_PREVIEW.step    33.30 MB   부품 분리 유지
export/stl/BOTTOM_CARRIER_FINAL.stl                   1.12 MB   동결, 무변경

export/step/MOTION15_REMOVED.step                     2.95 MB   절삭 체적 (검증/시각화용)
export/stl/MOTION15_REMOVED.stl

preview/V4_{SIDE,ISOMETRIC,TOP,FRONT_ARMSIDE,REAR,BOTTOM,CUTAWAY}.png
preview/V3_V4_CAVITY_COMPARE.png
reports/12_v4_audit.json  /  12_motion15_accept.json  /  13_25wrap_final_v4.json
```

V3·V2·V1 및 이전 산출물은 전부 보존.

## 13. 검사 코드 수정 (§1)

**(1) 게이트 부울 방향**

`housing - ns` 를 썼는데 OCC 가 코어 전체(495,649)를 그대로 돌려줬다 — 작고 단순한
solid 에서 크고 복잡한 solid 를 빼면 원본이 나오는 함정이고, 그 주석이 바로 위에
있었는데 그대로 밟았다. 교집합만으로 판정하게 바꿨다.

```
removed ⊆ m15  ⟺  vol(housing∩m15) − vol(ns∩housing∩m15) == hv − iv
```

**(2) flood fill 메모리**

`(y,x)` 튜플 스택이 1.4 M 셀에서 `MemoryError`. `y*W+x` 정수 인코딩 + numpy bool
배열로 교체하고 px 1400 → 800 (0.45 mm/px).

**Sanity check:** 수정한 검사기로 V3 재실행 → **PASS 23 / FAIL 0**, 수치가 이전
V3 실행과 소수점까지 동일 (992,760.8691 / 55.8785 / 161.0208 / 0.0000).
CAD 는 건드리지 않았다.

**(3) §6 판정 기준** — 원시 카운트는 접선선을 세므로 부적절. 군집 성격
(면적형 = 리브)으로 교체.

**(4) §6 접선 스침 필터 / 영역 조건** — `덱 0.029 mm @ Z −61.89` 는 동일평면 스침,
`left cavity @ Y −260` 은 팔받침 램프였다. `|n·d| ≥ 0.35` 필터와 X/Y/Z 전부 건
영역 조건으로 교정.

## 14. 작업 함정 (기록)

1. **`radial_poly` 부호 오류** — 광선-변 교차에서 `u` 부호를 뒤집어 자기교차
   다각형이 나왔고 OCC 가 `TopoDS::Face` 타입 오류를 냈다. 올바른 식은
   `t = cross(w,e)/cross(d,e)`, `u = cross(w,d)/cross(d,e)`. 자기검증 추가.
2. **빌드 실패인데 finalize 가 이어 돌아 낡은 STEP 을 V4 로 내보냈다.**
   로그가 아니라 산출물로 확인해야 한다는 기존 교훈을 재발. 이후 빌드 성공을
   확인한 뒤에만 finalize 하도록 분리.
3. **heredoc 안 `\n` 이스케이프가 3회 깨졌다** — 패치 스크립트가 조용히 실패하고
   낡은 파일로 검증이 돌았다. 스크립트는 Write 로 통째로 재작성할 것.
4. **`hull`/`grow` 를 블록 치환으로 지웠다** — 함수 사이 구간을 통째로 바꿀 때
   그 안의 다른 정의가 같이 사라진다.

## 15. 미착수 (지시대로)

deck opening (92.9 × 89.8 유지) / 외부 형상 / M3 나사 / 전장 / 배터리 / 버튼 /
상부 손가락 형상.
