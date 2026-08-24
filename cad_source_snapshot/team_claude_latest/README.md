# 팀원 최신안·Claude Code 최소 원본 스냅숏

이 폴더는 `cad/onegrip-full-module-v3/build_full_module_blender.py`를 다른
컴퓨터에서도 재실행할 수 있도록 필요한 최소 원본만 모은 스냅숏이다.

## 포함 범위

- 팀원 최신 OneGrip 우측 그립의 상부 쉘 기준 JSON 2개
- 원본 조립 위치를 읽기 위한 `asmdef_Joystick.json`
- 원형을 유지한 엄지 버튼·조이스틱 부품 STL 10개
- Claude Code 작업에서 생성·검토한 하부 매립형 짐벌 JSON 5개

전체 Desktop 작업 폴더나 중간 렌더·캐시는 복사하지 않았다. 현재 통합 모델을
재생성하는 데 실제로 참조되는 파일만 포함한다.

## 작업 계보

1. **팀원 최신안**
   - 우측 그립 상부 쉘과 기존 엄지 구조
   - 원본 버튼 및 조이스틱 부품
2. **Claude Code 체크포인트**
   - `build123d_workbench`의 검지·중지·엄지 구조 분석
   - `lower_adapter`의 20° 매립형 하부 짐벌 형상과 검증 자료
3. **현재 저장소 통합본**
   - 검지·중지 8버튼 카세트 V2
   - 하부 짐벌 고정/가동 부모 계층과 좌표계 보정
   - RP2040·전원보드 단층 서비스 카세트

팀원 작업 폴더와 Claude Code 전체 체크포인트에 있던
`lower_adapter/cad_dump/mesh_EMB_HOUSING.json`의 SHA-256은 다음과 같이
동일함을 확인했다.

```text
F2D73A368F7B4CA74B48FD66985B4F9EF59EF95CFA53F0481D3F68DACF3E59DB
```

따라서 현재 저장소의 하부 짐벌 입력은 두 작업본 사이에서 같은 형상을
기준으로 한다.

