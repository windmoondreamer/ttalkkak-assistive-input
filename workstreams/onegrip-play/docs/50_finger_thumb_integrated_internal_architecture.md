# OneGrip Play — Finger + lowered Thumb 통합 내부구조 V3

## 1. 최종 결론

LOCAL build123d + OCCT에서 승인된 Finger 8-button 외부 배열과 lowered thumb
rigid cluster를 그대로 유지한 통합 내부구조를 실제 B-rep으로 작성하고 검증했다.

- `FINGER EXTERNAL LAYOUT = PRESERVED`
- `THUMB EXTERNAL LAYOUT = PRESERVED`
- `LOCAL INTEGRATED V3 = PASS`
- Onshape API/browser/CAD write: **0**
- production Finger V2 overwrite: **0**
- physical validation kit 변경: **0**

이번 PASS는 production freeze 또는 실물 출력 PASS가 아니다. 다음 단계는 Finger와
lowered Thumb를 함께 포함한 **통합 functional validation section**의 FDM 시험이다.

## 2. 작업 경계와 exact source

| 항목 | 결과 |
|---|---|
| geometry kernel | build123d + OCCT exact B-rep |
| source file | `build123d_workbench/finger_thumb_integrated_v3.py` |
| render file | `build123d_workbench/render_finger_thumb_integrated_v3.py` |
| validation | `build123d_workbench/out/finger_thumb_integrated_v3/finger_thumb_integrated_v3_validation.json` |
| JaD source | immutable `JAD_FINGER_V2.step` |
| JfD source | immutable `JFD_FINGER_V2.step` |
| thumb source | exact `THUMB_TARGET_EXACT_MODULE.step` |
| Onshape access | API 0 / browser 0 / write 0 |

Combined model에는 clean JaD/JfD, frozen Finger caps, ITS-1105 ×8, exact lowered
thumb module, carrier 6개, Finger/Thumb wiring envelope, split thumb seat, 신규 screw
3개와 boss 6개가 동시에 들어간다.

## 3. Hard-freeze 확인

| 항목 | 결과 |
|---|---:|
| thumb translation | `(0.000,+12.250,-21.000) mm` |
| I2/I3/I4 center movement | 각 `0.000 mm` |
| M3/M4 center movement | 각 `0.000 mm` |
| N1/N2/N3 center movement | 각 `0.000 mm` |
| Finger cap size/exposure change | 없음 |
| thumb relative geometry/scale/orientation change | 없음 |
| maximum Finger switch axis adjustment | `0.000°` |

외부 center를 내부 구조에 맞춰 이동하지 않았다. 낮아진 thumb interface를 위해
변경한 것은 shell의 국부 내부 개구, seat, boss와 배선 경로뿐이다.

## 4. 최종 carrier grouping

총 carrier service part 수는 **6개**다.

1. `N1_N2_V3_shared_front_carrier`
2. `N1_N2_V3_rear_restraint`
3. `I2_I3_shared_carrier`
4. `M4_N3_shared_carrier`
5. `I4_carrier`
6. `M3_carrier`

Part count 감소 자체를 목표로 복잡한 일체형 carrier를 만들지 않았다. 같은 insertion
direction과 shell ownership을 갖는 N1/N2만 새 shared front seat로 묶고, rear
restraint는 별도 분리해 pre-wire와 switch 교체가 가능하게 했다. 나머지 네 그룹은
검증된 Finger V2 carrier STEP를 immutable import했다.

모든 carrier는 valid single solid이며 small solid 또는 tangent-only bridge가 없다.

## 5. N1 내부구조

N1/N2 공통 구조는 다음 순서로 switch를 잡는다.

`frozen cap → front ring → ITS-1105 body → removable central rear restraint`

- N front depth: `1.20 mm`
- front ring reference depth: `2.02 mm`
- switch pocket: `6.40 × 6.40 mm`
- carrier wall: `1.60 mm`
- rear restraint thickness: `1.60 mm`
- front/rear positive bridge: `2.40 mm`
- switch axis adjustment: `0.00°`

Fixed terminal root는 rigid envelope로 보존했다. 그 이후 lead만 바깥쪽으로 한 번
성형하고 solder envelope를 거쳐 아래쪽 shared corridor로 보낸다.

| N1 check | exact result |
|---|---:|
| hard geometry ↔ thumb | `1.421369850 mm`, penetration 0 |
| wiring ↔ thumb | `2.123227103 mm`, penetration 0 |
| N1 ↔ N2 switch | `4.637978454 mm` |
| switch-switch global minimum | `1.358718942 mm` |

`N1 INTERNAL = PASS`

## 6. N2 seam 구조

JfD를 locating shell로 사용하고 JaD는 clearance/capture만 담당한다. N2 cap과
switch center는 이동하지 않았으며, JaD closure가 rear restraint와 front carrier를
잡되 switch 위치를 결정하지 않게 했다.

| N2 check | exact result |
|---|---:|
| hard geometry ↔ thumb | `1.485253666 mm`, penetration 0 |
| wiring ↔ thumb | `2.191216898 mm`, penetration 0 |
| front carrier ↔ opposite JaD | `1.054170903 mm`, penetration 0 |
| rear restraint ↔ complete shell | `0.924696092 mm`, penetration 0 |
| cap center movement | `0.000 mm` |

이전 `0.204599960 mm` opposite-shell 상태를 폐기했고 practical `0.80 mm` gate를
넘겼다. `N2 SEAM = PASS`다.

## 7. Lowered thumb seating과 shell interface

원본 button/joystick cluster는 exact rigid module로 유지했다. 새로운 내부 interface는
다음으로 구성된다.

- split continuous flange: `1.60 mm`
- outer frame: `42 × 64 mm`
- inner frame: `34 × 56 mm`
- conformal pad 3개
- pad size: `5.0 mm`
- pad reach: `4.8 mm`
- local mechanism relief: `0.80 mm`
- shell closing으로 anti-rotation/capture

Full seat는 valid single solid다. 가장 작은 arm/pad positive connection volume은
`12.671999049 mm³`다.

| Seat connection | positive overlap |
|---|---:|
| JaD seat ↔ shell | `126.491297755 mm³` |
| JfD seat ↔ shell | `176.483200927 mm³` |

두 번째 `HW504_B`가 lowered 위치에서 shell 내부 모서리와 겹치던 원래 부피는
JaD `33.838519636 mm³`, JfD `59.349547098 mm³`였다. 각 exact 교차 B-rep의
bounding region에만 `0.80 mm` 국부 relief를 적용해 최종 thumb↔shell penetration을
`0.000000000 mm³`로 만들었다.

Visual QC 과정에서 다음 두 방식은 폐기했다.

- 38 mm full-depth continuous cavity: 반대쪽 외피까지 큰 가로 service window를
  만들어 외관 보존 취지에 맞지 않았다.
- HW504 exact-tooth sweep relief: JaD 31 solids / JfD 59 solids를 만들어 fragment
  gate를 위반했다.

최종 방식은 shell single-solid를 유지하는 단순한 국부 relief다. Backplate와 seat의
의도된 접면 때문에 minimum distance는 `0`이지만 exact penetration과 intersecting
pair는 모두 `0`이다.

`THUMB SEATING = PASS`

## 8. Fastening candidate 비교

모든 후보는 M3 class envelope와 +X driver axis를 사용했다.

| Option | 개념 | screw↔thumb | screw↔Finger | boss↔thumb | boss↔Finger | 판정 |
|---|---|---:|---:|---:|---:|---|
| A | 기존 screw 일부 최소 relocate | 6.551192 | 3.168115 | 4.687469 | 1.244774 | Finger 인접 boss 여유가 작고 비대칭 |
| B | thumb dedicated + shell 분리 | 4.634298 | 17.912674 | 1.584298 | 14.822382 | boss↔thumb 2.0 mm practical gate 미달 |
| C | posterior redistributed 3-point | 5.349360 | 17.912674 | 3.499360 | 14.822382 | **선택** |

단위는 mm다. Option C는 최소 여유, shell clamp 삼각형, driver 접근과 service order가
가장 균형적이라 선택했다.

### 선택한 screw 위치와 축

| Screw | Y mm | Z mm | axis |
|---|---:|---:|---|
| 1 | `10.00` | `35.00` | `+X` |
| 2 | `25.00` | `8.00` | `+X` |
| 3 | `15.80` | `-21.35` | `+X` |

- boss outer radius: `4.60 mm`
- driver radius: `2.80 mm`
- minimum boss radial wall: `1.80 mm`
- supporting web: `3.20 mm`
- tangent-only boss: 0
- minimum boss-to-shell positive overlap: `94.999545414 mm³`

`NEW FASTENING = PASS`

## 9. Wiring architecture

N1/N2는 다음 연속 topology를 사용한다.

`fixed terminal root → one-time outward formed lead → solder envelope → insulated wire → downward shared corridor`

나머지 Finger wiring은 기존 carrier와 함께 아래로 보내고, thumb bundle은 posterior
corridor로 별도 하강시킨다. Shell을 닫을 때 두 bundle을 screw axis 사이에 둬 pinch를
피한다.

| Wiring clearance | exact minimum |
|---|---:|
| Finger wiring ↔ thumb | `2.123227103 mm` |
| N1 wiring ↔ thumb | `2.123227103 mm` |
| N2 wiring ↔ thumb | `2.191216898 mm` |
| Finger wiring ↔ new screw | `18.950468390 mm` |
| Finger wiring ↔ new boss | `15.900468390 mm` |
| Thumb wiring ↔ new screw | `11.481327086 mm` |
| Thumb wiring ↔ new boss | `10.049027150 mm` |
| Thumb wiring ↔ Finger wiring | `20.046229948 mm` |

모든 critical service/wiring clearance는 `0.80 mm` gate를 넘는다.

`WIRING = PASS`

## 10. 전체 exact clearance matrix

| Pair | minimum clearance mm | penetration mm³ |
|---|---:|---:|
| switch ↔ switch | `1.358718942` | `0` |
| Finger switch bodies ↔ thumb | `3.188412035` | `0` |
| Finger carriers ↔ thumb | `1.714770848` | `0` |
| Finger wiring ↔ thumb | `2.123227103` | `0` |
| thumb ↔ new screws | `5.349359580` | `0` |
| thumb ↔ new bosses | `3.499359580` | `0` |
| Finger hard geometry ↔ new screws | `17.912673924` | `0` |
| Finger hard geometry ↔ new bosses | `14.822382286` | `0` |
| thumb ↔ shell | intended contact `0` | `0` |
| N front carrier ↔ shell | `0.408148021` | `0` |
| N rear restraint ↔ shell | `0.924696092` | `0` |
| N2 carrier ↔ opposite JaD | `1.054170903` | `0` |

N front carrier의 `0.408 mm` shell distance는 locating/capture interface이며 배선 또는
free-motion gap이 아니다. Carrier는 shell closure에 의해 의도적으로 위치 결정된다.

## 11. Fragment와 FDM gate

| Generated body | valid | solid count | small solid count | volume mm³ |
|---|---|---:|---:|---:|
| JaD shell | yes | 1 | 0 | `46048.667795` |
| JfD shell | yes | 1 | 0 | `46305.922403` |
| N shared front carrier | yes | 1 | 0 | `378.134716` |
| N rear restraint | yes | 1 | 0 | `92.690075` |
| I2/I3 carrier | yes | 1 | 0 | `500.074049` |
| M4/N3 carrier | yes | 1 | 0 | `530.377695` |
| I4 carrier | yes | 1 | 0 | `266.675016` |
| M3 carrier | yes | 1 | 0 | `264.562302` |

- orphan: 0
- sliver: 0
- leftover cutter: 0
- tangent-only connection: 0
- carrier functional wall: `1.60 mm`
- boss radial wall: `1.80 mm`
- boss web: `3.20 mm`

### 추천 print orientation

- JaD/JfD: split/seam face를 bed에 두고 cap guide와 conformal pad에 support scar가
  생기지 않게 한다.
- N shared front carrier: front-ring plane을 flat으로 두고 bridge만 최소 local support.
- N rear restraint: 넓은 restraint face를 flat으로 두면 support-free 출력 가능.

`FDM PRINTABILITY = PASS`, `FRAGMENT GATE = PASS`

## 12. 조립 순서

1. I2/I3, I4, M3, M4/N3 switch를 pre-wire하고 각 carrier에 설치한다.
2. N1/N2 switch를 shared front ring에 축방향으로 삽입한다.
3. N1/N2 distal lead를 한 번 성형하고 solder한 뒤 rear restraint를 설치한다.
4. Finger wire를 shared corridor 양쪽으로 아래로 보낸다.
5. lowered rigid thumb module을 pre-wire한다.
6. thumb Backplate를 three-pad split flange에 seat한다.
7. thumb bundle을 posterior corridor로 보낸다.
8. JaD/JfD를 닫아 N carrier와 thumb flange를 capture한다.
9. +X 방향 M3-class screw 3개를 체결한다.

Exact closing state에서 control, wiring, boss, shell penetration은 0이다.

`ASSEMBLY = PASS`

## 13. Service 순서

1. M3-class screw 3개를 제거한다.
2. 접착제를 자르지 않고 JaD/JfD를 분리한다.
3. split conformal seat에서 thumb module을 들어낸다.
4. N rear restraint를 제거한다.
5. N1/N2 switch를 front ring에서 뺀다.
6. 나머지 네 carrier group을 각각 독립적으로 제거한다.

Structural adhesive는 사용하지 않는다. `SERVICEABILITY = PASS`다.

## 14. Visual QC

1. `renders/finger_thumb_integrated_v3/01_complete_exterior.png`
2. `renders/finger_thumb_integrated_v3/02_transparent_complete_internals.png`
3. `renders/finger_thumb_integrated_v3/03_n1_n2_closeup.png`
4. `renders/finger_thumb_integrated_v3/04_thumb_seating_backplate.png`
5. `renders/finger_thumb_integrated_v3/05_new_screw_boss_architecture.png`
6. `renders/finger_thumb_integrated_v3/06_finger_carriers_exploded.png`
7. `renders/finger_thumb_integrated_v3/07_thumb_exploded.png`
8. `renders/finger_thumb_integrated_v3/08_wiring_routes.png`
9. `renders/finger_thumb_integrated_v3/09_shell_closing_view.png`
10. `renders/finger_thumb_integrated_v3/10_service_disassembly.png`

Contact sheet:
`renders/finger_thumb_integrated_v3/00_contact_sheet.png`

## 15. Final verdicts

| Gate | Verdict |
|---|---|
| FINGER EXTERNAL LAYOUT | **PRESERVED** |
| THUMB EXTERNAL LAYOUT | **PRESERVED** |
| N1 INTERNAL | **PASS** |
| N2 SEAM | **PASS** |
| FINGER CARRIERS | **PASS** |
| THUMB SEATING | **PASS** |
| NEW FASTENING | **PASS** |
| WIRING | **PASS** |
| ASSEMBLY | **PASS** |
| SERVICEABILITY | **PASS** |
| FDM PRINTABILITY | **PASS** |
| FRAGMENT GATE | **PASS** |
| LOCAL INTEGRATED V3 | **PASS** |

## 16. 다음 단계 제한

이 결과로 전체 production 출력이나 production freeze를 진행하지 않는다. 다음 허용
단계는 Finger + lowered Thumb를 한 번에 검증하는 local functional validation section
설계와 FDM 실물 시험뿐이다. 그 시험에서 switch fit, cap travel, seam jam, thumb seat,
screw access와 wiring pinch를 확인한 뒤에만 production 반영 여부를 판단한다.
