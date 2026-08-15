# OneGrip Play — 3방향 손가락 입력 카트리지 V1

## 결론

이 디렉터리는 검지·중지·약지·소지 각각에서 손끝 위치를 거의 유지한
채 `LEFT / CENTER / RIGHT`를 입력하는 실제 파라메트릭 CAD와 출력물을
담는다. V1 우선안은 **Variant B 독립 3패들**이다.

- LEFT / RIGHT: 서로 독립된 금속축 회전 패들 + 수직 가이드 팔로워
- CENTER: 회전하지 않는 2점 가이드 직선키
- 센서: Panasonic `EVQ-P0E07K` 3개/카트리지
- 스위치는 신호만 검출하며, 최대 하중은 PETG 셸 하드스톱이 받는다.
- 각 카트리지는 나사로 분리·교체하며 본체를 다시 출력하지 않는다.
- 소지는 검지 STL의 단순 축소가 아니라 별도 폭·레버비·힘 프리셋이다.

이 설계는 P0 제작 전 CAD 검증본이다. 사람에게 맞는지와 95% 입력 정확도는
아직 실물 시험으로 확인해야 하므로 임상적으로 검증됐다고 표현하면 안 된다.

## Lalboard에서 참고한 것과 바꾼 것

공식 Lalboard v2.5.1 소스와 그 소스가 가리키는 3MF를 조사했다. 참고한 것은 중앙 기준점, 독립된
방향키, 짧은 fingertip roll, 오목한 접촉면, 로컬 피벗과 손가락별 조절 원리다.
OneGrip용 원본 CAD를 새로 작성했으며 upstream mesh나 생성 코드는 복사하지
않았다.

제거·변경한 요소:

- 5입력 → LEFT/CENTER/RIGHT 3입력
- 광학 센서·자석·커스텀 PCB → 일반 저압 택트 스위치와 직접 배선
- 3점 자석식 6자유도 지지 → 교체식 카트리지와 별도 슬롯 마운트
- Lalboard의 매우 작은 PLA 공차 → 0.4mm 노즐 PETG 시작 공차

상세 분석과 라이선스는
[`../../docs/lalboard_analysis.md`](../../docs/lalboard_analysis.md)와
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)를 참고한다.
고정한 upstream 커밋과 재생성 절차는
[`../../references/README.md`](../../references/README.md)에 있다.

## 디렉터리

```text
cad/finger-input-v1/
├─ finger_module_common.py        파라메트릭 CAD 원본
├─ finger_module_{index,middle,ring,pinky}.py
├─ variant_{a,b,c}_*.py           비교안 진입점
├─ generate_all.py                전체 재생성
├─ tolerance_coupon.py            PETG 공차 쿠폰
├─ validate_geometry.py           형식·메시·기구 검증
├─ render_previews.py             Blender 5 렌더 생성
├─ printable/                     개별 출력 부품 STL/STEP/3MF + 조립체 STEP/3MF
├─ variants/                      A/B/C 개별 부품과 조립체 CAD
├─ test_fixture/                  P0 높이·각도 조절 지그
├─ integration/                   4손가락 배열 CAD
├─ renders/                       30개 PNG, Blender 장면, 시각화 전용 메시 캐시
└─ reports/                       자동 검증 결과
```

## 산출물 형식 정책

- **개별 출력 부품**은 `STL / STEP / 3MF` 세 형식을 제공한다. 실제 출력에는
  `printable/`, `test_fixture/`, `integration/`, `variants/`의 부품별 STL을 쓴다.
- `*_assembly`, `fixture_with_middle_module`, `four_finger_array`,
  `four_finger_array_with_attached_rail`처럼 서로 접촉하는 여러 부품을 한 파일에
  담은 **조립체의 권위본은 STEP/3MF**다. 조립체 STL은 배포하지 않으며 조립체를
  한 덩어리로 출력해서도 안 된다.
- [`renders/geometry_cache/`](renders/geometry_cache/)의
  `*_visualization_only.stl`은 Blender가 빠르게 읽도록 여러 솔리드를 평탄화한
  **시각화 전용 캐시**다. 접촉 경계 때문에 인쇄용 watertight 메시를 보장하지
  않으므로 출력·치수 검증·제작 전달에 사용하지 않는다.
- 형상이 서로 다르게 보일 경우 개별 부품은 STEP/3MF와 해당 부품 STL을,
  조립 관계는 STEP/3MF를 기준으로 판단한다.

## 손가락별 시작값

| 손가락 | 유효 폭 | 중앙 캡 | 카트리지 외함 | 측면 레버비 | 계산 손끝 힘 | 계산 측면 이동 | 본체 배치 Z / 깊이 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 검지 | 21.0mm | 9.5mm | 35×32mm | 1.35 | 0.548N | 0.837mm | 116 / -3mm |
| 중지 | 22.0mm | 9.5mm | 35×32mm | 1.40 | 0.529N | 0.868mm | 86 / 0mm |
| 약지 | 20.5mm | 8.5mm | 35×32mm | 1.50 | 0.493N | 0.930mm | 57 / -3mm |
| 소지 | 18.5mm | 7.5mm | 35×32mm | 1.65 | 0.448N | 1.023mm | 30 / -8mm |

측면 압력 방향은 카트리지의 `X`, 손가락 길이는 `Y`, 지문면 법선은 `Z`다.
소지 패들은 더 좁고, 스위치에 대한 접촉점 지렛팔이 더 길어 같은 스위치로도
손끝 작동력을 낮춘다.

## P0에서 우선 출력할 파일

전체 네 카트리지를 한 번에 출력하지 않는다. 아래 순서로 진행한다.

1. `test_fixture/petg_tolerance_coupon.stl`
   - 하드스톱 보정은 `hard_stop_shim_0.1mm.*`, `hard_stop_shim_0.2mm.*`,
     `hard_stop_shim_0.3mm.*`도 함께 준비한다.
2. `test_fixture/fixture_base.stl`
3. `test_fixture/fixture_carrier.stl`
4. `printable/index_cartridge.stl`
5. `printable/index_bottom_cover.stl`
6. `printable/index_left_key.stl`
7. `printable/index_left_follower.stl`
8. `printable/index_center_key.stl`
9. `printable/index_right_follower.stl`
10. `printable/index_right_key.stl`
11. 필요하면 `index_*_tpu_pad.stl`

`fixture_with_middle_module.step/.3mf`와 `*_assembly.step/.3mf`는 조립 위치를
확인하는 권위본이며 한 덩어리로 출력하는 파일이 아니다. 같은 장면의
`renders/geometry_cache/*_visualization_only.stl`은 렌더 전용이다.

## 대표 렌더

Variant B의 실제 분리 부품, 작동 상태와 네 손가락 통합 배치를 먼저 확인한다.
모든 이미지는 위 형식 정책에 따라 생성한 시각화 자료이며 제작 치수의 권위본은
CAD STEP/3MF다.

![Variant B 분해도](renders/variant_b_05_exploded.png)

![Variant B LEFT 작동 상태](renders/variant_b_07_state_left.png)

![네 손가락 배열과 M 그립 통합 프리뷰](renders/final_03_grip_m_integration_preview.png)

## 권장 출력 조건

### PETG 셸·키

- 0.4mm 노즐, 0.2mm 층
- 외벽 4줄, 상·하 5층 이상
- 25~35% gyroid/cubic infill
- 키 뿌리와 피벗 주변은 5벽 또는 modifier로 60% 이상
- 치수 우선: XY 보정·elephant-foot 보정을 먼저 쿠폰에서 결정
- 축 구멍은 서포트와 맞닿지 않게 배치하고 출력 뒤 Ø2.4mm 리머/드릴로
  손으로 정리한다. 전동 공구로 구멍을 크게 만들지 않는다.

### TPU 패드

- TPU 95A, 0.2mm 층, 외벽 3줄
- 패드는 선택 사항이다. PETG 키만 먼저 시험해 경계가 불분명하거나 피부
  압박이 있을 때 붙인다.
- 순간접착제로 영구 고정하기 전에 얇은 양면테이프로 두께를 비교한다.

### 서포트

- 셸: 평평한 바닥면을 베드에 두면 내부 6.6mm 브리지만 남는다. 일반적인
  튜닝 프린터에서는 무서포트 시작안이다.
- 바닥 커버·마운트·쿠폰: 무서포트.
- 패들 키: 피벗 축을 수평으로 놓으면 원통 하부 품질이 나빠질 수 있으므로
  슬라이서에서 키를 옆면으로 눕히고 빌드플레이트 한정 유기 서포트를 피벗
  배럴에만 허용한다. 첫 P0에서는 0.15mm와 0.20mm 접촉 여유를 모두 시험한다.

## 필요한 기계 부품 — 한 카트리지

- EVQ-P0E07K 3개
- Ø2.0mm 스테인리스 축 2개, 각 약 14.5mm
- Ø1.0mm 스테인리스 anti-loss pin 2개, 각 약 4mm
- M2 바닥 커버 나사 4개와 M2 insert 4개
- M3 카트리지 장착 나사 2개와 insert/너트
- JST-SM 4P pigtail 1세트
- 26~28AWG 연선 4가닥: LEFT, CENTER, RIGHT, COMMON GND

완전 BOM과 공식 전기 조건은
[`../../docs/finger_module_bom.md`](../../docs/finger_module_bom.md)에 있다.

## 조립 순서

1. 공차 쿠폰에서 축 구멍과 이동 간극을 선택한다.
2. 셸의 스위치 포켓, 배선 홈, 축 구멍만 정리한다. 키 접촉면을 사포로 임의
   변경하지 않는다.
3. CENTER 키의 두 post를 guide에 넣고 Ø1mm anti-loss pin 두 개를 측면
   슬롯으로 삽입한다. 핀은 키와 함께 0.62mm 이동해야 한다.
4. LEFT/RIGHT 키를 pivot ear 사이에 두고 Ø2mm 축을 끼운다. 축 끝은 E-clip,
   얇은 열수축튜브 또는 나사 고정용 소형 collar로 이탈을 막는다.
   각 키 아래에는 같은 방향의 수직 팔로워를 가이드에 먼저 넣는다.
5. 셸을 뒤집어 스위치 3개를 각 포켓에 넣는다. `C/NO` 두 단자를 사용한다.
6. 세 스위치의 한쪽 단자를 GND로 묶고 나머지를 L/C/R 신호선으로 납땜한다.
7. 배선을 홈에 눕히고 rear exit 뒤에 열수축튜브 또는 케이블 타이로 strain
   relief를 만든다. 움직이는 키·축과 배선이 닿으면 안 된다.
8. 바닥 커버를 M2 나사로 조인다. 스위치가 흔들리지 않을 만큼만 조이며,
   커버로 스위치 몸체를 변형시키지 않는다.
9. 무부하 100회 복귀와 멀티미터 연속성 검사를 한 뒤 지그에 M3로 장착한다.

## 배선

```text
JST-SM 4P
1  BLACK  COMMON GND ─┬─ switch L
                     ├─ switch C
                     └─ switch R
2  BLUE   LEFT signal
3  WHITE  CENTER signal
4  YELLOW RIGHT signal
```

MCP23017은 3.3V 입력과 풀업으로 읽고 기구 시험에서는 ON 5ms / OFF 10ms stable debounce를
같게 적용한다. 펌웨어 상호잠금으로 기구 오입력을 숨기지 않는다.

## 하드스톱과 조정

- EVQ-P0E07K 최대 pretravel 0.50mm
- CAD 기본 stop gap: 0.62mm. 실제 작동거리를 실측한 뒤 `작동거리 + 0.10~0.12mm`가 되도록 U-shim으로 줄임
- center 총 stroke: 0.62mm 직선 이동
- side switch 지점 이동: 0.62mm; 손끝에서는 레버비에 따라 0.84~1.02mm
- 축 지름: Ø2.0mm; CAD 축공 Ø2.4mm(직경 0.4mm 시작 여유)
- 스위치 포켓: 실물 외형에서 면당 0.20mm 시작 여유

스위치를 먼저 넣고 키가 바닥까지 계속 눌리는 경우 P0를 중단한다. 스위치가
구조 스토퍼가 된 것이므로 셸 랜딩 또는 0.1/0.2/0.3mm shim으로 하드스톱을
앞당긴다.

## 테스트

1. 멀티미터로 L/C/R 독립성을 확인한다.
2. 중립 60초 자동 입력이 없어야 한다.
3. 방향별 30회, 총 90회 무작위 입력을 기록한다.
4. CENTER 4Hz, LEFT/RIGHT 3Hz 반복 시험을 한다.
5. 같은 지그에서 A/B/C를 비교하고 소지를 별도 확인한다.

정확한 판정식과 P0/P1/P2 Gate는
[`../../docs/finger_module_test_protocol.md`](../../docs/finger_module_test_protocol.md)를
따른다.

## 재생성

Python 3.12와 `requirements-cad.txt`를 사용한다.

```powershell
python -m pip install -r cad/finger-input-v1/requirements-cad.txt
python cad/finger-input-v1/generate_all.py
python cad/finger-input-v1/tolerance_coupon.py
python cad/finger-input-v1/validate_geometry.py
```

Blender 5 렌더:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe' `
  --background --python cad/finger-input-v1/render_previews.py
```

## 현재 알려진 한계

- CAD의 손가락 surrogate는 인체 계측 proxy일 뿐 실제 사용자 손이 아니다.
- M 그립 통합은 대략 배치로, 실제 체결용 벽·나사 보스·손바닥/엄지 clearance는
  P1/P2 뒤 본체 CAD에 반영해야 한다.
- 자동 검증은 파일 형식·솔리드 간섭·캠/팔로워 접촉·유지핀 이동창·단자 relief·마운트 범위를 확인한다. 스위치 편차, PETG
  크리프, 피부 압력, 경직·떨림, finger enslaving은 실물 시험이 필요하다.
- 자동 형식 검증의 STL 대상은 개별 출력 부품이다. 조립체는 STEP/3MF의 독립
  솔리드를 검사하며 `renders/geometry_cache`의 평탄화 STL은 검증·출력 대상에서
  제외한다.
- 측면 패들 회전은 약 7.75°다. 소지 손끝 이동은 약 1.02mm지만, 실제
  촉각 경계가 불명확하면 소지 피벗/스위치 위치를 P0 데이터로 바꿔야 한다.
- 8월 16일까지 B안이 P0 Gate를 통과하지 못하면 C안을 튜닝하지 않고 A안으로
  전환한다.
