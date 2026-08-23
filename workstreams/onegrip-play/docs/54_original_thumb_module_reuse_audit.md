# OneGrip Play — original Thumb module reuse audit

Audit ID: `ONEGRIP_ORIGINAL_THUMB_REUSE_2026-08-22`  
Date: 2026-08-22  
Mode: **local OCCT exact B-rep / analysis only / Onshape 0 / production CAD write 0**

## 0. Executive answer

현재 Finger 8 배열과 maximum-lowered Thumb exterior를 변경하지 않은 상태에서 원본
오픈소스 Thumb subsystem의 **20 exact parts 중 18 parts의 형상을 그대로 유지할 수 있다.**

- direct drop-in 가능: `17 / 20 = 85.0 %`
- shell-side adaptation을 전제로 원본 part 형상 유지 가능: `18 / 20 = 90.0 %`
- 원본 mounting part 자체 변경 필요: `0 / 20`
- 원본 mechanism 변경 필요: `2 / 20`

두 mechanism part는 서로 다른 joystick 두 개가 아니라 **하나의 HW504 module을 이루는 두
exact solids**다. 따라서 part 기준 재사용률은 90.0%지만, subsystem 판정은 HW504가 N1/N2
switch 및 shared carrier와 실제로 겹치므로 `ORIGINAL THUMB MECHANISM = REDESIGN REQUIRED`다.

**ORIGINAL THUMB REUSE RATIO = 90.0 %**

## 1. Sources and immutable scope

### 1.1 Exact sources

| Source | Role | SHA-256 |
|---|---|---|
| `lower_adapter/local_cad/reference/ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step` | complete original assembly occurrence geometry, HW504, PushBtn and three M3 screws | `deb2f78838b41ab125247bd4068d7c0d08b5bddf780b449534b716fe35dc0ed4` |
| `local_cad/reference/THUMB_ORIGINAL_PRE_FINGER_REFERENCE.step` | original Part Studio Backplate/cap corroboration | `c80a6e44dab38b88791d6167d9a7e5d3e800f48db316e5cbe988eb997d99d21d` |
| `build123d_workbench/out/finger_thumb_joint_feasibility/THUMB_TARGET_EXACT_MODULE.step` | exact 20-part assembly normalized to Part Studio coordinates and rigidly lowered | `adc870ffaf55a9342d62df89f162827a744bdf1d43060c0fbb69f7c8e8089fe9` |
| `build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JAD_EXTERIOR_LOWERED_THUMB_V1.step` | current exact JaD review shell | `b223757ee25fdd5eddf710b8666bcd388d4221235d8d876f620eb0005d5b75b6` |
| `build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JFD_EXTERIOR_LOWERED_THUMB_V1.step` | current exact JfD review shell | `d1bf68b105dce11374ab1f89981ee503a5591d2ff7fa5175777432171855bf7f` |
| `build123d_workbench/out/finger_controls_v2/FINGER_V2_ASSEMBLY_REFERENCE.step` | present frozen Finger switch/carrier reference | `c2ce9e0bd180c24c7f2792d4691a53566040bfdce1d1273d014ea33e2dc67fc1` |

### 1.2 Hard freeze honored

- latest Finger exterior: `I2, I3, I4, M3, M4, N1, N2, N3`
- Thumb transform: `(DX,DY,DZ) = (0.00,+12.25,-21.00) mm`
- exterior surface change: `0`
- new carrier/seat/boss/screw mount/wiring channel: `0`
- custom V3/V3.1 geometry imported as design source: `0`
- collision auto-fix: `0`
- production/print approval: **NOT EVALUATED**

## 2. Original Thumb subsystem part list

모든 cartridge part는 동일한 rigid transform으로 함께 이동한다. 세 개의 M3 screw와 JaD/JfD
shell material은 shell-side이므로 cartridge part count에서 제외했다.

| # | Part name | Source label | Role | Moves with Thumb? | Result |
|---:|---|---|---|:---:|---|
| 1 | `THUMB_BACKPLATE` | Backplate | common swept backplate; 8-button support/retainer 통합 | YES | Class B — shell-side adapter required |
| 2 | `THUMB_BUTTON_1_CAP__Button_corner_1` | Button_corner_1 | Thumb button 1 cap | YES | reusable as-is |
| 3 | `THUMB_BUTTON_2_CAP__Button_middle_1` | Button_middle_1 | Thumb button 2 cap | YES | reusable as-is |
| 4 | `THUMB_BUTTON_3_CAP__Button_corner_2` | Button_corner_2 | Thumb button 3 cap | YES | reusable as-is |
| 5 | `THUMB_BUTTON_4_CAP__Button_side_1` | Button_side_1 | Thumb button 4 cap | YES | reusable as-is |
| 6 | `THUMB_BUTTON_5_CAP__Button_middle_2` | Button_middle_2 | Thumb button 5 cap | YES | reusable as-is |
| 7 | `THUMB_BUTTON_6_CAP__Button_side_2` | Button_side_2 | Thumb button 6 cap | YES | reusable as-is |
| 8 | `THUMB_BUTTON_7_CAP__Button_wide_1` | Button_wide_1 | Thumb button 7 cap | YES | reusable as-is |
| 9 | `THUMB_BUTTON_8_CAP__Button_wide_2` | Button_wide_2 | Thumb button 8 cap | YES | reusable as-is |
| 10 | `THUMB_BUTTON_1_PUSHBTN` | PushBtn occurrence | Thumb button 1 mechanism | YES | reusable as-is |
| 11 | `THUMB_BUTTON_2_PUSHBTN` | PushBtn occurrence | Thumb button 2 mechanism | YES | reusable as-is |
| 12 | `THUMB_BUTTON_3_PUSHBTN` | PushBtn occurrence | Thumb button 3 mechanism | YES | reusable as-is |
| 13 | `THUMB_BUTTON_4_PUSHBTN` | PushBtn occurrence | Thumb button 4 mechanism | YES | reusable as-is |
| 14 | `THUMB_BUTTON_5_PUSHBTN` | PushBtn occurrence | Thumb button 5 mechanism | YES | reusable as-is |
| 15 | `THUMB_BUTTON_6_PUSHBTN` | PushBtn occurrence | Thumb button 6 mechanism | YES | reusable as-is |
| 16 | `THUMB_BUTTON_7_PUSHBTN` | PushBtn occurrence | Thumb button 7 mechanism | YES | reusable as-is |
| 17 | `THUMB_BUTTON_8_PUSHBTN` | PushBtn occurrence | Thumb button 8 mechanism | YES | reusable as-is |
| 18 | `THUMB_JOYSTICK_HW504_COMPONENT_1` | HW504_B | HW504 module larger exact solid | YES | Class D — mechanism change required |
| 19 | `THUMB_JOYSTICK_HW504_COMPONENT_2` | HW504_B | HW504 module second exact solid | YES | Class D — mechanism change required |
| 20 | `THUMB_JOYSTICK_SMALL_ATTACHMENT` | Small_joystick_attachment | joystick attachment/opening counterpart | YES | reusable as-is |

Shell-interface inventory:

| Part/feature | Source | Role | Moves with Thumb? |
|---|---|---|:---:|
| `ORIGINAL_M3_SHELL_SCREW_1~3` | complete assembly STEP | split-shell clamp / Backplate capture | NO |
| original JaD/JfD Thumb opening/support material | clean pre-Finger shell STEP pair | shell-side opening, capture and support geometry | NO |

## 3. Original mechanical architecture

원본은 독립 carrier 여러 개가 아니라 다음과 같은 하나의 shared Thumb architecture다.

```text
Small_joystick_attachment
        +
HW504 module (2 exact solids)
        +
8 independent button caps
        +
8 PushBtn occurrences
        +
one swept Backplate
        +
original JaD/JfD shell capture
        +
three shell-side M3x0.50x16 screws
```

- 별도 button-support part는 없다. 원본 support/retainer 형상은 Backplate와 shell 내부에 통합돼 있다.
- Backplate는 8개 PushBtn와 cap의 중심·간격·작동축을 하나의 rigid 관계로 유지한다.
- HW504 두 solid는 하나의 joystick module이며 서로 독립 joystick가 아니다.
- M3 screw 세 개는 cartridge와 함께 이동하는 fastener가 아니라 original shell datum에 남는
  shell-side clamp/capture다.

## 4. Rigid cartridge definition and transform integrity

`ORIGINAL THUMB CARTRIDGE`는 위 part list의 20 exact solids다.

| Metric | Result |
|---|---:|
| DX / DY / DZ | `0.00 / +12.25 / -21.00 mm` |
| Scale | `1.000000` |
| Rotation change | `0.000000°` |
| Max center round-trip residual | `0.000000 mm` |
| Max volume residual | `0.000000 mm³` |
| Max pairwise-center-distance residual | `1.4211e-14 mm` |
| Relative geometry validation | **PASS** |

따라서 joystick, cap, PushBtn, mechanism depth와 Backplate 관계는 바뀌지 않았다.

## 5. Current lowered exterior alignment

현재 exterior와 cartridge의 external control solids는 같은 exact source와 같은 rigid transform을
사용한다. 9개 current opening tool의 boolean residual도 모두 `0.000000 mm³`다.

| Check | Error | Result |
|---|---:|---|
| joystick center | `5.3291e-14 mm` | PASS |
| circular recess center | `5.3291e-14 mm` | PASS |
| button 1 center | `3.5527e-15 mm` | PASS |
| button 2 center | `2.0948e-15 mm` | PASS |
| button 3 center | `3.5527e-15 mm` | PASS |
| button 4 center | `3.9721e-15 mm` | PASS |
| button 5 center | `3.9968e-15 mm` | PASS |
| button 6 center | `1.7764e-15 mm` | PASS |
| button 7 center | `1.9860e-15 mm` | PASS |
| button 8 center | `1.9860e-15 mm` | PASS |
| cap ↔ opening reference max | `3.9968e-15 mm` | PASS |
| button travel-axis angular error | `0.000000°` | PASS |

수치는 floating-point roundoff 범위이므로 engineering position error는 `0.000000 mm`로 본다.

## 6. Exact OCCT collision matrix

### 6.1 Group matrix

| Audit pair | Minimum clearance (mm) | Penetration volume (mm³) | Pairs | Result |
|---|---:|---:|---:|---|
| A. joystick mechanism ↔ shell | `0.000000` | `87.852198` | 2 | collision |
| B. Thumb caps + PushBtn ↔ shell | `0.300280` | `0.000000` | 0 | no penetration; below 0.80 mm robust target |
| C. Backplate ↔ shell | `0.000000` | `217.838944` | 2 | collision |
| D. Small attachment ↔ shell | `0.800000` | `0.000000` | 0 | no penetration |
| E. full cartridge ↔ Finger switches | `0.000000` | `1.259889` | 3 | collision |
| F. full cartridge ↔ Finger carriers | `0.000000` | `71.642203` | 2 | collision |
| G. full cartridge ↔ seam X=0 | `0.000000` | `0.000000`² | 8 crossing parts | crosses seam |
| full cartridge ↔ current shell | `0.000000` | `305.691142` | 4 | collision |
| full cartridge ↔ original fixed screws | `0.000000` | `12.094078` | 2 | collision |

² seam은 zero-thickness plane이므로 penetration volume은 정의상 0이다. 교차 part와 X span을
별도로 기록했다.

### 6.2 Exact positive-volume pairs

| Cartridge part | Target | Penetration (mm³) | Class |
|---|---|---:|---|
| Backplate | JaD shell | `88.497725` | B |
| Backplate | JfD shell | `129.341219` | B |
| HW504 component 1 | JaD shell | `32.753134` | D |
| HW504 component 1 | JfD shell | `55.099064` | D |
| HW504 component 1 | Finger N1 switch | `0.696219` | D |
| HW504 component 1 | Finger N2 switch | `0.243301` | D |
| HW504 component 2 | Finger N2 switch | `0.320370` | D |
| HW504 component 1 | N1/N2 shared carrier | `45.272894` | D |
| HW504 component 2 | N1/N2 shared carrier | `26.369309` | D |
| HW504 component 1 | original fixed screw 2 | `2.863145` | B fastening blocker; D overall because of Finger/shell conflict |
| Backplate | original fixed screw 3 | `9.230933` | B fastening blocker |

### 6.3 Seam crossings

8개 part가 original design intent대로 X=0 split seam을 가로지른다.

- Backplate
- Button 2 cap and PushBtn
- Button 5 cap and PushBtn
- HW504 component 1 and component 2
- Small joystick attachment

seam crossing 자체는 collision volume이 아니라 assembly/capture requirement다.

### 6.4 A/B/C/D classification result

| Class | Actual parts | Meaning in this audit |
|---|---|---|
| A | none confirmed | shell 내부 material relief만으로 exterior를 보존할 수 있다고 확정된 part 없음 |
| B | Backplate; original screw capture | original part는 유지할 수 있으나 shell-side adapter/capture 변경 필요 |
| C | none | original mounting part 자체 변경으로 해결되는 항목 없음 |
| D | HW504 component 1 and 2 | frozen Finger N1/N2와 물리적으로 겹치므로 Thumb mechanism 자체 변경 또는 사용자 정책 변경 필요 |

기존 V3의 HW504 local relief는 외형에 N1/N2 뒤 through-window를 만들었고 handoff에서 폐기됐다.
따라서 이번 감사에서 HW504↔shell 충돌을 Class A로 낙관 분류하지 않았다.

## 7. Original fastening reuse analysis

원본 M3 hardware 자체는 재사용할 수 있으나, original shell-side axes를 lowered cartridge에 그대로
쓸 수는 없다.

| Screw | Axis point (mm) | Axis direction | Lowered-target collision |
|---|---|---|---|
| screw 1 | `(7.4140,16.3463,-21.3540)` | `(0.997965,-0.063768,0)` | none |
| screw 2 | `(7.4140,-13.8959,23.0639)` | `(0.997965,-0.063768,0)` | HW504 component 1, `2.863145 mm³` |
| screw 3 | `(7.4140,-41.3171,45.9812)` | `(0.997965,-0.063768,0)` | Backplate, `9.230933 mm³` |

```text
ORIGINAL HARDWARE REUSABLE = YES
ORIGINAL AXES REUSABLE AT LOWERED POSITION = NO
ORIGINAL FASTENING = SHELL-SIDE ADAPTER REQUIRED
```

이번 단계에서는 새 screw, boss, mount 또는 fastening architecture를 만들지 않았다.

## 8. Wiring exit analysis

새 channel을 설계하지 않고 PushBtn/HW504 exact B-rep support point에서 ±X/±Y/±Z로
`12.0 mm`, `1.20 × 1.20 mm` analysis probe만 검사했다.

| Control | Preferred unblocked direction | Other unblocked directions |
|---|---|---|
| PushBtn 1 | `-X` | `-Y, -Z` |
| PushBtn 2 | `-Z` | `+X, -X, +Y` |
| PushBtn 3 | `+X` | `-Y, -Z` |
| PushBtn 4 | `-X` | `+Y, -Z` |
| PushBtn 5 | `-Z` | `+X, -X, -Y` |
| PushBtn 6 | `-Z` | `+X, +Y` |
| PushBtn 7 | `-X` | none |
| PushBtn 8 | `+X` | none |
| HW504 component 1 | `+Y` | `+Z` |
| HW504 component 2 | `+X` | `-Z` |

Direction aggregate blocked counts out of ten control solids:

| Direction | Blocked probes |
|---|---:|
| `+X` | 4 |
| `-X` | 5 |
| `+Y` | 6 |
| `-Y` | 7 |
| `+Z` | 9 |
| `-Z` | 3 |

`-Z`가 aggregate 기준 가장 덜 막히지만 모든 control에 공통인 단일 방향은 아니다. 또한 imported
PushBtn/HW504 occurrence는 fused solid라 connector sub-body name이 없다. 따라서 위 값은 terminal
pinout가 아니라 **clearance map**이고 production wiring 결정으로 사용하면 안 된다.

## 9. Original reuse ratio

| Category | Exact part count | Ratio |
|---|---:|---:|
| Original Thumb parts | 20 | 100.0% |
| Directly reusable as-is / drop-in | 17 | 85.0% |
| Original geometry retained with shell-side adaptation | 1 | 5.0% |
| Original mounting part modification required | 0 | 0.0% |
| Mechanism redesign required | 2 | 10.0% |
| **Original parts retained unchanged** | **18** | **90.0%** |

Reuse-ratio definition:

```text
ORIGINAL THUMB REUSE RATIO
= (direct as-is + Class A/B original geometry retained) / original exact parts
= (17 + 1) / 20
= 90.0 %
```

별도로, adaptation이 전혀 없는 **DIRECT DROP-IN RATIO = 85.0 %**다.

## 10. Minimum changes indicated by the audit

### 10.1 Parts requiring shell-side adaptation

- original Backplate capture/seating interface
- screw 2 and screw 3 shell-side datum/capture relationship

Backplate exact geometry는 유지 가능한 것으로 분류했지만 shell penetration `217.838944 mm³`와
fixed screw collision이 있으므로 adapter/capture architecture는 별도 사용자 승인 없이는 진행할 수 없다.

### 10.2 Parts requiring mechanism redesign

- `THUMB_JOYSTICK_HW504_COMPONENT_1`
- `THUMB_JOYSTICK_HW504_COMPONENT_2`

두 part는 한 HW504 module이다. 현재 frozen Finger N1/N2 switch 및 shared carrier와 교차하고,
component 1은 current shell과도 `87.852198 mm³` 겹친다. Finger를 움직이지 않고 exterior를
뚫지 않는다는 현재 정책에서는 shell-side adapter만으로 해결할 수 없다.

### 10.3 Parts requiring no geometry change

- 8 original caps
- 8 original PushBtn mechanisms
- Small joystick attachment

## 11. Required renders

Directory: `renders/original_thumb_module_reuse_audit/`

1. `01_current_final_exterior.png`
2. `02_original_thumb_cartridge_isolated.png`
3. `03_original_thumb_cartridge_exploded.png`
4. `04_lowered_original_thumb_cartridge.png`
5. `05_current_exterior_plus_original_cartridge.png`
6. `06_transparent_shell_with_original_cartridge.png`
7. `07_joystick_alignment_closeup.png`
8. `08_thumb_button_alignment_closeup.png`
9. `09_thumb_vs_finger_internals.png`
10. `10_thumb_vs_shell_collision_map.png`
11. `11_original_fastening_geometry.png`
12. `12_full_internal_overview.png`

`12_full_internal_overview.png`에는 JOYSTICK, THUMB BACKPLATE, BUTTON 1~8, BUTTON SUPPORT,
ORIGINAL FASTENER, SHELL, FINGER SWITCH를 직접 표시했다. `00_contact_sheet.png`도 추가 생성했다.

## 12. Analysis outputs

Directory: `build123d_workbench/out/original_thumb_module_reuse_audit/`

| Output | SHA-256 |
|---|---|
| `ORIGINAL_THUMB_CARTRIDGE.step` | `ee6ed6848e7c0481a2c73639c85fc39bf63ac837514ca13b16bdc1bc6e075527` |
| `LOWERED_ORIGINAL_THUMB_CARTRIDGE.step` | `f7a7cea568b08ff1565b90c886de955cccf246bf88b7f4a46a00ca61f35c4bc2` |
| `ORIGINAL_FASTENING_REFERENCE.step` | `540d8e36712e2f20e59d449c9a74fd6bf4265db18a1daf7b3ee28f92611d8068` |
| `ORIGINAL_THUMB_COLLISION_DEBUG.step` | `dfbe62248079029a5928342f9231007c4e93572689c6795ee196bd60c18a1058` |
| `THUMB_WIRING_CLEARANCE_PROBES.step` | `16140680357f939cd3574016228e47a1db8a11130b31b5e6daa8be4f6be8db5c` |
| `original_thumb_module_reuse_audit.json` | machine-readable full audit; self-hash intentionally omitted |

Reproduction:

```powershell
& '.venv-build123d\Scripts\python.exe' -m build123d_workbench.original_thumb_module_reuse_audit
& '.venv-build123d\Scripts\python.exe' -m build123d_workbench.render_original_thumb_module_reuse_audit
```

## 13. Limitations and approval gates

1. current exact review STEP는 documented `0.80 mm` localized opening envelope를 포함한다.
   actual lower-15 exterior의 authoritative surface는 visual STL graft이며 exact editable B-rep가 아니다.
2. Finger switch/carrier는 present frozen V2 exact reference다. handoff는 internal design을 아직
   `DEFERRED`로 표시하므로 이 충돌은 production 승인 결과가 아니라 현재 reference 기준 evidence다.
3. wiring probe는 분석용이며 pinout, wire OD, solder fillet, strain relief를 확정하지 않는다.
4. 외관 user approval은 handoff 기준 `PENDING`, production/print approval은 `NOT EVALUATED`다.
5. 이 감사에서는 어떠한 collision도 자동 수정하지 않았다.

## 14. Final verdict

```text
CURRENT EXTERIOR
= PRESERVED

ORIGINAL THUMB CARTRIDGE
= IDENTIFIED

JOYSTICK ALIGNMENT
= PASS

THUMB BUTTON ALIGNMENT
= PASS

ORIGINAL THUMB MECHANISM
= REDESIGN REQUIRED

ORIGINAL BACKPLATE
= ADAPTER REQUIRED

ORIGINAL FASTENING
= ADAPTER REQUIRED

SHELL INTERNAL ADAPTATION
= MAJOR

FINGER CONFLICT
= PRESENT
```

## 15. Final question

> 현재 사용자가 승인한 최신 Finger 배열과 maximum-lowered Thumb exterior를 전혀 변경하지 않고,
> 원본 오픈소스 DIY Joystick의 Thumb 내부 기구를 얼마나 그대로 사용할 수 있는가?

**답:** exact part 기준 20개 중 18개 원본 형상을 유지할 수 있으므로 **90.0%**다. 다만 완전
drop-in은 17개, 즉 85.0%이고, Backplate는 shell-side adapter가 필요하다. HW504 한 module을
구성하는 두 solid는 frozen N1/N2 Finger internals 및 current shell과 충돌하므로 현재 정책에서는
mechanism redesign이 필요하다.

**ORIGINAL THUMB REUSE RATIO = 90.0 %**

**STOP — 다음 internal design은 사용자 검토 후 별도 지시가 있을 때만 진행한다.**
