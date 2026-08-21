# 29. MIDDLE LOW-PROFILE SWITCH ENVELOPE FEASIBILITY

## Status

- **Onshape CAD WRITE: 0건**
- **INDEX_FINAL_VALIDATED: 완전 FREEZE 유지**
- 비교 version: `03ede76e83b5c865d9a69c35`
- configuration: `default`
- **Hardware fallback: A-family — 6×6×6 유지 가능**
- **MIDDLE CAD WRITE = HOLD**

이번 결과의 핵심은 low-profile이 INDEX clearance의 필수조건이 아니라는 점이다. H=6.0 mm에서도
robust clearance 0.50 mm를 통과하는 새 center/free-axis 조합을 찾았다. 이 조합은 OPTION C보다
row translation을 2.987 mm 줄인다. H≤3.5 mm에서는 다시 0.586 mm를 더 줄일 수 있지만, 그
추가 이득은 body-height 감소폭에 비해 작다.

## 1. Source of truth와 READ-ONLY 경계

다음 동결 tessellation을 docs/28과 같은 좌표계로 재사용했다.

- `INDEX_FINAL_SHELL_KEEPOUT`
- `INDEX_FINAL_RWID`
- `INDEX_FINAL_RZKD`
- JaD/JfD 원래 shell surface projection

모든 계산은 로컬 triangle-soup/OBB 연산이다. Onshape Feature 생성·수정·삭제·suppress,
workspace 변경, version 생성은 없었다. 이번 실행에서는 동결 cache를 재사용했으므로 Onshape
GET도 새로 호출하지 않았다.

## 2. Parametric envelope

고정값:

- switch footprint: 6.0×6.0 mm
- pocket footprint: 6.4×6.4 mm
- holder width: 12.4 mm
- shell wall datum: 3.0 mm
- holder front trim datum: 2.8 mm
- rear retention land: 1.2 mm
- cap: 8 mm 외형, shell surface의 기존 접촉 중심 유지

H와 nominal front lip `L`에 따른 최소 rear envelope는 다음으로 계산했다.

```text
switch front depth = 3.0 + L
switch rear depth  = 3.0 + L + H
holder rear datum  = 3.0 + L + H + 1.2
holder depth behind 2.8 trim datum = 1.4 + L + H
```

따라서 H가 줄면 holder rear도 같은 양만큼 줄었다. 6 mm switch용 12.5 mm rear holder를 낮은
H에 그대로 적용하지 않았다.

## 3. Search와 gate

docs/28의 coarse center grid에서 시작해 robust 경계 주변을 0.125…0.25 mm 간격으로 정련했다.
각 center 후보에서 surface에 다시 seat한 뒤, local normal 주변과 기존 A/B/C 축 주변에서 버튼당
900…2,200개의 축을 재생성했다. 4축 조합은 다음 우선순위로 정렬했다.

1. exact INDEX clearance ≥0.50 mm
2. nominal row translation 최소
3. pitch 10.5…11.5 mm 안에서 11 mm 유지
4. 3+1 split wall 유지
5. 최대 local-normal deviation 최소

keep-out broad phase는 target의 절반만큼 팽창한 full holder를 사용했고, 최종 판정은 반드시 exact
triangle↔OBB Euclidean distance로 다시 계산했다. 따라서 팽창 broad phase는 탐색 가속용이고,
아래 clearance 숫자가 최종 gate이다.

`best`는 기록된 hierarchical center/free-axis search에서 찾은 **best certified candidate**를 뜻한다.
비매끄러운 mesh 거리 위에서의 연속 전역최적 증명은 아니다.

최종 hard gate:

- switch SAT ≥1.20 mm
- pocket divider ≥0.80 mm
- split wall ≥1.50 mm
- screw clearance ≥2.50 mm
- 3+1 ownership 유지
- frozen INDEX shell/RWID/RZKD와 switch·pocket·holder intersection 0
- exact minimum INDEX clearance ≥0.50 mm
- 8 mm cap pair separation >0

## 4. Height sweep 요약

아래 front-lip 범위는 선택된 center/axis에서 exact geometry gate가 확인된 **certified range**다.
실제 stem reach와 actuation travel이 확인되지 않았으므로 제품 설계 범위로 곧바로 승인한 값은 아니다.

| H | best row ΔX/ΔY/ΔZ | ‖Δ‖ | max individual | max axis dev | pitch M1–2 / M2–3 / M3–4 | min SAT | divider | split | screw | INDEX | holder rear / depth | certified lip | seat/reach corridor |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|---|
| 6.0 | +1.250 / +3.750 / −5.500 | 6.773 | 9.992 | 26.891° | 11.118 / 11.372 / 11.164 | 1.344 | 0.886 | 1.532 | 6.183 | **0.580** | 12.458 / 9.658 | 2.258…2.400 | 5.258…5.400 |
| 5.0 | +1.250 / +3.750 / −5.500 | 6.773 | 9.992 | 26.891° | 11.118 / 11.372 / 11.164 | 1.464 | 1.005 | 1.561 | 6.729 | **0.580** | 11.458 / 8.658 | 2.258…3.375 | 5.258…6.375 |
| 4.3 | +1.250 / +3.750 / −5.500 | 6.773 | 9.992 | 26.891° | 11.118 / 11.372 / 11.164 | 1.464 | 1.005 | 1.561 | 7.150 | **0.580** | 10.758 / 7.958 | 2.258…4.000 | 5.258…7.000 |
| 3.5 | +1.500 / +3.125 / −5.125 | 6.187 | 9.849 | 24.709° | 11.100 / 11.348 / 11.015 | 1.506 | 1.034 | 1.514 | 7.750 | **0.532** | 9.932 / 7.132 | 2.232…2.400 | 5.232…5.400 |
| 3.1 | +1.500 / +3.125 / −5.125 | 6.187 | 9.849 | 24.709° | 11.100 / 11.348 / 11.015 | 1.506 | 1.034 | 1.514 | 8.024 | **0.607** | 9.532 / 6.732 | 2.232…2.800 | 5.232…5.800 |

모든 길이 단위는 mm다. `holder rear`는 surface datum에서 rear까지이고, `depth`는 2.8 mm trim
datum 뒤쪽 길이다. 모든 행에서 INDEX intersection count는 0이다.

### H=6.0 mm

6 mm body 자체가 robust 0.50 mm gate를 막지 않는다. 이전 OPTION A/B의 0.006/0.015 mm를
재사용하지 않고 축을 다시 풀었을 때 0.579963 mm를 확보했다. 지배 minimum은 M4 holder 대
frozen INDEX shell surface다.

### H=5.0 mm

H=6 winner가 envelope 포함관계로 그대로 PASS한다. 별도 H=5 axis rerun도 수행했으나 더 작은
exact-pass center는 인증되지 않았다. rear datum은 1.0 mm 줄지만 minimum clearance가 holder의
공통 front/side 영역에 있어 row 위치는 H=6과 같다.

### H=4.3 mm

H=6 winner가 그대로 PASS하며 rear datum은 1.7 mm 줄었다. 그러나 holder front width 12.4 mm가
유지되므로 robust gate에서 center displacement 개선은 인증되지 않았다.

### H=3.5 mm

더 짧은 pair envelope가 다른 축 조합을 허용해 row norm이 6.187 mm로 감소했다. exact INDEX
clearance는 0.531897 mm로 PASS지만 0.50 mm gate에 가깝다. nominal lip을 2.45 mm로 늘리면
clearance가 0.491 mm가 되어 FAIL하므로 lip range가 좁다.

### H=3.1 mm

H=3.5와 같은 center/axis를 사용하면서 rear envelope가 0.4 mm 더 줄어 INDEX clearance가
0.607206 mm로 증가한다. row displacement는 더 줄지 않았다.

## 5. Centers와 optimized axes

H=6.0/5.0/4.3은 같은 certified center/axis를 사용한다.

| Button | center X/Y/Z | optimized axis X/Y/Z | normal deviation |
|---|---|---|---:|
| M1 | −19.879659 / +0.138133 / −11.500000 | −0.787388 / −0.566203 / −0.243791 | 21.966664° |
| M2 | −13.306340 / −8.412238 / −14.200000 | −0.579137 / −0.812952 / −0.060912 | 26.891325° |
| M3 | −3.830370 / −14.089823 / −11.500000 | +0.251151 / −0.791271 / −0.557506 | 20.597581° |
| M4 | +7.306877 / −13.321625 / −11.500000 | +0.193384 / −0.783718 / −0.590244 | 1.918069° |

H=3.5/3.1은 다음 certified center/axis를 사용한다.

| Button | center X/Y/Z | optimized axis X/Y/Z | normal deviation |
|---|---|---|---:|
| M1 | −19.835372 / −0.614992 / −11.125000 | −0.837519 / −0.499950 / −0.220481 | 20.941536° |
| M2 | −12.899418 / −8.744828 / −14.125000 | −0.601521 / −0.782846 / −0.159135 | 21.830425° |
| M3 | −3.537874 / −14.413709 / −11.125000 | +0.320429 / −0.733473 / −0.599452 | 24.708626° |
| M4 | +7.444328 / −13.569623 / −11.125000 | +0.224859 / −0.772793 / −0.593489 | 0.000000° |

8 mm cap은 optimized internal axis를 따라 기울이지 않고 각 center의 shell surface normal을
유지했다. 최소 cap pair separation은 각각 2.294 mm와 2.134 mm여서 외형 접촉 배열은 유지된다.

## 6. INDEX↔MIDDLE 3D center spacing과 OPTION C 비교

| H group | I1–M1 | I2–M2 | I3–M3 | I4–M4 |
|---|---:|---:|---:|---:|
| OPTION C | 30.318 | 32.798 | 28.667 | 29.101 |
| H=6.0/5.0/4.3 | 27.141 | 29.360 | 25.596 | 26.070 |
| H=3.5/3.1 | 26.375 | 29.140 | 25.124 | 25.633 |

OPTION C reference:

- Δ=(+1.0,+5.5,−8.0) mm
- row norm 9.759611 mm
- M2 displacement 13.382987 mm
- INDEX clearance 0.783400 mm

H=6.0/5.0/4.3 best는:

- row norm을 2.986502 mm, **30.601%** 줄인다.
- M2 displacement를 3.391265 mm 줄여 9.991722 mm로 만든다.
- 네 INDEX↔MIDDLE spacing을 3.031…3.438 mm 줄인다.

H=3.5/3.1 best는:

- row norm을 3.572426 mm, **36.604%** 줄인다.
- M2 displacement를 3.533743 mm 줄여 9.849244 mm로 만든다.
- 네 INDEX↔MIDDLE spacing을 3.468…3.943 mm 줄인다.

그러나 low-profile만의 추가 이득은 H=6 best 대비 row norm 0.585924 mm, 8.65%다. H=6에서도
이미 OPTION C 대비 큰 개선이 발생하므로, low-profile이 명확히 우월하다고 판정할 정도는 아니다.

## 7. Maximum allowable H 역산

제품 후보 sweep의 상한인 H=6.0 mm가 세 clearance 목표에서 모두 가능했다. 따라서 candidate
range 안에서의 결과는 모두 `Hmax ≥6.00 mm`다. OPTION C의 ergonomic ceiling
(`row norm ≤9.759611`, `M2 displacement ≤13.382987`) 안에서 각 목표용 고정 center/axis branch를
H>6으로 연장한 보수적 certified ceiling은 다음과 같다.

| target | H=6 exact clearance | branch row norm | certified H | next tested FAIL | 해석 |
|---:|---:|---:|---:|---:|---|
| ≥0.50 | 0.579963 | 6.773 | **H≤6.10** | 6.20 | pair SAT/divider가 먼저 제한 |
| ≥0.80 | 0.890436 | 8.047 | **H≤6.20** | 6.30 | pair SAT/divider가 먼저 제한 |
| ≥1.00 | 1.134601 | 8.732 | **H≤6.30** | 6.40 | pair SAT/divider가 먼저 제한 |

이는 각 고정 branch의 certified ceiling이지 H>6 전역 재최적화의 수학적 상한은 아니다. 실제 SKU
요구조건으로 가장 보수적으로 쓰려면 **6.0×6.0 footprint, body H≤6.0 mm**를 사용하면 세 목표
branch를 모두 보존한다. 0.50 mm만 요구할 때도 low-profile 필수조건은 나오지 않았다.

## 8. Front lip, seat depth, stem travel

front lip 하한은 tilted switch front 네 모서리 모두에서 실제 material lip ≥0.50 mm가 되도록
해석적으로 계산했다. 상한은 선택된 axis에서 hard gate와 robust INDEX clearance를 함께 재검사한
certified 값이다. INDEX의 2.3 mm를 자동 복사하지 않았다.

`seat/reach corridor = 3.0 + front lip`은 surface cap datum과 switch front datum 사이의 필요한
유효 stem reach다. **실제 moving stem travel/actuation stroke는 body-height envelope에서 역산할 수
없다.** stem 형상, free height, pre-travel, over-travel, terminal 위치가 없는 상태에서 숫자를 만들면
허위 정밀도가 된다. 따라서 cap 8 mm 외형과 접촉 중심은 유지됐지만, 실제 travel은 SKU 검증 항목으로
남는다.

H=4.3의 geometry-only upper lip 4.0 mm처럼 큰 값은 stem reach 7.0 mm를 요구한다. 이는 collision
PASS일 뿐 제품 적합성 PASS가 아니다. 실제 설계에서는 각 행의 lower lip 부근을 우선해야 한다.

## 9. Hardware fallback 판정

판정은 **A-family**다.

- 6×6×6 유지 가능
- robust 0.50/0.80/1.00 mm branch 모두 H=6에서 존재
- low-profile H≤3.5가 주는 추가 row-norm 이득은 0.586 mm뿐
- footprint 변경 필요 없음

다만 요청문 A의 “OPTION C가 가장 합리적”이라는 문자 그대로의 후반부는 이번 재최적화로
supersede된다. OPTION C는 geometry fallback reference로 보존하되, 새 H=6 robust branch가 더 작은
row 이동을 제공한다.

**Low-profile 전용 SKU 검색은 현재 필요하지 않다.** 그러나 CAD WRITE 전에는 어느 높이를 쓰든
실제 SKU의 stem reach/travel, terminal keep-out, mounting/retention, force curve를 검증해야 한다.
이는 low-profile 선택을 위한 검색이 아니라 실제 하드웨어 정의를 위한 검증이다.

## 10. Final decision

Geometry envelope만 보면 6×6×6 유지가 가능하고 OPTION C보다 ergonomic displacement가 작다.
그럼에도 이번 단계는 CAD WRITE 승인 단계가 아니다.

HOLD 사유:

1. 사용자가 MIDDLE CAD WRITE = HOLD를 명시했다.
2. 실제 stem/terminal/SKU geometry가 source of truth에 없다.
3. H=6 branch의 최대 axis deviation 26.891°와 M2 displacement 9.992 mm는 ergonomic approval이
   필요하다.
4. 계산은 동결 tessellation 기반 envelope feasibility이며 새 CAD B-rep를 생성·재생성하지 않았다.

따라서:

- **MIDDLE LOW-PROFILE FEASIBILITY = COMPLETE**
- **MIDDLE CAD WRITE = HOLD**
- **INDEX_FINAL_VALIDATED = UNCHANGED / FROZEN**

## A–N 최종 보고

### A. 6.0 mm 결과

Δ=(+1.250,+3.750,−5.500), norm 6.773, max individual 9.992, INDEX 0.580 mm. 모든 hard gate PASS.

### B. 5.0 mm 결과

같은 center/axis, norm 6.773, INDEX 0.580 mm. holder rear 11.458 mm.

### C. 4.3 mm 결과

같은 center/axis, norm 6.773, INDEX 0.580 mm. holder rear 10.758 mm.

### D. 3.5 mm 결과

Δ=(+1.500,+3.125,−5.125), norm 6.187, max individual 9.849, INDEX 0.532 mm. 모든 hard gate PASS.

### E. 3.1 mm 결과

같은 low-profile center/axis, norm 6.187, INDEX 0.607 mm. holder rear 9.532 mm.

### F. clearance 0.50 확보 가능 최대 H

Candidate sweep에서는 Hmax≥6.00 mm. 선택 고정 branch의 certified ceiling은 **H≤6.10 mm**다.

### G. clearance 0.80 확보 가능 최대 H

Candidate sweep에서는 Hmax≥6.00 mm. 선택 고정 branch의 certified ceiling은 **H≤6.20 mm**다.

### H. clearance 1.00 확보 가능 최대 H

Candidate sweep에서는 Hmax≥6.00 mm. 선택 고정 branch의 certified ceiling은 **H≤6.30 mm**다.

### I. 각 높이의 row displacement

6.0/5.0/4.3 mm는 6.773 mm, 3.5/3.1 mm는 6.187 mm다.

### J. OPTION C 대비 ergonomic improvement

Row norm 30.601% 또는 36.604% 감소, M2 displacement 3.391 또는 3.534 mm 감소다.

### K. 추천 hardware envelope

6.0×6.0 footprint, body H≤6.0 mm, 6.4×6.4 pocket, holder rear 공식
`3.0 + L + H + 1.2`, H=6에서 L=2.258…2.400 mm를 우선한다.

### L. 실제 low-profile SKU 검색 필요 여부

**불필요.** 단 실제 switch SKU/stem/terminal 검증은 CAD WRITE 전에 필요하다.

### M. 6×6×6 유지 / hardware fallback 판정

**A-family: 6×6×6 유지.** OPTION C는 reference로 보존하지만 새 robust H=6 branch가 우선이다.

### N. MIDDLE CAD WRITE GO/HOLD

**MIDDLE CAD WRITE = HOLD**
