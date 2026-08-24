# 89 — I2 +U final local three-way clearance balancing audit

FINAL VERDICT = **B — IMPROVED BALANCE BUT ONE CLEARANCE REMAINS TIGHT**

| Metric | docs/88 D | Final balanced candidate |
|---|---:|---:|
| I2 body clearance | 0.062755 | **0.145815 mm** |
| minimum terminal clearance | 0.396236 | **0.395539 mm (T3)** |
| T4 clearance | 1.148952 | **1.151129 mm** |
| I3 clearance | 0.219919 | **0.145850 mm** |
| MIN_3WAY_CLEARANCE | 0.062755 | **0.145815 mm** |
| +U nominal thickness | 1.300 | **1.285741 mm** |
| +U effective thickness | 1.211070 | **1.200000 mm** |
| minimum neck | 1.270 | **1.270 mm** |
| remaining shell | 1.200134 | **1.200134 mm** |
| rear-harness assembly | PASS | **PASS** |

## Pareto candidates

| candidate | root U shift | effective | body | terminal | I3 | MIN_3WAY | rear |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 — maximum MIN_3WAY / selected | −0.054250 | 1.200 | 0.145815 | 0.395539 | 0.145850 | **0.145815** | PASS |
| 2 — manufacturing section margin | −0.054250 | 1.210 | 0.140458 | 0.395539 | 0.140507 | **0.140458** | static PASS |
| 3 — max I3 with body ≥0.15 | −0.050000 | 1.200 | 0.150146 | 0.395501 | 0.141349 | **0.141349** | static PASS |

The limiting pair is BODY/I3, not terminals. The bounded 22-candidate section sweep plus 12 tangent checks peaks
where BODY and I3 are nearly equal. A 0.15 mm simultaneous margin is short by **0.004185 mm**;
further U motion improves I3 while reducing BODY by the same order. No tight tolerance is moved to a near-zero pair.

## Manufacturing / shell / assembly gates

- one fused solid / STEP reimport: **1 / 1**;
- valid/watertight: **True**;
- tangent-only / zero-thickness: **0 / 0**;
- minimum neck: **1.270 mm**;
- minimum effective section: **1.200000 mm**;
- +U root common volume: **1.801679 mm³**;
- endpoint/slot change: **NO**; shell penetration 0; remaining exterior shell **1.200134 mm**.

Original detailed 3,530-facet PushBtn, T1–T4/corners/bottom and measured D3.35 × 2.44 actuator were used. The
five-state user-intended rear-harness check keeps PushBtn translation/rotation at 0 and reports terminal/body,
pusher/actuator, shell and final unintended penetration all **0 mm³**; elastic deformation **NO**.

## Renders / outputs / STOP

- [01_docs88_d_three_way_closeup.png](../renders/i2_final_local_clearance_balancing_audit/01_docs88_d_three_way_closeup.png)
- [02_final_balanced_three_way_closeup.png](../renders/i2_final_local_clearance_balancing_audit/02_final_balanced_three_way_closeup.png)
- [03_i2_body_minimum_clearance.png](../renders/i2_final_local_clearance_balancing_audit/03_i2_body_minimum_clearance.png)
- [04_i3_minimum_clearance.png](../renders/i2_final_local_clearance_balancing_audit/04_i3_minimum_clearance.png)
- [05_terminal_minimum_clearance.png](../renders/i2_final_local_clearance_balancing_audit/05_terminal_minimum_clearance.png)
- [06_rear_harness_full_seat.png](../renders/i2_final_local_clearance_balancing_audit/06_rear_harness_full_seat.png)

- `build123d_workbench/out/i2_final_local_clearance_balancing_audit/I2_FINAL_BALANCED_MANUFACTURING_HARNESS_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_final_local_clearance_balancing_audit/i2_final_local_clearance_balancing_audit.json`

Production modification=0; 8-button propagation=0; N2=0; coupon=0; architecture redesign=0. All
167 protected docs/79–88 and prior artifacts retain identical SHA-256 hashes:
**True**.
