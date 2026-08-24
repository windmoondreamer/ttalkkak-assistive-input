# 86 — I2 manufacturing four-edge harness rebase audit

FINAL VERDICT = **C — A SIMPLE PRINTABLE FOUR-EDGE HARNESS CANNOT PRESERVE THE REQUIRED INSERTION CORRIDOR**

## 1. Current docs/84 harness

The docs/84 audit harness is two rectangular seating-cross boxes plus four oriented rectangular probe prisms.
Each prism has only **0.15 mm** axial Boolean overlap. It is a valid one-solid probe, but not approved
manufacturing geometry. At docs/85 state 18 / U=−5.25 mm the old 15.271882439 mm³ BODY collision decomposes to:

| region | BODY penetration |
|---|---:|
| main U/V cross | 0.000000000 mm³ |
| +U / +V / −V prisms | 0.000000000 mm³ |
| **−U approach prism** | **15.271882439 mm³** |

The old −U corridor was therefore never legitimate.

## 2. Manufacturing rebase

The replacement is one 1.60 mm single-outline four-spoke bottom seat plus four straight 1.60 mm tangential-width
legs. Root embed is 1.40 mm; every root has positive common volume with the seat. −U/+V shell floor points receive
only 0.004/0.121 mm axial depth correction; no angle or root optimization was run.

| root | root U,V,W | shell endpoint U,V,W | axial correction | shared width | shared thickness | minimum neck | actual base/leg common volume |
|---|---|---|---:|---:|---:|---:|---:|
| +U | [3.8615, -0.2, 0.06000000000000005] | [5.08138829728736, 2.1026637357302924, 6.900538427483028] | 0.000 | 1.40 | 1.25 | 1.25 | 2.158117 |
| -U | [-4.255, 0.0, 0.06000000000000005] | [-6.055877825536448, -0.3445084974212549, 5.671444110443599] | 0.004 | 1.60 | 1.60 | 1.40 | 3.491295 |
| +V | [-0.3, 3.925, 0.06000000000000005] | [-2.084890912260996, 5.272116549400704, 7.155309518484693] | 0.121 | 1.30 | 1.60 | 1.30 | 3.239744 |
| -V | [0.33, -3.925, 0.06000000000000005] | [1.752684813086336, -5.288617406781559, 7.280587258261695] | 0.000 | 1.27 | 1.60 | 1.27 | 3.100883 |

## 3. Manufacturing-geometry gate

| gate | result |
|---|---:|
| harness / STEP reimport solid count | **1 / 1** |
| valid / watertight BRep | **True** |
| face/tangent-only / zero-thickness | **0 / 0** |
| minimum structural neck | **1.250 mm** |
| static detailed penetration | **0.000000000 mm³** |
| minimum blind depth / remaining shell | **1.200453 / 1.200134 mm** |
| required docs/85 −U→+U 9-state corridor | **FAIL** |
| 9-state BODY↔HARNESS maximum | **9.421611494 mm³** |
| 9-state all-detailed↔HARNESS maximum | **15.106667023 mm³** |

Overall manufacturing gate = **FAIL** because the required insertion corridor is closed. Ten manufacturing renders
were generated before this decision. Per the STOP rule, the comparable 33-state Sequence B and Sequence C were
**NOT RUN**.

## 4. Why a legal straight −U leg cannot clear the path

- detailed BODY envelope: U ±3.155, V ±3.005, W 0.060…3.560 mm;
- the −U midpoint leg is crossed whenever the BODY centre moves through U=−7.410…−1.100 mm;
- with a 1.60 mm tangential section, V-clearance requires a leg centre at **|V| ≥ 3.805 mm**;
- the adjacent ±V root is at |V|=3.925 mm, leaving only **0.120 mm**, below the 1.20 mm structural rule and
  converting the support into the expressly prohibited corner-post architecture;
- routing the leg below W=0.060 requires abandoning the local direct slot: bounded canonical outward/down rays
  either leave ≤1.178 mm shell after a 1.20 mm blind seat or hit the remote shell outside the I2 local crop.

Thus reducing the blocky prism is insufficient: any nonzero straight approach-side midpoint leg connected to the
frozen upper shell target crosses the rigid BODY swept envelope. The only escapes are a corner relocation, remote
shell target, bent/flexible leg, multi-piece harness, or a different assembly architecture—all out of scope.

## 5. Critical comparison / verdict

| metric | docs/85 old probe harness | new manufacturing candidate |
|---|---:|---:|
| BODY↔HARNESS, comparable 33-state maximum | 15.271882439 mm³ | **NOT RUN — gate FAIL** |
| BODY↔HARNESS, comparable swept volume | 25.221116186 mm³ | **NOT RUN — gate FAIL** |
| gate-only 9-state BODY maximum | — | **9.421611494 mm³** |

The gate-only sample is numerically **5.850270946 mm³ / 38.307%** below the old 33-state maximum, but it is not a
replacement 33-state or swept result and is not promoted as a like-for-like pass metric.

Verdict **C** applies within the required rigid, straight, side-midpoint four-edge architecture. No replacement
architecture was generated.

## 6. FDM / outputs / preservation

The candidate itself is one continuous watertight FDM solid for P1S / 0.4 mm, with no zero-thickness or trapped
internal feature and minimum neck 1.250 mm. It is rejected solely by the actual
insertion-corridor gate.

- [01_current_docs84_harness_isometric.png](../renders/i2_manufacturing_harness_rebase_audit/01_current_docs84_harness_isometric.png)
- [02_current_harness_with_detailed_pushbtn.png](../renders/i2_manufacturing_harness_rebase_audit/02_current_harness_with_detailed_pushbtn.png)
- [03_new_manufacturing_harness_isometric.png](../renders/i2_manufacturing_harness_rebase_audit/03_new_manufacturing_harness_isometric.png)
- [04_new_harness_top_with_detailed_pushbtn.png](../renders/i2_manufacturing_harness_rebase_audit/04_new_harness_top_with_detailed_pushbtn.png)
- [05_plusU_root_closeup.png](../renders/i2_manufacturing_harness_rebase_audit/05_plusU_root_closeup.png)
- [06_minusU_root_closeup.png](../renders/i2_manufacturing_harness_rebase_audit/06_minusU_root_closeup.png)
- [07_plusV_root_closeup.png](../renders/i2_manufacturing_harness_rebase_audit/07_plusV_root_closeup.png)
- [08_minusV_root_closeup.png](../renders/i2_manufacturing_harness_rebase_audit/08_minusV_root_closeup.png)
- [09_main_body_bottom_seating_region.png](../renders/i2_manufacturing_harness_rebase_audit/09_main_body_bottom_seating_region.png)
- [10_detailed_pushbtn_insertion_corridor.png](../renders/i2_manufacturing_harness_rebase_audit/10_detailed_pushbtn_insertion_corridor.png)

- `build123d_workbench/out/i2_manufacturing_harness_rebase_audit/I2_MANUFACTURING_FOUR_EDGE_HARNESS_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_manufacturing_harness_rebase_audit/I2_MANUFACTURING_FOUR_DIRECT_SLOT_SHELL_CROP_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_manufacturing_harness_rebase_audit/i2_manufacturing_harness_rebase_audit.json`

All 135 protected docs/79–85 and prior artifacts retain identical SHA-256
hashes: **True**. Production modification=0; Sequence C=0;
8-button propagation=0; N2 redesign=0; physical coupon=0.
