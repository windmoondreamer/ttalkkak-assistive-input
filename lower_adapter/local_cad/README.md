# local_cad — 로컬 build123d 인체공학 외피 작업공간

하부 **인체공학 외피(ergonomic outer shell)** 개발을 Onshape API 의존에서 떼어내
로컬 파라메트릭 CAD 로 옮긴 작업공간이다.

```
검증된 Onshape 기계 형상
        ↓  STEP 으로 동결 (수동 export)
로컬 build123d / OpenCascade
        ↓
인체공학 하우징 개발
        ↓
STEP + STL + BREP 출력
```

```
ONSHAPE_API       = FORBIDDEN
LOCAL_CAD_ENGINE  = build123d
CUSTOM_GIMBAL     = FORBIDDEN
APPROXIMATE_CORE_REBUILD = FORBIDDEN
```

이 폴더 안에서는 **Onshape API 를 호출하지 않는다.** Onshape 는 STEP 을 수동으로
내보내기 위한 원본 저장소일 뿐이다.
상체(손가락 버튼) 워크플로는 이관 대상이 아니며 기존 위치에 그대로 둔다.

---

## 현재 상태

**Phase 0 완료 · 동결 레퍼런스 STEP 대기 중.**

| | |
|---|---|
| build123d | **0.11.1** (venv python 3.12.13, OCP `cadquery-ocp-novtk` 7.9.3.1.1) |
| 스모크 테스트 | **PASS 7/7** — primitive / boolean / fillet / loft / export / roundtrip / STL |
| STEP 왕복 | **PASS** — bbox 오차 1.42e-14 mm, 부피 상대오차 3.92e-14 |
| 저장소 STEP/BREP | **0개** → 형상 작업 미착수 |

**저장소에 STEP / BREP / FCStd 가 하나도 없다.**
지시 §8 / STOP 조건에 따라 근사 치수나 tessellation 캐시로 기계 코어를 재구성하지
않고 멈춰 있다.

필요한 파일과 정확한 내보내기 방법:
**[`reference/STEP_EXPORT_REQUEST.md`](reference/STEP_EXPORT_REQUEST.md)** (CAD 엔진과
무관한 내용이라 CadQuery→build123d 전환과 상관없이 그대로 유효하다)

```
필수   STOCK_GIMBAL_REFERENCE.step
       CONFORMAL_CORE_REFERENCE.step        <- 가장 중요
       ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step
선택   ONEGRIP_REFERENCE.step
       ELECTRONICS_REFERENCE.step
```

넣을 위치: `lower_adapter/local_cad/reference/`

---

## 폴더

```
lower_adapter/local_cad/
├── README.md                  이 문서
├── reference/                 동결 레퍼런스 STEP (읽기 전용)
│   └── STEP_EXPORT_REQUEST.md 필요한 내보내기 목록
├── build123d/
│   ├── parameters.py          W2 파라미터 + 동결 상수 + 허용 오차
│   ├── geometry_utils.py      STEP 임포트/출력, bbox/부피, 왕복 비교, STL 검사
│   ├── import_reference.py    레퍼런스 검사 + 무변경 왕복 (§9)
│   ├── ergo_shell.py          인체공학 외피 생성 (편집 대상)
│   ├── assembly_preview.py    조립 프리뷰 STEP (부품 분리 유지)
│   ├── verify_geometry.py     로컬 검증 (Onshape 미조회)
│   └── smoke_test.py          엔진 스모크 테스트
├── export/
│   ├── step/                  설계 마스터
│   ├── stl/                   슬라이싱용
│   └── brep/
├── preview/
└── reports/                   smoke_test.json / reference_inspect.json 등
```

`ergo_shell.py` · `assembly_preview.py` · `verify_geometry.py` 는 레퍼런스가 없으면
**형상을 만들지 않고 필요한 파일을 알려주고 종료**한다.

---

## Python 환경

전역 Python 을 건드리지 않고 **격리 venv** 를 쓴다.

```
시스템 Python   3.12.6   C:\Users\User\AppData\Local\Programs\Python\Python312
격리 환경       .venv-build123d/         (저장소 루트, 약 592 MB)
  python        3.12.13
  build123d     0.11.1
  cadquery-ocp-novtk 7.9.3.1.1
  ocpsvg        0.6.0
  numpy 2.5.2 / scipy 1.18.0
FreeCAD CLI     미설치 (선택. 시각 확인 용도로만 쓸 수 있다)
```

만들 때 쓴 명령:

```bash
python -m venv .venv-build123d
.venv-build123d/Scripts/python -m pip install --upgrade pip
.venv-build123d/Scripts/python -m pip install build123d
```

이후 **모든** 로컬 CAD 명령은 이 인터프리터로 실행한다:

```bash
.venv-build123d/Scripts/python lower_adapter/local_cad/build123d/<script>.py
```

> `.venv-cadquery/` 는 엔진 전환 전에 만들다 만 것이다. **사용하지 않는다.**
> 지우는 데 시간을 쓰지 않았을 뿐이다.

> Windows 설치 주의: pip 를 동시에 두 번 돌리면 `WinError 32/5` 로 깨진다
> (`ipython.exe`, `scipy/_fblas.pyd` 등이 잠긴다). 한 번만 순차 실행할 것.

---

## 동결 대상 (편집 금지)

```
CUSTOM_GIMBAL = NOT ALLOWED
STOCK_GIMBAL  = REQUIRED
```

- 스톡 짐벌 내부 일체 (베어링 / Pitch / Roll / Spring_holder / 스프링 / 샤프트 /
  홀 / 마그넷 / 스톡 Base / OneGrip↔Pitch 인터페이스)
- 검증된 내부 공동 (conformal cavity), 캐리어 개구, 마운팅/인서트 형상
- `BOTTOM_CARRIER` 및 카트리지 마운팅
- 20° 인체공학 기준면, 그립 중립축 직교 관계, `HAND_REF` 위치

편집 대상은 **인체공학 외피 하나뿐**이다.

### 유지해야 할 검증값

```
경사 인체공학 기준면            20.000 deg
그립 중립축 ⟂ 기준면            90.000 deg
HAND_REF 변화                   0 mm
하우징 아래 스톡 돌출             0 mm
짐벌 모션                       ±10 deg (중립 / ±10 X / ±10 Y / 코너 4)
```

참고 (Onshape W2 결과 — 재구성 목표가 아니라 대조용):

```
외형        128.6 x 219.7 x 139.9 mm
손목 지지    7,173 mm2 @ 7.0 deg
```

### 좌표계 정책 (§7)

Part Studio STEP 각각의 로컬 좌표계를 **임의로 맞추지 않는다.**
`ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step` 을 world transform 기준으로 삼고,
개별 STEP 의 위치는 어셈블리와 비교해 **실제 rigid transform 을 계산**한다.
근사 좌표를 직접 입력하지 않는다.

> 어셈블리는 **편향 상태**로 저장돼 있다 (Pitch 5.6062°, Roll 0.452°).
> 중립 복원 행렬은 `lower_adapter/cad_dump/stock_frames.json` 에 있다.

---

## W2 인체공학 파라미터 (`build123d/parameters.py`)

```python
WRIST_PAD_ANGLE  = 7.0    # 평가 범위 5 / 7 / 9
WRIST_PAD_LENGTH = 85.0   # 평가 범위 70 / 85 / 100
WRIST_PAD_WIDTH  = 86.0
WRIST_PAD_RADIUS = 16.0
WRIST_ANCHOR_Y   = -20.0
EDGE_FILLET      = 3.0    # 실패 시 2.5 -> 2.0 (해당 group 만)
FRONT_RAKE       = 5.0
SHELL_WALL       = 5.0    # 일반 외피
WRIST_WALL       = 6.0    # 손목 접촉면
NECK_WALL        = 4.5    # 손목 넥 최소
```

이 값을 바꿔도 **내부 코어는 재구성되지 않는다.**

---

## 명령

```bash
# 엔진 스모크 테스트 (레퍼런스 없어도 실행 가능)
.venv-build123d/Scripts/python lower_adapter/local_cad/build123d/smoke_test.py

# 레퍼런스 검사 + 무변경 왕복
.venv-build123d/Scripts/python lower_adapter/local_cad/build123d/import_reference.py

# 외피 생성 / 프리뷰 / 검증  (레퍼런스 필요)
.venv-build123d/Scripts/python lower_adapter/local_cad/build123d/ergo_shell.py
.venv-build123d/Scripts/python lower_adapter/local_cad/build123d/assembly_preview.py
.venv-build123d/Scripts/python lower_adapter/local_cad/build123d/verify_geometry.py
```

Onshape 접속 없이 STEP/STL/BREP 가 처음부터 다시 만들어져야 한다.

## 출력

```
export/step/ERGO_HOUSING_W2.step        설계 마스터
export/step/ONEGRIP_LOCAL_PREVIEW.step  조립 프리뷰 (fuse 하지 않고 부품 분리 유지)
export/stl/ERGO_HOUSING_W2.stl          슬라이싱용
export/brep/ERGO_HOUSING_W2.brep
```

단위는 전부 **mm**. STEP 이 설계 마스터이고 STL 은 파생물이다.

## 검증 허용 오차

```
20.000 / 90.000 판정       1e-4 deg
좌표 일치                  1e-3 mm
STEP 왕복 bbox             1e-6 mm
STEP 왕복 부피 상대오차      1e-6
```

## 알려진 제약

- **캐시는 정밀 CAD source 로 사용 금지.**
  `stock_full.npz` / `conformal_meshes.npz` / `ergo_meshes.npz` 는
  chordTolerance 0.0002~0.0003 의 근사 삼각형망이다.
  시각 대조 · 충돌 교차검사 · 회귀 비교에만 쓴다.
- OCC 필렛은 얇은 벽 근처에서 실패한다. 전역 반경을 밀어붙이지 말고 실패한
  edge group 만 반경을 낮추고 기록한다 (§16). 성공한 다른 필렛은 유지한다.
- 임포트한 STEP 이 중립 정지 상태 solid 뿐이라 관절 운동을 복원할 수 없으면,
  기존 검증된 모션 포락선(`lower_adapter/cad_dump/motion_configs.npz`)으로 검증한다.
  리포트에서 **DIRECT BREP COLLISION CHECK** 와 **CACHED MOTION ENVELOPE CHECK** 를
  반드시 구분해 적는다. 둘을 같은 수준의 검증으로 표현하지 않는다.
- build123d `Joint`(Rigid/Revolute/Ball)는 **스톡 운동 관계를 그대로 표현할 수 있을
  때만** 쓴다. 기능이 있다는 이유로 짐벌 운동학을 새로 설계하지 않는다.
