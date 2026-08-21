# INDEX I4 separate retainer — 구현 및 INDEX FINAL VALIDATION

- 일자: 2026-08-20
- 승인 근거: `docs/23 fastening 결과 승인 / shared retainer fastening = PASS / I4 진행`
- 착수 전 체크포인트: **`INDEX_SHARED_RET_FINAL`** (`6703cd9cbd0d5e321ac10b87`)
- 최종 체크포인트: **`INDEX_FINAL_VALIDATED`** (`03ede76e83b5c865d9a69c35`)
- 결과: **I4 PASS / INDEX = FINAL SUCCESS / MIDDLE 미착수**

---

## A. I4 rear-space 분석

### source of truth

```
center       (+5.496, -29.325, +9.000) mm
F2 axis      (+0.024161, -0.968017, -0.249718)
switch       6 x 6 x 6 mm nominal
seat         6.4 x 6.4 mm
opening      8 x 8 mm
front lip    2.3 mm (실제 F2 source of truth)
switch rear  axis depth 11.3 mm
holder rear  axis depth 12.5 mm
```

라이브 JaD tessellation을 I4 local frame의 5 x 5 ray grid로 측정했다.

| 항목 | 결과 |
|---|---:|
| switch rear 중심 | `(5.223, -18.386, 11.822)` mm |
| holder rear 중심 | `(5.194, -17.225, 12.121)` mm |
| 중심축 다음 JaD 내벽 | depth **45.579 mm** |
| holder rear 이후 가용 깊이 | **33.079 mm** |
| 기존 나사 A/B/C 최소 여유 | 33.78 / **1.96** / 37.60 mm |

I4 rear 중앙과 주변에는 평판을 둘 공간이 충분하다. 복잡한 negative-mold 구조는 필요 없다.

## B. 채택 retainer 구조

**A안 small flat/faceted cap**을 채택했다.

```
NEW PART           RZKD (Part 18)
Feature Studio     OneGrip_I4_Retainer
eid                620b3aaafb6d658702f093d5
FeatureScript      cad/OneGrip_I4_Retainer.fs

plate local u      -1.5 .. +5.0 mm
plate local v      -5.0 .. +5.0 mm
plate axis depth   12.7 .. 15.5 mm
plate size         6.5 x 10.0 x 2.8 mm
final volume       284.8453 mm3
```

초기에는 10 x 10 mm 평판(`u=-5..+5`)을 만들었으나 frozen RWID fastening 영역과
실제 관통이 확인됐다. RWID 최대 X가 `+3.1744 mm`인 반면 초기 평판 최소 X가
`+0.0919 mm`였기 때문이다.

shared geometry는 전혀 수정하지 않고, I4 평판의 기능 없는 split-side 가장자리만
`u=-5.0 -> -1.5 mm`로 줄였다. 최종 평판 최소 X는 **+3.3664 mm**이고,
RWID와 shared service 이동 0..2.09 mm 전 구간에서 양방향 관통 표본은 **0**이다.

## C. pad geometry

```
section      3.6 x 3.6 mm
normal       I4 F2 axis와 동일
front depth  SW_REAR - preload = 11.15 mm (nominal)
rear depth   13.20 mm
plate overlap 0.50 mm
```

pad 중심은 I4 switch rear 중심과 일치한다. holder/seat/opening/cap은 수정하지 않았다.

## D. preload

FeatureScript enum으로 다음 세 값을 유지한다.

| 설정 | 값 |
|---|---:|
| LOW | 0.10 mm |
| **NOMINAL (현재)** | **0.15 mm** |
| HIGH | 0.20 mm |

실제 switch SKU 확정 전 provisional 값이다.

## E. fastening 구조

```
ear center offset   local +u 7.0 mm
ear                 OD 7.0, depth 12.7 .. 16.2 mm
JaD boss            OD 6.0, depth 8.0 .. 12.5 mm
retainer hole       OD 2.4
JaD pilot           OD 1.7
counterbore         없음
```

boss는 JaD에만 downstream positive feature로 추가했다.

```
qUnion([EXISTING_JaD_TARGET_FIRST, NEW_BOSS_SECOND])
```

따라서 JaD partId가 유지된다. 기존 original `Screw_holes`는 수정하지 않았다.

## F. provisional screw

| 항목 | 값 | 상태 |
|---|---:|---|
| screw nominal | 2.0 mm | PROVISIONAL |
| radial clearance | 0.2 mm | PROVISIONAL |
| retainer through hole | 2.4 mm | 계산 결과 |
| pilot | 1.7 mm | PROVISIONAL |
| boss OD | 6.0 mm | PROVISIONAL |

M2급 geometry를 가정했을 뿐 실제 M2 SKU가 최종 선정됐다고 선언하지 않는다.

초기 boss OD 5.0은 pilot 기준 방사벽이 1.65 mm였으므로, 동일 하중 경로의 목표
2.0 mm를 확실히 넘도록 OD 6.0으로 조정했다. 최종 boss 방사벽은 **2.15 mm**다.

## G. driver access

shell-open service 상태에서 screw axis의 rear 방향으로 검사했다.

| 항목 | 결과 |
|---|---:|
| 최초 JaD 장애물 | **28.0989 mm** 이후 |
| I4 switch/holder 간섭 | 0 |
| retainer 자체 차단 | 없음 (관통공) |
| 기존 screw B 최소 여유 | 1.96 mm |

나사와 드라이버 접근 모두 PASS다.

## H. wiring

```
direction      local -v, edge-open
notch width    2.5 mm
notch v range  -5.2 .. -2.2 mm
pad v range    -1.8 .. +1.8 mm
pad gap        0.40 mm
```

pin exit·납땜·wire bend를 위해 평판 가장자리까지 완전히 열린 notch를 만들었다.
notch는 pad에서 0.40 mm 떨어져 있어 pad 하중 단면을 약화시키지 않는다.

## I. d_I4_required

I4는 axis와 같은 방향으로 pad를 빼므로 shared의 사선 이동 공식을 복사하지 않는다.

```
pad front depth = 11.30 - 0.15 = 11.15 mm
holder rear     = 12.50 mm
d_I4_required   = 12.50 - 11.15
                = 1.35 mm
```

## J. d_I4_service

```
d_I4_service = d_I4_required + 0.50
             = 1.85 mm
```

최종 RZKD tessellation의 vertex + face-centroid 표본을 JaD와 RWID에 대해 검사했다.

| 이동 | JaD 관통 | RWID 관통 |
|---:|---:|---:|
| 0.00 | 0 | 0 |
| 0.50 | 0 | 0 |
| 1.00 | 0 | 0 |
| 1.35 | 0 | 0 |
| **1.85** | **0** | **0** |

I4 service sequence는 `shell open -> screw 제거 -> -I4_axis로 1.85 mm 이동 -> pad 완전 이탈
-> 열린 shell에서 손으로 제거`로 성립한다.

## K. structural minimum

| 위치 | 두께 |
|---|---:|
| plate | 2.80 mm |
| pad 단면 | 3.60 mm |
| ear radial wall `(7.0-2.4)/2` | **2.30 mm** |
| ear/plate throat | 2.80 mm 이상 |
| notch 옆 ligament | 3.75 mm |
| JaD boss radial wall `(6.0-1.7)/2` | 2.15 mm |
| **I4 retainer 최소** | **2.30 mm** |

target 2.0 / absolute minimum 1.8을 모두 통과한다.

## L. JaD identity

```
Joystick_1 = JaD, single body
I4 retainer = RZKD, single separate body
solid API count = 18
```

체크포인트 대비 I4 opening/seat 내부 9개 ray의 교차점은 전부 동일하다.
JaD 형상 변화는 신규 boss/pilot 구역에만 국소화됐다.

```
changed vertex bbox:
X 11.342 .. 15.297
Y -22.159 .. -16.298
Z  8.093 .. 15.026 mm
```

기존 opening, seat, cap 위치와 original thumb feature는 변경하지 않았다.

## M. shared retainer 재검증

착수 전 workspace 메시 지문과 최종 메시를 동일 tessellation 조건으로 비교했다.

| frozen part | triangle | volume | fingerprint |
|---|---:|---:|---|
| JfD | 16910 -> 16910 | 49670.4285 -> 49670.4285 | **exact same** |
| RWID | 2112 -> 2112 | 2136.4634 -> 2136.4634 | **exact same** |

따라서 frozen 항목은 전부 무변화다.

- shared minimum web = **1.96 mm** 유지
- shared service travel = **2.09 mm** 유지 (요구 2.07)
- PAD_I1/I2/I3 = 무변화
- wiring slot I1/I2/I3 = 무변화 (I3 기존 95% 상태 그대로)
- relief / EAR_A' / EAR_B' / boss B / holes = 무변화

추가로 frozen RWID를 실제 `+w` 방향으로 0..2.09 mm 이동시키며 RZKD와 교차 검사했다.
모든 단계에서 `RWID in I4 = 0`, `I4 in RWID = 0`이다.

## N. assembly / regeneration

```
feature count       180
OK                  180
ERROR               0
WARNING             0
INFO                4 (원본)
isComplete          true

Joystick assembly   25 / 25 active
occurrences         25
JaD reference       1
JfD reference       1
```

원자 구현 피처:

| 단계 | 피처 | featureId | 결과 |
|---|---|---|---|
| A | `I4_retainer_blank` | `F2N4HZlwCZvkovM_16` | OK |
| B | `I4_contact_pad` | `F9gfp07SWlzFSnX_17` | OK |
| C | `I4_wiring_notch` | `FEZ9SgwjlG4BU2t_17` | OK |
| D | `I4_fastening_ear` | `FTNp8kCrxK2t33K_17` | OK |
| E | `I4_JaD_boss` | `FP31q74LciCNpK9_17` | OK |
| F | `I4_screw_hole` | `FWR7cU5dM92MTjy_17` | OK |

## O. INDEX FINAL SUCCESS / HOLD

### **INDEX = FINAL SUCCESS**

I4 PASS 조건 13개와 INDEX 전체 재검증 조건을 모두 만족한다.

## P. INDEX_FINAL_VALIDATED 생성 여부

### **생성 완료**

```
name  INDEX_FINAL_VALIDATED
id    03ede76e83b5c865d9a69c35
```

이 버전 이후 MIDDLE 개발 중 INDEX feature를 수정하지 않는다.

## Q. MIDDLE GO / HOLD

### **MIDDLE = 다음 실행부터 GO, 이번 실행에서는 HOLD(미착수)**

지시대로 `INDEX_FINAL_VALIDATED` 생성 직후 멈췄다. M1~M4는 생성하지 않았다.

---

## 최종 PASS 표

| # | 조건 | 결과 |
|---|---|---|
| 1 | nominal switch rear retention | PASS |
| 2 | existing I4 seating unchanged | PASS |
| 3 | existing opening unchanged | PASS |
| 4 | pad aligned to F2 axis | PASS |
| 5 | service removal | PASS, 1.85 mm |
| 6 | wiring access | PASS |
| 7 | screw fastening | PASS, provisional |
| 8 | driver access | PASS, 28.10 mm |
| 9 | structural thickness >=1.8 | PASS, 2.30 mm |
| 10 | JaD identity | PASS |
| 11 | JfD/shared retainer unchanged | PASS, exact fingerprint |
| 12 | ERROR 0 | PASS |
| 13 | assembly normal | PASS, 25/25 |
