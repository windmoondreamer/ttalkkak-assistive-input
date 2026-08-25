# 99 — Critical true-bare Finger shell source pre-gate

## Hard-gate result

```text
CURRENT "CLEAN" SOURCE IS TRUE BARE = NO

HISTORICAL START FINGER SHELL IS BARE = YES
HISTORICAL START HAS APPROVED LOWER15 THUMB EXTERIOR = NO

TRUE BARE COMPLETE V2 BASE = NOT CONFIRMED
BASE-SOURCE RECOVERY = FAIL
DIRECT-EMBEDDED SOCKET BOOLEAN STARTED = NO
```

The current docs/97 input is the print-ready shell with all eight 8 mm-class Finger
openings already subtracted.  Its intact fill authority is the later exact
`THUMB_LOWER15_HOUSING_V1` shell, which was exported after the historical INDEX/MIDDLE
features existed.  Therefore neither file is a bare Finger base.

The exact historical `Start` AP242 pair is a genuine pre-Finger shell and is the only
confirmed bare Finger geometry authority.  It preserves the original JaD/JfD split but
predates the approved LOWER15 Thumb exterior, so it cannot by itself be promoted to the
complete final V2 base requested here.  No guessed de-feature, Boolean fill, planar patch,
or source graft was performed.

## Current-source audit

| Button | Bare exterior skin? | Legacy large opening? | Legacy internal housing? | Legacy boss/wall? | Safe for direct ITS embedding? |
|---|---|---|---|---|---|
| N1 | NO | YES | NO | NO | NO |
| N2 | NO | YES | NO | NO | NO |
| I2 | NO | YES | YES | YES | NO |
| I3 | NO | YES | YES | YES | NO |
| I4 | NO | YES | YES | YES | NO |
| M3 | NO | YES | YES | YES | NO |
| M4 | NO | YES | YES | YES | NO |
| N3 | NO | YES | NO | NO | NO |

`Legacy internal housing/boss/wall` requires both positive interior material in exact
LOWER15 relative to historical Start and explicit Finger feature lineage at that location.
That lineage exists at I2/I3/I4/M3/M4.  N3's local box also measures LOWER15-vs-Start
material change, but history identifies N3 as new and the change lies in the neighboring
Thumb/M4 region; it is therefore not mislabelled as an N3-specific legacy holder.
N1/N2/N3 still fail the current-source bare-skin gate because docs/96 subtracted the later
8 mm-class opening cutter.

## Numeric local proof

| Button | Current exterior material removed vs Start (mm³) | LOWER15 interior material added vs Start (mm³) | LOWER15 interior material removed vs Start (mm³) | Current center-axis local hits W (mm) | LOWER15 center-axis local hits W (mm) | Start center-axis local hits W (mm) |
|---|---:|---:|---:|---|---|---|
| N1 | 152.876615 | 0.000000 | 0.000000 | [] | [0.06947843615188454, 3.069452082452724] | [0.06947843615188454, 3.069435045070172] |
| N2 | 182.395132 | 0.000000 | 0.000000 | [] | [0.0063100869673178295, 3.0067809775187087] | [0.006310086967314277, 3.0067819500233597] |
| I2 | 150.363122 | 505.212236 | 37.248553 | [11.072973699818476, 14.012569851494167] | [11.072973699803757, 14.012569851489808] | [0.0, 3.0035197133688065] |
| I3 | 149.749833 | 512.923563 | 37.302730 | [11.000000000007326, 13.122921317000387] | [10.530239389752282, 13.122921316998575] | [5.329070518200751e-15, 3.0033307379102787] |
| I4 | 148.243678 | 524.856062 | 72.669247 | [] | [] | [1.7763568394002505e-15, 3.000002300981965] |
| M3 | 183.834083 | 315.147063 | 22.515767 | [] | [8.755033962642216, 8.99007558955567, 10.872368794012612, 12.210145878270023] | [0.0, 2.9998640874131084] |
| M4 | 173.099745 | 397.772542 | 55.074590 | [] | [9.045728078068784, 9.246216457691496] | [0.0, 3.0056293936684284] |
| N3 | 147.227474 | 129.390993 | 80.205435 | [] | [0.0014472392837880932, 3.0162012188466925] | [0.0014472392837880932, 3.016360137318763] |

Audit bands use frozen center/axis only: exterior W = -2.50…2.50 mm,
interior W = 2.50…15.50 mm.  Positive W is inward.
The local volume threshold for a legacy feature is 0.05 mm³.

## Source lineage

| Lineage | Finger exterior | Finger internal | Thumb exterior | Decision |
|---|---|---|---|---|
| current print-ready docs/96 source | all 8 large openings | later internal material remains where present in LOWER15 | approved exact LOWER15 | reject as bare base |
| exact `THUMB_LOWER15_HOUSING_V1` | old INDEX/MIDDLE opening/seat traces at retained locations | old Finger-added walls/holders at retained locations | approved exact LOWER15 | reject as bare base |
| exact historical `Start` AP242 | smooth pre-Finger skin | no Finger holder group | original pre-LOWER15 Thumb | bare Finger authority only; incomplete final base |

Feature-history evidence: historical `Start` is immutable Onshape version
`4342e7db262cbced58bf16b8`, with INDEX/MIDDLE group absent.  Exact LOWER15 is immutable
version `50dfe4e752e447375b95493a`.  docs/06 records the earlier Finger feature sequence as
8 × 8 mm openings followed by 12.4 × 12.4 mm holders and switch pockets.

## Required visual proof

- `renders/true_bare_finger_shell_source_pregate/01_all8_current_source_exterior.png`
- `renders/true_bare_finger_shell_source_pregate/02_all8_current_source_interior.png`
- `renders/true_bare_finger_shell_source_pregate/03_i2_representative_legacy_cross_section.png`
- `renders/true_bare_finger_shell_source_pregate/04_true_bare_candidate_exterior.png`
- `renders/true_bare_finger_shell_source_pregate/05_true_bare_candidate_interior.png`

The images use a farther camera and intentionally omit top-left labels.  Red in the
interior/cross-section proof is later LOWER15 material absent from historical Start.

## Stop condition

The next admissible source-recovery action is a read-only/exported Onshape state that
retains exact LOWER15 Thumb features while suppressing or rolling back all Finger-specific
openings/holders, or an equivalently exact feature-history export.  Until that exists:

```text
BASE-SOURCE RECOVERY = FAIL
STOP
```

Generated: 2026-08-25T08:53:31.517404+00:00
