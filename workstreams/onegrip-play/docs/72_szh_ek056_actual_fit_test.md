# 72 — SZH-EK056 actual-part physical fit test fixture

> ## ⚠ RECLASSIFIED (2026-08-23) — LEGACY CUSTOM-BUTTON-BASELINE FIT FIXTURE
>
> 이 fixture 는 **LEGACY CUSTOM-BUTTON-BASELINE FIT FIXTURE** 로 재분류됐다.
> Finger button source lineage 검토 지시에 따른 것이며, geometry/printability 검증
> 자체는 §8/§8.1 그대로 유효하다.
>
> **후속 감사 결과 → [docs/73](73_original_button_geometry_lineage_audit.md).**
> 판정: **REUSABLE WITH CAP-SIDE CHANGES ONLY.**
>
> docs/73 요약:
> - 이 fixture 안에는 **cap geometry 가 한 조각도 없다** (STEP label 40개 중 cap solid 0).
> - N1/N2 switch pose / terminal / carrier rear 는 전부 **cap 과 무관**하게 결정된다.
>   cap 은 `front_depth` 를 읽어 만들어지는 **말단(leaf)** 이다.
> - 현재 cap 의 **외형은 원본과 정확히 일치**한다 (판 7.600 mm, 개구부 8.00 mm).
>   custom 인 것은 ITS-1105 용 **내부 socket** 뿐이다.
> - 따라서 cap 을 현재 외형 유지 + socket 으로 확정하면(docs/73 §7 갈래 A)
>   **이 fixture 는 수정 0건으로 그대로 인쇄·시험 가능하다.**
> - 반대로 원본 solid block 을 무수정 채용하면(갈래 B) switch 가 **1.382~1.578 mm**
>   깊어지고 carrier rear 가 SZH 공간을 그만큼 더 침범하므로
>   **N1/N2 region 재생성이 필요하다.**
>
> 갈래 선택 전까지 이 문서의 측정표를 채우는 것은 **갈래 A 전제에서 유효**하다.


## 1. Status

이 결과는 **TEST FIXTURE / SACRIFICIAL PROTOTYPE**이다. Production OneGrip geometry가 아니다.

| gate | result |
|---|---|
| local printable fit fixture | **GENERATED / PASS** |
| actual SZH-EK056 integration | **HOLD — PHYSICAL TEST REQUIRED** |
| stock knob as final packaging constraint | **EXCLUDED** |
| custom OneGrip knob adapter | **NOT CREATED** |
| N1/N2 production geometry modification | **0** |
| Finger / Thumb / shell production geometry modification | **0** |

실물 결과가 나오기 전에는 provisional `PCB ↔ N1/N2`, `N1 T4 ≈ 1.108 mm`, shaft/gimbal sweep, wiring HOLD를 해결하기 위한 production 수정으로 넘어가지 않는다.

## 2. Deliverables

Mandatory assembly는 실제 OneGrip world coordinate에 놓인 fixture body와 N1/N2 carrier를 함께 보존한다.

| file | purpose | bytes | SHA-256 |
|---|---|---:|---|
| `build123d_workbench/out/szh_actual_fit_fixture/SZH_EK056_ACTUAL_FIT_FIXTURE.step` | labeled world-coordinate assembly | 7,256,140 | `1aafcf4c9c761175c3a7e483dc6c01febfb6363ab694b9899718efa109ea17e9` |
| `build123d_workbench/out/szh_actual_fit_fixture/SZH_EK056_ACTUAL_FIT_FIXTURE.stl` | mandatory multi-body mesh | 2,656,984 | `9464ed66f38bb1800f2d024da431d8506f90da9cf5534b24e5bd2c8f659792b8` |
| `build123d_workbench/out/szh_actual_fit_fixture/SZH_EK056_ACTUAL_FIT_FIXTURE_BODY.step` | shell/Backplate/sacrificial frame print split | 6,484,772 | `9cbbe2903f7c00fe0be22205ca3afdf466c553fe5d070a9ce0b3e79a906b676a` |
| `build123d_workbench/out/szh_actual_fit_fixture/SZH_EK056_ACTUAL_FIT_FIXTURE_BODY.stl` | recommended body print | 2,558,184 | `71b27c4071674cc7c1f55a2195686f9e108ce2cf34abb24e74a1230b4bc39c8a` |
| `build123d_workbench/out/szh_actual_fit_fixture/SZH_EK056_ACTUAL_FIT_FIXTURE_N1_N2_CARRIER.stl` | approved carrier exact-copy print split | 107,684 | `14b0ba5426e7299944c411f88ca02d95dd6ad27f65e64fa3212e23cc336096fb` |
| `build123d_workbench/out/szh_actual_fit_fixture/szh_ek056_actual_fit_fixture.json` | coordinates, hashes, crop, support and memory record | — | generated record |

Generator: `build123d_workbench/szh_actual_fit_fixture.py`.

### Recommended print set

Mandatory STL은 조립 좌표 검증용 multi-body다. 실제 출력은 다음 두 파일을 쓰는 편이 안전하다.

1. `SZH_EK056_ACTUAL_FIT_FIXTURE_BODY.stl`
2. `SZH_EK056_ACTUAL_FIT_FIXTURE_N1_N2_CARRIER.stl`

단위는 **mm**다. Body는 slicer에서 한 개의 rigid body로 회전할 수 있지만, 내부 shell/Backplate component를 따로 자동 정렬하면 안 된다. N1/N2 carrier는 별도 출력한 뒤 승인된 seating position에 넣는다. Carrier fastening boss는 이번 범위에서 만들지 않았으므로 필요하면 외부 비기능 면에 low-tack putty 또는 테이프를 임시로 사용한다.

## 3. Preserved coordinate frame

| datum | value |
|---|---|
| approved joystick pivot datum, world mm | `(-0.216040, -23.149077, 40.496179)` |
| joystick axis / local +Z | `(0.000181854, 0.598493369, 0.801127739)` |
| local +X | `(0.001022863, -0.801127445, 0.598492917)` |
| local +Y | `(0.999999460, 0.000710605, -0.000757865)` |
| source geometry translation | `0.000 mm` |
| source geometry rotation | `0.000°` |
| original Backplate mount-hole centre plane | local `Z = 1.000000 mm` |
| local crop | `51 × 36 × 43 mm` |

JaD/JfD current shell과 lowered original Thumb Backplate는 위 좌표에서 잘라낸 local exact section이다. Crop boundary와 별도 희생형 frame/support만 새 geometry다. Shell inner surface, opening, N1/N2 상대 위치, Backplate mount reference는 이동하지 않았다.

Web reference의 `1.8 mm` axial sensitivity는 렌더에서 approximate module을 놓는 참고값일 뿐이다. 실제 모듈을 강제로 그 위치에 고정하는 hard locator는 만들지 않았다.

## 4. Fixture architecture

- Body: current JaD/JfD local shell section + lowered Backplate local section.
- Sacrificial foundation: open-centre `59 × 43 × 3 mm` frame.
- Structural links: crop 외곽에만 붙는 `3.2 mm` section support 6개.
- Carrier: docs/63 이후 승인된 N1/N2 carrier의 무수정 복사본.
- Printed switch: 없음. 실제 ITS-1105 또는 실측 dummy를 carrier에 넣는다.
- Printed joystick: 없음. 실제 SZH-EK056를 넣는다.
- Stock knob: 제거 상태로 시험한다.
- Stock header: 유지 상태로 시험한다.

Foundation의 중앙 후면, PCB/header 측면, N1/N1-T4 측면, N2 측면, shaft/gimbal 외측 opening이 열려 있다. `1.0–1.3 mm` wire 한 가닥을 rear / side / shell-wall 방향으로 직접 대볼 수 있다.

Embossed labels:

`N1`, `N2`, `PCB DATUM`, `JOYSTICK AXIS`, `+X`, `-X`, `+Y`, `-Y`, `N1 T4 CHECK`, `TEST ONLY`.

## 5. Print and preparation

1. Body와 carrier를 출력한다. Body의 여섯 support link와 foundation은 제거하지 않는다.
2. Stringing 또는 support residue는 access window에서만 제거한다. Shell inner surface, Backplate mount reference, carrier seating surface는 사포로 보정하지 않는다.
3. Carrier를 정확한 seating position에 dry-fit한다. 임시 고정재는 terminal/joystick 쪽이 아닌 외부 비기능 면에만 쓴다.
4. 실제 또는 dummy ITS-1105를 N1/N2에 넣는다. N1 T4를 절단·굽힘·연마하지 않는다.
5. 실제 SZH-EK056 stock knob를 제거한다. Stock header와 pin은 그대로 둔다.
6. 열린 후면에서 모듈을 손으로 넣어 neutral shaft를 OneGrip opening/axis에 맞춘다. Web-reference mounting holes에 억지로 맞추지 않는다.
7. 접촉 확인에는 얇은 마커, transfer ink, 종이/필름 feeler를 사용한다. 실제 부품 또는 production source를 갈아내지 않는다.

지그가 먼저 닿는 경우에만 fixture 내부를 파일/사포/rotary tool로 relief한다. Relief 위치와 대략 깊이를 아래 표에 기록한다.

## 6. Measurement sheet

### 6.1 Actual module metrology

| measurement | actual result | method / note |
|---|---|---|
| MODULE PCB X | `_____ mm` | caliper |
| MODULE PCB Y | `_____ mm` | caliper |
| MODULE PCB Z / thickness | `_____ mm` | bare PCB thickness |
| mounting-hole X pitch | `_____ mm` | hole centre-to-centre |
| mounting-hole Y pitch | `_____ mm` | hole centre-to-centre |
| mounting-hole diameter | `_____ mm` | 4 holes individually if different |
| joystick centre from PCB X datum | `_____ mm` | sign follows fixture labels |
| joystick centre from PCB Y datum | `_____ mm` | sign follows fixture labels |
| ACTUAL MOUNTING POSITION local X | `_____ mm` | relative to labeled axis/datum |
| ACTUAL MOUNTING POSITION local Y | `_____ mm` | relative to labeled axis/datum |
| ACTUAL MOUNTING POSITION local Z | `_____ mm` | relative to Backplate mount plane |
| X potentiometer max envelope | `_____ × _____ × _____ mm` | include terminals |
| Y potentiometer max envelope | `_____ × _____ × _____ mm` | include terminals |
| bottom switch max envelope | `_____ × _____ × _____ mm` | include solder legs |
| stock header max envelope | `_____ × _____ × _____ mm` | plastic + pins |

### 6.2 Shaft / future knob interface

Original printable knob reference bore is approximately `4.150813 × 3.150000 mm`, depth `9.000 mm`. 이것을 근거로 실물 shaft를 PASS 처리하지 않는다.

| measurement | actual result | note |
|---|---|---|
| SHAFT PROFILE | `ROUND / D / KEYED / OTHER: _____` | photo/sketch 권장 |
| SHAFT X | `_____ mm` | maximum section |
| SHAFT Y | `_____ mm` | orthogonal maximum section |
| exposed shaft length | `_____ mm` | housing/shoulder to end |
| available insertion length | `_____ mm` | usable knob engagement only |
| shoulder / step position | `_____ mm` | if present |
| original knob direct fit | `YES / NO / UNKNOWN` | force-fit 금지 |

### 6.3 N1/N2 physical contact

| check | result |
|---|---|
| N1 CONTACT | `NONE / TOUCH / INTERFERENCE` |
| N1 INTERFERENCE LOCATION | `________________________________` |
| N1 T4 direct contact | `NONE / TOUCH / INTERFERENCE` |
| N1 MANUAL RELIEF REQUIRED | `_____ mm approximate / NONE` |
| N2 CONTACT | `NONE / TOUCH / INTERFERENCE` |
| N2 INTERFERENCE LOCATION | `________________________________` |
| N2 MANUAL RELIEF REQUIRED | `_____ mm approximate / NONE` |
| stock header blocks insertion | `YES / NO` |
| stock header contact location | `________________________________` |

### 6.4 Shaft/gimbal tilt

Neutral shaft를 `JOYSTICK AXIS`에 맞춘 뒤 stock knob 없이 천천히 움직인다. 억지로 hard stop을 넘기지 않는다.

| direction | result | first contact location / note |
|---|---|---|
| CENTER | `FREE / TOUCH / BLOCKED` | `____________________________` |
| +X TILT | `FREE / TOUCH / BLOCKED` | `____________________________` |
| -X TILT | `FREE / TOUCH / BLOCKED` | `____________________________` |
| +Y TILT | `FREE / TOUCH / BLOCKED` | `____________________________` |
| -Y TILT | `FREE / TOUCH / BLOCKED` | `____________________________` |
| observed maximum +X | `_____° / _____ mm at shaft end` | method: `_____` |
| observed maximum -X | `_____° / _____ mm at shaft end` | method: `_____` |
| observed maximum +Y | `_____° / _____ mm at shaft end` | method: `_____` |
| observed maximum -Y | `_____° / _____ mm at shaft end` | method: `_____` |

### 6.5 One-wire departure probe

`1.0–1.3 mm` class insulated wire 한 가닥만 손으로 대본다. Production channel을 만들거나 carrier를 깎지 않는다.

| route | result | tight/contact location |
|---|---|---|
| REAR WIRE DEPARTURE | `CLEAR / TIGHT / BLOCKED` | `____________________________` |
| SIDE WIRE DEPARTURE | `CLEAR / TIGHT / BLOCKED` | `____________________________` |
| SHELL-WALL DEPARTURE | `CLEAR / TIGHT / BLOCKED` | `____________________________` |
| preferred physical route | `REAR / SIDE / SHELL-WALL / NONE` | `____________________________` |

## 7. Review renders

![Actual fit fixture assembled](../renders/szh_actual_fit_fixture/01_actual_fit_fixture_assembled.png)

![N1 T4 access](../renders/szh_actual_fit_fixture/02_access_windows_and_n1_t4.png)

![Shaft tilt reference](../renders/szh_actual_fit_fixture/03_shaft_tilt_direction_reference.png)

Web module의 green PCB/colored body는 위치 설명용 translucent reference다. STEP/STL print geometry에는 포함되지 않는다.

## 8. Verification record

| verification | result |
|---|---|
| mandatory STEP re-import | **PASS** |
| STEP solid count | `74` |
| STEP leaf-solid volume sum, serialization diagnostic only | `15157.361121 mm³` |
| nested root mass property, serialization diagnostic only | `4127.525150 mm³` |
| canonical carrier ↔ exported carrier | **EXACT COPY / distance 0.000000 mm** |
| web PCB/gimbal/header/shaft solids in fixture STEP | **ABSENT** |
| local full-shell crop operations | `2`, serial |
| full shell STEP/STL export | `0` |
| web joystick exported into fixture | `NO` |
| custom knob/adapter generated | `NO` |
| source hash before/after | **IDENTICAL** |
| peak process RSS | `525.3 MB` |
| production geometry modification | **0** |

### 8.1 Independent re-verification (generator report not trusted)

Fixture 산출물을 generator 의 자체 JSON 과 무관하게 다시 검사했다. Crop 은 동결 source 에서
**재계산**해 STEP 안에 실제로 들어 있는 solid 와 대조했다.

| gate | result |
|---|---|
| JaD 국소 crop = 동결 source 재계산본 | **PASS** — solid 3개, dCentroid `2.618e-05 mm`, dBbox `6.135e-05 mm` |
| JfD 국소 crop = 동결 source 재계산본 | **PASS** — solid 2개, dCentroid `3.208e-05 mm`, dBbox `6.122e-05 mm` |
| lowered Backplate crop = 동결 source 재계산본 | **PASS** — dCentroid `8.834e-09 mm` |
| N1/N2 carrier = 승인 carrier 무수정 복사본 | **PASS** — dVol `4.832e-12 mm3`, dCentroid `3.197e-14 mm` |
| 필수 label 10개 존재 | **PASS** |
| tilt reference mark 4개 존재 | **PASS** |
| label/mark 가 ring band 위, 개구부 위로 캔틸레버 없음 | **PASS** (§8.2 수정 후) |
| label/mark 가 frame 상면 `z = -11.0` 에 정확히 안착 | **PASS** |
| label 간 충돌 | **PASS** — 0건 (§8.2 수정 후) |
| STL 열린 경계 / degenerate | **PASS** — 3개 파일 전부 boundary 0, degenerate 0 |
| STEP leaf solid 유효성 | **PASS** — 74개 전부 valid, 부피 양수 |
| printable fixture 안의 web reference solid | **PASS** — 0건 |

좌표 일치가 정확히 0 이 아니라 `~3e-05 mm` 인 것은 **STEP 직렬화 정밀도**다. Generator 는
`full & crop_world` 만 수행하고 `moved()` 를 전혀 쓰지 않으므로 코드상 병진·회전은 **0** 이다.
`3e-05 mm` 는 FDM/SLA 해상도보다 3~4 자릿수 아래라 실물에서 의미가 없다.

**STL 의 non-manifold edge 189개는 결함이 아니다.** 열린 경계는 0 이고, 이 edge 들은 서로
맞닿는 별개 body(분할면에서 만나는 JaD/JfD 쉘 섹션, frame 위에 얹힌 embossed label)의
**정상적인 면 접촉**에서 나온다. Slicer 가 union 으로 처리한다.

### 8.2 검증 중 발견·수정한 fixture 결함 2건

둘 다 **희생형 frame 안에서만** 발생했다. Production geometry 수정은 여전히 **0** 이다.

1. **tilt mark 4개가 개구부 위 캔틸레버였다.** `TILT_MARK_*` 가 aperture 안쪽
   (`|x| <= 24.5`, `|y| <= 16.5`)을 향해 뻗어 있어 **ring 재료 위 footprint 가 0.0%** 였고,
   ring 안쪽 벽에 **0.44 mm2 맞대기 면 하나로만** 붙은 4 mm 캔틸레버였다 (겹침 부피 0.000 mm3).
   FDM 에서 첫 레이어가 허공에 놓여 처지거나 떨어져 나간다. -> 각 tick 을 자기 label 옆
   **band 위로 이설**했다. 재검사 footprint **100.0%**.
   `+X (24.7~28.7, 4.4~5.2)` / `-X (-28.7~-24.7, 4.4~5.2)` /
   `+Y (-14.5~-13.7, 17.0~21.0)` / `-Y (-14.5~-13.7, -21.0~-17.0)`.
2. **`JOYSTICK AXIS` 와 `TEST ONLY` 글자가 겹쳤다** (`0.080523 mm3`). `Text` 가 원점 기준
   **중앙 정렬**이라 `x = -5.0` 에서 두 문자열이 `x -2.52..-0.78` 구간에서 맞물렸다.
   -> `TEST ONLY` 를 `x = -7.5` 로 이동. 재검사 충돌 **0건**, 두 label 간극 `0.76 mm`.

**교훈: 각도·부피·해시가 전부 통과해도 "그 solid 밑에 재료가 있는가" 는 별도 지표다.**
tick 은 좌표·치수·label 이 모두 옳았고 STEP/STL 도 닫혀 있었지만 출력하면 사라졌을 것이다.

Key frozen source guards:

| source | SHA-256 |
|---|---|
| `N1_N2_SHARED_CARRIER_N1_LOCAL.step` | `2485e34f8716395459f1f7b10384fd73a33695472f9aae689cf321d583830756` |
| `JAD_FINGER_V2.step` | `a477aa79e55ddb21fb2a45c7f616544f6eb4844b593f61cf7d45303476c5a762` |
| `JFD_FINGER_V2.step` | `d457d5d9b305a4c7d77e21aab3cb7d33336d672d4d8bf031e6158de44c26ad50` |
| `THUMB_TARGET_EXACT_MODULE.step` | `adc870ffaf55a9342d62df89f162827a744bdf1d43060c0fbb69f7c8e8089fe9` |

## 9. Stop gate

실물 측정표와 contact/tilt/wire 결과가 채워질 때까지:

- N1/N2 terminal 수정 금지
- N1/N2 carrier 수정 금지
- Thumb/shell 수정 금지
- SZH mounting adapter production 설계 금지
- final wire channel 생성 금지
- custom knob bore/adapter 변경 금지

**STOP — actual SZH-EK056 physical result required.**
