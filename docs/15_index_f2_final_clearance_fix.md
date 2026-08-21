# INDEX F2 최종 여유 수정 — 적용 및 실물 검증

- 일자 2026-08-19
- 승인 근거: `docs/14_index_f2_rebuild.md` (HOLD 3건 + 수정안 승인)
- 체크포인트 버전: **`F2_final_fix_start`** (`63e475448496b75aaeefdc24`)
- WRITE 대상: `OneGrip_Play_V1` did `a21e64f36bc61df760d4587c` / wid `ef6a7b3ccc45186203e4d2ca`
- **판정: §15 PASS 조건 11개 중 10개 직접 확인 PASS, 1개(regeneration 상태 직접 읽기)는
  rate limit 으로 간접 확인. 형상 결함 없음.**

---

## 0. 적용한 변경 — FeatureScript 3곳

피처를 추가·삭제하지 않았다. FS 소스만 고쳐 기존 인스턴스를 전부 재생성했다.

| # | 변경 | 이전 → 이후 |
|---|---|---|
| 1 | `IDX` 축 | F2 → **승인된 신규 축 4개** |
| 2 | `LIP_F2` | 1.5 → **2.3 mm** (스위치 앞면 축깊이 **5.3 mm**) |
| 3 | `blankTo` | `seatTo + retT(2.5)` → **`seatTo + 1.0`** |

3번으로 `#finger_retainer_thickness` 참조가 사라져 `retT` 가 미사용이 되었고,
**FeatureScript 는 미사용 지역변수를 에러로 처리**하므로 선언을 함께 제거했다.
(docs/14 §0.2 와 같은 유형. 이제 알려진 함정이다)

### 깊이 체계

```
쉘 벽             0 … 3.0      (n0 기준)
front trim 평면   n0 깊이 2.8   ← blank 앞면
스위치 앞면       축 깊이 5.3   (= 3.0 + 2.3)
스위치 뒷면       축 깊이 11.3
seat 끝           축 깊이 11.5
blank 뒤끝        축 깊이 12.5  (= seatTo + 1.0)
holder 단면       12.4 × 12.4
```

---

## 1. 최종 보고 (A ~ N)

### A. rebuild — **PASS**

| 항목 | 결과 |
|---|---|
| FS 컴파일 | OK (`idxHolderAtomic`) |
| solid body | **18개** (원본 14 + INDEX 캡 4). 예상 외 body **0개** |
| 시트 치수 | **4/4 전부 축에서 3.200 mm** = 정확히 6.4 × 6.4 (깊이 6.0 / 8.4 / 11.0 전부) |
| front trim | **4/4 적용.** 원본 외피 바깥 표본 289개 × 4 중 재료 **0개**, 돌출 **0.00 mm** |
| split clip | **4/4 적용** (아래 I 항목) |

### B. final axes

| | 축 (x, y, z) | 법선 편차 |
|---|---|---|
| **I1** | `(-0.851033, -0.500047, -0.160298)` | 17.21° |
| **I2** | `(-0.393870, -0.571110, -0.720208)` | 17.21° |
| **I3** | `(-0.069850, -0.997555, +0.002429)` | 17.21° |
| **I4** | `(+0.024161, -0.968017, -0.249718)` | 2.66° |

버튼 중심·Z=+9·피치 11·캡 8·6×6×6 스위치·3+1 ownership **전부 유지**.

### C. exact SAT minimum clearance — **1.3476 mm (조건 ≥ 1.20) PASS**

정확 분리축 정리(SAT). vertex-distance 미사용.

| 쌍 | 여유 |
|---|---|
| **I1-I2** | **+1.3476 mm** |
| I2-I3 | +1.3490 mm |
| I1-I3 | +4.7151 mm |
| I3-I4 | +3.9314 mm |
| I1-I4 | +13.3946 mm |
| I2-I4 | +10.0811 mm |

docs/14 예상 **1.348 mm** → 실제 **1.3476 mm**. 일치.

### D. pocket divider minimum — **0.8000 mm (조건 ≥ 0.80) PASS**

| 쌍 | 해석(포켓 OBB) | **실물 메시 광선상 재료** |
|---|---|---|
| **I1-I2** | 0.8000 mm | **0.8000 mm** (구간 [0.000, 0.800]) |
| **I2-I3** | 0.8000 mm | **0.8000 mm** (구간 [0.000, 0.800]) |
| I1-I3 | 4.2055 mm | — |
| I3-I4 | 3.5133 mm | — |

> **§10 요구 확인:** 경계값 0.800 이 메시 오차인지 실제 부족인지 구분했다.
> 두 포켓 최근접점을 잇는 선을 실물 tessellation 으로 관통 측정한 결과
> 재료 구간이 **정확히 0.800 mm** 로, 해석값과 완전히 같다.
> 포켓은 `fCuboid` 로 만든 정확한 박스이므로 이 값이 곧 B-rep 값이다. **부족분 없음.**

### E. actual seating — **4/4 YES**

평평한 쉘 가정을 쓰지 않고, **재생성된 실물 tessellation** 에 대해
각 버튼 축을 따라 6 × 6 단면(225개 표본)을 광선 관통시켜 측정했다.

| | required seating depth | first shell collision depth | seating feasible | min shell clearance |
|---|---|---|---|---|
| **I1** | **5.300 mm** | 5.300 mm (국소 −2.57, −2.57) | **YES** | 0.200 mm |
| **I2** | **5.300 mm** | 5.300 mm (국소 −2.57, +0.43) | **YES** | 0.200 mm |
| **I3** | **5.300 mm** | 5.300 mm (국소 −2.14, +3.00) | **YES** | 0.200 mm |
| **I4** | **5.300 mm** | 5.300 mm (국소 +2.57, −2.57) | **YES** | 0.200 mm |

**필요 깊이가 4개 전부 설계값 5.300 mm 와 정확히 같다.**
docs/14 HOLD-1 의 "개구부 바깥 쉘 벽이 앞모서리를 막는" 현상이 **완전히 사라졌다**
(이전: 필요 4.75 / 4.70 / 5.15 / 4.30 로 설계 4.5 를 초과했다).
min shell clearance 0.200 mm 는 설계 포켓 여유(6.4 − 6.0)/2 그대로다.

### F. opening / stem minimum clearance — **PASS**

기존 8 × 8 개구부를 **재생성 없이 그대로** 사용한다.

| | 4.5 mm 잠정 stem bore ↔ 개구부 벽 |
|---|---|
| I1 | 0.801 mm |
| **I2** | **0.730 mm** |
| I3 | 0.731 mm |
| I4 | 1.616 mm |

→ 최소 **0.730 mm > 0**. 통과 가능.

### G. cap travel — **PASS (외형 무수정)**

| | 캡 이동축(n0) ↔ 플런저축 | 행정 0.25 mm 당 측방 어긋남 |
|---|---|---|
| I1 / I2 / I3 | 17.21° | **0.0740 mm** |
| I4 | 2.66° | 0.0116 mm |

최대 **0.0740 mm < 캡 여유 0.20 mm**. **외부 캡 형상은 전혀 건드리지 않았다.**
남은 작업은 캡 밑면 접촉 pad 의 방향뿐이며, 이번 실행 범위가 아니다.

### H. screw B minimum 3D clearance — **2.990 mm (I4), 조건 ≥ 2.50 PASS**

단순 Z 비교가 아니라 유한 원기둥(⌀7, X ∈ [−6, +10]) ↔ 홀더 OBB 의 정확 3D 최소거리.

| | I1 | I2 | I3 | **I4** |
|---|---|---|---|---|
| 나사 B 3D 최소거리 | 4.466 | 5.058 | 4.726 | **2.990 mm** |

최소값 버튼 = **I4**. docs/14 예상 2.89 → 실제 **2.99 mm** (예상보다 양호).
`blankTo` 를 13.2 → 12.5 로 줄인 효과다.

### I. split ownership — **PASS**

| | 포켓 X 범위 | 분할면 벽 | 요구 | 판정 |
|---|---|---|---|---|
| I3 | −8.319 … **−1.500** | **1.500 mm** | X ≤ 0 | **PASS** |
| I4 | **+1.999** … +8.587 | **1.999 mm** | X ≥ 0 | **PASS** |

holder blank 은 여전히 분할면을 넘으므로(I3 → +1.56, I4 → −1.04) `SPLITCLIP` 이 필요하며,
**실물에서 적용 확인**: `JfD` 안의 X>0 영역 표본 253개 중 재료 **0개**,
`JaD` 안의 X<0 영역 표본 176개 중 재료 **0개**.

기존 결과를 재사용하지 않고 **신규 geometry 로 다시 실측**했다.

### J. JaD / JfD — **PASS**

| 항목 | 결과 |
|---|---|
| `JaD` = Joystick_1 | 유지, **body 1개** |
| `JfD` = Joystick_2 | 유지, **body 1개** |
| body split | **0** |
| duplicate shell | **0** |
| 예상 외 신규 body | **0** |

### K. assembly / regeneration

| 항목 | 결과 |
|---|---|
| `Joystick` occurrences / instances | **25 / 25** |
| `Joystick_1` → `JaD`, `Joystick_2` → `JfD` | **정상** |
| 삭제된 plug 참조 (dangling) | **0개** |
| **regeneration ERROR 직접 읽기** | **불가 — `/features` GET 429 (Retry-After 6,174 s ≈ 1.7 h)** |

> **간접 확인:** 모든 stage 인스턴스의 산출물이 정상이다 —
> blank 4개 존재, 시트 4/4 정확히 6.4×6.4, front trim 4/4 적용(돌출 0.00),
> split clip 4/4 적용, union 4/4 완료(별도 body 잔존 0), RETAINER no-op 4/4(plug 0개),
> body 수 18개로 예상과 정확히 일치, assembly 무결.
> **어느 피처가 ERROR 였다면 이 중 하나는 반드시 어긋난다.** 형상 결함은 없다.
> 다만 `featureStates` 를 직접 읽은 것은 아니므로, **rate limit 해제 후 확인 예정**이다.

### L. front lip actual applied value — **2.3 mm**

```
FeatureScript:  const LIP_F2 = 2.3 * millimeter;
결과 스위치 앞면 축깊이 = SHELL_WALL(3.0) + 2.3 = 5.3 mm
```
실물 측정에서 스위치가 정확히 5.300 mm 에 착좌함을 확인했다(§E).
**이 값이 현재 형상의 source of truth 다.**

### M. stale tree-variable 상태 — **TECHNICAL DEBT (기록됨)**

| | 값 | 상태 |
|---|---|---|
| FS 상수 `LIP_F2` | **2.3 mm** | **실제 형상 기준 (source of truth)** |
| 트리 변수 `#finger_switch_front_lip` | 0.8 mm | **사문(死文). 아무 데서도 읽히지 않음** |

FS 소스 상단에 `===== TECHNICAL DEBT / TODO =====` 블록으로 명시했다.
트리 변수를 수정하려면 그 featureId 가 필요하고 그러려면 `/features` GET 이 필요한데
429 상태다. **rate limit 해제 후 트리 변수를 2.3 으로 바꾸고 `getVariable` 로 되돌린다.**
**트리의 0.8 mm 를 기준으로 삼지 말 것.**

### N. shared retainer 진행 — **GO (단, K 의 formal 확인을 선행)**

§15 PASS 조건 대조:

| # | 조건 | 결과 |
|---|---|---|
| 1 | switch SAT ≥ 1.20 mm | **1.3476** PASS |
| 2 | pocket divider ≥ 0.80 mm | **0.8000** PASS |
| 3 | screw clearance ≥ 2.50 mm | **2.990** PASS |
| 4 | actual seating 4/4 YES | **4/4 YES** PASS |
| 5 | 기존 8×8 openings 사용 가능 | **PASS** (최소 0.730 mm) |
| 6 | cap exterior unchanged | **PASS** (무수정) |
| 7 | 3+1 ownership 유지 | **PASS** |
| 8 | JaD/JfD 유지 | **PASS** |
| 9 | assembly 25/25 | **PASS** |
| 10 | regeneration ERROR 0 | **간접 PASS** (직접 읽기 429) |
| 11 | old twist-lock plug 재생성 없음 | **PASS** (`RWID`/`RmID`/`R2ID`/`RGJD` 부재) |

→ **실패 항목 0건.** 10번만 형식적 확인이 남았다.
`/features` 가 열리는 즉시 `featureStates` 를 읽어 확정한 뒤 retainer 로 넘어간다.

**이번 실행에서는 §16 지시대로 shared retainer 를 만들지 않고 여기서 멈춘다.**

---

## 2. 다음 단계

1. (rate limit 해제 후) `featureStates` 확인 → §15-10 확정
2. (같은 시점) `#finger_switch_front_lip` 트리 변수를 2.3 으로 동기화하고
   FS 를 `getVariable` 로 복귀 + RETAINER no-op 스텁 4개 삭제 + 피처 이름 정리
3. **I1/I2/I3 공용 후면 retaining plate 설계**
   — 뒷면 사잇각이 34~56° 로 벌어져 평판 불가. **pad 3개를 각각 다른 높이·각도로 설계한 1장** (docs/14 §6-L)
4. I4 별도 소형 retainer
5. INDEX 최종 SUCCESS 후 MIDDLE (free-axis minimax, docs/13 §13-K 규칙)
