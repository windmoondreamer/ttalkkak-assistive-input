# 60 — N2 Candidate A production-intent mechanism

## 결론

사용자가 제공한 실물 continuity/trim test를 승인 근거로 반영해 **N2 Candidate A를 PRODUCTION-INTENT INTERNAL BASELINE으로 구현**했다. 외부 cap 형상·중심·각도·이동축, switch 위치, direct actuation, HW504 A/B는 변경하지 않았다.

최종 gate: **PASS / PRODUCTION-INTENT INTERNAL BASELINE**  
Production geometry는 N2 cap 내부와 shared carrier의 N2 영역에만 생성했으며 N1에는 확장하지 않았다.

## 1. 실물 전기 확인 반영

- T1–T2: 항상 연결
- T3–T4: 항상 연결
- T1–T3: 평상시 단선 / 누르면 연결
- T2/T4 external stub trim 후 T1–T3 switching 및 actuator return 정상
- Production electrical terminals: **T1 + T3**
- Unused trimmed stubs: **T2 + T4**

## 2. 실제 solid architecture

- Cap retention: cap 내부 6.50 mm square shoulder와 carrier front shoulder
- Cap guide: Ø4.50 tail / Ø4.80 bore, radial clearance 0.150 mm
- Anti-rotation: 6.50 mm square shoulder / 6.80 mm cavity, side clearance 0.150 mm
- Actuator contact: 중앙 Ø3.00 contact puck, rest부터 접촉
- Switch locating: 6.40 mm lateral pocket + guide rear face + rear reaction frame
- Rear reaction: body rear face의 broad frame support; 계산 접촉 가능 면적 약 13.183 mm²
- Overtravel stop: shoulder rear face와 carrier rear stop, **0.350 mm**
- Return: ITS internal return force → actuator → contact puck → cap; spring 0
- Service: shell open → carrier release → T1/T3 bay 접근 → switch/cap lateral C-path 분리

## 3. Exact motion

| Travel mm | Cap↔guide penetration mm³ | Cap↔shell penetration mm³ | Cap↔actuator distance mm | Front retention gap mm | Rear hard-stop gap mm | Result |
|---:|---:|---:|---:|---:|---:|---|
| 0.000 | 0.000000000 | 0.000000000 | 0.000000 | 0.000 | 0.350 | PASS |
| 0.175 | 0.000000000 | 0.000000000 | 0.000000 | 0.175 | 0.175 | PASS |
| 0.350 | 0.000000000 | 0.000000000 | 0.000000 | 0.350 | 0.000 | PASS |

## 4. Static exact gates

| Gate | Clearance | Penetration | Result |
|---|---:|---:|---|
| Switch body ↔ carrier | 0.000000 mm | 0.000000000 mm³ | PASS contact |
| T1/T3 ↔ HW504 B | 2.119093 mm | 0.000000000 mm³ | PASS |
| trimmed T2/T4 ↔ HW504 B | 0.818769 mm | 0.000000000 mm³ | PASS |
| production carrier ↔ HW504 A/B | 0.004964 mm | 0.000000000 mm³ | PASS |
| production carrier ↔ local shell | 0.240975 mm | 0.000000000 mm³ | PASS |

## 5. Wall / exterior / service

- Guide closed-side wall: **1.250 mm**
- Rear reaction minimum strip: **1.200 mm**
- Existing relieved carrier conservative wall: **1.314848 mm**
- Overall minimum structural wall: **1.200 mm** (`>= 1.20 mm PASS`)
- Exterior centre movement: **0.000 mm**
- Exterior geometry symmetric difference: **0.000000000 mm³**
- Switch lateral service sweep penetration: **0.000000000 mm³**
- Cap lateral service sweep penetration: **0.000000000 mm³**

## 6. Outputs / STOP

- `build123d_workbench\out\n2_production_intent_mechanism\N2_PRODUCTION_INTENT_CAP.step`
- `build123d_workbench\out\n2_production_intent_mechanism\N1_N2_SHARED_CARRIER_N2_PRODUCTION_INTENT.step`
- `build123d_workbench\out\n2_production_intent_mechanism\N2_PRODUCTION_INTENT_LOCAL_ASSEMBLY.step`
- `build123d_workbench\out\n2_production_intent_mechanism\n2_production_intent_mechanism.json`
- `renders\n2_production_intent_mechanism` — 필수 렌더 7개

사용자 형상 검토를 위해 여기서 STOP한다. N1 또는 다른 버튼에는 자동 확장하지 않았다.
