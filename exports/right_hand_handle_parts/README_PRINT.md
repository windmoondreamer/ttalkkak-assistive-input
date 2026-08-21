# OneGrip 오른손 핸들 출력 세트

## 바로 출력할 파일

`plates/OneGrip_RightHand_Handle_plate_01_of_01.stl`

프로젝트 기록의 Bambu Lab P1S 기준으로 배치했다.

- plate: 256 × 256 mm
- 실제 모델 점유 범위: X 13.000–237.103 mm / Y 13.000–233.091 mm
- 실제 최소 가장자리 여유: 13.0 mm
- 파트 간 최소 간격: 10.0 mm
- 최대 출력 높이: 38.759 mm
- printable solids: 30
- STL disconnected components: 30
- triangle count: 165,612
- plate STL SHA-256: `9DF047B3E161A1F1E1FBC990F88FEE9ADFE325784553F4A68F5F15F4FAF3F6C4`

## 슬라이서에서

1. 단위를 `mm`로 연다.
2. plate STL을 원점 기준 그대로 불러온다.
3. `자동 배치/Auto arrange`는 실행하지 않는다. 이미 10 mm 안전 간격으로 배치돼 있다.
4. 하나의 모델로 보이더라도 STL 내부에는 서로 닿지 않는 30개 component가 있다.
5. 출력 전 슬라이스 미리보기에서 첫 레이어와 shell 내부 overhang을 확인한다.
6. 작은 spacer/cap의 첫 레이어가 불안하면 brim 3–5 mm를 추가한다.

## 구성

- `OneGrip_RightHand_Handle_Parts.zip`: Onshape 원본 개별 STL 30개
- `individual_stl/`: 압축을 푼 개별 STL
- `plates/OneGrip_RightHand_Handle_plate_01_of_01.stl`: 한 판 출력용 결합 STL
- `plates/OneGrip_RightHand_Handle_plate_01_layout.png`: 배치도
- `plates/layout_manifest.json`: 모든 파트의 방향, 위치, 치수 및 검증값
- `OneGrip_RightHand_Handle_PrintSet.zip`: 위 자료를 묶은 최종 전달 파일

다른 프린터의 베드가 256 × 256 mm보다 작으면 이 plate STL을 그대로 출력하지 말고 개별 STL을 다시 패킹해야 한다.
