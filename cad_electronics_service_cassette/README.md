# OneGrip Play 전자부품 단층 서비스 카세트 V4

기존 스톡 짐벌 뒤 `RP2040_ZERO_TRAY`를 대체하는 조립성 우선 설계다.
RP2040-Zero와 전원보드를 적층하지 않고 나란히 둔다. 최종 구조에서는
카세트 본체는 오픈소스 짐벌의 고정 하부 부품인 `Base` 전면에 낮은 브리지로
영구 연결하고, 뚜껑만 분리 가능한 정비 부품으로 유지한다. `Base`의 네
스프링 나사 보스와 움직이는 `Spring_holder`의 네 귀는 그대로 보존한다.
별도 부품인 `CARRIER_PLATE`를 짐벌 플레이트로 오인한 이전 출력은 사용하지 않는다.

## 외형과 배치

| 항목 | 값 |
|---|---:|
| 조립 외형 | 36 × 45 × 14 mm |
| 본체 | 36 × 45 × 12 mm |
| 뚜껑 | 36 × 45 × 1.8 mm |
| RP2040 | 17.92 × 23.15 mm, USB 벽 개방 |
| RP2040 포켓 | 18.42 × 24.35 mm |
| RP2040 여유 | 폭 0.25 mm/측, 삽입 방향 0.60 mm/끝 |
| 전원보드 | 23.24 × 15.35 mm 방향으로 90° 회전 |
| 보드 측면 여유 | 0.25 mm/측 |
| 체결 | M3 수직 나사 4개 |

## 사람이 직접 조립하는 순서

1. 짐벌 플레이트+카세트 본체 일체형과 뚜껑을 출력하고 USB 컷·배선
   게이트·나사 구멍을 디버링한다.
2. 두 보드는 **카세트 밖에서** 전원 극성, USB 데이터선, 납땜 상태를 먼저
   검사한다. 필요한 선도 이때 예비 납땜한다.
3. 전원보드 하부를 실물로 보고 네 지지 패드와 겹치는 부품이 없는지 확인한다.
   겹치면 `build_service_cassette.py`의 네 패드 좌표만 이동하고 다시 출력한다.
4. RP2040을 USB 개방부에 맞춰 위에서 넣는다. USB 단자를 먼저 벽 쪽으로
   기울여 넣은 다음 지지 패드 위에 수평으로 내린다.
5. 전원보드를 별도 포켓에 위에서 넣는다. 두 보드는 서로를 덮지 않으므로
   순서를 바꾸어도 된다.
6. 보드 사이 배선은 중앙 `10 × 3.2 mm` 게이트로 통과시킨다. 실물 피드백에
   따라 전원보드 쪽 `+Y` 외벽 단자 개구는 삭제했다. 외부 배선은 RP2040 쪽
   서비스 방향으로 모으고 내부에서 케이블 타이 또는 중성 실리콘으로
   스트레인 릴리프를 만든다.
7. 실제 상부 부품 높이를 재고, 뚜껑 안쪽의 **부품이 없는 PCB 가장자리**에만
   닿도록 EVA 패드 두께를 고른다. 인쇄물이 IC·커넥터를 직접 누르면 안 된다.
8. 뚜껑을 덮고 M3 나사 네 개를 대각선 순서로 조금씩 조인다. 네 나사는 모두
   보드 바깥에 있어 보드를 뺄 필요가 없다.
9. 전원·USB·HID 시험 후 일체형 플레이트를 하우징에 체결한다.

## 정비 순서

1. 전원 분리
2. 뚜껑 M3 4개 제거
3. 해당 보드의 배선만 분리
4. 해당 보드를 위로 꺼냄

스톡 짐벌이나 다른 보드를 제거할 필요가 없다.

## 출력 권장값

- 소재: PETG 권장, PLA도 1차 조립 검증에는 사용 가능
- 노즐: 0.4 mm
- 레이어: 0.20 mm
- 벽: 4줄
- 상·하단: 5층 이상
- 인필: 15~25%
- 플레이트+본체 일체형: 넓은 캐리어 하부를 베드에 놓음, 서포트 없음
- 뚜껑: 바깥 면을 베드에 놓음
- 뚜껑: 서포트 없음

USB 개구의 상단은 약 9.7 mm 브리지이므로 브리징이 불안한 프린터에서는
USB 포트 쿠폰을 먼저 출력한다.

RP2040을 다시 끼우기 전에는
`RP2040_LENGTH_CLEARANCE_COUPON_050_060_070.stl`을 먼저 출력한다. 세 칸은
23.15 mm 방향의 끝당 여유가 각각 `0.50 / 0.60 / 0.70 mm`이며, V4 본체는
가운데 값인 `0.60 mm/끝`을 사용한다.

### 본체와 뚜껑을 같은 출력판에서 출력

`ONEGRIP_ELECTRONICS_CASSETTE_PRINT_LAYOUT_V5.stl`을 사용한다.

- 본체와 뚜껑이 같은 베드 면에 나란히 배치돼 있다.
- 두 부품은 서로 닿지 않는 독립 솔리드이며 연결 탭이 없다.
- 출력 후 절단할 부분 없이 바로 분리된다.
- 전체 출력판 크기는 약 `77 × 45 × 12 mm`다.

### 최종 스프링 Base 일체형

제조용 단일 부품은
`ONEGRIP_STOCK_SPRING_BASE_CASSETTE_BODY_INTEGRATED_V4.stl`이다.

- 원본 `Base`의 중앙 후면 `24 × 43 mm` 카세트형 돌출부는 빨간 X 피드백에
  따라 스프링 데크 경계 `Y=76.636 mm`에서 제거한다.
- 절단 뒤 남는 중앙 후면 벽도 `X=-15~15 mm`, `Y=69~77 mm` 범위에서
  실제 데크 상면 `Z=-21.5996 mm`까지만 제거한다. 바닥 두께 `6.5 mm`를
  유지해 주변 바닥과 단차가 생기지 않는다.
- 수정 고정 하부 `Base`: `100 × 100 × 16.5 mm`, 스프링 나사 보스 4개 유지
- 움직이는 `Spring_holder`: `57.52 × 61.32 × 7 mm`, 스프링 귀 4개 유지
- 카세트와 Base 사이에는 `1 mm` 서비스 간격을 두고, 하단
  `30 × 7 × 5 mm` 브리지로 한 솔리드로 연결한다.
- 카세트 중심은 `(X,Y)=(0,-46.864) mm`다.
- USB 개구는 플레이트 전방 `-Y`를 유지한다.
- 뚜껑은 별도 탈착 부품이다.
- 통합 부품 외형은 약 `100 × 146 × 16.5 mm`다.
- 스프링 보스 4개 보존 영역과 추가 부품의 간섭은 모두 `0 mm³`다.
- Pitch·Spring holder·Roll을 중립, 축별 `±20°`, 대각선 `±20°`로 검사한
  전 자세에서 간섭은 `0 mm³`다.

일체형과 분리 뚜껑을 한 슬라이서 파일로 불러오려면
`ONEGRIP_STOCK_SPRING_BASE_CASSETTE_LID_PRINT_LAYOUT_V4.stl`을 사용한다. 이 파일은
`플레이트+본체` 1솔리드와 `뚜껑` 1솔리드, 총 2개 부품이다.

### 카세트 전면 배치 판단

고정 `Base`의 중앙 전면 배치는 기구적으로 적합하다.

- 좌우 중앙 `X=0`에 있어 고정 하판의 좌우 편심을 만들지 않는다.
- 카세트 본체·브리지·뚜껑은 스프링 보스 4개 보존 영역과 `0 mm³` 간섭이다.
- 가동부를 축별·대각선 `±20°`로 기울였을 때 본체와 뚜껑 모두 간섭 `0 mm³`다.
- USB-C는 외부 `-Y`를 향해 조립과 정비가 쉽다.
- 움직이는 그립으로 올라가는 배선은 뚜껑 통풍구를 이용해 여유 루프를 만들고,
  고정부와 가동부 양쪽에 스트레인 릴리프를 둔다. 실제 케이블 외경과 굽힘
  반경은 최종 배선 전에 실물로 확인한다.

## 아직 확정하면 안 되는 항목

- 전원보드 PCB 실제 두께
- 전원보드 하부 부품의 XY 위치
- 전원보드 상부 최고 부품 높이
- 실제 USB-C 플러그 외형과 케이블 굽힘 반경

남은 실측값은 보드 지지 패드와 케이블 스트레인 릴리프 확정에 사용한다.

## 파일

- `build_service_cassette.py`: 파라메트릭 생성·검증
- `integrate_stock_spring_base_cassette.py`: 실제 Base+본체 영구 연결·스프링/짐벌 운동 검증
- `render_service_cassette.py`: 오프라인 프리뷰 생성
- `render_stock_base_cassette_integration.py`: 실제 스프링 Base·가동부·카세트 결합 프리뷰
- `export/ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_BODY_V4.step/.stl`
- `export/ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_LID_V4.step/.stl`
- `export/ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_ASSEMBLY_V4.step`
- `export/ONEGRIP_ELECTRONICS_CASSETTE_PRINT_LAYOUT_V5.step/.stl`
- `export/ONEGRIP_STOCK_SPRING_BASE_CASSETTE_BODY_INTEGRATED_V4.step/.stl`
- `export/ONEGRIP_STOCK_SPRING_BASE_CASSETTE_LID_ASSEMBLY_V4.step/.stl`
- `export/ONEGRIP_STOCK_SPRING_BASE_CASSETTE_LID_PRINT_LAYOUT_V4.step/.stl`
- `export/STOCK_SPRING_BASE_REAR_REMOVED_FLAT_DECK_REFERENCE.step/.stl`
- `export/STOCK_MOVING_SPRING_HOLDER_REFERENCE.step/.stl`
- `export/RP2040_LENGTH_CLEARANCE_COUPON_050_060_070.step/.stl`
- `export/service_cassette_report.json`
- `export/stock_spring_base_cassette_report.json`
