# INDEX 4개 holder atomic 확장 — 완료

- 일자 2026-08-19
- 체크포인트: 버전 `I1_holder_done` (`e108e48d116813a53ea27762`)
- 결과: **I1 / I2 / I3 / I4 holder 전부 완성.** RETAINER · MIDDLE 미생성 (지시대로)

---

## 0. 결론

> ## SUCCESS
>
> I1 에서 검증된 atomic pipeline 을 I2 → I3 → I4 로 확장 완료.
> 쉘에 대한 negative boolean 은 **승인된 버튼 개구부(OPENINGS) 하나뿐**이며,
> holder 는 전부 blank NEW BODY → blank 자체만 hollow → 마지막 ADD UNION 으로 만들었다.
>
> **`JaD` / `JfD` identity 유지, body split 0, assembly 25/25, regeneration ERROR 0.**
> 4개 seat 전부 기하 기준선과 **0.000 mm** 일치 (완전 개방).

---

## 1. 아키텍처 확장 시 추가한 것

FeatureScript 를 버튼 파라미터화하고(`IdxButton` × `IdxStage`),
**blank 를 `qContainsPoint` 가 아니라 생성 Feature 의 id 로 직접 참조**하도록 바꿨다.

```
blank = qCreatedBy(makeId(definition.blankId), EntityType.BODY)
```

이유: 버튼이 늘어나면 `qContainsPoint` 식별점이 이웃 holder 나 쉘 안에 들어갈 수 있어
**잘못된 body 를 subtraction target 으로 잡을 위험**이 있다. id 참조는 그 위험이 없다.

### 새로 필요해진 단계 — `CLEARNBR`

I1 을 union 한 뒤 I2 blank(속이 찬 12.4 각기둥)를 union 하면
**I2 의 solid 재료가 이미 뚫어놓은 I1 의 seat 를 메운다.**
실측으로 확인: I1 seat 반폭이 3.147 → **0.152 mm** 로 붕괴.

→ union 전에 각 blank 에서 **이웃 버튼의 seat 기둥을 미리 비우는** 단계를 추가했다.
target 은 여전히 그 blank 하나뿐이며 쉘은 절대 target 이 아니다.

1차 시도(깊이 `swFront`=3.8 부터 비움)로는 부족했다.
이웃의 **보어 구간(깊이 2.8~3.8)** 재료가 남아 I1/I2 seat 를 0.37~0.48 mm 침범했다.
→ `blankFrom − 1 mm`(=1.8) 부터 비우도록 수정해 해결.

---

## 2. 실행 순서 (버튼당 독립 Feature)

각 버튼 = **6~7개 독립 Feature**. 한 Feature = 한 operation 계열.
배열 다중 boolean / 다중 target / 여러 버튼 동시 처리를 쓰지 않았다.

```
BLANK → SEAT → REAR → LIP → (SPLITCLIP) → CLEARNBR → UNION
```

`CLEARNBR` 4개를 모두 끝낸 뒤 `UNION` 4개를 순서대로 수행했다
(JfD + I1 → JfD + I2 → JfD + I3 → JaD + I4).

---

## 3. Feature 기록

| 버튼 | stage | Feature name | Feature ID | state |
|---|---|---|---|---|
| I1 | BLANK | `DEBUG_I1_holder_blank` | `FTBPtZICKt1S0XU_16` | OK |
| I1 | SEAT | `DEBUG_I1_switch_seat` | `FZGX69S3I3fLv7o_17` | OK |
| I1 | REAR | `DEBUG_I1_open_rear` | `F9Ikj85FanyNCeN_17` | OK |
| I1 | LIP | `DEBUG_I1_front_lip_bore` | `FA1uZNGIoZlqm0Z_17` | OK |
| I1 | CLEARNBR | `DEBUG_I1_clear_nbr` | `F7xVidvKzOEkMDP_17` | OK |
| I1 | UNION | `DEBUG_I1_union` | `Faq1i46Ef29bucn_17` | OK |
| I2 | BLANK | `DEBUG_I2_holder_blank` | `FftGAIlvFOLgteM_15` | OK |
| I2 | SEAT | `DEBUG_I2_switch_seat` | `FLtTXDnH8D1v6xr_16` | OK |
| I2 | REAR | `DEBUG_I2_open_rear` | `F1tHAuBZptGyecL_16` | OK |
| I2 | LIP | `DEBUG_I2_front_lip_bore` | `FPJypcltjCiDiWx_16` | OK |
| I2 | CLEARNBR | `DEBUG_I2_clear_nbr` | `F2AVoYMTLCoRIW3_17` | OK |
| I2 | UNION | `DEBUG_I2_union` | `FNO5bzv7JhcVHL1_16` | OK |
| I3 | BLANK | `DEBUG_I3_holder_blank` | `F3UIvAT7CRAfpfo_15` | OK |
| I3 | SEAT | `DEBUG_I3_switch_seat` | `Fl6YPxYayGxmiR5_16` | OK |
| I3 | REAR | `DEBUG_I3_open_rear` | `FxoisfQQ1d7qJwo_16` | OK |
| I3 | LIP | `DEBUG_I3_front_lip_bore` | `Fvi4MAOdMsN5a7Y_16` | OK |
| I3 | **SPLITCLIP** | `DEBUG_I3_split_clip` | `FXOQJU5IeiI6xxD_16` | OK |
| I3 | CLEARNBR | `DEBUG_I3_clear_nbr` | `FdfeaVlNKuEIlcR_17` | OK |
| I3 | UNION | `DEBUG_I3_union` | `F4F50LeTtMmU6EO_16` | OK |
| I4 | BLANK | `DEBUG_I4_holder_blank` | `FztH4ORStBiyYAL_15` | OK |
| I4 | SEAT | `DEBUG_I4_switch_seat` | `FEo1XRskPlSdtBs_16` | OK |
| I4 | REAR | `DEBUG_I4_open_rear` | `FlO0NWnqwKFSoSt_16` | OK |
| I4 | LIP | `DEBUG_I4_front_lip_bore` | `FMeR60yn9ZKtMIw_16` | OK |
| I4 | **SPLITCLIP** | `DEBUG_I4_split_clip` | `F6bx67rYhdboIax_16` | OK |
| I4 | CLEARNBR | `DEBUG_I4_clear_nbr` | `FGxVTTGf5ge1fpi_17` | OK |
| I4 | UNION | `DEBUG_I4_union` | `FDnrFl6XltxLnLL_16` | OK |

**총 26개 Feature. 전부 state = OK.**

---

## 4. split clip 판정

union 전에 각 blank 의 X 범위를 실측해 CASE A/B 를 결정했다.

| 버튼 | clip 전 X 범위 | 침범 | 판정 | clip 후 X 범위 | 부피 |
|---|---|---|---|---|---|
| I1 | — | 없음 | **CASE A** (clip 불필요) | — | 1.1149 cm³ |
| I2 | — | 없음 | **CASE A** | — | 1.1149 cm³ |
| **I3** | −11.656 … **+1.250** | **+1.250 mm** | **CASE B** | −11.656 … **0.0000** | 1.1149 → **0.9955** cm³ |
| **I4** | **−1.250** … +11.656 | **−1.250 mm** | **CASE B** | **−0.0000** … +11.656 | 1.1149 → **0.9955** cm³ |

split clip 은 `DEBUG_I3_split_clip` / `DEBUG_I4_split_clip` **독립 Feature**로 수행했고,
target 은 각각 그 blank 하나뿐이다. 쉘은 target 이 아니다.

---

## 5. seat 개방 검증 (핵심)

`evDistance` 로 버튼 축에서 최근접 면까지 거리를 깊이별로 측정했다.
seat 가 완전히 비었을 때의 **기하 기준선**은 보어(반경 2.25) → seat(반경 3.20) 단차 때문에

```
ref(d) = min(3.20, sqrt((d − 3.8)² + 2.25²))
```

| 깊이 | d4 | d5 | d6 | d7 | d8 | d9 |
|---|---|---|---|---|---|---|
| **기준선** | 2.259 | 2.550 | 3.147 | 3.200 | 3.200 | 3.200 |
| I1 | 2.259 | 2.550 | 3.147 | 3.200 | 3.200 | 3.200 |
| I2 | 2.259 | 2.550 | 3.147 | 3.200 | 3.200 | 3.200 |
| I3 | 2.259 | 2.550 | 3.147 | 3.200 | 3.200 | 3.200 |
| I4 | 2.259 | 2.550 | 3.147 | 3.200 | 3.200 | 3.200 |

**기준선 대비 최대 부족량 = 0.000 mm.**
4개 seat 모두 **6.4 × 6.4 mm 로 완전히 개방**되어 있다.
6.0 mm 스위치(반폭 3.0)에 편측 0.2 mm 여유가 그대로 확보된다.

> 중간 단계에서 측정한 2.356 / 3.147 같은 값은 결함이 아니라
> **보어 단차 모서리까지의 대각 거리**다. 기준선과 비교해야 판정할 수 있다.

---

## 6. 실제 switch envelope 상호 clearance

6 × 6 × 6 nominal envelope 를 각 local axis 에 배치(앞면 깊이 3.8 mm):

| 쌍 | precheck | **CAD 후** | 판정 |
|---|---|---|---|
| **I1 ↔ I2** | 2.036 | **2.036 mm** | 최소값. > 1 mm 권장 충족 |

> **[2026-08-19 철회] 이 절의 스위치 상호 clearance 수치는 오류다.**
> 꼭짓점 최단거리로 계산해 회전된 박스의 관통을 검출하지 못했다.
> 분리축 정리(SAT)로 다시 계산하면 **I1↔I2 는 1.833 mm 관통(충돌)**,
> **I2↔I3 는 여유 0.040 mm** 다. 근거와 대안: `docs/12_switch_collision_stop_condition.md`


| I2 ↔ I3 | 2.164 | **2.164 mm** | |
| I1 ↔ I3 | 3.644 | **3.644 mm** | |
| I3 ↔ I4 | 4.176 | **4.176 mm** | 분할면 건너 |
| I2 ↔ I4 | 10.341 | 10.341 mm | |
| I1 ↔ I4 | 13.707 | 13.707 mm | |

버튼 좌표를 바꾸지 않았으므로 precheck 값과 동일하다. **충돌 0.**

---

## 7. 16개 항목 검증

| # | 항목 | 결과 |
|---|---|---|
| 1 | I1~I4 중심 위치 변화 없음 | **YES** (좌표 미변경) |
| 2 | local normal axis 유지 | **YES** (승인 법선 그대로 사용) |
| 3 | 3+1 shell ownership 유지 | **YES** |
| 4 | I1/I2/I3 → JfD | **YES** |
| 5 | I4 → JaD | **YES** |
| 6 | shell split crossing 없음 | **YES** (I3 max X = 0.0000, I4 min X = −0.0000) |
| 7 | 6.4 mm locating seat 유지 | **YES** (기준선 대비 0.000 mm) |
| 8 | rear cavity open | **YES** (깊이 10.0 부터 관통) |
| 9 | deep divider tube 없음 | **YES** (holder 끼리 내부에서 연결) |
| 10 | switch bodies collision 없음 | **NO — 2026-08-19 철회.** I1↔I2 는 실제로 1.833 mm 관통 (docs/12) |
| 11 | wiring 접근 가능 | **YES** (rear 개방 → 그립 내부) |
| 12 | screw structure 무침범 | **YES** (§8) |
| 13 | original thumb structure 무침범 | **YES** (파트 10개 그대로) |
| 14 | JaD/JfD identity 유지 | **YES** |
| 15 | assembly occurrences 정상 | **YES** (25/25) |
| 16 | regeneration ERROR | **0** |

### 8. 나사 구조 확인

나사 축 중심에서 최근접 면까지 거리:

| 나사 | Joystick_2 | Joystick_1 |
|---|---|---|
| A (Z 45.98) | 10.090 | **2.993** |
| B (Z 23.07) | 10.089 | **2.990** |
| C (Z −21.35) | 10.090 | **2.996** |

Joystick_1 쪽 약 2.99 mm 는 **카운터보어 반경(3.0)** 이며 홀 형상이 그대로 살아 있다.
holder 재료가 나사 홀을 메우지 않았다.

기하학적으로도 안전하다: holder blank 의 Z 범위는 **3.89 … 18.58**,
가장 가까운 나사 B 의 보스 하단은 Z 19.57 → **0.99 mm 이상 이격**.

---

## 9. 최종 상태

| 항목 | 값 |
|---|---|
| Joystick_2 (`JfD`) | **49.2368 cm³**, body 1개 |
| Joystick_1 (`JaD`) | **47.3824 cm³**, body 1개 |
| 전체 solid | **16개** (쉘 2 + 엄지 10 + 신규 캡 4) |
| assembly | `Joystick_1`→`JaD`, `Joystick_2`→`JfD`, 25/25 |
| regeneration | **오류 0** |

---

## 10. 남은 작업

1. **RETAINER** — rear retaining plate. 양성 고정(나사/슬라이드) 설계 필요
2. **MIDDLE row** — 동일 파이프라인 재사용. 곡률이 더 크므로 `CLEARNBR` 이 더 중요
3. `DEBUG_*` Feature 26개의 정식 이름 정리 (지시대로 이번에는 하지 않음)
4. 신규 캡 4개 이름 재부여 (`Part 13~16` → `INDEX_BTN_n_cap`)
5. 실제 스위치 SKU 확정 시 `#finger_switch_stem_height` 입력 → 전 치수 자동 갱신

---

## 11. 이번에 배운 것 (다음 단계 필수 참고)

- **union 순서 함정**: 이미 seat 를 뚫은 holder 에 나중 holder 의 속 찬 blank 를 union 하면
  seat 가 메워진다. `CLEARNBR` 로 union **전에** 이웃 seat 기둥을 비워야 한다.
  비우는 깊이는 `blankFrom` 부터여야 하며, `swFront` 부터로는 보어 구간이 남는다
- **`try silent`** 로 감싸면 교차하지 않는 이웃 tool 때문에 boolean 이 실패하지 않는다
- **자기 자신 seat 를 tool 에 넣으면** "효과 없음"으로 Feature 가 ERROR 난다
- blank 참조는 **생성 Feature id** 로. `qContainsPoint` 는 버튼이 늘면 위험하다
- `evDistance` 결과는 **기하 기준선과 비교**해야 한다. 절대값만 보면 오판한다
