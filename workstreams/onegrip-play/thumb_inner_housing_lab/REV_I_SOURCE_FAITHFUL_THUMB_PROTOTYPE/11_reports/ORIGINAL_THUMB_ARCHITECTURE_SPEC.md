# ORIGINAL_THUMB_ARCHITECTURE_SPEC

What the original OneGrip designer actually built, measured from exact geometry.
This is the internal design reference for REV_I (§3, §25).

Sources: `ORIGINAL_THUMB_CARTRIDGE.step` (13 leaf solids), `THUMB_BACKPLATE`,
and the pre-finger shell pair `{JAD,JFD}_CLEAN_PRE_FINGER.step`.
Scripts: `i02_original_external_stack.py`, `i03_original_joystick_architecture.py`,
plus REV_H `h01`/`h02` for the internal switch stack.

Every axial number is on that control's **TRUE press axis**. The Thumb panel is
inclined and the eight caps sit 0.00–9.38° apart, so a world-Z reading is
meaningless here.

---

## 1. The organising idea

Eight switches and the joystick all bottom out on **one conformal ~2.0 mm
plate**. No boss, no shoulder, no recess, no per-button holder. The plate follows
the grip surface, so it runs deeper under the joystick (−16.8 mm) than under the
buttons (−8.4 mm), and each component simply sits on it.

```text
BUTTON CAP -> ACTUATOR -> SWITCH BODY -> FLAT 2.003 mm PLATE -> TERMINAL SLOTS -> CAVITY
JOYSTICK KNOB -> SHAFT -> HW504 MODULE -> same plate (0.011 mm contact)
```

## 2. Button — internal

| dimension | value | note |
|---|---:|---|
| support-seat bearing | **6.02 × 6.04 mm** flat | switch body sits directly on the plate |
| body-to-plate gap | **0.051 mm** | contact |
| plate thickness | **2.003 mm** | p25/p50/p75 = 1.898 / 2.004 / 2.026 |
| terminal slots | **2 × (1.30 × 6.40 mm)** at **±2.60 mm** | legs splay to 7.568 × 4.632, wider than the 6 mm body |
| cap underside → plate top | **4.759 mm** | the dimension that sets seat depth |
| switch body height | 3.144 mm | |
| actuator | Ø3.51, **1.909 mm** above the body | |
| actuator into the cap | 0.345 mm | engagement |
| terminal drop below the plate | 1.651 mm | 3.654 mm below the plate top face |

The same 4.759 mm and the same 2.00–2.01 mm plate appear at **all eight**
buttons. Only the slot offset varies, by ±0.7 mm.

## 3. Button — external

| dimension | min | max | mean |
|---|---:|---:|---:|
| **unpressed protrusion above the skin** | **1.066** | **1.459** | **1.264** |
| skirt insertion depth into the opening | 3.502 | 3.825 | 3.660 |
| cap height | — | — | ~4.92 |
| lateral clearance to the opening | 0.252 | 0.372 | 0.314 |

* pressed protrusion ≈ **1.01 mm** (1.264 − 0.25 mm travel, **travel PROVISIONAL**)
* the cap has no flange, so it could sink until its top reached the skin — 1.26 mm,
  five times the switch travel, so bottoming never binds
* protrusion correlates with cap tilt at **+0.819**: the flat cap top on a tilted
  axis over a curved panel. The 0.393 mm spread is that curvature, not a second law

```text
ONE COMMON PROTRUSION LAW  =  cap top 1.26 +- 0.20 mm above the local skin
```

## 4. Joystick — internal package

| item | value |
|---|---|
| module (`HW504_COMPONENT_1`) | 1461.114 mm³, axial length **14.250 mm**, max radius 23.011 mm |
| moving stick (`HW504_COMPONENT_2`) | 767.126 mm³, axial length 19.000 mm |
| knob (`SMALL_ATTACHMENT`) | 284.541 mm³, height **11.000 mm**, max radius **7.007 mm** |
| module top / bottom vs skin | −4.793 / **−19.043 mm** |
| **module bottom to plate** | **0.011 mm — it bears on the plate, exactly like the switches** |
| plate near the JOY axis | spans −16.824 to −4.487; nearest material to the axis at the module-top plane **10.210 mm** |
| internal depth consumed | **19.043 mm** from the skin |

## 5. Joystick — external stack

| dimension | value |
|---|---:|
| **knob top above the skin** | **+7.607 mm** |
| knob base above the skin | −3.393 mm |
| exposed shaft between module top and knob base | 1.400 mm |
| shell opening half-width | 7.099 mm |
| knob max radius | 7.007 mm |
| **knob-to-opening clearance** | **0.092 mm** — deliberately snug, the opening guides the knob |

## 6. Button ↔ joystick relationship

| relation | value |
|---|---:|
| **knob top above the tallest cap top** | **+6.556 mm** |
| per-cap, knob top minus cap top | 6.556 – 7.822 mm |
| nearest cap surface to any joystick part | **6.788 mm** (T7/T8) |
| centre spacing, JOY → T7/T8 | 20.60 mm |
| centre spacing, JOY → T2 | 30.98 mm |
| centre spacing, JOY → T4/T6 | 32.84 mm |
| centre spacing, JOY → T1/T3 / T5 | 42.66 / 41.92 mm |

The thumb reaches a knob standing 7.6 mm proud and buttons sitting 1.3 mm proud
— a **6.6 mm** height difference that separates the two gestures.

## 7. Packaging

| item | value |
|---|---|
| adjacent button centres | 10.301 – 10.901 mm |
| across rows | 14.678 – 16.244 mm |
| plate plan bbox (local) | u [−20, +20], v [−49, +14] |
| plate volume / faces | 5899.528 mm³ / 85 |
| plate conformal gap to the shell | p50 **1.292 mm**, p05 0.253, p90 1.648 |
| **plate-to-shell contact-band fraction** | **6.39 %** — the plate touched the shell over a small fraction of its area |
| wiring | terminals drop 1.651 mm below the plate into the open cavity |
| assembly | one plate, everything laid on it from inside; caps drop into their bores from outside |

**Load path principle (§21):** button and joystick loads go into the plate, the
plate spreads them, and only ~6 % of the plate area actually lands on the shell.
The original did *not* rely on continuous contact — it relied on a stiff plate
with a few broad landings.

---

## 8. Appendix — what the CURRENT frozen geometry does to this

Measured the same way against the exact approved lowered shell.

| dimension | ORIGINAL | CURRENT as inherited | delta |
|---|---:|---:|---:|
| cap protrusion, T1 | +1.385 | **−4.193** | −5.578 |
| cap protrusion, T2 | +1.066 | **−6.152** | −7.217 |
| cap protrusion, T3 | +1.459 | −4.116 | −5.575 |
| cap protrusion, T4 | +1.291 | −5.603 | −6.894 |
| cap protrusion, T5 | +1.166 | −4.885 | −6.051 |
| cap protrusion, T6 | +1.338 | −5.545 | −6.883 |
| cap protrusion, T7 | +1.200 | **−7.179** | −8.378 |
| cap protrusion, T8 | +1.211 | −7.162 | −8.373 |
| knob top | +7.607 | **−1.732** | −9.339 |
| JOY opening half-width | 7.099 | **6.555** | −0.544 |

**The inherited caps and knob are buried inside the openings, not protruding.**
They are the original parts rigidly translated by `THUMB_DELTA`, whose −9.49 mm
component along the surface normal took them below a skin that was never
re-lofted. Nothing frozen is wrong — the caps were simply never re-derived.

This is why REV_I places the seats from the **restored** cap position rather than
the inherited one, and why the knob must be a new part (§12 permits replacing it).
