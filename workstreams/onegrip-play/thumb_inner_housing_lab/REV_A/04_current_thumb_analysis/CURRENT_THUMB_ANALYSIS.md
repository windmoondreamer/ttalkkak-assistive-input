# CURRENT_THUMB_ANALYSIS — the frozen lowered Thumb, measured

Sources: `a02`, `a03`, `a04`, `a05`, `a06`, `a07`, `a08`, `a09`, `a10`.

---

## 1. What "current Thumb inner housing" actually is

There is **no production Thumb inner housing**. `docs/53` states plainly that the
lowered exterior was an exterior-first mockup and that internal design is
`DEFERRED`; `docs/54` classifies the Backplate as *adapter required* and creates
nothing. The only thing that plays the role of a current inner housing is the
**original Backplate rigidly translated by (0, +12.25, −21.00) mm**, which is what
`docs/72`'s fixture also uses ("lowered Thumb Backplate").

So the comparison in this Lab is:

```text
ORIGINAL   original Backplate   vs  original shell
CURRENT    same Backplate + rigid translation  vs  frozen lowered shell
```

Volume is identical in both (5,899.5278 mm³) and the round-trip residual in
`docs/54` is 0.000000 mm — it is the same part, moved.

## 2. How the frozen exterior was built

From `integrated_exterior_clean_v1.py` / `integrated_exterior_lowered_thumb_v1.py`:

1. start from the clean pre-Finger shells
2. **fill** the original Thumb openings back in (`restore_original_thumb_openings`)
3. take the original opening **void solids** and translate them by the same rigid
   `(0, +12.25, −21.00)`
4. cut the restored shell with those translated voids + the Finger-8 cutters
5. cut again with 9 `thumb_user_side_service_box` tools — each is a **world-axis
   AABB of the control grown by 0.80 mm**, clipped to a Thumb-side slab

Nothing re-lofted the shell surface. The controls and the opening voids moved;
the surface did not.

## 3. Conformity, measured on the same grid as the original

Gap = shell inner surface − Backplate outer surface, 0.5 mm columns:

| metric | ORIGINAL | CURRENT |
|---|---:|---:|
| overlapping columns | 6,260 | 7,293 |
| gap median | **+1.292 mm** | **+9.027 mm** |
| gap mean | +1.194 mm | +8.200 mm |
| gap min / max | −0.022 / +4.789 | −28.495 / +14.804 |
| columns within 0.5 mm (contact band) | 854 | **21** |
| columns within 1.0 mm | 1,975 | 47 |
| columns beyond 3.0 mm | 131 | 6,888 |
| columns beyond 6.0 mm | **0** | **6,123** |
| interfering columns | 4 | 189 |

Sanity check on frame registration: the part-outer n range is **[−3.646, +2.307]
in both cases**, i.e. the part sits at identical local coordinates in its own
frame. Everything that changed is the shell.

Caveat: the CURRENT `min = −28.495 mm` is a wall-slab selection artefact in a
handful of columns where the heuristic picked the far (palm-side) wall; the
distribution (median, quartiles, tail counts) is robust and is what the finding
rests on.

## 4. Where the wall actually is

Material slabs along each control axis, combined JaD ∪ JfD shell (A06). Probing
one half alone is invalid: JaD spans u ≳ 0 and JfD u ≲ 0, so every u = 0 column
grazes the split seam.

| control | FROZEN Thumb-wall slab (n) | thickness | cap n | cap top − wall inner |
|---|---|---:|---|---:|
| T1_corner_1 | none (fully open) | — | 1.30 … 6.66 | — |
| T2_middle_1 | 11.056 … 12.733 | 1.677 | 2.06 … 7.35 | −3.706 |
| T3_corner_2 | none (fully open) | — | 1.29 … 6.67 | — |
| T4_side_1 | 11.204 … 12.136 | 0.932 | 2.06 … 7.49 | −3.714 |
| T5_middle_2 | none (fully open) | — | 1.30 … 6.58 | — |
| T6_side_2 | 11.197 … 12.060 | 0.863 | 2.06 … 7.49 | −3.707 |
| T7_wide_1 | 11.459 … 14.441 | **2.981** | 2.96 … 7.77 | −3.689 |
| T8_wide_2 | 11.428 … 14.416 | **2.988** | 2.96 … 7.77 | −3.658 |
| JOYSTICK | none (fully open) | — | 3.40 … 14.40 | — |

For comparison the same columns in the CLEAN shell carry a 2.99 – 3.26 mm wall
whose position varies from n = 5.76 to n = 12.67 across the cluster — the surface
is curved by about 7 mm over the button field. A rigid translation of the opening
voids cannot follow that.

## 5. The exterior is not currently open

Two independent methods.

**A08 — footprint projection along n, cap bbox footprints:**

| control | FROZEN open | CLEAN open |
|---|---:|---:|
| T1 | 55.4 % | 76.7 % |
| T2 | **0.0 %** | 96.6 % |
| T3 | 57.9 % | 73.3 % |
| T4 | 8.2 % | 96.3 % |
| T5 | 33.8 % | 93.8 % |
| T6 | 9.9 % | 96.6 % |
| T7 | **0.0 %** | 96.4 % |
| T8 | **0.0 %** | 96.4 % |
| JOYSTICK | 62.5 % | 85.2 % |

**A09 — straight clear path along each control's OWN press axis** (900 samples
per cap, so the tilt of each button is respected):

| control | ORIGINAL | FROZEN | delta |
|---|---:|---:|---:|
| T1_corner_1 | 100.0 % | 34.3 % | −65.7 pp |
| T2_middle_1 | 100.0 % | **0.0 %** | −100.0 pp |
| T3_corner_2 | 100.0 % | 36.4 % | −63.6 pp |
| T4_side_1 | 100.0 % | **1.2 %** | −98.8 pp |
| T5_middle_2 | 100.0 % | 32.9 % | −67.1 pp |
| T6_side_2 | 100.0 % | **3.9 %** | −96.1 pp |
| T7_wide_1 | 100.0 % | **0.0 %** | −100.0 pp |
| T8_wide_2 | 100.0 % | **0.0 %** | −100.0 pp |
| JOYSTICK | 100.0 % | 39.8 % | −60.2 pp |

A10, ray from each cap's outermost point along its own axis, confirms the same
thing part by part: T1 1.09 / T2 2.95 / T3 1.07 / T4 1.61 / T6 1.57 / T7 3.27 /
T8 3.20 mm of air, then an intact 2.9 – 3.0 mm wall.

The production validation file already contains the signature of this without
naming it: `Button_wide_1` and `Button_wide_2` opening tools intersected the
source shell by only **9.20** and **10.15 mm³**, against 233.0 and 242.0 mm³ for
`Button_corner_1/2`. A 9 mm³ intersection cannot make an 8 × 8 mm opening through
a 3 mm wall.

## 6. Renders

* `02_CURRENT_section.png`, `05_CURRENT_button_row.png` — the void between plate and wall
* `09_frozen_exterior_sealed_buttons.png` — the exterior, buttons behind the wall
