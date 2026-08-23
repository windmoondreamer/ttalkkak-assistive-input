# OneGrip Play — Integrated V3 Internal Design Review

## 1. Review result

이번 검토는 `docs/50_finger_thumb_integrated_internal_architecture.md`와
`build123d_workbench/finger_thumb_integrated_v3.py`를 실제 최종 제품의 기계구조로
사용할 수 있는지 다시 평가한 LOCAL build123d + OCCT 리뷰다.

외부 Finger 8-button 배열과 thumb rigid cluster `(0,+12.25,-21.00) mm`는 전혀
변경하지 않았다. Onshape 접근, production V3 overwrite, 목업 STL, print plate와
출력 준비도 수행하지 않았다.

결론은 **REVISE**다. 이전 PASS는 충돌·최소벽·fragment 같은 디지털 gate에는
유효했지만, 다음 제품구조 문제를 검출하지 못했다.

1. N front carrier ↔ rear restraint: `10.657042 mm³` positive overlap
2. N front carrier ↔ N switch bodies: `0.293379 mm³` positive overlap
3. N rear restraint ↔ N switch bodies: `6.795207 mm³` positive overlap
4. three screws ↔ final shells: `8.091043 / 137.015052 / 74.117632 mm³`
5. N1 wiring four segments ↔ JfD: total `48.036648 mm³`
6. current thumb corridor lower end: shell 외부로 최소 `3.23 mm` 이탈
7. complete Finger shared trunk와 thumb module-to-trunk branch가 실제로 정의되지 않음
8. thumb seat는 exact zero-clearance contact지만 반대편 preload 기준이 없음
9. three-point screw triangle이 Finger 또는 thumb load region을 둘러싸지 않음

따라서 현재 `LOCAL INTEGRATED V3 = PASS`를 곧바로 제품 내부구조 승인으로 해석하면
안 된다.

## A. Internal architecture overview

현재 구조는 다음 세 층으로 나뉜다.

1. **Finger modules** — caps, ITS-1105 ×8, removable carrier/service part ×6
2. **Thumb module interface** — rigid thumb module, split flange, three datum pads
3. **Shell infrastructure** — boss halves ×6, M3-class screws ×3, wiring envelopes,
   lower electronics bay

기존 네 C-channel carrier는 switch axis와 owner shell이 서로 달라 각각 독립적인
조립 경로를 가진다. 이 네 부품을 한 덩어리로 합치면 part count는 줄지만 seam
삽입, pre-wire, terminal access와 개별 교체성이 악화된다. 문제는 carrier 수가 아니라
새 N1/N2 pair의 실제 겹침과 위치결정 방식이다.

## B. Part/function map

| 구조 | 역할 | shell/ownership | removable | 위치 결정 | 고정 | 조립/분해 |
|---|---|---|---|---|---|---|
| I2/I3 carrier | I2/I3 pocket, rear plate, terminal exits | JfD | yes | 두 frozen axis + JfD local wall | broad C-channel + shell closure | 외부 pre-wire 후 opposite ends에서 load, seam으로 삽입 |
| I4 carrier | 독립 I4 cradle | JaD | yes | I4 axis + JaD wall | broad C-channel + closure | pre-wire 후 seam 삽입 |
| M3 carrier | 독립 M3 cradle | JfD | yes | M3 axis + JfD wall | broad C-channel + closure | pre-wire 후 seam 삽입 |
| M4/N3 carrier | 서로 다른 축의 두 switch shared cradle | JaD | yes | M4/N3 axis + split trim datum | broad shared carrier + closure | opposite ends에서 load 후 seam 삽입 |
| N1/N2 front carrier | front locating rings | JfD locates, JaD clears | yes | N1/N2 axes + JfD relief | shell closure 주장 | wired switch를 축방향 삽입 |
| N1/N2 rear restraint | switch rear axial stop, terminal-root relief | 현재 두 shell 사이 floating | yes | 현재 positive key 없음 | shell closure 주장 | solder 후 별도 배치, shell open 시 loose |
| split seat/flange | Backplate perimeter support와 shell interface | JaD/JfD에 각 half fuse | no; module만 removable | split frame와 Backplate surface | shell 자체에 positive union | shell open 후 module을 lift-out |
| conformal pads ×3 | Backplate datum plane과 anti-rock support | split seat에 fuse | no | 비공선 3점 | flange arm과 positive union | module만 pads에서 분리 |
| new boss ×6 | 3개 체결축의 두 shell bearing/load path | 각 shell에 3개 fuse | no | YZ fixed axis | shell positive union + web | shell과 함께 출력 |
| M3-class screw ×3 | 두 shell clamp | +X, JfD→JaD | yes | boss axis | head shoulder + far-side thread 필요 | 외부 driver로 삽입/제거 |
| Finger corridor | 각 carrier terminal exit와 shared trunk | 주로 JfD/central | wire removable | 현재 local envelope 위주 | channel 미정 | 현재 complete route 없음 |
| Thumb corridor | thumb service loop를 lower bay로 전달 | posterior/inboard target | wire removable | 현재 X=24 mm exterior route | channel 미정 | 현재 internal route가 아님 |

## C. Carrier review

### 유지할 네 그룹

다음은 **KEEP AS-IS**다.

- `I2_I3_shared_carrier`
- `I4_carrier`
- `M3_carrier`
- `M4_N3_shared_carrier`

이들은 1.60 mm functional wall, valid single solid, no sliver 상태이며 owner shell과
insertion direction이 명확하다. 서로 합치면 조립성과 serviceability가 나빠진다.

### N pair

현재 front/rear 2-stage 개념 자체는 유효하다. pre-wire와 switch replacement를 위해
rear stop을 분리하는 이유도 합리적이다. 그러나 현재 두 부품은 실제로 동시에 존재할
수 없도록 겹친다.

| current exact pair | penetration mm³ |
|---|---:|
| front ↔ rear | `10.657042` |
| front ↔ switch bodies | `0.293379` |
| rear ↔ switch bodies | `6.795207` |

원인은 1.20 mm switch depth 자체가 아니다. V3는 N switch를 의도적으로 1.20 mm로
옮겼다. 문제는 front ring이 switch rear보다 약 0.71 mm 뒤까지 연장되고, outer-width
rear strap이 같은 영역에 들어오며, 2.40 mm rear bridge가 switch 쪽으로 되돌아오는
형상이다.

Review-only non-interfering seed에서는 front support depth를 줄이고 front bridge를
body 바깥쪽으로 이동했으며 rear bridge를 완전히 switch 뒤로 보냈다.

| review candidate | clearance mm | penetration mm³ |
|---|---:|---:|
| front ↔ rear | `0.391593` | `0` |
| front ↔ switch | `0.110000` | `0` |
| rear ↔ switch | `0.140000` | `0` |
| front ↔ shell | `0.408148` | `0` |
| rear ↔ shell | `0.924696` | `0` |
| pair ↔ thumb | `1.543619` | `0` |

두 candidate part는 각각 valid single solid다. 그러나 rear part를 assembly 중 잡아주는
positive key는 아직 없다. 최종안은 다음 단계에서 broad non-snap key를 추가해야 한다.

- wall `>=1.60 mm`
- engagement `>=3.0 mm`
- closed-shell axial float target `0.25–0.40 mm`
- tiny hook, rail, snap, thin bridge 사용 금지

## D. N1/N2 review

Front locating-ring 개념은 유지한다. switch body보다 충분히 큰 parameterized pocket과
두 axis를 한 carrier에서 관리하는 방식은 N1/N2 row alignment에 유리하다.

Rear restraint는 terminal root를 피하려는 목적은 맞지만 현재 다음 문제가 있다.

- 현재 switch와 positive overlap이 있어 조립 불가
- front carrier와 positive overlap이 있어 별도 part로 조립 불가
- terminal root 최소 여유가 `0.506071 mm`로 service `0.80 mm` gate보다 작음
- shell과 `0.924696 mm` 떨어져 있어 closure가 직접 preload/capture하지 않음
- positive rear key count `0`; open-shell assembly 중 떨어질 수 있음

따라서 rear restraint는 삭제보다는 **재구성**이 맞다. 분리형을 유지하되 corrected
front/rear zones와 broad key를 사용하고, terminal/solder branch를 실제 conductor OD로
재검증해야 한다.

## E. N2 seam review

N2의 locating principle은 **KEEP AS-IS / ACCEPT**다.

- JfD: locating shell
- JaD: clearance/capture only
- front carrier ↔ opposite JaD: `1.054171 mm`
- 0.80 mm gate 위 margin: `0.254171 mm`
- cap center movement: `0`

JaD가 N2 axis를 밀어 정렬하는 구조가 아니므로 seam variation이 switch axis에 직접
누적되지 않는다. 다만 rear restraint는 seam gate와 별개로 수정해야 한다. 현재
`0.924696 mm` rear-to-shell free space를 “preload”로 해석하면 안 된다.

## F. Thumb seat review

비공선 3점 지지는 Backplate plane을 정의하고 rocking을 막는 올바른 방향이다. split
flange가 양 shell에 positive union된 점과 module이 shell open 후 빠지는 service concept도
좋다.

현재 수치:

- outer/inner: `42×64 / 34×56 mm`
- wall: `1.60 mm`
- pads: 3 × `5.0 mm`
- reach: `4.8 mm`
- seat volume: 약 `1,755.33 mm³`
- modeled contact clearance: `0 mm`

문제는 exact conformal subtraction이 실제 FDM에서 zero-clearance 접촉이 된다는 점과
반대쪽 preload feature가 정의되지 않았다는 점이다. warpage가 있으면 완전 삽입 불가,
rocking 또는 shell closure stress 중 하나가 발생할 수 있다.

추천:

- frame/pad 위치는 유지
- assembly clearance `0.15–0.25 mm` parameter 추가
- 반대쪽에 broad compliant shim/preload zone 하나 정의
- 구조용 접착제는 사용하지 않음
- 실제 Backplate 두께와 flatness 측정 전 flange 축소는 보류

## G. Fastening review

### 현재 geometry 오류

현재 boss는 bore를 가진 상태로 shell에 fuse된다. 하지만 fuse 뒤 final shell에 bore를
다시 절삭하지 않아 기존 shell wall이 축을 메운다.

| screw | current screw↔final shell mm³ | review final-bore candidate mm³ |
|---|---:|---:|
| 1 | `8.091043` | `0` |
| 2 | `137.015052` | `0` |
| 3 | `74.117632` | `0` |

Review-only candidate는 boss-shell union 뒤 다음을 final-cut했다.

- screw clearance: Ø`3.40 mm`
- head counterbore: Ø`5.80 mm`
- head radial clearance: `0.15 mm`
- head bearing shoulder radial width: `1.70 mm`
- insert pocket: Ø`4.60 mm`
- insert radial wall: `2.30 mm`

결과는 두 shell valid single solid, 세 screw intersection 0이다.

### clamp distribution

현재 YZ screw triangle:

- `(10,35)`
- `(25,8)`
- `(15.8,-21.35)`
- area: `344.325 mm²`

Finger center 전체와 thumb Backplate center 모두 이 triangle 밖이다. Finger center에서
가장 가까운 screw까지의 worst distance는 `47.143 mm`다. 즉 control force가 shell을
벌리는 쪽에서 clamp가 load를 둘러싸지 않고 shell bending에 의존한다.

따라서 bore correction만으로 fastening을 ACCEPT할 수 없다. 최소 한 체결점을 negative-Y
control side 또는 seam perimeter 쪽으로 재분배하고, actual shell wall과 external driver
appearance를 함께 확인해야 한다.

### hardware concept

| concept | 반복 분해 | FDM 강도 | 공간 | 조립 | 부품성 | 순위 |
|---|---|---|---|---|---|---:|
| M3 heat-set insert + machine screw | best | 적절한 boss에서 best | medium | 열삽입 depth 관리 필요 | 높음 | 1 |
| captured M3 nut + screw | good | good | nut trap/access가 큼 | blind nut handling 위험 | 높음 | 2 |
| plastic self-tapping | poor | 재료/층방향 의존 | small | 첫 조립은 쉬움 | 높음 | 3 |

현재 프로젝트에는 **M3 heat-set insert + machine screw**가 가장 현실적이다. insert
OD/length와 screw length는 실제 SKU 측정 전 parameter로 둔다. M3×16은 후보일 뿐
bottom-out, engagement와 head seat가 검증되기 전 확정하지 않는다.

## H. Wiring review

### Current Finger wiring

비-N switch는 carrier 뒤의 짧은 `4.0×3.2 mm` service envelope까지만 있고 electronics
bay로 내려가는 complete shared trunk가 없다. N1/N2는 formed lead와 13 mm wire를
모델링했지만 N1 바깥쪽 두 branch가 JfD를 관통한다.

| N1 segment | JfD penetration mm³ |
|---|---:|
| solder `-1,-1` | `2.991088` |
| wire `-1,-1` | `22.972703` |
| solder `-1,+1` | `2.556758` |
| wire `-1,+1` | `19.516099` |
| total | `48.036648` |

### Current Thumb wiring

현재 lower corridor bounding X는 `22.4..25.6 mm`다. `Z=-35 mm`의 shell 외곽은 약
`X=±19.17 mm`이므로 corridor가 외부로 최소 `3.23 mm` 떨어져 있다. shell intersection
0은 “내부에서 잘 비켜갔다”는 뜻이 아니라 “처음부터 shell 밖에 있다”는 뜻이다.

### Review-only route seeds

- Finger 4 mm trunk envelope: penetration `0`, minimum clearance `4.410469 mm`
- Thumb 3.2 mm inboard harness envelope: penetration `0`, minimum clearance
  `0.929205 mm`

이는 full branch design이 아니라 lower trunk feasibility seed다. 최종 구조는:

- Finger open channel `>=6×4 mm`
- Thumb open channel `>=4×4 mm`
- bend radius `>=4 mm`
- tiny clip 없음
- 두 broad removable tape/cover zone
- 실제 conductor count와 insulation OD 반영
- solder joint와 service loop를 carrier 뒤에서 손으로 볼 수 있게 유지

가 필요하다.

## I. Assembly review

현재 순서는 loose rear restraint와 미정의 wire trunk 때문에 실제 작업자가 shell을 닫기
어렵다. 추천 순서는 다음과 같다.

1. open JaD에 heat-set insert를 depth stop으로 설치하고 bore를 전수 검사한다.
2. I2/I3, I4, M3, M4/N3 carrier module을 pre-wire/load한다.
3. N1/N2를 corrected front carrier에 넣고 revised broad-key rear restraint를 설치한다.
4. 모든 Finger branch를 open shared trunk로 보내고 두 broad zone에서 임시 고정한다.
5. thumb module을 three datum pad에 seat하고 필요하면 broad preload shim을 설치한다.
6. thumb cable을 inboard channel로 보낸다.
7. lower bay의 controller/battery를 연결하고 service loop를 확인한다.
8. wire를 직접 보면서 JfD를 JaD에 닫는다.
9. seam이 먼저 완전히 닫힌 뒤 M3 screws를 체결한다.

현재 blind operation은 loose N rear restraint 잡기, uncontained wire를 seam 밖으로 피하기,
thumb preload를 보지 못한 채 shell을 닫는 세 가지다.

## J. Service review

- I2/I3, I4, M3, M4/N3 switch: 실제 교체 가능성이 높음
- N1/N2: CAD상 removable이지만 current positive overlap으로 실제 교체 불가
- thumb module: shell open 후 제거 가능하나 zero-clearance seat가 달라붙을 수 있음
- wiring: local solder joint는 보이지만 complete trunk와 service loop가 없어 repair path 미완성
- fastening: heat-set 적용 시 반복 service 적합, self-tapping은 부적합

## K. Structural/load-path review

### Finger

`cap → actuator → ITS body → carrier rear plate/walls → owner shell`

기존 네 carrier는 1.60 mm wall과 broad plate가 있어 load path가 단순하다. N pair는
current overlap을 제거하고 rear stop을 key로 잡아야 같은 수준이 된다.

### Thumb

`thumb module/Backplate → three pads/flange → both shells → shell clamp`

세 점은 유효하지만 preload가 없으므로 Backplate와 pad 사이의 힘 전달량이 공차에 따라
달라진다.

### Shell clamp

추천 load path는
`screw head → JfD bearing shoulder/web → seam → JaD boss → heat-set insert`다.
현재 final bore가 막혀 있고 clamp triangle이 control load region을 둘러싸지 않아 이
load path는 아직 성립하지 않는다.

## L. FDM realism

0.4 mm nozzle 기준에서 1.60 mm carrier wall, review head shoulder 1.70 mm, insert radial
wall 2.30 mm는 출력 가능한 범위다. 그러나 다음은 반드시 수정/실물 확인해야 한다.

- final bore를 union 뒤 다시 절삭
- hole roundness와 insert depth coupon
- insert 설치축 주변 layer split 방지
- N pocket/body nominal `0.11–0.14 mm` fit의 printer별 보정
- N broad key는 layer 방향을 가로지르는 얇은 snap이 아니라 broad shear face로 구성
- thumb zero-clearance contact 제거
- wire channel internal roof를 만들지 말고 open channel로 구성
- support scar가 pad, pocket, bearing shoulder에 닿지 않도록 orientation 유지

## M. Electronics free-volume assessment

Lower handle 내부 cavity section:

| Z mm | inner area mm² | inner bbox X×Y mm |
|---:|---:|---:|
| `-65` | `540.960` | `21.072×25.672` |
| `-55` | `540.960` | `21.072×25.672` |
| `-45` | `942.044` | `33.060×35.593` |
| `-35` | `941.355` | `32.335×35.756` |

단면 적분 근사 `Z=-65..-35` cavity volume은 약 `22,242 mm³`다. 다음 reserve box는
shell과 mechanical internals 모두 intersection 0이다.

- MCU/IO/connector board reserve: `27×17×6 mm`, `2,754 mm³`
- compact battery reserve: `16×18×7 mm`, `2,016 mm³`

따라서 현재 mechanical internals가 electronics 공간을 없애지는 않았다.
`ELECTRONICS SPACE = ACCEPT`다. 단 battery capacity, board mounts, connector access와
charging port는 아직 설계되지 않았고 이 reserve보다 큰 배터리는 다시 검토해야 한다.

## N. Simplification opportunities

1. 기존 네 carrier는 합치지 않는다.
2. N front support의 switch 뒤 불필요한 연장을 제거한다.
3. N rear bridge를 switch 뒤로 보내고 broad key 하나의 명확한 기능만 맡긴다.
4. shell 밖의 thumb corridor를 삭제하고 하나의 inboard channel로 대체한다.
5. 개별 Finger service envelope를 lower shared trunk에 연결한다.
6. boss pre-bore/fuse 중복을 없애고 final-cut 순서 하나로 통일한다.
7. thumb flange 축소는 preload와 실제 Backplate 측정 전 보류한다.
8. localized HW504 AABB relief는 현재 유지하되, 추후 wall section에서 과도한 material
   removal이 확인될 때만 단순 capsule relief로 교체한다.

## O. Changes actually made

Production V3는 수정하지 않았다. 별도 review script 안에서만 다음 candidate를 만들고
전후를 비교했다.

1. boss-shell union 뒤 final bore/counterbore/insert pocket 적용
2. N front support shortening + bridge outward shift
3. N rear bridge를 switch 뒤로 이동
4. collision-free lower Finger trunk envelope seed
5. inboard Thumb harness envelope seed
6. collision-free board/battery reserve volumes

Review-only source:

- `build123d_workbench/integrated_v3_internal_design_review.py`
- `build123d_workbench/render_integrated_v3_internal_design_review.py`
- `build123d_workbench/out/finger_thumb_integrated_v3_internal_review/integrated_v3_internal_design_review.json`

STL/print plate/mockup은 생성하지 않았다.

## P. Final recommended architecture

다음 순서로 V3.1 internal candidate를 단계적으로 만들어야 한다.

1. final screw bores와 actual heat-set insert parameter 확정
2. N front/rear non-interfering geometry 반영
3. broad N rear key 추가와 assembly sweep
4. one negative-Y/perimeter clamp point를 포함하도록 fastening redistribution
5. complete Finger branch/trunk와 Thumb internal branch/channel 구축
6. thumb pad clearance + broad preload zone 추가
7. electronics mounts/connectors를 reserve 안에 배치
8. 모든 exact gate 재실행 후 integrated physical validation

큰 변경을 한 번에 합치지 않는다. 각 단계에서 external centers/caps/thumb target은 계속
hard-freeze하고 이전 단계보다 나빠지면 rollback한다.

## Internal visualization

필수 내부뷰 10장과 section 3장을 다음 폴더에 생성했다.

`renders/finger_thumb_integrated_v3_internal_review/`

주요 파일:

1. `01_transparent_full_assembly.png`
2. `02_JaD_removed.png`
3. `03_JfD_removed.png`
4. `04_all_carriers_highlighted_annotated.png`
5. `05_N1_N2_exploded.png`
6. `06_thumb_seat_isolated.png`
7. `07_screws_bosses_isolated.png`
8. `08_finger_wiring_only.png`
9. `09_thumb_wiring_only.png`
10. `10_full_exploded_mechanical.png`
11. `11_section_A_N1_N2_thumb.png`
12. `12_section_B_middle_finger_carriers.png`
13. `13_section_C_thumb_seat_screw_boss.png`

## Design quality classification

| subsystem | classification |
|---|---|
| I2/I3 carrier | **KEEP AS-IS** |
| I4 carrier | **KEEP AS-IS** |
| M3 carrier | **KEEP AS-IS** |
| M4/N3 carrier | **KEEP AS-IS** |
| N1/N2 carrier | **REDESIGN RECOMMENDED** |
| N2 seam | **KEEP AS-IS** |
| thumb seat | **MINOR IMPROVEMENT** |
| screw fastening | **REDESIGN RECOMMENDED** |
| Finger wiring | **REDESIGN RECOMMENDED** |
| Thumb wiring | **REDESIGN RECOMMENDED** |
| shell integration | **MINOR IMPROVEMENT** |

## Final verdict

```text
INTERNAL ARCHITECTURE = REVISE
N1/N2 = REVISE
N2 SEAM = ACCEPT
THUMB SEATING = REVISE
FASTENING = REVISE
WIRING = REVISE
ASSEMBLY = REVISE
SERVICEABILITY = REVISE
STRUCTURE = REVISE
FDM REALISM = REVISE
ELECTRONICS SPACE = ACCEPT
```

### 이 구조를 실제 최종 제품 내부구조의 baseline으로 삼아도 되는가?

**NO.**

외부 UX와 기존 네 carrier, N2 locating principle은 유지할 수 있다. 그러나 N pair의
positive overlap, screw axis blockage/clamp distribution, incomplete/outside wiring과
thumb preload를 수정하기 전에는 실제 최종 제품 내부구조 baseline으로 승인할 수 없다.

