# 83 — I2 minimum-angle direct-shell harness and assembly audit

ANGLE-REQUIRING LEGS = **4 / 4**

MINIMUM REQUIRED ANGLES = **+U 10.597° / -U 13.006° / +V 7.708° / -V 8.637°**

ONE-PIECE ASSEMBLY = **nominal rectangular mouths NO; simple 0.35 mm/side × 0.30 mm open-entry mouths YES**

FINAL VERDICT = **B — GEOMETRY WORKS BUT ASSEMBLY/FDM REQUIRES SIMPLE REVISION**

## 1. Minimum-angle candidate

The search order was exact: tilt first, root displacement second, functional leg length third.  docs/80 was used
only as a feasible seed.  A 2,476-point exact-W shell map exposed disconnected lower-angle basins; each was then
refined with exact 3×3 B-rep footprints to approximately 0.01°.

| leg | thickness | root shift U,V,W mm | functional length | tilt from +W | angle to U-V | UV azimuth | min remaining shell |
|---|---:|---|---:|---:|---:|---:|---:|
| +U | 1.20 | [0.0, 1.7156249999999997, 0.0] | 7.099 | 10.597° | 79.403° | 17.603° | 1.200 |
| -U | 1.60 | [0.0, -0.5812499999999988, 0.0] | 6.873 | 13.006° | 76.994° | -161.919° | 1.200 |
| +V | 1.60 | [-1.56625, 0.0, 0.0] | 7.981 | 7.708° | 82.292° | 106.830° | 1.202 |
| -V | 1.60 | [1.693125000000003, 0.0, 0.0] | 8.092 | 8.637° | 81.363° | -73.018° | 1.201 |

All four legs are single straight rectangular prisms.  A 0.15 mm same-axis inward tail fuses each prism into the
minimum open cross; printed harness solid count = **1**.  No shoulder,
transition, panel, receiver, strut, carrier, dogleg or adhesive load path is present.

## 2. Static exact gates

- minimum remaining exterior shell at nominal blind floors: **1.200 mm**;
- minimum pusher clearance: **1.250 mm**;
- minimum terminal clearance: **0.001 mm**;
- minimum I3/neighbor clearance: **0.223 mm to I3**;
- minimum corner-feature clearance: **0.803 mm**;
- ITS body, pusher, terminal, neighbor and corner penetration: **0 mm³**.

## 3. Rigid assembly path

Independent directions differ by up to **23.603°**.
The minimax common insertion vector is `[-0.019744523092266302, -0.007269740127812785, 0.99977862784035]`
(tilt 1.206°, azimuth -159.787°).

With nominal 0.20 mm/side rectangular mouths, a 1.60 mm rigid insertion produces maximum instantaneous shell
penetration **0.176958 mm³** and swept collision
**0.309120 mm³**.  It fails.

Option B direction convergence was screened before changing the slot mouth.  The nearest feasible +U/-U
directions still miss the common vector by 12.302° and
12.351°, beyond the 9.462° nominal-clearance cone.

The smallest tested simple revision that passes is a **0.35 mm/side, 0.30 mm-deep rectangular open-entry mouth**
at each blind slot.  The load-bearing lower blind slot remains 0.20 mm/side and 1.20 mm deep.  Mouth-floor remaining
shell is **2.100 mm**.  Across
33 START→PARTIAL→FULL states:

- shell swept collision volume = **0.000000 mm³**;
- maximum pusher penetration = **0.000000 mm³**;
- maximum neighbor penetration = **0.000000 mm³**;
- minimum moving neighbor clearance = **0.000 mm**;
- harness elastic bending assumption = **0**.

## 4. FDM — P1S / 0.4 mm nozzle

Print the open cross flat on the build plate with local +W vertical.  Leg axes are only 7.708°–13.006° from build Z;
no support is required under the legs or inside the ITS cage.  Minimum normal-projected leg thickness is
**1.180 mm** (three 0.4 mm lines at +U before slicing compensation).
The 0.15 mm same-axis tails avoid a zero-volume face-contact root.  Support removal between legs and inside the cage
is therefore not required.  Physical coupon remains mandatory before production release.

## 5. docs/80 comparison

| leg | docs/80 tilt | new minimum tilt | reduction |
|---|---:|---:|---:|
| +U | 19.376° | 10.597° | 8.779° |
| -U | 22.654° | 13.006° | 9.648° |
| +V | 11.867° | 7.708° | 4.159° |
| -V | 13.500° | 8.637° | 4.863° |

Maximum tilt: **22.654° → 13.006°**.
Mean tilt: **16.849° → 9.987°**.

| audit metric | docs/80 | new minimum-angle candidate | change / disposition |
|---|---:|---:|---|
| minimum remaining exterior shell | 1.243 mm | 1.200 mm | -0.043 mm; both ≥1.20 mm |
| minimum I3/neighbor clearance | 0.215 mm | 0.223 mm | +0.007 mm |
| rigid assembly path | not swept-path validated | nominal mouths fail; revised mouths pass | 33-state rigid sweep, bending=0 |
| FDM printability | one fused solid; orientation/support not audited | support-free proposed orientation | P1S/0.4 mm; coupon still required |

## 6. Required renders

- [01_i2_exterior_its_frozen_orientation.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/01_i2_exterior_its_frozen_orientation.png)
- [02_four_roots_top_view.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/02_four_roots_top_view.png)
- [03_plus_U_minimum_angle.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/03_plus_U_minimum_angle.png)
- [04_minus_U_minimum_angle.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/04_minus_U_minimum_angle.png)
- [05_plus_V_minimum_angle.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/05_plus_V_minimum_angle.png)
- [06_minus_V_minimum_angle.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/06_minus_V_minimum_angle.png)
- [07_four_minimum_angle_legs_only.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/07_four_minimum_angle_legs_only.png)
- [08_four_direct_shell_slots_only.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/08_four_direct_shell_slots_only.png)
- [09_leg_slot_sectional_view.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/09_leg_slot_sectional_view.png)
- [10_full_seated_assembly.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/10_full_seated_assembly.png)
- [11_assembly_start.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/11_assembly_start.png)
- [12_assembly_partial_insert.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/12_assembly_partial_insert.png)
- [13_assembly_full_seat.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/13_assembly_full_seat.png)
- [14_assembly_swept_collision_diagnostic.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/14_assembly_swept_collision_diagnostic.png)
- [15_harness_fdm_print_orientation.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/15_harness_fdm_print_orientation.png)
- [16_docs80_vs_new_minimum_angle.png](../renders/i2_minimum_angle_direct_shell_assembly_audit/16_docs80_vs_new_minimum_angle.png)

## 7. Preservation and stop

- `build123d_workbench/out/i2_minimum_angle_direct_shell_assembly_audit/I2_MINIMUM_ANGLE_FOUR_EDGE_HARNESS_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_minimum_angle_direct_shell_assembly_audit/I2_MINIMUM_ANGLE_FOUR_SLOT_SHELL_CROP_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_minimum_angle_direct_shell_assembly_audit/I2_MINIMUM_ANGLE_FULL_SEATED_ASSEMBLY_AUDIT_ONLY.step`
- `build123d_workbench/out/i2_minimum_angle_direct_shell_assembly_audit/i2_minimum_angle_direct_shell_assembly_audit.json`

All 74 docs/79–82 and production artifacts retain identical SHA-256
hashes: **True**.  Production modification = 0; eight-button
propagation = 0; physical coupon = 0; N2 redesign = 0; new inner housing = 0.
