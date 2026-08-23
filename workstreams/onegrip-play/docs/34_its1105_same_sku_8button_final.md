# ITS-1105 same-SKU 8-button final implementation

## 결론

- **INDEX = PASS**
- **MIDDLE = PASS**
- **ITS SAME-SKU 8-BUTTON IMPLEMENTATION = PASS**

최종 checkpoint는 `ITS1105_SAME_SKU_8BTN_FINAL`, versionId는
`e05a9ff0fa5a7bd51eb848a7`이다. M4는 `ITS1105_M4_actual`
(`MPFPMgIUS7WLdMWzv`) 한 건만 생성됐고, solid body는 28 → 30으로 증가했다.
추가 body는 독립 spacer `RLVD`와 독립 cap `RPVD`이며 removed body는 없다.

## 1. Hardware 및 공통 정책

| 항목 | 확정값 |
|---|---:|
| SKU | ITS-1105-6mm |
| collision design envelope | 6.18 × 6.12 × 3.56 mm |
| physical nominal | 6.12 × 6.05 × 3.56 mm |
| actuator | Ø3.35 mm, projection 2.44 mm |
| drawing travel | 0.25 ± 0.10 mm |
| pocket | 6.40 × 6.40 mm |
| pocket clearance | X 0.11 / Y 0.14 mm per side |
| terminal policy | fixed root rigid; distal pin one-time forming; direct wiring allowed |

## 2. INDEX final numbers

| gate | 결과 | 판정 |
|---|---:|---|
| minimum body SAT @ 6.18 × 6.12 | **1.213965 mm** | PASS (≥1.20) |
| robustness SAT @ 6.20 × 6.15 | **1.178957 mm** | MARGINAL, non-blocking |
| minimum terminal web, zero-clear channel | 1.712585 mm | — |
| minimum structural terminal web, 0.08 mm/side channel | **1.552585 mm** | PASS (≥1.50) |
| minimum divider | **0.807375 mm** | PASS (≥0.80) |
| minimum split wall | **1.514222 mm** | PASS |
| minimum screw clearance | **2.989336 mm** | PASS (≥2.50) |
| shared retainer service | **2.09 mm** | PASS (≥2.07) |
| I4 service | **1.85 mm** | PASS |

INDEX spacer는 I1/I2/I3 2.4403 mm, I4 2.4400 mm이다. Cap usable travel은
I1 0.383617, I2 0.384256, I3 0.383623, I4 0.399624 mm이며 최소값은
0.383617 mm이다. F2 axis 수정량은 I1~I3 각각 0.407921°이고 I4는 유지했다.

## 3. MIDDLE final layout

| button | center mm | F2 axis | roll |
|---|---|---|---:|
| M1 | (−19.835372, −0.614992, −11.125000) | (−0.837519, −0.499950, −0.220481) | 90° |
| M2 | (−12.899418, −8.744828, −14.125000) | (−0.601521, −0.782846, −0.159135) | 90° |
| M3 | (−3.537874, −14.413709, −11.125000) | (+0.320429, −0.733473, −0.599452) | 0° |
| M4 | (+7.444328, −13.569623, −11.125000) | (+0.224859, −0.772793, −0.593489) | 0° |

| gate | 결과 | 판정 |
|---|---:|---|
| exact 6.18 × 6.12 minimum body SAT | **1.347146 mm** | PASS |
| conservative 6.18 square minimum SAT | **1.301397 mm** | PASS |
| minimum INDEX/retainer clearance | **0.547325 mm** | PASS, collision 0 |
| minimum divider | **1.041660 mm** | PASS |
| minimum terminal web | **1.957425 mm** | PASS |
| minimum split wall | **1.529287 mm** | PASS |
| split support ownership | JfD/M3 0.50, JaD/M4 0.50 mm | PASS |
| minimum screw clearance | **9.234316 mm** | PASS |
| minimum cap pair gap | **2.134043 mm** | continuous row 유지 |
| minimum usable actuator travel | **0.363378 mm** | PASS (≥0.35) |

M1/M2/M3은 JfD, M4는 JaD 소유로 유지된다. 각 feature는 shell-first union,
6.4 mm seat, 8.4 mm opening, rigid-root channel, integrated rear beam/hook,
2.44 mm independent spacer, 8.0 mm independent cap을 구현한다.

## 4. Atomic CAD result

| button | featureId | independent spacer | independent cap |
|---|---|---|---|
| M1 | `MmpBMYK4r3YQubx6n` | `R4PD` (Part 23) | `R8PD` (Part 24) |
| M2 | `Mg4CS9ouVxzcPvhDU` | `RkRD` (Part 25) | `RoRD` (Part 26) |
| M3 | `M5mAoLzCamzWWTulC` | `RaTD` (Part 27) | `ReTD` (Part 28) |
| M4 | `MPFPMgIUS7WLdMWzv` | `RLVD` (Part 29) | `RPVD` (Part 30) |

M4 commit 직전 `ITS1105` 필터 결과는 M1/M2/M3 세 건과 28 parts였고,
commit 직후 M1~M4 네 건과 30 parts였다. 따라서 M4 added solids = 2,
removed solids = 0이며 중복 M4는 없다.

## 5. Global identity / regeneration / assembly

| 항목 | 최종 상태 |
|---|---|
| feature count | 200 |
| solid part count | 30 |
| JaD | 존재, `Joystick_1`, identity 유지 |
| JfD | 존재, `Joystick_2`, identity 유지 |
| RWID | 존재, independent part |
| RZKD | 존재, independent part |
| Part Studio `:errors` | 0 / 200 |
| visible ERROR/WARNING flag | 0 |
| assembly components | 25 |
| assembly visible ERROR/WARNING/dangling flag | 0 |
| dangling references | 0 |

Access-key 일일 할당량이 0이 된 뒤에는 로그인된 Onshape UI를 사용해 최종 감사를
수행했다. Part Studio `:errors` filter, warning/error DOM flag, identity partId,
featureId, solid count, Assembly component count를 직접 읽었다. M4는 Part Studio-only
feature이고 JaD identity가 유지되므로 기존 Assembly reference graph는 변하지 않는다.
M4 전 API 감사의 25/25·dangling 0과 M4 후 UI의 25 components·flag 0이 일치한다.

## 6. Final 30-body inventory

| # | partId | name / role |
|---:|---|---|
| 1 | `JaD` | Joystick_1 / JaD shell |
| 2 | `JfD` | Joystick_2 / JfD shell |
| 3 | `RYDD` | Backplate |
| 4–11 | `RAED`, `RAEH`, `RAEL`, `RBED`, `RBEH`, `RBEL`, `RDED`, `RDEH` | original thumb buttons |
| 12 | `RHED` | Small_joystick_attachment |
| 13–16 | `R4ED`, `R9ED`, `RCFD`, `RHFD` | INDEX caps I1–I4 |
| 17 | `RWID` | shared retainer |
| 18 | `RZKD` | I4 retainer |
| 19–22 | `RmND`, `RqND`, `RuND`, `RyND` | INDEX spacers I1–I4 |
| 23–24 | `R4PD`, `R8PD` | M1 spacer / cap |
| 25–26 | `RkRD`, `RoRD` | M2 spacer / cap |
| 27–28 | `RaTD`, `ReTD` | M3 spacer / cap |
| 29–30 | `RLVD`, `RPVD` | M4 spacer / cap |

## 7. Render

최종 감사 render는 `renders/its1105_same_sku_8button_final.png`이며 1500 × 1125 px,
SHA-256은 `A5705A88DD5A6C522688E2112B975703D18A543BAE467657204D655765CD2388`이다.
마지막으로 확보한 live shell tessellation과 확정 FeatureScript의 M4 positive primitives,
8개 switch/cap/spacer envelope를 동일 좌표계에서 합성한 exploded audit view다.

## Final declaration

**INDEX = PASS**  
**MIDDLE = PASS**  
**ITS SAME-SKU 8-BUTTON IMPLEMENTATION = PASS**
