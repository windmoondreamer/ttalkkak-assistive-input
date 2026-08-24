# 78 — Slot-anchored harness and captive pusher audit

ARCHITECTURE
= **SLOT-ANCHORED HARNESS + CAPTIVE PUSHER**

INNER HOUSING
= **CONDITIONAL — frozen-shell-derived 1.60 mm local conformal bands + open two-slot load columns; exact BRep offset/loft required**

HARNESS CORE
= **COMMON OPEN-FRAME SWITCH CAGE + STANDARD TAB MODULE; N2 USES SAME-HALF TAB MODULE**

HARNESS RETENTION
= **SLOT/SHOULDER + ADHESIVE**

PUSHER
= **SEPARATE D2.60 TIP / D4.60 SHAFT / D6.40 STOP SHOULDER / D7.20 CAP-CONTACT HEAD**

PUSHER RETENTION
= **METAL E/C-CLIP REPRESENTATION; PRINTED GROOVE CONDITIONAL, METAL PIN OR SEPARATE COLLAR PREFERRED IF COUPON CRACKS**

CLIP LOAD-BEARING
= **NO**

HARD STOP
= **PUSHER D6.40 SHOULDER → GUIDE D6.80 CAVITY FLOOR; T_STOP=0.38 mm PROVISIONAL**

N2 SEAM
= **CONDITIONAL — BOTH SLOT BOSSES/SHOULDERS ON JfD SIDE; PHYSICAL CLOSURE TRIAL REQUIRED**

8-POSITION FIT
= **CONDITIONAL — COMMON CAGE, TWO TAB MODULES, LOCAL CONFORMAL HOUSING PANELS; NEIGHBOR TRIM REVIEW REMAINS**

FDM COUPON
= **REQUIRED**

EXTERIOR
= **PRESERVED**

JaD/JfD SPLIT
= **PRESERVED**

PRODUCTION MODIFICATION
= **0**

## 1. Architecture correction and verdict

**B — SLOT-ANCHORED ARCHITECTURE IS MECHANICALLY COHERENT, BUT EXACT BREP HOUSING AND PHYSICAL COUPON ARE REQUIRED.**

docs/77의 glue-foot 방식은 삭제하지 않았으며 **SUPERSEDED ARCHITECTURE CANDIDATE / ALTERNATIVE**로 보존했다.
이번 후보는 접착면이 press reaction을 받지 않는다. 두 broad shoulder가 slot boss에 앉고, 두 1.60 mm
load column이 shell-derived inner-housing band로 하중을 전달한다.

```text
FINGER / FROZEN CAP
→ separate captive pusher
→ ITS actuator/body
→ open cross seat
→ two broad harness shoulders
→ keyed slot bosses + broad load columns
→ conformal inner-housing band
→ frozen outer shell
```

E/C clip은 guide inner face 바깥 이탈만 제한한다. 누를 때 clip은 guide에서 멀어지며 hard-stop 접촉에는
참여하지 않는다.

## 2. Frozen authority and representative

N1/N2/I2/I3/I4/M3/M4/N3 center·W axis, visible layout, exterior, maximum-lowered Thumb, JaD/JfD split은
모두 읽기 전용이다. 대표는 seam 특수성이 없는 곡면 JfD 위치 **I2**이고, N2는 별도 same-half
tab layout으로 재검토했다.

## 3. Conformal inner housing

각 owner shell mesh의 local U/V triangle-centroid depth를 panel별 robust plane으로 맞춘 뒤, residual
상한을 포함한 controlled inward clearance와 1.60 mm thickness를 적용했다. 이는 audit solid이며 production
BRep의 exact offset/loft가 아니다.

| metric | result |
|---|---:|
| original OneGrip median local housing/shell gap | 2.333 mm |
| current lowered median local gap | 3.842 mm |
| candidate robust gap range across 8 | 0.300…1.364 mm |
| candidate local band thickness | 1.60 mm |
| load support | two slot bosses + two broad columns per button |

Gap은 coincident zero가 아니라 shell tessellation residual을 흡수한 audit clearance다. 실제 생산에서는 shell
material, fastening/merge 방식, 최소 벽, cure/assembly datum을 BRep에서 다시 잠가야 한다.

## 4. Harness and keyed slots

공통 cage는 body-bottom plus cross, −U/−V controlled cheeks, +V clearance cheek, removable broad +U keeper로
구성된다. switch를 둘러싼 6.4 closed pocket은 없다. 비대칭 A/B tongue 폭은 2.40/3.20 mm이며 tiny key가 아니다.

| parameter | nominal |
|---|---:|
| tongue A / B | 2.40×2.00 / 3.20×2.00 mm |
| tongue insertion length | 3.20 mm |
| slot A / B | 2.90×2.50 / 3.70×2.50 mm |
| slot depth | 2.40 mm |
| clearance | 0.25 mm/side |
| minimum slot wall | 1.20 mm |
| broad shoulder margin | +1.20 mm U / +1.00 mm V per side |

Slot은 U/V translation, roll, depth를 glue 전에 기계적으로 등록한다. Adhesive는 rear slot exit에서 도포하며
anti-pullout, anti-vibration, anti-slip, tolerance fill만 담당한다. 중앙 actuator/pusher 및 T1–T4가 glue keep-out이다.

## 5. Captive pusher, clip safety, hard stop

| item | value / verdict |
|---|---|
| guide bore / shaft | 5.00 / 4.60 mm |
| radial clearance | 0.20 mm/side |
| guide length | 1.75 mm |
| nominal angular clearance proxy | 6.52° |
| groove root / shaft | 3.80 / 4.60 mm |
| remaining cross-section | 68.2% |
| clip outward retention travel | 0.05 mm |
| clip gap from guide at FULL | 0.43 mm |
| hard-stop gap REST / FULL | 0.38 / 0.00 mm |

Printed groove의 단면 68%는 자동 PASS가 아니다. Axis-on-build-Z coupon에서 100-cycle, clip installation 10회,
pullout, whitening/crack을 검사한다. 실패하면 D4.6 printed pin을 키우는 대신 **metal pin 또는 separate retained
collar**를 우선한다.

## 6. REST / CLICK / FULL simultaneous stack

| state | pusher travel | actuator compression after 0.08 gap | shoulder-stop | clip press load |
|---|---:|---:|---|---|
| REST | 0.000 | 0.000 | 0.380 open | NO |
| CLICK | 0.330 | 0.250 | 0.050 open | NO |
| FULL | 0.380 | 0.300 | CONTACT | NO |

0.350 mm는 final truth로 고정하지 않았다. T_CLICK/T_DESIGN_FULL/T_STOP는 실물 force-travel coupon 뒤 다시 잠근다.

## 7. Per-position virtual propagation

| button | family | slots U×V×W mm | housing robust gap mm | terminals open | neighbor gap | same owner half | verdict |
|---|---|---|---:|---:|---:|---:|---|
| N1 | STANDARD TAB MODULE | A 2.90×2.50×2.40; B 3.70×2.50×2.40 | 0.30…1.17 | True | 0.00 | True | **CONDITIONAL / COUPON + EXACT BREP HOUSING REQUIRED** |
| N2 | N2 SAME-HALF TAB MODULE | A 2.90×2.50×2.40; B 3.70×2.50×2.40 | 0.30…0.60 | True | 0.00 | True | **CONDITIONAL / COUPON + EXACT BREP HOUSING REQUIRED** |
| I2 | STANDARD TAB MODULE | A 2.90×2.50×2.40; B 3.70×2.50×2.40 | 0.30…1.36 | True | 0.00 | True | **CONDITIONAL / COUPON + EXACT BREP HOUSING REQUIRED** |
| I3 | STANDARD TAB MODULE | A 2.90×2.50×2.40; B 3.70×2.50×2.40 | 0.30…1.15 | True | 0.00 | True | **CONDITIONAL / COUPON + EXACT BREP HOUSING REQUIRED** |
| I4 | STANDARD TAB MODULE | A 2.90×2.50×2.40; B 3.70×2.50×2.40 | 0.30…0.82 | True | 0.00 | True | **CONDITIONAL / COUPON + EXACT BREP HOUSING REQUIRED** |
| M3 | STANDARD TAB MODULE | A 2.90×2.50×2.40; B 3.70×2.50×2.40 | 0.30…1.20 | True | 0.01 | True | **CONDITIONAL / COUPON + EXACT BREP HOUSING REQUIRED** |
| M4 | STANDARD TAB MODULE | A 2.90×2.50×2.40; B 3.70×2.50×2.40 | 0.30…1.23 | True | 0.00 | True | **CONDITIONAL / COUPON + EXACT BREP HOUSING REQUIRED** |
| N3 | STANDARD TAB MODULE | A 2.90×2.50×2.40; B 3.70×2.50×2.40 | 0.30…0.92 | True | 0.00 | True | **CONDITIONAL / COUPON + EXACT BREP HOUSING REQUIRED** |

AABB overlap은 collision 확정이 아니라 local housing band/column trim 요청이다. Frozen center/axis를 움직이지 않고
inner-housing panel 또는 column만 조정해야 한다.

## 8. N2 seam correction

N2의 두 slot center를 local U=−4.20, V=±5.50으로 옮겼다. 따라서 두 slot boss와 shoulder는 JfD 쪽에
남고 큰 glue foot나 양 shell-half anchor가 필요 없다. Switch cage 자체는 seam clearance 공간을 사용할 수 있지만
mechanical anchor는 JfD 한쪽뿐이다. JaD/JfD closure, active T1/T3 wire access, shell flex는 physical trial gate다.

## 9. Assembly and service sequence

1. Frozen outer opening 바깥에서 pusher를 guide로 삽입한다.
2. Shell 내부에서 E/C clip을 groove에 장착하고 0.05 mm retention float를 확인한다.
3. ITS를 open-frame cage의 +U 쪽으로 넣고 broad keeper를 설치한다.
4. A/B tongue를 keyed slot에 삽입해 shoulder 두 곳을 완전히 seat한다.
5. Rear slot exit에서 secondary adhesive를 도포하고 squeeze-out을 제거한다.
6. Terminal을 검사·납땜하고 open side corridor로 배선한다.
7. REST/CLICK/FULL과 pusher return을 확인한 뒤 JaD/JfD를 닫는다.

Shell을 열면 clip 제거 후 pusher 교환이 가능하다. Harness는 접착 때문에 완전 비파괴 serviceable이 아니지만
terminal inspection/solder access는 유지한다.

## 10. Architecture comparison

| criterion | old closed pocket | docs/77 glue-foot | slot-anchored + captive pusher |
|---|---|---|---|
| packaging | closed 6.4 pocket + walls | low core, broad feet | **open cage + two small slots/columns** |
| N1/N2 | carrier/seam sensitive | N2 one-foot HOLD | **N2 same-half slots; conditional** |
| press load | pocket walls/rear seat | adhesive foot dependent | **shoulder → inner housing** |
| FDM repeatability | all-wall tolerance sensitive | shell-foot fit sensitive | **keyed slot coupon-calibrated** |
| assembly | simplest | jig + broad glue | clip + keyed insertion + small glue bead |
| adhesive dependence | low | primary | **secondary only** |
| pusher alignment | legacy guide | harness guide | **frozen shell guide + keyed harness datum** |
| serviceability | pocket extraction | adhesive destructive | pusher clip-removable; harness adhesive-limited |
| terminal access | restricted | open | **open quadrants; local N2 trial** |
| shell modification | pocket/carrier | none in audit | **small guide bore only; production edit still 0** |

## 11. FDM coupon V2

Coupon contains 0.15/0.25/0.35 mm-per-side slot stations, actual-body insertion references, shoulder seating,
rear glue access/squeeze-out, D5.00 guide/D4.60 pusher, E-clip access, groove inspection, and structural stop.

Required physical checks: insertion force, shoulder flushness, adhesive access, clip tool access, pullout, REST/CLICK/FULL,
return, hard-stop witness, 100-cycle actuation, 10× clip install/remove, groove crack/whitening, and terminal tool clearance.

## 12. Required renders

- [01_exploded_architecture.png](../renders/slot_anchored_harness_captive_pusher_audit/01_exploded_architecture.png)
- [02_outer_shell_and_pusher_guide.png](../renders/slot_anchored_harness_captive_pusher_audit/02_outer_shell_and_pusher_guide.png)
- [03_pusher_and_retaining_groove.png](../renders/slot_anchored_harness_captive_pusher_audit/03_pusher_and_retaining_groove.png)
- [04_e_clip_closeup.png](../renders/slot_anchored_harness_captive_pusher_audit/04_e_clip_closeup.png)
- [05_pusher_hard_stop_shoulder.png](../renders/slot_anchored_harness_captive_pusher_audit/05_pusher_hard_stop_shoulder.png)
- [06_its_and_open_frame_harness.png](../renders/slot_anchored_harness_captive_pusher_audit/06_its_and_open_frame_harness.png)
- [07_harness_tongue_and_shoulders.png](../renders/slot_anchored_harness_captive_pusher_audit/07_harness_tongue_and_shoulders.png)
- [08_inner_housing_slots.png](../renders/slot_anchored_harness_captive_pusher_audit/08_inner_housing_slots.png)
- [09_harness_inserted_into_slots.png](../renders/slot_anchored_harness_captive_pusher_audit/09_harness_inserted_into_slots.png)
- [10_secondary_adhesive_region.png](../renders/slot_anchored_harness_captive_pusher_audit/10_secondary_adhesive_region.png)
- [11_full_button_to_shell_section.png](../renders/slot_anchored_harness_captive_pusher_audit/11_full_button_to_shell_section.png)
- [12_rest.png](../renders/slot_anchored_harness_captive_pusher_audit/12_rest.png)
- [13_click.png](../renders/slot_anchored_harness_captive_pusher_audit/13_click.png)
- [14_full_hard_stop.png](../renders/slot_anchored_harness_captive_pusher_audit/14_full_hard_stop.png)
- [15_n2_seam_closeup.png](../renders/slot_anchored_harness_captive_pusher_audit/15_n2_seam_closeup.png)
- [16_all8_virtual_arrangement.png](../renders/slot_anchored_harness_captive_pusher_audit/16_all8_virtual_arrangement.png)
- [17_inner_housing_outer_shell_conformal_section.png](../renders/slot_anchored_harness_captive_pusher_audit/17_inner_housing_outer_shell_conformal_section.png)
- [18_coupon_v2_preview.png](../renders/slot_anchored_harness_captive_pusher_audit/18_coupon_v2_preview.png)

## 13. Outputs, preservation, STOP

- standard harness STEP: `build123d_workbench/out/slot_anchored_harness_captive_pusher_audit/STANDARD_SLOT_ANCHORED_OPEN_FRAME_HARNESS_AUDIT_ONLY.step`
- representative full-stack STEP: `build123d_workbench/out/slot_anchored_harness_captive_pusher_audit/I2_SLOT_ANCHORED_HARNESS_CAPTIVE_PUSHER_AUDIT_ONLY.step`
- all-eight virtual STEP: `build123d_workbench/out/slot_anchored_harness_captive_pusher_audit/ALL8_SLOT_ANCHORED_HARNESS_VIRTUAL_AUDIT_ONLY.step`
- coupon STEP/STL: `build123d_workbench/out/slot_anchored_harness_captive_pusher_audit/SLOT_ANCHORED_HARNESS_CAPTIVE_PUSHER_COUPON_V2_AUDIT_ONLY.step` / `build123d_workbench/out/slot_anchored_harness_captive_pusher_audit/SLOT_ANCHORED_HARNESS_CAPTIVE_PUSHER_COUPON_V2_AUDIT_ONLY.stl`
- audit JSON: `build123d_workbench/out/slot_anchored_harness_captive_pusher_audit/slot_anchored_harness_and_captive_pusher_audit.json`
- docs/77 preserved hash: `dbd740a9cde99d0ae61eb3953331a94439b99e818a59ff4349bffc745673a4e0`
- protected inputs preserved: **True**
- production modification: **0**

**STOP.** Exact production shell/inner-housing BRep, carrier, cap, pusher sources에는 적용하지 않았다.
