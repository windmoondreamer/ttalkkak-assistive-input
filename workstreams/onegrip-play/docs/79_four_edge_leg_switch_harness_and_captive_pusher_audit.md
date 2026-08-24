# 79 — Four-edge-leg switch harness and captive pusher audit

HARNESS TYPE
= **FOUR-EDGE-LEG STRUCTURAL HARNESS**

LEG COUNT
= **4**

LEG LOCATIONS
= **+U / -U / +V / -V SWITCH EDGES**

VERTEX/CORNER POSTS
= **NO**

LARGE SWITCH POCKET
= **NO**

INNER-HOUSING RECEIVERS
= **4 SMALL HOLES/SLOTS**

HARNESS LOAD-BEARING
= **YES**

ADHESIVE PRIMARY LOAD-BEARING
= **NO**

PUSHER
= **SEPARATE D2.60 TIP / D4.60 SHAFT / D6.40 HARD-STOP SHOULDER**

CLIP
= **RETENTION ONLY**

HARD STOP
= **PUSHER SHOULDER → GUIDE CAVITY FLOOR; T_STOP=0.38 mm PROVISIONAL**

N2
= **CONDITIONAL — FOUR RECEIVERS ON JfD; REAR ROUTE FAMILY + PHYSICAL CLOSURE TEST REQUIRED**

8-POSITION VIRTUAL FIT
= **CONDITIONAL — ONE STANDARD CORE + ONE N2 REAR-ROUTE VARIANT**

FDM COUPON
= **READY**

EXTERIOR
= **PRESERVED**

JaD/JfD SPLIT
= **PRESERVED**

PRODUCTION MODIFICATION
= **0**

## 1. Final verdict

**B. FOUR-EDGE-LEG HARNESS WORKS WITH LIMITED LOCAL VARIANTS.**

Top view에서 네 structural member는 switch corner가 아니라 +U/−U/+V/−V side midpoint를 각각 감싼다.
docs/77 glue-foot와 docs/78 two-tongue/large-shoulder 후보는 삭제하지 않고 **SUPERSEDED ALTERNATIVE
ARCHITECTURES**로 보존했다.

```text
FINGER → PUSHER → ITS ACTUATOR/BODY
→ MAIN-BODY-BOTTOM OPEN CROSS
→ +U / -U / +V / -V EDGE LEGS
→ FOUR MINIMAL LANDINGS
→ FOUR SMALL RECEIVERS + OUTBOARD STRUTS
→ EXACT-BREP-DERIVED CONFORMAL PANELS
→ FROZEN OUTER SHELL
```

## 2. Why four minimal landings exist

Through receiver에 stop이 없으면 press 때 leg가 계속 −W로 밀려 들어가 adhesive가 primary reaction을 받는다.
따라서 각 leg root에 **0.60 mm extension × 0.60 mm thickness**의 작은 landing만 추가했다. 이는 docs/78의
broad shoulder/block가 아니며 receiver rim 위에서 insertion depth와 press reaction만 등록한다.

## 3. Switch fit and edge-leg geometry

| item | value |
|---|---:|
| measured body | 6.12 × 6.05 × 3.56 mm |
| leg structural thickness | 1.60 mm |
| side-wrap tangent width | 2.60 mm |
| locating-side gap −U/−V | 0.18 mm |
| clearance-side gap +U/+V | 0.35 mm |
| receiver insertion length | 3.20 mm |
| landing extension / thickness | 0.60 / 0.60 mm |
| corner feature minimum clearance | 0.856 mm |

Four corner features는 D1.40×0.80 UNKNOWN keep-out로 검사했고 locating/seating에 사용하지 않았다. Main-body
bottom만 open cross에 앉는다. Switch는 exterior 쪽에서 W축으로 삽입하며 all-wall press fit가 아니다.

## 4. Four receivers and conformal inner housing

| parameter | value |
|---|---:|
| receiver clearance | 0.25 mm/side |
| receiver depth | 2.40 mm |
| receiver wall | 1.20 mm |
| conformal panel thickness | 1.60 mm |
| exact validation | frozen STEP face intersections, 3×3 build + 5×5 check |
| all-eight min/max gap | 0.200…3.046 mm |
| unsupported area proxy >1 mm | 58.69 mm² |

Full shell boolean이나 mesh nearest-plane을 사용하지 않았다. Owner shell STEP의 exact face intersections로 local
inner depth를 얻고, representative I2에서는 exact 22×22×8 mm local BRep crop section을 별도로 생성했다.
Audit panel은 exact sample을 잇는 faceted ruled solid이며 production에서는 동일 BRep authority로 smooth
offset/loft와 fastening/merge detail을 확정해야 한다.

## 5. Terminal corridors and load distribution

Leg가 side midpoint에 있으므로 T1–T4 corner corridor가 열린다. CAD boolean proxy 결과 all-eight terminal
access는 **True**다.

Standard family는 nominal 25%/leg다. N2 rear route는 transition section/length stiffness proxy로
14.7…35.1%/leg이며 한 leg가 majority를 받지 않는다.
이는 FEA가 아니라 sizing screen이며 coupon의 네 landing witness mark와 rocking 검사로 확인한다.

## 6. Pusher, clip and hard stop

| item | value |
|---|---:|
| guide / shaft | D5.00 / D4.60 mm |
| radial clearance | 0.20 mm/side |
| nominal angular clearance proxy | 6.52° |
| groove root / shaft | D3.80 / D4.60 mm |
| remaining groove area | 68.2% |
| clip press-load bearing | NO |
| T_CLICK / T_DESIGN_FULL / T_STOP | 0.33 / 0.38 / 0.38 mm provisional |

Clip은 outward anti-loss만 담당하고 press 때 guide에서 멀어진다. D6.40 pusher shoulder가 D6.80 guide cavity
floor에 닿아 destructive overtravel 전에 reaction을 받는다. Printed groove가 coupon에서 crack/whitening이면
metal pin 또는 separate retained collar로 바꾼다.

## 7. Per-button virtual propagation

| button | family | terminals open | corner gap | housing gap | unsupported >1 | load share | same-half | neighbor gap | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| N1 | STANDARD FOUR-EDGE-LEG | True | 0.86 | 0.29…0.34 | 0.00 | 25.0…25.0% | True | 0.00 | **CONDITIONAL / PHYSICAL COUPON + LOCAL NEIGHBOR REVIEW** |
| N2 | N2 SAME-HALF FOUR-RECEIVER ROUTE | True | 0.86 | 0.29…2.13 | 0.64 | 14.7…35.1% | True | 0.00 | **CONDITIONAL / PHYSICAL COUPON + LOCAL NEIGHBOR REVIEW** |
| I2 | STANDARD FOUR-EDGE-LEG | True | 0.86 | 0.20…3.05 | 8.40 | 25.0…25.0% | True | 0.00 | **CONDITIONAL / PHYSICAL COUPON + LOCAL NEIGHBOR REVIEW** |
| I3 | STANDARD FOUR-EDGE-LEG | True | 0.86 | 0.20…2.92 | 17.17 | 25.0…25.0% | True | 0.00 | **CONDITIONAL / PHYSICAL COUPON + LOCAL NEIGHBOR REVIEW** |
| I4 | STANDARD FOUR-EDGE-LEG | True | 0.86 | 0.28…1.62 | 6.72 | 25.0…25.0% | True | 0.00 | **CONDITIONAL / PHYSICAL COUPON + LOCAL NEIGHBOR REVIEW** |
| M3 | STANDARD FOUR-EDGE-LEG | True | 0.86 | 0.26…0.32 | 0.00 | 25.0…25.0% | True | 0.00 | **CONDITIONAL / PHYSICAL COUPON + LOCAL NEIGHBOR REVIEW** |
| M4 | STANDARD FOUR-EDGE-LEG | True | 0.86 | 0.20…2.24 | 15.12 | 25.0…25.0% | True | 0.00 | **CONDITIONAL / PHYSICAL COUPON + LOCAL NEIGHBOR REVIEW** |
| N3 | STANDARD FOUR-EDGE-LEG | True | 0.86 | 0.20…1.26 | 10.64 | 25.0…25.0% | True | 0.00 | **CONDITIONAL / PHYSICAL COUPON + LOCAL NEIGHBOR REVIEW** |

AABB overlap은 full collision verdict가 아니라 local receiver/strut trim screen이다. Frozen center/axis/exterior를
움직이지 않고 inner support만 다듬는다.

## 8. N2 seam

N2의 upper four edge contacts는 frozen switch sides에 유지한다. Receiver centers는 local
`(-3.30,0), (-7.00,0), (-4.20,+5.00), (-4.20,-5.00)`으로 route하여 네 boss 모두 JfD에 남긴다.
Harness는 양 shell half에 anchor하지 않는다. Rear transition 길이 보정으로 load-share proxy도 majority-free지만
JaD/JfD closure, T1/T3 wire, flex, adhesive tool access는 physical gate다.

## 9. Adhesive and assembly

Adhesive는 receiver rear exit에서 leg 양쪽에 도포해 pull-out/vibration/tolerance만 제어한다. Central switch,
pusher, actuator, corner terminal corridor는 keep-out이고 squeeze-out은 rearward open이다.

1. ITS를 exterior/W 방향에서 four-edge cage에 삽입해 bottom cross에 seat한다.
2. Pusher를 frozen outer guide에 넣고 내부에서 E/C clip을 설치한다.
3. Four legs를 four receivers에 동시에 삽입하고 네 landing flush를 확인한다.
4. Pusher/actuator center와 REST return을 확인한다.
5. Receiver rear exit에 secondary adhesive를 도포하고 squeeze-out을 제거한다.
6. T1–T4 검사/납땜/배선 후 REST/CLICK/FULL을 확인하고 shell을 닫는다.

## 10. Architecture comparison

| criterion | old pocket | docs/77 glue-foot | docs/78 two-tongue | new four-edge-leg |
|---|---|---|---|---|
| packaging | closed/bulky | low core, broad feet | two large blocks | **four small side receivers** |
| load path | pocket walls | adhesive-dependent | two shoulders | **four structural legs/landings** |
| switch locating | all-wall sensitive | three cheeks | common cage | **four side regions + bottom cross** |
| FDM robustness | pocket shrink risk | foot fit risk | large tabs robust | **1.60 legs + 1.20 receiver walls** |
| housing removal | high | none in audit | two large slots | **four small slots** |
| terminal access | restricted | open | locally open | **corner corridors open** |
| adhesive | low | primary | secondary | **secondary** |
| N2 | seam-sensitive | HOLD | same-half two slot | **same-half four receiver variant** |
| service | pocket extraction | adhesive-limited | pusher serviceable | pusher serviceable; harness adhesive-limited |

## 11. Coupon V3

Coupon includes four-leg cage/receiver stations at 0.15/0.25/0.35 mm per-side clearance, measured-body insertion,
anti-rock/landing witness checks, D4.80/D5.00/D5.20 guide bores, clip mockup, 0.34/0.38/0.42 stop comparison,
and rear adhesive access.

Required tests: ITS insertion, four landing flushness, leg insertion force, rocking, terminal tool access, adhesive
application/squeeze-out, pusher slide/return, 10× clip install/remove, pullout, hard-stop witness, 100-cycle actuation.

## 12. Required renders

- [01_original_actual_its_detailed.png](../renders/four_edge_leg_harness_captive_pusher_audit/01_original_actual_its_detailed.png)
- [02_four_edge_leg_harness_top.png](../renders/four_edge_leg_harness_captive_pusher_audit/02_four_edge_leg_harness_top.png)
- [03_four_edge_leg_harness_isometric.png](../renders/four_edge_leg_harness_captive_pusher_audit/03_four_edge_leg_harness_isometric.png)
- [04_leg_plus_u_closeup.png](../renders/four_edge_leg_harness_captive_pusher_audit/04_leg_plus_u_closeup.png)
- [05_leg_plus_v_closeup.png](../renders/four_edge_leg_harness_captive_pusher_audit/05_leg_plus_v_closeup.png)
- [06_corner_feature_edge_leg_clearance.png](../renders/four_edge_leg_harness_captive_pusher_audit/06_corner_feature_edge_leg_clearance.png)
- [07_terminal_corridors.png](../renders/four_edge_leg_harness_captive_pusher_audit/07_terminal_corridors.png)
- [08_its_inserted_into_harness.png](../renders/four_edge_leg_harness_captive_pusher_audit/08_its_inserted_into_harness.png)
- [09_four_inner_housing_receivers.png](../renders/four_edge_leg_harness_captive_pusher_audit/09_four_inner_housing_receivers.png)
- [10_four_legs_inserted_into_inner_housing.png](../renders/four_edge_leg_harness_captive_pusher_audit/10_four_legs_inserted_into_inner_housing.png)
- [11_conformal_inner_housing_frozen_shell_section.png](../renders/four_edge_leg_harness_captive_pusher_audit/11_conformal_inner_housing_frozen_shell_section.png)
- [12_full_button_pusher_harness_housing_stack.png](../renders/four_edge_leg_harness_captive_pusher_audit/12_full_button_pusher_harness_housing_stack.png)
- [13_outer_shell_pusher_guide.png](../renders/four_edge_leg_harness_captive_pusher_audit/13_outer_shell_pusher_guide.png)
- [14_retaining_clip.png](../renders/four_edge_leg_harness_captive_pusher_audit/14_retaining_clip.png)
- [15_independent_hard_stop.png](../renders/four_edge_leg_harness_captive_pusher_audit/15_independent_hard_stop.png)
- [16_n2_seam_closeup.png](../renders/four_edge_leg_harness_captive_pusher_audit/16_n2_seam_closeup.png)
- [17_all8_virtual_placement.png](../renders/four_edge_leg_harness_captive_pusher_audit/17_all8_virtual_placement.png)
- [18_exploded_assembly.png](../renders/four_edge_leg_harness_captive_pusher_audit/18_exploded_assembly.png)
- [19_coupon_v3_preview.png](../renders/four_edge_leg_harness_captive_pusher_audit/19_coupon_v3_preview.png)

## 13. Outputs / preservation / STOP

- standard harness: `build123d_workbench/out/four_edge_leg_harness_captive_pusher_audit/STANDARD_FOUR_EDGE_LEG_HARNESS_AUDIT_ONLY.step`
- representative full stack: `build123d_workbench/out/four_edge_leg_harness_captive_pusher_audit/I2_FOUR_EDGE_LEG_FULL_STACK_AUDIT_ONLY.step`
- all-eight virtual: `build123d_workbench/out/four_edge_leg_harness_captive_pusher_audit/ALL8_FOUR_EDGE_LEG_VIRTUAL_AUDIT_ONLY.step`
- coupon STEP/STL: `build123d_workbench/out/four_edge_leg_harness_captive_pusher_audit/FOUR_EDGE_LEG_RECEIVER_PUSHER_COUPON_V3_AUDIT_ONLY.step` / `build123d_workbench/out/four_edge_leg_harness_captive_pusher_audit/FOUR_EDGE_LEG_RECEIVER_PUSHER_COUPON_V3_AUDIT_ONLY.stl`
- JSON: `build123d_workbench/out/four_edge_leg_harness_captive_pusher_audit/four_edge_leg_harness_and_captive_pusher_audit.json`
- docs/77 hash preserved: `dbd740a9cde99d0ae61eb3953331a94439b99e818a59ff4349bffc745673a4e0`
- docs/78 hash preserved: `55e3b3b62931b2503c196936b36c643f0d813e9e93dc71be2427945d3af064ef`
- protected inputs preserved: **True**
- production modification: **0**

**STOP.** Production shell, inner housing, pusher, harness에는 적용하지 않았다.
