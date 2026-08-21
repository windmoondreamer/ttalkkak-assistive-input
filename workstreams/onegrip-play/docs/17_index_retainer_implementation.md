# INDEX rear retainer 구현 — stale feature 정리 · HOLDER FINAL PASS · retainer 1차 구현

- 일자 2026-08-19
- 승인 근거: docs/16 §G 원인 분석 승인 + suppress 방식 지시
- 체크포인트 버전: `INDEX_holder_final` (`6f0e56b8f7504503dc2db465`)
- 신규 Feature Studio: `OneGrip_Retainer` (`372973e3f8ac06ede47d95c2`), 소스 `cad/OneGrip_Retainer.fs`

---

## A. stale feature suppress — 완료

```
POST /features/featureid/FkGjuaVRtcptOX1_14   suppressed: true
-> status 200, featureState OK, suppressed True
```

`INDEX_construction` 을 포함해 **다른 피처는 일절 건드리지 않았다.**

## B. regeneration ERROR 0 — PASS

suppression 직후 `/features` 재조회:

| 항목 | 값 |
|---|---|
| isComplete | **true** |
| OK | 162 |
| **ERROR** | **0** |
| **WARNING** | **0** (신규 unexpected 없음) |
| INFO | 4 (원본 `Joystick_part_1~4_plane`, 기존 상태) |
| suppressed | **정확히 1건** — `FkGjuaVRtcptOX1_14` |

## C. suppression 전후 geometry 변화 — 없음

| 항목 | 결과 |
|---|---|
| solid count | **18** (retainer 생성 전) |
| Joystick_1 / Joystick_2 | `JaD` / `JfD`, 각 1 body |
| body split / duplicate | 0 / 0 |
| 예상 외 body | 없음 |
| assembly occurrences / instances | **25 / 25**, dangling 0 |
| 시트 4개 | **전부 축에서 3.200 mm = 6.4 x 6.4** |
| 최소 포켓 칸막이 | **0.8000 mm** (docs/15 와 동일) |
| 나사 B 최소 3D 거리 | **2.990 mm (I4)** (docs/15 와 동일) |
| 구 twist-lock plug body | **0개** |
| I3 / I4 ownership | I3 X ≤ −1.500 / I4 X ≥ +1.999 — 유지 |

**suppression 으로 바뀐 값 0건.**

## D. INDEX F2 HOLDER = **FINAL PASS**

A~C 전부 통과. stale legacy feature 는 지시대로 **suppress 상태로 남겨두었다** (DELETE 하지 않음).

---

## E. retainer fit clearance — **0.25 mm 채택**

복셀 sweep (step 0.6, 실측 쉘 표면거리 기반):

| fit clr | 자유복셀 | pad 3개 연결 | I1-I2 | I2-I3 | I1-I3 | 최소 |
|---|---|---|---|---|---|---|
| 0.20 | 17,057 | 3/3 | 3.853 | 3.853 | 6.224 | 3.853 |
| **0.25** | 16,877 | 3/3 | 3.753 | 3.753 | 6.124 | **3.753** |
| 0.30 | 16,735 | 3/3 | 3.653 | 3.653 | 6.024 | 3.653 |

셋 다 목표 2.0 mm 를 크게 상회하므로, 지시대로 **P1S V1 기본값 0.25 mm** 를 채택했다.

## F. insertion path — **FAIL (미해결, 이번 실행의 차단 항목)**

### 삽입 방향 유도

pad 가 보어에서 빠져나오려면 삽입축이 각 보어축과 이루는 각 θ 가
`tanθ ≤ (보어 6.4 − pad 3.6)/2 ÷ pad 돌출 1.35` → **θ ≤ 46.0°** 여야 한다.

| 후보 | I1 | I2 | I3 | 최대 | 판정 |
|---|---|---|---|---|---|
| 공간 최적 (−0.899, −0.241, +0.365) | 34.2° | 76.8° | 72.3° | 76.8° | **FAIL** |
| **세 축 최소원뿔축 (−0.4734, −0.8350, −0.2805)** | 30.1° | 30.1° | 30.1° | **30.1°** | **PASS** |

→ 삽입축 **w = (−0.4734, −0.8350, −0.2805)** 확정.
(이 값은 §L 의 최적 출력 방향과 동일하다 — 둘 다 세 축의 최소원뿔축이기 때문)

복셀 해석에서는 이 방향으로 홀더·쉘을 모두 통과하는 부분집합이 존재했다
(추출가능 7,024 복셀 = 1,517 mm³).

### 그러나 실제 B-rep 에서는 막힌다

최종 형상을 w 반대로 이동시키며 충돌 검사:

```
t = 1.5 mm 에서 충돌 62 / 5,846 복셀   -> FAIL
막히는 위치: X -19.9~-6.6,  Y = -19.0 (단일 평면),  Z +21.5~+23.6
전부 JfD, 전부 I2 근방
```

**원인:** `SHELLCUT` 을 삽입방향으로 **sweep 하지 않았다.**
쉘 원형을 그대로 빼면 retainer 가 쉘 오목부를 채우게 되고, 그 부분은 직선으로 빠지지 않는다.
막히는 곳은 나사 B 절삭 원기둥(r 4.5) **바로 바깥**의 얇은 플랜지다.

### 시도한 수정과 결과

| 시도 | 결과 |
|---|---|
| 나사 B 절삭 sweep | retainer 가 **3조각으로 분할** → 철회 |
| blank 확대 (15→17, 17.0→19.5) + 쉘 절삭 | web 은 그대로, 인출 여전히 FAIL |
| 나사 B 절삭 r 4.5 → 6.0 | retainer 가 **2조각으로 분할** → 철회 |

**미해결.** §7 지시("직선 삽입 불가면 HOLD")에 따라 여기서 멈춘다.

### 다음에 시도할 것 (계산 근거 있음)

1. **`SHELLCUT` 을 w 로 sweep** 한다. 쉘 전체를 12회 복사하는 것은 무겁지만,
   retainer 주변만 잘라낸 국소 쉘 조각을 sweep 하면 가볍다.
2. 또는 blank 를 처음부터 **추출 가능 영역(E(w))의 근사 다면체**로 정의한다.
   복셀 해석에서 E(w) 는 1,517 mm³ 이고 세 pad 를 연결한다.

## G. final minimum structural web — **1.91 mm** (요구 ≥1.5 PASS, 목표 2.0 미달)

최종 B-rep 복셀(0.5 mm) + 자기 표면까지의 거리로 실측:

| 연결 | 최소 단면 두께 |
|---|---|
| I1-I2 | **2.28 mm** |
| I2-I3 | **1.91 mm** |
| I1-I3 | **1.91 mm** |

> **중간에 발견한 결함:** 처음 측정값은 1.37~1.40 mm 였다.
> 원인은 web 이 아니라 **배선 슬롯**이었다 — 오프셋 5.0 mm / 높이 10.0 mm 로 두어
> 슬롯이 v = 0 까지 뻗어 **pad(3.6, ±1.8) 를 파고들었다.**
> 오프셋 6.0 / 높이 8.0 (v 구간 [2,10]) 으로 고쳐 pad 에서 0.2 mm 이격시키자
> 2.41 mm (확대 blank) / 1.91 mm (현재 blank) 로 회복되었다.
>
> 병목 위치를 실측해 "web 이 아니라 pad 였다"를 특정한 것이 해결의 열쇠였다.

## H. pad geometry / preload

| | 값 |
|---|---|
| 단면 | **3.6 x 3.6 mm** (6.4 보어 안에 사방 1.4 mm 링을 핀·배선용으로 남김) |
| 접촉면 법선 | **각 F2 스위치 축과 정확히 일치** (I1/I2/I3, 변경 없음) |
| 돌출 | 홀더 뒷면(12.5) → 스위치 뒷면(11.3) = 1.2 mm **+ preload** |
| preload | `#finger_retainer_preload` = **0.15 mm** (provisional, 0.10/0.15/0.20 조정 가능) |

실물 확인: 세 버튼 모두 깊이 11.20 / 11.60 / 12.00 / 12.40 에서 9/9 표본이 retainer 재료.

## I. wiring slot

| | 방향 | 단면 | 실측 자유 여유 |
|---|---|---|---|
| I1 | **−v** | 2.5 x 1.5 mm | 22.9 mm |
| I2 | **+v** | 2.5 x 1.5 mm | 23.6 mm |
| I3 | **−v** | 2.5 x 1.5 mm | 12.7 mm |

오프셋 6.0 mm / 높이 8.0 mm → v 구간 [2, 10]. **pad 에서 0.2 mm 이격** (§G 참조).

## J. fastening — **미구현**

승인 anchor(EAR_A: I1 축 −u 8 mm / EAR_B: I3 축 −v 8 mm)는 docs/16 §G 에 확정되어 있으나,
**§7 insertion path 가 FAIL 이므로 ear·나사 구멍을 만들지 않았다.**
기존 `Screw_holes` 는 손대지 않았다.

## K. I4 retainer — **미구현**

같은 이유로 착수하지 않았다. 설계는 docs/16 §H 에 확정되어 있다.

## L. printability

- 최적 베드 법선 **(−0.4734, −0.8350, −0.2805)** 에서 세 pad 면 경사가 모두 **30.08°** → **서포트 불필요**
- 최소 벽: web **1.91 mm** (0.4 노즐 기준 약 5 lines), pad 3.6 x 3.6 — 전부 여유
- retainer 는 **별도 NEW PART** (`RWID`). JaD/JfD 와 union 하지 않았다 (§14 준수)

## M. JaD / JfD / assembly

| 항목 | 결과 |
|---|---|
| solid | **19** (원본 14 + INDEX 캡 4 + retainer 1) |
| `JaD` = Joystick_1 / `JfD` = Joystick_2 | 각 1 body, split 0 |
| retainer ∩ JfD | **0** |
| retainer ∩ JaD | **0** |
| feature 총수 / ERROR / WARNING | **168 / 0 / 0**, isComplete true |
| suppressed | 1 (`FkGjuaVRtcptOX1_14`) |

**SUBTRACT target 은 항상 retainer body 하나뿐이었다.**
쉘은 `opPattern` 복사본으로만 tool 로 썼고 원본은 손상되지 않았다.

## N. INDEX FINAL SUCCESS — **HOLD**

| 조건 | 상태 |
|---|---|
| holder final PASS | **PASS** |
| regeneration ERROR 0 | **PASS** |
| 착좌 / SAT / divider / screw | **PASS** (docs/15, C 항목에서 재확인) |
| shared retainer 장착 가능 | **HOLD — insertion path FAIL** |
| I4 retainer | 미구현 |
| switch removal | insertion 미해결로 미검증 |

## O. MIDDLE — **HOLD**

§13 지시대로 이번 실행에서 만들지 않았다.

---

## 구현 기록 (§12 원자 순서)

| 단계 | Feature | id | 결과 |
|---|---|---|---|
| A blank | `RET_blank` | `Fq5IPkiwWk5pWYv_15` | OK, 신규 body `RWID` |
| B 홀더 sweep 절삭 | `RET_cut_holders` | `FAjh6Fc5YNmHKHA_16` | OK |
| C 나사 B 절삭 | `RET_cut_screwB` | `FGhyePlAlr5Ibph_16` | OK (sweep 하면 3분할 → 미sweep) |
| D pads | `RET_pads` | `FKRZgsFiBbntLOB_16` | OK |
| E 배선 슬롯 | `RET_wire_slots` | `FylTpDMeC1jcNNP_16` | OK (오프셋 6.0 / 높이 8.0 으로 수정) |
| F 쉘 절삭 | `RET_cut_shell` | `FJIROSGHcjuZmvi_16` | OK (원위치 복사 거부 → 멀리 복사 후 복귀) |

### FeatureScript 에서 배운 것 (누적)

1. 미사용 지역변수 = **에러** (이미 2회)
2. `opPattern` 은 **원위치(identity) 복사를 거부**한다 → 멀리 복사 후 `opTransform` 으로 복귀
3. 볼록체를 방향 d 로 sweep 하려면 간격 ≤ 그 방향 폭이면 `opPattern` + union 으로 **정확**하다
