# SOURCE_MAP — Thumb Inner Housing Lab REV_A

Date: 2026-08-24
Mode: local build123d / OCCT, read-only on all production geometry, Onshape API 0.

Names in the task brief were mapped to real files by inspection, not by guessing.
Where two production scripts disagreed about which file is "current", the winner
was decided by geometry (A03), not by filename.

---

## 1. Authority table

| Role in the brief | Actual file | Authority | Format |
|---|---|---|---|
| current production Thumb **exterior** (max-lowered) | `build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JAD_EXTERIOR_LOWERED_THUMB_V1.step` + `JFD_...` | **PRIMARY** | exact B-rep |
| original OneGrip Thumb **exterior** | `local_cad/reference/JAD_CLEAN_PRE_FINGER.step` + `JFD_...` | PRIMARY | exact B-rep |
| pre-lowering shell with Finger-8 only | `build123d_workbench/out/finger_controls_v2/JAD_FINGER_V2.step` + `JFD_...` | superseded for Thumb | exact B-rep |
| original Thumb **inner housing** | `THUMB_BACKPLATE` inside `build123d_workbench/out/original_thumb_module_reuse_audit/ORIGINAL_THUMB_CARTRIDGE.step` | PRIMARY | exact B-rep |
| "current" Thumb inner housing | same Backplate, rigidly translated: `.../LOWERED_ORIGINAL_THUMB_CARTRIDGE.step` | PRIMARY | exact B-rep |
| original Thumb module (source) | `build123d_workbench/out/finger_thumb_joint_feasibility/THUMB_TARGET_EXACT_MODULE.step` | PRIMARY | exact B-rep |
| HW504 reference | `THUMB_JOYSTICK_HW504_COMPONENT_1/2` inside the cartridge STEP | REFERENCE / PLACEHOLDER | exact B-rep |
| SZH-EK056 reference | `local_cad/reference/SZH_EK056_WEB_REFERENCE.step` (+ `.json`) | **PROVISIONAL** | exact B-rep of an approximate model |
| SZH actual-fit fixture | `build123d_workbench/out/szh_actual_fit_fixture/*` , `docs/72` | test fixture, not geometry authority | STEP/STL |
| N1/N2 internals | `build123d_workbench/out/n1_production_intent_mechanism/N1_N2_SHARED_CARRIER_N1_LOCAL.step` | frozen, keep-out only | exact B-rep |
| original shell-side fastening | `build123d_workbench/out/original_thumb_module_reuse_audit/ORIGINAL_FASTENING_REFERENCE.step` | REFERENCE | exact B-rep |
| Thumb docs | `docs/37, 38, 39, 53, 54_original_thumb_module_reuse_audit, 55, 56, 57, 71, 72` | narrative | md |
| generators | `integrated_exterior_clean_v1.py`, `integrated_exterior_lowered_thumb_v1.py`, `original_thumb_module_reuse_audit.py`, `finger_controls_v2.py`, `szh_ek056_web_reference.py` | read only, never executed | py |

STL was never used as authority. Every measurement in this Lab comes from exact
B-rep, tessellated locally at a stated tolerance for ray work only.

---

## 2. Which shell is the frozen exterior? (resolved by geometry)

Two production scripts disagree:

* `original_thumb_module_reuse_audit.py` → `*_EXTERIOR_LOWERED_THUMB_V1.step`
* `szh_ek056_provisional_thumb_integration_audit.py` → `*_FINGER_V2.step`

A03 settled it by placing the Thumb control solids in both positions and
measuring how much of each control is buried in shell material:

| control set | position | buried in `LOWERED_THUMB` | buried in `FINGER_V2` | buried in `CLEAN` |
|---|---|---:|---:|---:|
| 9 Thumb controls | ORIGINAL | 339.0 / 355.7 mm³ | 1.7 / 3.0 mm³ | 1.7 / 3.0 mm³ |
| 9 Thumb controls | LOWERED | **0.0 / 0.0 mm³** | 11.3 / 12.0 mm³ | 11.3 / 12.0 mm³ |

`FINGER_V2` and `CLEAN` still carry the **original** Thumb openings and are
byte-identical in the Thumb region. Only `*_EXTERIOR_LOWERED_THUMB_V1.step`
carries the lowered openings.

```text
FROZEN THUMB EXTERIOR AUTHORITY
= build123d_workbench/out/integrated_exterior_lowered_thumb_v1/
      JAD_EXTERIOR_LOWERED_THUMB_V1.step
      JFD_EXTERIOR_LOWERED_THUMB_V1.step
```

### Consequence for docs/71

`docs/71` used `JAD/JFD_FINGER_V2.step` as `local_shell`. That shell does not
have the lowered Thumb exterior. Every `docs/71` row naming `local_shell`
(`PCB↔local_shell` 69.5 / 111.7 mm³, `SHAFT↔local_shell`, `HEADER_PLASTIC↔local_shell`,
`REMOVABLE_KNOB↔local_shell`) was therefore measured against the **un-lowered**
Thumb shell. Those rows should be re-run before being used as evidence.
The `docs/71` rows that involve only N1/N2 and the SZH module are unaffected.

---

## 3. Frames

```text
CURRENT / FROZEN local frame
  origin  DATUM_P = (-0.216040135, -23.149076642, 40.496179115)   world mm
  u       DATUM_U = ( 0.999999460,  0.000710605, -0.000757865)
  v       DATUM_V = ( 0.001022863, -0.801127445,  0.598492917)
  n       OUTWARD = -DATUM_N = (0.000181854, 0.598493369, 0.801127739)

ORIGINAL local frame
  origin  DATUM_P - THUMB_DELTA = (-0.216040135, -35.399076642, 61.496179115)
  same u, v, n
```

`DATUM_P` was confirmed (A04) to be the **lowered** joystick centre: the lowered
`Small_joystick_attachment` centres on `(u, v) = (0.001, -0.536)`, the original
one on `(-0.024, 21.846)`.

`THUMB_DELTA = (0, +12.25, -21.00) mm`, of which **−9.49 mm is along n** (into
the shell) and +22.42 mm is along v.

Handedness note: `(U, V, -N)` is **left**-handed (`U × V = +N`). The valid
placement ordering is `(V, U, -N)`, which is also what
`szh_actual_fit_fixture.py` uses.

---

## 4. Part-count discrepancy found in the source

`docs/54` lists 20 Thumb parts including `THUMB_BUTTON_1_PUSHBTN` …
`THUMB_BUTTON_8_PUSHBTN`. The exported STEP contains **13 distinct solids** and
exactly **one** `PushBtn` and **two** `HW504` solids; `THUMB_TARGET_EXACT_MODULE.step`
likewise carries one `PushBtn` and one `HW504_B`.

The docs/54 count is an assembly-occurrence count, which is legitimate, but the
STEP cannot be used to check eight PushBtn positions — only one exists. Keep-out
work in this Lab therefore uses the cap-derived control axes, not PushBtn solids.
