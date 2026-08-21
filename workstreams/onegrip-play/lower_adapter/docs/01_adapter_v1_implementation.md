# 하부 20° 경사 어댑터 — 1차 CAD 구현

- 일자: 2026-08-20
- 대상 문서: `OneGrip_Play_V1` (did `a21e64f36bc61df760d4587c` / wid `ef6a7b3ccc45186203e4d2ca`)
- 체크포인트: `PRE_ADAPTER` = `40aeafabde5ccb638fa0aec3` (parent = `INDEX_FINAL_VALIDATED`)
- 결과 버전: `LOWER_ADAPTER_V1` = `41712f1bb7b025dbdb8b67b4`
- 신규 Part Studio: `OneGrip_LowerAdapter` = `bbfebe9c42748fb6d5b912e8`
- 신규 Feature Studio: `OneGrip_LowerAdapter_FS` = `fad6109b6980934c74639943`
- **상체 Joystick Part Studio 에 대한 쓰기 0건** (§8 증명)
- 판정: **전 항목 PASS.** 짐벌은 착수하지 않았다.

---

## 1. 생성된 부품 / 피처

Part Studio 피처 8개, solid body 4개.

| 피처 | stage | 내용 |
|---|---|---|
| `ADP_A_cradle_blank` | CRADLE_BLANK | 림 외곽 프리즘 + 클램프 이어 6개 union |
| `ADP_B_seat` | CRADLE_SEAT | 착좌 평면 + 림 안쪽 파냄 |
| `ADP_C_boss_pocket` | CRADLE_POCKET | 보스 포켓 |
| `ADP_D_post_cable` | CRADLE_POST | post union + 케이블 보어 |
| `ADP_E_cradle_holes` | CRADLE_HOLES | 웨지 볼트 하공 4 + 이어 하공 6 |
| `ADP_F_wedge` | WEDGE | 웨지 blank + 월드 수평 기준면 절단 |
| `ADP_G_wedge_holes` | WEDGE_HOLES | 관통공 4 + 스포트페이스 4 + 케이블 보어 + 짐벌 하공 4 |
| `ADP_H_clamp_ring` | RING | 클램프 링 2분할 + 관통공 12 |

| body | partId | 부피 | bbox (그립 좌표) |
|---|---|---:|---|
| CRADLE | `JHD` | 68,042.3 mm³ | X[−45.24, 45.24] Y[−19.50, 71.92] Z[−78.08, −53.88] |
| WEDGE | `RoBD` | 149,602.3 mm³ | X[−43.00, 42.99] Y[−14.31, 66.73] Z[−118.32, −78.08] |
| RING_F | `RwCD` | 5,060.8 mm³ | X[−45.11, 45.11] Y[−19.50, 26.00] Z[−64.03, −60.03] |
| RING_B | `RzDD` | 5,054.5 mm³ | X[−45.24, 45.24] Y[26.00, 71.92] Z[−64.03, −60.03] |

합계 227,760 mm³ (**CAD 솔리드 기준**). 웨지가 66 % 를 차지하므로 실제 출력은 인필로 낮춘다.

## 2. 20° 검증 (핵심 수용 조건)

웨지 밑면 = 짐벌 인터페이스 = 월드 수평면. 실제 tessellation 에서 재측정:

```
기준면 facet 858 개, 면적 6174.7 mm2
밑면 법선            (-0.000000, -0.342020, -0.939693)
angle(밑면 법선, 소켓축 +Z)   20.000000 deg      목표 20.000000
밑면 평면도 (최대 facet 편차)  0.007764 deg
```

- `GRIP_AXIS ⟂ TILT_SURFACE` = **90.000000°** (착좌면 법선이 곧 +Z 이고 정의상 항등 성립)
- `TILT_SURFACE ∠ horizontal` = **20.000000°**
- `GRIP_AXIS ∠ global vertical` = **20.000000°**
- 방향: `RotX(+θ)`, 그립 상단이 **−Y (엄지 패널 쪽)** 로 눕는다

**각도는 CAD 상 단 한 곳에만 존재한다** — 웨지의 기준면 절단 (`BASE_PT`, `UP_LOCAL`).
크래들·링·post·포켓은 전부 그립 프레임에서 각도 0 으로 만들어진다.

## 3. 소켓 / post 물림

| 항목 | 설계 | 실측 (tessellation) |
|---|---|---|
| post 단면 | 20.272 × 25.272 | **20.272 × 25.272** |
| 소켓 여유 | X 0.400 / Y 0.200 mm/side | **X 0.400 / Y 0.200** (원본과 동일) |
| 보어 물림 | 20.000 mm | **20.000** (직진 보어 21.000 중) |
| post 끝 ↔ 보어 막힌 끝 | 1.000 mm | **1.000** |
| 보스 포켓 | 31.672 × 36.272 × 6.20 | 여유 0.30 mm/side, 바닥 간극 0.20 |
| 착좌면 | Z = −67.878507 평면 | 정점 468, X[−39.00, 38.99] Y[−10.31, 62.73] |
| post 내부 | 12.272 × 17.272 케이블 보어 | 크래들 밑면까지 관통 |

원본 Pitch post 와 **같은 단면·같은 여유**다. 상체는 원본과 똑같이 끼워진다.

## 4. 체결 / 유지 방식

```
① 평면 착좌  : 5017 mm2 평면이 수직 하중을 받는다 (원본의 좁은 접촉 ~330 mm2 대비 15배)
② 보스 포켓  : 31.672 x 36.272 x 6.2 — 전단 + 회전키 + 쉘 벌어짐 억제
③ post 복제  : 20.272 x 25.272 x 물림 20.0 — 정밀 위치 + 케이블 덕트
④ 클램프 링  : 2분할, 립 물림 5.000 mm(반경), 수직 유격 0.327 mm, M3 x 6
⑤ 크래들-웨지: M3 x 4, (±26, 8) / (±26, 46), 탭 8.0 mm, 웨지 쪽 스포트페이스 6.5
⑥ 짐벌 인터페이스: M3 x 4, 기준면 국소 56 x 44 mm 직사각, 탭 8.0 mm
```

- 나사 규격은 전부 **PROVISIONAL** (M3 급 가정, 관통 3.4 / 셀프탭 하공 2.5)
- 클램프는 **예압형이 아니라 유지형**이다. 20° 에서 중력의 축방향 성분은
  `cos20 = 0.940` 으로 그립을 **착좌면에 눌러 넣는** 방향이므로, 링은 취급 중 이탈만 막으면 된다.
  3 mm 두께 플랜지 가장자리에 예압을 주지 않는다
- **상체는 일절 가공하지 않았다.** 기존 쉘 나사 3개도 사용하지 않는다
  (가장 낮은 것도 착좌면 위 46.5 mm 라 크래들이 닿을 수 없다)

## 5. 치수 / 스택 높이

| 항목 | 값 |
|---|---|
| 크래들 plan (이어 포함) | 90.5 × 91.4 mm |
| 웨지 plan | 86.0 × 81.0 mm |
| 웨지 두께 | **10.095 ~ 37.811 mm** (얇은 쪽 = −Y 내리막, 두꺼운 쪽 = +Y 오르막) |
| 크래들 두께 | 10.20 mm + 림 3.85 mm |
| 클램프 링 | 4.00 mm |
| **추가 스택 높이** | **33.900 mm** (짐벌 인터페이스 평면 → 상체 착좌 평면, 월드 수직) |
| 어댑터 전체 높이 | 0 ~ 56.549 mm |
| 그립 포함 전체 높이 | 0 ~ 145.860 mm |

## 6. 최소 살두께

| 부위 | 값 |
|---|---:|
| 크래들 포켓 바닥 | 4.000 mm |
| post 벽 | 4.000 mm |
| 림 벽 | 4.000 mm |
| 클램프 링 | 4.000 mm |
| 이어 벽 (하공 2.5 기준) | 3.250 mm |
| 웨지 최소 | 10.095 mm |
| **전체 최소** | **3.250 mm** |

모두 원본 쉘 벽 3.0 mm 이상이다.

## 7. 간섭 검사 (0.4 mm 복셀, ray-parity)

**상체는 frozen `INDEX_FINAL_VALIDATED` 메시로 검사했다.**

| 대상 | 겹침영역 복셀 | 어댑터 내부 | 간섭 | 판정 |
|---|---:|---:|---:|---|
| CRADLE ↔ 그립 | 1,988,500 | 558,800 | **0** | PASS |
| WEDGE ↔ 그립 | bbox 겹침 없음 | — | **0** | PASS |
| RING_F ↔ 그립 | 221,160 | 65,580 | **0** | PASS |
| RING_B ↔ 그립 | 176,540 | 52,210 | **0** | PASS |
| CRADLE ↔ RING_F / RING_B | 257,640 / 259,900 | — | **0 / 0** | PASS |
| 그 외 부품쌍 | bbox 겹침 없음 | — | **0** | PASS |

- 크래들 밑면 ↔ 웨지 윗면 간극 **0.000000 mm** (정확히 접촉, 둘 다 Z = −78.078508)
- 기준면 아래로 내려간 웨지 재료 **0.0000 mm**

## 8. 상체 무변화 증명

이 작업의 모든 쓰기는 신규 Part Studio `bbfebe9c42748fb6d5b912e8` 로만 나갔다.

- `lower_adapter/scripts/run_adapter.py` 에 `_guard_eid()` 가 있어
  Joystick Part Studio(`425d9199b59cfb1efd9ddc35`)를 대상으로 하면 예외를 던진다
- 신규 Part Studio 에는 **derive 가 없다.** 상체 body 가 아예 존재하지 않으므로
  이 FeatureScript 는 구조적으로 상체를 수정할 수 없다
- 상체 정합은 전부 `lower_adapter/docs/00` 의 실측 상수로만 보장한다

### ⚠ 다만 상체는 실제로 바뀌었다 — 다른 워크플로가 바꿨다

작업 중 Joystick Part Studio 가 **feature 180 → 192, solid 18 → 22** 로 변했다.
추가된 12개 피처는 전부 `its1105Index` 타입이다:

```
ITS_I1~I4_fixed_root_channel / ITS_I1~I4_rear_spacer / ITS_I1~I4_cap_boss_stop
신규 body: RmND, RqND, RuND, RyND (Part 19~22)
JaD+JfD 부피 97177.9 -> 97141.4 mm3 (-36.5)
```

이는 **병렬 손가락 버튼 워크플로**(docs/32 ITS-1105 감사)의 결과이며 이 작업과 무관하다.
`oneGripLowerAdapter` featureType 은 상체 트리에 **0건**이다.

**영향 확인 완료 (라이브 재측정).** ITS-1105 변경 후의 workspace JaD/JfD 를 새로 받아
하단 인터페이스를 다시 쟀다:

| 항목 | 기준 (`INDEX_FINAL_VALIDATED`) | ITS-1105 이후 라이브 | 차 |
|---|---:|---:|---:|
| 소켓 보어 | 21.0720 × 25.6720 | **21.0720 × 25.6720** | 0.0000 |
| 보스 끝면 Z | −73.8785 | **−73.8785** | 0.0000 |
| 착좌 평면 Z | −67.8785 | **−67.8785** | 0.0000 |
| 보스 외형 X | ±15.536 | **±15.536** | 0.000 |

→ **어댑터 정합 상수 전부 유효.** ITS-1105 피처는 전부 INDEX 버튼 영역(Z ≈ +9)이라
하단을 건드리지 않았다. 캐시: `lower_adapter/cad_dump/mesh_LIVE_JaD/JfD.json`

## 9. 출력 방향

| 부품 | 베드에 붙일 면 | 이유 |
|---|---|---|
| **WEDGE** | **밑면(월드 수평 = 짐벌 인터페이스)** | 가장 중요한 평면을 베드에 붙인다. 86×81 mm 넓은 바닥, 서포트 불필요. 윗면은 20° 경사라 계단이 생기지만 4개 볼트 접촉부만 쓰므로 무해 |
| **CRADLE** | **착좌면(위)을 아래로 뒤집어** | 착좌 평면과 보스 포켓 벽이 베드/수직면이 되어 정밀해진다. post 는 아래로 향하는 돌기가 되어 서포트가 필요하다 → 대안: 밑면을 베드에 붙이면 post 가 수직으로 서서 서포트 0 이지만 층간 굽힘에 약해진다. **전단은 보스 포켓이 받으므로 밑면-베드(서포트 0) 를 권장** |
| **CLAMP RING ×2** | 평판이므로 어느 면이든 | 서포트 0 |

웨지는 인필 15~20 % 로 출력한다 (솔리드 149.6 cm³ 는 과하다).

## 10. 이월 / 미결

- **중력 모멘트** — 사용자 지시대로 이번 단계에서 보상하지 않았다. 기록만 남긴다:

  ```
  원본 수직        약 4020 g·mm
  20도 확정 배치   약 6840 g·mm      증가 약 1.70배
  ```

  실제 해법은 ① 어댑터 물리 확정 ② 최종 가동질량 확정 ③ 실제 센터링 스프링 선정·실측
  ④ 짐벌 피벗 기하 확정 **이후** 결정한다. **Hall 오프셋은 보상 수단이 아니다** —
  전기적 중심만 옮길 뿐 중력 토크를 상쇄하지 못한다 (사용자 정정 반영).
- 나사 규격 확정 (현재 전부 PROVISIONAL)
- `#gimbal_bolt_pattern` 동결 여부 — 현재 기준면 국소 56 × 44 mm 직사각 4×M3
- FDM 프린터·재료 확정 후 `#fdm_clearance` 0.30 재검토
- post 끝 lead-in 챔퍼 미적용 (삽입성 개선용, 0.8 × 45° 권장)
- 캔틸레버 — 20° TOP→−Y 는 그립 머리가 이미 −Y 로 넘어간 방향과 **같은 방향**이라
  머리 끝이 짐벌 인터페이스 기준 수평으로 약 120 mm 바깥까지 나간다
  (`lower_adapter/cad_dump/shot_composite_side.png`). 짐벌·거치 설계에서 반영 필요

## 11. FeatureScript 교훈 (이번에 실제로 막힌 것들)

1. **함수 인자 8개는 거부된다.** 7개까지. 초과하면 컴파일이 **에러 메시지 없이** 실패한다
2. **함수명 `box` 는 std 와 충돌한다.** 같은 증상(조용한 컴파일 실패). `mkBox` 로 회피
3. **body 생성 id 는 반드시 feature 의 `id` 하위여야 한다.** `makeId("문자열")` 로 만들면
   feature 가 ERROR 가 된다. 앞 단계 body 를 되찾을 때만 `makeId(featureId)` 를 쓴다
4. **`qCreatedBy(id, EntityType.BODY)` 는 스케치 wire body 도 잡는다.** boolean tool 에
   그대로 넣으면 실패한다 → `qBodyType(..., BodyType.SOLID)` 로 감싼다
5. Onshape 는 feature ERROR 의 **메시지를 API 로 주지 않는다.** `/featurescript` 평가
   엔드포인트는 top-level 에서 익명 함수 하나만 받으므로 진단기로 쓰기 어렵다.
   결국 **단계를 잘라 올려 이분 탐색**하는 것이 가장 빨랐다

## 12. 재현

```bash
python lower_adapter/scripts/gen_adapter_constants.py   # 상수 생성 + 사전 검증
python lower_adapter/scripts/run_adapter.py upload      # FS 업로드
python lower_adapter/scripts/run_adapter.py add CRADLE_BLANK ADP_A_cradle_blank
# ... B~H (cradleId / wedgeId 인자는 앞 단계 featureId)
python lower_adapter/scripts/verify_adapter.py --fetch  # 전 항목 검증
python lower_adapter/scripts/shots.py                   # 렌더 + 합성 측면도
```
