# 59 — N2 internal actuation architecture

## 결론

외부·Thumb·HW504 B를 모두 고정한 상태에서 가장 단순한 경로는 **Candidate A — 외부 redundant terminal trim**이다. CAD에서는 T2/T4를 housing 밖의 짧은 stub까지만 남기면 terminal penetration이 0이고 minimum clearance가 **0.818769 mm**다.

다만 실제 구매품의 continuity와 cutting 안전성이 아직 실물로 확인되지 않았으므로 최종 상태는 **CONDITIONAL RECOMMENDATION / NEEDS PHYSICAL CONTINUITY TEST + PHYSICAL TRIM TEST**다. Production에는 적용하지 않았다.

## 1. Exact terminal map

| Terminal | Local position | Collision | Penetration | Distance |
|---|---|---|---:|---:|
| T1 | -U/-V | NO | 0.000000000 mm³ | 2.119093 mm |
| T2 | -U/+V | YES | 0.401336507 mm³ | 0.000000 mm |
| T3 | +U/-V | NO | 0.000000000 mm³ | 3.203679 mm |
| T4 | +U/+V | NO | 0.000000000 mm³ | 0.793771 mm |

충돌은 **T2 하나**이며 충돌 centroid는 housing rear보다 바깥쪽의 절단 가능한 external lead zone에 위치한다.

## 2. Electrical gate

- Local drawing reference에는 `T1/T2 common`, `T3/T4 common`, press 시 두 group 연결로 기록되어 있다.
- 그러나 실제 보유 switch continuity 측정 기록은 없다.
- 따라서 공식 판정은 `NEEDS PHYSICAL CONTINUITY TEST`다.
- Provisional active pair: **T1 + T3**
- Conditional external trim: **T2 + T4**
- Housing 내부 leadframe modification: **0**

## 3. Candidate A

- Direct actuation 유지; plunger 없음
- Cap / actuator / switch body / carrier 위치 변경 0
- Trim cut local depth: **8.510 mm**
- Housing rear 이후 axial stub: **0.150 mm**
- Root 시작점 기준 retained envelope centerline: **0.463 mm**
- Terminal: **0.818769 mm / 0.000000000 mm³**
- Switch body: **0.867511 mm / 0.000000000 mm³**
- CAD result: **PASS**

## 4. Candidate B setback screen

| Setback mm | Terminal mm | Body mm | Local shell mm | Result |
|---:|---:|---:|---:|---|
| 0.5 | 0.000000 | 0.406255 | 2.377231 | FAIL |
| 1.0 | 0.000000 | 0.000000 | 2.541994 | FAIL |
| 1.5 | 0.000000 | 0.000000 | 2.646723 | FAIL |
| 2.0 | 0.000000 | 0.000000 | 2.836988 | FAIL |
| 2.5 | 0.000000 | 0.000000 | 3.097067 | FAIL |
| 3.0 | 0.000000 | 0.000000 | 3.411026 | FAIL |
| 4.0 | 0.000000 | 0.000000 | 4.149882 | FAIL |

Cap에서 switch를 뒤로 이동하는 지정 방향은 HW504 B 안쪽으로 더 들어간다. 0.5–4.0 mm 전 구간에서 terminal distance가 0이며 1.0 mm부터 body도 0이다. 따라서 `THIS INTERNAL CANDIDATE FAILED`다.

Plunger concept 자체는 D3.0 one-piece stem, radial guide clearance 0.25 mm, broad 0.35 mm overtravel stop으로 구성했지만 이 배치에서는 채택하지 않는다.

## 5. Candidate C

Dedicated carrier는 N1 구조와 N2 구조를 분리할 수 있으나 switch/HW504 상대 위치를 바꾸지 않는다. 동일 4.0 mm setback에서 terminal/body가 모두 0 distance이므로 `THIS INTERNAL CANDIDATE FAILED`다. 외부 불가능 판정이 아니다.

## 6. Comparison

| Candidate | Exterior | Thumb | Switch modification | HW/terminal clearance | Wall | Part delta | Complexity | Printability | Result |
|---|---:|---:|---|---:|---|---:|---|---|---|
| A terminal trim | 0 | 0 | external unused leads only | 0.818769 mm | docs/57 1.314848 mm 유지 | 0 | LOW | unchanged | CONDITIONAL PASS |
| B setback + plunger | 0 | 0 | body +4.0 mm setback | 0 mm | not reached | +1 | MEDIUM | guide/stop conditional | FAILED |
| C setback + dedicated carrier | 0 | 0 | body +4.0 mm setback | 0 mm | 1.60 mm seed, not gated | +2 | HIGH | printable concept | FAILED |

## 7. User-facing mechanism answer

- N2가 눌리는 방식: **Candidate A에서는 현재처럼 cap이 ITS actuator를 직접 누름**
- Switch 위치: **현재 위치 유지**
- Plunger: **필요 없음** — B/C는 내부 충돌로 미채택
- 사용하는 terminal: **실물 continuity 확인 후 T1+T3 provisional**
- Carrier 분리: **필요 없음**
- Return: **ITS 내부 return force 그대로 사용**
- Overtravel: **현재 direct-actuation stop architecture 유지**

## 8. STOP

Production geometry 변경 0. 실제 switch에서 T1/T2 및 T3/T4 continuity, T1–T3 press continuity, 0.46 mm급 external stub cutting 안전성을 확인하기 전에는 terminal을 절단하지 않는다.
