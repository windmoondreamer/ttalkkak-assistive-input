# Clean pre-finger baseline + external 8-button layout

- 일자: 2026-08-22 (KST)
- Onshape access: **logged-in Codex in-app browser GUI only**
- Onshape REST API / FeatureScript API: **0 calls**
- Onshape CAD geometry write: **0**
- current workspace rollback/delete/suppress/restore: **0**
- local shell cut / pocket / carrier / wiring: **0**

## 1. Result

```text
CLEAN HISTORY STATE = CONFIRMED
LOCAL CLEAN BASELINE = FOUND
EXTERNAL 8-BUTTON MARKER MOCKUP = GENERATED
INTERNAL DESIGN = NOT STARTED
NEXT = USER ERGONOMIC APPROVAL
```

`OneGrip_Play_V1`의 Version & History에서 `Start`를 보기 전용으로 열어 clean state를
확인했다. export 완료 후 브라우저는 최신 `Main` workspace URL로 복귀했다.

## 2. Historical state evidence

| item | result |
|---|---|
| historical state | `Start` |
| versionId | `4342e7db262cbced58bf16b8` |
| read-only banner | YES |
| feature count | 93 |
| solid part count | 12 |
| curve count | 2 |
| JaD / JfD | present |
| original Backplate + 8 caps + small joystick attachment | present |
| Part 13 or later | absent |
| INDEX/MIDDLE feature group | absent |

현재 Main은 203 features / 22 parts였고 `Start`는 원본 12 parts만 존재했다. History row를
보기 전용으로 열었으며 현재 workspace를 rollback 또는 restore하지 않았다.

## 3. AP242 baseline exports

공통 export 조건은 `STEP / AP242 / Millimeter / Y-axis-up unchecked / preprocessing none`이다.

| file | solid | valid | exact volume | topology V/E/F | SHA-256 |
|---|---:|---|---:|---:|---|
| `local_cad/reference/JAD_CLEAN_PRE_FINGER.step` | 1 | PASS | 46,577.761694 mm3 | 116 / 170 / 62 | `01f5708a29ca46b0f9f13b5c63b5f4d9b7b46bcf04fc8b0a55b806085f1ff4f0` |
| `local_cad/reference/JFD_CLEAN_PRE_FINGER.step` | 1 | PASS | 47,850.714043 mm3 | 107 / 159 / 60 | `8d290891dd93f16f50789f24ef7d27c754b27b4250caa1ebb3cb587648475792` |
| `local_cad/reference/THUMB_ORIGINAL_PRE_FINGER_REFERENCE.step` | 10 | PASS | 8,252.347679 mm3 | 258 / 393 / 143 | `c80a6e44dab38b88791d6167d9a7e5d3e800f48db316e5cbe988eb997d99d21d` |

각 JaD/JfD 파일은 OCCT가 읽은 single valid closed solid다. original thumb reference는
Backplate + 8 caps가 shell coordinates에 있고 `Small_joystick_attachment`는 원본 Part Studio의
parked position(X 약 103.5 mm)을 그대로 보존한다. 이 parked service part는 외형 mockup에서만
제외했고 reference STEP에서는 이동하지 않았다.

별도 표준 screw STEP은 만들지 않았다. original screw hole/boss/interface는 clean shell solid에
이미 포함되어 있고, 실제 screw keep-out은 기존 검증 reference를 유지한다.

## 4. New finger geometry absence

known I/M datum에서 exact OCCT face까지의 최소 거리를 검사했다.

| datum | clean face distance |
|---|---:|
| I1 | 0.000885 mm |
| I2 | 0.002466 mm |
| I3 | 0.000446 mm |
| I4 | 0.000446 mm |
| M1 | 0.027073 mm |
| M2 | 0.012892 mm |
| M3 | 0.011635 mm |
| M4 | 0.015895 mm |

maximum은 0.027073 mm다. 모든 datum이 continuous clean shell face 위에 있으므로 opening
center가 void로 빠지는 곳이 없다.

```text
I1 opening present = NO
M1 opening present = NO
M2 opening present = NO
other new finger geometry present = NO
ALL NEW FINGER GEOMETRY = ABSENT
```

## 5. Immutable manifests

- detailed baseline manifest: `local_cad/reference/clean_pre_finger_baseline_manifest.json`
- repository inventory: `local_cad/manifests/local_reference_manifest.json`

repository manifest gate도 다음으로 갱신됐다.

```text
JaDShellStep = FOUND
JfDShellStep = FOUND
```

## 6. External marker-only layout

외부 cap language만 검토하도록 7.6 x 7.6 x 1.2 mm의 독립 marker 8개를 배치했다.
1.2 mm는 visual exposure seed이며 opening depth나 switch travel이 아니다.

| ID | kind | center XYZ mm | outward normal | owner/review |
|---|---|---|---|---|
| I2 | retained | (-15.971165, -26.209817, 8.998807) | (-0.472400, -0.736800, -0.483800) | JfD |
| I3 | retained | (-5.496017, -29.325426, 8.999870) | (-0.038300, -0.955600, -0.292100) | JfD |
| I4 | retained | (5.496017, -29.325426, 8.999870) | (0.038300, -0.955600, -0.292100) | JaD |
| M3 | retained | (-6.890920, -13.716686, -11.118070) | (-0.224260, -0.771794, -0.595014) | JfD |
| M4 | retained | (7.379332, -13.575227, -11.115547) | (0.224859, -0.772793, -0.593489) | JaD |
| N1 | new | (-10.990443, -35.800028, 25.000000) | (-0.076466, -0.872459, -0.482667) | JfD seed |
| N2 | new | (0.000000, -35.765119, 25.000000) | (-0.043168, -0.859399, -0.509479) | **split-plane ergonomic review** |
| N3 | new | (17.486897, -6.664472, -11.125000) | (0.737273, -0.507790, -0.445621) | JaD curved-side seed |

N1/N2는 사용자 markup의 후면 중앙 상단을 따라 Z=25 mm, arc station -11/0 mm에 두었다.
둘의 center chord는 약 10.99 mm이며 nominal cap gap은 약 3.39 mm다. N3는 M-row 우측
곡면의 arc station 약 +19.97 mm이며 M4 center에서 약 12.25 mm 떨어져 있다.

N2는 의도적으로 사용자 표시와 같은 중앙 seam에 둔 **외부 ergonomic marker**다. 사용자
위치 승인 전에는 owner, split bridge 또는 내부 switch architecture를 결정하지 않는다.

## 7. Exact local outputs

| output | result |
|---|---|
| `FINGER_LAYOUT_EXTERNAL_MARKERS_8.step` | 8 valid independent solids, 554.496 mm3 |
| `CLEAN_SHELL_EXTERNAL_LAYOUT_REVIEW.step` | 2 shells + 9 in-place original thumb solids + 8 markers = 19 solids |
| marker manifest | 8 buttons / 5 retained / 3 new / 3 removed references |

출력 위치:

```text
build123d_workbench/out/finger_layout_reset/
```

## 8. Render inventory

```text
renders/finger_layout_reset/00_contact_sheet.png
renders/finger_layout_reset/01_button_facing_rear.png
renders/finger_layout_reset/02_left_oblique.png
renders/finger_layout_reset/03_right_oblique.png
renders/finger_layout_reset/04_side_profile.png
renders/finger_layout_reset/05_removed_comparison.png
```

blue는 retained/recreated 5개, red는 신규 N1/N2/N3다. comparison render의 red X는 제거할
I1/M1/M2 reference이며 실제 geometry로 생성하지 않았다.

## 9. Stop gate

```text
button markers = 8 solids
shell cut = 0
opening = 0
pocket = 0
carrier = 0
retention = 0
wiring = 0
```

사용자가 N1/N2 높이·간격, N3 곡면 위치, retained 5개와의 관계를 승인하기 전에는 내부
geometry를 시작하지 않는다.

