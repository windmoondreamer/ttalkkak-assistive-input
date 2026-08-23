# 원본 DIY Joystick CAD 구조 분석

- 출처: https://cad.onshape.com/documents/143d2aa6a2cf1c2ed82be979/w/f0ab4fb72b468eeb38cc7a63/e/212ec93359aad06aa2bd2fad
- 문서명: **Joystick** / 소유자: Adam Simon
- 공개 상태: **public (ANONYMOUS_ACCESS)** — API 키 없이 일부 읽기 가능
- 생성 2024-07-11 / 최종 수정 2025-08-21
- 조회일: 2026-08-18 (읽기 전용 GET만 수행, **수정 없음**)
- 원시 덤프: `cad_dump/` — 아래 내용은 전부 실제 API 응답에서 나온 값이다.

---

## 1. Document 구조 — element 33개

| 구분 | 이름 | elementId |
|------|------|-----------|
| Part Studio | Base | `2fae0d1a0124e696279efed6` |
| Part Studio | **Joystick** (기본 element) | `212ec93359aad06aa2bd2fad` |
| Part Studio | Magnet | `bc18608af20c3b08c0ff7444` |
| Part Studio | Hall_effect_sensor | `22b139a2653e397a94b9d9e1` |
| Part Studio | 625zz_bearing | `88241e40294795eaf2206863` |
| Part Studio | PushBtn | `7b9ddcd8027f0e95b934afc3` |
| Part Studio | HW504_B (엄지 조이스틱 모듈) | `c349d3fc572261fbfb95897f` |
| Part Studio | ARDUINO PRO MICRO parts | `2a2504992e329ba63eccf9fc` |
| Assembly | **Complete** (최상위) | `b844c9f23a7beb9d72779e4f` |
| Assembly | Base | `f28515c05753a2a56c83f653` |
| Assembly | Joystick | `14f545ef519ae3e58e12f61f` |
| Assembly | Bearing | `6fafe2b4bb803cc32e160661` |
| Assembly | Hall_effect_sensor | `2d9f69fcbaa034c7b028471c` |
| Assembly | ARDUINO PRO MICRO | `f25d08b15ace207c1dd8b61d` |
| Assembly | micro usb | `c462d684244ff632c409a6b1` |
| Assembly | MICRO_stackable header 12 (2개) | `e2d8a298fa9fb67e226c9a69`, `e005c2b1f5b7545445a25c40` |
| Variable Studio | Variable Studio 1 | `557f940136df10b235ef6ccd` |
| Blob | HW504_B.STEP / PushBtn.SLDPRT / SKF_625_2Z.STEP / ARDUINO PRO MICRO.STEP / 참고 이미지 2장 | — |
| BOM | 9개 (자동 생성) | — |

단위: 전 element `millimeter` / `degree` / `gram`.

---

## 2. Assembly 계층 (BOM 실측)

```
Complete
├── Base (assembly)
│   ├── Base                 x1
│   ├── Pitch                x1
│   ├── Roll                 x1
│   ├── Roll_holder          x1
│   ├── Roll_holder_2        x1      <- roll_holder는 2개짜리 세트
│   ├── Spring_holder        x1
│   ├── Bearing (asm)        x4      <- 625zz, 볼 8 + 내/외륜
│   ├── M5x0.80 x 12 screw   x4
│   ├── M3x0.50 x 16 screw   x6
│   ├── Hall_effect_sensor   x2      <- 축당 1개 (roll / pitch)
│   ├── Magnet               x4
│   └── Spacer               x1
├── Joystick (assembly)  <- grip
│   ├── Backplate                    x1
│   ├── Joystick_1                   x1   <- 쉘 A
│   ├── Joystick_2                   x1   <- 쉘 B
│   ├── Small_joystick_attachment    x1   <- 엄지 조이스틱 장착부
│   ├── PushBtn                      x8   <- 스위치 8개
│   ├── HW504_B                      x2   <- 엄지 조이스틱 모듈 2개 (확인 필요)
│   ├── Button_corner_1 / Button_side_1 / Button_wide_1 / Button_middle_1   각 x1
│   ├── Button_corner_2 / Button_side_2 / Button_wide_2 / Button_middle_2   각 x1
│   └── M3x0.50 x 16 screw           x3
└── ARDUINO PRO MICRO (assembly)  - atmega32U4 보드 모델
```

### 핵심 발견

**원본은 이미 버튼 8개 구조다.** PushBtn x8 + 버튼 캡 8개.
캡은 `corner / side / wide / middle` 4종이 `_1` / `_2` 두 그룹으로 나뉘며,
Joystick Part Studio의 `Mirror 1`, `Mirror 2` 피처와 대응한다.
즉 **손가락 2개 x 버튼 4개 = 8개**라는 OneGrip Play 목표와 원본 구조가 이미 일치한다.

버튼을 새로 추가할 필요가 없을 가능성이 높다. 재배치/재매핑 문제일 수 있다.
단, `_1` / `_2` 그룹이 실제로 검지/중지에 대응하는지는 **형상 좌표로 확인한 뒤 확정**한다.

---

## 3. Part Studio: Base — 피처 117개

마스터 변수 39개가 트리 최상단에 선언되고 그 아래에서 형상이 만들어지는 **완전 파라메트릭** 구조다.
치수를 바꾸려면 스케치가 아니라 변수를 바꾸는 것이 정석이다.

### 3.1 마스터 변수 (실측값)

| 분류 | 변수 | 값 |
|------|------|-----|
| **bearing** | `#bearing_outer_diameter` | 16 mm |
| | `#bearing_inner_diameter` | 5 mm |
| | `#bearing_width` | 5 mm |
| | `#bearing_tolerance` | 0.15 mm |
| **magnet** | `#magnet_diameter` | 8 mm |
| | `#magnet_width` | 4.5 mm |
| | `#magnet_tolerance` | 0.15 mm |
| **hall sensor** | `#hall_effect_sensor_length` | 4 mm |
| | `#hall_effect_sensor_width` | 1.5 mm |
| | `#hall_effect_sensor_height` | 4 mm |
| | `#hall_effect_sensor_tolerance` | 0.2 mm |
| **짐벌 거동** | `#joystick_angle` | **15 deg** (스틱 최대 기울기) |
| | `#offset_around_pitch` | `0.2mm * (#joystick_angle / deg) + 1mm` (각도 종속) |
| | `#pitch_offset` | 0.5 mm |
| | `#roll_offset` | 5 mm |
| | `#pitch_top_width` | 10 mm |
| | `#pitch_depth` | 3 mm |
| | `#wall_behind_bearing` | 2 mm |
| **spring** | `#spring_distance` | 15 mm |
| | `#spring_distance_base` | 30 mm |
| | `#spring_o_ring_diameter` | 5 mm |
| **screw** | `#screw_head_diameter` | 8 mm |
| | `#screw_depth` | 10 mm |
| | `#screw2_diameter` | 3 mm (M3) |
| | `#screw2_head_diameter` | 5 mm |
| | `#screw2_head_height` | 3 mm |
| | `#screw2_length` | 16 mm |
| **base / 전자부** | `#base_height` | 3 mm |
| | `#base_screw_box_length` | 15 mm |
| | `#base_screw_box_height` | 10 mm |
| | `#arduino_width` / `#arduino_length` / `#arduino_height` | 23 / 40 / 11 mm |
| | `#spacer_height` | 7 mm |
| **grip 결합** | `#attachment_tolerance` | 0.2 mm |
| | `#attachment_width` / `#attachment_depth` | 측정 변수 (MEASUREMENT) |
| | `#turning_height` | 측정 변수 (`Measure_turning_height` 스케치 기반) |
| | `#roll_diameter` | 측정 변수 |

> `#joystick_angle = 15 deg`가 `#offset_around_pitch`를 통해 형상에 전파된다.
> 기울기 각도를 바꾸면 클리어런스가 자동으로 따라오는 구조이므로 파급이 크다.

### 3.2 주요 스케치 (형상 순서)

`Measure_turning_height` → `Roll_holder` → `Bearing` → `Back_support` →
`Roll_holder_bottom_hole` → `Pitch` → `Roll_pitch_offset` → `Pitch_bearing` →
**`Pitch_attachment`** → `Cable_route` → `Roll_screw_hole` → **`Spring_holder`** →
`Base` → `Base_spring_hooks` → `Base_spring_hook_screw_hole_1~4` →
`Hall_effect_sensor_stop_pitch` → `Hall_effect_sensor_stop_roll`

트리 끝에 `Transform 1`, `Transform 2`가 있다 (부품 배치용).

---

## 4. Part Studio: Joystick (grip) — 피처 89개

### 4.1 마스터 변수 (실측값)

| 분류 | 변수 | 값 |
|------|------|-----|
| **엄지 조이스틱** | `#small_joystick_pin_width` | 3 mm |
| | `#small_joystick_pin_depth` | 4 mm |
| | `#small_joystick_pin_height` | 8 mm |
| | `#small_joystick_top_diameter` | 14 mm |
| | `#small_joystick_tolerance` | 0.075 mm |
| | `#joystick_hole_diameter` | 15 mm |
| **버튼** | `#button_width` | 8 mm |
| | `#button_gap` | 3 mm |
| | `#button_module_width` | 6 mm |
| | `#button_tolerance` | 0.2 mm |
| | `#button_support_thickness` | 4 mm |
| | `#button_cover_height` | 4 mm |
| **스위치** | `#switch_width` | 10 mm |
| | `#switch_height` | 7 mm |
| **screw** | `#screw_diameter` | 3 mm (M3) |
| | `#screw_head_width` | 5 mm |

### 4.2 grip 형상 생성 방식

```
Joystick_side_profile + Joystick_front_profile   (2방향 프로파일 스케치)
  -> Projected curve 1                           (3D 곡선 생성)
  -> cPlane x 4  (Joystick_part_1~4_plane)       (곡선 위 4개 단면 평면)
  -> Joystick_part_1~4 스케치                    (각 평면의 단면)
  -> Loft 2                                      (4단면 로프트 = 그립 본체)
  -> Enclose 1 -> Extrude 1 -> Boolean 1
  -> Shell 1                                     (속 비움)
  -> Mirror 1                                    <- 좌/우 분할의 근원
  -> Screw_holes -> Extrude 18~22
```

**grip은 단면 4개를 로프트한 유기적 곡면이다.** 박스가 아니다.
버튼 위치를 옮기려면 로프트 표면의 곡률을 따라가야 하며,
`Buttons_plane`(Projected curve 2 기반 cPlane) 위의 `Buttons` 스케치가 그 기준면이다.

### 4.3 버튼 / 백플레이트 계통

```
Projected curve 2 -> cPlane 'Buttons_plane' -> 스케치 'Buttons' (엔티티 49개) -> Extrude 2
스케치 'Backplate' + 'Sweep_guide' -> Sweep 1 -> Mirror 2
스케치 'Buttons_backplate_holes'    -> Extrude 7
스케치 'Buttons_backplate_supports' -> Extrude 8, 9
스케치 'Buttons_cover'              -> Extrude 17, 23, 24
```

### 4.4 grip <-> Base(Pitch) 결합 방식

```
superDerive 1   (operationType=NEW, origin=true, includeVariables=true)
  -> Base Part Studio의 형상 + 변수를 Joystick Studio로 가져옴
스케치 'Attachment' + 'Fill_botom'
  -> Extrude 14 -> Boolean 2 -> Delete part 1 -> Boolean 3
  -> Extrude 15 -> Boolean 4 -> Delete part 2 -> Boolean 5
```

즉 **grip의 결합부는 Base의 `Pitch_attachment` 형상을 derive해서 boolean으로 파낸 것**이며,
`#attachment_tolerance = 0.2 mm` 클리어런스가 적용된다.

> 중요: `superDerive`가 걸려 있으므로 **Base Part Studio를 수정하면 grip 결합부가 자동으로 따라 변한다.**
> 반대로 grip 쪽에서 결합부만 임의로 바꾸면 derive 결과와 충돌한다.
> Base와 Joystick은 독립이 아니라 **단방향 종속(Base → Joystick)** 관계다.

### 4.5 Joystick_1 <-> Joystick_2 결합 방식

- 두 쉘은 `Shell 1` → `Mirror 1`로 생성된 좌/우 반쪽이다.
- 스케치 `Screw_holes` + Extrude 18~22로 체결 구멍이 뚫린다.
- Joystick assembly BOM에 **M3x0.50 x 16 나사 3개**가 있다 (쉘 체결용으로 보인다).
- 정확한 mate 관계는 assembly definition 조회가 필요한데 **익명 접근으로 401**이다 (5장 참조).

---

## 5. 접근 제약 — API 키가 필요한 부분

익명(키 없음) 상태에서 엔드포인트별 실제 응답:

| 엔드포인트 | 결과 | 얻을 수 있는 것 |
|-----------|------|----------------|
| `GET /documents/{did}` | **200** | 문서 메타 |
| `GET /documents/d/{did}/w/{wid}/elements` | **200** | element 목록 |
| `GET /partstudios/.../features` | **200** | 피처 트리 + 변수 + 스케치 형상 전체 |
| `GET /assemblies/.../bom` | **200** | BOM 계층 |
| `GET /parts/...` | **401** | part id, part별 속성 |
| `GET /partstudios/.../bodydetails` | **401** | B-rep 상세 |
| `GET /partstudios/.../massproperties` | **401** | 부피 / 무게중심 / bounding box |
| `GET /partstudios/.../configuration` | **401** | configuration 정의 |
| `GET /assemblies/.../` (definition) | **401** | **mate 관계, 부품 배치 좌표** |
| `GET /variables/...` | **401** | Variable Studio 값 |
| `GET /documents/d/{did}/versions` | **401** | 버전 이력 |

### 지금 당장 못 하는 것

1. **assembly mate 관계** — Joystick_1/Joystick_2가 어떤 mate로 붙는지, grip이 Pitch에 어떤 mate로 붙는지
2. **부품별 3D 좌표** — 버튼 8개의 실제 위치, 검지/중지 대응 여부
3. **bounding box / 무게중심** — 그립의 실제 외형 크기
4. **모든 쓰기 작업** — 파생 문서 생성, 피처 추가/수정

### 필요한 것 (사용자 조치)

**A. Onshape API 키** — 읽기 전용 분석을 완성하려면 최소한 이것이 필요하다.

1. https://dev-portal.onshape.com/keys 접속 (Onshape 계정으로 로그인)
2. "Create new API key" → **Read** 권한(`OAuth2Read`) 체크
3. Access Key / Secret Key 발급 → 프로젝트 루트에 `.env` 생성:

```
ONSHAPE_ACCESS_KEY=...
ONSHAPE_SECRET_KEY=...
```

4. `.env`는 절대 커밋하지 않는다.

**B. 쓰기 작업까지 하려면** — 위 키에 **Write** 권한(`OAuth2Write`)을 추가한다.
단, 원본 문서는 Adam Simon 소유이므로 **키가 있어도 원본은 수정할 수 없다.**
사용자 계정으로 원본을 **Copy workspace / Fork** 해서 사본 문서를 만들고,
그 사본의 did/wid를 알려주면 그 문서를 대상으로 작업한다.

**C. 라이선스 확인** — 원본이 public이라는 것과 파생·배포가 허용된다는 것은 별개다.
Onshape 공개 문서 페이지나 원저작자 배포처(Thingiverse/Printables 등)에서 라이선스를 확인해야 한다.

---

## 6. 확정하지 않은 것 (추측 금지 항목)

- `Button_*_1` / `Button_*_2` 그룹이 검지/중지에 각각 대응하는지 — 좌표 확인 필요
- 그룹당 버튼 4개가 "LEFT 3 + RIGHT 1"로 나뉘어 있는지 — 좌표 확인 필요
- **HW504_B가 2개**인 이유 — 엄지 조이스틱이 원래 2개인지, 미사용 인스턴스인지
- `Roll_holder` / `Roll_holder_2`의 역할 분담
- 그립의 실제 외형 치수 (massproperties 401)
- 원본이 왼손용인지 오른손용인지

---

## 7. 재현 방법

```bash
python scripts/dump_structure.py
```

키가 없으면 익명으로 가능한 것만, 키가 있으면 401 항목까지 `cad_dump/`에 채워진다.
