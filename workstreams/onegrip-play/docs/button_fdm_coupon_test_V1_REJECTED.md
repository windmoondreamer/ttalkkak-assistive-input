# BUTTON FDM TEST COUPON — P1S / 0.4 mm nozzle

## Scope and freeze

This is an independent print-test fixture for the completed OneGrip eight-button mechanism. It was built from new primitives only. No production STEP was imported, no production carrier/source parameter was changed, and the generated geometry must not be substituted into production without a separate decision.

## Generated artifacts

- `build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.step`
- `build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.stl`
- print layout: 76.000 × 78.250 × 12.050 mm
- solids in the one-file print layout: 11 = base/fixtures 1 + removable caps 5 + switch service gates 5

The labels beginning with `G` identify the complete guide/mechanism row. Labels beginning with `P` identify the through pocket-fit row. The framed `G4.80` and `P6.40` are the current seeds.

## Parametric hardware inputs

The defaults are grouped in `CouponConfig` at the top of `build123d_workbench/button_fdm_coupon.py`. They can also be overridden from the command line without editing construction code.

| Parameter | Default |
|---|---:|
| measured switch body X | 6.12 mm |
| measured switch body Y | 6.05 mm |
| housing height | 3.56 mm |
| actuator diameter | 3.35 mm |
| actuator projection | 2.44 mm |
| fixed cap tail | Ø4.50 mm |
| central direct contact | Ø3.00 mm |
| mechanical hard stop | 0.350 mm |
| minimum structural wall in fixture | 1.20 mm |

Example for a newly measured lot:

```powershell
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.button_fdm_coupon --body-x 6.14 --body-y 6.08 --housing-height 3.58
```

## What is physically represented

Each `G` station has a 6.40 mm side-loading switch pocket, terminal floor channels, broad rear support, removable lower service gate, Ø4.50 solid cap tail, C-shaped guide bore, 6.50 mm retention shoulder, 6.80 mm shoulder cavity, Ø3.00 direct contact, ITS return, and an independent carrier hard stop. At full press the 1.20 mm cap shoulder transfers load to the printed guide at 0.350 mm; the switch housing is not the overtravel stop.

The smallest structural guide side wall is `(9.30 - 6.80) / 2 = 1.25 mm`. The front lip, cap shoulder, and service-gate flange are each 1.20 mm, so the global minimum structural thickness is 1.20 mm. The cap tail is solid, avoiding an under-thickness cylindrical wall.

## Print setup

1. Import the STL as one object with multiple parts and keep the supplied orientation and 100% scale.
2. Bambu Lab P1S, 0.4 mm nozzle; start with 0.20 mm layer height and at least 3 wall loops.
3. Print without supports. The fixture plate is flat, caps are pad-face-down, and service gates are broad-face-down.
4. Keep XY/hole compensation at zero for the first run. Record filament, nozzle age, layer height, wall generator, line width, cooling, and build-plate type.
5. Do not drill, ream, sand, or lubricate before the as-printed comparison. If a second corrected trial is made, record the correction separately.

## Assembly

1. Remove only loose stringing; preserve the guide-bore surfaces for the first measurement.
2. For a `G` station, feed the ITS-1105 laterally from the open right side. Align the two terminal rows with the two floor slots and seat the housing on the rear support.
3. Slide one service gate into the lower opening until its flange meets the tower. The central tongue closes the 6.40 mm pocket without loading the terminal rows.
4. At the upper opening, slide a cap shoulder and tail laterally into the C-guide. The actuator return should lift the shoulder to the front retention lip.
5. Press only on the cap pad. Stop if the switch or printed wall visibly deforms.
6. The `P` row is a through gauge: insert the same switch squarely from above and push it back out from below. Use the same switch for all five pockets.

## Guide-clearance record

| G label / bore Ø mm | diametral clearance mm | radial clearance mm | wobble | binding | return | click feel | 100 cycles |
|---:|---:|---:|---|---|---|---|---|
| 4.70 | 0.200 | 0.100 |  |  |  |  |  |
| 4.75 | 0.250 | 0.125 |  |  |  |  |  |
| 4.80 | 0.300 | 0.150 |  |  |  |  |  |
| 4.85 | 0.350 | 0.175 |  |  |  |  |  |
| 4.90 | 0.400 | 0.200 |  |  |  |  |  |

Select the smallest guide that completes 100 presses without intermittent binding and returns positively on every cycle. Compare wobble only among the passing variants.

## Switch-pocket record

Clearance is calculated from the current measured body, before printer error.

| P label / square pocket mm | X side clearance mm | Y side clearance mm | insertion | retention | removal / damage |
|---:|---:|---:|---|---|---|
| 6.30 | 0.090 | 0.125 |  |  |  |
| 6.35 | 0.115 | 0.150 |  |  |  |
| 6.40 | 0.140 | 0.175 |  |  |  |
| 6.45 | 0.165 | 0.200 |  |  |  |
| 6.50 | 0.190 | 0.225 |  |  |  |

Use one insertion direction and keep the switch orientation fixed. Mark any whitening, layer split, gouging, or corner damage after removal.

## Required test items

For the selected guide/pocket combination, record:

- cap wobble: none / slight / objectionable, plus measured lateral play if available
- cap binding: none, intermittent, or continuous; note press direction and temperature
- return: 10/10 slow releases and 10/10 off-axis releases before cycling
- click feel: clean / damped / double-feel / hard-stop masks click
- 0.350 mm hard stop: measured rest-to-stop displacement and measuring method
- switch retention: gate installed, including pull direction and subjective force
- switch removal: tool used, removal force if available, and whether the same switch is reusable
- wall damage: cracks, whitening, delamination, crushed lip, or terminal-slot damage
- repeated press: 100 cycles; inspect again at cycles 25, 50, and 100

### Run sheet

| Field | Result |
|---|---|
| printer / nozzle | Bambu Lab P1S / 0.4 mm |
| filament / lot / dry state |  |
| layer / wall generator / wall count |  |
| slicer XY or hole compensation | 0 for baseline |
| selected G variant |  |
| selected P variant |  |
| rest-to-hard-stop displacement |  |
| cap wobble / binding |  |
| return / click feel |  |
| switch retention / removal |  |
| wall damage after removal |  |
| 25-cycle inspection |  |
| 50-cycle inspection |  |
| 100-cycle result |  |
| decision / next compensation |  |

## Digital geometry checks

- B-rep validity: `PASS`
- connected fixture base: `PASS` (1 solid)
- cap/gate fragmentation: `PASS`
- minimum structural wall: `1.20 mm` (`PASS >= 1.20 mm`)
- guide/cap penetration at rest: `0 mm³` for all five variants
- guide/cap penetration at full 0.350 mm press: `0 mm³` for all five variants; coincident hard-stop faces only
- switch body/pocket, actuator/guide, gate/fixture, and gate/switch unintended penetration: `0 mm³`
- production source import/write: `0`
