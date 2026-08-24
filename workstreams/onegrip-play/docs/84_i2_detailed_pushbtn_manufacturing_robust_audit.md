# 84 — I2 detailed PushBtn manufacturing-robust audit

ORIGINAL ONEGRIP PushBtn USED = **YES**

SOURCE FILE / SOURCE OBJECT = **cad_dump/mesh_PushBtn.json / PushBtn / ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID**

ORIGINAL PushBtn SOLID COUNT = **1**

ORIGINAL PushBtn TERMINALS INCLUDED = **YES**

ORIGINAL CORNER FEATURES INCLUDED = **YES**

ACTUATOR REBASED TO MEASURED ITS = **YES**

SIMPLIFIED SWITCH PROXY USED FOR FINAL CLEARANCE VERDICT = **NO**

FINAL VERDICT = **C — DETAILED PUSHBTN REVEALS AN ARCHITECTURAL CONFLICT**

## 1. Authority correction

`cad_dump/mesh_PushBtn.json`의 3,530 facets를 그대로 sewing한 valid one-solid BRep를 사용했다.
원작 plastic body, bottom detail, four exact terminals 및 four corner protrusions를 유지했다. 원작 actuator만 제거하고
동일 frozen axis/front datum에서 measured ITS-1105 **D3.35 × 2.44 mm** actuator로 교체했다.
Original main-body bottom은 docs/83 measured-body rear datum보다 +W 0.06 mm이며 이것이 새 support-cross seating plane이다.

## 2. A/B/C comparison

| metric | A. docs/83 simplified proxy | B. unchanged docs/83 + detailed PushBtn | C. robust + detailed PushBtn |
|---|---:|---:|---:|
| terminal clearance | 0.001 mm | 0.000000 mm; penetration 0.002031926 mm³ | 0.059066 mm; penetration 0 |
| original corner-feature clearance | proxy 0.803 mm | 0.795842 mm | 0.794484 mm |
| harness/body | simplified envelope PASS | penetration 0.000371932 mm³ | main-bottom contact, penetration 0 |
| pusher clearance | 1.250 mm | 1.249532 mm | 1.348763 mm |
| I3/neighbor clearance | 0.223 mm | 0.158897 mm | 0.059187 mm |
| remaining exterior shell | 1.200 mm | 1.200 mm | 1.245622 mm |
| minimum effective FDM section | 1.180 mm | 1.180 mm | 1.228681 mm |
| rigid assembly | proxy + 0.35/0.30 mouth PASS | static detailed collision → not qualified | **FAIL** — shell 0 / pusher 0, but detailed I3 T2 collision |

The unchanged docs/83 geometry is therefore **FAIL** under detailed authority: +U intersects the source skirt/body and T4 terminal.

## 3. Robust four-straight-leg candidate

| leg | root shift from docs/83 U,V,W mm | length | tilt | azimuth | nominal t | effective FDM t | remaining shell |
|---|---|---:|---:|---:|---:|---:|---:|
| +U | [0.12149999999999972, 1.715625, 0.06000000000000005] | 6.959 | 10.597° | 17.603° | 1.25 | 1.229 | 1.246 |
| -U | [-0.21499999999999986, 0.075, 0.66] | 5.904 | 18.238° | -166.885° | 1.60 | 1.520 | 1.397 |
| +V | [-1.76, -0.25, 0.66] | 7.111 | 11.008° | 102.585° | 1.60 | 1.571 | 1.394 |
| -V | [1.74, 0.08000000000000007, 0.66] | 7.348 | 10.695° | -89.467° | 1.60 | 1.572 | 1.313 |

All four are one straight rectangular prism, fused with the main-body-bottom open cross into **one printed solid**.
No dogleg, flexible leg, hook, panel, housing, receiver cage, strut, carrier, broad foot or transition bracket was added.

## 4. Detailed exact static gates

- minimum original terminal clearance: **0.059066 mm**, +U ↔ T4;
- minimum original corner-feature clearance: **0.794484 mm**;
- minimum pusher/harness clearance: **1.348763 mm**;
- minimum detailed I3 clearance: **0.059187 mm**;
- minimum remaining exterior shell: **1.245622 mm**;
- body / terminal / corner / pusher / neighbor penetration: **0 mm³**.

### +U Pareto proof

Detailed I2↔I3 main-body minimum gap is **1.337971 mm**.
The requested 0.40 + 1.20 + 0.40 mm body/leg/neighbor stack requires **2.000 mm**, exceeding that gap by
**0.662029 mm** before terminal/corner geometry is considered.
At +U radial gap 0.0815 mm, terminal and I3 clearances balance at 0.059066 / 0.059187 mm.
Moving outward improves T4 but worsens I3; moving inward does the reverse. This is the zero-penetration Pareto point,
not a manufacturing-ready 0.40 mm margin. No complex support was generated.

## 5. Slot and rigid assembly

- lower blind slot: **0.20 mm/side clearance × 1.20 mm depth**;
- simple rectangular open entry: **1.03 mm/side × 0.93 mm depth**;
- blind-slot depth remaining below the open entry: **0.27 mm**;
- common insertion vector: `[0.3415514166060052, -0.017899951255297575, 0.9396926207859084]`;
- travel/states: **1.600 mm / 33**;
- maximum shell / pusher / neighbor penetration: **0.000000000 / 0.000000000 / 0.040606908 mm³**;
- shell / neighbor swept collision volume: **0.000000000 / 0.057238312 mm³**;
- limiting detailed pair/state: **I3 HARNESS:T2 / state 0**;
- elastic deformation assumed: **NO**.

The selected 20° straight rigid path clears the cut shell and captive pusher at all 33 states, but it intersects the
detailed I3 T2 terminal. Therefore the rigid one-piece assembly gate is **FAIL**, irrespective of the static full-seat fit.

### Assembly-conflict proof

- docs/83 minimax-like direction: detailed-neighbor penetration **0.662391863 mm³**;
- pure +W direction: shell swept collision **0.009974251 mm³**, neighbor penetration **0.411040445 mm³**;
- selected 20° / −3° direction: shell/pusher penetration **0 / 0 mm³**, but I3 T2 penetration **0.040606908 mm³**;
- first neighbor-clear 36° / 0° direction: detailed I3 body and T2 both clear, but the harness collides with the central shell by
  **0.010322255 mm³**, even with a 1.50 mm/side × 1.10 mm open mouth;
- widening/deepening the four simple mouths through 2.50 mm/side × 1.30 mm does not remove that central-shell collision.

Removing the latter collision requires broad central shell relief or a non-straight/multi-part/flexible architecture,
which is outside the permitted Level-0 architecture. No such geometry was generated.

## 6. Actuator and pusher

- actuator diameter/projection: **3.35 / 2.44 mm**;
- actuator axis = pusher axis = approved press axis: **YES**;
- pusher center offset from actuator: **0.000000000 mm**;
- pusher-to-actuator rest gap: **0.080 mm**.

## 7. FDM

P1S / 0.4 mm nozzle; open cross flat on the build plate; local +W vertical. Support required = **NO**.
Minimum effective section is +U **1.228681 mm**, so the absolute 1.20 mm CAD projection gate passes.
Weakest region is the +U straight-leg/root fusion. Support removal between legs or inside the cage is not required.
The 0.059 mm detailed T4/I3 margin is provisional, and the rigid insertion gate fails; this candidate is not production releasable.
Physical coupon remains outside this audit.

## 8. Required renders

- [01_original_detailed_onegrip_pushbtn_alone.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/01_original_detailed_onegrip_pushbtn_alone.png)
- [02_original_pushbtn_detailed_terminal_view.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/02_original_pushbtn_detailed_terminal_view.png)
- [03_original_pushbtn_corner_feature_closeup.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/03_original_pushbtn_corner_feature_closeup.png)
- [04_original_vs_measured_actuator_overlay.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/04_original_vs_measured_actuator_overlay.png)
- [05_measured_actuator_rebase.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/05_measured_actuator_rebase.png)
- [06_detailed_pushbtn_inserted_in_harness.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/06_detailed_pushbtn_inserted_in_harness.png)
- [07_four_edge_harness_top_view.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/07_four_edge_harness_top_view.png)
- [08_four_straight_final_legs.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/08_four_straight_final_legs.png)
- [09_four_direct_shell_slots.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/09_four_direct_shell_slots.png)
- [10_worst_detailed_terminal_clearance.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/10_worst_detailed_terminal_clearance.png)
- [11_worst_original_corner_feature_clearance.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/11_worst_original_corner_feature_clearance.png)
- [12_detailed_i3_clearance.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/12_detailed_i3_clearance.png)
- [13_minimum_remaining_shell_section.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/13_minimum_remaining_shell_section.png)
- [14_minimum_effective_structural_section.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/14_minimum_effective_structural_section.png)
- [15_assembly_start.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/15_assembly_start.png)
- [16_assembly_partial.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/16_assembly_partial.png)
- [17_assembly_full_seat.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/17_assembly_full_seat.png)
- [18_swept_envelope_diagnostic.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/18_swept_envelope_diagnostic.png)
- [19_proposed_fdm_orientation.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/19_proposed_fdm_orientation.png)
- [20_docs83_proxy_vs_detailed_robust.png](../renders/i2_detailed_pushbtn_manufacturing_robust_audit/20_docs83_proxy_vs_detailed_robust.png)

## 9. Outputs / preservation / stop

- `build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit/ORIGINAL_ONEGRIP_PUSHBTN_3530_FACET_REFERENCE_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit/I2_ORIGINAL_PUSHBTN_MEASURED_ACTUATOR_HYBRID_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit/I2_DETAILED_PUSHBTN_ROBUST_FOUR_EDGE_HARNESS_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit/I2_ROBUST_FOUR_DIRECT_SLOT_SHELL_CROP_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit/I2_DETAILED_PUSHBTN_ROBUST_FULL_ASSEMBLY_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_detailed_pushbtn_manufacturing_robust_audit/i2_detailed_pushbtn_manufacturing_robust_audit.json`

All 98 protected docs/79–83, prior-audit and production artifacts retain identical SHA-256 hashes:
**True**. Production modification=0; 8-button propagation=0; N2 redesign=0; physical coupon=0.
