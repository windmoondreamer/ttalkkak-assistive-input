# 77 — Open-frame glued switch harness candidate

RECOMMENDED ARCHITECTURE
= **STANDARD OPEN-FRAME ITS HARNESS + POSITION-SPECIFIC CONFORMAL GLUE FEET + OPENING-DATUM JIG**

STANDARD CORE FEASIBLE
= **CONDITIONAL — common mechanical core works; +U broad service keeper and physical retention test remain**

CONFORMAL GLUE FOOT
= **REVISE — shell-derived candidate exists, but adhesive/cure coupon is required at every foot family**

ALIGNMENT JIG
= **PASS AS AUDIT GEOMETRY — center, axis, depth and roll are mechanically constrained**

SWITCH LOCATING
= **MAIN-BODY BOTTOM OPEN CROSS + −U/−V CONTROLLED CHEEKS + +V CLEARANCE CHEEK + BROAD +U KEEPER**

PUSHER
= **D2.60 TIP / D4.00 SHAFT / D4.80 SHOULDER / 0.08 GAP — PARAMETRIC, COUPON REQUIRED**

HARD STOP
= **HARNESS GUIDE SHOULDER, T_HARD_STOP=0.38 mm PROVISIONAL**

GLUE LOAD PATH
= **PRESS LOAD PRIMARILY COMPRESSION/SHEAR; PEEL DURING USER PRESS=0 BY CONSTRUCTION**

8-POSITION VIRTUAL FIT
= **CONDITIONAL — same core places at all eight; some feet/wings require local variants**

N1/N2 PACKAGING
= **IMPROVED REAR VOLUME; N2 SEAM CURE/CLOSURE TRIAL REQUIRED**

FDM
= **CONDITIONAL — all structural members ≥1.20 mm, preferred ribs/keeper/feet 1.60 mm; V2 coupon required**

SHELL SPLIT
= **PRESERVED**

EXTERIOR
= **PRESERVED**

PRODUCTION MODIFICATION
= **0**

## 1. Final verdict

**B. OPEN-FRAME HARNESS WORKS, BUT SOME POSITIONS NEED LOCAL VARIANTS.**

형님의 스케치처럼 switch 주위를 큰 상자로 막지 않고, rear cross-seat·세 개의 local cheek·세 개의
상부 rib·개구부 안쪽 원형 guide만 남겼다. 동일 core를 8개 W축에 놓을 수 있으며, 달라지는 것은
shell-derived foot와 wing 경로다. 다만 접착제/실물 ITS/경화 jig를 아직 물리 검증하지 않았으므로
`A preferred → production`으로 바로 승격하지 않는다.

## 2. Representative choice and architecture

대표는 **I2**다. N1/N2의 seam·Thumb 특수성에 치우치지 않으면서 실제 JfD 곡면, shared-carrier
각도, 네 terminal을 모두 대표한다.

```text
frozen 8 mm opening / cap
→ captured local pusher
→ D7.40 guide + internal shoulder stop
→ actual ITS actuator/body
→ 1.20 mm open cross seating datum
→ 1.60 mm ribs/wings
→ 3 shell-derived conformal feet
→ 0.20 / 0.30 / 0.50 mm adhesive bondline
→ frozen shell inner surface
```

- closed 6.4 pocket: 없음
- full bottom plate: 없음
- tiny snap/hook: 없음
- terminal quadrant closure: 없음
- +U insertion: broad keeper를 빼고 side insertion, keeper 설치 후 cure
- corner features: D1.40×0.80 UNKNOWN keep-out만 적용, locating/clamping 0

## 3. Standard core details

| item | value |
|---|---:|
| measured body authority | 6.12 × 6.05 × 3.56 mm |
| guide OD / opening | 7.40 / 8.00 mm |
| opening radial nominal clearance | 0.30 mm/side |
| guide bore / pusher shaft | 4.40 / 4.00 mm |
| structural guide radial wall | 1.20 mm |
| seat/rib/keeper/foot thickness | 1.20 / 1.60 / 1.60 / 1.60 mm |
| representative I2 rear depth | 10.16 mm from frozen exterior datum |
| N1/N2 rear depth | 9.56 mm from frozen exterior datum |
| N1/N2 reduction vs current 9.96 | 0.40 mm |
| core material volume | 124.20 mm³ |
| current closed-pocket candidate material | 235.76 mm³ |

Core는 switch main-body bottom을 plus-shaped cross로 받는다. 네 terminal은 V=±2.25 side corridor로
빠지고 cross는 U/V 중앙선에만 있어 solder iron과 wire departure를 막지 않는다. +U keeper도 두
terminal 사이 V=0에만 위치한다.

## 4. Pusher and simultaneous stack solver

| parameter | audit value | status |
|---|---:|---|
| REST_GAP | 0.08 | coupon variants required |
| T_CLICK | 0.33 cap travel | inferred from 0.08 + nominal 0.25 |
| T_DESIGN_FULL | 0.38 | provisional |
| T_HARD_STOP | 0.38 | provisional |
| actuator compression at stop | 0.30 | below recorded 0.35 upper bound, not a final spec |

```text
FIXED cap pose + W axis
+ measured body/actuator
+ body-bottom seat
+ pusher gap/diameter
+ captured shoulder cavity
+ structural stop
→ solve REST / CLICK / FULL together
→ then verify shell opening + foot + FDM
```

Shell-clearance-first `choose_front_depths()`는 packaging check로만 남고 pusher/travel authority가 아니다.

## 5. Glue feet and bondline

I2 및 나머지 위치에서 owner shell mesh를 local U/V ray로 표본화하고, local inner surface를 따라가는
faceted foot를 생성했다. 각 foot는 nominal 0.30 mm bondline만큼 안쪽에 있고 두께 1.60 mm다.
foot가 seam 반대 half로 넘어가는 candidate는 선택 단계에서 제외했다.

- bondline parameter: **0.20 / 0.30 / 0.50 mm**
- glue keep-out: central 8×8 guide/switch column + T1–T4 solder cones
- press force: shell normal 방향 성분은 compression, tangent 성분은 shear로 전달
- user press의 intentional peel: **0**
- cure shrink, shell flex, removal peel: **physical coupon gate**

CAD zero gap을 접착 PASS로 쓰지 않았다. 표면 표본/foot tessellation은 candidate이고, production에서는
chosen adhesive의 최소/최대 bondline, primer, cure fixture, shell material compatibility를 다시 잠가야 한다.

## 6. Alignment jig

Jig는 exterior opening을 datum으로 사용한다.

- 7.72 mm square key: opening center + roll
- D4.16 pilot: pusher/guide W axis
- 13 mm flange: exterior depth
- long exterior handle: cure 후 outward removal

따라서 조립자가 shell 안쪽에서 눈대중으로 center/angle/depth를 맞추지 않는다. 실제 반복정밀도는
V2 coupon의 opening plate에서 10회 설치/제거 후 측정한다.

## 7. Per-position virtual fit

| button | CORE TYPE | FOOT TYPE | GLUE AREA mm² | AXIS | REAR PROJECTION | TERMINAL ACCESS | WIRE EXIT | NEIGHBOR CLEARANCE | SEAM | JIG | VERDICT |
|---|---|---|---:|---|---:|---|---|---:|---|---|---|
| N1 | STANDARD V1 | 3-PATCH SHELL-DERIVED FACETED CONFORMAL FOOT | 22.08 | `-0.076, -0.872, -0.483` | 9.56 | T1/T2/T3/T4 available | ±U SIDE / four terminal quadrants open | 0.75 | HIGH | YES / opening pilot D4.16 + 7.72 key | **LOCAL FOOT VALIDATION REQUIRED** |
| N2 | STANDARD V1 | 1-PATCH SHELL-DERIVED FACETED CONFORMAL FOOT | 9.71 | `-0.043, -0.859, -0.509` | 9.56 | T1/T3 active; T2/T4 unused trim | ±U SIDE / four terminal quadrants open | 0.75 | HIGH | YES / opening pilot D4.16 + 7.72 key | **HOLD / FOOT PATCH INSUFFICIENT** |
| I2 | STANDARD V1 | 3-PATCH SHELL-DERIVED FACETED CONFORMAL FOOT | 24.99 | `-0.434, -0.757, -0.489` | 10.16 | T1/T2/T3/T4 open | ±U SIDE / four terminal quadrants open | 0.00 | LOW | YES / opening pilot D4.16 + 7.72 key | **LOCAL FOOT/WING VARIANT REQUIRED** |
| I3 | STANDARD V1 | 3-PATCH SHELL-DERIVED FACETED CONFORMAL FOOT | 27.49 | `-0.082, -0.952, -0.295` | 10.56 | T1/T2/T3/T4 open | ±U SIDE / four terminal quadrants open | 0.00 | MEDIUM | YES / opening pilot D4.16 + 7.72 key | **LOCAL FOOT/WING VARIANT REQUIRED** |
| I4 | STANDARD V1 | 3-PATCH SHELL-DERIVED FACETED CONFORMAL FOOT | 13.90 | `+0.038, -0.956, -0.292` | 10.56 | T1/T2/T3/T4 open | ±U SIDE / four terminal quadrants open | 0.00 | MEDIUM | YES / opening pilot D4.16 + 7.72 key | **LOCAL FOOT/WING VARIANT REQUIRED** |
| M3 | STANDARD V1 | 3-PATCH SHELL-DERIVED FACETED CONFORMAL FOOT | 19.29 | `-0.224, -0.772, -0.595` | 9.96 | T1/T2/T3/T4 open | ±U SIDE / four terminal quadrants open | 0.01 | MEDIUM | YES / opening pilot D4.16 + 7.72 key | **LOCAL FOOT VALIDATION REQUIRED** |
| M4 | STANDARD V1 | 3-PATCH SHELL-DERIVED FACETED CONFORMAL FOOT | 19.16 | `+0.288, -0.744, -0.603` | 9.56 | T2 unused; other terminals open | ±U SIDE / four terminal quadrants open | 0.00 | LOW | YES / opening pilot D4.16 + 7.72 key | **LOCAL FOOT/WING VARIANT REQUIRED** |
| N3 | STANDARD V1 | 3-PATCH SHELL-DERIVED FACETED CONFORMAL FOOT | 24.60 | `+0.692, -0.560, -0.455` | 10.36 | T3 unused; other terminals open | ±U SIDE / four terminal quadrants open | 0.00 | LOW | YES / opening pilot D4.16 + 7.72 key | **LOCAL FOOT/WING VARIANT REQUIRED** |

`AABB overlap proxy`가 있는 pair는 production collision 판정이 아니라 **wing/foot route local variant**
표시다. Core 중심/axis를 움직이지 않고 해당 foot 또는 wing만 다시 route해야 한다.

## 8. N1/N2 and shell split

N1/N2 rear depth는 9.56 mm로 current carrier 9.96보다 0.40 mm 줄었다. 폐쇄 rear wall과 wiring chamber가
없어 terminal은 ±U side departure가 가능하다. 그러나 N2는 center가 split에 놓이므로 core는 기하학상
양 half 공간을 통과한다. Feet는 JfD 한쪽에만 제한했지만 **shell closure가 core를 밀지 않는지 cure
trial이 필수**다. Split 삭제/bridge는 제안하지 않았다.

SZH render의 보라색 모델은 기존 LOW-confidence web reference다. 0.5 mm 이하 판정에는 쓰지 않는다.

## 9. Architecture comparison

| criterion | closed / large pocket | bulky cartridge | open-frame glued harness |
|---|---|---|---|
| material / envelope | medium / closed walls | highest | **lowest material, open quadrants** |
| rear projection | current N1/N2 9.96 class | ≥9.96, often longer | **N1/N2 9.56; position follows frozen front depth** |
| switch locating | all-wall tolerance sensitive | deterministic | 3 cheeks + keeper, conditional |
| FDM repeatability | shell angle coupled | separately printable | **same core, best orientation** |
| terminal/wire access | restricted | chamber dependent | **four open corridors** |
| serviceability | pocket extraction | cartridge removal | keeper removal; adhesive foot is destructive |
| assembly complexity | low/medium | medium | **highest: adhesive + jig + cure** |
| alignment sensitivity | shell CAD | cartridge datum | jig-controlled but bondline-sensitive |
| shell modification | possible pocket | mounts required | **0 / broad adhesive feet** |
| adhesive dependence | none/low | none/low | **primary dependency** |

따라서 packaging/FDM/terminal 면에서는 open frame가 우세하지만 assembly와 adhesive durability 때문에
물리 coupon 전에는 **B**가 맞다.

## 10. OPEN_FRAME_HARNESS_FDM_COUPON_V2

V1 `BUTTON_FDM_TEST_COUPON`은 그대로 보존했다. V2는 세 station을 포함한다.

| station | U/V locating gap | tip | hard stop |
|---|---|---|---|
| 1 | 0.12 / 0.14 | D2.40 | 0.34 |
| 2 | 0.20 / 0.22 | D2.60 | 0.38 |
| 3 | 0.32 / 0.35 | D2.80 | 0.42 |

검사항목: actual insertion, bottom seating, side clearance, corner keep-out, pusher, REST/click/return,
hard stop, T1–T4 access, removal, 100-cycle actuation. 같은 STEP에 curved shell-like glue surface와
8 mm opening/jig 반복성 test도 넣었다.

## 11. Required renders

- [01_open_frame_harness_isolated.png](../renders/open_frame_glued_switch_harness_candidate/01_open_frame_harness_isolated.png)
- [02_its_inserted_in_harness.png](../renders/open_frame_glued_switch_harness_candidate/02_its_inserted_in_harness.png)
- [03_bottom_seating_closeup.png](../renders/open_frame_glued_switch_harness_candidate/03_bottom_seating_closeup.png)
- [04_corner_feature_clearance.png](../renders/open_frame_glued_switch_harness_candidate/04_corner_feature_clearance.png)
- [05_open_terminal_access.png](../renders/open_frame_glued_switch_harness_candidate/05_open_terminal_access.png)
- [06_pusher_actuator_section.png](../renders/open_frame_glued_switch_harness_candidate/06_pusher_actuator_section.png)
- [07_hard_stop_section.png](../renders/open_frame_glued_switch_harness_candidate/07_hard_stop_section.png)
- [08_glue_wings_isolated.png](../renders/open_frame_glued_switch_harness_candidate/08_glue_wings_isolated.png)
- [09_conformal_foot_on_shell_inner_surface.png](../renders/open_frame_glued_switch_harness_candidate/09_conformal_foot_on_shell_inner_surface.png)
- [10_alignment_jig_installed.png](../renders/open_frame_glued_switch_harness_candidate/10_alignment_jig_installed.png)
- [11_jig_shell_harness_section.png](../renders/open_frame_glued_switch_harness_candidate/11_jig_shell_harness_section.png)
- [12_glue_load_path_visualization.png](../renders/open_frame_glued_switch_harness_candidate/12_glue_load_path_visualization.png)
- [13_representative_harness_in_shell.png](../renders/open_frame_glued_switch_harness_candidate/13_representative_harness_in_shell.png)
- [14_all8_virtual_harness_placement.png](../renders/open_frame_glued_switch_harness_candidate/14_all8_virtual_harness_placement.png)
- [15_n1_n2_thumb_szh_closeup.png](../renders/open_frame_glued_switch_harness_candidate/15_n1_n2_thumb_szh_closeup.png)
- [16_jad_jfd_split_relationship.png](../renders/open_frame_glued_switch_harness_candidate/16_jad_jfd_split_relationship.png)
- [17_coupon_v2_preview.png](../renders/open_frame_glued_switch_harness_candidate/17_coupon_v2_preview.png)

## 12. Outputs / verification / STOP

- standard core: `build123d_workbench/out/open_frame_glued_switch_harness_candidate/STANDARD_OPEN_FRAME_HARNESS_CORE_AUDIT_ONLY.step`
- I2 harness: `build123d_workbench/out/open_frame_glued_switch_harness_candidate/I2_OPEN_FRAME_GLUED_HARNESS_AUDIT_ONLY.step`
- alignment jig: `build123d_workbench/out/open_frame_glued_switch_harness_candidate/I2_OPENING_DATUM_ALIGNMENT_JIG_AUDIT_ONLY.step`
- all-8 virtual: `build123d_workbench/out/open_frame_glued_switch_harness_candidate/ALL8_VIRTUAL_OPEN_FRAME_HARNESS_AUDIT_ONLY.step`
- V2 coupon STEP/STL: `build123d_workbench/out/open_frame_glued_switch_harness_candidate/OPEN_FRAME_HARNESS_FDM_COUPON_V2_AUDIT_ONLY.step` / `build123d_workbench/out/open_frame_glued_switch_harness_candidate/OPEN_FRAME_HARNESS_FDM_COUPON_V2_AUDIT_ONLY.stl`
- JSON: `build123d_workbench/out/open_frame_glued_switch_harness_candidate/open_frame_glued_switch_harness_candidate.json`
- protected production hashes preserved: **True**
- production modification: **0**

**STOP.** 사용자 승인 전 production shell cut, harness placement, cap/center/Thumb 변경을 하지 않는다.
