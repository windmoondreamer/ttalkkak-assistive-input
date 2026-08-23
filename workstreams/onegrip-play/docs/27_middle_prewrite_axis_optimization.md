# MIDDLE pre-write axis optimization — READ-ONLY gate

- 일자: 2026-08-20
- frozen source: `INDEX_FINAL_VALIDATED` / `03ede76e83b5c865d9a69c35`
- Part Studio: `425d9199b59cfb1efd9ddc35`
- explicit configuration: `default`
- 기준: `docs/26_index_final_geometry_identity_audit.md`
- **Onshape CAD WRITE: 0건**
- **결론: MIDDLE CAD WRITE = HOLD**

이번 실행은 MIDDLE feature/solid를 생성·수정·삭제·suppress하지 않았다. 확정 version의
JaD/JfD/RWID/RZKD는 동일 tolerance와 `configuration=default`로 **GET만** 수행해 로컬에
캐시했다. 축·OBB·간섭 계산과 이 문서 작성만 로컬에서 수행했다.

---

## 1. 계산 기준

| 항목 | 기준 |
|---|---|
| center/normal source | pre-opening `Joystick_1_baseline` + `Joystick_2_baseline` tessellation |
| final surface cross-check | frozen final JaD/JfD에서 center/normal을 재추출해 소수 9자리까지 동일 확인 |
| row | `Z=-6.000 mm`, arc `s=-27.5/-16.5/-5.5/+5.5 mm` |
| nominal switch | 6.0 × 6.0 × 6.0 mm OBB |
| pocket | 6.4 × 6.4 mm, switch body를 포함하는 6.2 mm 길이 OBB |
| switch collision | full 15-axis OBB SAT; vertex/corner/nearest-point 판정 미사용 |
| INDEX retainer collision | frozen RWID/RZKD triangle ↔ OBB full SAT |
| optimization | M1~M4 각각 독립 2-DOF unit axis, 최대 normal deviation minimax |
| holder proxy | 12.4 mm 폭, axis depth 2.8…12.5 mm short-holder blank |

Onshape tessellation은 B-rep의 on-demand approximation이므로 raw hash를 identity gate로 쓰지
않았다. 다만 여기서는 동일 고정 tolerance의 실제 표면 좌표와 triangle/OBB 관통을 geometric
sanity 및 pre-write collision gate로 사용했다. 아래 HOLD는 0에 가까운 거리 오차가 아니라
nominal switch/pocket이 RWID와 다수 triangle에서 관통하는 결과다.

---

## 2. A–E. MIDDLE center와 local surface normal

arc pitch는 정확히 11.000 mm다. 곡면 위 chord distance가 약간 짧은 것은 정상이며 center
추가 이동은 적용하지 않았다.

| | center XYZ (mm) | local outward normal `n0` | 이웃 chord (mm) |
|---|---|---|---:|
| **A. M1** | `(-20.492962, -4.277303, -6.000000)` | `(-0.940551, -0.200970, -0.273817)` | M1-M2 10.769641 |
| **B. M2** | `(-15.353762, -13.741645, -6.000000)` | `(-0.512716, -0.640584, -0.571642)` | M2-M3 10.882331 |
| **C. M3** | `(-5.465308, -18.285169, -6.000000)` | `(-0.143459, -0.756558, -0.637997)` | M3-M4 10.933556 |
| **D. M4** | `(+5.468247, -18.279620, -6.000000)` | `(+0.133638, -0.758123, -0.638271)` | — |

**E. local normals**는 위 표와 같다. final switch axis로 고정하지 않고 초기 reference로만 썼다.
M1/M2/M3 center는 X<0(JfD), M4는 X>0(JaD)라 3+1 center ownership은 유지된다.

`Z=-6`은 원본 쉘의 finger-rest 표면·내부 깊이 관점에서는 성립하지만, §8의 frozen INDEX
충돌 때문에 **최종 CAD row height로 승인할 수 없다.**

---

## 3. F. local-normal baseline exact SAT

baseline은 기존 reference와 같은 front depth 3.8 mm(벽 3.0 + lip 0.8)다.

| pair | signed SAT (mm) | 판정 |
|---|---:|---|
| **M1-M2** | **−1.168005** | **COLLISION**, penetration MTD 1.168005 |
| **M2-M3** | +0.559661 | 분리지만 1.20 미달 |
| M1-M3 | +5.060403 | 분리 |
| M3-M4 | +1.613546 | 분리 |

따라서 `local normal = final axis`는 재사용할 수 없다. 이전 예비 감사의 M1-M2 collision 및
M2-M3 작은 여유를 독립 재현했다.

---

## 4. G–K. free-axis minimax 후보

아래 축은 center 고정 상태에서 switch SAT, pocket divider, split wall, front lip을 동시에 넣어
구한 **switch-row 기하 후보**다. §8 INDEX gate에서 탈락하므로 CAD-authorized axis가 아니다.

| | optimized axis | normal deviation |
|---|---|---:|
| **G. M1** | `(-0.910729, -0.407794, -0.065396)` | 16.971996° |
| **H. M2** | `(-0.322354, -0.543351, -0.775150)` | **16.972295°** |
| **I. M3** | `(-0.047755, -0.555011, -0.830471)` | 16.944658° |
| **J. M4** | `(+0.040212, -0.712450, -0.700570)` | 6.949938° |

**K. maximum normal deviation = 16.972295°** (M2).

uniform interpolation `t`는 사용하지 않았다. 각 axis의 X/Y/Z 성분을 독립적으로 풀었으며,
center correction은 0.000 mm다.

---

## 5. L. optimized nominal switch SAT

front depth 5.3 mm(권장 nominal lip 2.3 mm)에서의 full 15-axis SAT다.

| pair | SAT separation (mm) | exact Euclidean OBB gap (mm) | gate |
|---|---:|---:|---|
| M1-M2 | +1.351408 | 1.359956 | PASS |
| **M2-M3** | **+1.302125** | 1.302125 | **minimum / PASS** |
| M1-M3 | +7.913090 | 7.913095 | PASS |
| M3-M4 | +3.725090 | 3.725090 | PASS |

switch-only 최소 SAT는 **1.302125 mm ≥ 1.20 mm**다.

---

## 6. M. actual pocket-divider prediction

| pair | pocket SAT (mm) | Euclidean gap (mm) | 판정 |
|---|---:|---:|---|
| **M1-M2** | **0.800820** | 0.806663 | PASS, 경계 여유 +0.000820 |
| M2-M3 | 0.801391 | 0.801391 | PASS, 경계 여유 +0.001391 |
| M3-M4 | 3.290341 | 3.290341 | PASS |

minimum predicted divider = **0.800820 mm**. 절대 기준 0.80은 통과하지만 목표 `>1.0 mm`는
M1-M2와 M2-M3에서 달성하지 못한다. 최종 CAD 전에 B-rep 재검증이 필요한 경계값이다.

`CLEARNBR` 분석:

| pair | holder ↔ neighbor pocket | 계획 |
|---|---|---|
| M1-M2 | 양방향 overlap | **CLEARNBR 필수** |
| M2-M3 | 양방향 overlap | **CLEARNBR 필수** |
| M3-M4 | 0.044 / 0.264 mm 분리 | nominal상 불필요, 생성 후 재측정 |

CLEARNBR는 future MIDDLE holder body에서 neighbor seat/pocket/bore envelope를 빼고 나서 shell에
union하는 순서여야 한다. RWID 자체를 빼거나 수정하는 용도로 사용할 수는 없다.

---

## 7. N–O. split ownership과 screw clearance

### N. split ownership prediction

| | pocket split-side coordinate | wall to X=0 | gate |
|---|---:|---:|---|
| M3 / JfD | maxX = −1.500093 | **1.500093 mm** | PASS |
| M4 / JaD | minX = +1.684563 | **1.684563 mm** | PASS |

nominal pocket는 반대 shell을 침범하지 않는다. 12.4 mm holder blank는 별도 `holder-only
split clip`이 필요하며 shell을 clip target으로 쓰지 않는다.

### O. existing screw minimum 3-D clearance

유한 X-axis screw envelope(반경 3.5 mm, X −6…+10)와 full holder OBB를 계산했다.

| button | nearest screw | clearance (mm) |
|---|---|---:|
| **M1** | C | **11.034048** |
| M2 | B | 12.156913 |
| M3 | B | 11.860997 |
| M4 | B | 12.393443 |

global minimum = **11.034048 mm ≥ 2.50 mm**, PASS다.

---

## 8. P. frozen INDEX geometry clearance — **FAIL / STOP**

### 8.1 selected switch-row 후보의 실제 frozen-part clearance

| | switch → RWID | pocket → RWID | holder → RWID | holder → RZKD | pocket → INDEX holder |
|---|---:|---:|---:|---:|---:|
| M1 | 6.206 | 6.005 | 2.983 | 15.035 | 7.201 |
| **M2** | **0 / collision** | **0 / collision** | **0 / collision** | 10.897 | **0 / collision** |
| **M3** | **0 / collision** | **0 / collision** | **0 / collision** | 2.705 | 0.094 |
| **M4** | **0 / collision** | **0 / collision** | **0 / collision** | 0.648 | 2.313 |

RWID triangle ↔ 6.4 pocket exact intersection triangle 수는 M2 **22**, M3 **417**, M4 **20**다.
즉 raw tessellation의 1점 접촉이나 tolerance 경계가 아니라 nominal switch/pocket 자체의
명확한 관통이다. M2는 frozen INDEX holder와도 nominal pocket가 관통한다.

따라서 positive holder를 얇게 깎거나 MIDDLE CLEARNBR를 추가하는 것으로 해결할 수 없다.
**6×6×6 switch와 6.4 pocket가 별도 독립 부품 RWID를 이미 침범**하기 때문이다.

### 8.2 fixed-center escape probe

각 버튼을 다른 MIDDLE pair 제약 없이 개별적으로만 놓고, normal에서 0…70° 범위 axis 5,000개를
검사했다.

| | INDEX-safe pocket 최소 sampled deviation | INDEX-safe full holder samples |
|---|---:|---:|
| M1 | 0.003° | 1,091 / 5,000 |
| M2 | 0.001° | **0 / 5,000** |
| M3 | **23.493°** | **0 / 5,000** |
| M4 | 9.983° | **0 / 5,000** |

이 표는 전역 불가능성의 수학적 증명은 아니지만, pair SAT를 넣기 전에도 M2/M3/M4 full holder가
fixed center에서 성립하지 않는다는 강한 진단이다. 특히 M3 pocket만 피하는 데도 sampled lower
bound가 23.493°다.

현재 후보를 유지한 uniform −Z probe에서는 full holder 4개가 RWID/INDEX holder에서 모두
분리되는 첫 1 mm 격자값이 **ΔZ=−8 mm**, 즉 row `Z≈−14 mm`다. `Z≈−6`에서 8 mm 이동은
미세 center correction이 아니라 **큰 layout 변경**이므로 이번 지시의 STOP 조건에 해당한다.

### 8.3 original thumb geometry

full holder와 원본 엄지 부품의 최소 거리는 M2→Backplate **22.811 mm**다. original thumb
geometry는 차단 원인이 아니며 수정할 필요도 없다.

---

## 9. Q. holder feasibility

frozen INDEX를 잠시 제외한 원본 쉘 공간만 보면 short-holder architecture는 충분하다.

| | wall along proposed axis | next shell obstruction depth | wall 뒤 가용 | rear-axis open | stem/opening conservative clearance |
|---|---:|---:|---:|---:|---:|
| M1 | 3.133 | 42.251 | 39.118 | 29.761 | 1.648 |
| M2 | 3.168 | 42.810 | 39.642 | 30.320 | 1.648 |
| M3 | 3.146 | 44.303 | 41.157 | 31.813 | 1.648 |
| M4 | 3.027 | 42.710 | 39.683 | 30.220 | 1.733 |

- front opening / 6.4 seat / rear open cavity / stem bore: shell-only 기준 PASS
- cap travel lateral offset: 최대 `0.25 sin(16.972°)=0.0730 mm`, nominal 0.20 mm 안
- wiring exit: rear-axis open distance 29.8 mm 이상
- screw: §7 PASS
- M1-M2 / M2-M3: CLEARNBR 필수
- deep tube / global trough: 사용하지 않음
- intended future sequence: short seat → open rear → separate NEW BODY → CLEARNBR → holder-only
  split clip → `qUnion([EXISTING_SHELL_TARGET_FIRST, NEW_HOLDER_SECOND])`

그러나 실제 full system에서는 M2/M3/M4 switch/pocket가 frozen RWID/INDEX holder와 충돌한다.
따라서 **actual holder feasibility = FAIL**이다. INDEX geometry나 JaD/JfD identity를 수정하는
우회는 허용되지 않으며 수행하지 않았다.

---

## 10. R. recommended front lip

조건부 추천 nominal front lip은 **2.3 mm**다.

| nominal lip | 결과 |
|---:|---|
| 0.8 mm | 동시 제약 해 없음; actual lip 최소 −0.039 mm |
| 1.5 mm | divider/split/actual-lip가 각각 약 0.002 mm 경계 미달 |
| **2.3 mm** | switch SAT 1.302+, divider 0.8008+, split wall 1.5001+, actual lip 1.031+ |

2.3 mm 적용 시 switch front depth는 5.3 mm이고, 버튼별 실제 최소 lip은
M1 1.031 / M2 1.121 / M3 1.193 / M4 1.949 mm다. 단, 이는 §8 충돌이 해결된 새 layout에서
다시 최적화·검증해야 할 provisional 값이며 CAD 입력 승인값이 아니다.

---

## 11. S. FINAL PRE-WRITE GATE

| gate | 결과 |
|---|---|
| center continuity / nominal arc pitch | PASS |
| local-normal baseline | FAIL → free-axis 필요 확인 |
| optimized switch SAT ≥1.20 | PASS, 1.302125 |
| predicted divider ≥0.80 | PASS, 0.800820 |
| 3+1 pocket ownership | PASS |
| split-side wall ≥1.5 | PASS |
| screw clearance ≥2.50 | PASS, 11.034048 |
| original thumb clearance | PASS, 22.811+ |
| **frozen INDEX holder/RWID collision** | **FAIL — M2/M3/M4** |
| pitch/layout 큰 변경 불필요 | **FAIL — 현 후보는 약 −8 mm row shift 필요** |
| INDEX modification needed/performed | **금지 / 0건** |

## **MIDDLE CAD WRITE = HOLD**

HOLD 원인은 단 하나로 충분하다: `Z=-6` fixed-center 후보의 M2/M3/M4 nominal switch/pocket가
frozen INDEX RWID/holder와 충돌한다. 이는 stop condition의 `INDEX geometry와 충돌 금지` 및
`큰 layout 변경 필요`에 해당한다.

INDEX, original thumb, JaD, JfD는 수정하지 않았다. 새로운 MIDDLE layout 방향을 승인받기 전까지
FeatureScript/feature/solid를 만들지 않는다.

---

## 12. 재현 파일

- `scripts/fetch_index_final_meshes.py` — fixed version + explicit configuration GET-only cache
- `scripts/analyze_middle_prewrite.py` — center/normal, SAT, free-axis, holder/clearance 계산
- `scripts/probe_middle_index_conflict.py` — frozen INDEX conflict 및 −Z probe
- `cad_dump/middle_prewrite_axis_optimization.json` — 주 계산 데이터
- `cad_dump/middle_index_conflict_probe.json` — INDEX conflict 데이터

현재 frozen INDEX 상태는 docs/26 그대로다: ERROR 0 / WARNING 0 / assembly 25/25 / dangling 0.
이번 실행은 CAD WRITE 0건이므로 regeneration·assembly 상태 변화도 0건이다.
