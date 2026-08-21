# INDEX 버튼 CAD 구현 기록

- 일자: 2026-08-19
- 1차: STEP 0 에서 중단 (WRITE 대상 URL 미지정). CAD WRITE 0건
- **2차: 사용자 승인 후 STEP 1~8 실제 WRITE 수행 — 아래 "2차 실행" 절 참조**

---

## 0. 실행 결과 요약

| STEP | 내용 | 상태 |
|---|---|---|
| **STEP 0** | PRE-WRITE CHECKPOINT | **중단 — 아래 §3 참조** |
| STEP 1 | 신규 변수 | 미실행 |
| STEP 2 | INDEX 기준 geometry | 미실행 |
| STEP 3 | INDEX shell openings | 미실행 |
| STEP 4 | INDEX holder | 미실행 |
| STEP 5 | switch pockets | 미실행 |
| STEP 6 | INDEX caps | 미실행 |
| STEP 7 | 최종 검증 | 미실행 |

**POST / PUT / DELETE 요청을 한 건도 보내지 않았다.**
Adam Simon 원본 문서에도, 사본에도 아무 변경이 없다.

---

## 1. DOMINANT / OPPOSITE SHELL 결정 (RIGHT HAND)

CAD 파트 이름(`Joystick_1` / `Joystick_2`)은 좌우 의미를 담고 있지 않다.
따라서 이름이 아니라 **실측 3D 형상 + 손 해부학**으로 결정했다.

### 1.1 근거 체인

**① 사용자는 −Y 쪽에 있다**

- 엄지 패널 스위치 축 8개 전부 `(0, −0.757, +0.653)` → −Y 이면서 **위(+Z)** 를 향한다
- 그립 전면(−Y) 이 위로 갈수록 앞으로 나온다: Z=−52 에서 Y=−0.12 → Z=+32 에서 Y=−40.37
  = **상단이 −Y 쪽으로 기운 pistol-grip 레이크**
- 두 사실 모두 "−Y = 사용자 쪽" 을 가리킨다

**② 손바닥은 +Y 면, 손끝은 −Y 면**

- 신규 버튼은 −Y 면에 놓인다 (승인된 위치: I3/I4 가 Y ≈ −29.3)
- 버튼을 누르는 것은 손끝이므로 **손끝이 −Y 면**, 따라서 **손바닥은 +Y 면**

**③ 오른손 + 엄지 +Z ⇒ 손가락은 반시계 방향으로 감긴다**

오른손 법칙 그대로다. 엄지를 +Z 로 세우면 손가락은 +Z 에서 내려다볼 때 반시계로 감긴다:

```
   +Y (손바닥)  →  −X  →  −Y (손끝)  →  +X (더 굽히면)
```

**④ 손끝이 도달 가능한 호 구간**

손가락은 −X 쪽에서 감아 들어온다. 즉 중간마디·첫마디가 −X 면을 덮고,
손끝이 전면(−Y)에 닿으며, 더 굽히면 중앙을 조금 넘어 +X 까지 간다.
**폭 47.75 mm 그립을 손끝이 +X 쪽 깊숙이 감쌀 수는 없다.**

승인된 row 범위 `s = −31.5 … +9.5` 가 정확히 이 도달 범위와 일치한다.

### 1.2 결정

| | 파트 | partId | X 범위 | 배치 |
|---|---|---|---|---|
| **DOMINANT_SHELL** | **Joystick_2** | `JfD` | **X < 0** | **I1, I2, I3 (3개)** |
| **OPPOSITE_SHELL** | **Joystick_1** | `JaD` | **X > 0** | **I4 (1개)** |

- `#hand_sign = +1` — docs/03·04 에서 쓴 s 부호를 **그대로 사용**한다 (반전 불필요)
- row center offset −11.0 mm 은 **−X 방향**을 의미한다
- 참고: Joystick_2 는 나사 **탭홀** 쪽, Joystick_1 은 **카운터보어** 쪽이다.
  docs/05 에서 확인했듯 보스 외곽 ⌀7 은 양쪽 동일하므로 holder 여유에 영향 없다

> 왼손 버전은 `#hand_sign = −1` 로 s 부호만 반전하면 된다.
> 그때는 나사 머리 삽입 방향을 함께 결정해야 한다 (docs/05 §5).

---

## 2. STEP 0 — WRITE 대상 검증 결과

사용자 메시지의 WRITE 대상 URL 자리가 **플레이스홀더 그대로**였다:

```
[COPY한 OneGrip_Play_V1 Onshape URL 입력]
```

URL 이 없으므로 지시된 "URL 의 did/wid/eid/owner 재확인" 을 수행할 수 없었다.
대신 **인증된 계정의 문서 목록을 조회**해 후보를 특정하고, 요구된 4개 항목을 전부 검증했다.

### 2.1 후보 문서 검증

| 검증 항목 | 값 | 판정 |
|---|---|---|
| name | **OneGrip_Play_V1** | 사용자가 적은 이름과 **정확히 일치** |
| documentId | `a21e64f36bc61df760d4587c` | — |
| workspaceId | `ef6a7b3ccc45186203e4d2ca` (Main, isReadOnly=false) | 편집 가능 |
| owner | 홍민 윤 (id `6a846a597fc61bf7360208bc`) | 인증 주체와 **동일** |
| permission | **OWNER** | 편집 권한 있음 |
| 원본(Adam Simon) 문서인가 | 아니오 (`143d2aa6…` 와 다름) | **안전** |
| element 수 | 33 / 원본 33 | **구조 완전 일치** |
| createdAt / modifiedAt | 둘 다 2026-08-18T14:23:53 | **복사 후 미수정** |
| 기존 version | `Start` (`4342e7db262cbced58bf16b8`) | 롤백 지점 존재 |
| **public** | **true** | **§3 주의** |
| 사용자 소유 문서 총 개수 | 1개 (이 문서뿐) | 후보 모호성 없음 |

주요 element id (사본):

```
PARTSTUDIO  Joystick    425d9199b59cfb1efd9ddc35   <- WRITE 대상 (기본 element)
PARTSTUDIO  Base        df9a32f1f239bc71a732f5d3
ASSEMBLY    Joystick    250f706cb675e635b8d344c4
ASSEMBLY    Base        7467121d05e045bfb5b2939f
ASSEMBLY    Complete    d0f87c9cb6d605a481820aa1
```

### 2.2 기준 상태 (baseline) — 수정 전

| 항목 | Joystick Part Studio | Base Part Studio |
|---|---|---|
| feature count | **89** (원본 89, 일치) | **117** (원본 117, 일치) |
| rollbackIndex | **89** | **117** |
| isComplete | true | true |
| feature 상태 | 전부 OK/INFO, **오류 0** | 전부 OK/INFO, **오류 0** |
| feature 이름·순서 | 원본과 동일 | 원본과 동일 |
| sourceMicroversion | `22739d762329ce3bc5f74929` | `22739d762329ce3bc5f74929` |

Joystick Part Studio **part count = 14** (solid 12 + wire 2), 부피:

| partId | 이름 | 부피 (cm³) |
|---|---|---|
| `JaD` | Joystick_1 | **46.658** |
| `JfD` | Joystick_2 | **47.925** |
| `RYDD` | Backplate | 5.900 |
| `RAED` / `RBEL` | Button_wide_1 / _2 | 0.288 / 0.288 |
| `RAEH` / `RBEH` | Button_side_1 / _2 | 0.271 / 0.271 |
| `RAEL` / `RBED` | Button_corner_1 / _2 | 0.199 / 0.199 |
| `RDED` / `RDEH` | Button_middle_1 / _2 | 0.275 / 0.275 |
| `RHED` | Small_joystick_attachment | 0.285 |

partId 가 원본과 동일하고 부피도 원본 실측치(46.660 / 47.930)와 반올림 오차 내로 일치한다.
→ **docs/00 ~ 05 의 모든 좌표·법선·클리어런스 분석이 사본에 그대로 적용된다.**

---

## 3. 중단 보고

### PROBLEM

WRITE 대상 문서가 사용자 메시지에서 **명시되지 않았다.**
URL 자리가 `[COPY한 OneGrip_Play_V1 Onshape URL 입력]` 플레이스홀더 그대로다.

사용자가 STEP 0 에 직접 설정한 게이트는 다음과 같다:

> "작업 전에 URL의 document ID / workspace ID / element ID / owner 를 다시 읽어서
> 사용자가 소유한 편집 가능한 사본인지 확인하라. **확인되지 않으면 WRITE하지 말고 중단하라.**"

검증 대상인 URL 자체가 없으므로 이 게이트를 지시대로 통과시킬 수 없다.

### CAUSE

메시지 작성 시 URL 붙여넣기가 누락된 것으로 보인다. 설계 내용에는 문제가 없다.

### AFFECTED FEATURE

없음. **어떤 Feature 도 생성·수정·삭제되지 않았다.**
원본 문서와 사본 문서 모두 조회 전후 상태가 동일하다.

### MINIMAL FIX OPTION

사용자가 다음 한 가지만 확인해주면 즉시 STEP 1 부터 진행 가능하다:

```
WRITE 대상 = OneGrip_Play_V1
  did = a21e64f36bc61df760d4587c
  wid = ef6a7b3ccc45186203e4d2ca
  eid = 425d9199b59cfb1efd9ddc35   (Joystick Part Studio)
```

이 문서는 §2.1 의 모든 검증을 통과했다 — 이름 일치, 소유자 일치, OWNER 권한,
원본과 다른 문서, 33/33 element 구조 일치, 복사 후 미수정, 사용자 소유 문서 중 유일.

### ALTERNATIVE

1. 다른 사본을 쓸 예정이라면 해당 URL 을 알려준다
2. 사본을 아직 만들지 않았다면 알려준다 (문서 생성도 WRITE 이므로 임의 실행하지 않음)

### RECOMMENDATION

**위 did/wid/eid 로 진행해도 되는지 한 줄로 확인해달라.**

추가로 **반드시 먼저 확인이 필요한 사항이 하나 더 있다:**

> **`OneGrip_Play_V1` 은 현재 `public = true` 다.**
> 이 문서에 추가하는 모든 Feature 는 **즉시 전 세계에 공개된다.**
> 설계를 비공개로 유지하려면 WRITE 전에 문서를 private 으로 전환하기를 권한다
> (문서 공유 설정 변경도 WRITE 이므로 임의로 바꾸지 않았다).

---

## 4. 진행 준비 완료 사항

확인만 받으면 아래를 순서대로 실행한다. 각 단계는 WRITE → GET 재조회 → health 확인 → 다음.

### STEP 1 — 신규 변수 (`assignVariable`, 트리 최하단 append)

| 변수 | 값 | 근거 |
|---|---|---|
| `#finger_button_cap_width` | 8 mm | 원본 `#button_width` |
| `#finger_button_gap` | 3 mm | 원본 `#button_gap` |
| `#finger_button_pitch` | 11 mm | cap + gap |
| `#finger_button_pocket_width` | 6.4 mm | `#button_module_width` 6 + 2×0.2 |
| `#finger_button_tolerance` | 0.2 mm | 원본 `#button_tolerance` |
| `#finger_button_cap_height` | 4 mm | 원본 `#button_cover_height` |
| `#finger_button_support_thickness` | 4 mm | 원본 `#button_support_thickness` |
| `#finger_holder_depth` | 10 mm | docs/04 검증 |
| `#finger_index_z` | 9 mm | docs/04 §6 (12 → 9 로 하향 검증됨) |
| `#finger_row_offset` | 11 mm | docs/03 |
| `#hand_sign` | 1 | RIGHT HAND (§1) |

기존 변수는 **덮어쓰지 않는다.** 전부 `#finger_` 접두 신규 네임스페이스.

### STEP 2~6 대상 좌표 (source of truth = docs/04 실측)

| 버튼 | 3D XYZ (mm) | local surface normal | shell | s |
|---|---|---|---|---|
| INDEX_BTN_1 | (−22.22, −17.49, +9.0) | (−0.92, −0.24, −0.30) | DOMINANT (JfD) | −27.5 |
| INDEX_BTN_2 | (−15.97, −26.20, +9.0) | (−0.48, −0.74, −0.48) | DOMINANT (JfD) | −16.5 |
| INDEX_BTN_3 | (−5.50, −29.32, +9.0) | (−0.02, −0.97, −0.24) | DOMINANT (JfD) | −5.5 |
| INDEX_BTN_4 | (+5.50, −29.32, +9.0) | (+0.03, −0.96, −0.28) | OPPOSITE (JaD) | +5.5 |

각 holder / switch 축 = 해당 위치의 **local 3D normal**. 공통 축 사용 안 함.
사전 검증된 holder 여유: I1 18.2 / I2 13.5 / I3 39.7 / I4 39.9 mm.
나사 최소 여유 4.20 mm (I2), 엄지 구조 최소거리 19.27 mm (I2).

### 검증 계획

각 STEP 후 `GET .../features` 로 featureStates 전수 확인,
`GET .../tessellatedfaces` 재조회 후 `scripts/clearance_check.py` 로 실측 재검증.
목표 위치 오차 ≤ 0.2 mm, 0.5 mm 초과 시 즉시 중단.

---
---

# 2차 실행 — 실제 CAD WRITE 기록 (2026-08-19)

WRITE 대상 확정: `OneGrip_Play_V1` / did `a21e64f36bc61df760d4587c` /
wid `ef6a7b3ccc45186203e4d2ca` / eid `425d9199b59cfb1efd9ddc35` (Joystick Part Studio).
쓰기 가드(`onshape/write_client.py`)가 이 did/wid 이외의 요청을 예외로 차단한다.
원본 Adam Simon 문서(`143d2aa6…`)는 명시적 차단 목록에 등록되어 있다.

## 10. 생성한 Feature 목록

Part Studio 트리 최하단에 **21개 append.** 기존 89개 피처는 하나도 수정하지 않았다.

### STEP 1 — 신규 변수 16개 (`assignVariable`, index 90–105)

| # | Feature name | Feature ID | 값 |
|---|---|---|---|
| 90 | `#finger_button_cap_width` | `Ftd5cOI61ZSDFsY_14` | 8 mm |
| 91 | `#finger_button_gap` | `FhGUCwPkl9bJDvF_14` | 3 mm |
| 92 | `#finger_button_pitch` | `FCKmZk0VU0d3hkH_14` | `#finger_button_cap_width + #finger_button_gap` |
| 93 | `#finger_button_pocket_width` | `Fp8dr7lkSU2Uytc_14` | 6.4 mm |
| 94 | `#finger_button_clearance` | `FNcBRYaT3v5e9fA_14` | 0.2 mm |
| 95 | `#finger_button_cap_height` | `Fyw78h4pvq9ETZy_14` | 4 mm |
| 96 | `#finger_button_support_thickness` | `FV85dLdbVEuxMh8_14` | 4 mm |
| 97 | `#finger_holder_depth` | `FT5uJD1OEcUWla9_14` | 10 mm |
| 98 | `#finger_index_z` | `FYH6tFUlpFW2gz8_14` | 9 mm |
| 99 | `#finger_middle_z` | `FNWU6l51nUsvGUi_14` | −6 mm |
| 100 | `#finger_row_offset` | `FN8yEPxqKRnol6v_14` | 11 mm |
| 101 | `#hand_sign` | `FqBQWiufyk2szSC_14` | 1 (NUMBER) |
| 102 | `#finger_index_i1_s` | `F0oijBOzxAY1BRd_14` | `-27.5 mm * #hand_sign` |
| 103 | `#finger_index_i2_s` | `FxX9mDSrSLJUd0m_14` | `-16.5 mm * #hand_sign` |
| 104 | `#finger_index_i3_s` | `F0fiddZEHi1a8an_14` | `-5.5 mm * #hand_sign` |
| 105 | `#finger_index_i4_s` | `FYrmZiUplXXCIhe_14` | `5.5 mm * #hand_sign` |

기존 원본 변수(`#button_width` 등)는 **덮어쓰지 않았다.** 전부 `#finger_` / `#hand_` 신규 네임스페이스.

### 신규 Feature Studio

| element | id | 내용 |
|---|---|---|
| `OneGrip_FingerButtons` (FEATURESTUDIO) | `d151f2915f76be6046b43c07` | 커스텀 피처 `oneGripIndexButtons` (FeatureScript 2878). 소스: `cad/OneGrip_FingerButtons.fs` |

곡면 위 임의 법선 정렬이 필요해 built-in 피처 대신 FeatureScript 커스텀 피처를 사용했다.
`stage` enum 하나로 5단계를 분리해 **단계별 WRITE → GET → 검증** 흐름을 유지했다.

### STEP 2–7 — 커스텀 피처 5개 (index 106–110)

| # | Feature name | Feature ID | stage | 역할 |
|---|---|---|---|---|
| 106 | `INDEX_construction` | `F2G4jPtZZqR00ez_14` | CONSTRUCTION | I1~I4 기준 평면 4개 |
| 107 | `INDEX_openings` | `Fbxi4RcceV2c8L6_14` | OPENINGS | 8×8 mm 쉘 개구부 4개 (REMOVE) |
| 108 | `INDEX_holders` | `FscLnXq8rwLMZNd_14` | HOLDERS | 12.4×12.4 mm holder, 깊이 2.8→13 mm (UNION) |
| 109 | `INDEX_switch_pockets` | `FBaLb6Ayqc1Me7s_14` | POCKETS | 6.4×6.4 mm 관통 포켓 (REMOVE) |
| 110 | `INDEX_button_caps` | `FR549zFST8H811Q_14` | CAPS | 7.6×7.6×4 mm 캡 4개 (신규 body) |

STEP 6(별도 support rib)은 **생성하지 않았다.** holder 자체가 3 mm 벽 폐단면 튜브로
쉘 벽에 융합되어 있어 V1 에서는 추가 리브가 불필요하다고 판단했다 (§13-1 재확인 필요).

## 11. 실제 좌표 / 법선 (B-rep 실측)

목표점을 `evDistance` 로 실제 B-rep 표면에 투영해 얻은 값이며, FeatureScript 가 이 값을 사용한다.

| Button | 실제 XYZ (mm) | local surface normal | 접선각 | shell | partId |
|---|---|---|---|---|---|
| INDEX_BTN_1 | (−22.224, −17.494, 9.000) | (−0.9291, −0.2385, −0.2828) | −75.60° | Joystick_2 | `JfD` |
| INDEX_BTN_2 | (−15.970, −26.208, 9.000) | (−0.4724, −0.7368, −0.4838) | −32.67° | Joystick_2 | `JfD` |
| INDEX_BTN_3 | (−5.496, −29.325, 9.000) | (−0.0383, −0.9556, −0.2921) | −2.30° | Joystick_2 | `JfD` |
| INDEX_BTN_4 | (+5.496, −29.325, 9.000) | (+0.0383, −0.9556, −0.2921) | +2.30° | Joystick_1 | `JaD` |

- 사전 목표점 대비 **최대 위치오차 0.00879 mm** (목표 ≤ 0.2 mm)
- tessellation 법선 대비 **최대 0.64°**
- 생성된 construction plane 실측: 위치오차 **0.00000 mm**, 법선오차 ≤ 0.36°
  (0.36° 는 FS 에 법선을 소수 4자리로 반올림한 데서 나온다)

**각 holder / pocket / cap 축은 위 local normal 에 개별 정렬**되어 있다. 공통 global 축을 쓰지 않았다.

## 12. 검증 결과

### 12.1 치수 (신규 tessellation 실측)

| 항목 | 설계 | I1 | I2 | I3 | I4 |
|---|---|---|---|---|---|
| 개구부 폭 | 8.0 mm | **8.000** | **8.000** | **8.000** | **8.000** |
| 포켓 폭 (깊이 6 mm) | 6.4 mm | **6.400** | **6.400** | **6.400** | **6.400** |
| 포켓 관통 | 관통 | 관통 | 관통 | 관통 | 관통 |
| holder 도달 깊이 | 13.0 mm | 13.00 | 13.00 | 13.00 | 13.00 |
| 캡 부피 | 0.23104 cm³ | 0.23104 | 0.23104 | 0.23104 | 0.23104 |

캡 중심 실측 오차 **≤ 0.001 mm** (설계 위치 = 표면점에서 법선 안쪽 0.6 mm).

### 12.2 3+1 shell ownership / 분할면

| 검사 | 결과 |
|---|---|
| I1·I2·I3 소속 | **Joystick_2 (`JfD`, X<0) = DOMINANT** ✔ |
| I4 소속 | **Joystick_1 (`JaD`, X>0) = OPPOSITE** ✔ |
| 개구부 분할면 침범 | **0개.** DOMINANT 신규면 X ≤ −1.325, OPPOSITE X ≥ +1.325 (여유 1.325 mm 양측) |
| holder 분할면 침범 | **0개.** Joystick_2 최대 X = **+0.0000**, Joystick_1 최소 X = **−0.0000** (X=0 에서 정확히 클립) |
| I3/I4 gap 중앙 | X = 0 (분할면과 일치) |

### 12.3 기존 구조 무결성

| 검사 | 결과 |
|---|---|
| 나사 A/B/C 축 관통 재료량 | 수정 전후 **완전 동일** (12.56 / 14.49 / 9.59 mm, 변화 +0.00) → **나사 구조 무침범** |
| 기존 엄지 버튼 캡 8개 부피 | **전부 변화 없음** (0.1994 / 0.2710 / 0.2885 / 0.2751 cm³) |
| Backplate 부피 | 5.8999 cm³ **변화 없음** |
| Small_joystick_attachment | 0.2845 cm³ **변화 없음** |
| 기존 89개 Feature | **하나도 수정하지 않음** |
| upstream loft / Mirror 1 / Screw_holes | **무수정** |
| Base / Pitch / Roll Part Studio | **무수정** (쓰기 요청 0건) |

### 12.4 Assembly 영향

| 검사 | 결과 |
|---|---|
| Joystick assembly `Joystick_1 <1>` | partId **`JaD` 정상 참조** ✔ |
| Joystick assembly `Joystick_2 <1>` | partId **`JfD` 정상 참조** ✔ |
| instances / occurrences | 25 / 25 (변화 없음) |

> **중요한 함정과 해결:** FeatureScript `opBoolean` UNION 을
> `qUnion([box, target])` 순서로 호출하면 결과 body 에 **새 partId 가 발급되어**
> 기존 `JaD`/`JfD` 가 사라지고 Joystick assembly 의 두 인스턴스 참조가 끊긴다
> (1차 시도에서 실제로 발생 → 진단 후 롤백).
> **`qUnion([target, box])` 로 target 을 먼저 두면 identity 가 보존된다.**
> FS 소스에 주석으로 명시해 두었다. SUBTRACTION 은 순서와 무관하게 identity 를 보존한다.

### 12.5 Feature health

| 항목 | 수정 전 | 수정 후 |
|---|---|---|
| feature count | 89 | **110** (+21) |
| rollbackIndex | 89 | **110** |
| isComplete | true | **true** |
| ERROR / WARNING feature | 0 | **0** |
| INFO feature | 4 (원본 cPlane) | 4 (동일) |
| solid part count | 12 | **16** (+4 캡) |
| Joystick_1 부피 | 46.658 cm³ | **47.411 cm³** (+0.753) |
| Joystick_2 부피 | 47.925 cm³ | **49.254 cm³** (+1.329) |

부피 변화 내역 (전부 신규 INDEX 피처로 설명됨):

```
Joystick_2 (DOMINANT, 3개)  −0.584(개구부) +3.128(holder) −1.213(포켓) = +1.331  ≈ 실측 +1.329
Joystick_1 (OPPOSITE, 1개)  −0.195(개구부) +1.373(holder) −0.418(포켓) = +0.760  ≈ 실측 +0.753
```

### 12.6 신규 파트

| partId | 이름 | 부피 |
|---|---|---|
| `RKGD` | INDEX_BTN_1_cap | 0.23104 cm³ |
| `RPGD` | INDEX_BTN_2_cap | 0.23104 cm³ |
| `RUGD` | INDEX_BTN_3_cap | 0.23104 cm³ |
| `RZGD` | INDEX_BTN_4_cap | 0.23104 cm³ |

## 13. 미해결 / 후속 확인 필요

1. **holder 접선방향 벽 두께 — 최우선 확인 항목.**
   깊이 8 mm 단면 스캔에서 holder 의 **그립축(y) 방향 벽은 4개 버튼 모두 정상**(3 mm 이상)이나,
   **접선(t) 방향 벽이 I1 · I2 · I3 에서 설계 3 mm 보다 얇거나 일부 구간 결손**으로 측정된다.
   I3 의 +t 측은 분할면 클립에 의한 의도된 절단이지만, I1 의 +t 측과 I2 의 양측은 설명되지 않았다.
   holder 부피가 이론값의 약 70 %(개당 1.043 vs 약 1.5 cm³)인 것과 방향이 일치한다.
   → **Onshape UI 에서 육안 확인 후 필요하면 holder 폭 / 시작 깊이를 조정해야 한다.**
   개구부(8.000 mm)와 포켓(6.400 mm)은 정확하므로 스위치 실장 자체에는 영향이 없다.
2. holder 조립·배선 접근성 (포켓이 관통형이라 내부에서 스위치 삽입 가능하나 실물 확인 필요)
3. 캡 상면이 평면이라 곡률이 큰 I1 에서 모서리가 최대 약 0.3~0.6 mm 뜬다 (V1 허용, V2 에서 곡면화 검토)
4. 캡 유지 구조(shoulder 0.8 mm/측)는 원본과 동일하나 실제 조립 시 이탈 여부 미검증
5. support rib 미생성 — 1번 확정 후 재판단
6. MIDDLE row 미생성 (이번 실행 범위 밖)

## 14. 사용한 도구

| 파일 | 역할 |
|---|---|
| `onshape/write_client.py` | **WRITE 가드** (did/wid 하드코딩 대조, 원본 문서 차단) + feature JSON 빌더 |
| `scripts/deploy_fs.py` | Feature Studio 업로드 + 커스텀 피처 추가/제거 |
| `scripts/fs_eval.py` | Part Studio 내 FeatureScript 평가 (읽기 전용 측정) |
| `cad/OneGrip_FingerButtons.fs` | 커스텀 피처 소스 (버전 관리 대상) |
| `scripts/mesh_probe.py`, `scripts/clearance_check.py` | tessellation 기반 실측 검증 |

## 15. 알려진 API 제약 (다음 실행 참고)

- `GET /partstudios/.../features` 는 응답이 약 3 MB 라 **레이트 리밋이 빨리 걸린다** (429가 10분 이상 지속).
  `POST .../features` 는 `serializationVersion` / `sourceMicroversion` 을 **생략해도 동작**하므로,
  연속 WRITE 시 매번 features 를 GET 하지 말 것.
- `POST /partstudios/.../featurescript` (읽기 평가) 에서는 `op*` 계열 함수가 실행되지 않는다.
  기하 생성 코드는 이 엔드포인트로 디버깅할 수 없다.
- `plane(coordSystem)` 형태는 실패한다. `plane(origin, normal, xDir)` 3인자 형태를 쓸 것.
- `evVolume` 의 파라미터 키는 `entities` 이고, `evDistance` 결과의 `sides[0]` 에는
  `entity` 가 아니라 `index` 가 들어 있다 (`evaluateQuery` 결과 배열의 인덱스).
- `opBoolean` 대상 body 를 `qContainsPoint` 로 지정할 때, **식별점이 그 연산으로 제거되는 영역 안에
  있으면 실패**한다. 신규/기존 어떤 피처도 건드리지 않는 위치를 써야 한다
  (현재 Z=−35, 두께 9.77 mm 구간 사용).
