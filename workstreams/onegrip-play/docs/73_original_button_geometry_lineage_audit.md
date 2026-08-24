# 73 — Original button geometry lineage audit

## 0. Status

**READ ONLY.** Production geometry 수정 0건. Fixture 재생성 0건. Onshape API 0건.
측정은 전부 동결 source (`cad_dump/mesh_*.json`, `build123d_workbench/out/**`) 에서 했다.

## 1. 결론 (verdict)

**DOCS/72 SZH FIT FIXTURE = REUSABLE WITH CAP-SIDE CHANGES ONLY**

단, 이 판정에는 **경계조건**이 있다. 아래 §7 의 두 갈래 중 어느 쪽을 택하느냐로 갈린다.

| cap 결정 | switch pose | docs/72 fixture |
|---|---|---|
| **A. 현재 외형 유지 + actuator socket** (권장) | **무변화** (`front_depth 4.80`) | **그대로 사용 가능, 수정 0건** |
| B. 원본 solid block 을 **무수정** 채용 | **1.382 ~ 1.578 mm 더 깊어짐** | **N1/N2 region 재생성 필요** |

**전제 검증 결과: "N1/N2 carrier 와 switch pose 가 custom cap 을 기준으로 설계됐다" 는
근거가 없다.** switch pose 는 shell 이 결정하고 cap 은 그 결과를 받아 만들어지는 **말단(leaf)**
이다 (§5). 그리고 **docs/72 fixture 안에는 cap geometry 가 아예 없다** (§6).

## 2. Q1 — 원본 open-source button exact part

`cad_dump/` 에 원본 mesh 가 전부 있다. 캡 4형상 × 2 mirror = 8개, 스위치 1종.

| part | partId | tris | 실측 |
|---|---|---:|---|
| `Button_corner_1` / `_2` | RAEL / RBED | 138 / 136 | **7.597 × 7.597** mm, 두께 **4.866** |
| `Button_middle_1` / `_2` | RDED / RDEH | 12 / 12 | **7.600 × 7.600** mm, 두께 **4.762** |
| `Button_side_1` / `_2` | RAEH / RBEH | 38 / 38 | **7.600 × 7.600** mm, 두께 **4.938** |
| `Button_wide_1` / `_2` | RAED / RBEL | 26 / 26 | **9.600 × 6.600** mm, 두께 **4.742** |
| `PushBtn` (원본 스위치) | — | 3530 | bbox **7.566 × 8.519 × 6.010** mm |

**원본 캡은 socket 도 boss 도 없는 solid block 이다.** `Button_middle_1` 은 삼각형이 **12개**
(= 6면 × 2) 뿐이고 mesh 부피 **275.054 mm³** 가 `7.6 × 7.6 × 4.762 = 275.05` 와 정확히 같다.
즉 fill = **1.000**, 내부 공동 0.

> 측정 함정: PCA 로 OBB 를 잡으면 정사각 판이 **45° 대각으로 정렬**돼 `10.748 × 10.748`
> (= 7.6√2) 이 나오고 fill 이 0.50 으로 보인다. 지배 평면 법선을 축으로 써야 한다.

**원본 8버튼은 엄지 클러스터다.** 원본 캡 도심에서 가장 가까운 손가락 버튼까지
**38.10 ~ 49.08 mm** 다. 즉 **원본에 대응하는 N1/N2 버튼은 존재하지 않는다.**
N1/N2 를 포함한 손가락 8버튼은 전부 신규 추가분이다 (CLAUDE.md §2.2 와 일치).

## 3. Q2 — 현재 N1/N2 cap 은 original / modified / custom 중 무엇인가

**답: 외부는 ORIGINAL 정합, 내부는 CUSTOM.** 한 단어로는 **MODIFIED**.

| 항목 | 원본 | 현재 | 판정 |
|---|---|---|---|
| 캡 판 크기 | **7.600 × 7.600** mm (실측) | `CAP_SIZE = 7.60` | **일치** |
| 쉘 개구부 | `#button_width` **8.00** mm | `OPENING_SIZE = 8.00` | **일치** |
| 캡 클리어런스 | 사방 0.20 mm | (8.00−7.60)/2 = 0.20 | **일치** |
| 캡 내부 | **없음 (solid block)** | boss ⌀4.50 + socket ⌀3.45 | **CUSTOM** |
| 캡 축방향 총 길이 | 4.742 ~ 4.938 mm | **4.71** mm (`u −1.00 → +3.71`) | 근사 일치 |
| 노출량 | (미분리) | `CAP_EXPOSURE = 1.00` | 신규 정의 |
| 대상 스위치 | `PushBtn` 7.57×8.52×6.01 | ITS-1105 6.18×6.12×3.56 | **다른 부품** |

즉 현재 cap 은 **원본 외형 규격(7.60 판 / 8.00 개구부 / 0.20 클리어런스)을 정확히 지키면서
그 안에 ITS-1105 용 socket 기구를 새로 넣은 것**이다. 외형 규격은 custom 이 아니다.

## 4. Q3 — 원본 button 을 승인 external center/axis 에 놓으면 switch pose 가 같은가

**축과 중심: 같다.** 승인 external center/axis 는 cap 과 무관한 입력이다.

**깊이: cap 을 어떻게 쓰느냐에 달렸다.**

- **원본 cap 을 modified 로 (socket 추가해서) 쓰면 — 동일하다.** `front_depth = 4.80` 불변.
- **원본 solid block 을 무수정으로 쓰면 — 동일하지 않다.** block 에 socket 이 없으므로
  ITS actuator 상면이 block 뒷면에 그대로 눌린다. block 뒷면 `u = −1.00 + t` 이고
  actuator 상면은 `u = front_depth − 2.44` 이므로 `front_depth = t + 1.44`:

| 원본 캡 | t | 필요 front_depth | 현재 4.80 대비 |
|---|---:|---:|---:|
| wide | 4.742 | 6.182 | **+1.382 mm** |
| middle | 4.762 | 6.202 | **+1.402 mm** |
| corner | 4.866 | 6.306 | **+1.506 mm** |
| side | 4.938 | 6.378 | **+1.578 mm** |

현재 형상에서 원본 block 을 그대로 얹으면 actuator 상면(`u = +2.36`)을
**1.382 ~ 1.578 mm 관통**한다.

## 5. Switch-pose dependency chain (핵심)

`build123d_workbench/finger_controls_v2.py` 정적 추적 결과:

```
front_depth  <- choose_front_depths(carrier vs clean shell, ITS body vs clean shell)
switch pose  <- (approved centre, approved axis, front_depth)
terminals    <- terminal_root_cutters(datum, front_depth)
carrier      <- build_individual_carrier(datum, front_depth)
opening      <- opening_cutter(datum)            # 8.00 / N2 seam 8.40, front_depth 무관
cap          <- build_cap(datum, front_depth)    # LEAF
```

- `choose_front_depths()` 의 수락 조건은 **carrier↔shell 간섭 + ITS body↔shell 간섭 +
  최소이격 0.20 mm** 뿐이다. **인자에 cap 이 없다.**
- `caps = {...}` 는 `build_finger_controls_v2()` 에서 **맨 마지막에** 계산되어 결과
  dataclass 에 담길 뿐, 어떤 boolean 에도 다시 들어가지 않는다.
- `build_cap()` 은 오히려 `front_depth` 를 읽어 `boss_rear = min(front−0.45,
  front−ACTUATOR_PROJECTION+1.35)` 로 자기 형상을 맞춘다. **방향은 switch → cap 이다.**

**따라서 "switch pose 가 custom cap 기준으로 설계됐다" 는 전제는 성립하지 않는다.**

### 5.1 부수 발견 — depth search seed 가 탐색범위를 자르고 있다 (cap 무관)

`CARRIER_FRONT_SEED = 4.40` 은 **문서화된 유도가 없는 상수**이고 cap 산술
(`1.00+1.20+2.44 = 4.64`, `2.44+0.20 = 2.64`) 중 어느 것과도 맞지 않는다. cap 유래가 아니다.

같은 수락 조건으로 seed 아래까지 직접 돌려 보면:

| front_depth | N1 | N2 |
|---:|---|---|
| 3.40 | 간섭 0.5954 mm³ | 이격 0.1338 (부족) |
| 3.60 | 간섭 0.0471 mm³ | **FEASIBLE** 0.3336 |
| 3.80 | 이격 0.0571 (부족) | FEASIBLE 0.5334 |
| **4.00** | **FEASIBLE** 0.2517 | FEASIBLE 0.7332 |
| 4.40 (seed) | FEASIBLE 0.6403 | FEASIBLE 1.1329 |
| 4.80 (frozen) | FEASIBLE 1.0283 | FEASIBLE 1.5325 |

개별 기준으로는 N1 이 **4.00**, N2 가 **3.60** 부터 가능하다. 최종 4.80 은 seed 가 아니라
**N1/N2 공용 bridge 루프**(융합 carrier 가 shell 을 못 벗어나면 둘을 함께 0.20 씩 밀어냄)가
4.40 에서 2스텝 밀어낸 결과다. seed 를 낮추면 시작점이 (4.00, 3.60) 이 되어 최종값이
달라질 수 있다.

**이건 cap lineage 문제가 아니라 별개의 최적성 문제다.** 다만 SZH 방향으로 1.2 mm 이상
여유를 만들 수 있는 자리이므로 docs/71 충돌 해소 때 재검토 대상으로 기록해 둔다.

## 6. Q5 / Q4 — carrier rear 와 terminal 은 재사용 가능한가

**Q4 terminal global position: 동일하다.** `terminal_root_cutters(datum, front_depth)` 는
datum 과 front_depth 만 받는다. 둘 다 안 바뀌면(§7 갈래 A) terminal 위치도 안 바뀐다.

**Q5 carrier 의 SZH-facing rear geometry: 그대로 재사용 가능하다.**

```
carrier rear u = front_depth + SWITCH_BODY_H + CARRIER_REAR_PLATE
              = 4.80 + 3.56 + 1.60 = 9.96 mm
```

입력은 승인 center / 승인 axis / ITS body 높이 / carrier rear plate 네 개뿐이고
**cap 항이 없다.**

### 6.1 docs/72 fixture 가 실제로 담고 있는 것

STEP label 40개 전수 조사: **`CAP` 를 포함하는 solid 0개.**

| fixture 내용물 | cap 의존성 |
|---|---|
| `JAD_CURRENT_SHELL_LOCAL_FIT_SECTION` | 개구부 8.00 = 원본 `#button_width` → 없음 |
| `JFD_CURRENT_SHELL_LOCAL_FIT_SECTION` | 동일 → 없음 |
| `LOWERED_THUMB_BACKPLATE_LOCAL_MOUNT_REFERENCE` | 없음 |
| `N1_N2_APPROVED_CARRIER_EXACT_COPY` (379.533822 mm³) | 없음 (§6) |
| 희생형 frame / support / label | 없음 |

**fixture 는 cap 을 한 조각도 인쇄하지 않는다.** 그래서 cap 계보 문제가 fixture 로
전파되는 경로는 **switch pose 를 통한 간접 경로 하나뿐**이고, 그 경로는 갈래 A 에서 닫힌다.

## 7. 두 갈래와 권고

### 갈래 A — 현재 외형 유지 + actuator socket (권고)

원본 외형 규격(7.60 판 / 8.00 개구부 / 0.20 클리어런스)은 **이미 정확히 지켜지고 있다**.
남는 것은 "원본은 solid block, 현재는 socket 이 있다" 뿐인데, **ITS-1105 를 쓰는 한
socket 은 선택이 아니라 필수**다 (없으면 §4 대로 1.4~1.6 mm 관통).

→ `front_depth 4.80` / terminal / carrier rear 9.96 **전부 불변**
→ **docs/72 fixture 수정 0건, 그대로 인쇄·시험 가능**

### 갈래 B — 원본 solid block 무수정 채용

→ switch 가 **1.382 ~ 1.578 mm 더 깊어진다**
→ carrier rear 가 9.96 → **11.342 ~ 11.538 mm** 로 SZH 공간을 더 침범한다
→ **이건 docs/71 이 조사 중인 `PCB ↔ N1/N2` 충돌을 정확히 그만큼 악화시킨다**
→ docs/72 fixture 의 N1/N2 region **재생성 필요**

**권고: 갈래 A.** 갈래 B 는 원본 충실도를 얻는 대신 이미 tight 한 SZH 충돌을 1.4 mm 이상
키우고, 그 대가로 얻는 것은 socket 없는 블록뿐이다.

## 8. 미해결 / 주시

- **CLAUDE.md §3 의 "버튼 스위치: 원본 `PushBtn` 유지 vs 교체" 는 아직 공식적으로 닫히지
  않았다.** 실작업은 ITS-1105 로 진행돼 왔고 물리 샘플 감사도 여러 건 있다
  (`cad_dump/its1105_*.json`). 이 항목을 정식으로 닫는 결정이 필요하다.
  **PushBtn 으로 되돌리는 선택은 이 audit 의 범위 밖이며, 그 경우 8버튼 전체
  재유도가 된다** (PushBtn 8.519 mm vs ITS 3.56 mm).
- `CARRIER_FRONT_SEED = 4.40` 의 유도 근거 부재 (§5.1).
- `N2_SEAM_OPENING_SIZE = 8.40` 은 분할면 여유값이며 cap 유래가 아니다. 다만 원본 7.60 캡
  기준으로는 사방 0.40 이 되어 개구부 대비 캡 여유가 N1 보다 크다.
- 이 audit 은 **N1/N2 만** 다뤘다. I2/I3/I4/M3/M4/N3 의 cap 계보는 같은 상수를 공유하므로
  같은 결론이 예상되지만 **개별 검증은 하지 않았다.**

## 9. Stop

원본 button lineage 와 switch-pose dependency 만 감사했다.
**N1/N2 / Thumb / shell / cap / fixture 수정 0건.** 다음 단계는 §7 갈래 선택 승인이다.
