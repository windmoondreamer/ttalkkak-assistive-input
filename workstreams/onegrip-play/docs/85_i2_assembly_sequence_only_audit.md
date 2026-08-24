# 85 — I2 assembly-sequence-only audit

| Sequence | Result | Limiting collision | Swept collision |
|---|---|---|---:|
| A. I2 harness first | **PASS** | none | 0.000000000 mm³ |
| B. I2 detailed PushBtn second | **FAIL** | BODY ↔ HARNESS, 15.271882439 mm³ | 25.221116186 mm³ |
| C. I3 installed afterward | **FAIL (prerequisite)** | B prevents a legitimately completed I2 state | N/A |

Can assembly order alone solve docs/84 rigid-assembly failure? = **NO**

FINAL VERDICT = **B — ASSEMBLY ORDER PARTIALLY HELPS BUT ONE INSTALLATION STEP STILL FAILS**

## 1. Frozen authority

docs/84의 I2 one-piece harness, four straight legs, roots, tilts, lengths, thicknesses, direct slots,
1.03 mm/side × 0.93 mm mouths, shell, pusher, guide/hard stop, I2/I3 poses를 변경하지 않았다.
원본 `cad_dump/mesh_PushBtn.json`의 **3,530-facet one-solid detailed PushBtn**을 사용했고,
body/bottom/T1–T4/corner features를 유지했다. Actuator만 **D3.35 × projection 2.44 mm**이다.
Final collision verdict에 simplified proxy 사용 = **NO**. 새 STEP/geometry 생성 = **0**.

## 2. Sequence A — I2 harness before I3

- path: single straight docs/84 vector `[0.3415514166060052, -0.017899951255297575, 0.9396926207859084]`;
- travel / states: **1.600 mm / 33**;
- shell penetration: **0.000000000 mm³**;
- pusher penetration: **0.000000000 mm³**;
- guide / hard stop / clip penetration: **0.000000000 / 0.000000000 / 0.000000000 mm³**;
- swept collision volume: **0.000000000 mm³**;
- elastic bending assumed: **NO**.

따라서 I3 T2가 아직 없으면 현재 I2 one-piece harness는 현재 four slots에 먼저 설치할 수 있다.

## 3. Sequence B — detailed I2 PushBtn after seated harness

우선 기존 정상 switch preload authority인 **local −U open-side lateral path**를 사용했다.

- travel / states: **12.000 mm / 33**;
- maximum total unintended penetration: **24.408041982 mm³**;
- limiting pair: **BODY ↔ HARNESS**;
- limiting state / offset: **18 / [-5.25, 0.0, 0.0] mm**;
- limiting pair penetration: **15.271882439 mm³**;
- swept collision volume: **25.221116186 mm³**;
- shell / pusher / guide / hard-stop / clip maximum penetration on the documented path: **0 mm³**;
- I2 PushBtn insertion possible: **NO**.

Static FULL SEAT는 docs/84대로 penetration 0이지만, 실제 경로 중 body가 four-edge harness를 통과하지 못한다.
Static PASS를 Assembly PASS로 사용하지 않았다.

### Simple-path exclusion, without geometry search

| final approach | limiting pair | maximum sampled penetration |
|---|---|---:|
| documented −U lateral, 33 states | BODY ↔ HARNESS | 15.271882439 mm³ |
| rear axial −W, 33 states | BODY ↔ HARNESS | 20.006400668 mm³ |
| exterior axial +W, 33 states | BODY ↔ PUSHER | 63.086473062 mm³ |
| +U / +V / −V cardinal coarse gates | BODY ↔ HARNESS | 10.252846 / 13.010331 / 13.524522 mm³ |
| four UV diagonals, coarse gates | BODY ↔ HARNESS | minimum 9.923647 mm³ |

따라서 APPROACH→SHORT ALIGNMENT의 마지막 단순 translation도 어느 side/diagonal/axis로 진입하든 현재
harness 또는 pusher를 통과한다. 이를 회전과 세 번째 translation으로 우회하면 practical three-plus-DOF
puzzle motion이므로 지시 기준 practical FAIL이다. 회전 자동탐색이나 geometry optimization은 하지 않았다.

## 4. Sequence C — I3 afterward

Sequence C는 A와 B가 모두 PASS할 때만 실행하도록 명시되어 있다. B가 FAIL했으므로 legitimately completed
I2 assembly가 존재하지 않으며, I3를 teleport 배치해 C를 PASS시키는 검사를 하지 않았다.
결과는 **FAIL (prerequisite) / NOT EXECUTED**이다. 따라서 조립 순서 전체에서 I3 후설치는 성립하지 않는다.

## 5. Static manufacturing margin remains provisional

docs/84 reference를 변경 없이 유지한다:

- detailed terminal clearance: **0.059066 mm**;
- detailed I3 clearance: **0.059187 mm**;
- effective FDM section: **1.228681 mm**;
- minimum remaining shell: **1.245622 mm**.

Sequence A가 PASS해도 이 약 0.059 mm manufacturing margin은 provisional이다.

## 6. Renders and preservation

Sequence C 렌더는 prerequisite FAIL/STOP condition 때문에 생성하지 않았다. Teleport된 허위 조립 상태도 만들지 않았다.

- [01_sequence_a_i2_harness_start.png](../renders/i2_assembly_sequence_only_audit/01_sequence_a_i2_harness_start.png)
- [02_sequence_a_i2_harness_partial.png](../renders/i2_assembly_sequence_only_audit/02_sequence_a_i2_harness_partial.png)
- [03_sequence_a_i2_harness_full_seat.png](../renders/i2_assembly_sequence_only_audit/03_sequence_a_i2_harness_full_seat.png)
- [04_sequence_b_detailed_i2_pushbtn_start.png](../renders/i2_assembly_sequence_only_audit/04_sequence_b_detailed_i2_pushbtn_start.png)
- [05_sequence_b_detailed_i2_pushbtn_full_seat.png](../renders/i2_assembly_sequence_only_audit/05_sequence_b_detailed_i2_pushbtn_full_seat.png)
- [06_sequence_b_limiting_body_harness_collision.png](../renders/i2_assembly_sequence_only_audit/06_sequence_b_limiting_body_harness_collision.png)

All 126 protected docs/79–84, prior-audit and production artifacts retain identical SHA-256 hashes:
**True**. Production modification=0; geometry optimization=0;
8-button propagation=0; N2 redesign=0; physical coupon=0.
