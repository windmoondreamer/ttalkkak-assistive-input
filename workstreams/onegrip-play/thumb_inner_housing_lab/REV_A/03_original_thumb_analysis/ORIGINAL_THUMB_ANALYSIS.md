# ORIGINAL_THUMB_ANALYSIS — how the original inner housing conformed

Sources: `a11_original_backplate_anatomy.py`, `a07_conformity_map.py`,
`a08_opening_map.py`, `a09_cap_axis_exposure.py`.
All numbers measured from exact B-rep, never from STL.

---

## 1. The architecture

The original OneGrip Thumb module has **no separate button-support parts**.
Support, retention and spacing are all integrated into one part:

```text
Small_joystick_attachment
        +
HW504 module (2 exact solids)
        +
8 button caps + 8 PushBtn occurrences
        +
ONE swept Backplate            <-- the inner housing
        +
JaD/JfD shell capture
        +
3 shell-side M3 screws
```

The Backplate holds all eight button centres, spacings and travel axes in one
rigid relationship, and the shell closure captures it. That is the whole
mechanism.

## 2. Measured design law of the Backplate

| property | measured value |
|---|---|
| volume | 5,899.5278 mm³ |
| B-rep faces | 85 |
| plan extent (local u, v) | u [−20.0, +20.0], v [−49.0, +14.0] → 40 × 63 mm |
| **nominal thickness** | **2.004 mm** (p25 1.898 / p50 2.004 / p75 2.026) |
| local bosses | p95 6.309 mm, p99 12.014 mm, max 12.057 mm |
| topology | 6,814 single-slab columns vs 862 double-slab → genuinely one sheet |

So: **a constant 2 mm swept sheet with local bosses**, not a block.

## 3. The conformal law — the thing that broke

Gap = (shell inner surface) − (Backplate outer surface), per 0.5 mm column,
in the original frame:

| percentile | gap (mm) |
|---:|---:|
| p01 | +0.123 |
| p05 | +0.253 |
| p10 | +0.395 |
| p25 | +0.829 |
| **p50** | **+1.292** |
| p75 | +1.500 |
| p90 | +1.648 |
| p99 | +3.828 |

Summary over 6,260 overlapping columns: min −0.022, mean +1.194, max +4.789,
only **4 interfering columns**, **0 columns beyond 6 mm**.

Contact / load-transfer band (gap ≤ 0.30 mm): **400 columns = 6.4 %** of the
overlap. The plate does not float — it lands on the shell along a band and
carries press load into it.

```text
ORIGINAL CONFORMAL LAW
    outer face rides 0.4 - 1.6 mm off the shell inner surface,
    median 1.29 mm,
    with a 6.4 % contact band and no region further than 4.8 mm.
```

## 4. Exterior in the original state

Along each control's own press axis, straight-path exposure through the shell
(A09, 900 samples per cap):

| control | clear path |
|---|---:|
| T1 … T8, JOYSTICK | **100.0 % each** |

Footprint-projection method (A08) agrees: 73.3 – 96.6 % open per footprint,
mean residual wall 0.02 – 0.45 mm.

Every original control had a fully cut opening normal to the local surface.

## 5. What is reusable, and what the reuse ratio actually counts

`docs/54` reports 90.0 % reuse over 20 parts. Two clarifications from this Lab:

1. The 20 is an **assembly-occurrence** count. The exported STEP holds 13
   distinct solids: 1 Backplate, 8 caps, **1** PushBtn, 2 HW504 solids,
   1 attachment. Eight PushBtn positions cannot be verified from that file.
2. The reusable content that matters for this task is not the part list but the
   **design law in §2 and §3**. That law is fully transferable to the frozen
   shell and is exactly what candidate C01 re-derives.

## 6. Renders

* `08_renders/01_ORIGINAL_section.png` — section at u = 0
* `08_renders/04_ORIGINAL_button_row.png` — section at v = −30, button row
* `08_renders/10_original_exterior_reference.png` — exterior, same viewpoint as image 09

In `04` the orange Backplate sits directly under the shell wall with a thin,
even gap along the whole span. Compare with `05` (current).
