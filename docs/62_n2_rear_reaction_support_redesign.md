# 62 — N2 rear reaction support redesign

## 결론

`SELECTED SUPPORT TYPE = B — SHORT U-SHAPED REACTION CRADLE`다. 기존 broad rear frame의 기능은 유지하되 HW504 쪽 rail 길이를 줄이고 terminal-safe crossbar로 반력 경로를 다시 연결했다.

- `N2 ARCHITECTURE = ACCEPT`
- `REAR REACTION SUPPORT = PASS`
- `HW504 A ROBUST CLEARANCE = PASS`
- `N2 MOTION = PASS`
- `T2/T4 CAD FIT = ACCEPTABLE`
- `T2/T4 PHYSICAL TRIM = CONDITIONAL`
- `EXTERIOR = PRESERVED`

## 1. Candidate comparison

| Type | Architecture | Unique area mm² | Zones | Span mm | Support↔HW A mm | Connected | Result |
|---|---|---:|---:|---:|---:|---|---|
| A | CENTRAL RELIEVED REAR FRAME | 10.863 | 1 | 0.000 | 0.000 | NO | REJECT |
| B | U-SHAPED REACTION CRADLE | 13.524 | 3 | 4.890 | 0.351 | YES | SELECT FOR EXACT |
| C | TWO-PAD REACTION SUPPORT | 6.192 | 2 | 4.890 | 0.370 | NO | REJECT |
| D | THREE-PAD REACTION SUPPORT | 6.940 | 3 | 5.578 | 0.000 | NO | REJECT |

B는 C의 안전한 짧은 rail 길이를 유지하면서 1.75 mm crossbar로 free rail을 carrier에 다시 연결한다. A/D는 support 자체가 HW504-A에 닿고, C는 한 pad의 load path가 끊겨 탈락했다.

## 2. Selected support

- SELECTED SUPPORT TYPE: **B — SHORT U-SHAPED REACTION CRADLE**
- OLD SUPPORT AREA: **13.183 mm²**
- NEW SUPPORT AREA: **13.524 mm²**
- CONTACT COUNT: **3 zones / 1 connected patch**
- CONTACT SPAN: **4.890 mm**
- MINIMUM SUPPORT WALL: **1.200 mm**
- MINIMUM STRUCTURAL WALL: **1.200 mm**
- remaining shared-bridge section after local relief: **2.000 mm**

지지는 ITS plastic rear housing face에만 형성된다. T1/T3 및 trimmed T2/T4 terminal root는 support contact에서 제외했다. 3개 reaction zone과 4.890 mm 좌우 span, 기존보다 큰 unique contact area가 뒤밀림·회전·rocking에 대한 연속 반력 경로를 만든다.

## 3. Exact clearance and static gates

- HW504 A ↔ CARRIER: **0.304180 mm**, penetration **0.000000000 mm³**
- HW504 B ↔ CARRIER: **1.360984 mm**, penetration **0.000000000 mm³**
- ITS body ↔ carrier unintended penetration: **0.000000000 mm³**
- T1/T3 ↔ HW504 B minimum: **2.119093 mm**
- carrier ↔ local shell penetration: **0.000000000 mm³**
- N1 functional geometry removed: **0.000000000 mm³**

0.304 mm는 absolute 0.30 mm gate를 통과하지만 preferred 0.50 mm에는 미달한다. 외형이나 switch pose를 바꾸지 않고 남은 shared bridge 및 1.20 mm wall gate를 유지한 결과다.

## 4. Motion revalidation

| Travel mm | Cap↔shell pen mm³ | Cap↔guide pen mm³ | Cap↔actuator pen mm³ | Hard-stop residual mm | Result |
|---:|---:|---:|---:|---:|---|
| 0.000 | 0.000000000 | 0.000000000 | 0.000000000 | 0.350 | PASS |
| 0.175 | 0.000000000 | 0.000000000 | 0.000000000 | 0.175 | PASS |
| 0.350 | 0.000000000 | 0.000000000 | 0.000000000 | 0.000 | PASS |

Hard stop은 기존 guide rear stop에 남아 있으며 rear reaction support나 ITS housing을 overtravel stop으로 사용하지 않는다.

## 5. T2/T4 policy

- Current trimmed T2/T4 CAD clearance: **0.818769 mm**
- Housing-flush theoretical reference: **0.959811 mm**
- `T2/T4 CAD = ACCEPTABLE`
- `T2/T4 PHYSICAL = CONDITIONAL`

1.00 mm numerical gate를 맞추기 위한 추가 housing 침범은 수행하지 않았다. 실제 ITS-1105 continuity/trim 확인 전에는 terminal production freeze를 하지 않는다.

## 6. Freeze / outputs / STOP

Exterior shell, external cap centre/orientation/axis, switch pose, guide, direct actuation, 0.350 mm hard stop, HW504 A/B와 joystick kinematics는 변경하지 않았다. N1 및 다른 Finger button으로 확장하지 않았다.

- `build123d_workbench\out\n2_rear_reaction_support_redesign\N1_N2_SHARED_CARRIER_N2_REAR_SUPPORT_REDRAFT.step` — selected local carrier STEP only
- `build123d_workbench\out\n2_rear_reaction_support_redesign\n2_rear_reaction_support_redesign.json`
- `renders\n2_rear_reaction_support_redesign` — required 8 local renders

Full shell / STL / print plate / full assembly는 생성하지 않았다. 여기서 STOP한다.
