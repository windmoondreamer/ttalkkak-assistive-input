# 58 — Button cap plane mapping

## 결론

8개 모두 실제 cap 외측 평면과 ITS-1105 housing 상면이 동일한 actuation axis에 수직이므로 **서로 평행**하다. Exact B-rep face-normal 비교값은 모두 허용오차 0.05° 이내다.

Shell tangent와의 관계는 별도다. `I2/I3`은 내부 간격 확보용 2.5° tilt, `M4/N3`는 4.0° tilt가 적용되어 cap 평면도 shell local tangent에서 같은 각도만큼 기울어져 있다. `I4/M3/N1/N2`는 shell tangent와 평행하다.

| ID | Owner | Carrier | cap ↔ switch plane | cap ↔ shell tangent | cap ↔ switch in-plane roll | Result |
|---|---|---|---:|---:|---:|---|
| I2 | JfD | I2_I3_shared_carrier | 0.000000° | 2.500° | -15.649° | PASS |
| I3 | JfD | I2_I3_shared_carrier | 0.000000° | 2.500° | -1.450° | PASS |
| I4 | JaD | I4_carrier | 0.000000° | 0.000° | -179.329° | PASS |
| M3 | JfD | M3_carrier | 0.000000° | 0.000° | -9.809° | PASS |
| M4 | JaD | M4_N3_shared_carrier | 0.000000° | 4.000° | -166.876° | PASS |
| N1 | JfD | N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF | 0.000000° | 0.000° | -2.422° | PASS |
| N2 | JfD | N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF | 0.000000° | 0.000° | -6.466° | PASS |
| N3 | JaD | M4_N3_shared_carrier | 0.000000° | 4.000° | -150.653° | PASS |

## 해석

- Cap 외측 평면 normal = actuation axis
- ITS-1105 top plane normal = actuation axis
- Cap socket / actuator axis offset = 0
- 외부 승인 center 이동 = 0.000 mm
- In-plane roll은 정사각 cap과 switch body의 평면 내 회전이며 평행도에는 영향을 주지 않는다.
- N2는 현재 추가 -5° clocking을 포함하지만 actuation axis와 상면 평행도는 변하지 않는다.

## Output

- `build123d_workbench/out/button_cap_plane_mapping/button_cap_plane_mapping.json`
- `renders/button_cap_plane_mapping/00_all_8_button_plane_mapping.png`
- `renders/button_cap_plane_mapping/01_I2_plane_mapping.png` … `08_N3_plane_mapping.png`

이 작업은 read-only mapping/render이며 production geometry를 수정하지 않았다.
