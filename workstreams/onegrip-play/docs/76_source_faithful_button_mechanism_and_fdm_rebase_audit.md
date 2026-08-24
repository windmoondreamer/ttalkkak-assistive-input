# 76 — Source-faithful button mechanism and FDM rebase audit

CORNER LUG FUNCTION
= **F. SWITCH-HOUSING STAKING / MOLD-ASSEMBLY POSTS; NOT POCKET LOCATORS OR SEATING FEET**

CURRENT POCKET
= **INCOMPLETE — 6.40 source expression is real, but production FDM locating/actual-lug closure is not demonstrated**

SWITCH SEATING DATUM
= **PLASTIC MAIN-BODY BOTTOM / REAR PLANE (source PushBtn local Y=0), not corner-lug bottom**

CURRENT PUSHER LENGTH
= **RECOMPUTE**

CURRENT TRAVEL MODEL
= **PROVISIONAL**

ACTUATION SOLVER
= **REVISE**

THUMB INNER HOUSING
= **NON-CONFORMAL — LOCAL CONFORMAL REBASE RECOMMENDED**

FDM TOLERANCE
= **FAIL under uncalibrated conservative worst case; coupon/calibrated pads required**

SHELL SPLIT
= **PRESERVED**

EXTERIOR
= **PRESERVED**

PRODUCTION MODIFICATION
= **0**

> docs/75의 `BASELINE ARCHITECTURE REUSE = 100%`는 삭제하지 않았지만 현재부터
> **PROVISIONAL — SOURCE-DETAIL DEPENDENCY RECHECK REQUIRED**로 강등했다. 본 문서는 audit-only
> 후보와 review render만 만들며 production source를 수정하지 않는다.

## 1. Final verdict

**C. SOURCE-FAITHFUL BUTTON MECHANISM REBASE RECOMMENDED**

외형, 8개 중심/방향, maximum-lowered Thumb exterior, JaD/JfD split은 그대로 유지할 수 있다.
실패 지점은 exterior가 아니라 `actual lug metrology → controlled pocket locating → pusher gap/length
→ click/overtravel → structural stop → FDM/assembly tolerance` 내부 연쇄다.

별도 판정: **THUMB INNER HOUSING = LOCAL CONFORMAL REBASE**. 원본 Backplate도 별도 captured
insert이며 exact zero-offset conformal solid는 아니지만, lowering 후 shell-near area가 줄고 그중
2 mm 초과 unsupported 비율이 커졌다. frozen exterior에서 inward-derived controlled-clearance band를
audit render로 제시했다.

## 2. Four corner posts — exact extraction

원본 mesh의 source +Y가 press axis이고 transverse 축은 source X/Z다. 아래 X/Z를 기능 좌표 U/V로
읽을 때 V 부호만 반전된다. 네 top disk는 각각 126개 triangle, 면적 0.785073 mm²로 D1.000 원에
해당하며, side 포함 nominal 형상은 **D1.000 × 0.500 mm**다.

| lug | source X,Z centre mm | width X | length Z | height | base Y | top Y | exact gap to original Backplate mm |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | -2.250, -2.250 | 0.999689 | 1.000000 | 0.500000 | 3.000000 | 3.500000 | 0.320367 |
| 2 | -2.250, +2.250 | 0.999689 | 1.000000 | 0.500000 | 3.000000 | 3.500000 | 0.407543 |
| 3 | +2.250, -2.250 | 0.999689 | 1.000000 | 0.500000 | 3.000000 | 3.500000 | 2.220774 |
| 4 | +2.250, +2.250 | 0.999689 | 1.000000 | 0.500000 | 3.000000 | 3.500000 | 0.476321 |

- count/symmetry: **4 / two-axis symmetric at ±2.250 mm**
- plastic relation: main housing top Y=3.000에서 시작해 Y=3.500까지 돌출한다.
- terminal relation: terminals는 Y<0 rear side에 있고 posts는 Y=3.0…3.5 front side라 기능면이 반대다.
- original pocket contact: selected exact OCCT pair에서 common volume 0, 네 gap 모두 양수다.
- 기능 판정: A/B/C/D가 아니다. **스위치 케이스 자체 staking/mold-assembly post(F)**가 가장
  일관된다. 실제 ITS에서도 존재는 YES이나 정밀 치수는 UNKNOWN이다.

## 3. Original pocket and seating reconstruction

| item | result |
|---|---|
| pocket U/V | **6.400 × 6.400 mm**, source expression `6.0 + 2×0.2` |
| source support thickness | **4.000 mm** |
| occupied body cavity depth | **3.500 mm** nominal PushBtn housing |
| corner-lug recess | **none found**; open/front headspace accommodates the posts |
| bottom/rear seating plane | **PushBtn plastic body bottom Y=0** |
| side locating | 6.40 square Backplate walls, nominal 0.195/side around 6.010 main body |
| skirt fit | 6.310 skirt leaves **0.045 mm/side**, CAD-fit but not FDM production clearance |
| rear reaction | Backplate seating ring/plane around terminal exits |
| insertion | interior/rear insertion; actuator toward cap/shell, terminals rearward |
| terminal exits | four rear openings/reliefs; not corner-post seats |

따라서 corner posts 때문에 body가 0.5 mm 뜨는 구조가 아니다. pusher 기준은 `body bottom →
housing top → actuator projection` 연쇄다. 다만 actual ITS의 body-bottom/foot 형상 실측이 없으므로
production pocket depth는 아직 잠그지 않는다.

## 4. Original PushBtn ↔ actual ITS feature map

| feature | ORIGINAL | ACTUAL ITS | STATUS |
|---|---:|---:|---|
| MAIN BODY X | 6.010 main / 6.310 skirt | 6.12 measured | NEAR-EQUIVALENT / actual controls |
| MAIN BODY Y | 6.010 main / 6.310 skirt | 6.05 measured | NEAR-EQUIVALENT / actual controls |
| BODY HEIGHT | 3.500 | 3.560 measured | NEAR-EQUIVALENT |
| TOTAL HEIGHT | 5.000 body-bottom→tip | 6.000 measured | DIFFERENT |
| ACTUATOR DIA | 3.500 | 3.350 measured | NEAR-EQUIVALENT |
| ACTUATOR PROJECTION | 1.500 | 2.440 measured | DIFFERENT |
| CORNER LUG COUNT | 4 exact | 4 visually observed by user | FEATURE EXISTS=YES |
| CORNER LUG X/Y | U/V=(±2.250,±2.250) | UNKNOWN | UNKNOWN |
| CORNER LUG SIZE | D1.000 nominal | UNKNOWN | UNKNOWN |
| CORNER LUG HEIGHT | 0.500 | UNKNOWN | UNKNOWN |
| TERMINAL ROOT | original detailed, 0.728×0.700 metal clue | 0.30×0.70 drawing / root physical UNKNOWN | DIFFERENT |
| TERMINAL ENVELOPE | 7.566 outer span clue | 7.90 drawing nominal | DIFFERENT |

Actual lug packaging rule은 **FEATURE EXISTS=YES / dimensions=UNKNOWN / first-article gate**다.
원본 D1×0.5를 실물 치수로 복사하지 않았다.

## 5. Audit-only pocket candidate

대표 local U/V/W 후보는 **7.10 × 7.10 clearance cavity**, rear body-bottom seat, terminal exits,
그리고 세 개의 교체/튜닝 가능한 datum pad를 쓴다. 모든 벽을 억지 끼움으로 만들지 않고
`−U 두 점 + −V 한 점`만 locating, 반대 벽은 clearance로 분리했다.

- actual body nominal gap before pads: U 0.490 / V 0.525 mm per side
- locating side after 0.25 pad: U **0.240** / V **0.275 mm**
- corner feature: D1.40 × 0.80 **UNKNOWN keep-out**, printed contact 없음
- pusher: **D2.60**, actuator radial centering margin **0.375 mm**
- nominal initial gap: **0.080 mm**; zero-preload를 의도하지만 FDM worst case는 아직 닫히지 않는다.
- removal: front/open insertion and rear terminal access; all-round press fit 없음

이 후보는 actual lug/body coupon에 맞춰 pad thickness와 keep-out을 재규격화하기 위한 review geometry다.

## 6. Pusher / travel / hard-stop re-derivation

| state | cap travel | pusher–actuator | actuator compression | structural-stop gap |
|---|---:|---|---:|---:|
| REST | 0.000 | 0.080 gap | 0.000 | 0.380 |
| CLICK (nominal inference) | 0.330 | contact | 0.250 | 0.050 |
| FULL audit stop | 0.380 | contact | 0.300 | 0.000 |

`0.350 mm`는 actual sample 기록의 upper observation/validation bound일 뿐 pre-travel/click/post-travel
분해가 없다. 후보는 0.30 compression에서 printed shoulder가 하중을 받도록 보였지만 이것도
**PROVISIONAL**이다. production hard stop은 실물 force–travel 또는 최소 REST/CLICK/BOTTOM-OUT
실측 전 확정할 수 없다.

## 7. Solver dependency audit

현재:

```text
shell/body clearance
→ choose_front_depths()
→ switch/body/terminal pose
→ carrier + pair bridge
→ build_cap() adapts last
→ later mechanism scripts inject D3 pusher + 0.350 guide/hard stop + support
```

권고:

```text
frozen exterior cap pose + W
+ actual body/lug seating datum
+ actual travel distribution
+ controlled pocket/rear reaction
+ pusher gap/length/tip
+ structural stop
→ simultaneous stack closure
→ shell/carrier/split/FDM clearance verification
```

`choose_front_depths` 자체의 shell-clearance 역할은 남길 수 있지만 최상위 solver가 될 수 없다.
`build_cap`, guide, pusher, hard stop, rear support와 pair bridge는 공통 stack result를 소비해야 한다.
production generator는 이번 작업에서 수정하지 않았다.

## 8. U/V/W, print orientation, FDM model

별도 carrier의 권장 출력 자세는 rear plate on bed라 pocket/pusher W가 build Z와 **0°**이고 pocket
walls도 build Z에 평행하다. 아래 global-Z 각도는 조립 자세를 보여 주며, 실제 인쇄에서는 각
carrier를 local frame으로 재배향해야 한다.

사용한 uncalibrated conservative 범위(mm): XY ±0.15, Z quantization ±0.10, small-pocket shrink
0…0.10/side, elephant foot 0…0.15/side, slope 0…0.20, bridge sag 0…0.20, support scar
0…0.15, warpage ±0.20, shell-half translation global axis별 ±0.20, rotation ±0.50°.

선형 worst-case 합산에서는 candidate locating-side minimum도 U −0.110 / V −0.075 mm가 되어
**BIND/PRELOAD** 가능성이 남는다. W stack도 모든 버튼에서 rest preload, fail-to-click,
overtravel을 동시에 배제하지 못한다. 그러므로 CAD `0.000 penetration`은 PASS가 아니다.

## 9. Per-button virtual propagation

| button | SWITCH LOCAL W | CORNER-LUG ACCOMMODATION | POCKET | PUSHER / REST GAP | REST GAP RANGE | TRAVEL | HARD STOP | FDM U | FDM V | FDM W STACK | SHELL-SPLIT | VERDICT |
|---|---|---|---|---|---:|---|---|---|---|---:|---|---|
| N1 | `-0.076, -0.872, -0.483` | D1.40×0.80 keep-out / actual UNKNOWN | 7.10 + 3 pads | D2.60 / 0.08 gap | -1.102…+1.262 | 0.25 nominal / UNKNOWN distribution | 0.38 provisional | 0.240 locate / −0.110 min | 0.275 locate / −0.075 min | ±1.182 | HIGH | **COUPON HOLD** |
| N2 | `-0.043, -0.859, -0.509` | D1.40×0.80 keep-out / actual UNKNOWN | 7.10 + 3 pads | D2.60 / 0.08 gap | -1.002…+1.162 | 0.25 nominal / UNKNOWN distribution | 0.38 provisional | 0.240 locate / −0.110 min | 0.275 locate / −0.075 min | ±1.082 | HIGH | **COUPON HOLD** |
| I2 | `-0.434, -0.757, -0.489` | D1.40×0.80 keep-out / actual UNKNOWN | 7.10 + 3 pads | D2.60 / 0.08 gap | -1.181…+1.341 | 0.25 nominal / UNKNOWN distribution | 0.38 provisional | 0.240 locate / −0.110 min | 0.275 locate / −0.075 min | ±1.261 | LOW | **COUPON HOLD** |
| I3 | `-0.082, -0.952, -0.295` | D1.40×0.80 keep-out / actual UNKNOWN | 7.10 + 3 pads | D2.60 / 0.08 gap | -1.034…+1.194 | 0.25 nominal / UNKNOWN distribution | 0.38 provisional | 0.240 locate / −0.110 min | 0.275 locate / −0.075 min | ±1.114 | MEDIUM | **COUPON HOLD** |
| I4 | `+0.038, -0.956, -0.292` | D1.40×0.80 keep-out / actual UNKNOWN | 7.10 + 3 pads | D2.60 / 0.08 gap | -1.025…+1.185 | 0.25 nominal / UNKNOWN distribution | 0.38 provisional | 0.240 locate / −0.110 min | 0.275 locate / −0.075 min | ±1.105 | MEDIUM | **COUPON HOLD** |
| M3 | `-0.224, -0.772, -0.595` | D1.40×0.80 keep-out / actual UNKNOWN | 7.10 + 3 pads | D2.60 / 0.08 gap | -1.097…+1.257 | 0.25 nominal / UNKNOWN distribution | 0.38 provisional | 0.240 locate / −0.110 min | 0.275 locate / −0.075 min | ±1.177 | MEDIUM | **COUPON HOLD** |
| M4 | `+0.288, -0.744, -0.603` | D1.40×0.80 keep-out / actual UNKNOWN | 7.10 + 3 pads | D2.60 / 0.08 gap | -1.109…+1.269 | 0.25 nominal / UNKNOWN distribution | 0.38 provisional | 0.240 locate / −0.110 min | 0.275 locate / −0.075 min | ±1.189 | MEDIUM | **COUPON HOLD** |
| N3 | `+0.692, -0.560, -0.455` | D1.40×0.80 keep-out / actual UNKNOWN | 7.10 + 3 pads | D2.60 / 0.08 gap | -1.172…+1.332 | 0.25 nominal / UNKNOWN distribution | 0.38 provisional | 0.240 locate / −0.110 min | 0.275 locate / −0.075 min | ±1.252 | LOW | **COUPON HOLD** |

Assembly global Z에 대한 W 각도(deg): N1 61.140, N2 59.371, I2 60.752, I3 72.847, I4 73.016, M3 53.486, M4 52.930, N3 62.931.

N1/N2는 seam/shared-carrier capture 때문에 HIGH, I3/I4/M3/M4는 MEDIUM, I2/N3는 LOW로
분류했다. 이것은 split 제거 권고가 아니며 screw/joint seating variation을 W에 투영한 것이다.

## 10. Thumb inner-housing relation

| metric | ORIGINAL | CURRENT LOWERED |
|---|---:|---:|
| minimum sampled local gap | 0.149 | 0.108 |
| median local gap (<5 mm region) | 2.333 | 3.842 |
| max reported local gap | 4.993 | 4.998 |
| contact proxy ≤0.10 mm² | 0.000 | 0.000 |
| near-shell area proxy <5 mm² | 5173.517 | 3019.579 |
| unsupported proxy 2…5 mm² | 2620.703 | 2321.419 |
| unsupported fraction of near area | 50.7% | 76.9% |

방법은 full boolean이 아니라 X=−10/0/+10 sections와 local centroid-to-shell samples다. 원본도
Backplate라는 별도 부품이며 exact fused/conformal zero-gap은 아니다. 그러나 lowering 후 near-shell
area가 줄고 median gap 및 unsupported fraction이 커졌다. 후보는 **frozen current shell의 local inner-facing tessellation에서
inward 0.30 mm로 유도한 render-only band**다. production에서는 mesh offset이 아니라 frozen BRep
local surface의 controlled offset/loft와 fastening datum으로 다시 만들어야 한다.

## 11. Load path / design-principle comparison

`USER FORCE → CAP → D2.60 PUSHER → ACTUATOR → SWITCH BODY → BODY-BOTTOM SEAT
→ POCKET/LOCATOR PADS → INNER HOUSING → SHELL`.

| function | comparison |
|---|---|
| switch locating | **HYBRID RECOMMENDED** — original seat principle + actual body metrology |
| corner-lug support | **ORIGINAL PRINCIPLE** — no printed load contact; keep-out only |
| pocket | **HYBRID RECOMMENDED** — source datum + FDM three-point pads |
| actuator contact / pusher | **CURRENT CONCEPT BETTER, DIMENSION RECOMPUTE** |
| guide / retention | **CURRENT BETTER** |
| hard stop | **CURRENT PRINCIPLE BETTER, 0.350 VALUE PROVISIONAL** |
| rear support | **HYBRID RECOMMENDED** — broad body seat, terminal-safe exits |
| inner housing / shell transfer | **LOCAL CONFORMAL REBASE** |

Candidate에서 lug point-contact, body cantilever와 all-wall press fit은 제거했지만, uncalibrated FDM
worst case가 locator pads와 W stack을 닫지 못하므로 production PASS는 아니다.

## 12. Required renders

- [01_original_detailed_pushbtn_top_bottom_isometric.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/01_original_detailed_pushbtn_top_bottom_isometric.png)
- [02_original_corner_lug_closeup.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/02_original_corner_lug_closeup.png)
- [03_original_pushbtn_inside_original_pocket.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/03_original_pushbtn_inside_original_pocket.png)
- [04_corner_lug_pocket_section.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/04_corner_lug_pocket_section.png)
- [05_simplified_its_vs_original_overlay.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/05_simplified_its_vs_original_overlay.png)
- [06_current_vs_source_faithful_pocket.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/06_current_vs_source_faithful_pocket.png)
- [07_actuation_stack_section.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/07_actuation_stack_section.png)
- [08_rest_click_full_sections.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/08_rest_click_full_sections.png)
- [09_original_thumb_inner_housing_shell_sections.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/09_original_thumb_inner_housing_shell_sections.png)
- [10_current_thumb_inner_housing_shell_sections.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/10_current_thumb_inner_housing_shell_sections.png)
- [11_proposed_conformal_inner_housing_section.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/11_proposed_conformal_inner_housing_section.png)
- [12_eight_button_local_axes.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/12_eight_button_local_axes.png)
- [13_shell_split_button_axis_relationship.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/13_shell_split_button_axis_relationship.png)
- [14_fdm_worst_case_tolerance_visualization.png](../renders/source_faithful_button_mechanism_fdm_rebase_audit/14_fdm_worst_case_tolerance_visualization.png)

## 13. Priority next step — production apply 전

1. **반드시 변경 검토:** pocket locating을 all-wall 6.40 clearance에서 datum-pad/clearance-surface
   구조로 rebase하고 pusher/hard-stop을 실측 travel stack으로 재계산한다.
2. **그대로 살릴 수 있음:** approved exterior, 8 center/axis, cap 외부 7.60/8.00 language,
   JaD/JfD split, current separate guide/structural-stop 원리.
3. **실측 필수:** actual lug U/V/D/H/base, main/skirt maximum, body-bottom seating flatness,
   actuator REST/CLICK/BOTTOM-OUT, terminal root/exit.
4. **coupon 필수:** 6.70/6.90/7.10 cavity와 0.15/0.25/0.35 locator pads, elephant-foot 방향,
   D2.4/2.6/2.8 pusher, 0.05/0.08/0.12 gap, assembly 반복성.
5. **production apply 전 render:** chosen measured ITS exact model in N1/N2 seam, all 8 local sections,
   Thumb BRep conformal insert/fastener sections, tolerance-min/max motion overlay.

## 14. Outputs / freeze / STOP

- audit STEP: `build123d_workbench/out/source_faithful_button_mechanism_fdm_rebase_audit/SOURCE_FAITHFUL_BUTTON_MECHANISM_AUDIT_ONLY.step`
- audit JSON: `build123d_workbench/out/source_faithful_button_mechanism_fdm_rebase_audit/source_faithful_button_mechanism_and_fdm_rebase_audit.json`
- report: `docs/76_source_faithful_button_mechanism_and_fdm_rebase_audit.md`
- protected production inputs preserved: **True**
- production geometry modification: **0**

**STOP.** 사용자 render review/승인 전 production pocket, carrier, cap, pusher, shell, Thumb에 적용하지 않는다.
