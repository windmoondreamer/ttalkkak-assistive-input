# ITS-1105 오른손 미러 최종 보고

## 결과

왼손으로 사용할 현재 완성본은 변경하지 않고, 해당 immutable version에서 별도 작업공간을 분기해 오른손용 좌우 대칭본을 완성했다.

- source version: `ITS1105_SAME_SKU_8BTN_FINAL`
- source versionId: `e05a9ff0fa5a7bd51eb848a7`
- right-hand workspace: `RIGHT_HAND_MIRROR`
- workspaceId: `db3d780eca8b1efe55a0dadd`
- right-hand final version: `ITS1105_RIGHT_HAND_8BTN_FINAL`
- right-hand versionId: `f24e655bc9b1b5dc97189a55`
- configuration: `default`

최종 판정:

- `RIGHT HAND MIRROR = PASS`
- 원본 왼손 완성본: 보존
- 오른손 분기: 독립 작업공간 및 immutable version 확정

## 구현 방식

단순히 기존 `#hand_sign` 값을 바꾸지 않았다. 완성 단계의 INDEX/MIDDLE 피처 중 일부는 명시 좌표를 사용하므로 변수 하나만 반전하면 전체 완성 형상이 정확히 대칭되지 않기 때문이다.

대신 마지막 피처로 모든 solid body에 다음 단일 변환을 적용했다.

```featurescript
opTransform(context, id + "mirror", {
    "bodies" : qBodyType(qEverything(EntityType.BODY), BodyType.SOLID),
    "transform" : mirrorAcross(YZ_PLANE)
});
```

- mirror plane: world `YZ_PLANE`
- equation: `X = 0`
- Feature Studio: `RIGHT_HAND_MIRROR_FS`
- final feature: `RIGHT_HAND_MIRROR_X0`
- local source: `cad/OneGrip_RightHandMirror.fs`

이 방식은 완성된 버튼 8개, 스페이서, 캡, JaD/JfD shell, RWID, RZKD를 같은 매트릭스와 간격으로 한 번에 좌우 반전한다.

## Part Studio audit

| 항목 | 원본 | 오른손 | 결과 |
|---|---:|---:|---|
| feature count | 200 | 201 | mirror feature 1개 추가 |
| solid count | 30 | 30 | 증감 없음 |
| wire count | 2 | 2 | 증감 없음 |
| added solids | - | 0 | PASS |
| removed solids | - | 0 | PASS |
| visible ERROR | 0 | 0 | PASS |
| visible WARNING | 0 | 0 | PASS |

GET part inventory로 원본 version과 오른손 workspace를 같은 `configuration=default` 조건에서 비교했다.

- 32 body ID set exact 동일: `30 solid + 2 wire`
- body name exact 동일
- body type exact 동일
- partIdentity mismatch: `0`
- `JaD = Joystick_1`: 유지
- `JfD = Joystick_2`: 유지
- `RWID = Part 17 / shared retainer`: 유지
- `RZKD = Part 18 / I4 retainer`: 유지

따라서 NEW PART를 다시 생성해 identity를 바꾼 것이 아니라 기존 완성 파트 자체를 좌우 대칭 위치로 변환한 것이다.

## 좌우 대칭 수치 확인

전체 30 solids mass properties를 같은 endpoint와 explicit `configuration=default`로 비교했다.

| 항목 | source | right-hand |
|---|---:|---:|
| nominal volume | 110,240.382070 mm³ | 110,241.491231 mm³ |
| lower bound | 106,428.547369 mm³ | 106,290.220012 mm³ |
| upper bound | 114,052.216772 mm³ | 114,192.762450 mm³ |

- absolute nominal difference: `1.109161 mm³`
- relative nominal difference: `0.0010061%`
- tolerance interval overlap: `[106,428.547369, 114,052.216772] mm³`
- overlap width: `7,623.669403 mm³`

전체 centroid nominal은 다음처럼 변했다.

- source: `[+35.860166826, +0.490162231, +2.207255107] mm`
- right-hand: `[-35.860166826, +0.490162231, +2.207255107] mm`

X만 부호가 정확히 반전되고 Y/Z는 동일하다. centroid mirror deviation은 `0.0 mm`다. nominal volume의 작은 차이는 두 mass-property tolerance interval이 크게 겹치는 API 수치 근사 범위다.

## Assembly audit

- components: `25`
- mate features: `24`
- visible ERROR: `0`
- visible WARNING: `0`
- missing/dangling marker: `0`

원본 assembly는 dangling `0`이었고, 오른손 분기에서도 모든 참조 partId 및 partIdentity가 보존됐다. live assembly는 25개 component를 모두 재생성했고 누락·오류·경고 표시가 없다.

## Render

- `renders/its1105_right_hand_8button_final.png`
- size: `1500 x 1125`
- SHA-256: `F28A4BD2A8EB236B0D73B7056FBA6C5172EA16490C4F97AAC241687A4FF1122B`

렌더는 원본 audit render의 모든 triangle과 I1-I4/M1-M4 label 좌표에 동일한 `X -> -X` 변환을 적용했다.
