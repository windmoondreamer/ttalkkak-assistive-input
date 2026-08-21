# INDEX shared holder 구현 — 중단 보고

- 일자 2026-08-19
- 상태: **STOP CONDITION 발생 후 되돌림.** 문서는 regeneration 오류 0의 정합 상태
- 체크포인트: 버전 `INDEX_v1_before_shared_holder` (`e1c51e0a0e7882096643a8a8`) — 작업 전 생성 완료

---

## 1. 완료한 것

### 1.1 스위치 치수 실측 (원본 CAD에서 추출)

원본 `PushBtn` Part Studio, partId `JFD`:

| 항목 | 실측 |
|---|---|
| bounding box | **7.566 × 8.519 × 6.010 mm** |
| 누름축(local Z) 방향 높이 | **6.010 mm** |
| 포켓에 들어가는 몸체 폭 | 6.0 mm (`#button_module_width` 와 일치) |

X 7.566 / Y 8.519 는 리드·레버를 포함한 최대 치수이며, 6.4 mm 포켓에 들어가는 것은
6.0 mm 몸체다. **몸체 높이와 액추에이터 높이의 분리는 확인되지 않았다** —
따라서 `#finger_switch_actuator_height` 는 0 으로 두고 사용자 조정 파라미터로 남겼다.

### 1.2 신규 변수 7개 추가 (전부 state OK)

| 변수 | 값 | featureId | 근거 |
|---|---|---|---|
| `#finger_switch_body_width` | 6 mm | `FFZudlwgBhPaitt_15` | 원본 `#button_module_width` |
| `#finger_switch_body_height` | **6.01 mm** | `FaisOHWslR7kPJb_15` | 원본 PushBtn 축방향 실측 |
| `#finger_switch_actuator_height` | 0 mm | `F9WBUQmoOcFjBr5_15` | **미확정 — 사용자 입력 필요** |
| `#finger_switch_clearance` | 0.2 mm | `FROiwPf0ljWmNky_15` | 원본 `#button_tolerance` |
| `#finger_switch_seat_depth` | 4 mm | `FACrSh5vgnjaGWI_15` | 설계값 |
| `#finger_retainer_clearance` | 0.2 mm | `Fn43oUb01QoWXaN_15` | 설계값 |
| `#finger_retainer_thickness` | 2.5 mm | `FzTde75HBsr9rli_15` | 설계값 |

### 1.3 FeatureScript V2 재설계 (`cad/OneGrip_FingerButtons.fs`)

- `POCKETS` 단계를 **개별 seat(6.4 mm, 깊이 3→7 mm) + I2 프레임 공용 trough(깊이 7→16 mm)** 로 교체
- `RETAINER` 단계 신설: I2 프레임 판 + 버튼별 로컬 법선 정렬 보스 (별도 body)
- I4 는 단독이므로 기존 관통 포켓 유지

배포 중 발견·수정한 FeatureScript 오류 2건:

| 오류 | 원인 | 수정 |
|---|---|---|
| CONSTRUCTION 포함 전 단계 ERROR | `CoordSystem` 에 **`yAxis` 필드가 없다** | `cross(cs.zAxis, cs.xAxis)` 로 계산 |
| RETAINER ERROR | `id + "I4boss"` 와 `id + "I4" + "boss"` 는 **다른 Id 경로** | 경로 일치시킴 |

수정 후 6단계 전부 `state = OK` 로 생성되었다.

---

## 2. STOP CONDITION

### PROBLEM

`INDEX_seats_trough` (공용 trough 절삭) 적용 후
**DOMINANT 쉘 `Joystick_2` 가 두 개의 body 로 쪼개지고 partId `JfD` 를 잃었다.**

```
정상 : JfD  Joystick_2                       (1개)
결과 : R1FD Joystick_2 / R1FH Joystick_2     (2개, 새 partId)
```

이는 다음 중단 조건에 해당한다:
- "원하지 않는 기존 Part 가 수정됨"
- Joystick assembly 의 `Joystick_2 <1>` 참조가 끊긴다 (docs/06 §12.4 와 동일한 유형)

### CAUSE

공용 trough 절삭 상자를 **I2 프레임의 단일 직육면체**(깊이 7→16 mm,
DOMINANT 3개 seat 를 감싸는 범위)로 정의했는데,
I1·I3 의 축이 I2 기준으로 각각 42° · 31° 기울어 있어
이 상자가 **I1 쪽 holder/쉘 벽을 관통**해 재료를 분리시킨 것으로 판단된다.

trough 를 단일 프레임의 프리즘으로 잡은 것이 근본 원인이다.
버튼 축이 서로 크게 기울어 있으므로 **하나의 직육면체로는 세 seat 를 안전하게 잇지 못한다.**

### AFFECTED FEATURE

- `INDEX_seats_trough` (`FRBbZwQIWmL5AEq_14`) — **삭제 완료**
- `INDEX_rear_retainer` (`F1YjyIM9EfjyI7f_15`) — 위에 의존하므로 **삭제 완료**
- 그 외 피처는 영향 없음

### 현재 문서 상태 (되돌린 후)

| 항목 | 값 |
|---|---|
| `JaD` Joystick_1 | **정상 복구** |
| `JfD` Joystick_2 | **정상 복구** |
| 기존 엄지 파트 10개 | 변화 없음 |
| 신규 캡 4개 | 존재 (`RaFD`/`RfFD`/`RkFD`/`RpFD`, 이름 미부여) |
| 살아있는 커스텀 피처 | `INDEX_construction`, `INDEX_openings`, `INDEX_holders`, `INDEX_button_caps` |
| **빠진 것** | **switch pocket 이 없다** (holder 가 속이 찬 상태) |
| regeneration | 오류 0 |

즉 **개구부·holder·캡은 있으나 스위치가 들어갈 포켓이 없는 중간 상태**다.
사용 가능한 상태가 아니므로 다음 실행에서 반드시 이어서 완료해야 한다.

### MINIMAL FIX

trough 를 단일 프리즘 대신 **버튼별 로컬 프레임의 상자 3개를 합집합**으로 만든다.

```
현재(실패):  I2 프레임 단일 상자 (xLo..xHi 범위) 로 3개 seat 를 한 번에 절삭
수정안    :  각 버튼 프레임에서 pockW x pockW 상자를 깊이 seat_end..troughTo 로 만들고
             3개를 qUnion 한 뒤 한 번에 절삭
```

이렇게 하면 절삭 영역이 각 버튼의 holder 안쪽으로만 뻗으므로
쉘 벽을 관통하지 않는다. 인접 홀더끼리는 어차피 깊은 곳에서 서로 겹치므로
(docs/07 §4) 세 공동은 자연스럽게 **하나로 연결**되어 의도한 공용 trough 가 된다.

부수 효과: 이 방식은 사실상 **V1 의 관통 포켓과 동일한 절삭**이며,
차이는 seat 구간(3→7 mm)만 6.4 mm 를 유지하고 그 뒤를 넓히지 않는다는 점이다.
따라서 V1 대비 재료가 늘어나 outer wall 은 개선된다.

### ALTERNATIVE

1. trough 절삭을 **holder body 에만** 적용 (쉘과 union 하기 전에 holder 를 미리 파낸 뒤 union)
   → 쉘 관통 자체가 원천 차단된다. 다만 holder 를 개별 body 로 유지해야 해서 단계 재구성 필요
2. trough 상자를 I2 프레임으로 두되 **깊이·폭을 축소**해 I1 쪽까지 닿지 않게 함
   → 공용 cavity 가 작아져 배선·조립 이점이 줄어든다

### RECOMMENDATION

**MINIMAL FIX(버튼별 상자 3개 합집합)를 채택할 것을 권고한다.**
가장 단순하고, 이미 검증된 `depthBox` + `qUnion` 패턴만 쓰며,
쉘 관통 위험이 구조적으로 없다.

다음 실행에서:
1. 위 방식으로 `POCKETS` 단계 수정 → 배포 → `JfD` 유지 확인
2. `RETAINER` 재적용 (코드는 이미 수정 완료, 재검증만 필요)
3. docs/07 기준으로 outer wall 재측정 (목표 ≥ 2.4 mm)
4. 캡 4개 이름 재부여 (`INDEX_BTN_n_cap`)

---

## 3. 확인된 API / FeatureScript 제약 (추가)

- `CoordSystem` 에는 `origin` / `xAxis` / `zAxis` 만 있다. **`yAxis` 는 없다**
- `id + "I4boss"` 와 `id + "I4" + "boss"` 는 **서로 다른 Id 경로**다
- `GET /partstudios/.../features` 는 응답 3 MB 라 장시간 429 가 걸린다.
  `POST .../features` 는 `serializationVersion` / `sourceMicroversion` 을 **생략해도 동작**하므로
  연속 작업 시 GET 을 쓰지 말 것. `assignVariable` 은 파라미터 10개
  (initEntities / mode / variableType / measurementMode / name /
  lengthValue / angleValue / numberValue / anyValue / value)만으로 생성된다
- `opBoolean` UNION 은 `targets` 를 받지 않는다. identity 보존은
  `qUnion([target, tool])` 순서로만 가능

---

## 4. 미결정 사항

- 실제 택트 스위치의 **몸체 높이 / 액추에이터 높이 분리값** (현재 축방향 총 6.01 mm 만 확인)
- retainer 고정 방식 확정: OPTION A(스냅) vs OPTION B(별도 판).
  FDM P1S · 교체성 · 조립성 기준으로는 **OPTION B(별도 rear retaining plate)** 가 유리하나,
  판을 뒤로 밀리지 않게 잡아주는 **양성 고정(나사 또는 슬라이드 홈)** 은 아직 생성하지 않았다.
  접착 고정은 사용하지 않는다는 요구에 따라 다음 실행에서 반드시 설계해야 한다
