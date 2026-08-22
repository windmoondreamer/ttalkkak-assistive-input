# INDEX / MIDDLE 버튼 삽입부 FDM 출력성 감사

Date: 2026-08-21  
Scope: INDEX/MIDDLE shell-integrated button seats and supports only  
THUMB: excluded and unchanged  
CAD WRITE: 0

## 결론

현재 하우징 STL은 watertight mesh이지만, 검지·중지 버튼 삽입부를 포함한
**기능성 FDM 출력물로는 HOLD**다. 기존 `printMeshGate = PASS`는 manifold,
winding, connected-component 검사만 통과했다는 뜻이며, 적층 오버행이나
실제 switch 삽입 공차를 인증하지 않았다.

현재 한판 STL은 두 shell의 mating plane을 베드에 놓는다. 이 방향에서
I2/I3/I4 및 M2/M3/M4의 seat/support axis가 build vertical로부터 45°를 넘고,
특히 I3/I4 및 M3/M4는 거의 수평인 하향면을 가진다.

## 버튼별 결과

| button | owner | center build height (mm) | axis tilt from build vertical | near-horizontal downward area (mm²) | support-free functional print |
|---|---|---:|---:|---:|---|
| I1 | JfD | 22.224 | 32.0° | 9.3 | MARGINAL |
| I2 | JfD | 15.970 | 67.2° | 8.5 | HOLD |
| I3 | JfD | 5.496 | 86.1° | 179.3 | HOLD |
| I4 | JaD | 5.496 | 88.6° | 149.9 | HOLD |
| M1 | JfD | 19.835 | 33.1° | 26.7 | MARGINAL |
| M2 | JfD | 12.899 | 53.0° | 7.3 | HOLD |
| M3 | JfD | 3.538 | 71.3° | 134.8 | HOLD |
| M4 | JaD | 7.444 | 77.0° | 109.3 | HOLD |

JfD 외피에 몰려 있는 3개 그룹을 기준으로 보면 I1/M1은 형상 자체가 생성될
가능성은 있으나, I2/M2부터 support-free 신뢰성이 낮고 I3/M3는 베드 가까이에서
수평 seat/support 형상이 형성되어 가장 실패 가능성이 높다.

## 기능 공차

- switch seat: 6.40 × 6.40 mm
- conservative body envelope: 6.18 × 6.12 mm
- conservative side clearance: 0.11 / 0.14 mm per side
- physical sample 6.12 × 6.05 mm 기준: 0.14 / 0.175 mm per side
- 6.4/6.5/6.6/6.7 mm pocket coupon: 아직 미검증

수평 천장의 bridge sag, support 접촉흔적, XY 수축 또는 elephant foot 중 하나만
발생해도 0.11–0.175 mm side clearance를 소비한다. 따라서 shell이 출력되더라도
실제 ITS-1105 body가 삽입되거나 반복 탈착된다는 보장은 없다.

## 최소 구조

| item | minimum | FDM interpretation with 0.4 mm nozzle |
|---|---:|---|
| INDEX divider | 0.807 mm | 약 2 line, 경계 |
| INDEX terminal web | 1.553 mm | 약 3–4 line |
| MIDDLE ring annulus | 0.80 mm | 약 2 line, 경계 |
| MIDDLE side beam | 0.80 mm | 약 2 line, snap root로는 취약 |
| MIDDLE hook depth | 0.70 mm | 2 line 미만 가능, 파손 위험 |
| MIDDLE divider | 1.042 mm | 약 2–3 line |

INDEX는 rear가 열려 있어 support 제거 접근은 상대적으로 낫다. MIDDLE은 rear
beam/hook가 shell에 통합돼 있어 support가 생성되면 제거 과정에서 0.8/0.7 mm
구조를 손상하거나 seat 내부를 거칠게 만들 가능성이 높다.

## 판정

- shell mesh/manifold: PASS
- 외형 크기 확인용 하우징 mock-up: CONDITIONAL
- 현재 방향의 support-free 출력: HOLD
- ITS-1105 실제 삽입/작동용 출력: HOLD
- THUMB 변경 필요: 없음

## 다음 CAD 단계 권고

1. THUMB geometry는 유지한다.
2. INDEX/MIDDLE seat ceiling을 45° chamfer 또는 self-supporting 형상으로 바꾼다.
3. MIDDLE 0.8 mm beam/ring과 0.7 mm hook root를 FDM용으로 보강하거나,
   holder를 shell과 분리된 삽입형 carrier로 만든다.
4. full shell보다 먼저 6.4/6.5/6.6/6.7 mm pocket coupon을 출력해 실제 lot과
   filament별 삽입 공차를 확정한다.
5. 최종 출력 STL에는 기능 seat 내부 support가 생기지 않는 방향 또는 분할 구조를
   적용하고, slicer layer preview에서 floating island와 bridge를 재검사한다.

Numeric data: `cad_dump/index_middle_printability_audit.json`
