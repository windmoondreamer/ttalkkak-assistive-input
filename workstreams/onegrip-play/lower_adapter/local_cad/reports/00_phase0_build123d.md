# Phase 0 — build123d 로컬 CAD 엔진 확정

- 일자: 2026-08-21
- **Onshape API 호출 0건**
- 결과: **엔진 확정. 동결 레퍼런스 STEP 대기 중.**

## 1. 엔진 전환

```
CadQuery  ->  build123d
```

`.venv-cadquery` 는 다운로드 도중 중단했고 **사용하지 않는다** (삭제에 시간을 쓰지 않았다).
`reference/STEP_EXPORT_REQUEST.md` 는 CAD 엔진과 무관하므로 그대로 보존했다.

## 2. 환경

| | |
|---|---|
| 격리 환경 | `.venv-build123d/` (저장소 루트, 592 MB) |
| python | 3.12.13 (venv) / 시스템 3.12.6 |
| **build123d** | **0.11.1** |
| OCP | `cadquery-ocp-novtk` 7.9.3.1.1 |
| 부속 | ocpsvg 0.6.0, numpy 2.5.2, scipy 1.18.0, ezdxf, lib3mf |

전역 Python 미수정.

### 설치 중 겪은 것

pip 를 백그라운드로 **두 번 동시에** 돌려 파일 잠금 충돌이 났다.

```
WinError 32  ...\mpmath\libmp\libmpc.py
WinError 5   ...\scipy\linalg\_fblas.cp312-win_amd64.pyd
WinError 32  ...\Scripts\ipython.exe -> ipython.exe.deleteme
```

venv 를 지우고 **순차로 한 번만** 실행해 해결했다.
Windows + Desktop 경로에서는 pip 동시 실행 금지.

## 3. 스모크 테스트 — PASS 7 / 7

```
[PASS] A. primitive  Box 10 x 20 x 30        vol 6000.0 mm3, bbox [10, 20, 30]
[PASS] B. boolean    Box - Cylinder 관통홀     vol 5151.77 (해석 5151.77)
[PASS] C. fillet     수직 모서리 4개 R1.5        모서리 4개, vol 5093.83
[PASS] D. loft       R40x30 -> R20x24 h25     vol 19956.34, bbox [40, 30, 25]
[PASS] E. export     STEP / STL / BREP        step 36KB stl 27KB brep 63KB
[PASS] F. roundtrip  STEP 재임포트             solid 1->1
                                             bbox delta 1.421e-14 mm
                                             vol  rel delta 3.919e-14
[PASS] G. STL        watertight / manifold    556 tri, non-manifold edge 0
```

- **B** 는 해석해(6000 − π·3²·30 = 5151.77)와 일치시켜 boolean 정확도를 확인했다.
- **C** 는 index 가 아니라 **의미 기반 선택**(`filter_by(Axis.Z)` + 중심 좌표 조건)으로
  수직 외곽 모서리 4개만 골랐다 (§10).
- **F** 왕복 오차가 1e-14 수준이라 STEP 을 설계 마스터로 쓰는 데 문제없다.

원본: `reports/smoke_test.json`

## 4. 생성한 코드

| 파일 | 역할 |
|---|---|
| `parameters.py` | W2 파라미터 · FROZEN 기계 상수(참조용) · 허용 오차 · 레퍼런스 경로 |
| `geometry_utils.py` | STEP 임포트/출력, solid/bbox/부피 기술, 왕복 비교, STL manifold 검사 |
| `import_reference.py` | §9 파이프라인 — 존재 확인 → 임포트 → solid/bbox/부피/center → 무변경 왕복 |
| `ergo_shell.py` | 외피 생성 (레퍼런스 없으면 STOP) |
| `assembly_preview.py` | 조립 프리뷰 (레퍼런스 없으면 STOP) |
| `verify_geometry.py` | 로컬 검증 (레퍼런스 없으면 STOP) |
| `smoke_test.py` | 엔진 스모크 |

세 STOP 스크립트는 실제로 실행해 **형상을 만들지 않고 필요한 파일만 안내**하는 것을
확인했다.

## 5. 아직 하지 않은 것 (§8 금지 항목)

```
OneGrip core 재건        미실시
Stock Gimbal 재건        미실시
Conformal cavity 재건    미실시
Carrier 재건            미실시
W2 외피 생성             미실시
```

tessellation 캐시(`stock_full.npz`, `conformal_meshes.npz`, `ergo_meshes.npz`)는
정밀 CAD source 로 **사용하지 않았다.**

## 6. 다음 단계 (레퍼런스 도착 후)

```
1. import_reference.py  — 3개 STEP 검사 + 무변경 왕복
2. 어셈블리 STEP 기준으로 개별 STEP 의 rigid transform 계산 (§7)
3. 20.000 / 90.000 / HAND_REF 스케일·좌표 검증
4. 코어를 감싸는 multi-section loft 외피 (§12, §13)
5. 7도 손목 지지면 통합 + 중공화 (§15)
6. edge group 별 fillet R3 (실패 시 그 group 만 낮춤, §16)
7. 모션 검증 — DIRECT BREP 와 CACHED ENVELOPE 를 구분해 보고 (§17)
8. STEP / STL / BREP + 프리뷰 출력 (§19), 리포트 (§20)
```
