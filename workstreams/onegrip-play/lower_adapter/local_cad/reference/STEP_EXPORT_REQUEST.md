# 필요한 STEP 내보내기 목록 (수동 작업 요청)

로컬 저장소에 **STEP / BREP / FCStd 가 하나도 없다** (§4 감사 결과, 아래 표).
지시(§5, §27)대로 근사 치수로 재구성하지 않고 여기서 멈춘다.

Onshape 에서 아래 파일들을 직접 내보내
`lower_adapter/local_cad/reference/` 에 넣어 주면 로컬 CadQuery 작업을 이어간다.

---

## 공통 설정 (모든 파일 동일)

```
Format        STEP
Version       AP242   (없으면 AP214)
Units         Millimeter
Export as     Single file          <- 부품별 분할 파일 아님
Include       Part names / product structure 유지 (기본값)
Scale         1.0
```

> Onshape: 대상 탭을 **우클릭 -> Export** 또는 Part 목록에서 다중 선택 후 Export.

문서: `OneGrip_Play_V1`
`did = a21e64f36bc61df760d4587c`  ·  `wid = ef6a7b3ccc45186203e4d2ca` (Main)

권장: **버전 `CONFORMAL_STOCK_EMBED_V1` (`42a15b14ff576623e223b7c6`) 에서 내보낼 것.**
워크스페이스는 병렬 상체 작업으로 계속 바뀐다.
버전 URL: `https://cad.onshape.com/documents/a21e64f36bc61df760d4587c/v/42a15b14ff576623e223b7c6`

---

## A. 필수 3개

### A-1. `STOCK_GIMBAL_REFERENCE.step`

| | |
|---|---|
| 대상 | **Part Studio `Base`** |
| element id | `df9a32f1f239bc71a732f5d3` |
| 포함 부품 | **solid 7개 전부** |
| 방식 | 단일 파일, 부품 구조 유지 |

포함되어야 할 7개 (partId — 이름):

```
RYBD  Base            (고정, 마운팅 인터페이스의 기준)
JJD   Roll_holder     (고정)
RKCD  Roll_holder_2   (고정)
ROCD  Spacer          (고정)
JaD   Roll            (이동)
JmD   Pitch           (이동)
RRBD  Spring_holder   (이동)
```

> 이 Part Studio 안에서는 7개가 **중립 자세**로 놓여 있다.
> (어셈블리 쪽이 편향 상태다 — A-3 참조)

### A-2. `CONFORMAL_CORE_REFERENCE.step`

| | |
|---|---|
| 대상 | **Part Studio `OneGrip_ConformalHousing`** |
| element id | `8945f7ac4100dfd52a8c8dba` |
| 포함 부품 | **solid 2개 전부** |
| 방식 | 단일 파일 |

```
JHD   CONFORMAL_HOUSING   495,615 mm3   128.6 x 170.6 x 139.9
RdKD  BOTTOM_CARRIER       90,178 mm3   118.0 x 123.0 x 9.0
```

**이 파일이 가장 중요하다.** 검증된 내부 공동(cavity)·캐리어 개구·착좌 환형·
인서트 위치가 전부 여기 들어 있고, 이걸 그대로 얼려서 그 바깥에 외피를 다시 그린다.

> 내보내기가 두 solid 를 한 덩어리로 합쳐 버리면, `BOTTOM_CARRIER` 만 따로
> `BOTTOM_CARRIER_REFERENCE.step` 으로 한 번 더 내보내 주면 된다.

### A-3. `ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step`

| | |
|---|---|
| 대상 | **Assembly `Complete`** |
| element id | `d0f87c9cb6d605a481820aa1` |
| 포함 | 전체 (그립 + 스톡 짐벌 + 베어링 + 전장 + 나사) |
| 방식 | 단일 파일, **부품 분리 유지** (하나로 합치지 말 것) |

**이 파일이 필요한 이유: 좌표계 정합.**
지금까지의 모든 설계값은 **그립(Joystick) Part Studio 좌표계** 기준이다.
Part Studio 를 개별로 내보내면 서로 다른 로컬 좌표계로 나오므로,
어셈블리 파일이 있어야 그 사이 변환을 로컬에서 복원할 수 있다.

> 이 어셈블리는 **편향 상태**로 저장돼 있다 (Pitch 5.6062°, Roll 0.452°).
> 그대로 내보내도 된다 — 중립 복원 행렬을 이미 갖고 있고
> (`lower_adapter/cad_dump/stock_frames.json`), STEP 에서 다시 유도할 수도 있다.

---

## B. 있으면 좋은 것 2개 (없어도 진행 가능)

### B-1. `ONEGRIP_REFERENCE.step`

| | |
|---|---|
| 대상 | **Part Studio `Joystick`** (상체) |
| element id | `425d9199b59cfb1efd9ddc35` |
| 포함 부품 | **`Joystick_1` (JaD) + `Joystick_2` (JfD) 2개만** |
| 방식 | 단일 파일 |

그립 외피만 있으면 된다. 손가락 버튼 / holder / retainer 는 **넣지 말 것**
(이번 작업 범위 밖이고 파일만 커진다).
이 파일이 있으면 그립 좌표계 원점을 STEP 에서 직접 잡을 수 있어 A-3 의존이 줄어든다.

### B-2. `ELECTRONICS_REFERENCE.step`

| | |
|---|---|
| 대상 | **Part Studio `ARDUINO PRO MICRO parts`** |
| element id | `f018a101ec0b6d10a6dcb0dc` |
| 포함 부품 | `micro board`, `micro usb shell`, `micro usb internal`, `MICRO_stackable header 12` (4종이면 충분) |

USB 포트 / 케이블 경로 검증용. A-3 어셈블리에 이미 포함되므로 **선택**이다.

---

## C. 내보내지 않아도 되는 것

- `OneGrip_ErgoShell` (`a2e4739a4d624b06dee5abba`) — 외피는 CadQuery 에서 다시 만든다.
  이번 이관의 목적 자체가 이 부분을 로컬 파라메트릭으로 옮기는 것이다.
- 손가락 버튼 / INDEX·MIDDLE holder / retainer — 이번 작업 범위 밖 (지시 마지막 문단).
- 베어링 / 나사 표준부품 — 어셈블리에 딸려오면 그대로 두면 되고 따로는 불필요.

---

## D. 왜 로컬 메시로는 안 되는가

현재 하부 기하는 전부 내가 만든 **tessellation 캐시**로만 존재한다.

| 캐시 | 내용 |
|---|---|
| `lower_adapter/cad_dump/stock_full.npz` | 스톡 39부품 삼각형망 (그립 좌표, 편향 상태) |
| `lower_adapter/cad_dump/conformal_meshes.npz` | `JHD` 7,800 tri / `RdKD` 6,794 tri |
| `lower_adapter/cad_dump/ergo_meshes.npz` | W2 외피 29,738 tri / 캐리어 6,794 tri |
| `lower_adapter/cad_dump/motion_configs.npz` | 9자세 모션 포락선 (33 MB) |

이건 **chordTolerance 0.0002~0.0003 의 근사 삼각형망**이다.
지시 §4 대로 시각 확인 · 충돌 검증 · 교차검사에는 쓰되,
**기계 설계의 1차 소스로 쓰지 않는다.** 특히 캐리어 포켓(0.30 mm/side),
스피곳 끼움(0.20 mm/side), C1/C2 슬롯 같은 공차 피처는 메시에서 복원하면 안 된다.

저장소 전체 감사 결과:

```
.step  0      .stp  0      .brep  0      .FCStd  0      .iges  0
.stl  67   <- 전부 상체(그립/버튼). 하부 부품은 하나도 없다
```

`exports/thumb_lower15_housing_mockup/` 의 "lower15_housing" 도 이름과 달리
**상체 쉘**(`Joystick_1_JaD` / `Joystick_2_JfD`) 이다.

---

## E. 파일을 넣을 위치

```
lower_adapter/local_cad/reference/
    STOCK_GIMBAL_REFERENCE.step                  (필수)
    CONFORMAL_CORE_REFERENCE.step                (필수)
    ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step        (필수)
    ONEGRIP_REFERENCE.step                       (선택)
    ELECTRONICS_REFERENCE.step                   (선택)
    BOTTOM_CARRIER_REFERENCE.step                (A-2 가 합쳐질 때만)
```

파일이 들어오면 바로 §26 순서로 진행한다:
프리즈 임포트 -> 무변경 재출력 -> 스케일/좌표 검증 -> W2 포락선 재현 -> STEP/STL.
