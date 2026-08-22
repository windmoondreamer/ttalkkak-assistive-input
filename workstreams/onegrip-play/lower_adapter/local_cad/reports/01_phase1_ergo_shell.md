# Phase 1 — build123d 로컬 W2 인체공학 외피

**결과: PHASE 1 COMPLETE — 검증 22 PASS / 0 FAIL.**
**Onshape API 호출 0건** (읽기·쓰기 모두). 이 단계의 모든 형상은 로컬 STEP + build123d 로만 만들었다.

| 항목 | 값 |
|---|---|
| 엔진 | build123d 0.11.1 / cadquery-ocp-novtk 7.9.3.1.1 (OpenCascade) |
| 산출 solid | `ERGO_HOUSING_W2` 단일 solid, shells 1 / faces 539 |
| BRepCheck | valid |
| 검증 | 22 PASS / 0 FAIL |

---

## 1. 하드 룰 준수

| 룰 | 상태 | 근거 |
|---|---|---|
| `ONSHAPE_API = FORBIDDEN` | 준수 | 이 단계 코드에 Onshape 클라이언트 import 없음. 네트워크 호출 0 |
| `ONSHAPE_WRITE = FORBIDDEN` | 준수 | 동일 |
| `LOCAL_CAD_ENGINE = build123d` | 준수 | CadQuery 미사용 |
| `CUSTOM_GIMBAL = FORBIDDEN` | 준수 | 짐벌 형상 생성 0 |
| `STOCK_GIMBAL = IMMUTABLE` | 준수 | STEP 부피 228,346.2159 mm³ 무변경 확인 |
| `BOTTOM_CARRIER = IMMUTABLE` | 준수 | 부피 90,177.998830 mm³ 무변경 확인, 새 하우징과 간섭 0 |
| `APPROXIMATE_CORE_REBUILD = FORBIDDEN` | 준수 | 코어는 STEP solid 를 **그대로 union** 했다. 재작성 0 |
| `MESH_TO_CAD_RECONSTRUCTION = FORBIDDEN` | 준수 | 메시는 점-내부 판정(교차검사)에만 사용. 형상 생성에 미사용 |

---

## 2. STEP 임포트 / 라운드트립 (§2)

허용치 bbox ≤ 1e-6 mm, 상대부피 ≤ 1e-6. **3/3 통과.**

| 레퍼런스 | solid | bbox 오차 [mm] | 상대부피 오차 |
|---|---|---|---|
| `STOCK_GIMBAL_REFERENCE.step` | 7 | 6.59e-12 | 1.53e-09 |
| `CONFORMAL_CORE_REFERENCE.step` | 2 | 2.00e-11 | 5.76e-15 |
| `ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step` | 172 | 통과 | 통과 |

## 3. 좌표계 정합 (§3)

손으로 넣은 근사 변환은 없다. 전부 형상에서 유도했다.

- 코어 STEP 이 이미 grip frame 임을 확인 (덱 평면 Z 오차 **7.0e-06 mm**)
- 캐리어 포켓 실측으로 앵커: Z −149.956514, 면적 9408.81 mm², 측당 여유 **0.300 mm**
- assembly ↔ grip 은 **Base solid 하나를 다리로** 삼아 Kabsch 정합 + 축정렬 24회전 탐색.
  정점 최대 편차 **4.32e-14 mm**, `rz = 180.0°`
- **함정:** Part Studio 의 부품 위치는 *layout* 위치라 조립 위치가 아니다.
  `Roll_holder`/`Roll_holder_2`/`Spacer` 가 t=(0.076, −34.826, 35.100) 로 완전히 같고
  `Base` 만 (0.222, −34.539, 28.100) 으로 정확히 7.007 mm(= Spacer 두께) 차이가 난다.
  그래서 어셈블리를 진리로 두고 Base solid 하나만 다리로 썼다.

## 4. 전략 선택 (§6)

| 안 | 내용 | 판정 |
|---|---|---|
| A | 코어 외피를 offset/thicken | **기각** — offset 이 코어 위상을 재작성한다. `APPROXIMATE_CORE_REBUILD` 위반 소지 |
| **B** | `NEW = HOUSING ∪ (SMOOTH_ENVELOPE − CAVITY_PROTECT − CARRIER_SWEEP)` | **채택** — 코어 solid 를 원본 그대로 union 하므로 코어가 비트 단위로 보존된다 |
| C | 별도 커버를 나사로 체결 | 보류 — 부품 수·조립 공정이 늘고 W2 의 연속 외피 요구와 어긋난다 |

## 5. 빌드 파이프라인

```
housing_profile()      HOUSING 을 Z 26 스테이션으로 단면 실측 (loft 가 덮어야 할 최소 경계)
  -> bound 단조 스무딩 (아래 단면이 위쪽 전부를 덮는다) + MARG 2.5
body / body_in         Z 스택 ruled loft (바깥 / 안쪽=SHELL_WALL 5.0 균일 인셋)
wrist / wrist_in       Y 스택 스플라인 loft 5 섹션
                       front lip / early / mid / palm heel / transition, wfrac [0.72,0.86,1,1,1]
env = body ∪ wrist  ->  지면평면 / 덱평면 / 패드평면 절단
shell = env − env_in
keep  = shell − CAVITY_PROTECT − CARRIER_SWEEP
NEW   = keep ∪ HOUSING  -> heal -> 필렛 -> keep-out 재적용 -> heal
```

## 6. 이번에 잡은 결함 6건 (전부 실측으로 특정)

1. **단조 스무딩이 중심을 무시했다.** 크기만 `max` 하고 단면 중심을 그대로 둬서
   +Y 가 22 mm 부풀었다 (Y_max 93.98 → 115.98). **경계값(bound) 기준으로 max/min** 하도록 수정.
2. **`Plane(origin, z_dir=(0,1,0))` 의 자동 축.** build123d 가 `x_dir` 을 (0,0,1) 로 잡아
   local x→world Z, local y→world X 가 된다. 그대로 쓰니 손목 단면 5개가 90° 돌아간 채
   X≈−118 로 날아갔고 평면 절단에 통째로 잘렸다 — **손목이 모델에 아예 없었다.**
   축을 못박는 `yz_plane()` 헬퍼로 교체. 이것이 손목 면적 784 → 4,834 mm² 의 원인이다.
3. **스플라인 loft 의 overshoot.** 스테이션 13→14 에서 깊이가 5 mm Z 구간 동안 160→113 mm 로
   급변한다(덱 개구부). 스플라인이 여기서 넘쳐 바깥/안쪽 곡면이 교차하고 `body − body_in` 에
   invalid face 가 생겼다. **본체만 `ruled=True`** 로 바꿔 해소 — 선형 보간은 균일 인셋을
   정확히 보존하므로 벽이 음수가 될 수 없다. 손목 loft 는 사용자 접촉면이라 스플라인 유지.
4. **불필요한 `− HOUSING` 이 두께 0 접합을 만들었다.** `(E−H−C) ∪ H ≡ (E−C) ∪ H` 인데
   앞 형태를 쓰는 바람에 98.41 × 1.67 × **0.25 mm** 짜리 내부 공동 shell 이 남았다.
5. **오목 모서리 필렛은 재료를 더한다.** 손목 필렛이 캐리어 인출 경로를 201.5 mm³ 침범했다.
   필렛 뒤 **keep-out 재적용 + 코어 재union** 으로 불변량 복원.
6. **`Compound.moved()` 의 위치는 `.children` 에 반영되지 않는다** (`.solids()` 에는 반영됨).
   프리뷰가 원본 어셈블리 좌표로 나가 하우징과 따로 놀았다. 자식마다 명시적으로 이동.

### OCC 부울 신뢰성 (중요)

- **Compound 를 피연산자로 주면 조용히 빈 결과가 나온다.** 같은 간섭 검사가
  Compound 로 138.277 mm³, Solid 로 0.000 mm³ 였다. 검증기의 모든 부울을 단일 Solid 로 통일했다.
- **`작은 − 큰` 방향은 신뢰할 수 없다.** `HOUSING − NEW` 가 HOUSING 전체를 그대로 돌려줬다.
  포함 판정은 잘 조건화된 `NEW & HOUSING` 으로 한다
  (`NEW − HOUSING = 218,808.2528` 이 `NEW − HOUSING 부피차`와 정확히 일치해 교차검증됨).
- **invalid solid 는 모든 후속 부울을 무효화한다.** 위 4번의 0.25 mm shell 하나 때문에
  `BRepCheck_Analyzer` 가 invalid 를 내고 그 뒤 부울이 전부 빈 결과였다.
  그래서 `geometry_utils.heal()` 을 만들어 **단계마다 유효성을 강제**한다 (실패 시 STOP).

## 7. 필렛 (§13)

`fillet` 은 집합 안에 실패 모서리가 하나라도 있으면 전체가 실패한다. 그룹으로 나누고,
실패하면 반경 강등(3.0 → 2.5 → 2.0), 그래도 실패하면 **모서리 하나씩** 재시도한다.

| 그룹 | 결과 |
|---|---|
| `FRONT_LIP` | R3.0 / R2.5 실패 → **R2.0 · 12 모서리** |
| `WRIST_SIDE` | 그룹 단위 전 반경 실패 → **개별 R2.0 · 32 모서리 성공** |
| `PAD_PERIMETER` | **R3.0 · 4 모서리** |

## 8. 검증 22 PASS / 0 FAIL

**DIRECT BREP** (STEP solid 간 실제 boolean) 과 **CACHED ENVELOPE** (검증된 9자세 포락선 캐시에
대한 점-내부 판정) 를 구분해서 보고한다. 캐시 쪽은 STEP 만으로 관절을 복원한 것이 아니므로
DIRECT 가 아니다.

- 동결 레퍼런스 보존: 스톡 부피 / 캐리어 부피 무변경, **`NEW & HOUSING` = 495,615.4703 vs
  HOUSING 495,615.4704 (차 −6.6e-05 mm³)** → 코어 완전 포함
- 새 하우징 solid **valid** (shells 1 / faces 539)
- 20° 기준면 존재, **기준면 vs 수평 = 20.000000000°**, 그립 중립축 ⟂ 기준면 = 90°
- HAND_REF 변화 **0**
- 하우징 최저 = 지면 평면 −171.3261, **스톡 돌출 0.000000 mm**
- DIRECT: `NEW ∩ BOTTOM_CARRIER` = 0, **캐리어 −Z 인출 0–100 mm 무충돌**
- DIRECT: 새 하우징이 **추가한** 어셈블리 간섭 **0.000000 mm³**
- CACHED: 9자세 전부 `0 / 20,130 점`

## 9. 측정 (§20 / §22) 와 Onshape W2 대조

| 항목 | 로컬 build123d | Onshape W2 (docs/08) | 차 |
|---|---|---|---|
| 폭 W [mm] | 133.600 | 128.6 | +5.0 |
| 길이 L [mm] | 197.243 | 219.7 | −22.5 |
| 높이 (월드) [mm] | 139.857 | 139.9 | −0.04 |
| 손목 각도 [°] | 7.0 | 7.0 | 0 |
| 손목 지지 면적 [mm²] | 4,833.6 | 7,173 | −2,339 |
| 덱 → HAND_REF [mm] | **55.8785** | 55.8785 | **0** |
| 지면 → HAND_REF [mm] | **161.0208** | 161.0208 | **0** |
| 스톡 돌출 [mm] | **0.0000** | 0.0000 | **0** |
| 부피 [mm³] | 715,118 | 634,810 + 캐리어 | — |
| 코어 대비 증분 [mm³] | +219,503 | +139,195 | +80,308 |

**인체공학 불변량 3개(덱→HAND_REF, 지면→HAND_REF, 스톡 돌출)는 Onshape 기준과 정확히 일치한다.**
W/L 과 손목 면적이 다른 것은 로컬 외피가 다른 방식으로 만들어졌기 때문이다:
Onshape 판은 손목 넥을 별도 스테이션 5개로 뽑아 앞으로 길게 뻗었고(L 219.7),
로컬 판은 본체 loft 를 MARG 2.5 로 덮으면서 폭이 커지고(W 133.6) 손목이 짧아졌다.
면적 차이는 **정의 차이도 섞여 있다** — 로컬 측정기는 패드 평면과 법선이 1e-4 이내로
일치하는 **평면 면만** 세는데, 로프트 상면이 곡면이라 곡률 구간이 빠진다.

## 10. 남은 항목

1. **동결 코어가 이미 갖고 있던 간섭 138.2772 mm³** — `Hex_socket_head_cap_screw_M3×16`
   머리 4개. 위치 (44.8, 74.5, −133.5) 42.77 / (−44.2, −21.1, −133.5) 26.68 /
   (44.9, −21.2, −133.5) 22.71 / (−44.0, 74.4, −133.5) 46.12 mm³.
   **W2 가 추가한 몫은 0** 이다. `CONFORMAL_HOUSING` 은 동결 대상이라 이번 범위에서
   수정하지 않았다. 이 나사들은 CLAUDE.md 상 M3×22 로 **교체** 예정이므로,
   교체 시 헤드 좌표가 바뀌면 자연히 해소될 수 있다 — 다음 단계에서 확인 필요.
2. **손목 지지 면적 측정기** — 곡면 상단을 포함하도록 정의를 바꿔야 Onshape 값(7,173)과
   같은 기준으로 비교할 수 있다.
3. **손목 길이 L** — Onshape 판(219.7)과 22.5 mm 차이. 늘릴지 여부는 사용자 결정 사항.
4. `#usb_clearance` 6.0 mm, M3×22, M3 인서트는 여전히 provisional.

## 11. 산출물

```
export/step/ERGO_HOUSING_W2.step            4.9 MB   단일 solid
export/step/ONEGRIP_LOCAL_PREVIEW.step     32.3 MB   부품 분리 유지(fuse 안 함)
export/step/BOTTOM_CARRIER_REFERENCE.step            동결 캐리어 원본
export/stl/ERGO_HOUSING_W2.stl              6.9 MB   138,862 삼각형
export/brep/ERGO_HOUSING_W2.brep           12.5 MB
preview/{ISOMETRIC,SIDE,FRONT,TOP,BOTTOM,CUTAWAY}.png
reports/{01_reference_alignment,02_verify}.json
```
