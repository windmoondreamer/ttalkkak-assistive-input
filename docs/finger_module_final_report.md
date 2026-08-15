# OneGrip Play 3방향 손가락 모듈 — 최종 구현 보고

작성일: 2026-08-13  
상태: CAD·디지털 검증 완료, P0 실물 검증 대기

## A. 결론

V1 손가락 입력 기구로 **Variant B — 독립 3패들 카트리지**를 선정했다.

- LEFT와 RIGHT는 Ø2mm 스테인리스 축을 쓰는 별도 회전 패들이다.
- CENTER는 회전하지 않는 2점 가이드 직선키다.
- 방향별 Panasonic `EVQ-P0E07K` 스위치 하나가 신호를 검출한다.
- 회전 패들의 짧은 캠이 별도 수직 팔로워를 내려 스위치에는 축방향 힘만 준다.
- 0.62mm 기본 스톱은 실측 작동거리 뒤 0.10~0.12mm가 되도록 U-shim으로 보정한다.
- 검지·중지·약지·소지는 접촉 폭과 레버비가 서로 다른 네 프리셋이다.
- 각 모듈은 나사 체결 카트리지라 본체를 재출력하지 않고 교체할 수 있다.

자동 검증은 최종 재생성 산출물에 대해 솔리드 간섭·캠/팔로워 접촉·유지핀
행정·단자 relief·±8mm/±8° 마운트를 다시 실행한다. 합격 수치는
`reports/geometry_validation.md`의 최신 소스 해시를 기준으로 하며, 실제 손에서
편안하고 95% 정확하다는 뜻은 아니다.

## B. 왜 이 안을 선택했는가

| 안 | 가중점수 | 판단 |
|---|---:|---|
| A 직접 3스위치 | 76.2/100 | 일정 백업. 빠르지만 손가락 중앙 지지가 약함 |
| B 독립 3패들 | **85.6/100** | V1 우선. 방향 분리·손가락별 튜닝·수리성 우수 |
| C 공유 로커 | 61.4/100 | 제외. 동시입력·공차·피벗 마모 위험 |

공식 Lalboard는 공용 로커가 아니라 중앙 독립 직선키와 방향별 독립 회전키를
쓴다. OneGrip는 그 원리를 3입력만 남기고 광학센서·자석·PCB 없이 단순화했다.
소지는 레버비 1.65로 손끝 계산 작동력을 약 0.448N까지 낮췄다.

## C. 생성한 파일

- 파라메트릭 CAD: [`../cad/finger-input-v1/finger_module_common.py`](../cad/finger-input-v1/finger_module_common.py)
- 손가락 프리셋: `finger_module_index.py`, `middle.py`, `ring.py`, `pinky.py`
- A/B/C 소스와 출력: [`../cad/finger-input-v1/variants/`](../cad/finger-input-v1/variants/)
- 손가락별 개별 출력 부품 STL·STEP·3MF와 조립체 STEP·3MF: [`../cad/finger-input-v1/printable/`](../cad/finger-input-v1/printable/)
- P0 지그·공차 쿠폰: [`../cad/finger-input-v1/test_fixture/`](../cad/finger-input-v1/test_fixture/)
- 4손가락 배열·P1 rail STEP/3MF: [`../cad/finger-input-v1/integration/`](../cad/finger-input-v1/integration/)
- 30개 렌더·편집 가능 Blender 5 장면·시각화 전용 캐시: [`../cad/finger-input-v1/renders/`](../cad/finger-input-v1/renders/)
- 자동 검증기: [`../cad/finger-input-v1/validate_geometry.py`](../cad/finger-input-v1/validate_geometry.py)
- 검증 결과: [`../cad/finger-input-v1/reports/geometry_validation.md`](../cad/finger-input-v1/reports/geometry_validation.md)
- 제작 안내: [`../cad/finger-input-v1/README.md`](../cad/finger-input-v1/README.md)
- Lalboard 분석: [`lalboard_analysis.md`](lalboard_analysis.md)
- 구조 비교: [`finger_module_tradeoff.md`](finger_module_tradeoff.md)
- BOM: [`finger_module_bom.md`](finger_module_bom.md)
- 시험법: [`finger_module_test_protocol.md`](finger_module_test_protocol.md)

## D. 바로 출력할 파일

P0에서는 다음만 출력한다.

1. `test_fixture/petg_tolerance_coupon.stl`
2. `test_fixture/fixture_base.stl`
3. `test_fixture/fixture_carrier.stl`
4. `printable/index_cartridge.stl`
5. `printable/index_bottom_cover.stl`
6. `printable/index_left_key.stl`
7. `printable/index_left_follower.stl`
8. `printable/index_center_key.stl`
9. `printable/index_right_follower.stl`
10. `printable/index_right_key.stl`
11. `test_fixture/hard_stop_shim_0.1mm.*`, `hard_stop_shim_0.2mm.*`,
    `hard_stop_shim_0.3mm.*`
12. 필요 시 `index_left/center/right_tpu_pad.stl`

`index_assembly.step/.3mf`와 `fixture_with_middle_module.step/.3mf`는 독립
솔리드를 유지한 조립 확인 권위본이며 한 덩어리로 출력하지 않는다. 조립체 STL은
배포하지 않는다. `renders/geometry_cache/*_visualization_only.stl`은 Blender용
평탄화 캐시로, 인쇄·치수 검증·제작 전달에는 사용하지 않는다.

## E. 필요한 P0 부품

- EVQ-P0E07K 3개 + 예비·선별용 3개
- Ø2mm 스테인리스 봉 약 30mm
- Ø1mm 스테인리스 봉 약 10mm
- M2×5~6 바닥 커버 나사 4개와 M2 insert 4개
- M3×8~10 카트리지 체결 나사 2개와 너트/insert
- JST-SM 4P 수·암 pigtail 1세트
- 26~28AWG 4색 연선 약 0.3m
- 열수축튜브, PETG, 선택 TPU 95A
- 지그용 M4×35 볼트·와셔·손잡이너트 2세트

전체 4손가락 부품비 추정은 보유 필라멘트 사용 시 약 5.5만~8.8만원,
필라멘트와 부자재를 새로 사면 약 9만~14만원이다.

## F. 조립 순서

1. 공차 쿠폰으로 Ø2mm 축공과 움직임 간극을 고른다.
2. 셸·LEFT/CENTER/RIGHT 키와 LEFT/RIGHT 팔로워를 출력하고 축공만 손으로 정리한다.
3. CENTER 두 post를 guide에 넣고 Ø1mm anti-loss pin 두 개를 끼운다.
4. 수직 팔로워를 guide에 넣고 LEFT/RIGHT를 ear 사이에 둔 뒤 Ø2mm 축 두 개를 끼운다.
5. 셸 하부에 스위치 3개를 넣고 한쪽 단자를 공통 GND로 묶는다.
6. 나머지 단자를 L/C/R에 납땜하고 JST 4P로 뺀다.
7. wire channel과 rear exit에서 strain relief를 만든다.
8. 바닥 커버를 M2로 닫고 100회 수동 복귀·연속성 시험을 한다.
9. 지그에 장착하고 높이·깊이·각도를 맞춘다.

세부 조립·출력 조건은 CAD README가 기준이다.

## G. 아직 검증해야 하는 것

- PETG 출력 후 실제 축공·guide·switch pocket 간극
- center/side 실측 작동력과 hard-stop 뒤 실제 overtravel
- LEFT/CENTER/RIGHT 각 30회 정확도와 인접·중복 입력
- CENTER 4Hz, LEFT/RIGHT 3Hz 연타와 100% 복귀
- 약지·소지 finger-enslaving과 소지 피로
- 10N 정적 하중과 1,500회 P0 내구 뒤 균열·유격
- P1 네 손가락에서 손가락별 높이·깊이·±8° 각도
- M 그립에서 엄지·손바닥·배선·스트랩과의 간섭

자동 검증 범위와 실제 파일 수는 최종 보고서에 자동 기록된다. 핵심 범위는
개별 부품 STL/STEP/3MF 재열기와 형식 간 치수, 조립체 STEP/3MF 독립 솔리드,
4프리셋×4상태의 실제 B-rep 간섭,
캠·팔로워·switch contact, switch pocket·단자·cover, anti-loss pin 이동창,
wedge·mount·fixture·array/rail 체결 정렬이다.

## H. 다음 행동

1. 공차 쿠폰과 검지 B안 P0를 즉시 출력한다.
2. 출력과 동시에 같은 스위치 6개를 작동력별로 선별한다.
3. 90회 무작위 입력과 반복 시험을 기록한다.
4. B안이 Gate를 통과하면 소지 프리셋을 출력한다.
5. B안이 Gate를 통과하지 못하면 2026-08-16에 A안으로 전환한다.
6. B/A가 결정된 뒤에만 네 손가락 rail을 출력하고 P1을 진행한다.
7. P1 데이터가 나온 뒤 기존 M 그립의 사본에만 체결 rail과 배선 창을 넣는다.
