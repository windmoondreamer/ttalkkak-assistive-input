# P0 단일 손가락 지그

## 목적

OneGrip 전체 그립을 출력하기 전에 손가락 하나로 LEFT/CENTER/RIGHT의 구분,
힘, 연타, 복귀를 확인하는 지그다. `fixture_base`와 `fixture_carrier`는 분리
출력하고 M4 볼트 두 개로 결합한다.

## 조절 범위

- 높이: 두 upright의 24mm 세로 슬롯
- 각도: carrier의 횡축을 기준으로 마찰 고정; 기구상 ±15° 이상, 시험은
  OneGrip 목표 범위인 ±8°부터 사용
- 카트리지 깊이: carrier의 19.4mm 전체 슬롯(볼트 중심 가동 16mm), 기준에서 ±8mm

## 출력 파일

- `petg_tolerance_coupon.stl` — 반드시 먼저 출력
- `hard_stop_shim_0.1mm.*`, `hard_stop_shim_0.2mm.*`,
  `hard_stop_shim_0.3mm.*` — 0.1/0.2mm는 치수 참고
- `hard_stop_shim_profile.dxf` — 0.1/0.2mm PET shim stock 절단용 2D 프로파일
- `fixture_base.stl`
- `fixture_carrier.stl`
- `fixture_with_middle_module.step/.3mf` — 독립 솔리드를 유지한 조립 확인 권위본,
  일체 출력 금지

개별 출력물은 위 `*.stl` 세 파일과 필요한 shim이다. 지그·중지 카트리지가
접촉한 전체 조립체는 STEP/3MF로만 배포하며 합쳐진 조립체 STL은 제공하지 않는다.

## 체결품

- M4×35 볼트 2, M4 와셔 4, M4 손잡이 너트 2
- M3×10 볼트 2, M3 너트 또는 insert 2
- 책상 고정용 M6 볼트 또는 클램프 2

## 사용 순서

1. 지그를 책상에 고정한다.
2. 가운데손가락 높이를 기준으로 carrier를 맞춘다.
3. 손목·손가락에 힘을 주지 않은 상태에서 CENTER 캡 중심에 지문 중심이
   오도록 높이와 깊이를 맞춘다.
4. 각도를 0°에서 시작해 ±3°, ±6°, ±8° 순으로 한 변수씩 바꾼다.
5. [`../../../docs/finger_module_test_protocol.md`](../../../docs/finger_module_test_protocol.md)의 P0 절차를 실행한다.
