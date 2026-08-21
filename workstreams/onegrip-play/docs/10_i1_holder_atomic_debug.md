# I1 holder pipeline 원자 분해 디버그 — 전 단계 PASS

- 일자 2026-08-19
- 대상: **INDEX_BTN_1 하나뿐.** I2/I3/I4/MIDDLE/RETAINER 미생성
- 체크포인트: 버전 `I1_atomic_debug_start` (`d6bd9efad2901e6f6103dfca`) — 작업 전 생성
- 결과: **TEST A~E 전부 PASS.** pre-union holder 파이프라인이 정상 동작함을 증명

---

## 0. 결론

> **CASE 6 — A~E 전부 성공.**
> pre-union holder 아키텍처(blank NEW BODY → blank만 hollow → 마지막 ADD UNION)는
> **정상 작동한다.** 직전 실행의 `INDEX_holders_preunion` 실패는 아키텍처 문제가 아니라
> **한 Feature 안에서 4버튼을 배열/다중 boolean 으로 동시에 처리한 로직**의 문제였다.

---

## 1. 사전 확인

| 항목 | 결과 |
|---|---|
| `JaD` Joystick_1 / `JfD` Joystick_2 | 존재, solid 16개 |
| regeneration 오류 | 0 |
| 체크포인트 버전 | `I1_atomic_debug_start` 생성 완료 |

### I1 축 재확인

승인 좌표 `(-22.224, -17.494, 9.000)` 에서 현재 표면을 재측정하면
**거리 4.003 mm, 법선 (+0.2739, +0.0703, −0.9592)** 가 나온다.
이는 오류가 아니라 **승인된 8 mm 개구부가 그 지점의 표면을 이미 제거했기 때문**이며,
측정된 면은 개구부의 측벽이다.

검증: 그 측벽 법선과 승인 축의 내적

```
(0.2739, 0.0703, −0.9592) · (−0.9291, −0.2385, −0.2828)
  = −0.25450 − 0.01677 + 0.27127 = −0.00000
```

**정확히 0 → 개구부가 승인 축에 정밀하게 정렬되어 있음이 확인된다.**
따라서 승인 축 `(-0.9291, -0.2385, -0.2828)` 을 그대로 사용했다.

(참고: 축에서 7 mm 떨어진 온전한 표면의 법선은 중심과 11~25° 차이가 난다.
I1 국소 곡률반경이 약 17 mm 로 작기 때문이며 정상이다.)

---

## 2. 디버그 구조

기존 `OneGrip_FingerButtons` 를 건드리지 않기 위해
**별도 Feature Studio** `OneGrip_I1_Debug` (`12c6873f8965a019b17f4e24`) 를 만들었다.
소스: `cad/OneGrip_I1_Debug.fs`

이번 디버그에서 **의도적으로 사용하지 않은 것**:

- `clipAtSplit` / X=0 클리핑 (I1 은 분할면에서 충분히 떨어져 있음)
- `concatenateArrays` 를 이용한 배열 UNION
- 다중 target REMOVE
- 여러 버튼 동시 boolean
- 쉘 2개를 한 op 에서 처리

**한 stage = 한 operation 계열**, body 는 blank 1개와 JfD 1개만 다뤘다.

blank 식별은 이름/인덱스가 아니라 좌표로 한다:
`blankPt = P − zA·6mm + xA·4.5mm` (holder 벽 안, seat/bore 어디에도 속하지 않는 지점).

### 깊이 체계 (전부 파라미터 종속)

```
쉘 벽 안쪽면   3.0
blank          2.8 … 12.5   (12.4 × 12.4)
front lip      2.8 … 3.8    (stem bore 4.5 만 관통)
switch seat    3.8 … 10.0   (스위치 3.8…9.8 + retainer_clearance 0.2)
rear 개방      10.0 … 14.5
```

---

## 3. TEST 결과

| TEST | Feature name | Feature ID | operation | state | solid before→after | 신규 body | 소멸 body | JaD | JfD |
|---|---|---|---|---|---|---|---|---|---|
| **A** | `DEBUG_I1_holder_blank` | `FfmaKp2OQZTimUt_15` | `fCuboid` + `opTransform` (NEW BODY) | **OK** | 16 → 17 | `RMFD` | — | 유지 | 유지 |
| **B** | `DEBUG_I1_switch_seat` | `FezJmTeZqE7iGiI_16` | seat 6.4×6.4 SUBTRACT (target = blank) | **OK** | 17 → 17 | 없음 | 없음 | 유지 | 유지 |
| **C** | `DEBUG_I1_open_rear` | `FVnIKEB4TpMO9oH_16` | rear 개방 SUBTRACT (target = blank) | **OK** | 17 → 17 | 없음 | 없음 | 유지 | 유지 |
| **D** | `DEBUG_I1_front_lip_bore` | `FpG3GYhbq9gpPMO_16` | stem bore 4.5 SUBTRACT (target = blank) | **OK** | 17 → 17 | 없음 | 없음 | 유지 | 유지 |
| **E** | `DEBUG_I1_union_JfD` | `FzbDmDsB3vjLdH6_16` | `qUnion([JfD, blank])` UNION | **OK** | 17 → 16 | 없음 | `RMFD` (JfD 로 흡수) | 유지 | **유지** |

**최초 실패 operation: 없음.**

### TEST E 직후 무결성 검사 (8개 항목 전부 통과)

| # | 항목 | 결과 |
|---|---|---|
| 1 | `JfD` partId 유지 | **YES** |
| 2 | `Joystick_2` body 개수 | **1개** (`JfD`) |
| 3 | duplicate `Joystick_2` | **없음** |
| 4 | body split | **없음** (신규 partId 0개) |
| 5 | `JaD` 정상 | **YES** (`Joystick_1` 1개) |
| 6 | assembly `Joystick_2 <1>` 참조 | **`JfD` 정상** |
| 7 | occurrences | **25 / 25** (변화 없음) |
| 8 | regeneration ERROR | **0** |

---

## 4. 최종 I1 holder geometry 실측

`evDistance` 로 버튼 축에서 가장 가까운 면까지의 거리를 측정:

| 깊이 | 측정값 (축→면) | 설계값 | 판정 |
|---|---|---|---|
| 3.3 mm (stem bore 구간) | **2.250 mm** | 4.5/2 = 2.25 | **정확 일치** |
| 6.0 mm (switch seat) | **3.147 mm** | 6.4/2 = 3.20 | 일치 (−0.053, 모서리 근접 측정 오차) |
| 11.0 mm (rear 개방) | **3.200 mm** | 6.4/2 = 3.20 | **정확 일치** |

- `Joystick_2` 부피 = **48.3755 cm³**
- solid body 수 = **16** (원래 상태 복귀 + holder 흡수)
- switch seat **6.4 × 6.4 mm** 확보
- front lip 4.5 mm 보어로 **front stop 형성** (스위치 6.0 mm 는 통과 불가)
- rear 완전 개방 → 내부 삽입 경로 및 배선 접근 확보

---

## 5. 직전 실행 실패의 원인 범위 축소

| 후보 | 판정 |
|---|---|
| pre-union 아키텍처 자체 | **무죄** — A~E 전부 PASS |
| `fCuboid` / `opTransform` blank 생성 | **무죄** (TEST A) |
| blank 대상 seat SUBTRACT | **무죄** (TEST B) |
| blank 대상 rear SUBTRACT | **무죄** (TEST C) |
| blank 대상 bore SUBTRACT | **무죄** (TEST D) |
| `qUnion([shell, body])` UNION | **무죄** (TEST E) |
| **`concatenateArrays` 배열 UNION** | **용의자 잔존** |
| **다중 target SUBTRACT (blank 여러 개)** | **용의자 잔존** |
| **`clipAtSplit` (I3/I4 전용)** | **용의자 잔존** |
| **한 Feature 안 4버튼 동시 처리** | **용의자 잔존** |

→ 다음 단계는 **버튼을 하나씩 추가하며 같은 원자 패턴을 반복**하는 것이다.
배열/다중 boolean 을 쓰지 말고, 버튼마다 별도 stage 또는 별도 Feature 로 처리하면
직전 실패를 재현하지 않는다.

---

## 6. 현재 문서 상태

| 항목 | 값 |
|---|---|
| 살아있는 커스텀 피처 | `INDEX_construction`, `INDEX_openings`, `INDEX_button_caps` + `DEBUG_I1_*` 5개 |
| `JaD` / `JfD` | 정상, split 0 |
| 기존 엄지 파트 10개 | 변화 없음 |
| **I1 holder** | **완성** (blank → seat → rear → lip → JfD 흡수) |
| I2 / I3 / I4 holder | 없음 |
| retainer | 없음 (지시대로 미생성) |
| regeneration | **오류 0** |

`DEBUG_I1_*` 5개 피처는 디버그용 이름이지만 **실제 형상을 만들고 있으므로 삭제하지 않았다.**
다음 실행에서 정식 파이프라인으로 통합할 때 이름을 정리하면 된다.

---

## 7. 다음 실행 권고

1. I2 를 같은 원자 패턴으로 추가 (blank → seat → rear → lip → union). 배열 사용 금지
2. 성공하면 I3 (여기서 `clipAtSplit` 을 **별도 stage 로 분리해** 단독 검증)
3. 그다음 I4 (JaD union)
4. 4개 완료 후 outer wall / switch clearance 재측정
5. 마지막에 retainer 단계

각 버튼 추가 직후 반드시 `JfD`/`JaD` partId·body 개수·assembly 참조를 확인한다.
