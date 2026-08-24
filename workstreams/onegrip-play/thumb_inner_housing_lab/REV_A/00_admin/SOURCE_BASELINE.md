# SOURCE_BASELINE — production integrity

Machine-readable manifest: `00_admin/SOURCE_BASELINE.json` (213 files at capture),
re-check output: `00_admin/a16_source_check.json`.

## Repository state at Lab start

```text
repo      C:/Users/User/Desktop/OneGrip-Play
branch    main
HEAD      15be4594c392573bf056eb4c2444e387be1c24c5
worktree  ALREADY DIRTY before this Lab: 16 modified + 19 untracked paths
```

The working tree was already dirty when the Lab started (Finger button-harness
work in progress: `docs/73, 75-79`, `four_edge_leg_harness_captive_pusher_audit.py`,
`button_fdm_coupon`, `szh_actual_fit_fixture` outputs and renders). That state was
recorded, not cleaned.

`git` refused to operate on the repo (`dubious ownership`: `.git` is owned by
`CodexSandboxOffline`, the session user is `User`). Every git command in this Lab
used `git -c safe.directory=...` so that **no global git config was modified**.

## Write scope

```text
WRITES ALLOWED   thumb_inner_housing_lab/REV_A/**
WRITES MADE      thumb_inner_housing_lab/REV_A/** only
PRODUCTION EDIT  0
ONSHAPE API      0
```

No production Python module was executed. Two production modules were *imported*
for constants only, after checking that all of their writes are guarded behind
`if __name__ == "__main__"`:

* `build123d_workbench.szh_ek056_web_reference` (SZH constants + `build_reference()`)
* the Lab's own copies of helper logic; all other production generators were read
  as text and re-implemented locally rather than imported.

## Re-check at Lab end

### Thumb authority sources — 13 of 13 UNCHANGED

| source | sha256 |
|---|---|
| `JAD_EXTERIOR_LOWERED_THUMB_V1.step` | `b223757ee25fdd5eddf710b8666bcd388d4221235d8d876f620eb0005d5b75b6` |
| `JFD_EXTERIOR_LOWERED_THUMB_V1.step` | `d1bf68b105dce11374ab1f89981ee503a5591d2ff7fa5175777432171855bf7f` |
| `JAD_CLEAN_PRE_FINGER.step` | `01f5708a29ca46b0f9f13b5c63b5f4d9b7b46bcf04fc8b0a55b806085f1ff4f0` |
| `JFD_CLEAN_PRE_FINGER.step` | `8d290891dd93f16f50789f24ef7d27c754b27b4250caa1ebb3cb587648475792` |
| `JAD_FINGER_V2.step` | `a477aa79e55ddb21fb2a45c7f616544f6eb4844b593f61cf7d45303476c5a762` |
| `JFD_FINGER_V2.step` | `d457d5d9b305a4c7d77e21aab3cb7d33336d672d4d8bf031e6158de44c26ad50` |
| `ORIGINAL_THUMB_CARTRIDGE.step` | `ee6ed6848e7c0481a2c73639c85fc39bf63ac837514ca13b16bdc1bc6e075527` |
| `LOWERED_ORIGINAL_THUMB_CARTRIDGE.step` | `f7a7cea568b08ff1565b90c886de955cccf246bf88b7f4a46a00ca61f35c4bc2` |
| `THUMB_TARGET_EXACT_MODULE.step` | `adc870ffaf55a9342d62df89f162827a744bdf1d43060c0fbb69f7c8e8089fe9` |
| `THUMB_ORIGINAL_PRE_FINGER_REFERENCE.step` | `c80a6e44dab38b88791d6167d9a7e5d3e800f48db316e5cbe988eb997d99d21d` |
| `N1_N2_SHARED_CARRIER_N1_LOCAL.step` | `2485e34f8716395459f1f7b10384fd73a33695472f9aae689cf321d583830756` |
| `ORIGINAL_FASTENING_REFERENCE.step` | `540d8e36712e2f20e59d449c9a74fd6bf4265db18a1daf7b3ee28f92611d8068` |
| `SZH_EK056_WEB_REFERENCE.step` | `39fc7e19c36844e6f0eab4da88d519d6debccf41b8d5f5bc3f244afbce5ec4c5` |

### Whole watch set — 1 changed, 5 added, 0 removed

```text
CHANGED  build123d_workbench/four_edge_leg_harness_captive_pusher_audit.py
ADDED    build123d_workbench/direct_shell_four_edge_i2_simplification_audit.py
ADDED    build123d_workbench/i2_parallel_w_four_edge_leg_revalidation_audit.py
ADDED    build123d_workbench/i2_parallel_w_root_slide_simplification_audit.py
ADDED    docs/80_direct_shell_four_edge_i2_simplification_audit.md
ADDED    docs/81_i2_parallel_w_four_edge_leg_revalidation_audit.md
```

**These were not written by this Lab.** All six are Finger switch-harness
(I2 / four-edge-leg) files belonging to a concurrent workflow — the same
parallel-workflow contention CLAUDE.md already records. None of them is in the
Thumb dependency set, none is read by any Lab script, and every Thumb authority
source is byte-identical to the baseline. The Lab's conclusions are unaffected.

Flagged rather than silently accepted: if the user did not expect another
workflow to be writing to `build123d_workbench/` and `docs/` during this session,
that is worth checking.
