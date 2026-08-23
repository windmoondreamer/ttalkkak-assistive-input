# build123d 작업 환경

날짜: 2026-08-21  
기준 CAD: `FINGER_SIMPLIFIED_CARRIER_V1`  
Onshape versionId: `f51e9d9a868db9ef0fcd4b06`

## 목적

Onshape의 확정 형상을 임의로 추정해 다시 그리는 환경이 아니라, 확정된
I1~I4/M1~M4 중심·축과 RWID/RZKD 캐리어 치수를 로컬 파라메트릭 코드의
고정 기준으로 사용한다.

## 환경

- Python: `3.12`
- build123d: `0.11.1`
- 가상환경: `.venv-build123d`
- 코드: `build123d_workbench/`
- 생성물: `build123d_workbench/out/` (Git 제외)

설치 및 전체 검증:

```powershell
.\scripts\setup_build123d.ps1
```

STEP/STL만 다시 생성:

```powershell
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.export_baseline
```

스모크 테스트:

```powershell
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.smoke_test
```

MIDDLE 신규 설계/검증/렌더/출력 배치:

```powershell
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.validate_middle_redesign
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.render_middle_redesign
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.prepare_middle_print_stl
```

`middle_redesign.py` 상단에 switch/pocket/cap/opening/exposure, M1~M4 datum,
carrier wall, terminal/wiring clearance를 모았다. 신규 캐리어 OCC B-rep은
`validate_middle_redesign.py`에서 고정 INDEX/RWID/RZKD mesh obstacle과 함께
검사하며, 모든 스크립트의 Onshape CAD WRITE는 0건이다.

## 모델 경계

현재 build123d 네이티브 B-rep으로 이식한 범위는 단순 공용 캐리어의 신규
재료다.

- JfD/RWID 측: I1~I3 포스트 3, M1~M3 포스트 3, 백본 4
- JaD/RZKD 측: I4 포스트 1, M4 포스트 1, 백본 1
- 합계: 13 solid

기존 JaD/JfD 쉘과 RWID/RZKD STL은 위치·외형 참고용 mesh source로만
연결한다. STL triangulation을 editable B-rep으로 오인하지 않으며, manifest에
각 원본의 SHA-256을 기록한다. 쉘/리테이너를 수정할 다음 단계에서는 현재
Onshape version에서 STEP 또는 Parasolid를 직접 내보내 B-rep source로 추가해야
한다.

## 이어서 작업할 위치

- 확정 좌표/치수: `build123d_workbench/source_of_truth.py`
- 캐리어 형상 함수: `build123d_workbench/model.py`
- 출력/manifest: `build123d_workbench/export_baseline.py`
- 회귀 검사: `build123d_workbench/smoke_test.py`

확정 기준을 보존하려면 `source_of_truth.py`를 직접 덮어쓰지 않고, 신규 설계
모듈에서 해당 값을 import한 뒤 파생 파라미터로 실험한다.
