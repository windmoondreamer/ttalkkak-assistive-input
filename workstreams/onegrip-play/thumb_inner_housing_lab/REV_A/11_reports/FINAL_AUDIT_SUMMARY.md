# FINAL_AUDIT_SUMMARY — Thumb Inner Housing Lab REV_A

Date 2026-08-24 · local build123d / OCCT · **Onshape API 0 · production writes 0**

---

## 1. Source discovery

`01_source_map/SOURCE_MAP.md`. The frozen Thumb exterior authority is
`JAD/JFD_EXTERIOR_LOWERED_THUMB_V1.step`, decided by geometry (A03), not by name:
the nine lowered Thumb controls are buried **0.000 mm³** in it and 11.3 / 12.0 mm³
in `*_FINGER_V2.step`, while the *original*-position controls are buried
339 / 356 mm³ in it and only 1.7 / 3.0 mm³ in `FINGER_V2`.

Two source-level issues surfaced:

* **`docs/71` used the wrong shell.** It read `JAD/JFD_FINGER_V2.step`, which does
  not carry the lowered Thumb exterior. Every `docs/71` row naming `local_shell`
  was measured against the un-lowered shell.
* **`docs/54`'s 20-part list is an occurrence count.** The exported STEP has 13
  distinct solids and exactly **one** `PushBtn`; eight PushBtn positions cannot be
  checked from it.

## 2. Source safety

`00_admin/SOURCE_BASELINE.md`. All **13 Thumb authority sources byte-identical**
to the pre-work baseline. Writes confined to `thumb_inner_housing_lab/REV_A/`.

**Flag:** six files outside the Lab changed during the session —
`four_edge_leg_harness_captive_pusher_audit.py` (modified) plus five new
I2 / four-edge-leg files and `docs/80`, `docs/81`. Not written by this Lab, not in
the Thumb dependency set, no effect on any conclusion here. Reported because a
concurrent workflow writing into `build123d_workbench/` and `docs/` may not be
expected.

## 3. Original design

`03_original_thumb_analysis/ORIGINAL_THUMB_ANALYSIS.md`.
One swept plate, **2.004 mm** nominal thickness, 40 × 63 mm plan, local bosses to
12 mm, riding **0.4 – 1.6 mm** off the shell inner surface (median **+1.292 mm**)
with a **6.4 %** contact band ≤ 0.30 mm. No separate button-support parts. All
nine controls had **100 %** clear paths through their openings.

## 4. Current failure

`11_reports/CONFORMITY_FAILURE_ANALYSIS.md`.

```text
ROOT CAUSE
The Thumb cartridge was moved by a rigid translation with a -9.49 mm component
along the Thumb surface normal, while the shell surface was never re-lofted -
only the opening VOID solids were translated and re-cut.  The housing sank away
from a surface that stayed put.
```

| | ORIGINAL | CURRENT |
|---|---:|---:|
| conformal gap median | +1.292 mm | **+9.027 mm** |
| columns within 0.5 mm | 854 | **21** |
| columns beyond 6.0 mm | **0** | **6,123** |

The same mismatch appears on the exterior. Clear path along each control's own
press axis: T2 / T7 / T8 = **0.0 %**, T4 = 1.2 %, T6 = 3.9 %, T1 / T3 / T5 = 33–36 %,
joystick 39.8 % — against 100 % for all nine originally. The production validation
file already recorded the signature: the `Button_wide_1/2` opening tools
intersected the shell by only **9.20 / 10.15 mm³**.

## 5. SZH status

`06_keepouts/KEEPOUT_DEFINITION.md`.

```text
SZH-EK056 = PROVISIONAL / WEB REFERENCE (docs/71 quality LOW)
MEASURE ON ARRIVAL
```

Class A preserved (PCB outline, gimbal, shaft, both pots, push switch, mounting
regions, 25° moving envelope). Class B (distal pins, header insulator, knob) may
be trimmed later; a stock-header collision alone does not disqualify the module.
No sub-mm clearance, shaft profile, PCB edge or header geometry is treated as
final.

## 6. N1 / N2 status

External centre and press axis = hard constraint, untouched. Internal harness =
provisional coordination keep-out at 0.50 mm, using the frozen
`N1_N2_SHARED_CARRIER_N1_LOCAL.step`. The four-edge-leg harness now in development
was not redesigned. C01 keep-out residual against it is **0.000000 mm³**.

## 7. C01

`11_reports/CANDIDATE_C01_REPORT.md`. Conformal substrate derived from the frozen
shell inner surface, single solid, 3,374.98 mm³, gap p25/p50/p75 =
**+1.176 / +1.196 / +1.201 mm**, shell intersection **0.000000 mm³**, all keep-outs
clear. Seats and SZH mount deliberately deferred on stated blockers.

## 8. Metrics at a glance

| metric | ORIGINAL | CURRENT | C01 |
|---|---:|---:|---:|
| conformal gap median | +1.292 | +9.027 | **+1.196** |
| gap min | −0.022 | −28.495 | +0.163 |
| columns within 0.5 mm | 854 | 21 | (contact band re-established) |
| shell interference | ~0 | 217.84 mm³ | **0.000000** |
| nominal thickness | 2.004 | 2.004 | 2.400 |
| solids | 1 | 1 | 1 |
| keep-out residual | — | — | 0.000000 mm³ |

## 9. Unknown / measurement required

1. SZH-EK056 actual PCB X/Y/Z, mount pitch and hole Ø, pivot height, shaft
   profile, pot and push-switch envelopes, header geometry, true max tilt.
2. Whether the Thumb switch stays `PushBtn` or becomes ITS-1105 (`CLAUDE.md` §3).
3. Whether the SZH header can be depopulated (Class C, `docs/71`).
4. Actual wire OD / routing for the Thumb cluster.
5. Whether the 25° moving envelope is real; it drives the 223.8 mm³ C01 removed.

## 10. Render paths

All under `thumb_inner_housing_lab/REV_A/08_renders/`. Images 01–03 share one
camera and one section plane; 04–06 share another; 09 and 10 share a viewpoint.

```text
01_ORIGINAL_section.png                 original shell + original Backplate, u = 0
02_CURRENT_section.png                  frozen shell + lowered Backplate, u = 0
03_CANDIDATE_C01_section.png            frozen shell + C01, u = 0
04_ORIGINAL_button_row.png              button row, v = -30
05_CURRENT_button_row.png               button row, v = -30      <- the void
06_CANDIDATE_C01_button_row.png         button row, v = -30      <- restored
07_C01_with_keepouts_section.png        C01 + SZH + moving envelope + N1/N2
08_C01_transparent_shell_iso.png        transparent shell, isometric
09_frozen_exterior_sealed_buttons.png   frozen exterior from outside
10_original_exterior_reference.png      original exterior, same viewpoint
```

Most legible pair: **04 vs 05** (design law vs the failure), then **06**.

## 11. Verdict

```text
CANDIDATE PROMISING - USER REVIEW REQUIRED
```

C01 restores the original conformal relationship against the frozen shell,
exactly, with zero interference and all keep-outs respected. It is a substrate,
not a finished housing.

The blocking item is not internal. With the exterior frozen exactly as delivered,
three Thumb buttons are behind an intact ~3.0 mm wall and two more are ≥ 96 %
sealed, and the caps sit 3.66 – 3.71 mm behind the wall inner surface. No internal
architecture can open a solid wall. The narrowest possible unfreeze — which is the
user's call, not this Lab's — is the **nine opening cut solids plus cap position
along its own axis**; the exterior *surface and silhouette*, the button (u, v)
positions, the press axes and the joystick centre and axis can all stay frozen.

## 12. Next recommended action (audit only — no production apply)

1. **Decide the opening question.** Either accept the narrow unfreeze in §11 or
   state that the Thumb buttons are dropped. Everything downstream depends on it.
2. **Re-run `docs/71` against the correct shell.** Its `local_shell` rows used the
   un-lowered `FINGER_V2` shell.
3. **C02_JOYSTICK_CARRIER** — resolve the 26 mm depth budget: cradle descending
   from the conformal plate, or reference off the opposite wall, or SZH axial
   repositioning. Depends on §9 item 1.
4. **C03_SEATED_PLATE** — add button seats to C01 once the switch is chosen and
   the openings are settled.
5. Keep everything in `thumb_inner_housing_lab/`. Nothing here is production.
