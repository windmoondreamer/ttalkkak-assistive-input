# BUTTON FDM TEST COUPON V2 — P1S / 0.4 mm nozzle

## 결론과 범위

V1 G열의 옆삽입 포켓/좁은 핀 슬롯/공중에 생기는 포켓 지붕은 실물 FDM 시험에서 부적합으로 판정했다. V2는 **위에서 내려놓는 개방형 4코너 크래들 + 중앙 rear support + 별도 가이드 덱**으로 다시 만들었다.

OneGrip production STEP/carrier/source는 import, 수정, overwrite하지 않았다. 오픈소스 Thumb의 `PushBtn` exact STEP은 읽기 전용으로만 감사했고, 생성 스크립트에는 측정된 envelope 숫자만 독립 parameter로 기록했다.

## 생성물과 부품

- `build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.step`
- `build123d_workbench/out/button_fdm_coupon/BUTTON_FDM_TEST_COUPON.stl`
- print layout: 82.000 × 83.250 × 13.500 mm
- 총 12 solids: base/cradles 1 + 뒤집어 쓰는 guide deck 1 + caps 5 + C-clips 5
- 별도 준비: **M3×10 mm screw 2개**. 덱은 Ø3.40 clearance, base boss는 Ø2.80 self-tapping pilot이다.

`P`는 switch-body 관통 공차 게이지, `G`는 완성 기구의 guide bore 번호다. `G4.80`과 `P6.40` 테두리는 최초 seed 표시일 뿐이며, 실물 P6.30 합격 결과가 V2 G열의 body 기준이다.

## V2가 새로 반영한 실물 형상

| 항목 | V2 값/처리 |
|---|---:|
| 사용자의 measured body | 6.12 × 6.05 mm |
| G열 body locator | 6.30 mm |
| body 이론 side clearance X/Y | 0.090 / 0.125 mm |
| 네 모서리 전면 돌기 | 4 × Ø1.00, 중심 ±2.25, 높이 0.50 mm |
| 원본 formed-pin 최대 외폭 | 7.566 mm |
| 원본 pin rear reach | 3.52 mm |
| V2 아래쪽 pin 여유 깊이 | 4.20 mm |
| cap tail / contact | Ø4.50 / Ø3.00 mm |
| hard stop | 0.350 mm |

네 corner locator 사이의 네 방향은 완전히 열려 있다. 따라서 terminal root와 성형된 긴 핀이 좁은 slot을 통과할 필요가 없고, 핀을 자르거나 뿌리에서 꺾지 않는다. 중앙 4.00 mm pedestal만 housing 뒤 중앙을 받는다. 네 모서리 Ø1.00 돌기는 deck과 locator 어느 쪽에도 닿지 않는다.

## FDM 방향

1. STL을 multi-part 한 개 object로 가져오고 제공 방향/100% scale을 유지한다.
2. P1S / 0.4 mm nozzle, 0.20 mm layer, wall 3회 이상, support OFF로 시작한다.
3. 긴 guide deck은 **완성품 윗면이 build plate를 향하도록 이미 뒤집혀 있다.** 출력 후 뒤집어서 조립한다. 이 때문에 6.80 mm retention cavity가 출력 중 위로 열리고 공중 bridge/roof가 생기지 않는다.
4. 5개 guide bore는 모두 Z축 수직 hole이다. caps는 pad-face-down, C-clips는 flat으로 놓여 있다.
5. 첫 출력은 XY/hole compensation 0.00. 드릴, 리머, 사포, 윤활 없이 비교한다.

## 조립 순서

### P열 — body 공차 확인

1. 형님이 시험하신 것과 동일하게 **actuator/누르는 면이 아래쪽**을 향하게 한다.
2. 같은 switch를 P6.50부터 P6.30까지 넣고 아래에서 다시 밀어 뺀다.
3. 현재 실물 결과 `P6.30 = 아주 핏하게 삽입 가능`을 baseline으로 기록한다.

### G열 — 실제 누름 구조

1. switch를 **actuator 위 / 핀 아래** 방향으로 잡고 원하는 G 번호의 네 corner locator 사이에 수직으로 내려놓는다.
2. 핀은 locator 사이의 열린 방향과 아래 빈 공간으로 그대로 내려간다. **핀을 더 자르거나 억지로 좁은 홈에 넣지 않는다.** 중앙 pedestal에 housing 뒤 중앙만 닿으면 정상이다.
3. 빈 guide deck을 뒤집어 6.80 mm cavity/clip service opening이 아래를 향하게 하고, switch actuator 위로 수직으로 내린다.
4. 양 끝 Ø3.40 hole 두 개는 일부러 비대칭 위치다. **두 hole이 동시에 boss와 맞는 방향만 정방향**이며 G4.70/G4.90 뒤바뀜을 막는다. M3×10 screw 2개를 Ø2.80 pilot boss에 가볍게 self-tap하고, deck이 네 기둥 위에 닿은 뒤 더 조이지 않는다.
5. cap tail을 덱의 평평한 윗면에서 해당 **완전 원형 bore**로 넣고, cap pad 하단이 deck에 닿을 때까지 0.350 mm 눌러 유지한다. 이 위치에서 Ø3.50 groove가 앞쪽 clip service opening과 정렬된다.
6. flat C-clip의 열린 입구가 tail을 향하도록 앞쪽 service opening으로 밀어 groove에 건다. 완전히 들어가면 clip을 groove 축 주위로 90° 돌려 열린 입구가 좌/우 cavity 벽을 향하게 한다. 그러면 clip은 앞쪽으로 빠질 수 없다.
7. cap에서 손을 놓는다. ITS return이 cap/clip을 0.350 mm 올리고 clip 상면이 cavity roof에 걸려 cap을 유지한다. 다시 누르면 clip 하단과 cap pad 하단이 동시에 printed deck에 닿아 hard stop을 만든다.
8. 분해는 cap을 끝까지 누름 → clip 입구를 앞쪽으로 90° 복귀 → clip 인출 → cap 인출 → screw 2개 → deck 수직 인양 → switch 위로 인출 순서다.

## Guide 공차 기록

| G bore Ø mm | diametral clearance mm | radial clearance mm | wobble | binding | return | click feel | 100 cycles |
|---:|---:|---:|---|---|---|---|---|
| 4.70 | 0.200 | 0.100 |  |  |  |  |  |
| 4.75 | 0.250 | 0.125 |  |  |  |  |  |
| 4.80 | 0.300 | 0.150 |  |  |  |  |  |
| 4.85 | 0.350 | 0.175 |  |  |  |  |  |
| 4.90 | 0.400 | 0.200 |  |  |  |  |  |

100회 중 한 번도 걸리지 않고 모든 slow/off-axis release에서 복귀하는 가장 작은 G를 선택한 다음, 통과한 후보끼리 wobble을 비교한다.

## Pocket 공차 기록

| P square mm | X side clearance mm | Y side clearance mm | insertion | retention | removal / damage |
|---:|---:|---:|---|---|---|
| 6.30 | 0.090 | 0.125 |  |  |  |
| 6.35 | 0.115 | 0.150 |  |  |  |
| 6.40 | 0.140 | 0.175 |  |  |  |
| 6.45 | 0.165 | 0.200 |  |  |  |
| 6.50 | 0.190 | 0.225 |  |  |  |

## 실물 평가표

| 항목 | 결과 |
|---|---|
| printer / nozzle | Bambu Lab P1S / 0.4 mm |
| filament / 건조 상태 |  |
| layer / wall / line width |  |
| XY / hole compensation | 0.00 baseline |
| P6.30 재확인 |  |
| 선택 G |  |
| cap wobble |  |
| cap binding |  |
| slow/off-axis return 10+10회 |  |
| click feel |  |
| 실측 rest-to-stop travel |  |
| switch retention / removal |  |
| corner locator / wall damage |  |
| 25 / 50 / 100 cycle |  |
| 최종 선택 / 다음 보정 |  |

## 디지털 검사

- B-rep valid, connected base 1 solid, guide deck 1 solid: `PASS`
- cap 5 / retention clip 5 fragmentation: `PASS`
- minimum structural wall: 1.20 mm (`PASS >= 1.20`)
- body ↔ four-corner cradle unintended penetration: 0 mm³
- full uncut formed-pin envelope ↔ cradle penetration: 0 mm³
- four corner posts / actuator / body ↔ guide deck penetration: 0 mm³
- cap + C-clip ↔ deck penetration at rest: 0 mm³
- cap + C-clip ↔ deck penetration at 0.350 mm: 0 mm³, hard-stop faces only coincident
- production source import/write: 0

### Bambu Studio 실제 slice sanity check

- Bambu Studio 02.08.02.60 / `Bambu Lab P1S 0.4 nozzle` / stock 0.20 mm profile
- support: `OFF`; slice return code 0, warning 없음
- 입력 45,976 triangles / 82.00 × 83.25 × 13.50 mm
- slicer의 `Bridge` 태그는 Z=1.40, 1.80, 2.20 mm의 base/deck/cap 내부 top-skin 구간에만 존재했다.
- Z>2.20 mm의 switch cradle, guide bore, retention cavity에는 bridge-tagged extrusion이 0개다. 즉 V1처럼 switch pocket 위에서 filament가 공중에 시작하는 roof가 없다.
