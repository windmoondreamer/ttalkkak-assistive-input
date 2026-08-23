# MIDDLE center + axis joint optimization — READ-ONLY

- 일자: 2026-08-20
- frozen source: `INDEX_FINAL_VALIDATED` / `03ede76e83b5c865d9a69c35`
- Part Studio: `425d9199b59cfb1efd9ddc35`
- explicit configuration: `default`
- 이전 gate: `docs/27_middle_prewrite_axis_optimization.md`
- **Onshape CAD WRITE: 0건**
- **최종 판정: MIDDLE CAD WRITE = HOLD**

이번 실행은 MIDDLE/INDEX feature, solid, suppression, JaD/JfD를 전혀 변경하지 않았다. frozen
JaD/JfD/RWID/RZKD의 fixed-version tessellation을 로컬에서 읽고 center/axis 후보만 계산했다.

---

## 1. 방법과 판정 범위

1. docs/27 center를 `C0_M1…C0_M4`로 고정했다.
2. `dx=-4…+4`, `dy=-6…+6`, `dz=-8…+2 mm`의 rigid translation 1,287개를
   coarse 검사했다.
3. 각 translation target을 원본 shell 표면에 ray-project하여 다시 착좌시키고 local normal을
   재추출했다.
4. frozen final JaD/JfD에서 원본 shell과 0.05 mm보다 다르게 생긴 실제 INDEX surface
   1,634 triangles를 추출하고, RWID 2,112 / RZKD 628 triangles를 별도로 검사했다.
5. switch, pocket, full-holder 세 envelope 모두 triangle↔OBB full SAT로 관통 0을 요구했다.
6. rigid row 실패 후에만 버튼별 surface-tangent / longitudinal correction을 ±3 mm 안에서 허용했다.
7. 각 고정 center set마다 버튼별 독립 axis 3,000개를 표본화하고, INDEX-safe pool끼리 exact
   M1-M2/M2-M3/M1-M3/M3-M4 SAT 조합을 풀었다.

중요한 한계: Onshape tessellation은 B-rep의 on-demand approximation이다. 따라서 0.1 mm chord
tolerance보다 작은 양의 clearance는 **관통 0인 계산 후보**일 뿐, B-rep 제조 여유로 승인하지
않았다. 이 구분이 최종 HOLD의 핵심이다.

---

## A. nominal centers

| | docs/27 nominal center XYZ (mm) |
|---|---|
| M1 | `(-20.492962, -4.277303, -6.000000)` |
| M2 | `(-15.353762, -13.741645, -6.000000)` |
| M3 | `(-5.465308, -18.285169, -6.000000)` |
| M4 | `(+5.468247, -18.279620, -6.000000)` |

arc pitch intent 11 mm, cap 8 mm, switch 6×6×6 mm, pocket 6.4 mm, ownership JfD 3 + JaD 1은
모든 후속 후보에서 유지했다.

## B. nominal conflict summary

docs/27 재확인:

- local-normal M1-M2: penetration MTD 1.168005 mm
- docs/27 switch-axis 후보 자체는 switch SAT 1.302125 mm로 해결 가능
- 그러나 frozen INDEX에 대해 M2/M3/M4 switch·pocket·holder가 RWID/INDEX holder와 관통
- 따라서 axis-only 해는 불가하고 center 이동이 필요

---

## C. best rigid-row translation

**완전 feasible rigid-row translation은 0 / 1,287개다.**

INDEX 관통이 없었던 후보 중 continuous constraint violation이 가장 작은 것은:

```
Δrigid = (-1.000, +6.000, -8.000) mm
norm(Δ) = 10.049876 mm
```

이 후보는 frozen INDEX 관통은 피하지만 SAT/divider/split/screw/pitch를 동시에 실패한다.
따라서 `best rigid-row`는 **실패 진단 후보**이지 선택 가능한 OPTION이 아니다.

## D. re-seated centers

| | center XYZ (mm) |
|---|---|
| M1 | `(-19.729132, +2.364534, -14.000000)` |
| M2 | `(-15.441006, -6.776894, -14.000000)` |
| M3 | `(-6.314737, -11.776795, -14.000000)` |
| M4 | `(+4.452531, -12.202859, -14.000000)` |

## E. closest transferred axes

완전 constrained four-axis solution은 존재하지 않았다. 아래는 docs/27 tangent offset을 새 local
normal에 옮긴 closest reference다.

| | axis |
|---|---|
| M1 | `(-0.944106, -0.329035, +0.019982)` |
| M2 | `(-0.453776, -0.564159, -0.689791)` |
| M3 | `(-0.124131, -0.624097, -0.771423)` |
| M4 | `(+0.056497, -0.771577, -0.633622)` |

## F. rigid-row minimum SAT

Minimum switch SAT는 **0.187609 mm**로 1.20 mm gate를 실패했다.

## G. rigid-row minimum divider

Minimum divider는 **−0.319969 mm**로 pocket끼리 관통했다.

## H. rigid-row minimum split wall

Minimum split wall은 **0.463284 mm**로 1.50 mm gate를 실패했다.

## I. rigid-row screw clearance

Minimum screw clearance는 **1.960073 mm**로 2.50 mm gate를 실패했다.

## J. rigid-row INDEX clearance

Minimum frozen INDEX clearance는 **0.106553 mm**이고 관통은 없었다. 그러나 위 F–I 및 pitch
gate를 실패하므로 rigid row 전체는 탈락이다.

| gate | result | 판정 |
|---|---:|---|
| **F. minimum switch SAT** | 0.187609 mm | FAIL, <1.20 |
| **G. minimum divider** | −0.319969 mm | FAIL, pocket collision |
| **H. minimum split wall** | 0.463284 mm | FAIL, <1.50 |
| **I. minimum screw clearance** | 1.960073 mm | FAIL, <2.50 |
| pitch | 10.097 / 10.406 / 10.776 mm | FAIL, first two <10.5 |
| **J. INDEX minimum clearance** | 0.106553 mm, M4 holder→frozen shell INDEX surface | no collision |
| external cap footprint SAT | minimum 1.726510 mm | no collision |

결론: **rigid translation만으로는 해가 없다.**

---

## K. individual-correction optimum — OPTION A

OPTION A는 이번 표본 탐색에서 **row translation norm이 가장 작은 fully gated 후보**다.

```
common Δrow                = (0.000, +3.000, -4.250) mm
surface tangent correction = (-0.9, -0.3, +0.3, +0.9) mm
longitudinal/Z correction   = ( 0.0, -3.0, -0.75, -0.75) mm
```

### centers and axes

| | center XYZ (mm) | optimized axis | normal dev |
|---|---|---|---:|
| M1 | `(-20.130463, -0.140233, -10.250000)` | `(-0.722496, -0.631632, -0.281140)` | **27.2129°** |
| M2 | `(-14.012971, -8.589166, -13.250000)` | `(-0.531598, -0.829804, -0.169789)` | 23.1158° |
| M3 | `(-4.938064, -14.285897, -11.000000)` | `(+0.296261, -0.712888, -0.635625)` | 25.8258° |
| M4 | `(+6.085614, -14.038194, -11.000000)` | `(+0.091818, -0.830854, -0.548864)` | 6.7761° |

## L. per-button displacement

| | 3-D displacement from C0 |
|---|---:|
| M1 | 5.942 mm |
| M2 | **8.995 mm** |
| M3 | 6.424 mm |
| M4 | 6.586 mm |

OPTION A gates:

- pitch 10.854 / 10.948 / 11.026 mm
- switch SAT minimum 1.424787 mm
- divider minimum 0.968959 mm
- split wall minimum 1.656153 mm
- screw minimum 7.888408 mm
- cap footprint minimum gap 2.057564 mm
- switch/pocket/holder INDEX intersection 0
- **INDEX minimum clearance 0.006362 mm**, M4 holder→frozen shell INDEX surface

수학적 관통 0은 통과하지만 0.006 mm는 0.1 mm tessellation chord보다 작고, front lip도
0.506594 mm로 0.5 mm gate 바로 위다. **최소 이동 경계 후보이지 CAD 승인 후보가 아니다.**

---

## M. Z≈−14 fallback — OPTION C

docs/27의 단순 `ΔZ=-8`은 표면에 re-seat하면 X/Y가 안쪽으로 수축하여 pitch가
8.557…8.718 mm로 줄고, M3 holder도 INDEX와 충돌했다. 즉 **순수 vertical Z=-14 baseline은
feasible하지 않다.**

Z≈−14를 유지하면서 모든 gate를 통과한 corrected fallback은:

```
common Δrow                = (+1.000, +5.500, -8.000) mm
surface tangent correction = (-0.9, -0.3, +0.3, +0.9) mm
longitudinal/Z correction   = ( 0.0, -3.0,  0.0,  0.0) mm
```

| | center XYZ (mm) | optimized axis | normal dev |
|---|---|---|---:|
| M1 | `(-19.695276, +2.095703, -14.000000)` | `(-0.845595, -0.464153, -0.263687)` | 21.4678° |
| M2 | `(-13.343375, -6.388912, -17.000000)` | `(-0.686763, -0.709063, -0.159957)` | 20.1434° |
| M3 | `(-4.057348, -12.274989, -14.000000)` | `(+0.206506, -0.742928, -0.636720)` | **21.6830°** |
| M4 | `(+7.053029, -11.564704, -14.000000)` | `(+0.177414, -0.815799, -0.550451)` | 3.4403° |

| gate | result |
|---|---:|
| row translation norm | **9.759611 mm** |
| per-button displacement | 10.259 / **13.383** / 10.105 / 10.564 mm |
| pitch | 11.015 / 11.396 / 11.133 mm |
| minimum switch SAT | 1.389606 mm |
| minimum divider | 0.931447 mm |
| minimum split wall | 1.511535 mm |
| minimum screw clearance | 3.271212 mm |
| minimum cap footprint gap | 2.229832 mm |
| minimum frozen INDEX clearance | **0.783400 mm**, M4 holder→INDEX shell surface |
| INDEX intersections | 0 |

OPTION C는 세 옵션 중 INDEX clearance가 유일하게 tessellation chord보다 충분히 크지만, row 이동
9.76 mm와 M2 개별 13.38 mm가 발생한다. guaranteed-clear reference로는 유효하나 ergonomic
승인 없이 바로 채택할 수 없다.

---

## N. INDEX ↔ MIDDLE ergonomic row spacing

geodesic은 원본 shell tessellation edge graph의 shortest path 근사다. coarse tessellation vertex
snap error가 최대 약 2.2 mm이므로 순위/규모 판단용이며 B-rep exact geodesic은 아니다.

### nominal C0

| pair | 3-D center | surface geodesic | Z difference | XY tangential chord |
|---|---:|---:|---:|---:|
| I1↔M1 | 20.067 | 20.604 | −15.000 | 13.330 |
| I2↔M2 | 19.514 | 18.066 | −15.000 | 12.482 |
| I3↔M3 | 18.625 | 16.781 | −15.000 | 11.040 |
| I4↔M4 | 18.628 | 17.666 | −15.000 | 11.045 |

### OPTION A

| pair | 3-D center | surface geodesic | Z difference | XY tangential chord |
|---|---:|---:|---:|---:|
| I1↔M1 | 26.002 | 26.194 | −19.250 | 17.480 |
| I2↔M2 | **28.448** | 28.562 | **−22.250** | 17.727 |
| I3↔M3 | 25.030 | 26.638 | −20.000 | 15.049 |
| I4↔M4 | 25.180 | 24.972 | −20.000 | 15.298 |

### OPTION B

| pair | 3-D center | surface geodesic | Z difference | XY tangential chord |
|---|---:|---:|---:|---:|
| I1↔M1 | 27.907 | 29.276 | −21.000 | 18.379 |
| I2↔M2 | **30.455** | 29.120 | **−24.000** | 18.748 |
| I3↔M3 | 26.253 | 26.638 | −21.000 | 15.755 |
| I4↔M4 | 26.538 | 28.252 | −21.000 | 16.225 |

### OPTION C

| pair | 3-D center | surface geodesic | Z difference | XY tangential chord |
|---|---:|---:|---:|---:|
| I1↔M1 | 30.318 | 29.276 | −23.000 | 19.752 |
| I2↔M2 | **32.798** | 32.443 | **−26.000** | 19.992 |
| I3↔M3 | 28.667 | 30.417 | −23.000 | 17.111 |
| I4↔M4 | 29.101 | 29.036 | −23.000 | 17.828 |

OPTION A도 nominal 대비 같은 손가락 pair의 3-D row spacing이 약 5.9…8.9 mm 늘어난다.
OPTION C는 약 10.5…13.3 mm 늘어난다. 따라서 C의 큰 이동은 형상 여유는 설명하지만 ergonomic
justification은 제공하지 못한다.

---

## O. OPTION A/B/C comparison

| | **A — minimum geometry displacement** | **B — minimum axis deviation** | **C — Z≈−14 robust fallback** |
|---|---:|---:|---:|
| common translation | `(0,+3,-4.25)` | `(+0.5,+4,-6)` | `(+1,+5.5,-8)` |
| translation norm | **5.202** | 7.228 | 9.760 |
| max per-button displacement | 8.995 | 11.029 | 13.383 |
| max axis deviation | 27.213° | **20.785°** | 21.683° |
| pitch min/max | 10.854 / 11.026 | 10.863 / 11.306 | 11.015 / 11.396 |
| minimum switch SAT | 1.425 | 1.312 | 1.390 |
| minimum divider | 0.969 | 0.842 | 0.931 |
| minimum split wall | 1.656 | 1.623 | 1.512 |
| minimum screw | 7.888 | 5.143 | 3.271 |
| minimum cap footprint gap | 2.058 | 2.176 | 2.230 |
| switch/pocket/holder INDEX collision | 0 | 0 | 0 |
| minimum INDEX clearance | **0.006** | **0.015** | **0.783** |
| analytical hard gates | PASS | PASS | PASS |
| robustness / ergonomics | clearance 불충분 | clearance 불충분 | 이동량 과다 |

모든 값은 mm(각도 제외)다.

---

## P. recommended option

**형상 탐색의 추천 방향은 OPTION B**다.

이유:

- common translation norm 7.228 mm로 8 mm 아래
- 최대 axis deviation 20.785°로 A보다 6.43° 작음
- switch/pocket는 frozen INDEX에서 3.088 mm 이상 떨어짐
- divider, split, screw, cap gate 통과

단 M3/M4 **full holder**가 frozen INDEX surface에서 0.077 / 0.015 mm에 불과하다. B를 그대로
CAD에 쓰라는 승인이 아니라, 다음 exact B-rep/ergonomic 검증을 위한 선행 후보로 추천한다.

OPTION A는 이동이 가장 작지만 clearance 0.006 mm와 lip 0.507 mm로 이중 경계다. OPTION C는
형상적으로 가장 robust하지만 row spacing 증가가 크다.

---

## Q. 6×6×6 switch maintainability

**계산상 유지 가능 = YES, CAD 승인 = 아직 NO.**

A/B/C 모두 nominal 6×6×6 switch와 6.4 pocket로 analytical hard gate를 통과했다. 따라서 현
단계에서 6×6×6 hardware를 폐기할 근거는 없다. 다만 신뢰 가능한 frozen-INDEX 여유를 확보한
C는 common row 이동이 9.76 mm이므로, 6×6×6을 유지할 때 생기는 ergonomic cost가 크다.

---

## R. hardware fallback necessity

**CONDITIONAL — 즉시 필수는 아니며 병렬 검토 권장.**

- A/B가 exact B-rep에서도 양의 실질 clearance를 확보하면 low-profile fallback은 불필요
- A/B가 B-rep에서 관통으로 뒤집히면 robust 6×6×6 해는 C처럼 약 8 mm 이상 이동하므로
  MIDDLE 전용 low-body-height switch/mechanism fallback 검토가 필요
- 이번 실행에서는 신규 SKU를 선정하지 않았다

---

## S. FINAL GATE

## **MIDDLE CAD WRITE = HOLD**

HOLD 사유:

1. rigid-row 해가 없다.
2. 최소 이동 A와 최소 axis deviation B의 full-holder INDEX clearance가 0.006 / 0.015 mm로
   0.1 mm tessellation chord보다 작아 B-rep identity/clearance gate로 확정할 수 없다.
3. robust C는 common translation 9.76 mm, M2 displacement 13.38 mm이며 I2↔M2 spacing이
   32.80 mm까지 증가한다. 이는 ergonomic approval 없는 큰 layout 변경이다.

INDEX geometry 변경은 필요하지 않았고 수행하지 않았다. original thumb geometry도 변경하지
않았다. 다음 승인은 `OPTION B exact B-rep clearance + ergonomic review` 또는 hardware fallback
비교 중 하나가 선행되어야 한다.

---

## 재현 파일

- `scripts/extract_index_shell_keepout.py`
- `scripts/search_middle_joint.py`
- `scripts/optimize_middle_axes_at_rows.py`
- `scripts/evaluate_middle_joint_options.py`
- `cad_dump/middle_center_axis_joint_optimization.json`
- `cad_dump/middle_joint_rigid_coarse.json`
- `cad_dump/middle_joint_axis_rows_fine_v2.json`
- `cad_dump/middle_joint_axis_rows_deep_v3.json`

INDEX_FINAL_VALIDATED는 계속 FREEZE 상태다. 이번 실행으로 regeneration/assembly 상태는 변하지
않았으며 Onshape CAD WRITE는 0건이다.
