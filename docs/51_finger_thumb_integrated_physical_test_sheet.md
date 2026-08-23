# OneGrip Play — Finger + lowered Thumb 통합 FDM Physical Test Sheet

> 이 문서는 실제 출력·조립 결과 기록용이다. 빈 칸은 PASS로 간주하지 않는다.
> Production V3 파라미터는 이 시트와 사진을 검토하기 전까지 변경하지 않는다.

## 1. 현재 상태

| Gate | 현재 판정 |
|---|---|
| DIGITAL INTEGRATED VALIDATION | **PASS** |
| INTEGRATED PHYSICAL VALIDATION KIT | **READY** |
| PHYSICAL INTEGRATED V3 | **NOT YET VALIDATED** |
| PRODUCTION FREEZE | **PENDING USER FDM RESULTS** |

- local build123d + OCCT only
- Onshape API/browser/CAD write: `0`
- approved Finger/Thumb external geometry movement: `0.000 mm`
- thumb target: `(0,+12.25,-21.00) mm`
- production V3 parameter modification: `0`
- full production shell print: 포함하지 않음

## 2. Kit inventory

출력 폴더:

`build123d_workbench/out/finger_thumb_integrated_physical_validation/`

### Plate A — shell functional sections

- `VALIDATION_PLATE_A.stl`
- `JAD_VALIDATION_SECTION.stl`
- `JFD_VALIDATION_SECTION.stl`

Plate envelope: `202.00 × 80.00 × 25.03 mm`, component 2개, nominal gap `6 mm`.

Plate A에는 다음 production interface가 1:1로 들어 있다.

- Finger 8-button openings와 guides
- N2 seam/capture
- lowered thumb split seat와 three pads
- Option C screw boss 3쌍
- Finger/Thumb wiring corridor interface
- JaD/JfD closure geometry

### Plate B — fit coupon, carriers and caps

- `VALIDATION_PLATE_B.stl`
- `ITS_POCKET_FIT_COUPON.stl`
- carrier/restraint STL 6개
- cap STL 8개

Plate envelope: `189.62 × 38.92 × 11.94 mm`, component 15개, nominal gap `6 mm`.

### Reference-only files

- `FINGER_THUMB_INTEGRATED_FUNCTIONAL_SECTION.step`
- `FINGER_THUMB_INTEGRATED_FUNCTIONAL_SECTION.stl`
- `THUMB_TARGET_PHYSICAL_REFERENCE.step`

전체 assembly STL은 배치·시각 reference다. 실제 출력은 Plate A/B 또는 개별 STL을
사용한다.

## 3. Print setup

| Item | Record |
|---|---|
| Printer |  |
| Slicer / version |  |
| Material / brand / color |  |
| Nozzle | `0.4 mm` / actual: |
| Layer height |  |
| Line width |  |
| Wall count |  |
| Top / bottom layers |  |
| Infill / pattern |  |
| Nozzle / bed temperature |  |
| Flow ratio |  |
| XY / hole compensation |  |
| Elephant-foot compensation |  |
| Support type / threshold |  |
| Brim / raft |  |
| Print date |  |

## 4. Print orientation and support policy

| Part | Orientation | Support | Functional faces that must remain scar-free |
|---|---|---|---|
| JaD section | X=0 seam face on bed, Y `-90°` | YES, exterior crop perimeter only | cap guides, N2 seam, thumb pads, screw bore/mating face |
| JfD section | X=0 seam face on bed, Y `+90°` | YES, exterior crop perimeter only | cap guides, N2 seam, thumb pads, screw bore/mating face |
| Fit coupon | flat base, pockets vertical | NO | all pocket walls and lower pocket edges |
| Caps | external pad face on bed, socket upward | NO | actuator socket and guide edge |
| N shared front carrier | front-ring broad plane down, pockets upward | local bridge only if necessary | 6.40 pockets, terminal exits |
| N rear restraint | broad restraint face down | NO | switch-contact faces |
| Other carriers | broad rear face down, pockets upward | NO or local bridge only | switch pockets, terminal channels |

Measured downward overhang area at the supplied orientation:

- JaD section: `19.49%`
- JfD section: `20.69%`
- fit coupon: `0%`
- all caps: `0%`
- carriers: approximately `0.13–16.35%`

Support blocker를 다음 기능면에 반드시 설정한다.

- switch pockets
- cap guides/openings
- N2 seam
- thumb conformal pads
- screw bores와 mating faces

## 5. Recommended print order

1. `ITS_POCKET_FIT_COUPON.stl`만 먼저 출력한다.
2. 충분히 식힌 뒤 같은 ITS-1105 샘플로 fit을 측정한다.
3. production nominal `6.40 mm`를 자동 변경하지 말고 결과만 기록한다.
4. Plate B를 출력해 carrier/cap의 치수와 출력 상태를 확인한다.
5. Plate A를 seam-face-down 방향으로 출력한다.
6. support는 외부 crop 둘레에서만 제거하고 기능면을 줄·드릴로 보정하지 않는다.
7. ITS-1105 8개와 실제 wire를 pre-assemble한다.
8. thumb hardware를 seat한 후 shell을 닫고 M3 screw를 시험한다.
9. 각 cap을 최소 20회 작동하고 service/disassembly까지 수행한다.

## 6. ITS-1105 fit coupon

스위치를 큰 포켓부터 작은 포켓 순서로 시험한다. Body 옆 terminal root를 비틀지
않으며, distal pin만 필요할 때 한 번 성형한다.

| Pocket | Cannot enter | Tight | Good | Loose | Removal PASS | Notes |
|---:|:---:|:---:|:---:|:---:|:---:|---|
| 6.30 mm | ☐ | ☐ | ☐ | ☐ | ☐ |  |
| 6.35 mm | ☐ | ☐ | ☐ | ☐ | ☐ |  |
| **6.40 mm production nominal** | ☐ | ☐ | ☐ | ☐ | ☐ |  |
| 6.45 mm | ☐ | ☐ | ☐ | ☐ | ☐ |  |
| 6.50 mm | ☐ | ☐ | ☐ | ☐ | ☐ |  |

- selected pocket: __________ mm
- wall crack/layer split: NONE ☐ / PRESENT ☐
- production pocket change recommendation: NONE ☐ / `+_____ mm` / `-_____ mm`

## 7. Finger controls — 8-button physical test

Digital REST / `0.175 mm` / `0.350 mm` sweep는 전 버튼 hard intersection `0`으로
PASS했다. 아래는 출력물에서 각 버튼을 최소 20회 누른 뒤 기록한다.

| Button | Switch fit | Cap motion | Click | Return | Rub | Carrier fit | Notes |
|---|---|---|---|---|---|---|---|
| I2 | TIGHT ☐ GOOD ☐ LOOSE ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | NONE ☐ LIGHT ☐ BAD ☐ | PASS ☐ FAIL ☐ |  |
| I3 | TIGHT ☐ GOOD ☐ LOOSE ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | NONE ☐ LIGHT ☐ BAD ☐ | PASS ☐ FAIL ☐ |  |
| I4 | TIGHT ☐ GOOD ☐ LOOSE ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | NONE ☐ LIGHT ☐ BAD ☐ | PASS ☐ FAIL ☐ |  |
| M3 | TIGHT ☐ GOOD ☐ LOOSE ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | NONE ☐ LIGHT ☐ BAD ☐ | PASS ☐ FAIL ☐ |  |
| M4 | TIGHT ☐ GOOD ☐ LOOSE ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | NONE ☐ LIGHT ☐ BAD ☐ | PASS ☐ FAIL ☐ |  |
| N1 | TIGHT ☐ GOOD ☐ LOOSE ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | NONE ☐ LIGHT ☐ BAD ☐ | PASS ☐ FAIL ☐ |  |
| N2 | TIGHT ☐ GOOD ☐ LOOSE ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | NONE ☐ LIGHT ☐ BAD ☐ | PASS ☐ FAIL ☐ |  |
| N3 | TIGHT ☐ GOOD ☐ LOOSE ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | PASS ☐ FAIL ☐ | NONE ☐ LIGHT ☐ BAD ☐ | PASS ☐ FAIL ☐ |  |

## 8. N1/N2 critical region

| Check | PASS | FAIL | Notes |
|---|:---:|:---:|---|
| N1 inserts without terminal-root stress | ☐ | ☐ |  |
| N2 inserts without terminal-root stress | ☐ | ☐ |  |
| Shared front carrier seats fully | ☐ | ☐ |  |
| Rear restraint installs/removes without forcing | ☐ | ☐ |  |
| Terminal exits remain accessible | ☐ | ☐ |  |
| N1/N2 distal leads can be formed once | ☐ | ☐ |  |
| Shell closes with carrier installed | ☐ | ☐ |  |
| N1 cap click/return | ☐ | ☐ |  |
| N2 cap click/return | ☐ | ☐ |  |
| N carrier can be serviced after reopening | ☐ | ☐ |  |

### N2 seam

| Check | Result | Notes |
|---|---|---|
| Seam open | PASS ☐ / FAIL ☐ |  |
| Seam closed | PASS ☐ / FAIL ☐ |  |
| Jam | NONE ☐ / YES ☐ |  |
| Closed-shell cap rubbing | NONE ☐ / LIGHT ☐ / BAD ☐ |  |
| Digital opposite-shell clearance | `1.054 mm` | reference |

## 9. Lowered Thumb seat

Physical interface under test:

- split continuous flange: `1.60 mm`
- outer/inner frame: `42 × 64 / 34 × 56 mm`
- conformal pads: 3개, `5.0 mm`, reach `4.8 mm`
- local relief: `0.80 mm`

| Check | Result | Notes |
|---|---|---|
| Thumb insert | PASS ☐ / FAIL ☐ |  |
| Seating | FULL ☐ / PARTIAL ☐ / FAIL ☐ |  |
| Rocking | NONE ☐ / LIGHT ☐ / BAD ☐ |  |
| Anti-rotation | PASS ☐ / FAIL ☐ |  |
| Shell-closed retention | PASS ☐ / FAIL ☐ |  |
| Thumb controls remain unobstructed | PASS ☐ / FAIL ☐ |  |
| Removal after reopening | PASS ☐ / FAIL ☐ |  |
| Pad/flange damage | NONE ☐ / YES ☐ |  |

## 10. Option C fastening test

Digital boss geometry:

| Screw | Y | Z | Axis |
|---|---:|---:|---|
| 1 | `10.00 mm` | `35.00 mm` | `+X` |
| 2 | `25.00 mm` | `8.00 mm` | `+X` |
| 3 | `15.80 mm` | `-21.35 mm` | `+X` |

- boss outer radius: `4.60 mm`
- radial wall: `1.80 mm`
- supporting web: `3.20 mm`
- first hardware candidate: **M3 × 16 mm socket-head**, under-head length 기준
- maximum head envelope: diameter `5.5 mm`, height `3.0 mm`
- driver envelope: diameter `5.6 mm`
- modeled far-side engagement: approximately `4.0 mm`

실제 screw가 bottom-out되거나 head가 위 envelope보다 크면 억지로 체결하지 않는다.

| Check | PASS | FAIL | Notes |
|---|:---:|:---:|---|
| Screw 1 starts and clamps | ☐ | ☐ |  |
| Screw 2 starts and clamps | ☐ | ☐ |  |
| Screw 3 starts and clamps | ☐ | ☐ |  |
| Driver access for all three | ☐ | ☐ |  |
| Shell seam closes uniformly | ☐ | ☐ |  |
| Screw does not bottom out | ☐ | ☐ |  |
| Boss damage after first assembly | ☐ | ☐ | NONE / crack / layer split |
| Boss damage after 5 reopen cycles | ☐ | ☐ | NONE / crack / layer split |

Actual hardware record:

| Item | Record |
|---|---|
| Screw size/length |  |
| Head diameter/height |  |
| Driver type |  |
| Insert or printed pilot |  |
| Tightening method / torque if known |  |

## 11. Wiring test

권장 physical seed:

- individual insulated wire OD: `0.8–1.2 mm`
- N1/N2 individual maximum practical OD: `1.6 mm`
- other Finger corridor: `4.0 × 3.2 mm`, practical bundle OD 약 `3.0 mm` 이하
- Thumb corridor: `3.2 × 3.2 mm`, practical bundle OD 약 `2.8 mm` 이하

Actual wire:

| Item | Record |
|---|---|
| Wire conductor/gauge |  |
| Measured insulation OD |  |
| Finger bundle maximum OD |  |
| Thumb bundle maximum OD |  |
| Solder joint insulation |  |

| Check | PASS | FAIL | Notes |
|---|:---:|:---:|---|
| Finger route installs as modeled | ☐ | ☐ |  |
| Thumb route installs as modeled | ☐ | ☐ |  |
| N1/N2 formed leads avoid thumb module | ☐ | ☐ |  |
| Solder joints remain accessible | ☐ | ☐ |  |
| Shell closes fully with real wires | ☐ | ☐ |  |
| Finger wire pinch | NONE ☐ | YES ☐ |  |
| Thumb wire pinch | NONE ☐ | YES ☐ |  |
| Screw/boss wire pinch | NONE ☐ | YES ☐ |  |
| Wire insulation damage after reopening | NONE ☐ | YES ☐ |  |

## 12. Shell closure and service

| Check | PASS | FAIL | Notes |
|---|:---:|:---:|---|
| JaD/JfD mate without forcing | ☐ | ☐ |  |
| All three screw points align | ☐ | ☐ |  |
| No carrier shifts during closure | ☐ | ☐ |  |
| No cap binds after closure | ☐ | ☐ |  |
| Shell reopens without damage | ☐ | ☐ |  |
| Thumb module removes | ☐ | ☐ |  |
| N rear restraint removes | ☐ | ☐ |  |
| N carrier/switches remove | ☐ | ☐ |  |
| Other four carrier groups remove | ☐ | ☐ |  |
| Reassembly succeeds a second time | ☐ | ☐ |  |

## 13. Result for production feedback

- Required pocket change: NONE ☐ / `+_____ mm` / `-_____ mm`
- Required cap clearance change: NONE ☐ / ______________________________
- Required N2 seam change: NONE ☐ / ___________________________________
- Required thumb pad/flange change: NONE ☐ / ___________________________
- Required screw boss change: NONE ☐ / ________________________________
- Required wiring corridor change: NONE ☐ / ___________________________
- Photos attached: YES ☐ / NO ☐
- Physical integrated result: PASS ☐ / CONDITIONAL ☐ / FAIL ☐
- Production freeze recommendation: GO ☐ / HOLD ☐

Additional notes:

```

```

## 14. Digital evidence

- validation JSON:
  `build123d_workbench/out/finger_thumb_integrated_physical_validation/finger_thumb_integrated_physical_validation.json`
- contact sheet:
  `build123d_workbench/out/finger_thumb_integrated_physical_validation/renders/00_contact_sheet.png`
- all required digital gates: PASS
- each printable source part: valid single solid
- orphan/sliver/leftover cutter: 0
- Plate A components: 2 / expected 2
- Plate B components: 15 / expected 15
- 8-button motion: PASS
- thumb seat: PASS
- shell close: PASS
- screw access: PASS
- wiring: PASS

실물 결과가 채워질 때까지 최종 상태는 다음과 같다.

`PHYSICAL INTEGRATED V3 = NOT YET VALIDATED`

`PRODUCTION FREEZE = PENDING USER FDM RESULTS`
