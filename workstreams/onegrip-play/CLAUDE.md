# OneGrip Play

한손 FPS 컨트롤러 프로젝트. 기존 **DIY Joystick Onshape CAD**를 베이스로 파생 설계한다.
이 저장소는 설계 자료 / Onshape 연동 코드 / CAD 수정 스크립트 / 문서를 관리한다.

---

## 1. 제품 정의

한 손으로 FPS 게임의 이동과 시점 조작을 모두 처리하는 그립형 컨트롤러.
게임패드의 좌/우 스틱 역할을 한 손 안에서 분리된 두 축계로 구현한다.

| 입력 | 물리 구조 | 매핑 | 담당 |
|------|-----------|------|------|
| Left Stick | 하단 2축 짐벌 (Roll / Pitch) | 캐릭터 이동 (WASD / 좌스틱) | 손목·팔 전체 기울임 |
| Right Stick | 엄지 조이스틱 | 시점 조작 (Look / 우스틱) | 엄지 |
| 버튼 4개 | 검지 쉘 | 미정 (사격/조준 등) | 검지 |
| 버튼 4개 | 중지 쉘 | 미정 (재장전/점프 등) | 중지 |

---

## 2. 기구 구조

### 2.1 하단 짐벌 (Left Stick) — 초기에는 원본 유지

기존 DIY Joystick CAD의 다음 요소는 **초기 단계에서 최대한 변경하지 않는다**:

- `Base` (베이스 하우징)
- `Roll` 축 어셈블리
- `Pitch` 축 어셈블리
- bearing (베어링) 배치 및 시트
- Hall sensor (홀 센서) 마운트
- magnet (마그넷) 포켓 및 위치
- spring (센터링 스프링) 구조

> 변경이 불가피할 경우, 변경 전에 반드시 사용자에게 이유·영향 범위를 보고하고 승인을 받는다.
> 특히 magnet ↔ Hall sensor 상대 위치는 센싱 선형성에 직결되므로 임의 변경 금지.

### 2.2 그립 쉘 / 버튼 배치

원본 DIY Joystick의 grip은 **좌측 shell 1개 + 우측 shell 1개, 총 2개**로 분리된 구조다.
OneGrip Play도 이 2-shell 분할을 그대로 유지한다.

**쉘 개수는 늘리지 않는다. 버튼만 기존 2개 쉘 위에 배치한다.**

| 손가락 | LEFT shell | RIGHT shell | 손가락별 합계 |
|--------|-----------|------------|--------------|
| 검지 | 버튼 3개 | 버튼 1개 | 4개 |
| 중지 | 버튼 3개 | 버튼 1개 | 4개 |
| **쉘별 합계** | **버튼 6개** | **버튼 2개** | **총 8개** |

- shell 총 개수: **2개** (LEFT 1 + RIGHT 1)
- 버튼 총 개수: **8개**
- LEFT shell 1개가 검지 3 + 중지 3 = 6개 버튼을 담는다.
- RIGHT shell 1개가 검지 1 + 중지 1 = 2개 버튼을 담는다.

> 주의: "shell 1개 = button 1개"가 **아니다**. shell은 좌/우 2개뿐이고,
> 그 위에 버튼이 여러 개 올라간다. 이 점을 혼동하지 말 것.

여기서 "왼쪽/오른쪽"은 그립을 정면에서 봤을 때의 좌우 방향을 뜻한다.

**원본 CAD 조회 결과 (2026-08-18):** 원본 Joystick assembly에
`Joystick_1` / `Joystick_2` 쉘 2개, `PushBtn` 8개, 버튼 캡 8개가 존재한다.

> **정정 (중요):** 원본 `PushBtn` 8개는 우리가 추가하려는 검지/중지 버튼이 **아니다.**
> 원작자가 **엄지 영역**(그립 전면 상단, 엄지 조이스틱 바로 아래)에 배치한 기존 버튼이며,
> **그대로 유지한다.** 엄지 조이스틱 구조도 그대로 유지한다.
> 검지/중지 버튼 8개는 **신규로 추가**한다.
> 최종 목표 = 원본 엄지 버튼 8개 + 신규 검지/중지 버튼 8개 = **총 16개 공존**.
> 기존 PushBtn 8개를 이동·삭제하거나 신규 버튼으로 간주하지 말 것.

상세: [docs/00_original_cad_analysis.md](docs/00_original_cad_analysis.md),
[docs/01_original_button_mechanism_analysis.md](docs/01_original_button_mechanism_analysis.md)

### 2.3 엄지 조이스틱 (Right Stick)

엄지 조작용 소형 2축 조이스틱. 하단 짐벌과 독립된 축계이며,
그립 상단 엄지 자연 위치(neutral thumb position)에 배치한다.

---

## 3. 확인 필요 항목 (Open Questions)

작업 진행 전 사용자 확인이 필요한 사항. 임의로 가정하고 진행하지 않는다.

**차단 항목 (이게 없으면 다음 단계 진행 불가):**

- [ ] **Onshape API 키** (Read 권한) — 없으면 mate 관계·부품 좌표·bounding box 조회 불가
- [ ] **사본 문서** — 원본은 Adam Simon 소유라 수정 불가. Copy/Fork 후 did/wid 필요
- [ ] 원본 CAD의 라이선스 조건 (public ≠ 파생 허용)

**설계 결정 항목:**

- [x] **분할면 처리 방식** — **분할면 유지 확정.** B안(`Mirror 1` 폐기) 보류.
      row를 DOMINANT_SHELL 쪽으로 offset −11.0mm 하여 3+1 달성 (docs/03).
- [x] 검지 / 중지 행 높이 — **Z = +9.0 / Z = −6.0 확정** (3D 검증, docs/04).
      INDEX는 나사 B boss 여유 때문에 +12 → +9 로 3mm 하향
- [x] **holder 축 방향** — ~~OPTION B (local normal 정렬)~~ 철회. **자유축 minimax 확정.**
      INDEX 최종 축은 docs/15 §1-B. 최대 법선편차 17.21도, 스위치 여유 1.3476mm,
      포켓 칸막이 0.800mm. MIDDLE 도 같은 규칙 적용 (docs/13 §13-K).
- [ ] 왼손용 / 오른손용 중 어느 쪽 기준인가?
      (구조상 `#hand_sign` 변수 1개로 반전 가능 — docs/03 §9)
- [ ] 캡 밑면 접촉 패드 — F2 채택 시 캡 **외형은 변경 없음**(개구부 유지). 밑면 패드만
      축에 맞춰 기울이면 된다. 행정 0.25mm 당 측방 어긋남 0.071mm < 캡 여유 0.20mm (docs/13 §13-G)
- [x] Joystick_1/2 부피차 1.27cm³ — **규명 완료.** 96.6%가 나사 체결 구조
      (J1=클리어런스+카운터보어, J2=10mm 탭홀). 신규 버튼 영역은 완전 대칭 (docs/05)
- [ ] 엄지 조이스틱: 원본 `HW504_B` 모듈 유지 vs 교체
- [x] `HW504_B` ×2 — **중복 아님.** 모듈 본체(JFH) + 가동 스틱(JFD) 2 body. 조이스틱은 1개
- [ ] 버튼 스위치: 원본 `PushBtn`(#switch_width 10mm) 유지 vs 교체
- [ ] 컨트롤러 보드: 원본 Arduino Pro Micro 유지 vs 교체 (USB HID vs XInput)
- [ ] 3D 프린팅 기준 (FDM/SLA, 레이어 두께, 최소 벽 두께, 클리어런스)
      → **SLA 권장.** F2 에서 포켓 칸막이가 0.80mm 이며, 11mm 피치·수렴 곡면에서
        `HOLDER_WALL = 3mm` 는 어떤 축 해법으로도 불가능하다 (docs/13 §3)
- [ ] 버튼 8개의 기능 매핑 (사격/조준/재장전/점프 등)
- [ ] 원본 `#joystick_angle = 15 deg` 유지 여부 (FPS 이동 조작에 적정한가)

---

## 4. Onshape 연동 규칙

### 4.1 인증

- API 키는 **절대 코드나 문서에 하드코딩하지 않는다**. `.env`로만 관리한다.
  - `ONSHAPE_ACCESS_KEY`, `ONSHAPE_SECRET_KEY`, `ONSHAPE_BASE_URL`
- `.env`, 키 파일, 토큰은 커밋 대상에서 제외한다.
- 로그·에러 출력에 키가 노출되지 않도록 한다.

### 4.2 문서 참조

Onshape 리소스는 `did / wvm / wvmid / eid` 4요소로 식별된다.
문서 ID 등 상수는 코드에 흩뿌리지 말고 설정 파일 한 곳에 모은다.

**원본 DIY Joystick CAD (베이스 문서, 읽기 전용으로 취급):**

```
URL : https://cad.onshape.com/documents/143d2aa6a2cf1c2ed82be979/w/f0ab4fb72b468eeb38cc7a63/e/212ec93359aad06aa2bd2fad
did : 143d2aa6a2cf1c2ed82be979
wid : f0ab4fb72b468eeb38cc7a63   (workspace)
eid : 212ec93359aad06aa2bd2fad   (URL이 가리키는 element)
```

이 문서는 **직접 수정하지 않는다.** 작업은 아래 사본에서 한다.

**WRITE 대상 사본 (사용자 소유, 승인됨):**

```
name: OneGrip_Play_V1
did : a21e64f36bc61df760d4587c
wid : ef6a7b3ccc45186203e4d2ca   (Main)
eid : 425d9199b59cfb1efd9ddc35   (Joystick Part Studio)
     d151f2915f76be6046b43c07   (Feature Studio OneGrip_FingerButtons, 신규)
```

`onshape/write_client.py` 가 이 did/wid 이외의 쓰기를 예외로 차단한다.
초판 = **RIGHT HAND**, `#hand_sign = +1`,
DOMINANT_SHELL = Joystick_2 (`JfD`, X<0), OPPOSITE_SHELL = Joystick_1 (`JaD`, X>0).

### 4.3 CAD 수정 원칙

1. **읽기 우선**: 수정 전에 항상 현재 피처 트리 / 파라미터를 조회해 현재 상태를 확인한다.
2. **브랜치 우선**: 원본 워크스페이스를 직접 수정하지 않는다. 별도 브랜치/버전에서 작업한다.
3. **파라미터 우선**: 지오메트리를 새로 그리기보다 기존 스케치·피처의 변수(configuration / variable)를 조정하는 방식을 먼저 검토한다.
4. **되돌릴 수 있게**: 수정 전 버전을 생성하고, 어떤 버전에서 무엇을 바꿨는지 기록한다.
5. **한 번에 하나**: 여러 피처를 한 번에 바꾸지 않는다. 변경 → 확인 → 다음.

### 4.4 원본 구조상 반드시 지켜야 할 제약 (실제 조회로 확인됨)

- **Base → Joystick 단방향 종속**: Joystick Part Studio가 `superDerive`로 Base의 형상과
  변수를 가져온다. Base를 바꾸면 grip 결합부가 자동으로 따라 변한다.
  grip 결합부만 따로 손대면 derive 결과와 충돌한다.
- **변수 우선**: Base 39개, Joystick 16개의 마스터 변수가 트리 최상단에 있다.
  치수 변경은 스케치가 아니라 이 변수를 통해서 한다.
- **`#joystick_angle` 파급**: `#offset_around_pitch = 0.2mm * (#joystick_angle/deg) + 1mm`.
  각도를 바꾸면 클리어런스가 연동되어 변한다.
- **`Mirror 1` / `Mirror 2`**: 좌/우 쉘과 버튼 캡 `_1`/`_2` 그룹이 여기서 갈린다.
  좌우 비대칭 설계(LEFT 3 + RIGHT 1)를 하려면 이 미러 구조를 먼저 검토해야 한다.
- **grip은 로프트 곡면**: 단면 4개(`Joystick_part_1~4`)를 로프트한 형상이다.
- **기존 버튼 8개는 단일 스케치 묶음**: `Buttons` 스케치 1개 + `Extrude 2` 1회로 전부 뚫린다.
  버튼별 독립 피처가 없고 feature-level Pattern도 없다.
  이 스케치를 편집하면 기존 엄지 버튼 8개가 전부 영향을 받는다 → **편집 금지**.
- **분할면 = 미러면 = 버튼 스케치 x=0**: `Mirror 1`의 미러 평면 `'JEC'`가
  `Joystick_side_profile` · `Screw_holes` 평면과 같고, `Buttons` 스케치의 대칭선이 그 위에 있다.
  따라서 원본 버튼은 좌 3 / 우 3 / 분할면 걸침 2 구조다.
  **목표인 LEFT 3 + RIGHT 1 비대칭은 이 미러 구조로 만들 수 없다.**
  신규 버튼은 `Mirror 1` 이후 트리 최하단에 좌/우 스케치를 분리해 append 한다.

### 4.5 신규 버튼 추가 시 상속할 검증된 치수

| 항목 | 값 | 변수 |
|---|---|---|
| 버튼 개구부 | 8 × 8 mm | `#button_width` |
| 버튼 간격 | 3 mm | `#button_gap` |
| 스위치 포켓 | 6.4 × 6.4 mm (= 6 + 2×0.2) | `#button_module_width`, `#button_tolerance` |
| 캡 클리어런스 | 사방 0.2 mm | `#button_tolerance` |
| 캡 높이 | 4 mm | `#button_cover_height` |
| 지지 리브 두께 | 4 mm | `#button_support_thickness` |
| 쉘 벽 두께 | 3 mm | `Shell 1` |

벽 두께 3mm < 포켓 6.4mm 이므로, 신규 버튼도 **별도 backplate/리브 구조가 반드시 필요하다.**

---

## 5. 작업 규칙 (Claude 대상)

- **사용자의 명시적 지시 없이 CAD를 수정하지 않는다.** 조회·분석은 가능.
- 파괴적 동작(피처 삭제, 워크스페이스 덮어쓰기, 버전 삭제)은 실행 전 반드시 확인받는다.
- 설계 결정은 추측하지 말고 위 "확인 필요 항목"에 추가한 뒤 질문한다.
- 치수·각도·재료는 근거 없이 지어내지 않는다. 출처가 원본 CAD면 실제로 조회해서 확인한다.
- 응답 언어: 한국어.

---

## 6. 폴더 구조

```
OneGrip-Play/
├── CLAUDE.md                 # 이 문서
├── .env.example              # Onshape 키 템플릿 (.env는 커밋 금지)
├── docs/
│   ├── 00_original_cad_analysis.md            # 원본 CAD 구조 분석 (실측)
│   ├── 01_original_button_mechanism_analysis.md  # 원본 버튼 메커니즘 분석
│   ├── 02_button_row_layout_feasibility.md    # 검지/중지 1열 배치 실현성 검증
│   ├── 03_offset_3plus1_finger_rows.md        # 오프셋 3+1 row 배치
│   ├── 04_authenticated_internal_clearance.md # 3D 내부 공간 최종 검증 (확정안)
│   ├── 05_final_prewrite_validation.md        # 수정 직전 최종 검증 (GO 판정)
│   ├── 06_index_button_cad_implementation.md  # INDEX 버튼 CAD 구현 기록
│   ├── 07_index_holder_wall_diagnosis.md      # holder wall 정밀 진단
│   ├── 08_index_shared_holder_implementation.md  # shared trough 시도 (중단)
│   ├── 09_index_local_holder_preunion.md      # pre-union 재설계 + 6x6x6 전제
│   ├── 10_i1_holder_atomic_debug.md           # I1 원자 디버그 (A~E PASS)
│   ├── 11_index_all_holders_atomic.md         # INDEX 4개 holder 완성
│   ├── 12_switch_collision_stop_condition.md  # 스위치 상호 간섭 STOP
│   ├── 13_index_axis_collision_optimization.md # 축 최적화 해법 (F2)
│   ├── 14_index_f2_rebuild.md                  # F2 재생성 + 실물 검증 (HOLD 3건)
│   ├── 15_index_f2_final_clearance_fix.md      # 최종 여유 수정 적용 (INDEX holder 완료)
│   ├── 16_index_rear_retainer.md               # 후면 retainer 설계 확정
│   ├── 17_index_retainer_implementation.md     # retainer 1차 구현
│   ├── 18_index_retainer_insertion_relief.md   # 국소 relief 시도 (구 정의에서 HOLD)
│   ├── 19_index_retainer_service_disengagement.md # 새 정의 재검증
│   ├── 20_index_retainer_final.md               # 국소 relief 적용 완료
│   ├── 21_index_retainer_relief_precision.md    # relief 정밀화 검토
│   ├── 22_index_retainer_relief_2p07.md         # sweep 2.07 적용
│   ├── 23_index_retainer_fastening.md           # ★ EAR/boss/나사 구현 (fastening PASS)
│   ├── 24_index_i4_retainer.md                   # I4 별도 retainer + INDEX FINAL PASS
│   ├── 25_index_final_body_inventory_audit.md    # FINAL body inventory 감사 (solid 17->18 규명)
│   └── 26_index_final_geometry_identity_audit.md # ★ FINAL identity 재감사 (CONFIRMED, MIDDLE GO)
├── cad/
│   ├── OneGrip_FingerButtons.fs  # 구 커스텀 피처 (INDEX_openings/caps 용)
│   ├── OneGrip_I1_Debug.fs       # INDEX holder 파이프라인 (F2 확정)
│   ├── OneGrip_Retainer.fs       # 후면 shared retainer (negative-mold, 동결)
│   └── OneGrip_I4_Retainer.fs    # I4 전용 분리형 retainer
├── onshape/
│   ├── client.py             # 읽기 전용 Onshape 클라이언트 + element id 상수
│   └── write_client.py       # WRITE 가드 (승인 사본 1개로만 쓰기 제한)
├── scripts/
│   ├── dump_structure.py     # 원본 구조를 cad_dump/로 덤프
│   ├── inspect_feature.py    # 피처/스케치 상세 조회 (로컬 덤프만 읽음)
│   ├── section_arc.py        # 그립 단면 호길이/접선각 계산
│   ├── row_layout.py         # 오프셋 3+1 row 배치 계산 (2D 근사)
│   ├── check_auth.py         # 인증 상태 + 엔드포인트 접근 확인
│   ├── fetch_mesh.py         # tessellatedfaces -> 로컬 메시 캐시
│   ├── mesh_probe.py         # 레이캐스팅 / 단면 / 법선 유틸
│   ├── clearance_check.py    # 신규 버튼 3D 내부 공간 검증
│   ├── shell_diff.py         # 두 쉘 형상 차이 국소화
│   ├── run_holder.py         # holder FeatureScript 원자 실행/검증기
│   ├── run_retainer.py       # shared retainer 원자 실행/검증기
│   ├── run_i4_retainer.py    # I4 전용 FeatureScript 원자 실행/검증기
│   ├── deploy_fs.py          # Feature Studio 소스 업로드
│   ├── audit_index_body_inventory.py   # version 간 body inventory / identity 감사
│   ├── fetch_index_final_meshes.py     # FINAL 메시 캐시
│   ├── analyze_middle_prewrite.py      # MIDDLE 착수 전 사전 분석 (읽기 전용)
│   └── probe_middle_index_conflict.py  # MIDDLE-INDEX 간섭 사전 탐색 (읽기 전용)
├── cad_dump/                 # Onshape API 원시 응답 (피처 트리 / BOM / element / 메시)
└── lower_adapter/            # ★ 하부 경사 어댑터 서브시스템 (상체와 분리)
    ├── README.md             # 확정값 / 구조 방침 / 현재 상태
    ├── docs/
    │   └── 00_architecture_analysis.md  # 아키텍처 사전 분석 (CAD WRITE 0건)
    ├── cad/                  # FeatureScript (미생성)
    ├── scripts/
    │   └── analyze_lower_interface.py   # docs/00 의 모든 수치 재생성
    └── cad_dump/             # 하부 전용 파생 데이터 (.npy / transform)
```

**루트 `docs/` · `cad/` · `scripts/` 는 상체(검지/중지 버튼) 전용, `lower_adapter/` 는 하부 전용이다.**
두 워크플로가 병렬로 돌면서 루트 `docs/31` 번호가 충돌했기 때문에 분리했다.
하부 문서는 `lower_adapter/docs/` 안에서 `00_` 부터 독립 번호를 쓴다.
메시 캐시(`cad_dump/mesh_*.json`)는 공용이므로 루트에 그대로 두고 하부는 읽기만 한다.

`onshape/client.py`는 **GET만 수행한다.** 쓰기 메서드를 추가하려면 사용자 승인이 먼저다.

---

## 7. 현재 상태

- 2026-08-18: 프로젝트 초기화. CLAUDE.md 작성. CAD 미수정.
- 2026-08-18: shell 구조 정정 (shell은 좌/우 2개뿐, 버튼 8개가 그 위에 배치).
- 2026-08-18: 원본 Onshape 문서 읽기 전용 조회 완료.
  element 33개, Base 피처 117개, Joystick 피처 89개, BOM 3종 확보 → `cad_dump/`.
  마스터 변수 55개 실측. 분석 결과는 `docs/00_original_cad_analysis.md`.
  **CAD 수정 없음.** API 키 부재로 mate 관계·부품 좌표는 미확보 (401).
- 2026-08-18: 원본 버튼 메커니즘 READ ONLY 분석 완료 → `docs/01_...md`.
  버튼 8개 = 엄지 클러스터(단일 스케치+단일 압출), 분할면 걸침 2개 확인.
  신규 검지/중지 버튼은 트리 최하단 append 방식(Option B) 추천. **CAD 수정 없음.**
- 2026-08-18: 검지/중지 병렬 1열 배치 실현성 검증 → `docs/02_...md`.
  로프트 단면이 x=0→x=0 (절반만 생성) 확인. 단면 호길이/접선각 실측.
  **1열 2줄 구조는 실현 가능. fan 배열 불필요.**
  단 LEFT 3 + RIGHT 1은 정중앙 분할면과 충돌 → 분할면 처리 방식 결정 대기.
  **CAD 수정 없음.**
- 2026-08-18: 인체공학 전제 수정(row center != grip center) 후 재분석 → `docs/03_...md`.
  **분할면 유지한 채 3+1 달성 가능** — row를 offset −11.0mm, I3/I4 gap이 분할면 위.
  분할면 걸치는 신규 버튼 0개. LAYOUT A(원본 8/3mm) 권장. **CAD 수정 없음.**
- 2026-08-18: Onshape Read API 인증 설정 완료. 이전 401 항목 10개 전부 200.
- 2026-08-18: 실제 3D 메시(tessellatedfaces) 기반 내부 공간 최종 검증 → `docs/04_...md`.
  **판정: PASS WITH MINOR ADJUSTMENT.** INDEX 행 Z +12 → +9 (3mm 하향)만 수정하면
  8개 버튼 전부 SWITCH_POCKET_FIT = YES. 벽두께 실측 2.98~3.01mm.
  Pitch/엄지구조 간섭 없음(19mm+ 이격). 원본 8버튼 = 엄지 패널 **확정**
  (스위치 축 8개 전부 동일, 수직에서 49.2°). **CAD 수정 없음.**
- 2026-08-19: 수정 직전 최종 검증 완료 → `docs/05_...md`. **판정 GO.**
  UNKNOWN 2건 해소: 쉘 부피차 = 나사 체결 구조(의도된 설계),
  HW504_B ×2 = 2 body(중복 아님). 신규 버튼 영역 좌우 대칭 확인(최대차 0.10mm).
  기술적 차단 요소 없음. 남은 것은 사본 문서 / 라이선스 / 손 방향 결정.
  **CAD 수정 없음.**
  원본 Onshape 문서 URL 확보. 구조 분석 대기 중 — API 인증 미설정.
- 2026-08-19: **STOP CONDITION 발생 (docs/12). CAD WRITE 중단, 사용자 결정 대기.**
  INDEX rear retainer 설계 중, 실물 6x6x6 스위치의 **I1과 I2가 1.833mm 관통**함을
  분리축 정리(SAT)로 확인. 현재 CAD 실물에서도 두 시트가 **하나의 공동으로 병합**
  (두 중심 사이 재료 0/41 지점). I2-I3 여유 0.040mm, 칸막이 실측 약 1.14mm.
  원인 = 국소 법선 축의 수렴 (I1-I2 축 사이각 41.3도, 깊이 6.8mm에서 중심거리 10.73 -> 6.34mm).
  이전 보고 "I1-I2 clearance 2.036mm"는 꼭짓점 비교 오류 -> **철회** (docs/09, docs/11 표기 완료).
  버튼별 retainer plug 4개(`Part 17~20`)도 상호 간섭 -> 폐기 대상.
  문서 무결성은 정상: JaD/JfD partId 유지, split 0, assembly 25/25, regeneration 오류 0.
  MIDDLE row 미착수.
- 2026-08-19: docs/12 STOP 에 대한 축 최적화 완료 -> docs/13. **CAD WRITE 0건.**
  정확 SAT + 정확 OBB 최소거리로 재계산. uniform t sweep / 개별 t 최적화 수행.
  **핵심 발견: axis(t) 1-파라미터 패밀리로는 해가 없다.** I2-I3 여유를 얻으려면
  I3 를 기울여야 하는데 그 방향이 곧 분할면이라, 여유를 얻는 만큼 3+1 ownership 을 잃는다
  (uniform t=0.48 -> 분할면 0.85mm 침범, t=0.60 -> 1.49mm, 개별 t -> 벽 0.28mm 만 잔존).
  **해법 F2 (자유축):** 버튼 중심/Z=+9/피치 11/캡 8/6x6x6/3+1 전부 유지.
  변경되는 변수는 `#finger_switch_front_lip` 0.8 -> 1.5 하나뿐.
  축 I1(-0.814063,-0.500337,-0.294898) I2(-0.406762,-0.574504,-0.710274)
  I3(-0.074927,-0.997095,-0.013664) I4 변경없음.
  최소 스위치 여유 **1.200mm**, 최대 법선편차 **16.46도**, 분할면 벽 1.55/1.88mm,
  나사 B 2.89mm(기준선 동일), 배선 확보. 기존 8x8 개구부/캡 외형은 **유지**한다.
  구현 추가는 holder blank 에 front trim(n0 깊이 2.8) SUBTRACT 1단계뿐.
  잔여 리스크: 포켓 칸막이 0.80mm -> **SLA 출력 권장**.
  **MIDDLE 도 같은 문제 확인** (M1-M2 t=0 에서 1.186mm 관통) -> 같은 규칙 적용 필요.
  `Part 17~20` retainer plug 는 폐기 대상(목록만 작성, 삭제 미실행).
- 2026-08-19: **F2 CAD 재생성 실행 -> docs/14.** 체크포인트 `F2_rebuild_start`
  (`1bbe0311bfa8ecdc32a4a06d`). FS 편집만으로 처리 (Onshape 는 피처 중간 삽입 불가):
  IDX 축 교체 / GROOVE stage -> front trim 전용 / RETAINER stage -> no-op / lip 1.5 상수.
  결과: solid 22 -> 18 (plug 4개 소멸, 캡 4개 유지), JaD/JfD 정상, assembly 25/25,
  시트 6.4x6.4 정확, 분할 clip 적용, 개구부/stem/캡 정합 PASS.
  **plug 4개가 stage no-op 만으로 정확히 사라진 것이 곧 feature->part 라이브 검증이다.**
  **HOLD 3건 발생 (CAD WRITE 중단, 승인 대기):**
    1) 개구부 바깥 쉘 벽(안쪽면 n0 깊이 최대 4.10)이 기울어진 스위치 앞모서리를 막아
       실제 착좌 깊이가 4.5 -> 최대 5.15mm. 그 위치 기준 여유 1.200 -> **1.145mm**
    2) 칸막이 실측 **0.648mm** (승인 0.80). 원인: 칸막이를 스위치(6.0)가 아니라
       포켓(6.4x6.4x6.2)으로 구속했어야 함
    3) I4 홀더 <-> 나사 B **2.27mm** (요구 2.5). 원인: lip 확대로 blankTo 12.5 -> 13.2
  **수정안 (계산 완료, 미적용): 앞면 깊이 5.3(lip 2.3) + 축 재최적화로 3건 동시 해소.**
    최대 편차 16.46 -> 17.21도, 칸막이 0.800, 스위치 1.348, 나사 B 는 blankTo=seatTo+1.0.
    `INDEX_openings` 와 캡 외형은 손대지 않아도 된다.
  잔여: 트리 변수 `#finger_switch_front_lip`(0.8) 사문화 -> /features 429 해제 후 정리.
- 2026-08-19: **docs/14 HOLD 3건 수정 적용 완료 -> docs/15. INDEX holder geometry 완료.**
  체크포인트 `F2_final_fix_start` (`63e475448496b75aaeefdc24`). FS 3곳만 수정:
  IDX 축 교체 / `LIP_F2` 1.5 -> **2.3mm** / `blankTo` = seatTo + **1.0**.
  (retT 미사용이 되어 선언 제거 — FeatureScript 미사용 변수 = 에러, 두 번째 사례)
  최종 축: I1(-0.851033,-0.500047,-0.160298) I2(-0.393870,-0.571110,-0.720208)
           I3(-0.069850,-0.997555,+0.002429) I4(+0.024161,-0.968017,-0.249718)
  **검증 전항목 PASS:** exact SAT 최소 **1.3476mm**(>=1.20), 포켓 칸막이 **0.8000mm**(>=0.80,
  실물 메시로 해석값과 일치 확인), 나사 B **2.990mm**(I4, >=2.50),
  실제 착좌 **4/4 YES**(필요 깊이가 4개 전부 설계값 5.300mm 와 일치),
  stem/개구부 최소 0.730mm, 캡 어긋남 0.0740mm(<0.20, 캡 외형 무수정),
  분할 ownership PASS(I3 벽 1.500 / I4 1.999, clip 실물 확인),
  시트 4/4 정확히 6.4x6.4, front trim 외피 돌출 0.00mm,
  JaD/JfD 유지 split 0, assembly 25/25, 구 twist-lock plug 재생성 없음, solid 18개.
  regeneration 상태 직접 읽기만 `/features` 429 로 보류(간접 확인 완료).
  **기술부채:** `#finger_switch_front_lip` 트리 변수(0.8)는 사문. 형상 기준은 FS 의 2.3mm.
  rate limit 해제 후 동기화 필요. **다음: I1/I2/I3 공용 후면 retaining plate.**
- 2026-08-19: **후면 retainer 설계 확정 -> docs/16. CAD 형상 변경 0건.**
  체크포인트 버전 `INDEX_holder_final` (`6f0e56b8f7504503dc2db465`) 생성.
  **게이트 미개방:** `/features` GET 이 429 (Retry-After 약 5,700s, 버전 경로도 같은 버킷).
  `scripts/poll_features.py` 백그라운드 폴러 가동 중. 규정대로 **retainer 형상 미제작.**
  **확정 설계:**
   - 방식 = OPTION A (removable plate + 나사 2개). 슬라이드-in 은 세 bore 축이
     42.6/53.5/56.1도 벌어져 **공통 슬라이드 방향이 없어** 탈락.
   - 평면 backbone 도 탈락: 세 홀더를 비켜 가는 평면은 pad 가 6.0~8.5mm 필요
     (bore 관통은 1.2mm 뿐). -> **홀더 뒷면에 얹히는 faceted cap 3개 융합** 구조.
   - cap 11.0x11.0x2.0, 상호 겹침 2.19/0.28/1.75mm -> 단일 rigid body
   - pad 3.6x3.6, 돌출 1.2 + `#finger_retainer_preload`(0.15 provisional).
     pad 법선 = 각 스위치 축과 정확히 일치. 사방 1.4mm 링을 핀/배선용으로 남김
   - EAR_A = I1 축 -u 8mm (-18.19,-5.85,+10.52), EAR_B = I3 축 -v 8mm (-4.83,-19.87,+0.98)
     포켓 4.80mm / 나사B 16.9~19.3mm 여유. 기존 Screw_holes 무수정
   - I4 단독: cap+pad+ear(-v 8mm, X=+5.22 로 JaD 유지)
   - 배선: I2 만 축방향 3.2mm(나사B 보스) -> ±u 로 인출. cap 에 2.5x1.5 슬롯
   - 출력: 최적 베드 법선 (-0.4734,-0.8350,-0.2805) 에서 세 cap 경사 30.08도 -> **서포트 불필요**
  **INDEX FINAL SUCCESS 보류** (게이트 1건 + retainer 미제작 2건). MIDDLE 미착수.
- 2026-08-19: **rib 보강 지시 -> cap 설계 결함 발견 및 정정 (docs/16 §R). CAD 변경 0건.**
  I1/I2/I3 사이 별도 rib 을 넣으려 실측하다가 **11x11 평면 cap 자체가 쉘과 간섭**함을 확인
  (cap 부피 격자점 중 I1 1% / I2 15% / I3 16% 가 기존 재료와 겹침).
  원인: 홀더 뒷면은 노출된 평면이 아니라 세 홀더가 42.6/53.5/56.1도 로 융합된 faceted 면이고
  그 사이로 이웃 홀더·쉘이 파고들어 있다. 직선 rib·아치형 rib 전 조합 실패의 진짜 이유.
  **수정 아키텍처: retainer = 홀더 클러스터의 음형**
  (blank − 홀더OBB4+0.2 − 나사B+1.0 − 쉘 + pad3). backbone/rib 이 따로 필요 없어진다.
  0.75mm 복셀 25,839개 실측: 홀더 뒤 자유 공간이 **단일 연결 성분 2,440mm3** 이고
  세 pad 자리를 전부 포함. **병목 = I1-I2 3.54 / I2-I3 3.18 / I1-I3 3.18 mm**.
  -> **web 두께 2.0mm 채택** (양쪽 여유 +0.77/+0.59/+0.59mm, 요구 >=1.5 충족).
  병목 지점 전부 각 축 깊이 12.28~18.43 이고 최저점은 측방 11.0mm 라 스위치 뒷면과 무접촉.
  배선 슬롯 재배치: I1 -v / I2 +v(23.6mm) / I3 -v. pad 각도·위치는 불변.
- 2026-08-19: **regeneration 게이트 개방 -> ERROR 1건 확인. §1 에 따라 HOLD (docs/16 §G).**
  feature 162개 / OK 161 / INFO 4 / **ERROR 1** / suppressed 0 / isComplete true.
  ERROR = `INDEX_switch_pockets` (`FkGjuaVRtcptOX1_14`, 구 oneGripIndexButtons, stage=CONSTRUCTION,
  트리 인덱스 105). **원인: 참조하는 #finger_switch_* / #finger_retainer_* 변수가
  트리 인덱스 111~118 로 더 뒤에 있어 getVariable 실패.** 알려진 함정의 잔해다.
  **영향 없음** — CONSTRUCTION 은 참조 평면만 만들고 solid 를 만들지 않으며,
  인덱스 119 `INDEX_construction`(OK) 과 중복이고, ERROR 라 산출물이 없다.
  solid 18개로 예상과 일치하므로 docs/15 검증값은 전부 유효.
  INFO 4건은 전부 원본 `Joystick_part_*_plane` (신규 작업 무관).
  **권고: `FkGjuaVRtcptOX1_14` 삭제(또는 suppress) — 파괴적이라 승인 대기.**
  retainer 착수 보류, INDEX FINAL SUCCESS 보류 유지.
- 2026-08-19: **stale feature suppress -> INDEX F2 HOLDER = FINAL PASS. retainer 1차 구현 (docs/17).**
  `FkGjuaVRtcptOX1_14` (INDEX_switch_pockets) 만 suppress. 다른 피처 무수정.
  재조회: feature 162 / **ERROR 0** / WARNING 0 / INFO 4(원본) / isComplete true / suppressed 정확히 1.
  형상 무변화 확인: solid 18, JaD/JfD 각 1body, assembly 25/25, 시트 4개 6.4x6.4,
  칸막이 0.8000, 나사B 2.990, plug 0, ownership 유지 -> **INDEX HOLDER FINAL PASS**.
  **retainer (negative-mold, 신규 FS `OneGrip_Retainer` `372973e3f8ac06ede47d95c2`):**
   - fit clearance sweep 0.20/0.25/0.30 전부 목표 초과 -> **0.25 채택**
   - 삽입축 = 세 스위치 축의 **최소원뿔축 (-0.4734,-0.8350,-0.2805)**, 각 보어와 30.1도
     (pad 인출 허용 한계 46.0도). 공간최적 방향(-0.899,...)은 I2/I3 가 76/72도 로 탈락
   - 구현: blank -> 홀더 sweep 절삭 -> 나사B 절삭 -> pad3 -> 배선슬롯3 -> 쉘 절삭(복사본)
   - **solid 19, retainer 단일 body `RWID` 2028mm3, JaD/JfD 간섭 0, ERROR 0**
   - **web 최소 1.91mm** (I1-I2 2.28 / I2-I3 1.91 / I1-I3 1.91). 요구 1.5 충족, 목표 2.0 미달
   - 중간 결함: 배선슬롯(오프셋5.0/높이10.0)이 v=0 까지 뻗어 **pad 를 파고들어** web 이 1.37 로
     보였다. 오프셋6.0/높이8.0 으로 수정해 회복. 병목이 web 이 아니라 pad 였다
  **HOLD: insertion path FAIL.** t=1.5mm 에서 62/5846 복셀 충돌 (전부 I2 근방, Y=-19.0 평면).
  원인 = `SHELLCUT` 을 삽입방향으로 sweep 하지 않아 retainer 가 쉘 오목부를 채움.
  시도한 수정 3건(나사B sweep / blank 확대 / r 6.0) 모두 분할 또는 무효 -> 철회.
  다음: 국소 쉘 조각을 sweep 해 절삭하거나, blank 를 E(w) 근사 다면체로 정의.
  **ear/나사구멍·I4 retainer 미구현. INDEX FINAL SUCCESS 보류. MIDDLE 미착수.**
  FS 교훈 추가: `opPattern` 은 원위치(identity) 복사를 거부 -> 멀리 복사 후 opTransform 복귀.
- 2026-08-19: **국소 swept relief 시도 -> §12 fallback 조건 성립, HOLD (docs/18). CAD 원상 복구.**
  체크포인트 `RETAINER_core_v1` (`920a43fb9e0b5f01078d325d`).
  **obstacle 정체 확정:** face `JkO` = **나사 B 보스 원통면** (실측 r 3.500+-0.007,
  **X -21.74~0.00** — 기존 기록 X[-6,+10] 은 틀렸다), 차단 16%.
  face `SSIaC` = 그립 주 내벽 (실제 차단부 X -6.43~0, Y +1.70~+21.56, Z +10.27~+35.58), 차단 9%.
  필요 sweep: 보스 15.63mm / 주벽 34.09mm.
  시뮬레이션상 relief 후에도 최대성분이 세 pad 를 포함하고 **web 1.81mm (PASS)** 였으나,
  **실제 CAD 적용 시 retainer 가 2조각으로 분할 + feature ERROR** -> 피처 삭제하고 복구.
  **더 근본적 발견: 단일 직선 인출이 기하학적으로 불가능하다.**
  분할면 X=0 을 넘으려면 41.59mm 이동이 필요한데 그중 **+Y(후방) 34.73mm** 이고
  그립 공동이 그만큼 깊지 않다. pad 인출 제약(<=46도)이 w 를 보어축(대부분 -Y) 근처로 묶기 때문에
  인출은 필연적으로 +Y 지배가 된다. **pad 인출 조건과 분할면 탈출 조건이 반대 방향을 요구한다.**
  2구간 병진(-w 로 2~3mm 뺀 뒤 +X)도 2단계에서 t=1mm 만에 충돌 -> 실패.
  현재 상태: solid 19, retainer `RWID` 단일, JaD/JfD 정상, feature 168 / ERROR 0 / WARNING 0.
  **권고: 2순위 E(w) 방식으로 전환. 단 그 전에 '인출 완료' 정의를 확정해야 한다**
  (pad 분리+홀더 이탈 = 약 1.5~3mm 로 보면 성립, 분할면 완전 탈출로 보면 불가).
- 2026-08-19: **인출 완료 정의 변경 승인 -> SERVICE DISENGAGEMENT. 계산 재검증 (docs/19). CAD 수정 0건.**
  구 조건("retainer 전체가 X=0 을 41.6mm 넘어야 완료")은 폐기. 새 조건은
  "세 pad 가 보어에서 완전 이탈 + 안전여유" 까지만 CAD 로 강제한다.
  **d_I1 = d_I2 = d_I3 = 1.57mm** (w 가 최소원뿔축이라 사이각이 모두 30.08도 로 동일),
  d_required 1.57, **d_service = 2.07mm**.
  0~2.07mm 구간 충돌: **나사 B 보스 하나뿐, 334/16225 복셀 (2.1%, 42mm3)**, 최초 t=1.273.
  주 내벽(SSIaC)은 이 구간에 전혀 관여하지 않는다. 스위치는 t=0.20 부터 완전 분리.
  **국소 보스 relief sweep 길이 최적 = 3.00mm**: 제거 119mm3(5.9%), **단일 body 유지**,
  pad 3개 전량 보존, web 1.91mm 불변, 무충돌 이동 2.97mm (d_service 대비 +0.90 여유).
  5.0mm 이상 sweep 은 분할되므로 금지 (docs/18 의 15.63mm sweep 이 3분할된 이유).
  **결론: 기존 retainer 재설계 불필요. E(w) 다면체 불필요. relief 피처 1개만 추가하면 된다.**
  지시대로 CAD 수정 전에 멈춤. fastening 은 relief 적용·검증 후 GO.
- 2026-08-19: **국소 나사 B relief 적용 완료 -> docs/20.** 체크포인트 `RETAINER_pre_relief`
  (`2c90c9810a362680c1dfc8fa`). 피처 `INDEX_retainer_service_relief` (`F2M3epnJT0bImz7_16`).
  보스 원통(r 3.5+0.25) 을 w 로 **3.00mm sweep** 해 retainer 에서만 SUBTRACT.
  **결과 전항목 PASS:** RWID **단일 body**, 제거 **118.5mm3**(예측 119 와 일치),
  부피 2028 -> **1909.5mm3**, **무충돌 인출 2.93mm** (요구 2.07, +0.86 여유),
  보어 완전 이탈 **1.56mm** (해석 1.57 과 일치), t=2.07 에서 보어 겹침 **0/0/0/0**,
  스위치 간섭 t=0.20 부터 0, 배선 슬롯 3개 **완전 무변화**,
  feature 169 / ERROR 0 / WARNING 0, assembly 25/25, JaD/JfD 정상.
  **주시: web 1.91 -> 1.54mm.** 기준 1.50 은 충족하나 목표(1.91 유지) 미달이고 여유가 0.04mm 뿐.
  원인은 실제 sweep(0.5mm x 6)이 해석 모델(0.1mm 연속)보다 목 부근을 더 깎은 것.
  I2 pad 접촉면만 -1.3% (보스가 I2 에 가장 가까움), I1/I3 무변화.
  **EAR 앵커 재검증 완료:** EAR_A(-18.19,-5.85,+10.52) / EAR_B(-4.83,-19.87,+0.98) 유효.
  더 나은 위치도 발견 — EAR_A'(-14.11,-4.03,+11.24) / EAR_B'(-4.52,-15.38,+1.97) 는
  retainer 본체에 직접 붙고(탭 0) 쉘 보스만 2.4~2.5mm 필요.
  **fastening / I4 retainer 미구현 -> INDEX FINAL SUCCESS 보류. MIDDLE 미착수.**
  교훈: POST 응답의 featureState 는 재생성 완료 전 값이라 ERROR 로 보일 수 있다.
- 2026-08-19: **relief 정밀화 검토 (docs/21). CAD 수정 0건.**
  **docs/19 예측(1.91)이 빗나간 원인 규명:** web 측정 시 relief 절단면까지의 거리를
  포함하지 않고 원본 표면 거리만 썼다. 바로잡은 모델 예측 1.60 은 실측 1.54 와 일치한다.
  **이산화 비교 A(0.50x6) / B(0.25x12) / C(0.10x30) / D(연속근사 0.02x150):
  네 안이 모든 지표에서 완전히 동일** (제거 119.7mm3, web 1.60, travel 3.01, 단일 body).
  이유: relief 도구가 r3.75 x 23mm 굵은 볼록 원통이라 0.5mm 간격 합집합이 이미 연속과 같다.
  -> **FeatureScript 연속 sweep 구현 불필요. 이산화 개선으로는 게이트 통과 불가.**
  **web 을 지배하는 변수는 sweep 길이다:** 3.00->1.60 / 2.50->1.87(2분할) / **2.07->2.12**.
  sweep 3.00 을 유지하면 반경·X범위 어떤 조합으로도 최대 1.69mm (그 이하 반경은 body 분할).
  **권고: sweep 3.00 -> 2.07mm 만 변경.** fit 0.25 / 반경 3.75 / X[-22,+1] 전부 유지.
  결과 예측: 제거 65.7mm3, 단일 body, **web 2.12mm**, **travel 2.42mm**(요구 2.07 +0.35).
  근거: 요구 인출량이 곧 d_service 2.07 이므로 sweep 2.07 이 필요·충분값이고,
  3.00 의 초과분이 web 을 0.52mm 깎고 있었다.
  **fastening HOLD** (§6 게이트 web>=1.70 미달). sweep 변경 승인 대기.
- 2026-08-19: **relief sweep 3.00 -> 2.07mm 적용 완료 -> docs/22. fastening GO.**
  `INDEX_retainer_service_relief` 의 sweep 길이만 변경 (0.5x6 -> 0.345x6).
  fit 0.25 / 반경 3.75 / X[-22,+1] / w / d_service 2.07 전부 유지. pad·슬롯·홀더·쉘 무수정.
  **결과 전항목 PASS:** feature 169 / ERROR 0 / WARNING 0, RWID **단일 body**,
  제거 **60.3mm3** (예측 65.7, 복셀오차 범위), 부피 1967.7,
  **service travel 2.24mm** (요구 2.07 +0.17; 예측 2.42 보다 낮은 이유는 보스가 아닌
  다른 국소 쉘면 `RSI+` 가 2.24 에서 먼저 나타나기 때문),
  보어 완전 이탈 **1.56mm**, t=2.07 겹침 **0/0/0/0**, 스위치 t=0.20 부터 0,
  **최소 web 2.10mm** (I1-I2 2.10 / I2-I3 2.10 / I1-I3 2.15; 예측 2.12 와 0.02 차이),
  **pad 3개 접촉면 완전 회복** (sweep3.00 에서 I2 만 -1.3% 였던 것이 원래 값 복귀),
  배선 슬롯 3개 완전 무변화.
  **핵심 교훈: relief sweep 길이가 web 을 지배하는 유일한 변수였고,
  필요·충분값(d_service)으로 맞추자 web 이 relief 전(1.91)보다도 좋아졌다(2.10).
  과도한 sweep 이 순수 손실이었음이 실물로 증명되었다.**
  §8 fastening 게이트 8개 항목 전부 통과 -> **GO**.
  다음: EAR_A'(-14.11,-4.03,+11.24) / EAR_B'(-4.52,-15.38,+1.97) + 쉘 보스 + 나사구멍,
  그 뒤 service path 재검사 -> I4 retainer -> INDEX FINAL VALIDATION -> MIDDLE.
- 2026-08-19: **EAR_A'/EAR_B' fastening 구현 완료 -> docs/23. §15 조건 13개 중 12 PASS.**
  체크포인트 `INDEX_RETAINER_CORE_FINAL` (`744823195f26fedf7493f9ad`).
  피처 5개 RET_ear_A / RET_ear_B / RET_shell_boss_B / RET_hole_A / RET_hole_B 전부 OK.
  **EAR_A'** ⌀7.0, s[-2.5,+1.5], 기존 JfD 벽 6.2mm 에 직결 -> boss 불필요.
  **EAR_B'** ⌀7.0, s[-6.0,-0.5] + 쉘 boss ⌀5.0 s[+0.5,+5.2] (JfD 에 union, partId 보존).
  나사 규격 전부 PROVISIONAL (M2 급 가정, 기존 Screw_holes 복사 아님).
  **결과:** service travel **2.09mm** (요구 2.07, 여유 +0.02, 차단복셀 0),
  최소 web **1.96mm** (EAR_A-I1 2.38 / EAR_B-I3 1.97 / 코어 1.96),
  드라이버 무간섭 21.3mm(A) / X=0 완전개방(B), 나사B 간섭 0,
  pad 접촉면 3개 전부 무변화, 배선 I1·I2 무변화 **I3 만 -5%** (EAR_B' 근접),
  feature 174 / ERROR 0 / WARNING 0, RWID 단일 2136.4mm3, JaD/JfD 유지, assembly 25/25.
  **중간 결함 3건과 수정:**
   1) ⌀5 ear 에 ⌀3.8 카운터보어 -> 벽 0.6mm, neck 0.19 -> **카운터보어 폐기 + OD 7.0**
   2) `SHELLCUT` 이 0 clearance 라 표면이 쉘과 접해 travel 1.83 -> **쉘 복사본을 w 로
      2.07mm sweep 해서 빼도록 수정** (제거 0.2mm3 뿐인데 걸리던 살만 정확히 제거)
   3) EAR_B' 가 주변 retainer 보다 낮아 드라이버가 0.3mm 만에 막힘 -> **-w 로 더 돌출**
  **주시: travel 여유 0.02mm / I3 슬롯 -5%.**
  **I4 retainer 미착수 -> INDEX FINAL SUCCESS 보류, INDEX_FINAL_VALIDATED 미생성.**
- 2026-08-20: **I4 분리형 retainer 구현 + INDEX FINAL VALIDATION 완료 -> docs/24. 전 항목 PASS.**
  shared I1/I2/I3 retainer·JfD fastening은 승인 상태로 동결한 뒤 체크포인트
  `INDEX_SHARED_RET_FINAL` (`6703cd9cbd0d5e321ac10b87`) 생성.
  독립 FS `OneGrip_I4_Retainer`에 새 단일 부품 `RZKD`를 생성했다. 최종 구조는
  **6.5x10x2.8mm split-side plate + 3.6x3.6mm pad + edge-open notch + OD7 ear +
  JaD-only OD6 boss + clearance 2.4 / pilot 1.7mm**이며 나사 규격은 provisional이다.
  preload 0.15mm 기준 **d_required 1.35mm / d_service 1.85mm(+0.50 safety)**,
  실제 t=0/0.5/1.0/1.35/1.85 전 구간 JaD 차단 0, 드라이버 최초 간섭 28.10mm.
  초기 10x10 plate가 frozen `RWID`와 겹치는 것을 원자 단계 검증에서 발견하여 shared 형상은
  건드리지 않고 I4 plate만 split-side 폭으로 축소했다. 최종 actual mesh에서 I4-RWID 및 양쪽
  service sweep 전 구간 상호 침투 0을 확인했다. 최소 구조 두께는 plate 2.8 / pad 3.6 / ear wall 2.3 /
  boss wall 2.15mm로 목표 2.0mm 이상이다.
  **동결 증명:** JfD·RWID tessellation fingerprint/부피가 checkpoint와 정확히 동일,
  JaD 변경은 I4 boss 국소부에만 한정. 기존 I4 opening/seat/cap 및 shared pad 3개,
  I3 배선 -5% 상태, shared web 1.96mm, shared service 2.09mm도 유지했다.
  최종 **feature 180 / ERROR 0 / WARNING 0 / solid 18**, assembly **25/25**,
  JaD/JfD/RWID/RZKD identity 모두 단일 유지.
  전 항목 통과 후 최종 버전 `INDEX_FINAL_VALIDATED`
  (`03ede76e83b5c865d9a69c35`) 생성. **INDEX는 이 버전에서 동결.**
  **MIDDLE은 이번 작업에서 미착수이며, 다음 실행의 GO 단계다.**
- 2026-08-20: **INDEX FINAL 사후 감사 2건 -> docs/25, docs/26. CAD WRITE 0건 (GET only).**
  docs/24 가 보고한 `solid 19 -> 18` 이 body 소멸로 보일 수 있어 두 version 을
  동일 기준으로 재감사했다.
  **docs/25 (body inventory):** 원인은 소멸이 아니라 **counting rule 혼용**.
  구 `run_retainer.py` 의 `solids()` 가 `bodyType` 필터 없이 `/parts` 전체를 세어
  wire 2개(`Curve 1`=JMD, `Curve 2`=RNDD)를 포함했다. `bodyType=="solid"` 기준으로
  재계산하면 **17 -> 18 (+1, RZKD 추가)** 이고 사라진 body 는 없다.
  다만 strict exact fingerprint 게이트에서 **JfD raw tessellation hash / nominal volume 이
  fresh version-to-version GET 으로 재현되지 않아** 1건 FAIL -> **MIDDLE HOLD** 판정.
  **docs/26 (identity 재감사, `configuration=default` 명시):** 그 FAIL 이 형상 변화가
  아님을 확정했다.
   - **B-rep topology 완전 동일** — vertex 276 / edge 427 / face 145, entity ID 집합 동일,
     added·removed 0. 동일 entity ID 간 **최대 좌표편차 0.000000745mm**
   - **volume 차 0.4563mm3 (0.000918%)**, 두 tolerance interval 이 완전히 겹침 -> compatible
   - shared feature definition 12개 JSON exact same (group SHA-256 동일),
     RWID bodydetails SHA-256 도 동일
   - tessellation 은 Onshape 상 **persistent data 가 아니라 요청 시 생성되는 근사치**이므로
     raw hash exact equality 를 FINAL identity gate 에서 제외 (기록만 유지)
  -> **INDEX FINAL SUCCESS = CONFIRMED, MIDDLE = GO.**
  최종 라이브 상태 재확인: records 20 / **solid 18** / wire 2, JaD·JfD·RWID·RZKD 전부 단일,
  feature 180 / OK 180 / ERROR 0 / WARNING 0 / isComplete true,
  suppressed 정확히 1 (`INDEX_switch_pockets`), assembly 25/25 dangling 0.
  워크스페이스가 `INDEX_FINAL_VALIDATED` 와 동일하며 MIDDLE 지오메트리 피처는 0건이다.
  **교훈: body count 를 보고할 때는 반드시 `bodyType` 필터 기준을 함께 적어라.
  필터 없는 `/parts` 개수는 wire 를 포함해 서로 다른 실행기 사이에서 어긋난다.**
  참고: 재개 과정에서 동명 version `INDEX_SHARED_RET_FINAL` (`0e780d908243044205e5efef`,
  08-20 07:25) 이 하나 더 생성돼 있다. docs/24 가 기준으로 쓴 것은
  **`6703cd9cbd0d5e321ac10b87` (08-20 08:05)** 쪽이다. 버전은 불변 스냅샷이라 무해하나 혼동 주의.
- 2026-08-20: **하부 경사 어댑터 착수 — 아키텍처 확정. Onshape CAD WRITE 0건 (GET only).**
  상체를 무수정 탈착 모듈로 두고 그 아래에 경사 마운트를 새로 만드는 서브시스템을
  **`lower_adapter/` 로 분리**했다 (§6 참조). 루트 `docs/` 는 상체 전용으로 유지한다.
  분리 계기: 병렬 워크플로와 **`docs/31` 번호가 실제로 충돌**했다
  (`31_stock_6x6x6_switch_actual_fit_audit.md` vs 하부 분석). 하부 문서는
  `lower_adapter/docs/00_architecture_analysis.md` 로 이동, 이후 독립 번호를 쓴다.
  **상체 하단 인터페이스 실측 (전부 재현 가능: `lower_adapter/scripts/analyze_lower_interface.py`):**
   - **착좌면 = 평면 1개** Z −67.878507, 면적 5017.5mm2, 77.431 x 72.436mm, 도심 (0, 25.996).
     0.25mm 격자 전수 검사에서 보스 외 구멍·돌기 **0개** -> "음형 크래들"이 평면+타원벽으로 끝난다
   - **소켓 보어 21.072 x 25.672, 직진 깊이 정확히 21.000mm**, 축 = (0, 27.269160) 의 +Z.
     41단면 측정에서 **+Z 편차 0.000000도** (dX/dZ −5e-17)
   - **착좌면 법선 ⟂ 보어축 = 0.000000도** (3901점 적합, residual 6.4e-05mm).
     즉 `GRIP_AXIS ⟂ TILT_SURFACE` 가 원본에 이미 내장돼 있어 보정 회전이 필요 없다
   - **상대 post 20.272 x 25.272**, 여유 X 0.400 / Y 0.2068·0.1932 mm/side, 보어 물림 20.618mm.
     `Complete` assembly occurrence transform 실측으로 확보 (Pitch->Grip = 180도 about Z,
     t=(0, 53.9118, −114.8609)). **Base Part Studio 의 mesh 좌표는 layout 위치라 신뢰 불가**
   - 보스 31.0 x 35.5, 플랜지면 아래 6.000mm. 하단 살 13.9~21.0mm 통짜(스커트만 3.1~4.2mm)
   - **원본 짐벌 중심이 그립 좌표 (0, 27.312, −114.861)** = 중심축 위, 플랜지면 아래 46.98mm
   - 하단 인터페이스는 baseline 과 소수 4자리까지 동일 -> **손가락 버튼 작업이 전혀 안 건드렸다**
  **경고 (설계 필수 반영):**
   - 플랜지 윤곽의 **180도 회전대칭 오차가 평균 0.195mm** -> 외형 윤곽만으로 만든 크래들은
     그립을 뒤집어 끼울 수 있다. 보스 포켓(180도시 2.546mm 어긋남) 또는 post 가 반드시 필요
   - **소켓 구간에 두 쉘을 조이는 나사가 하나도 없다** (가장 낮은 S3 가 31.5mm 위).
     post 삽입이 쉘을 벌리는 방향이다 -> 보스 포켓을 외부 칼라로 쓴다
   - 쉘 나사 3개는 전부 플랜지면 위 46.5mm 이상 -> **크래들 체결에 못 쓴다**
  **확정 파라미터:** `#grip_tilt` 20도, `#tilt_direction` **TOP -> −Y** (`RotX(+θ)`,
  n=(0, −0.342020, 0.939693)), `#hand_sign` +1 (RIGHT HAND).
  구조 = Grip Cradle(각도 무관) + Tilt Wedge(각도 의존은 여기뿐) + Clamp Ring.
  **정정 2건 (이전 보고 오류):**
   1) "−Y = 엄지 패널 쪽" 은 부품 **위치** 기준으로만 맞다. 작동면 법선은
      **(0.000026, +0.658901, +0.752230)**, 수직에서 41.22도로 **+Y 와 위쪽을 향한다.**
      이걸 근거로 한 이전 인체공학 추론은 무효
   2) "경사 방향은 좌/우手 결정과 묶여 있다" 는 틀렸다. `M=diag(-1,1,1)` 과 `RotX(θ)` 는
      교환하므로(`M·RotX·M⁻¹ = RotX`) **경사 방향은 hand-neutral 이다**
  **이월:** 확정 방향의 CG 편차 −45.596mm (원본 수직 −26.817 의 1.70배)이고
  피벗 깊이 L 로 상쇄되지 않는다(`−45.596 − 0.342L`). 짐벌 단계에서 스프링 프리로드 /
  카운터웨이트 / 펌웨어 오프셋 중 택일 필요.
  **다음: `lower_adapter/docs/00` §10 의 0단계(version `PRE_ADAPTER`) — 착수 승인 대기.**
- 2026-08-20: **하부 20도 경사 어댑터 1차 CAD 구현 완료 -> `lower_adapter/docs/01`. 전 항목 PASS.**
  체크포인트 `PRE_ADAPTER` (`40aeafabde5ccb638fa0aec3`, parent = INDEX_FINAL_VALIDATED),
  결과 버전 `LOWER_ADAPTER_V1` (`41712f1bb7b025dbdb8b67b4`).
  **신규 Part Studio `OneGrip_LowerAdapter` (`bbfebe9c42748fb6d5b912e8`)** + Feature Studio
  `OneGrip_LowerAdapter_FS` (`fad6109b6980934c74639943`). 피처 8 / solid 4:
  CRADLE `JHD` 68042mm3 / WEDGE `RoBD` 149602mm3 / RING_F `RwCD` / RING_B `RzDD`.
  **상체 Joystick Part Studio 쓰기 0건.** 신규 스튜디오에 derive 가 없어 상체 body 가
  아예 없다 -> 구조적으로 수정 불가. `run_adapter.py` 의 `_guard_eid()` 가 상체 eid 를 차단.
  **20도 수용조건 실측 검증:** 웨지 밑면 법선 `(0, -0.342020, -0.939693)`,
  `angle(밑면 법선, 소켓축 +Z) = 20.000000 deg`, 밑면 평면도 편차 0.007764도.
  `GRIP_AXIS ⟂ TILT_SURFACE = 90.000000도`. 각도는 **웨지 기준면 절단 한 곳에만** 존재하고
  크래들/링/post/포켓은 그립 프레임에서 각도 0 으로 만든다 -> 15/25/30 은 웨지만 재생성.
  **물림:** post 20.272 x 25.272 (원본 Pitch post 와 동일), 여유 X 0.400 / Y 0.200 mm/side,
  보어 물림 20.000mm, 끝 여유 1.000mm. 착좌 평면 5017mm2 가 하중을 받는다(원본 ~330mm2).
  **체결:** 보스 포켓(31.672x36.272x6.2, 회전키 겸 칼라) + 2분할 클램프 링(립 물림 5.000mm,
  수직 유격 0.327mm, M3x6) + 크래들-웨지 M3x4 + 짐벌 인터페이스 M3x4(56x44 직사각).
  나사 규격 전부 PROVISIONAL. 상체 가공 0, 기존 쉘 나사 3개 미사용.
  **검증:** 간섭 0 (0.4mm 복셀 239만개), 부품 상호 간섭 0, 크래들-웨지 접촉 간극 0.000000,
  기준면 아래 돌출 0.0000, 최소 살 3.250mm, 스택 높이 33.900mm, 전체 높이 145.860mm.
  **중력 보상은 사용자 지시대로 하지 않았다.** 기록만: 원본 약 4020 -> 20도 약 6840 g·mm (1.70배).
  Hall 오프셋은 보상 수단이 아님(전기적 중심만 이동, 중력 토크 상쇄 불가).
  **경합 주의:** 작업 중 병렬 워크플로가 상체를 바꿨다 (feature 180->192, solid 18->22,
  `its1105Index` 12개, 신규 body RmND/RqND/RuND/RyND). 하단 인터페이스는 라이브 재측정에서
  소켓 21.0720x25.6720 / 보스면 -73.8785 / 착좌면 -67.8785 로 **소수 4자리까지 무변화** ->
  어댑터 정합 상수 유효.
  **FeatureScript 교훈 4건:** (1) 함수 인자 8개 거부(7개까지), 초과 시 **메시지 없이** 컴파일 실패
  (2) 함수명 `box` 는 std 와 충돌해 같은 증상 -> `mkBox` (3) body 생성 id 는 feature `id` 하위여야
  하고 `makeId("문자열")` 로 만들면 feature ERROR (앞 단계 body 조회에만 `makeId(featureId)` 사용)
  (4) `qCreatedBy(id, EntityType.BODY)` 는 스케치 wire body 도 잡으므로 boolean tool 에는
  `qBodyType(..., BodyType.SOLID)` 로 감싸야 한다.
  **짐벌(625ZZ/스프링/홀/카운터밸런스)은 착수하지 않았다. 별도 승인 필요.**
- 2026-08-21: **매립형(embedded) 20도 짐벌 1차 CAD 완료 -> `lower_adapter/docs/03`. 간섭 0.**
  사용자 아키텍처 정정 승인: 웨지 위에 짐벌을 쌓지 말고 **경사 베이스 자체를 짐벌 하우징**으로
  쓴다. 큰 웨지는 이동부에서 제거. 결과 버전 `EMBEDDED_GIMBAL_V1` (`239edc28544c9978899ed7a1`),
  신규 Part Studio `OneGrip_EmbeddedGimbal` (`2e024442c796323fd37e49c3`).
  body 5개: HUB `RnBD` 26654mm3(이동) / RING `RdCD` 13738mm3(이동) /
  HOUSING `JHD` 340272mm3(고정) / CARRIER x2 `J3D`,`RPBD` 4085mm3 각(고정, 분리형).
  **상체 Joystick Part Studio 쓰기 0건.**
  **파라미터화:** Part Studio 변수 `#pivot_depth` `#gimbal_travel` `#seat_recess`
  `#axis1_radius` `#axis2_radius` `#yoke_wall` 6개를 트리 상단에 선언하고 FS 가
  `getVariable` 로 읽는다. 파생 치수(well, 공동, 링 내경)는 전부 여기서 계산된다.
  **정정 (중요):** docs/02 의 "피벗 깊이 15mm 가능" 은 **틀렸다.** 포락선을 그립 메시의
  정점만(16,967개) 샘플링했는데 큰 평면은 tessellation 내부에 정점이 거의 없어 실제보다
  얕게 나왔다. 삼각형 표면 균등 샘플(224,881점)로 재계산한 실효 최소 피벗 깊이는
  **18.45 / 19.07 / 20.65 mm (각각 +-10 / +-12 / +-15도)** 다. 채택 p = **18.5mm**.
  넓은 베이스(a1>=58)로 빼면 p>=12.07 이지만 링이 커져 순 이득 약 2mm 뿐, 폭 +30mm 라 기각.
  **검증 (0.5mm 복셀 약 1200만개):** 총 간섭 **0**. GRIP 8방향 / RING 축1 +-10 /
  HUB 축2 +-10 / HUB 4방향 / 중립 fit 전부 0.
  `angle(하우징 밑면 법선, 소켓축) = 19.999999도`, post 20.272x25.272 여유 X0.400/Y0.200,
  보어 물림 20.000mm — V1 과 동일 인터페이스, 상체 무가공.
  **요청 높이 2건:** (1) 경사 외피 -> HAND_REF(중지 행 도심) = **55.879mm**,
  (2) 고정 베이스 바닥 -> HAND_REF = **85.153mm**. 착좌면은 외피보다 6mm 아래(well 안).
  하우징 116x116mm, 높이 0~66.48mm, 전체 조립 152.96mm. 적층안 대비 약 **43mm 낮다.**
  이동질량 약 192g (V1 의 WEDGE 186g / CRADLE 84g 은 이동부에서 제외).
  **중간 결함 4건과 수정:** (1) 캐리어 안쪽면이 링과 정지 상태에서 겹침 -> `ringOutU+0.5`
  (2) 허브 팔 14x14 가 링 숄더 D13.65 를 못 지남 -> 앞 3mm 를 **D8 노즈**로
  (3) p 를 올리자 팔 상단이 허브 바닥에 안 닿아 body 4분할 -> 팔을 항상 허브 바닥까지
  (4) 링 내경을 정지 기준으로 잡아 +-10도에서 허브 모서리와 간섭 ->
  `ringInU = hubHalfU*cos + (p-9.7)*sin + CLR` 로 스윕 기준 재정의.
  **조립:** 베어링 기둥을 통짜로 만들면 링을 well 로 못 넣는다 -> **캐리어 분리형**.
  HUB+RING 결합 -> well 로 투입 -> 캐리어 측면 삽입 후 바닥 M3 -> 축1 베어링/M5.
  **기술부채:** `GET /features` 가 429 (Retry-After 81,136s). POST/DELETE 는 정상이라
  POST 응답 + `/parts` + tessellation 으로만 검증했다. `#pivot_depth` 가 트리에 2번
  선언돼 있고(15 -> 18.5, 뒤가 이김) 429 때문에 앞 선언을 못 지웠다. 해제 후 정리 필요.
  **스프링 선정 / 홀 캘리브레이션 / 중력 보상 / 하우징 상하분할은 지시대로 미착수.**
