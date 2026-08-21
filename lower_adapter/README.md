# lower_adapter — 하부 경사 어댑터 서브시스템

OneGrip 상체(그립)를 **무수정 탈착 모듈**로 두고, 그 아래에 경사 마운트와 미래 X/Y 짐벌
인터페이스를 새로 만드는 작업 전용 폴더다.

상체(검지/중지 버튼·holder·retainer) 워크플로와 **완전히 분리**되어 있다.
루트의 `docs/` · `cad/` · `scripts/` 는 상체 전용이고, 이 폴더가 하부 전용이다.

> 분리 이유: 두 워크플로가 병렬로 돌아가면서 루트 `docs/` 번호가 충돌했다
> (`docs/31` 이 상체 스위치 감사와 하부 분석 양쪽에서 동시에 쓰였다).
> 하부 문서는 이 폴더 안에서 `00_` 부터 독립 번호를 쓴다.

---

## 폴더

```
lower_adapter/
├── README.md
├── docs/
│   └── 00_architecture_analysis.md   # 아키텍처 사전 분석 (READ ONLY, CAD WRITE 0건)
├── cad/
│   ├── OneGrip_LowerAdapter.fs       # 어댑터 FeatureScript (stage A~H)
│   └── _profiles.fs.inc              # 생성된 플랜지 윤곽 72점
├── scripts/
│   ├── analyze_lower_interface.py    # 00 문서의 모든 수치를 재생성
│   ├── gen_adapter_constants.py      # FS 상수 생성 + 사전 검증
│   ├── run_adapter.py                # 단계별 실행기 (상체 eid 차단 가드 포함)
│   ├── verify_adapter.py             # 최종 검증 (20도 / 물림 / 간섭 / 스택)
│   ├── shots.py                      # 렌더 + 측면 합성도
│   └── fs_probe.py                   # FeatureScript 오류 진단 보조
└── cad_dump/                         # 이 서브시스템 전용 파생 데이터
    ├── bot_first.npy / bot_n.npy     # 바닥면 +Z 레이캐스트 맵 (1.0 mm)
    ├── socket_first.npy / _last.npy  # 소켓 영역 정밀 맵 (0.25 mm)
    ├── flange_outline.npy            # 플랜지 윤곽 폐곡선 (360 pt)
    ├── outer_prof.npy                # Z별 외피 반경 프로파일
    ├── asm_transforms.json/.npy      # Complete assembly occurrence transform
    ├── adapter_constants.json        # FS 상수 + 사전 검증 결과
    ├── mesh_CRADLE/WEDGE/RING_*.json  # 생성된 어댑터 tessellation
    ├── mesh_LIVE_JaD/JfD.json         # ITS-1105 이후 상체 (하단 무변화 확인용)
    ├── shot_iso/top/composite_side.png
    └── verify_out.txt                 # 최종 검증 전문
```

**메시 원본(`mesh_*.json`)은 루트 `cad_dump/` 에 그대로 둔다.** 두 워크플로가 공유하며
이 폴더의 스크립트는 읽기만 한다.

## 재현

```bash
python lower_adapter/scripts/analyze_lower_interface.py
```

`--fetch-asm` 을 붙이면 Onshape assembly transform 을 다시 GET 한다 (그 외에는 캐시 사용).
GET 전용이며 POST/PUT/DELETE 를 하지 않는다.

---

## 확정된 것

| 항목 | 값 | 근거 |
|---|---|---|
| ONEGRIP_CENTER_AXIS | (0.000000, 27.269160) 을 지나는 grip +Z | 보어 41단면, +Z 편차 0.000000° |
| MOUNT_ORIGIN | (0.000000, 27.269160, −67.878507) | 중심축 × 플랜지면 |
| 착좌면 | 평면 1개, 5017.5 mm², 77.43 × 72.44 mm | 3901점 적합, residual 6.4e-05 mm |
| 착좌면 ⟂ 중심축 | **0.000000°** (이미 성립) | 평면적합 vs 보어축 |
| 소켓 보어 | 21.072 × 25.672 × 직진 21.000 mm | 실측 |
| 상대 post | 20.272 × 25.272, 여유 X 0.40 / Y 0.20 mm/side | assembly transform |
| 보스 | 31.0 × 35.5, 아래로 6.000 mm | 실측 |
| `#grip_tilt` | **20°** (15/25/30 파라미터화) | 사용자 지정 |
| `#tilt_direction` | **TOP → −Y**, `RotX(+θ)`, n = (0, −0.342020, 0.939693) | 사용자 확정 ("엄지는 위쪽") |
| `#hand_sign` | +1 (RIGHT HAND) | 사용자 확정. 경사와 독립 |

## 구조 방침

```
[ OneGrip 상체 ]  <- 무수정
      |   평면 착좌 + 보스 포켓 + post 복제 + 클램프 링
[ A. Grip Cradle ]   각도 무관, 정밀 피처 전부
      |   4xM3 평면 조인트
[ B. Tilt Wedge ]    15/20/25/30 deg, 각도 의존은 여기뿐
      |   수평 인터페이스 (동결 스펙)
[ 미래 X/Y 짐벌 ]
```

## 현재 상태

- **매립형 짐벌 1차 CAD 완료** → `docs/03_embedded_gimbal_v1.md`
  - 버전 `EMBEDDED_GIMBAL_V1` = `239edc28544c9978899ed7a1`
  - Part Studio `OneGrip_EmbeddedGimbal` = `2e024442c796323fd37e49c3` (body 5)
  - `#pivot_depth` **18.5 mm** / `#gimbal_travel` **10 deg** (변수로 조정 가능)
  - 간섭 0, 20.000000°, 경사외피→HAND_REF **55.879 mm**, 베이스→HAND_REF **85.153 mm**
- 아키텍처 비교/패키징 한계 → `docs/02_embedded_gimbal_architecture.md`
- (구) 적층형 어댑터 → `docs/01_adapter_v1_implementation.md`
- 체크포인트 `PRE_ADAPTER` = `40aeafabde5ccb638fa0aec3`
- 결과 버전 `LOWER_ADAPTER_V1` = `41712f1bb7b025dbdb8b67b4`
- 신규 Part Studio `OneGrip_LowerAdapter` = `bbfebe9c42748fb6d5b912e8` (피처 8 / solid 4)
- **상체 Joystick Part Studio 쓰기 0건** — 신규 스튜디오에 derive 가 없어 구조적으로 불가
- 검증 전 항목 PASS: 20.000000° / 물림 20.000mm / 간섭 0 / 최소 살 3.250mm / 스택 33.900mm
- **다음 단계(짐벌)는 별도 승인 필요**

## 이월된 미결

- 정적 편심: 확정 방향에서 CG 편차 −45.596 mm (원본 수직 −26.817 의 1.70배).
  전도 모멘트 약 4020 → 6840 g·mm (1.70배). 기하로는 상쇄 불가.
  **이번 어댑터 단계에서는 보상하지 않는다** (사용자 지시). 어댑터 물리 확정 →
  최종 가동질량 확정 → 실제 스프링 선정·실측 → 짐벌 피벗 확정 이후에 결정한다.
  **Hall 오프셋은 보상 수단이 아니다** — 전기적 중심만 옮길 뿐 중력 토크를 상쇄하지 못한다
- `#gimbal_bolt_pattern` 동결 시점
- FDM 프린터·재료 (`#fdm_clearance`)
- post 밑동 2.008 × 2.5 mm 관통 슬롯의 기능 (복제 여부)
