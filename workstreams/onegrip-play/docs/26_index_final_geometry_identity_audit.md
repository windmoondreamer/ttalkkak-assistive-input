# INDEX FINAL geometry identity READ-ONLY audit

- 대상 V1: `INDEX_SHARED_RET_FINAL` (`6703cd9cbd0d5e321ac10b87`)
- 대상 V2: `INDEX_FINAL_VALIDATED` (`03ede76e83b5c865d9a69c35`)
- Part Studio: `Joystick` (`425d9199b59cfb1efd9ddc35`)
- 방식: **authenticated GET only**
- CAD WRITE: **0건** — Feature 생성/수정/삭제/suppress 및 version 생성 없음
- 이 문서는 docs/25의 raw tessellation hash·nominal scalar exact gate를
  Onshape API 특성에 맞게 재평가한다.

## A. explicit configuration

두 version의 configuration endpoint 결과는 동일하다.

```text
currentConfiguration    []
configurationParameters []
```

즉 Joystick은 configuration input이 없는 Part Studio다. 그래도 implicit/current 상태를
사용하지 않고 모든 비교 GET에 아래 값을 명시했다.

```text
configuration=default
```

| 비교 | 동일 endpoint / explicit query parameters |
|---|---|
| inventory | `GET /parts/.../v/{versionId}/e/... ?configuration=default` |
| mass properties | `GET /partstudios/.../massproperties?configuration=default&partId=JfD` |
| B-rep | `GET /parts/.../partid/JfD/bodydetails?configuration=default` |
| tessellation | `configuration=default`, `partId=JfD`, angle `0.09`, chord `0.1` |
| feature tree | `configuration=default`, `noSketchGeometry=true` |
| assembly | `configuration=default` |

두 대상은 동일 document, 동일 Part Studio, 동일 configuration, 동일 endpoint와 동일 query
parameters로 비교됐다. Onshape configuration parameter 사용 원칙은
[공식 Configurations 문서](https://onshape-public.github.io/docs/api-adv/configs/)를 따른다.

## B. JfD V1 volume [nominal / lower / upper]

`INDEX_SHARED_RET_FINAL`의 `volume` 배열은 다음과 같다.

```text
raw m³   [0.00004968474087790842,
          0.000047941278759478154,
          0.00005142820299633858]

nominal  49,684.740877908422 mm³
lower    47,941.278759478155 mm³
upper    51,428.202996338579 mm³
```

응답 microversion은 `8c1c46dca02a771746d4a15b`다.

## C. JfD V2 volume [nominal / lower / upper]

`INDEX_FINAL_VALIDATED`의 `volume` 배열은 다음과 같다.

```text
raw m³   [0.00004968519718520176,
          0.000047946536778740046,
          0.00005142385759166344]

nominal  49,685.197185201760 mm³
lower    47,946.536778740046 mm³
upper    51,423.857591663444 mm³
```

응답 microversion은 `fa76ab8dec2c7df3d6b1a48a`다.

## D. absolute volume difference

```text
|V2_nominal - V1_nominal| = 0.456307293338 mm³
```

## E. relative volume difference

V1 nominal을 기준으로 계산했다.

```text
0.456307293338 / 49,684.740877908422
= 0.000009184052996
= 0.000918405300 %
```

## F. tolerance interval overlap

두 interval은 다음과 같다.

```text
V1  [47,941.278759478155, 51,428.202996338579] mm³
V2  [47,946.536778740046, 51,423.857591663444] mm³
```

교집합은 다음과 같다.

```text
[47,946.536778740046, 51,423.857591663444] mm³
overlap width = 3,477.320812923397 mm³
```

따라서 interval은 명확하게 겹친다. nominal difference `0.456307mm³`는 가장 작은
nominal-to-bound 폭의 `0.0262448%`에 불과하여 API numerical/tolerance 범위 안이다.

| volume gate | 결과 |
|---|---|
| tolerance intervals overlap | **PASS** |
| nominal difference within tolerance | **PASS** |
| B-rep topology same | **PASS** |
| part identity same | **PASS** |

결론: **JfD volume = compatible / geometry unchanged**.

## G. B-rep topology comparison

`configuration=default`를 명시한 part-specific bodydetails 결과다.

| primary identity item | V1 | V2 | 결과 |
|---|---:|---:|---|
| intended body / partId | `JfD` | `JfD` | PASS |
| part name | `Joystick_2` | `Joystick_2` | PASS |
| body count | 1 | 1 | PASS |
| vertices | 276 | 276 | PASS |
| edges | 427 | 427 | PASS |
| faces | 145 | 145 | PASS |
| vertex entity ID set | 동일 | 동일 | PASS |
| edge entity ID set | 동일 | 동일 | PASS |
| face entity ID set | 동일 | 동일 | PASS |
| added / removed topology entities | 0 / 0 | 0 / 0 | PASS |

따라서 JfD identity와 B-rep topology는 동일하다.

### shared-side feature definitions

다음 12개 feature definition은 `configuration=default`에서 version 간 JSON exact same이다.

1. `RET_blank`
2. `RET_cut_holders`
3. `RET_cut_screwB`
4. `RET_pads` — PAD_I1/I2/I3
5. `RET_wire_slots` — wiring slots
6. `RET_cut_shell`
7. `INDEX_retainer_service_relief`
8. `RET_ear_A`
9. `RET_ear_B`
10. `RET_shell_boss_B` — JfD shared fastening
11. `RET_hole_A`
12. `RET_hole_B`

definition group SHA-256은 양쪽 모두
`bb2a1cc3e66f22f8d36b8e8d85c018896831439145cd4ee757cd0494a8867e99`다.

RWID full B-rep도 **206 vertices / 312 edges / 108 faces**로 exact same이며,
양쪽 bodydetails SHA-256은
`9f0ded67dca482344d8f382ba2e6a87f8edd1567ad7591af35c9e41556d013ce`다.

따라서 RWID, EAR_A′, EAR_B′, shared service relief, pads, wiring slots 및 JfD fastening
definitions는 변경되지 않았다.

## H. coordinate deviation

동일 vertex entity ID끼리 bodydetails 좌표를 비교했다.

```text
maximum coordinate deviation = 0.000000745244742 mm
vertices with deviation > 0.000001 mm = 0
```

이는 B-rep identity 또는 공학적 형상 변화가 아니라 regeneration numerical noise 수준이다.

## I. tessellation hash 처리 결론

Onshape 공식 Architecture 문서에 따르면 tessellated data는 persistent model data가 아니며
API 요청 시 on-demand로 생성된다.
([Onshape Architecture](https://onshape-public.github.io/docs/api-intro/architecture/))

따라서 raw tessellation SHA-256 exact equality는 **FINAL identity gate에서 제외**한다.

| tessellation sanity item | V1 | V2 | 결론 |
|---|---:|---:|---|
| triangles | 16,910 | 16,910 | 동일 |
| bbox min | `[-38.779296, -61.419807, -73.878512]` | 동일 | 정상 |
| bbox max | `[0, 62.427491, 78.242071]` | 동일 | 정상 |
| raw canonical hash | mismatch | mismatch | 기록만 유지, gate 제외 |

raw hash mismatch는 geometry sanity failure가 아니며 HOLD 사유가 아니다.

## J. body inventory 17 → 18

동일 endpoint와 `bodyType == "solid"` 규칙, explicit `configuration=default`로 재계산했다.

| version | all part records | solids | wires |
|---|---:|---:|---:|
| INDEX_SHARED_RET_FINAL | 19 | **17** | 2 |
| INDEX_FINAL_VALIDATED | 20 | **18** | 2 |

과거 `solid 19`는 **17 solid + Curve wire 2개**를 합산한 reporting error로 확정한다.

## K. added / removed

```text
added solid    RZKD
removed solid  none
```

- `JaD`: 존재, identity 정상, 의도된 I4 boss downstream geometry
- `JfD`: 존재, identity/topology 정상
- `RWID`: independent solid, exact B-rep 유지
- `RZKD`: independent solid, final에 별도 추가
- RWID와 RZKD 사이 union·흡수·소멸 없음

## L. assembly / regeneration

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

기존 suppressed `INDEX_switch_pockets` 한 개는 양쪽 version에서 동일하며 이번 감사에서
suppress 변경은 수행하지 않았다.

## M. INDEX FINAL CONFIRMED / HOLD

### **INDEX FINAL SUCCESS = CONFIRMED**

| final gate | 결과 |
|---|---|
| JaD 정상 | PASS |
| JfD 정상 | PASS |
| RWID independent solid | PASS |
| RZKD independent solid | PASS |
| added RZKD / removed 0 | PASS |
| JfD topology 동일 | PASS |
| shared feature definitions 동일 | PASS, exact |
| mass-property tolerance compatible | PASS, interval overlap |
| coordinate deviation numerical noise | PASS, max 0.000000745mm |
| ERROR 0 / WARNING 0 | PASS |
| assembly 25/25 / dangling 0 | PASS |

docs/25의 두 HOLD 사유는 다음과 같이 해소됐다.

1. raw tessellation hash mismatch: on-demand approximation이므로 primary gate에서 제외
2. nominal volume mismatch: 전체 tolerance interval이 겹치므로 compatible

## N. MIDDLE GO / HOLD

### **MIDDLE = GO**

INDEX FINAL geometry identity gate가 전부 통과했다.

이번 재감사 종료 시점까지 CAD WRITE는 **0건**이다.
