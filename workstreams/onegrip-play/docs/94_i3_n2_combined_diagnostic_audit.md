# 94 — I3 + N2 combined diagnostic audit

```text
I3 / N2 combined diagnostic result:

I3 architecture = I3-B — MULTIPLE LOCAL CORRECTIONS REQUIRED
I3 primary failure = FULL-SEAT I3 -U leg ↔ frozen I2 harness collision
I3 local-only correction plausible = YES

N2 viable mechanical slots = 2/4
N2 plausible local-contact supports = 2/4
N2 +U JaD seam-side support = ASSEMBLY-LIMITED
N2 +V local contact support = POSSIBLE

REMOTE/THUMB-WALL SUPPORT REQUIRED = NO
```

## Scope and preservation

- Diagnostic and measurement geometry only. New harness/slot/foot/pad/boss/bridge/solution STEP count: **0**.
- Frozen buttons N1/I2/M3/M4/N3/I4 were not modified. Production modification count: **0**.
- Authority hashes preserved: **True** across 227 files.

## I3 — Exact failure decomposition

| Item | Result |
|---|---|
| I3↔I2 harness primary collision pair | I3 -U leg ↔ I2 harness |
| I3↔I2 harness penetration | 7.229763108 mm³ total; 5.555131963 mm³ in primary region |
| I3↔I2 PushBtn primary collision pair | I3 central seat ↔ I2 T3 |
| I3↔I2 PushBtn penetration | 0.073247828 mm³ total |
| FULL SEAT collision exists? | YES — frozen I2 interference |
| insertion-only collision exists? | YES — +U-foot early shell contact |
| +U foot causes early shell contact? | YES, exclusively at 25/50/75% |
| minimum local correction required | -U: 0.868544 mm along V; seat/T3: 0.496874 mm along V; foot lead-in: 0.051864 mm along U |
| I3 architecture verdict | I3-B — MULTIPLE LOCAL CORRECTIONS REQUIRED |

### I3 ↔ I2 harness at FULL SEAT

Exact total = **7.229763108 mm³**. Logical masks are disjoint; shared root material belongs to the central seat.

| I3 region | I2 harness penetration (mm³) |
|---|---:|
| central seat | 1.674631144 |
| +U foot | 0.000000000 |
| +U leg | 0.000000000 |
| -U leg | 5.555131963 |
| +V leg | 0.000000000 |
| -V leg | 0.000000000 |

PRIMARY LIMITING I3 REGION = **-U leg**. Full-seat collision = **YES**; insertion-only = **NO**.

### I3 ↔ I2 detailed PushBtn at FULL SEAT

Exact pairwise total = **0.073247828 mm³**. Primary pair = **I3 central seat ↔ I2 T3**, penetration = **0.062026274 mm³**.

| I3 region | I2 detailed part | penetration (mm³) |
|---|---|---:|
| central seat | main body | 0.011183325 |
| central seat | T3 | 0.062026274 |
| -U leg | main body | 0.000038228 |

Full-seat collision = **YES**; insertion-only = **NO**.

### I3 early shell contact

| State | +U foot | +U leg | seat | other legs | exact total (mm³) |
|---|---:|---:|---:|---:|---:|
| 25% | 0.000140463 | 0.000000000 | 0.000000000 | 0.000000000 | 0.000140463 |
| 50% | 0.004949602 | 0.000000000 | 0.000000000 | 0.000000000 | 0.004949602 |
| 75% | 0.007011563 | 0.000000000 | 0.000000000 | 0.000000000 | 0.007011563 |

Is early shell contact caused only by the +U contact foot? **YES**.
It exists only on the insertion path; FULL SEAT has intended finite-area foot contact rather than unintended volumetric penetration.

### Minimum local correction measurements — no edits applied

- Full-seat harness limiter: **0.868544 mm** local trim/removal envelope along V on **-U leg**.
- Detailed PushBtn limiter: **0.496874 mm** along local V for **I3 central seat ↔ I2 T3**.
- Early-contact lead-in: **0.051864 mm** collision-envelope removal at 75%, along local U.
- Diagnostic local normal directions = `[0.0, 1.0, 0.0]`, `[0.0, 1.0, 0.0]`, `[1.0, 0.0, 0.0]` respectively; no correction solid was made.

These are exact collision-solid envelope thicknesses, not generated corrections. Because the full-seat I2 conflict and the insertion-only shell lead-in occur in distinct constraints, verdict = **I3-B — MULTIPLE LOCAL CORRECTIONS REQUIRED**. The 3-slot + 1-contact architecture can **likely remain**, but one isolated trim is insufficient.

## N2 — Support architecture diagnosis

| Leg | Current state | Local support exists? | Same-half? | Seam involved? | Contact-only feasible? | Likely support type |
|---|---|---|---|---|---|---|
| -U | valid slot | YES | YES | NO | not required | mechanical slot |
| -V | 0.120358 mm deficit | YES, after micro-thickening | YES | NO | not required | mechanical slot |
| +U | JfD 0/9; JaD local land at 1.050 mm | YES on JaD | NO | YES | YES, closure-created | seam-side local contact |
| +V | opening/edge crossing for slot | YES | YES | NO | YES | local contact foot |

### N2 -V micro-thickening diagnosis

- Can it become a normal blind slot with micro-local inward thickening? **YES**.
- Required inward thickness = **0.120358 mm**.
- Minimum diagnostic pad footprint = **3.100 × 2.800 mm**.
- Added volume estimate = **1.044710 mm³**; outer exterior change required = **0 mm**.

### N2 +U seam diagnosis

- At the natural footprint: JfD = **0/9**, JaD material = **3/9**, opening void = **6/9**.
- A shifted but still local +U JaD footprint exists **1.050 mm** away: **9/9**, remaining shell **1.730939 mm**.
- If JaD/JfD are treated as the final assembled shell, a geometrically valid local JaD reaction surface exists: **YES**.
- A JaD blind slot would cross and mechanically bridge the physical seam: **YES**, therefore it is **not assembly-compatible**.
- A non-captive compression contact established by JaD closure is assembly-compatible but sequence-limited. Classification: **N2+U-2 — JaD LOCAL SEAM-SIDE SUPPORT POSSIBLE / ASSEMBLY-LIMITED**.

### N2 assembly sequence

| Sequence | Geometrically plausible? | Shell halves can close? | Harness removable? | Reason |
|---|---|---|---|---|
| A — harness before JaD closure | YES, CONTACT-ONLY | YES | YES, AFTER JaD REOPENING | JaD closure can establish local compression contact; a JaD blind slot would not accept the frozen harness by this closure motion. |
| B — harness after partial shell assembly | NO | NOT APPLICABLE | NO DIRECT REAR PATH | simultaneous access to JfD slots and a JaD seam-side blind engagement is not available after partial closure. |
| C — JaD closure creates support | YES, CONTACT-ONLY | YES | YES, AFTER SHELL OPENING | closure may create a non-captive +U compression reaction; it must not be modeled as a cross-seam blind slot or captive bridge. |

### N2 +V local contact diagnosis

- Nearest edge-measured local patch offset from the natural target = **0.377700 mm**; frozen root-to-patch UV distance = **1.729087 mm**.
- The original 1.60 × 1.30 mm envelope crosses the edge: **20/25**.
- A 1.60 × 1.30 mm patch placed from the measured edge with 0.030 mm margin has **25/25** coverage. Frozen root and angle authority were not searched.
- Available local surface area ≈ **2.084955 mm²**; simple foot contact ≈ **2.080000 mm²**.
- Minimum shell thickness under the accepted diagnostic patch = **1.896561 mm** (required diagnostic support threshold = 1.200 mm).
- Local shell normal = `[0.057903288, -0.037340774, 0.997623614]`; straight reaction-axis angle = **21.539101°**.
- Side identity preserved = **YES**; remote/Thumb wall required = **NO**; bondless compression path possible = **YES**.

## N2 support-count decision

- Realistic normal mechanical slots: **2/4** (`-U`, micro-thickened `-V`).
- Plausible local compression contacts: **2/4** (`+U` JaD closure-contact, `+V` JfD local contact).
- JaD seam-side support is geometrically possible: **YES**.
- JaD blind-slot/seam bridge is assembly-compatible: **NO**; closure-created contact is **YES, sequence-limited**.
- N2 requires a fundamentally new architecture: **YES** — a diagnostic direction of 2 mechanical slots + 2 local contacts, not a four-slot architecture.
- Restraint grade: **PLAUSIBLE**. Two non-collinear slots provide retention; the two opposite local contacts can close the press-load support polygon. A captive JaD seam bridge is **INVALID**.

## Outputs

- `renders/i3_n2_combined_diagnostic_audit/01_i3_i2_harness_limiting_collision.png`
- `renders/i3_n2_combined_diagnostic_audit/02_i3_i2_detailed_pushbtn_limiting_collision.png`
- `renders/i3_n2_combined_diagnostic_audit/03_i3_early_plus_u_foot_shell_contact.png`
- `renders/i3_n2_combined_diagnostic_audit/04_i3_full_seat_context.png`
- `renders/i3_n2_combined_diagnostic_audit/05_n2_jad_jfd_seam_plus_u_natural_support.png`
- `renders/i3_n2_combined_diagnostic_audit/06_n2_plus_v_local_contact_region_section.png`
- `renders/i3_n2_combined_diagnostic_audit/07_n2_minus_v_shell_thickness_section.png`
- `renders/i3_n2_combined_diagnostic_audit/08_n2_complete_local_support_map.png`

- JSON: `build123d_workbench/out/i3_n2_combined_diagnostic_audit/i3_n2_combined_diagnostic_audit.json`
- Solution STEP artifacts: **0**

```text
Recommended next design action for I3 = later test three bounded local corrections only: -U-leg/I2 clearance, central-seat/T3 clearance, and +U-foot entry lead-in.
Recommended next design action for N2 = later validate a 2-slot + 2-contact, Sequence-C shell-closure architecture; never create a captive JaD seam bridge.
```

Production geometry modification = 0.
