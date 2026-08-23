# INDEX FINAL body inventory READ-ONLY audit

- 감사 대상: `INDEX_SHARED_RET_FINAL` (`6703cd9cbd0d5e321ac10b87`) →
  `INDEX_FINAL_VALIDATED` (`03ede76e83b5c865d9a69c35`)
- Part Studio: `Joystick` (`425d9199b59cfb1efd9ddc35`)
- 감사 방식: **Onshape GET only**
- CAD WRITE: **0건** — Feature 생성/수정/삭제/suppress 및 version 생성 없음
- 원시 결과: `cad_dump/index_final_body_inventory_audit.json`

## A. 동일 기준 최종 solid count

두 version을 아래의 완전히 동일한 기준으로 다시 계산했다.

```text
endpoint   GET /parts/d/a21e64f36bc61df760d4587c/v/{versionId}/e/425d9199b59cfb1efd9ddc35
filter     bodyType == "solid"
count      filter를 통과한 part record 수
```

| version | 전체 part record | solid | wire |
|---|---:|---:|---:|
| `INDEX_SHARED_RET_FINAL` | 19 | **17** | 2 |
| `INDEX_FINAL_VALIDATED` | 20 | **18** | 2 |

따라서 동일 기준의 실제 변화는 **solid 17 → 18**, 즉 **+1**이다.
현재 최종 solid count는 **18**이며 감소한 body는 없다.

두 wire는 양쪽 version에서 동일하다.

- `Curve 1` — `JMD`
- `Curve 2` — `RNDD`

### 최종 solid body inventory

부피는 같은 version-specific `massproperties?partId={partId}` 응답의 nominal
`volume[0] × 10^9`를 mm³로 환산했다.

| part name | partId | volume (mm³) | owning / creating feature | JaD/JfD | RWID | RZKD |
|---|---|---:|---|---|---|---|
| Joystick_1 | `JaD` | 47,492.700587 | `Enclose 1` `FdflGREM19IRypF_1` | **JaD** | — | — |
| Joystick_2 | `JfD` | 49,685.197185 | `Mirror 1` `FfyGpppYw8McLsz_2` | **JfD** | — | — |
| Backplate | `RYDD` | 5,899.945734 | `Sweep 1` `FR1RGAmsfokIVzQ_4` | — | — | — |
| Button_wide_1 | `RAED` | 288.485949 | `Extrude 17` `FN60hLJrErylbKr_5` | — | — | — |
| Button_side_1 | `RAEH` | 271.040394 | `Extrude 17` `FN60hLJrErylbKr_5` | — | — | — |
| Button_corner_1 | `RAEL` | 199.440181 | `Extrude 17` `FN60hLJrErylbKr_5` | — | — | — |
| Button_corner_2 | `RBED` | 199.440185 | `Extrude 23` `F5f2Bqv3P4yttCY_8` | — | — | — |
| Button_side_2 | `RBEH` | 271.040394 | `Extrude 23` `F5f2Bqv3P4yttCY_8` | — | — | — |
| Button_wide_2 | `RBEL` | 288.485949 | `Extrude 23` `F5f2Bqv3P4yttCY_8` | — | — | — |
| Button_middle_1 | `RDED` | 275.054087 | `Extrude 24` `FhTqxuAvjIWGQgW_11` | — | — | — |
| Button_middle_2 | `RDEH` | 275.054087 | `Extrude 24` `FhTqxuAvjIWGQgW_11` | — | — | — |
| Small_joystick_attachment | `RHED` | 284.540889 | `Extrude 25` `FTcXnBBgATAer7g_13` | — | — | — |
| Part 13 | `R4ED` | 231.040000 | `INDEX_button_caps` `FSAYT6HrIBkapCP_14` | — | — | — |
| Part 14 | `R9ED` | 231.040000 | `INDEX_button_caps` `FSAYT6HrIBkapCP_14` | — | — | — |
| Part 15 | `RCFD` | 231.040000 | `INDEX_button_caps` `FSAYT6HrIBkapCP_14` | — | — | — |
| Part 16 | `RHFD` | 231.040000 | `INDEX_button_caps` `FSAYT6HrIBkapCP_14` | — | — | — |
| Part 17 | `RWID` | 2,136.305048 | `RET_blank` `Fq5IPkiwWk5pWYv_15` | — | **YES** | — |
| Part 18 | `RZKD` | 284.959443 | `I4_retainer_blank` `F2N4HZlwCZvkovM_16` | — | — | **YES** |

## B. JaD

- `Joystick_1 = JaD`: **존재**, 이름·partId·ordinal 1 유지
- body 수: 1
- final volume: **47,492.700587 mm³**
- checkpoint 대비 nominal volume: **+74.799158 mm³**
- tessellation: 17,250 → 17,712 triangles
- 원인: 의도된 `I4_JaD_boss` (`FP31q74LciCNpK9_17`)와
  `I4_screw_hole` (`FWR7cU5dM92MTjy_17`) downstream geometry

JaD identity는 정상이며 split·소멸·partId 교체가 없다.

## C. JfD

- `Joystick_2 = JfD`: **존재**, 이름·partId·ordinal 2 유지
- body 수: 1
- final volume: **49,685.197185 mm³**
- B-rep topology: **276 vertices / 427 edges / 145 faces**, 두 version 동일
- topology entity ID set: vertices / edges / faces 모두 동일
- bodydetails vertex 최대 좌표 편차: **0.000000745 mm**
- tessellation 고유 정점 최대 최근접 편차: **0.00000273 mm**

그러나 immutable version끼리 새로 받은 raw tessellation은 strict SHA-256이 다르다.

| 항목 | checkpoint | final |
|---|---:|---:|
| triangles | 16,910 | 16,910 |
| canonical raw tess hash | `a04195a3...` | `f80d0cb5...` |
| tess mesh volume (mm³) | 49,670.423116 | 49,670.428521 |
| nominal massproperties volume (mm³) | 49,684.740878 | 49,685.197185 |

Onshape tessellation은 저장된 영구 형상이 아니라 요청 시 생성된다.
([Onshape Architecture](https://onshape-public.github.io/docs/api-intro/architecture/))
따라서 위 차이는 partId·topology·실질 표면이 바뀐 증거가 아니라 regeneration의
수치적 jitter로 판단된다. 0.01 mm 정규화 B-rep geometry hash는 동일하다.

다만 이번 감사의 strict 조건인 **“fingerprint/volume exact unchanged”**는
두 고정 version의 fresh GET 결과로 그대로 재현되지 않았다. 이 점은 최종 게이트에 반영한다.

## D. RWID

- shared retainer `RWID`: **존재**, single independent solid
- final volume: **2,136.305048 mm³**
- RZKD와 partId가 다르며 union되지 않음
- tessellation: **2,112 → 2,112 triangles**, canonical hash exact same
- tess mesh volume: **2,136.463389 → 2,136.463389 mm³**, exact same
- B-rep: **206 vertices / 312 edges / 108 faces**, exact same
- normalized full bodydetails SHA-256:
  `9f0ded67dca482344d8f382ba2e6a87f8edd1567ad7591af35c9e41556d013ce`
  — 양쪽 version exact same

`RET_blank`부터 `RET_hole_B`까지 shared feature 12개의 정의도 version 간 exact same이다.
따라서 RWID 본체, EAR_A′, EAR_B′, shared service relief는 무변화다.

## E. RZKD

- I4 retainer `RZKD`: **존재**, single independent solid
- final volume: **284.959443 mm³**
- creating feature: `I4_retainer_blank` (`F2N4HZlwCZvkovM_16`)
- RWID와 독립된 별도 part record이며 union·흡수 관계 없음
- checkpoint에는 없고 final에만 존재

따라서 **RWID와 RZKD는 서로 독립된 NEW PART**임이 확인됐다.

## F. checkpoint 간 added / removed / changed solids

### partId set diff

```text
added    RZKD
removed  none
```

소멸한 partId가 없으므로 union 흡수, suppression, 삭제 또는 body-loss는 발생하지 않았다.

### geometry diff 분류

| partId | 분류 | 근거 |
|---|---|---|
| `RZKD` | **ADDED — intended** | 별도 I4 retainer |
| `JaD` | **CHANGED — intended** | I4 boss + pilot/clearance downstream geometry |
| `JfD` | numeric regeneration drift | identity/topology 동일, raw hash·nominal volume만 극미세 차이 |
| `RYDD` | kernel regeneration/topology healing | V/E/F 186/283/85 → 184/281/85, face set 유지, nominal volume −0.063918 mm³ |

`RYDD`의 변경은 I4 boolean target이 아니다. I4의 JaD 선택점은 `z=-35mm`이고
RYDD bbox는 `z=28.547..73.368mm`이며, 나머지 I4 단계는 `qCreatedBy(RZKD)`만 대상으로 한다.
따라서 작성된 I4 형상이 Backplate를 절삭한 것이 아니라 전체 Part Studio regeneration에서
edge 두 개가 healing/reparameterization된 것으로 분류한다. body identity와 face 수는 유지된다.

그 외 공통 solid 14개는 nominal volume과 canonical tessellation fingerprint가 동일하다.

## G. 왜 19 → 18처럼 보고됐는가

원인은 **body 소멸이 아니라 counting rule 혼용**이다.

과거 retainer 실행기의 `scripts/run_retainer.py` `solids()`는 `/parts` 응답을
`bodyType` 필터 없이 전부 셌다. 따라서 다음을 “solid”라고 잘못 표기했다.

```text
holder 완료      16 actual solids + 2 wires = 기록 18
shared RWID 후   17 actual solids + 2 wires = 기록 19
```

I4 실행기의 `scripts/run_i4_retainer.py` health 집계는
`bodyType == "solid"` 필터를 사용하여 final을 18로 보고했다.

동일 규칙으로 다시 쓰면 다음 두 표현 모두 일관된다.

```text
all part records   19 -> 20
solid-only         17 -> 18
```

endpoint 자체는 `/parts`로 동일하다. 차이는 API endpoint, suppression 또는 regeneration이
아니라 **wire 2개를 포함했는지 여부**다.

양쪽 version에서 suppressed feature는 기존 `INDEX_switch_pockets`
(`FkGjuaVRtcptOX1_14`) 한 개로 동일하므로 count 차이에 영향을 주지 않는다.

## H. assembly / regeneration

| gate | checkpoint | final | 결과 |
|---|---:|---:|---|
| feature count | 174 | 180 | I4 6개 append |
| OK | 174 | 180 | PASS |
| ERROR | 0 | 0 | PASS |
| WARNING | 0 | 0 | PASS |
| isComplete | true | true | PASS |
| assembly instances | 25 | 25 | PASS |
| active instances | 25 | 25 | PASS |
| occurrences | 25 | 25 | PASS |
| suppressed instances | 0 | 0 | PASS |
| dangling | 0 | 0 | PASS |

assembly는 **25/25, dangling 0**이다.

## I. INDEX FINAL CONFIRMED / HOLD

### **INDEX FINAL SUCCESS = HOLD**

| final gate | 결과 |
|---|---|
| JaD 존재 / identity | PASS |
| JfD 존재 / identity | PASS |
| RWID independent part | PASS |
| RZKD independent part | PASS |
| ERROR 0 / WARNING 0 | PASS |
| assembly 25/25 | PASS |
| dangling 0 | PASS |
| solid-count 설명 | PASS — 17→18, 과거 wire 포함 오집계 |
| RWID/shared feature exact unchanged | PASS |
| JfD raw fingerprint + volume exact unchanged | **FAIL — fresh version-to-version GET에서 재현 안 됨** |

실제 solid 감소나 identity 손실은 없다. JfD 차이는 나노미터급 regeneration jitter이며
공학적으로는 동일하지만, 사용자 지시의 strict **exact fingerprint/volume** 조건을 임의로
완화하지 않는다. 따라서 원인만 보고하고 CAD는 수정하지 않는다.

## J. MIDDLE GO / HOLD

### **MIDDLE = HOLD**

body inventory와 count 문제 자체는 정상이다. 그러나 INDEX FINAL의 strict shared fingerprint
게이트 한 항목이 literal exact 기준을 통과하지 못했으므로 MIDDLE로 진행하지 않는다.

이번 감사 종료 시점까지 CAD WRITE는 **0건**이다.
