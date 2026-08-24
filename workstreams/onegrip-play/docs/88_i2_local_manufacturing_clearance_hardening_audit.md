# 88 — I2 local manufacturing-clearance hardening audit

FINAL VERDICT = **A — LOCAL CLEARANCE IMPROVED TO PRACTICAL LEVEL**

## Authority correction

The supplied 0.059066 / 0.059187 mm pair is reproduced from the docs/84 robust/probe lineage. The STEP actually
used by docs/87 is the docs/86 manufacturing harness and measures +U↔T4 **0.954994 mm** and
+U↔I3 **0.090777 mm**. Both lineages are retained below rather than relabeling old numbers as docs/87.

| Metric | supplied legacy reference | docs/87 actual baseline | Best local candidate |
|---|---:|---:|---:|
| +U nominal thickness | 1.250 | 1.250 | **1.300 mm** |
| +U effective thickness | 1.228681 | 1.168114 | **1.211070 mm** |
| +U root shift from docs/87 | — | 0 | **[-0.13, 0, 0] mm** |
| +U tilt | 10.597° legacy | 20.853857° | **21.315657°** |
| T4 clearance | 0.059066 | 0.954994 | **1.148952 mm** |
| I3 clearance | 0.059187 | 0.090777 | **0.219919 mm** |
| MIN_LOCAL_CLEARANCE | ~0.059 | 0.090777 | **0.219919 mm** |
| remaining shell, global minimum | — | 1.200134 | **1.200134 mm (unchanged slot)** |
| rear-harness assembly | PASS | PASS | **PASS** |

## Bounded A–D evidence and Pareto stop

| candidate | simple change | min local | effective section | I2-body clearance | disposition |
|---|---|---:|---:|---:|---|
| A | docs/87 actual | 0.090777 | 1.168114 | 0.218197 | new 1.20 effective gate fails |
| B | root U −0.150 only | 0.252813 | 1.163903 | 0.067745 | effective gate fails |
| C | root U −0.100 + 1.30/1.20 section | 0.187815 | 1.211970 | 0.092799 | valid, below practical target |
| **D selected** | root U −0.130 + 1.30/1.20 section | **0.219919** | **1.211070** | **0.062755** | **PASS** |
| mathematical boundary | root U −0.190 + 1.30/1.20 | 0.283936 | 1.209214 | 0.002779 | rejected as non-hardened body margin |
| next boundary sample | root U −0.195 + 1.30/1.20 | 0.289259 | 1.209056 | penetration | FAIL |

The legacy ~0.059 mm pair is therefore **not** a topological limit. The local objective can exceed 0.20 mm with a
straight member. Continuing toward 0.284 mm only transfers the tight tolerance to the frozen I2 body, so
**0.219919 mm** is the practical Pareto stop used for the manufacturing candidate.

## Manufacturing and shell gate

- fused / STEP-reimport solids: **1 / 1**;
- valid/watertight: **True**;
- tangent-only / zero-thickness: **0 / 0**;
- minimum structural neck: **1.270 mm**;
- +U base/leg common volume: **1.822428 mm³**;
- harness↔unchanged slotted shell penetration: **0.000000000 mm³**;
- +U endpoint and matching slot: unchanged; global remaining exterior shell **1.200134 mm**.

Corner clearance=1.047537 mm; pusher clearance=1.605165 mm. Original detailed
3530-facet PushBtn and measured D3.35 × 2.44 actuator were used; no proxy was used.

## Rear-harness recheck

Five rigid states, PushBtn translation/rotation 0, elastic deformation NO. Result **PASS**; terminal,
pusher/actuator and shell maximum penetrations are all **0 mm³**; final unintended penetration **0 mm³**.

## Renders / outputs / STOP

- [01_baseline_plus_u_t4_i3_closeup.png](../renders/i2_local_manufacturing_clearance_hardening_audit/01_baseline_plus_u_t4_i3_closeup.png)
- [02_best_candidate_plus_u_closeup.png](../renders/i2_local_manufacturing_clearance_hardening_audit/02_best_candidate_plus_u_closeup.png)
- [03_t4_minimum_clearance_section.png](../renders/i2_local_manufacturing_clearance_hardening_audit/03_t4_minimum_clearance_section.png)
- [04_i3_minimum_clearance_section.png](../renders/i2_local_manufacturing_clearance_hardening_audit/04_i3_minimum_clearance_section.png)
- [05_hardened_manufacturing_harness_isometric.png](../renders/i2_local_manufacturing_clearance_hardening_audit/05_hardened_manufacturing_harness_isometric.png)
- [06_rear_harness_full_seat.png](../renders/i2_local_manufacturing_clearance_hardening_audit/06_rear_harness_full_seat.png)

- `build123d_workbench/out/i2_local_manufacturing_clearance_hardening_audit/I2_LOCAL_HARDENED_MANUFACTURING_HARNESS_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_local_manufacturing_clearance_hardening_audit/i2_local_manufacturing_clearance_hardening_audit.json`

Production modification=0; 8-button propagation=0; N2=0; physical coupon=0; architecture redesign=0. All
157 protected docs/79–87 and prior artifacts retain identical SHA-256 hashes:
**True**.
