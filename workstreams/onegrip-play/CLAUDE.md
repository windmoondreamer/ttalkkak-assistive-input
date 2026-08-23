# OneGrip Play

한손 FPS 컨트롤러 프로젝트. 기존 **DIY Joystick Onshape CAD**를 베이스로 파생 설계한다.
이 저장소는 설계 자료 / Onshape 연동 코드 / CAD 수정 스크립트 / 문서를 관리한다.

이 문서는 제품명·폼팩터·기구·전자·플랫폼을 포함한 **모든 제품 결정의 최상위 기준 문서
(source of truth)** 다. 외부 문서와 충돌할 경우 이 문서를 따른다.

**프로젝트 배경:** 제7회 국립재활원 보조기기 해커톤 참가 프로젝트이며,
동국대학교 전자전기공학부 김민섭 / 윤홍민 / 장재원 / 김예진 팀의 작업이다.
배경정보 출처는 [ttalkkak-assistive-input README](https://github.com/windmoondreamer/ttalkkak-assistive-input/tree/add/onegrip-play-cad-workspace)다.

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
    │   ├── 00_architecture_analysis.md  # 아키텍처 사전 분석 (CAD WRITE 0건)
    │   ├── 03_embedded_gimbal_v1.md     # OPTION B 매립 짐벌 (fallback, 보존)
    │   ├── 05_stock_cartridge_feasibility.md  # OPTION C 실현성 감사
    │   ├── 06_stock_cartridge_v1.md     # OPTION C thin-deck (참조 상태)
    │   └── 07_conformal_stock_embed_v1.md  # ★ 컨포멀 매립 (현재 활성)
    ├── cad/
    │   ├── OneGrip_EmbeddedGimbal.fs    # 커스텀 짐벌 (개발 중단, 참고 보존)
    │   ├── OneGrip_Cartridge.fs         # OPTION C thin-deck (참조)
    │   └── OneGrip_Conformal.fs(.tmpl)  # ★ 컨포멀 매립 하우징
    ├── scripts/
    │   ├── analyze_lower_interface.py   # docs/00 의 모든 수치 재생성
    │   ├── stock_geom.py                # 스톡 짐벌 중립 복원 형상 캐시
    │   ├── analyze_c1c2_wiring.py       # 사전검증 A(나사) / B(배선)
    │   ├── design_cartridge.py          # 모션 포락선 / keep-out
    │   ├── run_cartridge.py             # OPTION C FS 실행기 (WRITE 가드)
    │   ├── verify_cartridge.py          # thin-deck 32 게이트 검증
    │   ├── envelope_conformal.py        # ★ 필요 내부 포락선 (§17)
    │   ├── gen_conformal_fs.py          # ★ 컨포멀 FS 생성 (실측 -> 밴드)
    │   ├── run_conformal.py             # ★ 컨포멀 FS 실행기
    │   ├── verify_conformal.py          # ★ 26 게이트 검증
    │   ├── variants_conformal.py        # ★ COMPACT/BALANCED/FULLY_ENCLOSED 비교
    │   └── fs_trace.py                  # FS 평가 엔드포인트 진단기
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
- 2026-08-21: GitHub README에서 대회명과 참가 인원 등 프로젝트 배경정보만 병합.
  제품 관련 결정은 전부 이 문서를 유지했으며 **CAD 수정 없음.**
- 2026-08-21: **스톡 짐벌 카트리지(OPTION C) 실현성 감사 -> `lower_adapter/docs/05`. Onshape CAD WRITE 0건 (GET only).**
  사용자 지시로 커스텀 `625ZZ/HUB/RING/CARRIER` 매립 짐벌은 **일시 중단(삭제 아님)**.
  `EMBEDDED_GIMBAL_V1` / `lower_adapter/docs/03` / `docs/04` 는 fallback 으로 보존한다.
  원본 하부 짐벌을 **수정 불가 기계 카트리지**로 통째로 재사용하는 안을 측정만 했다.
  **FIXED/MOVING 판별 (편향 스냅샷의 Base 대비 상대 회전으로 확정):**
  FIXED = `Base`(RYBD) / `Roll_holder`(JJD) / `Roll_holder_2`(RKCD) / `Spacer`(ROCD).
  MOVING = `Roll` 0.452도 / `Pitch` 5.606도 / **`Spring_holder` 5.606도**.
  **`Spring_holder` 는 이름과 달리 이동부다. 카트리지 고정에 쓰면 안 된다.**
  **체결 후보:** 기존 `Roll_holder` M3x16 **2개**가 Base 밑면에 머리가 오는 관통 나사다
  ((0.35, 60.33) / (0.35, -6.95), Z -149.46, 밑면 -149.96 -> 0.5mm 카운터보어).
  **아래에서 직접 접근 가능 -> Priority 1 성립.** 다만 두 나사가 X=0.35 중심선상에
  **공선**이라 회전을 못 잡는다 -> Base 밑면 100.0 x 143.0 평면에 얕은 포켓(0.3mm/side)
  필수. Base 가 피벗 기준 Y -93.6/+49.4 로 **강하게 비대칭**이라 포켓만으로 180도 오조립이
  물리적으로 불가능하다(매립 V1 의 플랜지 0.195mm 대칭 문제와 대조적).
  스프링 훅 M3 4개(C3~C6)는 Base **윗면**이라 아래에서 못 쓴다. M5x12 4개는 짐벌 축 = 사용 금지.
  **삽입 깊이:** 덱을 착좌면 **+6.0mm** 까지 올릴 수 있고 그 상태에서 고정부(Base/holder x2/
  Spacer)가 **전부 덱 아래**, 덱 위로 나오는 것은 OneGrip 과 Pitch post 뿐이다.
  한계는 하드 충돌이 아니라 **손이 덱 림에 닿는 지점**이고 이는 매립 V1 과 **같은 제약**이다.
  **모션 개구부는 원형이 아니다.** Z 별 필요 단면: 착좌면+6 75.2x71.8 / 0 88.0x83.9 /
  **-3 93.0x88.5 / -6 93.3x88.2 (최대)** / -12 이하 69.7x73.8(Spring_holder 지배).
  권장 = **96.3 x 91.5 스트레이트 관통** (FDM 1.5mm/side). 덱 개구부는 비구조.
  **인체공학 (덱=착좌면+6, HAND_REF 정의는 docs/03 과 동일):**
   (1) 경사외피->HAND_REF **55.879mm** — **매립 V1(55.879)과 완전 동률**
   (2) 고정바닥->HAND_REF 153.287mm (V1 85.153) — 다리를 카트리지 최저점까지 내렸을 때
   (3) 경사외피->스톡 피벗 52.982mm (V1 24.500)  (4) **덱 아래 돌출 114.775mm** (V1 46.64)
  **스톡 수정 필요 항목: 0건.** 베어링/스프링/샤프트/홀/이동형상/그립-post 인터페이스 전부 무수정.
  나사 2개를 M3x16 -> M3x22 로 **교체**(가공 아님)하는 것만 필요.
  **권고: OPTION C.** #1 지표(손 높이)가 동률이면서 B 에 남아 있는 미착수 스코프
  (베어링 시트/저널 정렬/스프링 재설계/홀 재설계 = docs/04 결함 4건 포함)가 통째로 사라진다.
  신규 인쇄 부품 5 -> **2**, 신규 기계 인터페이스 6+ -> **2**.
  **조건: 덱 아래 약 115mm 공간 확보.** 총높이 100mm 이하가 강제되면 **B 로 회귀**한다.
  **정정 2건 (이전 보고 오류):** 원본 스톡 짐벌 "착좌면->베이스 바닥 122.47mm / 풋프린트
  100.0x151.4" 는 **틀렸다.** `Base` 부품 메시에 동명의 **서브어셈블리 transform** 을 적용했고
  조립 스냅샷이 중립이 아니었다. 중립 복원(Base 밑면 법선 (0,0,-1) 확인) 후 실측은
  **82.078mm / 100.0 x 143.0 x 18.5mm**. docs/02 의 "원본 대비 약 90mm 낮다" -> **약 41mm**.
  docs/02 와 `analyze_embedded_gimbal.py` 에 정정 반영 완료. 피벗 깊이 46.982mm 는 유효.
  **카트리지/캐리어/하우징/구멍/브래킷 미생성. 승인 대기.**
- 2026-08-21: **OPTION C 스톡 카트리지 1차 CAD 완료 -> `lower_adapter/docs/06`. 검증 32/32 PASS.**
  체크포인트 `PRE_STOCK_CARTRIDGE` (`f4503217c4b324ef98447bc6`),
  결과 버전 `STOCK_CARTRIDGE_V1_VALIDATED` (`2e661ad4e1f5970dee79371d`).
  신규 Part Studio `OneGrip_StockCartridge` (`f698b10ce216ca7c95051dd3`) +
  Feature Studio `OneGrip_Cartridge_FS` (`62a4eb9392f3b60332d335b0`). body 2개:
  `CARRIER_PLATE` `JHD` 117.6x117.6x9.0 (87,490mm3) / `DECK_HOUSING` `R/CD` 130x130 (271,171mm3).
  **상체 Joystick / 스톡 Base Part Studio 쓰기 0건.** OPTION B(`EMBEDDED_GIMBAL_V1`,
  docs/03, docs/04)는 fallback 으로 무수정 보존.
  **사전검증 A (C1/C2 스택업, 실측):** C1->`Roll_holder`(JJD) / C2->`Roll_holder_2`(RKCD),
  둘 다 **⌀3.000 원형 블라인드 깊이 13.000mm** (나사산 미모델링 = FDM 셀프탭 전제).
  Base 쪽은 **관통이 아니라 슬롯 3.4x11.4** + 카운터보어 슬롯 6.0x12.7x3.5.
  현재 물림 6.000 / 블라인드 잔여 7.000. **긴 나사가 이동부에 닿을 수 없다** (그 축에
  Roll/Pitch/Spring_holder 가 전혀 없다) — 유일한 한계는 블라인드 바닥.
  캐리어 부착 후 필요 길이 22.000~29.000 -> **M3x22 채택** (물림 6.000 / 여유 7.000 =
  스톡과 소수 3자리까지 동일). 가공 없이 **나사 2개 교체**만 필요.
  캐리어 구멍도 Base 와 같은 **Y 슬롯**으로 냈다 (Base 가 holder 에 대해 Y 로 float 하므로
  원형 구멍이면 포켓과 싸운다).
  **사전검증 B (배선):** Arduino Pro Micro + micro USB 가 어셈블리에 **있다.**
  X[-8.74,9.08] Y[-63.95,-29.50] Z[-152.81,-141.25], **USB 셸이 Base 밑면 아래 2.850mm**.
  **스톡 Base 는 100x143 직사각이 아니라 T 자다** — 본체 100.000x100.000 +
  전장 꼬리 28.000x43.000. **전장 포켓은 모델링돼 있지 않다** (전장 표본 81.1%가 Base
  솔리드 내부) -> 꼬리 전체를 보수적으로 비웠다. CABLE_EXIT=-Y, 채널 X[-14.65,15.35]/Y<=-23.31,
  STRAIN_RELIEF = `#usb_clearance` 6.0mm (provisional).
  **180도 오조립:** Base 본체만 보면 100x100 정사각이라 회전 불일치 4.24% 뿐 -> 못 막는다.
  **꼬리 포함 시 33.9%** -> 포켓에 꼬리 슬롯을 넣어 물리적으로 불가능하게 만들었다.
  **덱 개구 = 90.789x87.485 (R8)** — 9자세를 **덱 두께 구간에서만** 합집합한 값 + FDM 1.5/side.
  docs/05 의 96.3x91.5 는 **모든 Z 의 최대**(착좌면 -3~-6)라 덱 개구가 아니다.
  덱 아래 하우징 내부는 118x118 이라 keep-out 96.69x91.75 를 전부 포함한다.
  **검증 32/32:** 덱 vs 수평 **20.000000000도**, 그립축 ⟂ 실제 덱면 **90.000000000도**,
  스톡 Base PS solid 7개 무변화, 9자세(중립/±10 X/Y/코너4) 이동부 간섭 **전부 0**,
  전장 간섭 0, 캐리어<->하우징 0, **하방 인출 0~100mm 무충돌**, C1/C2 드라이버 120mm 무간섭.
  **최종:** 덱->HAND_REF **55.8785** (docs/05 목표 55.879 와 일치),
  지면->HAND_REF **161.0208**, 덱->피벗 **52.9823**, 덱 아래 돌출 **116.3076**,
  전체 높이 122.3076, 풋프린트 130x130, 최소 구조벽 6.000.
  docs/05 대비 돌출 +1.533 은 **docs/05 가 USB 를 빼고 Base 만 쟀기 때문**이고,
  지면->HAND_REF +7.734 는 거기에 `#usb_clearance` 6.0 이 더해진 것이다 (모델 차이 아님).
  **중간 결함 1건:** 하우징 꼬리 슬롯을 `BASE_BOT-1` 에서 끊어 하방 인출이 t=4.0mm 에서
  막혔다 (Base 꼬리가 -Y 벽 살에 박힘) -> **슬롯을 지면까지 관통**시켜 해소.
  **경량화:** 스커트 창 + 벽 9->6mm 로 하우징 471,933 -> **271,171mm3 (-42.5%)**.
  **프린트:** 캐리어 평판(서포트 0.9%), 하우징은 지면(20도) 베드 권장(10.1%, 높이 122.3mm)
  또는 덱면 베드(5.1%, 153.8mm). 분할 불필요.
  **기술부채:** `GET /features` 429 (Retry-After 23,400s) 로 재생성 상태 직접 확인 보류.
  간접 확인 완료 (POST featureStatus OK / parts solid 2 wire 0 / bodydetails SOLID /
  massproperties 부피가 메시 적분과 일치).
  **스프링·홀·베어링·샤프트·전자 인클로저·중력보상 전부 미착수 (지시대로).**
  **FS 교훈 5건 추가:** (1) `id + "platea"` != `id + "plate" + "a"` — 헬퍼가 만든 body 를
  호출부에서 찾을 때 결합 방식을 맞춰야 한다 (2) `tessellatedfaces` 응답 스키마가 2종이고
  신형(`BTExportTessellatedFacesResponse-898`)은 body 가 `j["bodies"]` 아래,
  vertices 가 dict 다. **최상위 `facetPoints` 는 비어 있어 "빈 응답" 으로 오판하기 쉽다**
  (3) 외부 표준부품 문서(나사)는 `/m/` `/v/` 모두 빈 tessellation -> transform 만 쓰고
  치수는 규격으로 (4) 어셈블리 instance name 에 `" <1>"` 인스턴스 번호가 붙는다
  (5) **`rot_angle(Rb.T @ R)` 로 FIXED/MOVING 을 분류할 수 없다** — 그 값은 편향이 아니라
  부품 로컬 방향까지 포함한 절대 방향차다 (마그넷이 110도로 나온다).
- 2026-08-21: **커스텀 짐벌 개발 중단 확정. 스톡 짐벌 컨포멀 매립 하우징 완료
  -> `lower_adapter/docs/07`. 검증 26/26 PASS. `CUSTOM_GIMBAL = NOT ALLOWED`.**
  체크포인트 `PRE_CONFORMAL_STOCK_EMBED` (`ab593a676cb73163260c50e5`),
  결과 버전 `CONFORMAL_STOCK_EMBED_V1` (`42a15b14ff576623e223b7c6`).
  신규 Part Studio `OneGrip_ConformalHousing` (`8945f7ac4100dfd52a8c8dba`) +
  Feature Studio `OneGrip_Conformal_FS` (`c7e1406e3a3a24817beb0e7b`). body 2개:
  `CONFORMAL_HOUSING` `JHD` 495,615mm3 / `BOTTOM_CARRIER` `RdKD` 90,178mm3.
  **상체 Joystick / 스톡 Base Part Studio 쓰기 0건.**
  `EMBEDDED_GIMBAL_V1` / `STOCK_CARTRIDGE_V1_VALIDATED` / docs/03~06 전부 무수정 보존.
  **구조 전환:** 얇은 덱 + 매달린 카트리지 -> **20도 경사 두꺼운 중공체 자체가 짐벌을
  담는 체적**. 공동은 상자가 아니라 **Z 밴드 10단 컨포멀**이다.
  **§17 포락선 최적화의 결정적 발견:** OneGrip 은 Pitch post 에서 뽑히는 별도 모듈이므로
  정비 순서를 "그립 먼저 탈거 -> 바닥 캐리어 제거 -> 짐벌 하강" 으로 정의하면
  인출 스윕에서 그립 쉘을 뺄 수 있다. 필요 포락선 부피가
  **751.4 -> 266.3 cm3 (단일 상자 1336.7 대비 -80.1%)**. 이 정의 하나가 하우징 크기를 지배했다.
  **최종 측정:** A 경사면->HAND_REF **55.8785** (thin-deck 와 동일),
  B 지면->HAND_REF **161.0208**, C 스톡최저->하우징바닥 **6.0000(안쪽)**,
  **D STOCK_PROTRUSION_BELOW_FINAL_HOUSING = 0.0000mm** (§19 "excellent"),
  E 공동 104x109x94.1, F 외형 128.6x170.6x**139.9**, G 접지 128.6x97.3 (3,176mm2),
  H 피벗->경사면 52.9823, I 벽 5.0 (스커트 5.0 / 플랜지 7.0). 캐리어 118x123x9.
  **§20 변형 3안 (스톡 동일, A/B/D/H 전부 동일):** COMPACT 322,198mm3 (허리 허용,
  접지 2,920mm2, 수평 단 최대 13mm 로 서포트 필요) / **BALANCED 채택 495,615mm3**
  (단조 테이퍼, 접지 3,176mm2) / FULLY_ENCLOSED 537,090mm3 (무릎 절단 없음, 접지 5,964mm2).
  부피는 **솔리드 부피**이고 FDM 실소요는 인필에 좌우된다 — BALANCED 의 두꺼운 중간부는
  인필로 비는 영역이라 실제 재료 차이는 부피 차이보다 훨씬 작다.
  **검증 26/26:** 경사외피 vs 수평 **20.000000000도**, 그립축 ⟂ 실제 외피면
  **90.000000000도**, 스톡 Base PS solid 7개 무변화, 9자세 이동부 간섭 전부 0,
  전장 0, 캐리어<->하우징 0, **하방 인출 0~100mm 무충돌**,
  **지지 평면 아래 스톡 정점 0**.
  **중간 결함 4건 (전부 불리언 위상):** (1) `BaseFill` enum 제거 시 블록이 반쯤 남아 깨짐
  (2) 밴드를 하나씩 빼면 `BOOLEAN_NON_MANIFOLD_RESULT` -> **도구를 먼저 UNION 한 뒤
  한 번에 SUBTRACT** (3) 외피를 "위쪽 최대"로만 잡아 Z 경계에서 **두께 0 칼날 모서리**
  (밴드2 y0=-25 가 한 밴드 위 외피면과 정확히 동일, Z=-126) -> 외피 규칙을
  **한 밴드 아래까지 포함**으로 변경 (4) 덱 개구부 테이퍼 마지막 단 실패 ->
  최상단 두 밴드 병합해 곧은 개구부 92x89.
  **검증 도구 결함 1건:** 복셀이 인서트 ⌀4 원기둥 **접선에 정확히** 놓이면 공유 모서리를
  스쳐 같은 t 가 2번 잡혀 레이 패리티가 뒤집힌다 (실측 `t=[3.043,3.043,11.043,11.043,18.0]`).
  `inside_mesh` 에 **교차점 중복 제거** 추가 -> 오탐 2건 해소.
  **기술부채:** `GET /features` 429 (Retry-After 20,887s) 로 재생성 상태 직접 확인 보류
  (간접 확인 완료). 진단용 `#trace_steps` 변수가 트리에 남아 있다(값 0 = 전체 실행).
  `#usb_clearance` 6.0mm 와 M3x22 / M3 인서트는 여전히 provisional.
  **외관 마감 / 배터리 / MCU 재배치 / 버튼 재설계 / 스톡 내부 수정 전부 미착수 (§24).**
  **API 교훈 2건:** (1) **`POST .../featurescript` 평가 엔드포인트는 `GET /features` 와
  다른 레이트 버킷이다** — 429 상황에서 오류 메시지를 얻는 유일한 경로.
  단 **최상위 선언 불가**(단일 함수 표현식만), `queries` 는 배열이 아니라 **map** 이어야 한다
  (2) 피처에 **단계 제한 변수**(`#trace_steps`)를 두면 POST 의 OK/ERROR 와 `/parts` 개수만으로
  실패 지점을 이분 탐색할 수 있다.
- 2026-08-21: **W2 손목 받침 인체공학 외피 -> `lower_adapter/docs/08`. 검증 28/28 PASS.
  단, Onshape API **402 (API limit exceeded)** 로 마지막 단계에서 중단 — 결과 버전 미생성.**
  체크포인트 `PRE_ERGO_SHELL` (`8099b51b080d7e6963fb0068`).
  신규 Part Studio `OneGrip_ErgoShell` (`a2e4739a4d624b06dee5abba`) +
  Feature Studio `OneGrip_Ergo_FS` (`0e8c283852c78f4b37cddc06`).
  `ERGO_SHELL` 634,810mm3 + `BOTTOM_CARRIER` 90,178mm3 (코어와 동일).
  **코어(CONFORMAL_STOCK_EMBED_V1) 는 상수로 재사용만 했고 쓰기 0건.**
  스톡 짐벌 PS / 상체 Joystick PS / `OneGrip_ConformalHousing` 전부 무수정.
  **핵심 기하: 손목면은 20도 평면 위에 놓을 수 없다** — 그 평면은 -Y 로 1mm 갈 때마다
  0.342mm 떨어져서, 상부 외피를 85mm 앞으로 늘리면 손목 자리가 29mm 낮아진다.
  그래서 `#wrist_pad_angle`=7도 의 **더 완만한 별도 평면**을 덱 평면 위에 얹었다
  (앵커 Y=-20/Z=-61.8785 -> 앞끝 Y=-103.44/Z=-42.61, 법선 (0,0.2251,0.9744)).
  조작 영역과 무충돌: ±10도 그립 스윕의 -Y 한계가 덱에서 Y=-10.51 이고 위로 갈수록
  -Y 로 물러나는데, 쐐기의 최대 Y 가 -20 이라 **어느 높이에서도 교차하지 않는다.**
  **계단식 밴드 스택 -> 로프트 연속 곡면.** 메인 14 스테이션 (각 스테이션 = 그 Z 주변
  창의 공동 최대 + 벽 5.0), 손목 넥 5 스테이션, 패드는 rounded prism 을 패드 평면으로 절단.
  스테이션 간 선형 보간이 항상 `공동+5.0` 이상임을 0.5mm 간격 전수검사 (위반 0).
  **측정:** A 경사면->HAND_REF **55.8785** (코어와 동일), B 지면->HAND_REF **161.0208**
  (동일), **HAND_REF 변화 0.000**, D 돌출 **0.0000**, H 52.9823,
  외형 **128.6 x 219.7 x 139.9**, 접지 128.6x146.4 (2,428mm2, 코어 대비 +53%),
  **손목 받침 7,173mm2 @ 7.0000도**, 지면 위 95.9~106.5 / HAND_REF 아래 54.5~65.1,
  받침살 6.0 / 넥살 4.5. 부피 **+139,195mm3 (+28.1%)** (제안 추정 +98,964 보다 41% 큼).
  **USB 는 측면(-X) 인출로 변경** — 앞으로 빼면 손목 밑을 지나고 지면 평면이
  Y=-78.9 에서 채널 바닥을 만난다. 커넥터 앞 12.9mm + -X 75mm, 51 표본 전부 개방.
  **직각(90도) 마이크로 USB 플러그 전제 (provisional).**
  **중간 결함 4건:** (1) `getVariable` 은 **트리에서 앞에 선언된 변수만** 본다 —
  `#edge_fillet` 을 나중에 append 했더니 피처가 ERROR. 피처 삭제 -> 변수 앞으로 -> 재부착
  (2) **패드 평면 절단을 셸 전체에 걸어** +Y 쪽에서 20도 기준면 상부를 통째로 잘랐다
  (최대높이 139.9 -> 118.4). 패드 body 에만 걸도록 수정
  (3) 손목 넥이 통짜라 1,034cm3 -> 아래로 열린 셸로 중공화. 이때 halfSpace 부호를 틀려
  21mm3 만 깎였다 (`halfSpace(n,d)` 를 빼면 `n·p >= d` 가 남는다 — 아래를 남기려면 부호 반전)
  (4) 면적 보고에서 `|cross|` 를 그대로 썼다 — **삼각형 넓이의 2배**. 면적은 나누고
  법선 정규화는 원래 크기로 해야 한다 (섞으면 접지면적이 9배).
  **모서리 라운드는 미적용.** 패드 주변 모든 모서리 일괄 필렛은 R6~1 전부 `FILLET_FAILED`,
  패드 상면 8개 모서리 일괄도 R8~2 전부 실패. **개별 `try silent` 로 돌리면
  앞면/양측면이 R3 로 성공**함을 평가 엔드포인트로 확인했고 코드에 반영했으나
  **402 때문에 실행하지 못했다.** `#edge_fillet` 은 0 인 상태.
  **⚠ 미확인 2건:** 마지막 FS 업로드의 컴파일 여부(내용 POST 성공, featurespecs GET 402),
  그리고 결과 버전 미생성. `#edge_fillet=0` 이라 컴파일만 되면 형상은 검증본과 동일하다.
  쿼터 회복 후 복구 순서는 docs/08 §7 에 적어 두었다.
  **API 교훈: Onshape 는 429(rate limit) 와 별개로 402 `API limit exceeded` 를 낸다.
  402 는 읽기까지 전부 막히고 `Retry-After` 헤더도 없다.**
- 2026-08-22: **로컬 CAD 전환 (Onshape API 사용 중단) + build123d Phase 0/1 완료.**
  사용자 지시로 외피 워크플로를 로컬로 옮겼다. 표준 룰:
  `ONSHAPE_API = FORBIDDEN` / `ONSHAPE_WRITE = FORBIDDEN` / `LOCAL_CAD_ENGINE = build123d` /
  `CUSTOM_GIMBAL = FORBIDDEN` / `STOCK_GIMBAL = IMMUTABLE` / `BOTTOM_CARRIER = IMMUTABLE` /
  `APPROXIMATE_CORE_REBUILD = FORBIDDEN` / `MESH_TO_CAD_RECONSTRUCTION = FORBIDDEN`.
  작업 공간은 `lower_adapter/local_cad/` (venv `.venv-build123d`,
  build123d 0.11.1 / cadquery-ocp-novtk 7.9.3.1.1). 스모크 테스트 7/7.
- 2026-08-22: **build123d 로컬 Phase 1 완료 — W2 인체공학 외피. 검증 22 PASS / 0 FAIL.
  Onshape API 호출 0건 (읽기·쓰기 모두).** 보고서 `lower_adapter/local_cad/reports/01_phase1_ergo_shell.md`.
  레퍼런스 STEP 3개 라운드트립 통과 (bbox 오차 최대 2.0e-11 mm, 상대부피 최대 1.5e-09).
  좌표 정합은 캐리어 포켓 앵커 + Base solid 1개 Kabsch + 축정렬 24회전 탐색으로 유도했고
  정점 최대 편차 **4.32e-14 mm**, 덱 평면 Z 오차 7.0e-06 mm. 손으로 넣은 근사 변환 0건.
  **함정: Part Studio 부품 위치는 layout 위치라 조립 위치가 아니다** —
  `Roll_holder`/`Roll_holder_2`/`Spacer` 가 t=(0.076,-34.826,35.100) 로 동일하고 `Base` 만
  (0.222,-34.539,28.100) 으로 정확히 7.007mm(= Spacer 두께) 차이. 어셈블리를 진리로 두고
  Base solid 하나만 다리로 썼다.
  전략 **B 채택**: `NEW = HOUSING u (SMOOTH_ENVELOPE - CAVITY_PROTECT - CARRIER_SWEEP)` —
  코어 STEP solid 를 원본 그대로 union 하므로 `APPROXIMATE_CORE_REBUILD` 를 구조적으로 피한다.
  산출 `ERGO_HOUSING_W2` 단일 solid, shells 1 / faces 539, BRepCheck valid, 715,118 mm3.
  필렛 FRONT_LIP R2.0x12 / WRIST_SIDE 개별 R2.0x32 / PAD_PERIMETER R3.0x4.
  **인체공학 불변량 3개가 Onshape W2 와 정확히 일치**: 덱->HAND_REF **55.8785**,
  지면->HAND_REF **161.0208**, 스톡 돌출 **0.0000**. 20도 기준면 **20.000000000도**,
  그립 중립축 수직 90도. 캐리어 -Z 인출 0~100mm 무충돌, 9자세 포락선 전부 0/20,130 점.
  W 133.600 / L 197.243 / H 139.857, 손목 7.0도 / 4,833.6mm2.
  **결함 6건 규명 및 수정 (전부 실측으로 특정):**
   (1) 단조 스무딩이 크기만 max 하고 단면 중심을 그대로 둬 +Y 가 22mm 부풀었다 -> bound 기준으로 변경
   (2) **`Plane(origin, z_dir=(0,1,0))` 의 자동 x_dir 이 (0,0,1)** 이라 local x->world Z,
       local y->world X 가 된다. 손목 단면 5개가 90도 돌아간 채 X~-118 로 날아가
       평면 절단에 통째로 잘렸고 **손목이 모델에 아예 없었다**. 축을 못박는 헬퍼로 교체.
       손목 면적 784 -> 4,834 mm2 의 원인이 이것이다
   (3) 스테이션 13->14 에서 깊이가 5mm Z 구간 동안 160->113mm 로 급변(덱 개구부)해
       스플라인 loft 가 overshoot, 바깥/안쪽 곡면이 교차 -> **본체만 `ruled=True`**.
       선형 보간은 균일 인셋을 정확히 보존하므로 벽이 음수가 될 수 없다
   (4) `(E-H-C) u H == (E-C) u H` 인데 앞 형태를 써서 **98.41 x 1.67 x 0.25mm 내부 공동 shell** 잔류
   (5) **오목 모서리 필렛은 재료를 더한다** — 손목 필렛이 캐리어 인출을 201.5mm3 침범.
       필렛 뒤 keep-out 재적용 + 코어 재union 으로 복원
   (6) **`Compound.moved()` 의 위치는 `.children` 에 반영되지 않는다** (`.solids()` 에는 반영).
       프리뷰가 원본 어셈블리 좌표로 나갔다
  **OCC 부울 신뢰성 교훈 3건 (중요):**
   - **Compound 를 피연산자로 주면 조용히 빈 결과**가 나온다. 같은 간섭 검사가
     Compound 138.277 / Solid 0.000 mm3. 모든 부울을 단일 Solid 로 통일할 것
   - **`작은 - 큰` 방향은 신뢰 불가** — `HOUSING - NEW` 가 HOUSING 전체를 그대로 돌려줬다.
     포함 판정은 잘 조건화된 `NEW & HOUSING` 으로 한다
   - **invalid solid 는 이후 모든 부울을 무효화한다.** 0.25mm shell 하나 때문에 전부 빈 결과였다.
     -> `geometry_utils.heal()` 로 단계마다 유효성 강제 (실패 시 STOP)
  **남은 항목:** 동결 코어가 **이미** 갖고 있던 간섭 **138.2772mm3**
  (`Hex_socket_head_cap_screw_M3x16` 머리 4개, Z -133.5). **W2 가 추가한 몫은 0.000000mm3** 이며
  코어는 동결 대상이라 수정하지 않았다. 해당 나사는 M3x22 교체 예정이라 그때 해소될 수 있다.
  손목 면적 측정기가 평면 면만 세어 곡면 상단이 빠진다(정의 차). L 은 Onshape 판 219.7 대비 197.2.
- 2026-08-22: **OneGrip 방향(front/back) 반전 교정. 방향 불변량 10 PASS / 0 FAIL,
  기계 재검증 22 PASS / 0 FAIL. Onshape API 0건, 하부 형상 변경 0건.**
  보고서 `lower_adapter/local_cad/reports/04_grip_orientation_fix.md`.
  **교훈 (일반): 각도 크기 통과 != 방향 통과.** 기준면 20도 / 중립축 수직 90도 /
  HAND_REF / 간섭 0 이 전부 통과하는데도 손잡이가 앞뒤로 뒤집혀 있었다.
  부착 post 단면이 직사각형이라 축 둘레 180도에 대해 자기 자신으로 가고,
  두 방향이 위 검사들을 똑같이 통과하기 때문이다. 대칭 아래 불변인 양만으로
  판정을 끝내지 말고 **비대칭 특징에서 유도한 방향 벡터**를 게이트로 둘 것.
  **ROOT CAUSE = post 물림의 2-fold 모호성 (변환 부호 오류 아님).**
   - assembly->grip 변환은 **옳다.** `align_reference.py` 1단계가 스톡 Base 회전을
     하드코딩 가정(`ts<0`)으로 골랐지만, 실제로 회전을 확정하는 건 **하우징 꼬리 슬롯**
     이고 부울 채점 결과 Rz(180) 간섭 **0.00** / Rz(0) 간섭 **2,621.78mm3** 로
     현재 값이 유일해다. 캐리어 포켓 바닥면은 100.600x100.600(본체만)이라 회전을 못 잡는다
   - 부착축을 두 부품에서 독립 유도해 일치 확인: OneGrip 착좌면 법선
     (+0.007857,-0.097373,-0.995217) / Pitch 상단면 (-0.007857,+0.097373,+0.995217).
     축 = 후자, grip +Z 에서 **5.6061도** (스냅샷 Pitch 편향)
   - 소켓 보어 내벽 4면 평면식 -> **21.0720 x 25.6720 직사각** -> 축 둘레 180도 자기 자신
   - **축은 짐벌 피벗을 지난다**: 통과점이 피벗 직선에서 **0.0068mm**, 축방향 46.982mm
     (기존 기록 46.98 과 일치). 9자세 Pitch 점군 Kabsch 로 교차검증 —
     **전 자세 피벗 이동 0.0000**, 중립 축 **(0,0,1) 정확**, 잔차 <=3.4e-12mm
  **교정 = 축 둘레 180도 강체 회전, OneGrip 상부에만.** 전체 Rz(180) 을 걸지 않았다.
  **방향 불변량 (신규):** `GRIP_FORWARD_VECTOR`(샤프트 PCA 축의 데크 평면 투영) vs
  `WRIST_SUPPORT_DIRECTION`(ERGO-CORE 재료 도심 - 코어 도심). 게이트 = 내적 < 0.
  before **+0.977169** (12.267도, FAIL) -> after **-0.986371** (170.530도, PASS).
  엄지패널 법선으로 교차검증도 같이 뒤집힘 확인.
  **보존 확인:** 착좌면 오프셋차 1.42e-14, 소켓 축 이동 **2.03e-14mm**,
  코어·캐리어 간섭 0->0, 스톡 간섭 0->0, HAND_REF/피벗/스톡Base/캐리어/20도/90도 전부 무변경,
  스톡 돌출 0.0000, 캐리어 -Z 인출 0~100mm 무충돌, 하우징 W/L/H 133.600/197.243/139.857 동일.
  **모션 검사는 TRANSFORMED / CACHED ENVELOPE 다 (DIRECT 아님).**
  캐시에 그립이 들어 있어(덱 위 246만 점) 그대로 못 쓴다 -> 자세별 축 (피벗, B_k·z) 둘레로
  **그립 점만** 회전시켜 `motion_configs_gripfix.npz` 재생성 (회전 점 2,567,430,
  스톡 이동부 점군 완전 무변화). 9자세 전부 0/20,130 점.
  **STOP: 손목 연장 / 외피 재설계 / 필렛 변경 미착수 (지시대로).**
  참고: 이 과정에서 사용자가 "경사 반전 TOP->+Y" 를 한 번 선택했으나
  방향 오류가 더 근본이라 **경사 관련 작업은 중단**했다. `#tilt_direction` 은
  여전히 TOP->-Y 이고, 그 인체공학 근거는 미재유도 상태다 (재개 시 결정 필요).
- 2026-08-22: **전면 지면 블렌드 A/B 안 생성 + 비교. 두 안 모두 23 PASS / 0 FAIL.
  Onshape API 0건. 하부 동결(쓰기 0건), 기존 `ERGO_HOUSING_W2.*` 덮어쓰지 않음.**
  보고서 `lower_adapter/local_cad/reports/05_ground_blend_variants.md`.
  **먼저 현재 결함 2건을 실측으로 규명했다:**
   (1) **손목 앞단이 지면에서 4.5mm 떠 있었다** — 접지가 u=-24.70 에서 끝나는데
       손목은 u=-81.89 까지 뻗은 캔틸레버였다. 원인은 바깥 단면 코너 R16 이
       안쪽 단면(그 높이 반폭 26.45 로 더 넓다)에 통째로 먹힌 것.
       `t = R - sqrt(R^2-(R-NECK_WALL)^2) = 4.88mm` 가 실측 4.41~4.66 과 일치.
       -> 바깥 단면도 지면 아래 20mm 까지 내려 지면 절단이 곧은 구간을 자르게 수정
   (2) 전면 절벽은 등Y 평면이고 20도 경사 때문에 월드 70도로 보이며
       **꼭대기가 밑동보다 33mm 앞으로 나온 오버행**이다. 이게 "블록 붙인 느낌"의 실체
  **길이 예산식 (이번 작업의 지배 제약):** 앞으로 s 나가며 h 내려올 때
  `du = -1.0642*s + 0.364*dh` 이므로 `dh/ds <= 2.923` 이어야 오버행이 안 생긴다.
  앞단 높이가 지면 위 96.2mm 라서 **오버행 제거만으로 s>31mm(전장 약 228),
  45도 접근은 s~117mm(전장 약 314)** 가 필요하다.
  -> **205~220mm 예산 안에서 지면까지 완만하게 내리는 것은 기하학적으로 불가능하다.**
  **A** `h(s)=96.2-2.85s`, s<=18, 3섹션 -> L 215.243 / 오버행 +16.34 / 앞단면 56.44
  **B** `h(s)=max(5, 96.2*(1-s/45)^1.35)`, s<=42, 14섹션 -> L 239.243 / 오버행 **+1.62** /
  앞단면 **13.18** / 접지 3,255mm2(+49.7%) / 서포트 0.123. **추천 = B.**
  폭 133.600 / 높이 139.857 / HAND_REF / 피벗은 세 안 완전 동일.
  **한계도 기록:** 두 안 다 "완만한 경사"에는 도달 못한다 (최대 기울기 A 80.6 / B 83.8도로
  현재 79.4보다 오히려 가파르다). 개선된 것은 기울기가 아니라 오버행 제거 + 지면 접촉 +
  앞단 테이퍼다. 진짜 완만한 블렌드는 전장 약 314mm 이고 손목 패드 높이(96mm) 재검토가 필요.
  **build123d/OCC 교훈 3건 추가:**
   - **multi-section loft 가 조용히 invalid solid 를 낸다.** A 8섹션에서 valid=False 이고
     부피도 882,321 로 구간별 union 940,221 보다 6.6% 모자랐다(형상이 실제로 망가진 것).
     -> **인접 두 섹션씩 loft 해서 union** (`seg_loft`) 로 해결
   - **필렛에서 OCC 가 segfault 로 죽는다** (예외 아님 -> try 로 못 잡는다).
     ruled 이음매(BLEND) 그룹에서 발생 -> 그 그룹은 제외. 그룹 실패 시 이분 분할로
     되는 부분집합만 살린다 (개별 재시도는 O(n^2) 라 느리다)
   - **실루엣을 정점만으로 샘플하면 안 된다.** 큰 평면은 내부에 정점이 없어 h_max 가
     0 으로 튄다 -> 삼각형 면 위 균등 샘플(`surf_points`)로 교체
  모션 검사는 `motion_configs_gripfix.npz` 사용 = **TRANSFORMED / CACHED ENVELOPE**.
  **STOP: 사용자 선택 대기. STL / 손목 연장 Phase 1.1 / 나사 재설계 미착수.**
- 2026-08-22: **SIDE 하부 프로파일 우선 방식으로 지면 블렌드 A/B 재생성. 두 안 23 PASS / 0 FAIL.
  Onshape API 0건. 상부 실루엣·그립 방향·하부 기구 무수정.** 보고서
  `lower_adapter/local_cad/reports/07_side_profile_ground_blend.md`.
  **접근 정정:** 직전 라운드(docs 05)는 **윗면을 내려서** 길이 예산에 부딪혔다.
  이번엔 윗면을 그대로 두고 **밑면만** 채우는 문제로 바꿨고 그게 옳았다.
  **설계를 가능하게 한 식:** 등Y 단면을 (u,h) 로 보내면
  `h = 2.92397*y - 2.74766*u + 171.326109`, `z = (0.9397*y - u)/0.342`.
  즉 **등Y 평면은 (u,h) 에서 정확히 70.0도 직선**이고(전면이 월드 70도로 보이는 이유),
  덕분에 하부 프로파일 f(u) 만 주면 각 단면 bottom Z 를 이분법으로 직접 풀 수 있다.
  `side_profile.zbot_for_y` 가 그것이다 (loft 결과에 맡기지 않음).
  **현재 실측:** 앞끝 u -81.89 / 첫 접지 u -24.89 / floating span 57.00 /
  하부 최대각 **71.23도**.
  **2D 프로파일** (단조 3차 Hermite, Fritsch-Carlson 직접 구현. 마지막 두 점을 h=0 으로
  두 번 둬 지면 접촉 기울기 정확히 0):
   A (-81.89,5)(-76,3.2)(-70,1.6)(-64,0.5)(-60,0)(-50,0)
   B (-81.89,5)(-78,3.6)(-73,2.0)(-69,0.8)(-67,0)(-55,0)
  **3D 실측 결과:** 전장 227.636 / 폭 133.600 / 높이 139.857 (두 안 동일, 폭·높이 불변).
   A 첫 접지 u **-63.79** / float **18.10** / 하부 최대각 **19.38도** / 접지 2,981mm2
   B 첫 접지 u **-68.10** / float **13.79** / 하부 최대각 **27.57도** / 접지 3,018mm2
   (현재 W2: -24.59 / 57.30 / 71.33도 / 2,175mm2).  **추천 = B** (목표 12~17 중앙, 접지 최대).
  손목 상면 4,916.7mm2 / 7.0도, HAND_REF·피벗·20도·90도·스톡 돌출 0 전부 불변.
  **결함 1건과 수정:** 뜬 립 구간과 지면 구간의 중공 전환을 `s=clamp((2-h)/1.8)` 로
  **바깥 밑면까지 블렌드**했더니 전환 구간 밑면이 프로파일보다 낮아져 지면에 일찍 닿았다
  (접지 -60 -> **-70.9**, 하부 최대각 15.8 -> **84.4도**). 불연속은 지면 아래에서만
  생기고 지면 절단이 지우므로 **하드 스위치(hp<=0.05)** 로 교체해 해소.
  **측정 지표 정정:** 하부 최대각을 전 구간에서 재면 두 안 다 84.4도가 나오는데
  그 지점은 **u=-35.9 의 국소 노치 = 동결 코어의 스톡 전장 꼬리 관통 슬롯**이다.
  블렌드와 무관하므로 지표를 **앞끝~첫 접지 구간**으로 한정했다.
  **작업 함정 1건:** 백그라운드 체인을 `until grep -q "출력:" <로그>` 로 걸었더니
  **이전 실행 로그가 남아 있어 조기 발동**했다(낡은 STEP 에 검증을 돌릴 뻔). 로그 내용을
  완료 신호로 삼지 말 것 — 산출물 타임스탬프로 확인해야 한다.
  구 안(윗면 강하식)은 `ERGO_HOUSING_W2_TOPDROP_A/B.*` 로 보존.
  **STOP: 사용자 선택 대기. STL / WRIST_SIDE 필렛 재적용 / GROUND_TRANSITION_EDGE 필렛 미착수.**
- 2026-08-22: **GROUND B 를 최종 외피로 확정하고 제조용 export 완료. 검증 23 PASS / 0 FAIL.
  Onshape API 0건. 형상 재설계 없음 (모서리 마감 + 검증 + export 만).**
  보고서 `lower_adapter/local_cad/reports/08_ground_b_final.md`.
  **필렛 selector 를 이면각으로 판별하게 바꾼 것이 핵심이다.** 기존 `WRIST_SIDE`
  (|X|>30, 208~210개)를 좁혀 좌우 접촉 외곽 4+4개를 뽑았더니
  **이면각이 정확히 0.000도** 였다 — `seg_loft` union 이 평면 위에 남긴 **인공 이음매**이지
  물리적 모서리가 아니다. `PAD_PERIMETER` 후보도 대부분 같았다. 즉 R2.0/R1.5 필렛이
  전부 실패한 것이 **정상**이다 (상면은 평평하고 좌우는 R16 라운드라 깎을 모서리가 없다).
  -> selector 에 **이면각 5도 미만 제외** 조건 추가.
  적용 결과: `GROUND_TRANSITION`(이면각 70.4~71.4도) **R1.0 x 6**,
  `PAD_PERIMETER` **R3.0 x 1**. `FRONT_LIP`(78~83도)은 R2.0/1.5/1.0 전부 실패 -> 미적용.
  **OCC segfault 재발:** `FRONT_LIP` 이분분할에서 exit 139. 예외가 아니라 프로세스가
  죽으므로 try 로 못 잡는다 -> `FILLET_PLAN` 에 **그룹별 분할 허용 플래그** 도입.
  **최종 수치:** W 133.6000 / L 227.4551 / H 139.8569 / 부피 732,064mm3 /
  faces 428 / edges 1180 / valid / shells 1 / sliver 0.
  첫 접지 u **-68.1086** (목표 -68.10, 차 0.009), floating **13.7814** (목표 13.79, 차 0.009)
  -> §5 접지 +-1mm 기준을 0.01mm 로 통과. 접지 면적 3,017.48mm2, 손목 4,910.60mm2 @ 7.0도.
  HAND_REF / 피벗 / 20도 / 90도 / 스톡 돌출 0 / 캐리어 인출 / 9자세 모션(TRANSFORMED
  CACHED) / 신규 나사 간섭 0 전부 유지.
  **측정 버그 2건 규명·수정:**
   (1) `measure()` 가 히스토그램 **bin 중심 좌표를 u 로** 써서 접지 -69.89 / floating 12.00
       을 보고했다. 실제 점 기준으로 고치니 -68.11 / 13.78 (목표와 0.01mm 이내)
   (2) 살두께 레이캐스팅이 **자기 인접 삼각형**을 맞아 0.054mm 를 냈다.
       시작점 오프셋 0.05 + t 하한 0.2 로 수정
  **최소 살두께:** 신규 스커트 **중앙 5.001mm** (설계 nominal 5.0 과 일치), 최소 0.250mm.
  최소값 지점은 전부 **지면 접촉선**(h~0.07) — 밑면이 15~28도로 접근하다 지면 평면에
  잘리므로 접촉선에서 두께가 0 으로 수렴한다. **near-tangent 요구의 필연적 결과**다.
  그 밖 얇은 지점(h 45~47)은 동결 코어 쪽이라 범위 밖.
  **미해결 2건:** (a) STL 경계 모서리 1 + 비다양체 1 (watertight False).
  **tessellation 밀도와 무관** — `BRepTools.Clean_s` 후 0.010(300,635 삼각형)과
  0.030(33,149)이 동일 결과. 위치 (22.19,-130.09,-121.58) u -80.66 h 12.58 로
  `GROUND_TRANSITION` 필렛 자리와 정확히 겹친다(좌측은 무결함). STEP/BREP 마스터는
  BRepCheck valid 이고 규모가 삼각형 1개 크기라 슬라이서가 자동 복구한다.
  (b) `FRONT_LIP` 필렛 미적용.
  **OCC 교훈 추가: `BRepTools.Clean_s` 로 기존 tessellation 을 지우지 않으면
  `export_stl` 의 tolerance 가 무시된다** (삼각형 수가 그대로다).
  **산출물:** `ERGO_HOUSING_W2_FINAL.{step,brep,stl}` (STL tol 0.015/ang 0.08,
  110,849 삼각형, mm), `BOTTOM_CARRIER_FINAL.{step,stl}` (동결 STEP 그대로,
  부피 90,177.998830 완전 일치, watertight True),
  `ONEGRIP_FINAL_LOCAL_PREVIEW.step` (부품 분리 유지),
  `preview/FINAL_B_{SIDE,ISOMETRIC,TOP,FRONT,BOTTOM,CUTAWAY}.png`.
  보존: `ERGO_HOUSING_W2.step`, `GROUND_A.*`, `TOPDROP_A/B.*`.
  **STOP: 손목 길이 재설계 / 그립 방향 / 경사 방향 / M3 나사 / 전장 재배치 / 배터리 /
  버튼 전부 미착수 (지시대로).**
- 2026-08-22: **FINAL STL watertight 원인 격리 완료 -> 제조용 `ERGO_HOUSING_W2_PRINT_FINAL` 확정.
  검증 23 PASS / 0 FAIL 유지. Onshape API 0건. 형상 재설계 0건 (R1.0 필렛 제거 외 변경 없음).**
  보고서 `lower_adapter/local_cad/reports/09_stl_watertight_isolation.md`.
  **원인 = `GROUND_TRANSITION` R1.0 필렛으로 확정.**
  A/B: F1(R1.0 유지) faces 428 / vol 732,081.2860, F0(R1.0 OFF) faces 409 / vol 732,223.7555.
  차이는 필렛 하나뿐(부피 -142.4695, face +19).
  **STEP 왕복 -> `Clean_s` -> 동일 tolerance(0.015/0.08) 라는 동일 조건에서만 갈렸다:**
   F1 삼각형 110,849 / 경계 1 / 비다양체 1 / watertight False
   F0 삼각형  67,722 / 경계 0 / 비다양체 0 / watertight **True**
  결함 좌표 (22.19,-130.09,-121.58) u -80.66 h 12.58 이 필렛 대상 모서리
  c=(+-20.45,-131.94,-123.07) h[5.01,16.11] 와 겹치고 **좌측엔 결함 없음**(비대칭).
  **함정 2건 (첫 A/B 가 "둘 다 watertight" 라는 오답을 냈다):**
   (1) 비교 조건이 섞였다 — BREP 지표는 STEP 에서, STL 지표는 **build 결과에서 바로 만든
       파일**에서 읽었다. 동일 조건 비교가 아니었다.
   (2) **`export_all` 이 STEP 을 쓰기 전에 tessellation 을 지우지 않아 STEP 에 메시가
       섞여 들어갔다** — edges 가 1,180 대신 **165,939**(삼각형 수의 1.5배)로 보고됐다.
       `BRepTools.Clean_s` 를 STL 직전에서 **STEP 이전으로** 이동해 해결.
  **제조용 최종:** solid 1 / shells 1 / faces 409 / edges 1143 / BRepCheck valid /
  vol 732,223.7555 / bbox 133.6000 x 227.6362 x 146.0911.
  **STL acceptance 전항목 통과**: 삼각형 67,722 / 경계 0 / 비다양체 0 / **degenerate 0** /
  watertight True / 단위 mm.
  **검증 유지:** 첫 접지 u **-68.1086**, floating **13.7814**, 앞끝 u -81.8900,
  접지 3,017.4800mm2, W 133.6000 / H 139.8569 불변 (L 은 필렛 제거로 227.4551 ->
  **227.6362**, 필렛 전 원형값), HAND_REF 55.8785 / 161.0208, 스톡 돌출 0,
  캐리어 인출 PASS, 9자세 모션 PASS(TRANSFORMED/CACHED), 신규 나사 간섭 0.
  최소 살두께 신규 스커트 중앙 5.257mm / 최소 0.487mm(지면 접촉선, near-tangent 필연).
  **산출물:** `ERGO_HOUSING_W2_PRINT_FINAL.{step,brep,stl}`,
  `BOTTOM_CARRIER_FINAL.{step,stl}`(동결 STEP 그대로, 부피 90,177.998830 일치),
  A/B 산출물 `TEST_F1/F0.*` 보존. 이전 `FINAL.*` 및 `GROUND_A/B.*` `TOPDROP_A/B.*` 도 보존.
  **미착수:** `FRONT_LIP` 필렛(§9 대로 유지), 프리뷰/조립 프리뷰 갱신
  (기존은 필렛 있던 FINAL 기준. 차이가 필렛 하나뿐이라 실루엣 구분 불가).
- 2026-08-22: **25도 단일 연속 경사 + 랩 스커트 = 최종 확정. 검증 23 PASS / 0 FAIL.
  Onshape API 0건.** 보고서 `lower_adapter/local_cad/reports/10_25deg_wrap_final.md`.
  **설계 전환 3단계:** (1) 지면 블렌드 A/B -> (2) 램프 40/30도 -> (3) **단일 연속 경사**.
  사용자가 "중간 턱 불필요" 를 지적해 7도 손목 패드를 없애고 한 면으로 통일했다.
  **핵심 기하: 하우징 상면(덱)이 이미 20도로 앞으로 내려간다.** 그래서 그립 능선에서
  20도보다 가파르게 내리면 하우징 위 구간에서 덱 밑에 묻혀 형상이 2조각으로 갈린다
  (실측 확인). 기준점을 **하우징 앞끝 상단**(u -55.87, h 85.67)으로 잡아야 하고,
  그때 20도면 꺾임 0, 25도면 (theta-20)=5도 만 꺾인다.
  경사면 상단은 `min(ramp_z, DECK)` 로 **덱에서 잘라** 하우징 상면과 단차 0 으로 맞췄다
  (그 전엔 Y=-15 에서 6.3mm 튀어나왔다).
  **랩 스커트:** 하우징 외곽선(R14)을 지면까지 내려 옆·뒤를 덮는다. 20도 경사라
  뒤가 22~55mm 떠 있던 것을 메운다. 캐리어(X +-59) 인출 통로만 0.5mm 여유로 비웠다.
  접지 3,017 -> **11,173mm2 (3.7배)**, 후방 지지팔 65.8 -> **131.3mm (2.0배)**.
  **무게추는 채택하지 않았다.** 팔을 5N 만 얹어도 뒤로 17.6N 을 버틴다(무게추 없이).
  300g 추가는 팔 뗀 상태(8.2->13.9N)만 개선하는데 총 931->1,231g 이 되고 인쇄 중
  일시정지가 필요하다. 누워 쓰는 용도라 가벼운 쪽이 낫다.
  **최종 수치:** L 365.760 / W 133.600 / H 140.524, 부피 934,074mm3,
  질량 289.6g(인필 25%), 팔 지지면 **11,631mm2**(투영 10,270, 평균경사 28.0도),
  접지 11,173mm2, 최전방 u -227.18 / 최후방 접지 u **+162.18**, 도심 u +30.87.
  덱->HAND_REF 55.8785 / 지면->HAND_REF **161.0208** / 스톡 돌출 0 유지.
  **STL: 62,368 삼각형, watertight True, 경계 0 / 비다양체 0 / degenerate 0 / mm.**
  BREP solid 1 / shells 1 / faces 572 / valid.
  **측정기 교정 3건:**
   (1) `wrist_area_mm2` **폐기** — 7도 패드 평면 face 를 찾는 방식이라 25도 구조에서
       구조적으로 0 이 나온다. `ARM_SUPPORT_SURFACE_AREA` 신설.
       **이전 보고 31,685mm2 는 틀렸다** (모델 전체의 위를 향한 면을 세서 덱·후방 포함).
       실제 팔받침은 **11,631mm2** 이고 173x70mm 와 일치한다
   (2) 캐리어 여유를 **bbox** 로 재서 0.0042mm 라는 무의미한 값이 나왔다. 캐리어를
       실제로 옆으로 밀어 재니 **0.3 < clearance <= 0.5mm** 로 설계값과 일치
   (3) CUTAWAY 를 삼각형 **중심**으로 잘라 절단면 걸친 삼각형이 뾰족하게 튀었다
       -> 세 정점이 모두 한쪽인 것만 남김
  **void 감사:** 렌더를 믿지 않고 SIDE 광선 투영 + 바깥 flood fill 로 판정.
  159x59 격자(2.5mm)에서 **내부 void 0 칸**. (앞서 실제 구멍을 렌더 아티팩트로
  오판한 전력 때문에 도입했다.)
  **스커트 구현에서 6번 걸렸고 전부 다른 원인:** 조각 분리를 STOP 으로 오판 /
  무릎 절단부(하우징 최저 -146.96)와 41mm 안 닿음 / **Compound 부울**(하나씩 더하면
  new 가 Compound 가 돼 이후 부울이 조용히 틀린다 — 이전에 기록해 둔 함정을 재발) /
  **sk_bot 을 앞쪽 Y 기준으로 잡아 뒤에서 44mm 못 미침**(지면이 가장 낮은 곳은 뒤쪽) /
  캐리어 여유 0 으로 접촉면 1.061mm3 잔류 / **keep-out 재적용 순서**(스커트를 필렛·
  keep-out 처리 뒤에 붙여 그 처리를 못 받음). 매번 heal 의 "solid 여러 개면 STOP"
  규칙과 23게이트가 잡았다.
  **heal 개선: 내부 공동을 부피가 아니라 최소 두께(2mm)로 판별한다** —
  101.6 x 3.77 x 1.19mm(58.8mm3) 짜리 종잇장 공동이 부피 임계값을 넘겨 통과했었다.
  **export_all 개선: STEP 을 쓰기 전에 `BRepTools.Clean_s`** — 안 하면 STEP 에 메시가
  섞여 edges 가 1,180 대신 165,939 로 보고되고 `export_stl` 의 tolerance 도 무시된다.
  **산출물:** `ERGO_HOUSING_25_WRAP_FINAL.{step,brep,stl}`,
  `BOTTOM_CARRIER_FINAL.{step,stl}`, `ONEGRIP_25_WRAP_FINAL_PREVIEW.step`(분리 유지),
  `preview/FINAL25_{SIDE,ISOMETRIC,TOP,FRONT,REAR,BOTTOM,CUTAWAY}.png`.
  이전 산출물 전부 보존.
  **STOP: M3 나사 재설계 / 전장 / 배터리 / 버튼 / 상부 손가락 형상 미착수.**
- 2026-08-22: **25° 랩 스커트 접합부 폭 정합 = 최종 V2. 23 PASS / 0 FAIL, STL watertight.
  Onshape API 0건.** 보고서 `lower_adapter/local_cad/reports/11_25wrap_final_v2.md`.
  하우징 ↔ 팔받침 접합부에서 TOP 실루엣이 **11.8mm 단차**로 튀었다. 원인은 폭 스케줄
  끝점을 하우징 **뒤끝**(Y=-15)에 걸어 하우징 앞면(Y=-81.8)에서 아직 0.91배(121.8mm)였던 것.
  끝점을 `y_front_body` 로 재앵커 -> 접합 구간 증분 5.74 -> **1.34mm/6mm**, Y=-80 에서
  133.60 도달 후 연속. **형상 변경은 이 한 곳뿐** (경사 25° / 스커트 / 덱 캡 / 필렛 무수정).
  **STL 결함 규명:** 기본 tol 0.015 에서 경계 모서리 6개 -> 위치가 전부
  **Z=-61.8785 (덱 평면 정확히), Y=-18** 이었다. 경사면 상단을 `min(ramp_z, DECK)` 로
  덱에 **정확히** 맞춰 잘라 동결 코어 상면과 완전 동일 평면이 되고, 폭 확대로 그 구간이
  커지면서 두 면의 tessellation 이 갈라진 것. tol 0.008/0.010/0.015/0.020 전부 실패,
  **0.030 부터 watertight** -> 형상 무수정으로 tol 만 0.030 채택 (0.03mm chord 편차는
  FDM 레이어 0.1~0.2mm 보다 훨씬 작다).
  **결과:** BREP solid 1 / shells 1 / faces 514 / valid True / 997,304.107mm3,
  STL 삼각형 20,016 / 경계 0 / 비다양체 0 / degenerate 0 / **watertight True**,
  광선 void 감사 내부 void **0칸**, 23게이트 **PASS 23 / FAIL 0**
  (기준면 20.000000000°, 중립축 ⟂ 90°, 덱→HAND_REF **55.8785**, 지면→HAND_REF **161.0208**,
  스톡 돌출 **0.0000**, 캐리어 -Z 인출 0~100mm 충돌 0, 9자세 전부 0/20,130,
  새 외피가 추가한 나사 간섭 0.000000mm3).
  캐리어 측방 실여유 **0.3 < c <= 0.4mm** (±0.3 무충돌 / ±0.4 4방향 접촉).
  보고된 `min_horizontal_clearance 0.0211` 은 **bbox 기준이라 무의미** — 실외형으로 재야 한다.
  **V1(폭 86) 대비:** 부피 934,074 -> **997,304mm3**, 질량 289.6 -> **309.1g**,
  팔 지지면 11,631 -> **20,340mm2 (+74.9%)**, 평균 경사 28.00 -> 26.82°,
  도심 u +30.87 -> **+21.82** (앞으로 9mm), 후방 지지팔 131.31 -> **140.36mm**.
  L/W/H **365.760 / 133.600 / 140.524** 로 외형 치수는 무변화.
  산출물 `ERGO_HOUSING_25_WRAP_FINAL_V2.{step,brep,stl}` +
  `ONEGRIP_25_WRAP_FINAL_V2_PREVIEW.step` + `preview/W134_*.png`.
  **이전 `ERGO_HOUSING_25_WRAP_FINAL*` 은 전부 보존.** 조립 프리뷰 파일명을 base 에서
  유도하도록 고쳐 V1/V2 가 서로 덮어쓰지 않는다.
  **STOP: M3 나사 재설계 / 전장 / 배터리 / 버튼 / 상부 손가락 형상 미착수.**
- 2026-08-22: **접합부 관통 슬릿 제거 = 최종 V3. 23 PASS / 0 FAIL, 관통 43.2 -> 0.0mm2,
  STL watertight. Onshape API 0건.** 보고서 `lower_adapter/local_cad/reports/12_25wrap_final_v3.md`.
  사용자가 슬라이서 화면에서 좌우 대칭 흰 슬릿을 지적했다. 세 지표를 따로 재서 정체를 확정:
  실루엣 관통 감사 **앞 부각30도 43.2mm2** (3x14 슬리버 2개), 짐벌 노출은 앞 0도에서 0.2% 뿐,
  수직 광선 스캔에서 **X 58~66.8 구간의 재료 최상단이 Y<=-13 은 -63.6 인데 Y>=-13 은 -129**.
  **원인: 램프 단면이 `y_rear = anchor[0] + 5.0` = Y -15 에서 끝나 바깥 폭이
  133.6 -> 113.0 으로 10.3mm 급히 꺾이고**, 램프의 둥근 코너와 블록 평면이 못 만나
  초승달 슬릿이 남았다. 좌우 대칭인 이유가 이것.
  **폐기 2건:** (1) `sk_top` 을 -140 -> DECK 로 올리기 -> **하우징 중공을 채워** 부피
  997,304 -> 1,762,931 (+77%), shells 3. `prot` 는 짐벌 공동만 보호하고 셸 내부
  (약 3,027,000mm3)는 보호하지 않는다. (2) 램프 단면을 하우징 뒤끝까지 연장 ->
  **동결 코어에서 8.3mm 뜬 이중벽** (Y=+60,Z=-86 의 +X 교차점 `31.0 54.0 | 62.3 66.8`),
  단면 상단 라운드 구간에서 열려 관통 **147.5mm2 로 악화**, 모션 FAIL 4점
  (전부 Y +64.1~64.7 / Z -61.9x = 덱 평면, 스윕 한계 Y +64.85 를 0.2~0.7mm 침범).
  **채택 = 폭 블렌드.** 접합 구간에서 램프 폭을 하우징 폭(113.0)까지 좁힌다
  (`f_end = 113.0/133.6 = 0.846`). Y -227.2 에서 90.8 / Y -81.8 에서 **133.6 (V2 의 접합부
  일치 유지)** / Y -15 에서 **113.0 = 하우징과 동일 -> 단차 0**. 이중벽도 안 만든다.
  **결과:** 관통 감사 부각30도 **43.2 -> 0.0mm2** (부각10/20, 측면 전부 0),
  23게이트 **PASS 23 / FAIL 0**, BREP solid 1 / shells 1 / faces 541 / valid,
  부피 **992,693mm3** (V2 997,284 보다 -4,591 로 오히려 가볍다), 질량 307.7g,
  STL 삼각형 20,446 / 경계 0 / 비다양체 0 / degenerate 0 / **watertight True** (tol 0.030),
  광선 void 감사 내부 void 0칸.
  L/W/H **365.760 / 133.600 / 140.524** 무변화, 덱→HAND_REF **55.8785**,
  지면→HAND_REF **161.0208**, 스톡 돌출 **0.0000**, 캐리어 -Z 인출 무충돌,
  9자세 전부 0/20,130. 팔 지지면 20,332mm2 / 접지 11,266mm2 / 후방 지지팔 140.22mm.
  남은 `앞 0도 5.2mm2` 는 V2 와 **완전히 같은 값**이고 1x3/0x4/1x1mm 짜리 —
  실루엣 래스터가 접선면을 스치는 측정 아티팩트이지 형상 결함이 아니다.
  산출물 `ERGO_HOUSING_25_WRAP_FINAL_V3.{step,brep,stl}` +
  `ONEGRIP_25_WRAP_FINAL_V3_PREVIEW.step` + `preview/V3_*.png`.
  **V2 및 이전 산출물 전부 보존**, 폐기한 시도도 `_FULLSIDE` / `_CONT` 로 남겼다.
  **신규 진단 도구:** `front_hole_audit.py` (실루엣 래스터 + flood fill 로 관통 면적),
  `locate_hole.py` (구멍 픽셀 -> 3D 좌표), `hole_views.py` (**전역 깊이 정렬** 렌더).
  **교훈 4건:** (1) **부품별로 그리는 렌더는 거짓말을 한다** — 나중 부품이 하우징 위에
  덧칠돼 짐벌이 비쳐 보였고 그걸 구멍으로 오판했다. 전 삼각형을 합쳐 한 번만 정렬할 것
  (2) **`FRONT` 라는 이름을 믿지 말 것** — `w = -UH` 는 팔받침 **반대쪽**이다.
  그래서 "정면에 구멍 없음" 이라고 한 번 잘못 보고했다. 방향은 형상에서 유도해 확인할 것
  (3) **구멍을 살로 메우는 방향은 대개 틀린다** — 두 시도 다 중공을 채우거나 이중벽을
  만들었고, 실제 해법은 **단차를 없애는 것**이었다
  (4) 광선 교차점 목록(`31.0 54.0 | 62.3 66.8`)이 이중벽을 한 줄로 드러냈다.
  부피·shell 개수만으로는 못 본다.
  **STOP: M3 나사 재설계 / 전장 / 배터리 / 버튼 / 상부 손가락 형상 미착수.**
- 2026-08-23: **±15도 내부 모션 클리어런스 = 최종 V4. 23 PASS / 0 FAIL.
  Onshape API 0건. 외부 형상 변화 0.** 보고서 `lower_adapter/local_cad/reports/12_motion15_final_v4.md`.
  **각도 세 값을 분리 기록한다 (섞지 말 것):**
   - **DOCUMENTED DESIGN ANGLE = 15도** — `cad_dump/features_Base.json` 마스터 변수
     `#joystick_angle = 15 deg`, 클리어런스 연동(`#offset_around_pitch = 0.2mm x 15 + 1mm`)
   - **STOCK GIMBAL MECHANICAL LIMIT ~= 15도 (부분 확인)** — 고정부(Base/Roll_holder x2/
     Spacer) 대비 이동부(Roll/Pitch/Spring_holder) 회전에서 **Y축이 14도까지 접촉수 33
     으로 완전 평탄, 15도부터 증가**. X축 결과는 무효 (2축 카르단을 강체 회전시킨 것)
   - **V4 HOUSING CLEARANCE LIMIT = 15.88도** — 24방위 최초접촉각 최소 (방위 45/315)
   실사용 허용각은 최소값이 지배한다. 하우징 여유 **+0.88도**, 여기에 포락선 기하 여유
   **1.5mm** 가 **별개**로 있다.
  **문제:** 하부 어댑터 전체가 Onshape 단계에서 **±10도 9자세 캐시**로 설계돼
  동결 코어 공동벽이 X- 12도 / Y± 14도에서 그립을 막았다. **덱 개구부가 아니라
  덱 아래 12~18mm 코어 내부 공동벽**이다 (X-12도 Y+73.0~74.1 / Y±15도 |X|49.1~50.4).
  **내 외피는 무죄** — 동결 코어 단독과 V3 전체의 각도별 충돌 점수가 완전히 동일
  (0/0, 67/67, 148/148, 179/179, 208/208).
  **포락선 방식을 6번 고쳤다:**
   1) 축정렬 bbox(원뿔) 15,906.6mm3 -> **0.4mm 리브** REJECTED
   2) 볼록껍질(원뿔) 7,556.4 -> **코너 4자세 FAIL** REJECTED
   3) 다각형 프리즘 적층(정사각 9x9) 25,444.7 -> **0.8mm 계단 턱** REJECTED
   4) 로프트(정사각 13x13) 32,353.7 -> **1mm 박판** REJECTED
   5) 로프트+smear 2mm 36,654.8 -> 박판 0.027mm 잔존 REJECTED
   6) **로프트+smear 4mm 44,885.1 ADOPTED**
  **핵심 발견 3건:**
   - **도달집합은 원뿔이 아니라 정사각형** `|roll|<=15 & |pitch|<=15`. 코너 (15,15)의
     합성 편향은 `acos(cos^2 15) = 21.06도` 로 반각 15도 원뿔 밖이다. 기존 ±10도 캐시가
     코너 4자세를 포함한 것도 같은 이유. -> 13x13 그리드(169자세, 2.5도)
   - **bbox 밴드는 둥근 포락선의 대각선을 최대 40% 과다 절삭**한다
   - **1mm 밴드 적층은 `1.0-2*PROT_EPS = 0.800mm` 계단 턱**을 남긴다. `min_wall` 이
     정확히 0.800 을 반복 출력한 것이 그것. -> 반경 32각형 + ruled loft (face 1541->1312)
   - 코어 후방 선반(Z -90.00~-80.02, 10mm, 밑면 평면, 아래 공동)을 절삭 곡면이 **접선
     접근**해 1.02mm 박판을 남겼다. smear 2mm 는 접점만 옮겼고(0.027mm) **평면 관통**이
     필요했다 -> 밴드 풀링 `[i-1,i+1]` -> `[i-1,i+4]`
  **결과:** §2 DIRECT 9자세(코너 4개 포함) + 콘24 + 사각경계24 **전부 간섭 0 / 12,000점**,
  §3 최소 최초접촉각 **15.88도**, §5 removed **44,885.1156mm3** 이면서
  **external bbox / SIDE / TOP / FRONT 실루엣 델타 전부 0.000000**,
  §6 **rib(면적형) 군집 V3 0 -> V4 0 / sliver solids 0** (원시 슬랩 <1.5mm V3 123 /
  V4 139 차이는 전부 접선선), §7 solid 1 / shell 1 / valid / faces 1312 / edges 3271 /
  vol **947,875.7535mm3**, §8 **PASS 23 / FAIL 0** (코어 절삭이 포락선 **밖으로 -0.0001mm3**),
  §9 void 앞부각10/20/30 및 측면 전부 0.0mm2, §10 STL 삼각형 25,044 / 경계 0 /
  비다양체 0 / degenerate 0 / **watertight True**.
  덱→HAND_REF **55.8785** / 지면→HAND_REF **161.0208** / 스톡 돌출 **0.0000** /
  W·L·H **133.6000 / 365.7597 / 140.5240** 전부 V3 와 동일.
  **검사 코드 수정 4건:** (1) 게이트가 `housing - ns` 를 써서 OCC 가 코어 전체(495,649)를
  돌려줬다 — 그 함정 주석이 바로 위에 있었는데 밟았다. **교집합만으로** 판정하게 교체
  (2) flood fill 튜플 스택이 1.4M 셀에서 MemoryError -> 정수 인코딩 + px 1400->800
  (3) §6 판정을 원시 카운트에서 **군집 성격(면적형=리브)** 으로 교체 — 이 지표는 접선
  자리를 함께 세고 V3 도 0.121/0.800 을 원래 갖고 있다 (4) §6 접선 스침 필터
  `|n·d| >= 0.35` + 영역조건에 Y 추가 (`덱 0.029mm @ Z -61.89` 는 동일평면 스침,
  `left cavity @ Y -260` 은 팔받침 램프였다).
  **Sanity check:** 수정 검사기로 V3 재실행 PASS 23 / FAIL 0, 수치가 이전과 소수점까지 동일.
  **산출물** `ERGO_HOUSING_25_WRAP_FINAL_V4.{step,brep,stl}` +
  `ONEGRIP_25_WRAP_FINAL_V4_PREVIEW.step` + `MOTION15_REMOVED.{step,stl}`(절삭 체적,
  교집합으로 독립 추출 44,885.1146) + `preview/V4_*.png` + `V3_V4_CAVITY_COMPARE.png`.
  **V3 및 이전 산출물 전부 보존.**
  **작업 함정 4건:** (1) `radial_poly` 광선-변 교차에서 u 부호를 뒤집어 자기교차 다각형
  -> `TopoDS::Face` 타입 오류. 올바른 식 `t=cross(w,e)/cross(d,e)`, `u=cross(w,d)/cross(d,e)`
  (2) **빌드 실패인데 finalize 가 이어 돌아 낡은 STEP 을 V4 로 내보냈다** — 로그가 아니라
  산출물로 확인하라는 기존 교훈 재발. 빌드 성공 확인 후에만 finalize 하도록 분리
  (3) **heredoc 안 `
` 이스케이프가 3회 깨져** 패치가 조용히 실패하고 낡은 파일로 검증이
  돌았다 -> 스크립트는 Write 로 통째 재작성 (4) 함수 사이 블록 치환으로 `hull`/`grow` 를
  같이 지웠다.
  **STOP: deck opening(92.9x89.8 유지) / 외부 형상 / M3 나사 / 전장 / 배터리 / 버튼 /
  상부 손가락 형상 미착수.**

- 2026-08-23: **P1S 2분할 제조 모델 REV D + CAD 통합 희생 support (PRINT_READY) 완료.
  Onshape API 0건. V4 외피 형상 재설계 0건.**
  보고서 `lower_adapter/local_cad/reports/15_p1s_split_print_engineering{,_REV_C,_REV_D}.md`
  및 `16_p1s_custom_support_print_ready.md`.
  **REV D 제조 확정값 (미확정 0건):** heat-set insert pilot **Ø5.2 x 8.0**,
  joint clearance **0.30 mm/side**, M4 관통 **Ø4.5**, 카운터보어 **Ø8.0 x 4.2**,
  나사 **M4 x 10** (잔여 관통 2.8 + insert 8.0 = 10.8). stepped lap overlap 28 mm,
  tapered doubler, rib/groove X +-12. MAIN 852,170.569 / ARMREST 153,747.076 mm3,
  둘 다 solid 1 / shell 1 / watertight. 100 N 최대 사용률 17.7 %.
  **PRINT_READY (이번 라운드):** REV D body 는 **강체 변환만** 했다 —
  부피 차 9.3e-10 / 5.8e-11 mm3, STEP·STL sha256 동일. support 는 부울 융합하지 않은
  **별도 solid** 다. 구조 = solid block 이 아니라 **print X 방향 수직 리브 벽**:
  두께 **0.8 mm**(= 접촉 rail 폭), 피치 **10 mm**, 천장 Z gap **0.20**(PLA / PETG 0.28
  파라미터화), 측면 **0.40**, teeth 접촉 6.0 : 비접촉 3.0 @ 9.0.
  **MAIN** 리브 43개 / 81,493.8 mm3 / 약 101.1 g, build-plate-start 16 + MODEL_ANCHOR 27
  (앵커 neck 은 전부 **0.8 mm x 접촉길이 1.0~113.0 mm**, 전량 비가시 내부면).
  **ARMREST** 리브 1개 / 2,553.5 mm3 / 3.2 g, **앵커 0개**.
  **검증:** **TRUE TRAPPED SUPPORT = 0** (MAIN 23 chunk 전부 DECK_OPENING +Y,
  최소 통과여유 4.4 mm@>=500mm3 / 1.2 mm@10mm3 복셀 잔여물 1개;
  ARMREST 1 chunk UNDERSIDE_OPEN 5.6 mm), **SUPPORT_FOR_SUPPORT 0.441 / 0.000 mm2**,
  제품 침범 최대깊이 **0.0983 mm**(설계 gap 0.20 미만 = 접촉조차 아님, 실침범 0),
  STL 경계 0 / 비다양체 0 / degen 0 / watertight True (multi-shell 허용),
  body-only 재검증 **23 gates PASS 23 / FAIL 0**, **+-15도 전자세 간섭 0**,
  최소 최초접촉각 **15.88도**, 조립 joint 밖 차이 **0**.
  금지영역(외부 팔접촉면 / lap mating / rib·groove / insert pilot 내부 / insert·
  counterbore seating)은 **천장뿐 아니라 바닥(앵커면)에도** 적용 -> 금지면 앵커 0개.
  insert pilot 은 의도적으로 CAD support 없이 **브리지 출력 후 Ø5.2 리밍**.
  brim 5 mm 는 CAD 에 융합하지 않고 슬라이서 설정으로 남겼다.
  **결함 3건 (전부 리브 폴리곤의 x 이음):** (1) 무효 표본을 건너뛰고 이어붙여 직선이
  재료 관통 -> 서브 폴리곤 분할 (2) **천장이 0.5 mm 사이에 38 mm 급락**하는데 바닥이
  같아 run 이 이어져 윗면 대각선이 **12.5 mm 관통** -> `|dB| > 2.0` 이면 run 절단.
  이 2건은 **정점 3개가 전부 바깥**이라 정점 검사로는 안 잡히고 **삼각형 중심 검사**로만
  드러났다 (3) **측정기 결함** — `zp < p_z - 1e-3` 로 아래를 찾아 **표면에 정확히 얹힌
  바닥이 제외**돼 SUPPORT_FOR_SUPPORT 가 746 mm2 로 나왔다. `<= p_z + 0.05` 로 고치니
  0.441. 형상이 아니라 판정식 문제였다.
  **교훈: 삼각형이 재료를 뚫는지 볼 때 정점만 검사하면 놓친다.**
  신규 스크립트 `build123d/custom_support.py` / `support_validate.py` / `print_ready.py` /
  `support_preview.py` / `diag_intrusion.py`.
  산출물 `MAIN|ARMREST_PRINT_READY_PLA.step`, `HOUSING_V4_{MAIN,ARMREST}_PRINT_READY_PLA.stl`,
  `*_CUSTOM_SUPPORT_PLA.{step,stl}`, `*_PRODUCT_ONLY_PLA.step`, preview 7종.
  **REV B/C/D 및 `JOINT_FIT_COUPON` 무수정 보존. G-code 미생성.**
  **STOP: PETG STL / M3·M4 나사 재설계 / 전장 / 배터리 / 버튼 / 상부 손가락 형상 미착수.**
