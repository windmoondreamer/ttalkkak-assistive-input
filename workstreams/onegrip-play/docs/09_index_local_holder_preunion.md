# INDEX local holder (pre-union 방식) — 사전 검증 및 중단

- 일자 2026-08-19
- **CAD WRITE 0건.** 이번 실행에서 Feature 추가·수정·삭제 없음
- 문서 상태는 직전 실행 종료 시점 그대로 (JaD / JfD 정상, regeneration 오류 0)
- 근거 데이터: 원본 `PushBtn` tessellation (chordTolerance 0.05mm), 로컬 계산

---

## 0. 요약

새 아키텍처(holder blank → 자체 hollow → 마지막에 shell ADD UNION)로 진행하기 전
§3·§7의 **필수 사전 검증 두 가지**를 먼저 수행했다.

| 검증 | 결과 |
|---|---|
| §7 실제 switch solid 간 충돌 | **PASS** — 최소 1.741 mm |
| §3 switch envelope 분해 → seat depth 산출 | **차단 요인 발견 — 아래 §3** |

§3 에서 나온 문제 때문에 **holder blank 생성 단계로 들어가지 않고 멈췄다.**
seat depth 를 추측으로 정하지 말라는 지시(§3)에 따른 것이다.

---

## 1. 실제 switch solid 충돌 검사 (§7) — PASS

각 버튼의 승인된 local 3D coordinate system 에 원본 `PushBtn` 실제 메시(정점 1767개)를
배치하고 쌍별 최소 거리를 계산했다. 배치 기준: 스위치 앞면을 쉘 벽 안쪽면(깊이 3.0 mm)에 정렬.

| 쌍 | 최소 거리 | 비고 |
|---|---|---|
| I1 ↔ I2 | **1.741 mm** | DOMINANT 내 최소 |
| I2 ↔ I3 | **2.226 mm** | |
| I1 ↔ I3 | 11.191 mm | |
| I3 ↔ I4 | 3.213 mm | 분할면 건너 (다른 쉘) |
| I2 ↔ I4 | 12.871 mm | 다른 쉘 |
| I1 ↔ I4 | 21.168 mm | 다른 쉘 |

**DOMINANT(I1/I2/I3) 최소 상호 clearance = 1.741 mm > 0 → 충돌 없음.**

> **[2026-08-19 철회] 이 절의 스위치 상호 clearance 수치는 오류다.**
> 꼭짓점 최단거리로 계산해 회전된 박스의 관통을 검출하지 못했다.
> 분리축 정리(SAT)로 다시 계산하면 **I1↔I2 는 1.833 mm 관통(충돌)**,
> **I2↔I3 는 여유 0.040 mm** 다. 근거와 대안: `docs/12_switch_collision_stop_condition.md`



> 이것이 이번 아키텍처 변경의 핵심 근거를 확증한다.
> 깊은 divider wall 이 없어도 **실제 스위치끼리는 물리적으로 간섭하지 않는다.**
> docs/07 에서 divider 가 0 mm 였던 것은 스위치 배치 문제가 아니라
> 포켓 절삭 형상의 문제였음이 다시 확인된다.

---

## 2. PushBtn B-rep 분해 (§3)

원본 `PushBtn` (partId `JFD`) 축(local Z = 누름축) 방향 단면 실측:

| Z (mm) | X 폭 | Y 폭 | 6.4 포켓 |
|---|---|---|---|
| −3.00 | 5.010 | 3.000 | OK |
| −2.75 | 5.143 | 0.500 | OK |
| −2.50 | 6.010 | 3.500 | OK |
| **−2.25** | **7.566** | **6.712** | **초과** |
| **−2.00** | 6.600 | **7.019** | **초과** |
| **−1.75** | 6.600 | **8.413** | **초과** |
| **−1.50** | **7.566** | **8.212** | **초과** |
| −1.25 … +1.25 | 2.6~6.0 | 2.000 | OK |
| **+1.50 … +2.25** | 6.6~7.566 | 6.7~8.4 | **초과** |
| +2.50 … +3.00 | 5.0~6.0 | 0.5~3.5 | OK |

- 전체 축방향 envelope = **6.010 mm** (Z −3.005 … +3.005)
- 형상이 Z=0 기준 **완전 대칭**이며, 넓은 밴드가 **양쪽 |Z| 1.5~2.25 에 두 번** 나타난다
- 가운데(|Z| ≤ 1.25)는 Y 폭이 2.000 mm 로 매우 얇다

### 판정: `#finger_switch_body_depth` / `#finger_switch_actuator_projection` 분리 불가

일반적인 택트 스위치라면 "몸체 + 한쪽 액추에이터" 로 비대칭이어야 하는데,
이 모델은 **Z=0 대칭**이고 넓은 밴드가 양쪽에 있다.
따라서 어느 쪽이 액추에이터인지, 어디까지가 mounting body 인지
**geometry 만으로 확정할 수 없다.**

원본 문서의 `PushBtn.SLDPRT` blob 을 임포트한 모델이며,
실제 부품의 기능적 방향 정보가 CAD 에 담겨 있지 않다.

---

## 3. 차단 요인 — seat depth 를 실측으로 정할 수 없다

스위치 앞면을 쉘 벽 안쪽면(깊이 3.0 mm)에 맞추면 깊이 대응은 다음과 같다.

```
깊이 d  ↔  스위치 local Z = 6.005 − d
```

| 깊이 구간 | 스위치 단면 | 6.4 mm seat 통과 |
|---|---|---|
| 3.00 … 3.755 mm | ≤ 6.0 | **가능** |
| **3.755 … 4.505 mm** | **최대 7.566 × 8.413** | **불가** |
| 4.505 … 7.505 mm | ≤ 6.0 | 가능 |
| **7.505 … 8.255 mm** | **최대 7.566 × 8.413** | **불가** |
| 8.255 … 9.010 mm | ≤ 6.0 | 가능 |

→ **6.4 × 6.4 seat 는 깊이 3.0 부터 0.755 mm 밖에 들어가지 못한다.**
0.755 mm 로는 locating seat 기능(측방 고정)을 할 수 없다.

즉 다음 중 하나가 성립해야 한다.

1. 스위치 배치 방향/깊이가 내 가정과 다르다 (앞면 정렬 위치가 다름)
2. 넓은 밴드(7.566 × 8.413)는 **seat 앞이나 뒤에 위치**해야 하며,
   seat 는 그 사이 좁은 구간만 잡아야 한다
3. 실제 사용할 스위치가 이 `PushBtn` 모델과 다르다

**원본 설계도 backplate 에 6.4 mm 관통 구멍을 쓰므로 같은 제약을 받는다.**
원본에서는 backplate 두께(약 2~3 mm)만큼만 6.4 구멍이고 나머지는 뒤쪽 공동에 있으므로
**"짧은 seat + 열린 뒤" 구조 자체는 원본과 동일**하다.
문제는 그 짧은 seat 를 스위치의 **어느 구간**에 걸어야 하는지가 확정되지 않는다는 점이다.

지시(§3 "값을 추측하지 말고 실측값을 근거로 정한다")에 따라 여기서 멈춘다.

---

## 4. 결정이 필요한 사항

다음 중 하나를 알려주면 즉시 holder blank 생성으로 진행할 수 있다.

**A. 실제 사용할 택트 스위치 사양** (권장)
- 몸체 치수 (예: 6×6×3.5 mm)
- 액추에이터 돌출 높이
- 핀 배치
→ 이 값으로 `#finger_switch_body_depth` / `#finger_switch_actuator_projection` 을 확정하고
  seat depth = body_depth + 0.2~0.3 mm 로 계산한다

**B. `PushBtn` 모델을 그대로 쓰되 배치 기준을 지정**
- 스위치의 어느 면을 쉘 벽 안쪽면에 맞출지
- 넓은 밴드(|Z| 1.5~2.25)를 seat 앞에 둘지 뒤에 둘지
→ 그에 맞춰 seat 구간을 계산한다

**C. seat 를 6.4 mm 가 아닌 스위치 최대폭(7.6 × 8.5 mm)으로 확대**
- 넓은 밴드까지 수용 가능해지지만 승인된 "pocket 6.4 mm 유지" 조건(§14-5)과 충돌한다
- 이 경우 성공 조건 변경 승인이 필요하다

---

## 5. 이번 실행에서 확정된 값

| 항목 | 값 | 근거 |
|---|---|---|
| switch 축방향 envelope | **6.010 mm** | PushBtn 실측 |
| switch 점유 깊이 (앞면 3.0 기준) | 3.0 … **9.010 mm** | 계산 |
| I1↔I2 실제 switch clearance | **1.741 mm** | 메시 실측 |
| I2↔I3 실제 switch clearance | **2.226 mm** | 메시 실측 |
| I3↔I4 실제 switch clearance | 3.213 mm | 분할면 건너 |
| deep divider 필요 여부 | **불필요** | 위 clearance 로 확증 |

---

## 6. 다음 실행 계획 (승인 대기)

§4 결정이 나오면 아래 순서로 진행한다. FeatureScript 골격은 이미 준비되어 있다.

1. 현재 상태 checkpoint 버전 생성
2. `HOLDER_BLANKS` 단계: 버튼별 로컬 프레임에 blank 를 **NEW BODY** 로 생성
   (쉘과 union 하지 않음)
3. blank **자체만** target 으로 seat pocket REMOVE + rear open
4. blank 3개 상태에서 §7 항목 재검증 (pocket size / seat depth / outer wall)
5. `HOLDER_UNION` 단계: `qUnion([JfD_target, blanks])` 로 ADD UNION
   → 직후 `JfD` 존재 / body split 0 / assembly 참조 즉시 확인, 실패 시 즉시 rollback
6. I4 도 동일 구조로 통일 (동일 FeatureScript 재사용성 확보)
7. retainer 는 별도 단계로 분리 (§12)


---
---

# 2차 실행 — 6x6x6 스위치 기준 재설계 (2026-08-19)

## 10. 전제 갱신

원작자 명시 사양 **6 x 6 x 6 mm tactile push switch** 를 하드웨어 기준으로 확정.
임포트된 `PushBtn.SLDPRT`(7.566 x 8.519 x 6.010)는 **참조 모델**로만 취급하고
기계적 envelope 의 source of truth 로 쓰지 않는다.
→ docs/09 §3 의 "6.4mm seat 가 0.755mm 밖에 안 들어간다" 차단 판정은 **철회**한다.

## 11. 6x6x6 기준 충돌 재검사 — PASS

스위치 앞면을 깊이 3.8mm(쉘 벽 3.0 + front lip 0.8)에 정렬한 6x6x6 envelope:

| 쌍 | 최소 거리 |
|---|---|
| **I1 ↔ I2** | **2.036 mm** |
| I2 ↔ I3 | 2.164 mm |
| I1 ↔ I3 | 3.644 mm |
| I3 ↔ I4 | 4.176 mm (다른 쉘) |

**DOMINANT 최소 2.036 mm > 0 → 충돌 없음.** 깊은 divider 불필요가 재확인된다.

> **[2026-08-19 철회] 이 절의 스위치 상호 clearance 수치는 오류다.**
> 꼭짓점 최단거리로 계산해 회전된 박스의 관통을 검출하지 못했다.
> 분리축 정리(SAT)로 다시 계산하면 **I1↔I2 는 1.833 mm 관통(충돌)**,
> **I2↔I3 는 여유 0.040 mm** 다. 근거와 대안: `docs/12_switch_collision_stop_condition.md`



## 12. 추가한 변수 (전부 state OK)

| 변수 | 값 | 성격 |
|---|---|---|
| `#finger_switch_total_height` | **6 mm** | 확정 (원작자 사양) |
| `#finger_switch_body_depth` | **6 mm** | 확정 (footprint) |
| `#finger_switch_pocket_width` | **6.4 mm** | 확정 (6.0 + 0.2/측) |
| `#finger_switch_stem_height` | **0 mm** | **미확정 — 실제 부품 확정 시 입력** |
| `#finger_switch_body_height` | 6 mm | `total - stem` 관계. 현재 stem=0 가정 |
| `#finger_switch_front_lip` | 0.8 mm | front stop 두께 (조정 가능) |
| `#finger_switch_stem_bore` | 4.5 mm | stem 통과 구멍 (조정 가능) |

## 13. V3 아키텍처 (FeatureScript 작성 완료, 배포 미완)

`cad/OneGrip_FingerButtons.fs` 를 pre-union 방식으로 재작성했다.

```
1) holder blank 를 NEW BODY 로 생성            (쉘과 무관)
2) blank 자체만 target 으로 seat + stem bore 제거
3) 마지막에 qUnion([shell, blanks]) 로 ADD UNION
```

쉘에 대한 negative op 는 **승인된 버튼 개구부(OPENINGS) 하나뿐**이다.
깊이 체계(전부 파라미터 종속):

```
쉘 벽 안쪽면   3.0
front lip      3.0 … 3.8      (stem bore 4.5mm 만 관통 -> front stop)
스위치         3.8 … 9.8      (total_height 6.0)
seat 끝        10.0           (+ retainer_clearance 0.2)
retainer 판    10.0 … 12.5    (retainer_thickness 2.5)
blank          2.8 … 12.5     (12.4 x 12.4, I3/I4 는 X=0 클립)
```

## 14. 중단 — HOLDERS 단계 배포 실패

`INDEX_holders_preunion` 이 두 차례 `state = ERROR` 로 생성되었다.

| 시도 | 변경 | 결과 |
|---|---|---|
| 1 | blank -> seat/bore 일괄 제거 -> union | ERROR |
| 2 | seat/bore 제거를 쉘별(dom/opp)로 분리 | ERROR |

오류 메시지를 Onshape API 가 노출하지 않아(featureStates 는 상태만 반환)
원인을 특정하지 못했다. 남은 후보:

1. `concatenateArrays([[shellQuery], blankQueries])` 로 만든 UNION tools 배열
2. `clipAtSplit` 의 blank 대상 subtraction
3. blank 끼리 겹친 상태에서의 다중 target subtraction

**budget 한계로 반복을 중단하고, 오류 피처를 삭제해 문서를 정합 상태로 되돌렸다.**

## 15. 현재 문서 상태

| 항목 | 값 |
|---|---|
| `JaD` Joystick_1 / `JfD` Joystick_2 | **정상, split 0** |
| 기존 엄지 파트 10개 | 변화 없음 |
| 살아있는 커스텀 피처 | `INDEX_construction`, `INDEX_openings`, `INDEX_button_caps` |
| 신규 캡 4개 | 존재 (`R4ED`/`R9ED`/`RCFD`/`RHFD`, 이름 미부여) |
| **빠진 것** | **holder 전체** (blank/seat/bore/union) |
| regeneration | **오류 0** |

## 16. 다음 실행 최소 작업

1. HOLDERS 단계를 **버튼 1개(I1)만** 대상으로 축소해 배포 → 어느 op 가 실패하는지 격리
   (Onshape 가 오류 메시지를 주지 않으므로 이 방법이 가장 빠르다)
2. 성공하면 4개로 확장
3. `qUnion(concatenateArrays(...))` 대신 미리 만든 배열 변수를 쓰는 형태로 단순화 시도
4. CAPS 이름 재부여, RETAINER 단계 적용
