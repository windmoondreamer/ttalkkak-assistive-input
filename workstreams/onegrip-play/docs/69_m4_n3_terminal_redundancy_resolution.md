# 69 — M4/N3 terminal redundancy resolution

## 1. Final verdict

- **M4 T2 electrical role = UNUSED / redundant Node A terminal**
- **N3 T3 electrical role = UNUSED / redundant Node B terminal**
- M4 T2 EXTERNAL TRIM SUFFICIENT = **YES**
- N3 T3 EXTERNAL TRIM SUFFICIENT = **YES**
- housing intrusion required = **NO**
- old penetration = **0.283393028 mm³**
- new penetration = **0.000000000 mm³**
- new minimum clearance = **0.262733122 mm**
- active terminal solder access = **PASS**
- M4/N3 regression = **PASS**
- EXTERIOR = **PRESERVED**

## 2. Physical continuity / electrical node map

동일 ITS-1105 실물 측정 결과를 M4와 N3에 적용했다.

| pair | rest | pressed |
|---|---:|---:|
| T1-T2 | connected | connected |
| T3-T4 | connected | connected |
| T1-T3 | open | connected |
| T1-T4 | open | connected |
| T2-T3 | open | connected |
| T2-T4 | open | connected |

M4와 N3 모두 평상시 **Node A = T1/T2**, **Node B = T3/T4**다. 누르면 Node A와 Node B가 연결된다. M4는 T1을 Node A active terminal로 유지하므로 T2를 UNUSED 처리할 수 있다. N3는 T4를 Node B active terminal로 유지하므로 T3를 UNUSED 처리할 수 있다. 나머지 비충돌 terminal도 원형 그대로 유지했다.

## 3. Housing face / collision / trim exact result

| terminal | modeled internal root start | housing outer face | full external leg mm | collision interval from face mm | one-side minimum trim mm | one-side max stub mm | external-only |
|---|---|---|---:|---:|---:|---:|---:|
| M4 T2 | 8.162252, -5.436312, -7.418412 | 8.145853, -5.196724, -7.224341 | 2.058428 | 0.622960 … 1.673901 | 1.434599 | 0.623830 | YES |
| N3 T3 | 9.015913, -4.860344, -6.760685 | 8.755546, -4.731524, -6.656043 | 2.058428 | 0.270418 … 1.320295 | 1.787637 | 0.270791 | YES |

docs/68의 N3 ROOT 0.011038 mm³는 ROOT 분류가 housing 안쪽 0.30 mm부터 바깥쪽 0.40 mm까지 포함하기 때문에 표시된 값이다. exact collision vertex를 각 terminal의 housing face 기준으로 투영한 결과와 flush probe를 함께 사용해 실제 housing 내부 침범 필요 여부를 판정했다.

## 4. Selected production-intent local trim

| terminal | selected trim mm | remaining external stub mm | housing intrusion |
|---|---:|---:|---:|
| M4 T2 | 1.758428 | 0.300000 | NO |
| N3 T3 | 1.758428 | 0.300000 | NO |

두 UNUSED leg는 housing 외부에서만 절단한다. plastic housing 및 내부 leadframe은 변경하지 않는다. 선택 stub은 **0.300 mm**이며, 두 conservative 0.12 mm service envelope 사이 exact penetration은 0, practical clearance는 **0.262733 mm**다.

## 5. Active terminals / regression

- M4 active = T1(Node A), T3/T4(Node B)
- N3 active = T1/T2(Node A), T4(Node B)
- active terminal geometry change = 0
- active terminal ↔ carrier penetration = 0
- wire exit / wire envelope ↔ carrier penetration = 0
- cap-gap minimum = **3.132653696 mm** (approved 3.132654 mm, exact tolerance 1e-6)
- reaction support = UNCHANGED
- hard stop = PASS
- service = PASS
- cap/switch/carrier/guide/retention/reaction/hard-stop/exterior hashes = PRESERVED

## 6. Outputs / scope

- `build123d_workbench/out/m4_n3_terminal_redundancy_resolution/m4_n3_terminal_redundancy_resolution.json`
- `build123d_workbench/out/m4_n3_terminal_redundancy_resolution/M4_N3_TRIMMED_TERMINALS_LOCAL_REFERENCE.step` — local terminal metal reference only
- `renders/m4_n3_terminal_redundancy_resolution/01_terminal_node_map.png`
- `renders/m4_n3_terminal_redundancy_resolution/02_external_trim_before_after.png`
- `renders/m4_n3_terminal_redundancy_resolution/03_trimmed_terminal_clearance.png`
- `renders/m4_n3_terminal_redundancy_resolution/04_m4_n3_both_full_regression.png`

No full shell, full assembly, STL, print plate, HW504 or actual joystick geometry was generated or evaluated. **STOP.**
