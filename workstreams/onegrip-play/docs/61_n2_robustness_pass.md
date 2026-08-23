# 61 — N2 robustness pass

## 결론

`N2 ARCHITECTURE = ACCEPT`를 유지한다. Cap/direct actuation/guide/rear reaction/hard stop/switch pose/exterior는 변경하지 않았다.

다만 요구 robustness target 두 개는 frozen geometry와 physical housing limit 안에서 달성할 수 없어 최종 `N2 PRODUCTION-INTENT ROBUSTNESS = HOLD`다.

## 1. HW504 A ↔ carrier

- Before: **0.004964 mm**, penetration 0
- Required: **0.500 mm**, preferred 0.800 mm
- Applied change: 기존 승인 non-functional corner relief의 tangential extent만 0.18 → 0.50 mm 확장
- Wall-normal depth increase: **0.000 mm**
- Removed carrier material: **0.180647 mm³**
- After / exact available maximum: **0.011000 mm**, penetration 0
- Next limiting geometry: **frozen rear reaction support**, distance 0.011000 mm
- Existing relief wall: **1.314848 mm**
- Overall minimum wall: **1.200 mm**
- Verdict: **HOLD**

0.50 mm를 만들려면 frozen rear reaction support 또는 1.20 mm wall gate를 건드려야 하므로 자동으로 더 깎지 않았다.

## 2. Trimmed T2/T4

- Current axial external stub: **0.150000 mm**
- Current external centerline stub: **0.154382 mm**
- Current clearance: **0.818769 mm**
- Housing-flush stub: **0.000 mm**
- Housing-flush maximum clearance: **0.959811 mm**
- 1.00 mm theoretical cut depth: **8.317259 mm**
- Additional shortening from current: **0.192741 mm**
- 1.00 mm target axial stub: **-0.042741 mm**
- 1.00 mm target external stub: **0.000000 mm** (plus 0.042741 mm forbidden housing intrusion)
- Physical verdict: **TOO CLOSE TO HOUSING**
- Real cut safety: **CONDITIONAL — pending user physical test**
- Robustness verdict: **HOLD**

Target은 housing rear plane보다 0.042741 mm 안쪽이므로 housing/leadframe 금지 영역이다. Current T2/T4 production trim은 변경하지 않았다. T1/T3 geometry와 solder access도 변경하지 않았다.

## 3. Motion revalidation

| Travel mm | Cap↔shell pen mm³ | Cap↔guide pen mm³ | Cap↔actuator pen mm³ | Hard-stop residual mm | Result |
|---:|---:|---:|---:|---:|---|
| 0.000 | 0.000000000 | 0.000000000 | 0.000000000 | 0.350 | PASS |
| 0.175 | 0.000000000 | 0.000000000 | 0.000000000 | 0.175 | PASS |
| 0.350 | 0.000000000 | 0.000000000 | 0.000000000 | 0.000 | PASS |

- T1/T3 ↔ HW504 B minimum: **2.119093 mm** — unchanged
- Robust carrier ↔ HW504 penetration: **0 mm³**
- N2 exterior geometry delta: **0 mm³**
- N2 motion: **PASS**

## 4. Final verdict

- `N2 ARCHITECTURE = ACCEPT`
- `HW504 A ↔ CARRIER ROBUSTNESS = HOLD`
- `T2/T4 TRIM ROBUSTNESS = HOLD`
- `N2 MOTION = PASS`
- `N2 EXTERIOR = PRESERVED`
- `N2 PRODUCTION-INTENT ROBUSTNESS = HOLD`

## 5. Outputs / STOP

- `build123d_workbench\out\n2_robustness_pass\N1_N2_SHARED_CARRIER_N2_ROBUSTNESS.step` — local carrier STEP only
- `build123d_workbench\out\n2_robustness_pass\n2_robustness_pass.json`
- `renders\n2_robustness_pass` — four required renders

Full shell / STL / print plate는 생성하지 않았다. 다른 버튼으로 확장하지 않고 여기서 STOP한다.
