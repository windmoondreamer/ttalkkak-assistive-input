# INDEX retainer fastening — EAR_A′ / EAR_B′ 구현 및 검증

- 일자 2026-08-19
- 승인 근거: docs/22 승인 + "EAR_A′/EAR_B′ fastening 구현" 지시
- 체크포인트: **`INDEX_RETAINER_CORE_FINAL`** (`744823195f26fedf7493f9ad`) — 착수 전 생성
- **결과: §15 조건 13개 중 12개 PASS, 1개 경미한 변화(I3 슬롯 −5 %). fastening 성립.**

---

## A. EAR_A′ geometry

```
앵커        (-14.11, -4.03, +11.24)
나사축      w = (-0.4734, -0.8350, -0.2805)
            체결하면 retainer 가 +w 로 당겨져 pad 가 스위치를 누른다
ear         ⌀7.0 원통, s ∈ [-2.5, +1.5]   (s = 앵커 기준 w 축 좌표)
관통공      ⌀2.4 (나사 ⌀2.0 + 여유 0.2), 카운터보어 없음
쉘 체결부   기존 JfD 벽 s ∈ [+2.8, +9.0] = 6.2 mm  ->  별도 boss 불필요
Feature     RET_ear_A (FQSx3oD6ZecTV7s_16) / RET_hole_A (Ff601HMuj4yhVGR_16)
```

## B. EAR_B′ geometry

```
앵커        (-4.52, -15.38, +1.97)
ear         ⌀7.0 원통, s ∈ [-6.0, -0.5]
관통공      ⌀2.4, 카운터보어 없음
쉘 boss     ⌀5.0, s ∈ [+0.5, +5.2]  (JfD 에 ADD UNION)
쉘 체결부   boss 4.7 mm + 기존 벽 3.4 mm = 8.1 mm
Feature     RET_ear_B (FrHG13cj6iqklLy_16) / RET_shell_boss_B (FQXvBEg2CkYE2l0_16)
            RET_hole_B (FgWEnKBo4zfXj6w_16)
```

### 치수 근거 (0.1 mm 해상도 실측)

| | 반경 3.5 가능 구간 | 앵커 축상 재료 구간 |
|---|---|---|
| EAR_A′ | s ≤ **+1.75** | retainer [0, +1.8] / 틈 [+1.8, +2.8] / 쉘 [+2.8, +9.0] |
| EAR_B′ | s ≤ **−0.5** | retainer [−3.4, 0] / 틈 [0, +5.1] / 쉘 [+5.1, +8.5] |

## C. ear minimum neck — **PASS**

| 연결 | 두께 |
|---|---|
| **EAR_A′ ↔ RWID** | **2.38 mm** |
| **EAR_B′ ↔ RWID** | **1.97 mm** |
| I1-I2 | 1.96 mm |
| I2-I3 | 1.96 mm |
| I1-I3 | 1.97 mm |
| **최소** | **1.96 mm** (요구 ≥ 1.80) |

> **중간 결함 1 — 카운터보어가 벽을 없앴다.**
> ⌀5.0 ear 에 ⌀3.8 머리 자리를 파니 벽이 0.6 mm 만 남아 neck 이 **0.19 mm** 로 떨어졌다.
> → **카운터보어 폐기** (나사 머리는 ear 의 −w 면에 그대로 앉는다. 그쪽은 열린 공간),
>   그리고 실측 프로파일을 근거로 **OD 5.0 → 7.0** → 벽 (7.0−2.4)/2 = **2.3 mm**.

## D. boss A / B

| | 결정 |
|---|---|
| **boss A** | **불필요** — EAR_A′ 위치의 기존 JfD 벽이 **6.2 mm** 로 충분 |
| **boss B** | **필요** — 기존 벽 3.4 mm 뿐 → ⌀5.0 boss (s ∈ [+0.5, +5.2]) 를 JfD 에 union |

`qUnion([JfD_target_first, boss_second])` 로 추가해 **partId 를 보존**했다.
JaD 에는 fastening geometry 를 추가하지 않았다. 기존 `Screw_holes` 무수정.

## E. provisional screw parameters — **전부 PROVISIONAL**

```
#finger_retainer_screw_diameter   = 2.0 mm    (M2 급 가정)
#finger_retainer_screw_clearance  = 0.2 mm    -> 관통공 ⌀2.4
#finger_retainer_boss_od          = 5.0 mm
#finger_retainer_head_diameter    = 3.8 mm    (엔벌로프 계산용. 카운터보어는 파지 않음)
#finger_retainer_head_height      = 1.6 mm    (동일)
pilot (셀프탭 하공)                = 1.7 mm
```

**실제 SKU 미확정.** 기존 쉘 `Screw_holes` 규격을 복사한 값이 아니며,
SKU 확정 시 위 값만 갱신하면 된다.

## F. driver access — **PASS**

나사축(w)을 따라 −w 쪽에서 ⌀3.0 드라이버가 들어오는 경로를 검사했다
(JaD 는 분해 상태, X ≥ 0 은 열린 공간).

| | 무간섭 길이 |
|---|---|
| **EAR_A′** | **21.3 mm** (이후 반대편 JfD 벽) |
| **EAR_B′** | **X = 0 까지 완전 개방** |

> **중간 결함 2 — ear 가 주변보다 낮으면 공구가 닿지 않는다.**
> EAR_B′ 를 s ∈ [−3.4, −0.5] 로 만들었더니 주변 retainer 본체가 s = −3.7 까지 있어
> **드라이버가 0.3 mm 만에 막혔다.** ear 를 **s ∈ [−6.0, −0.5]** 로 더 돌출시켜 해결.

## G. screw B clearance — **PASS**

fastening geometry(t = 0) 와 나사 B 보스(r 3.5, X ∈ [−21.74, 0]) 간섭 **0**.
EAR_A′ 는 나사 B 에서 12.26 mm, EAR_B′ 는 17.62 mm.

## H. wiring access

| | fastening 전 | 후 | |
|---|---|---|---|
| I1 pad 접촉면 | 182/225 | **182** | 무변화 |
| I2 pad 접촉면 | 194/225 | **194** | 무변화 |
| I3 pad 접촉면 | 183/225 | **183** | 무변화 |
| I1 슬롯 (−v) | 180/180 | **180** | 무변화 |
| I2 슬롯 (+v) | 180/180 | **180** | 무변화 |
| **I3 슬롯 (−v)** | 180/180 | **171** | **−9 (−5 %)** |

**I3 슬롯만 5 % 줄었다.** EAR_B′ 가 I3 의 −v 방향 8 mm 지점이라 슬롯 영역과 일부 겹친다.
개구의 **95 % 가 유지**되어 배선·납땜 경로는 성립하나 기록해 둔다.

## I. fastening 후 service travel — **2.09 mm (PASS)**

| | 값 |
|---|---|
| **무충돌 인출** | **2.09 mm** |
| 요구 (d_service) | 2.07 mm → **여유 +0.02 mm** |
| 2.07 이전 차단 복셀 | **0 / 17,102** |
| core baseline (fastening 전) | 2.24 mm |

> **중간 결함 3 — 0 clearance 로는 미끄러지지 못한다.**
> `SHELLCUT` 이 쉘을 여유 0 으로 빼고 있어 retainer 표면이 쉘과 정확히 접해 있었고,
> 그 탓에 travel 이 **1.83 mm** 로 떨어졌다 (표면 0.15 mm inset 만 줘도 2.55 로 회복되는 것으로 확인).
> → `SHELLCUT` 의 쉘 복사본을 **삽입방향 w 로 2.07 mm sweep** 해서 빼도록 수정.
>   제거량은 0.2 mm³ 뿐이지만 걸리던 얇은 살만 정확히 제거되어 travel 이 회복됐다.

**여유 0.02 mm 는 매우 얇다. 주시 항목이다.**

## J. final RWID minimum web — **1.96 mm** (요구 ≥ 1.80) **PASS**

## K. JfD identity — **PASS**

```
Joystick_1 = JaD (1 body)      Joystick_2 = JfD (1 body)
body split 0                   duplicate JfD 0
retainer = RWID 단일, 2136.4 mm³
solid 총 19
```

## L. assembly / regeneration — **PASS**

```
feature 174    OK 174 / ERROR 0 / WARNING 0 / INFO 4(원본)
isComplete true
assembly 25 / 25,  JaD·JfD 참조 정상
```

fastening 피처 5개 전부 `OK`:
`RET_ear_A` `RET_ear_B` `RET_shell_boss_B` `RET_hole_A` `RET_hole_B`

## §12 load path — 확인

```
screw head -> EAR (2.38 / 1.97) -> RWID backbone (1.96~1.97)
          -> PAD_I1/I2/I3 -> switch rear -> front lip
```

0.80 mm 포켓 칸막이는 **쉘(홀더) 쪽 구조**이며 retainer 하중 경로에 포함되지 않는다.
lateral locating 역할만 한다 (§12 준수).

## M. fastening PASS / HOLD — **PASS**

| # | 조건 | 결과 |
|---|---|---|
| 1 | EAR_A′ connected | **PASS** (2.38 mm) |
| 2 | EAR_B′ connected | **PASS** (1.97 mm) |
| 3 | RWID 최소 두께 ≥ 1.80 | **PASS** (1.96) |
| 4 | boss A/B valid | **PASS** (A 불필요, B ⌀5.0) |
| 5 | screw access valid | **PASS** (21.3 mm / 완전 개방) |
| 6 | pocket/switch 간섭 0 | **PASS** |
| 7 | screw B 간섭 0 | **PASS** |
| 8 | wiring access 유지 | **부분** — I3 슬롯 95 % 유지 |
| 9 | service travel ≥ 2.07 | **PASS** (2.09, 여유 0.02) |
| 10 | RWID single body | **PASS** |
| 11 | JfD identity 유지 | **PASS** |
| 12 | ERROR 0 | **PASS** |
| 13 | assembly 정상 | **PASS** (25/25) |

## N. I4 retainer — **미착수**

§16 은 fastening PASS 후 I4 설계를 지시한다. 이번 실행에서는 fastening 검증까지
수행했고 I4 는 만들지 않았다.

## O. INDEX FINAL SUCCESS — **HOLD** (I4 미구현)

## P. `INDEX_FINAL_VALIDATED` 생성 — **아직 생성하지 않았다** (§18 조건 미충족)

---

## 주시 항목

1. **service travel 여유 0.02 mm** — I4 나 이후 어떤 변경도 이 값을 반드시 재확인해야 한다
2. **I3 배선 슬롯 5 % 감소** — EAR_B′ 근접 때문. 실물 배선 시 확인
3. 나사 규격 전부 **PROVISIONAL** — SKU 확정 시 파라미터만 갱신

## 이번 단계의 교훈

1. **작은 boss 에 카운터보어를 파면 벽이 사라진다.** ⌀5 ear + ⌀3.8 머리자리 = 벽 0.6 mm.
   내부 부품은 나사 머리를 노출시키는 편이 낫다
2. **0 clearance 로 쉘을 빼면 부품이 미끄러지지 못한다.** 정적 간섭이 0 이어도
   접선 방향 이동이 즉시 막힌다. **이동 방향으로 sweep 해서** 빼야 한다
3. **드라이버 접근은 나사가 들어가는 것과 별개 조건이다.** ear 가 주변 재료보다
   솟아 있지 않으면 공구가 닿지 않는다
4. POST 응답의 `featureState` 는 재생성 완료 전 값이라 `ERROR` 로 보일 수 있다.
   반드시 `/features` 재조회로 확인할 것 (이번에도 5회 전부 실제로는 OK 였다)
