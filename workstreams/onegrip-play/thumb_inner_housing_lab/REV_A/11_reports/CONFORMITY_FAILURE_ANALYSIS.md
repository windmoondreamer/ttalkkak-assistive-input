# CONFORMITY_FAILURE_ANALYSIS

Question: *why does the current Thumb inner housing not conform to the current
outer shell the way the original one did?*

Answer, in one line:

```text
The Thumb cartridge was moved by a rigid translation whose component along the
Thumb surface normal is -9.49 mm, while the shell surface was never re-lofted.
Only opening VOIDS were translated and re-cut, so the housing sank away from a
surface that stayed where it was.
```

Every claim below is a measurement, with the script that produced it.

---

## 1. Candidate causes, tested

| hypothesis | verdict | evidence |
|---|---|---|
| old inner housing was never transformed | **FALSE** | A07: part-outer n range is identical `[-3.646, +2.307]` in both frames; docs/54 round-trip residual 0.000000 mm |
| two different transform conventions were used | **FALSE** | A04: `DATUM_P` is exactly the lowered joystick centre; lowered attachment centres on `(u,v) = (0.001, -0.536)` |
| only the shell was lowered | **FALSE, and reversed** | A03: the shell surface did **not** move; the controls did |
| legacy HW504 support forces the geometry | **NOT THE CAUSE** | HW504 spans n `[-12.250, +9.000]`; the conformity loss is on the outer face, 9 mm away |
| boolean reconstruction lost the surface relationship | **PARTLY** | the relationship was never re-derived; the shell was cut with **translated void solids**, not re-lofted |
| different source revision | **FALSE** | A16: all 13 Thumb authority sources byte-identical to baseline |
| local trim/crop error | **FALSE** | A06 re-measured on the combined JaD ∪ JfD shell with the crop extended in n |
| **rigid translation of a cartridge against a curved, unmoved surface** | **CONFIRMED — root cause** | §2 below |

## 2. The root cause, quantified

`THUMB_DELTA = (0, +12.25, −21.00) mm`. Decomposed in the Thumb frame:

```text
along v (across the surface)  +22.42 mm
along n (into the shell)       -9.49 mm
```

The shell surface over the Thumb button field is **curved by about 7 mm in n**:
in the CLEAN shell the wall inner surface at the eight button axes runs from
n = 5.76 (T1, T3) to n = 12.67 (T2) — see A06. Sliding the whole cartridge
22.4 mm across that surface while pushing it 9.5 mm into it cannot preserve a
1.3 mm offset.

Result, same grid, same method (A07):

```text
conformal gap median   +1.292 mm  ->  +9.027 mm
columns within 0.5 mm     854     ->      21
columns beyond 6.0 mm       0     ->   6,123
```

The 7.7 mm shift in median gap is the −9.49 mm normal translation minus the local
surface slope contribution. Nothing else is needed to explain it.

## 3. The same cause is visible on the exterior

The openings were produced by translating the **original opening void solids** by
the same rigid delta and re-cutting. Those voids were normal to the surface at
the *original* location. At the new location the surface has a different normal
and a different depth, so the same tool over-cuts in some places and misses in
others:

| control | opening-tool ∩ source shell (production validation file) | outcome |
|---|---:|---|
| `Button_corner_1` | 233.01 mm³ | over-cut |
| `Button_corner_2` | 241.99 mm³ | over-cut |
| `Button_middle_2` | 161.72 mm³ | partial |
| `Button_side_2` | 110.54 mm³ | mostly sealed |
| `Button_side_1` | 104.40 mm³ | mostly sealed |
| `Button_middle_1` | 53.58 mm³ | sealed |
| `Button_wide_2` | **10.15 mm³** | **sealed** |
| `Button_wide_1` | **9.20 mm³** | **sealed** |

Measured result on the frozen shell (A09, per control's own press axis):
T2 / T7 / T8 = **0.0 % clear path**, T4 = 1.2 %, T6 = 3.9 %, T1 / T3 / T5 = 33–36 %,
joystick 39.8 %. In the original exterior all nine were 100 %.

This is not a separate defect. It is the identical rigid-translation mismatch,
showing up on the outside instead of the inside.

## 4. What this means for the freeze

The brief freezes the exterior and says an internal candidate that does not fit
should be declared failed rather than blaming the exterior. That rule is honoured
here — but the button-sealing finding is **not** an internal-fit problem:

* a button reaching daylight is a property of the shell wall, not of the housing;
* no inner architecture, at any depth or angle, can open a 3.0 mm intact wall;
* the caps sit 3.66 – 3.71 mm **behind** the wall inner surface, so even the
  frozen external cap positions are not on the exterior surface.

It is worth being precise about what would have to be unfrozen, because it is
much less than "move the exterior":

| frozen item | affected? |
|---|---|
| exterior **surface / silhouette** | **no** — the openings are holes in that surface, not the surface |
| Thumb button external **positions** in (u, v) | no |
| Thumb button **press axes** | no |
| joystick external centre and axis | no |
| cap position **along its own axis** (n) | **yes** — caps must come out to the surface, 3.66 – 3.71 mm |
| the nine opening **cut solids** | **yes** — they must be re-derived normal to the local surface |

That is the narrowest possible unfreeze. It is the user's decision, not this
Lab's; nothing was changed.

## 5. Tooling failures found while measuring (recorded so they are not repeated)

1. **`local_box` handedness.** `(U, V, −N)` is left-handed (`U × V = +N`).
   Building a `Plane(x_dir=U, z_dir=−N)` silently yields `y_dir = −V`, so the
   first crop box landed mirrored in v (`v ∈ [−102, −36]` instead of `[−36, +30]`).
   Valid ordering is `(V, U, −N)`. A `assert_local_box` round-trip check was added.
2. **OCC shell-to-shell booleans are unusable here.** `A − B` between two
   near-coincident shell crops returned `A` whole; `A & B` returned
   **−44.90 mm³** (negative) for the JaD pairs and `0.0` for one JFD pair. Both
   directions failed. All shell-region localisation was moved to a ray-parity
   occupancy grid.
3. **Never drop crop-box faces before ray casting.** Filtering them opened the
   mesh and produced odd crossing counts, i.e. broken parity.
4. **Never probe a single shell half at u = 0.** JaD spans u ≳ 0, JfD u ≲ 0, so
   every u = 0 column grazes the seam. Probe the union.
5. **Crop deep enough.** The first crop stopped at n = +14; the Thumb wall
   extends past +16, so the wall was truncated and the first wall map was wrong.
6. **Render sections need the far half, not the near half.** `clip_half` keeps
   `(p−p0)·nrm ≤ 0`; with the camera looking along `−U` the visible half needs
   `nrm = +U`. The first render showed the outside of the shell instead of a cut.
7. Fusing 22 disjoint fragments into one "solid" makes the next boolean return a
   `Null TopoDS_Shape`. Select fragments; do not fuse them.
