# THUMB MODULE RESEATING implementation and final audit

## 0. Result

- 작업 종류: **THUMB REDESIGN이 아닌 original THUMB MODULE rigid reseating**
- actual global translation: **(ΔX, ΔY, ΔZ) = (0.000, +5.500, -6.000) mm**
- module scale / rotation change: **없음**
- final Part Studio: **202 features / 30 solids / 2 wires**
- final Assembly: **25 parts / 24 mates / dangling 0**
- ERROR: **0**
- WARNING: **0**
- unexpected fragment: **0**
- final decision: **THUMB MODULE RESEAT = CONFIRMED**
- CAD WRITE recommendation: **GO**

## 1. Source and checkpoint

- document: `OneGrip_Play_V1`
- documentId: `a21e64f36bc61df760d4587c`
- workspaceId: `ef6a7b3ccc45186203e4d2ca`
- Part Studio: `Joystick` / `425d9199b59cfb1efd9ddc35`
- Assembly: `Joystick` / `250f706cb675e635b8d344c4`
- Feature Studio: `OneGrip THUMB Module Reseat` / `21d5ac736dc37ece1eda8cd9`
- pre-write checkpoint: `THUMB_RESEAT_PREWRITE`
- checkpoint versionId: `3333f7d3f6c91687515706fb`

Checkpoint 당시 baseline은 `200 features / 30 solids`, Assembly `25 parts / 24 mates`였다. 작업은 Main workspace에 수행했으며 checkpoint가 전체 pre-write rollback point다.

## 2. Atomic implementation

### A. Checkpoint

`THUMB_RESEAT_PREWRITE`를 먼저 생성하고 JaD/JfD/RWID/RZKD, Backplate 및 8개 original thumb cap identity를 확인했다.

### B. Rigid original-module translation

Feature `THUMB B rigid module translation (0,+5.5,-6)`이 다음 **9개 existing solid**에 하나의 `opTransform`만 적용한다.

| role | partId |
|---|---|
| Backplate | `RYDD` |
| Button_wide_1 | `RAED` |
| Button_side_1 | `RAEH` |
| Button_corner_1 | `RAEL` |
| Button_corner_2 | `RBED` |
| Button_side_2 | `RBEH` |
| Button_wide_2 | `RBEL` |
| Button_middle_1 | `RDED` |
| Button_middle_2 | `RDEH` |

실행 후 `201 features / 30 solids`였다. 새 module을 복제하거나 유사 형상으로 재모델링하지 않았다.

`Small_joystick_attachment`(`RHED`), HW504 두 solid와 PushBtn 8개는 원래부터 Assembly mate chain으로 Backplate에 종속된다. 따라서 Part Studio staging body를 중복 Transform하지 않고 Assembly root mate를 조정해 전체 기구를 같은 global translation으로 이동했다.

### C. Original/new opening relationship

원본 `Buttons` removal feature `F9tZ4ezI7riogDz_2`가 만든 opening side face query를 재생성한 결과는 **36 faces**였다.

- 8 rectangular button openings: 32 side faces
- split joystick opening: 4 side faces

따라서 임의의 새 hole pattern을 재작성하지 않고 이 36개 original face를 shell-side source of truth로 사용했다.

### D. New opening / old opening heal

Feature `THUMB D original shell openings relocated`가 36개 face에 동일한 `(0,+5.5,-6)` transform을 `opMoveFace`로 적용했다. 이 direct edit는 owning shell B-rep을 heal하므로:

- old opening location은 별도 patch body 없이 닫힘;
- new opening은 original profile/spacing을 그대로 유지;
- leftover boolean tool body 없음;
- JaD/JfD identity 유지;
- 완료 후 `202 features / 30 solids` 유지.

### E–H. Seating / Backplate / structural transition / wiring

별도 pedestal, floating flange 또는 bulky adapter는 생성하지 않았다. 그 이유는 original Backplate, original integrated supports, caps, opening faces가 동일한 transform을 받아 서로의 validated 상대좌표를 정확히 유지하기 때문이다.

| gate | result |
|---|---:|
| shell wall source thickness (`Shell 1`) | 3.0 mm |
| original Backplate sweep thickness | 5.0 mm |
| original button-support minimum web | 4.0 mm |
| original support/service depth | 10.0 mm |
| button-module through opening | 6.4 mm |
| certified continuous virtual wire envelope | 4.0 mm |

Rear service volume은 원래 open-back architecture이고 Assembly 내부 component 관계가 rigid하게 유지된다. 4.0 mm wire envelope는 6.4 mm through-opening과 10.0 mm rear service depth 안에서 연속이다. 별도 wire cut이 오히려 shell wall과 screw clearance를 훼손하므로 추가 subtractive write를 하지 않았다.

### I. Final cleanup

새 tool body 자체가 없으므로 cleanup에서 제거할 body도 없다. `opTransform`은 existing 9 solids를 이동하고 `opMoveFace`는 existing JaD/JfD B-rep을 직접 수정한다. Part count가 30으로 유지되어 orphan, plug, patch, adapter fragment가 생기지 않았다.

## 3. Assembly relocation

Backplate root mate는 original rotation을 그대로 두고 mate-basis offset만 변경했다.

| parameter | before | after |
|---|---:|---:|
| X offset | 0.600000000 mm | 0.321013675 mm |
| Y offset | 0.200000000 mm | 0.291806143 mm |
| Z offset | 0.000000000 mm | 8.134109556 mm |
| Y-axis rotation | -2° | -2° |

이 값은 mate coordinate basis로 표현된 값이며 실제 world translation은 정확히 `(0,+5.5,-6) mm`다. 내부 Backplate→8 PushBtn/HW504→caps/attachment mate chain은 수정하지 않았다.

최종 UI regeneration 확인:

- instances/active parts: **25/25**
- mates: **24**
- unresolved/dangling: **0**
- red error/warning marker: **0**

## 4. Ergonomic reach result

동일한 exact thumb-cap mesh AABB center와 기존 INDEX/MIDDLE switch center를 사용했다.

| metric | old | relocated | improvement |
|---|---:|---:|---:|
| thumb ↔ INDEX nearest center | 37.867697 mm | **36.348712 mm** | 1.518985 mm |
| thumb ↔ MIDDLE nearest center | 52.275047 mm | **46.827106 mm** | 5.447941 mm |
| INDEX four-center nearest-thumb mean | 41.654267 mm | 40.682883 mm | 0.971384 mm |
| MIDDLE four-center nearest-thumb mean | 53.706389 mm | 49.302622 mm | 4.403768 mm |

양쪽 nearest pair는 `Button_corner_2 ↔ I1/M1`이다. `+Y` shell seating correction 때문에 pure `-Z 6 mm`만 적용한 audit 후보보다 INDEX 개선량은 줄지만, MIDDLE reach와 shell seating을 동시에 성립시키는 nominal target이다.

## 5. Screw B and protected geometry

Screw B source cylinder:

- axis point: `(0,-14.45,23.07)` mm
- finite X range: `[-6,+10]` mm
- radius: `3.5 mm`

Relocated exact Backplate fine mesh와 finite screw axis segment의 triangle distance를 계산했다.

- axis→Backplate minimum: `12.084185 mm`
- screw surface clearance: **8.584185 mm**
- closest axis X: `2.000000 mm` (finite cylinder interior)

따라서 Screw B는 변경하지 않았고 collision이 없다. INDEX/MIDDLE centers, holders, retainers, row layout도 변경하지 않았다.

## 6. Geometry identity

| check | changed? |
|---|---|
| button size | NO |
| button cap exterior | NO |
| button spacing | NO |
| joystick geometry | NO |
| joystick ↔ button relative position | NO |
| actuator relationship | NO |
| module scale | NO |
| module rotation | NO |

8개 cap center의 전체 pairwise-distance matrix는 old/new 사이 최대 변화가 **0.000000 mm**다. HW504, PushBtn과 Small attachment는 내부 mate chain을 보존한 채 Backplate root와 같이 이동했다.

## 7. Fragment / watertight audit

Rigid transform은 topology를 바꾸지 않는다. Fine-mesh cache에서 Backplate와 8개 caps 모두:

- connected components: **각 1**
- boundary edges: **각 0**
- non-manifold edges: **각 0**

Shell은 `opMoveFace` direct edit 후 B-rep regeneration을 완료했고 solid count가 유지됐다. 별도 positive/negative tool solid를 만들지 않았으므로 tangent-only union, edge-only attachment, isolated boss, leftover tool, patch plug가 구조적으로 존재하지 않는다.

- expected solids: 30
- actual solids: 30
- added solids: 0
- removed solids: 0
- unexpected disconnected solids: **0**

## 8. Final render

`renders/thumb_reseat_old_new_overlay.png`는 다음을 동시에 표시한다.

- magenta dashed: original thumb module position
- orange/gold: relocated original module and Backplate interface
- blue: INDEX row
- green: MIDDLE row
- red: Screw B

Render는 cached exact module meshes에 exact rigid transform을 적용한 local overlay이며 CAD write를 하지 않는다.

## 9. Final gate

| gate | result |
|---|---|
| nominal `(0,+5.5,-6)` target | PASS |
| original thumb functional/user geometry preserved | PASS |
| old opening heal / new opening | PASS |
| JaD / JfD identity | PASS |
| INDEX/MIDDLE protected | PASS |
| Screw B clearance | PASS, 8.584185 mm |
| shell wall / support web | PASS, 3.0 / 4.0 mm |
| continuous wiring envelope | PASS, 4.0 mm |
| solid inventory | PASS, 30 unchanged |
| fragment/orphan/tool body | PASS, 0 |
| Assembly | PASS, 25/25; 24 mates; dangling 0 |
| ERROR / WARNING | PASS, 0 / 0 |

**THUMB MODULE RESEAT = CONFIRMED**

**CAD WRITE recommendation = GO**

브라우저 보안 정책이 작업 종료 시 Feature Studio 탭 재접속과 별도 final-version 생성만 차단했다. 적용·재생성된 CAD geometry에는 영향이 없으며 pre-write checkpoint는 존재한다. 현재 완성 geometry는 Main workspace의 `202 features / 30 solids` 상태다.
