# 56 — Option C local exact prototype

형님 승인 범위에 따라 **Option C 한 개**만 local exact B-rep으로 구현·검증했습니다. 이 결과는 analysis prototype이며 production geometry에는 반영하지 않았습니다.

## 범위와 메모리 준수

- full JaD/JfD load: **0**
- full shell boolean/export: **0**
- full assembly export: **0**
- multiprocessing / concurrent OCC: **0 / 0**
- exact prototype: **1개**
- 사용 형상: HW504 A/B, N1/N2 ITS-1105, N1/N2 shared carrier, 기존 N2 local shell crop 2개
- peak recorded RSS: **484.7 MB** / stop limit 1100 MB
- visual QA: **2880×1920 supersampling → 1440×960**, render safety ceiling **24 GB**, observed render peak **463.5 MB**

## 필수 보고

- `HW504_A` = **NONFUNCTIONAL TRIM**
- `HW504_A_REMOVED_VOLUME` = **39.877975 mm³**
- `HW504_A_PROTECTED_VOLUME_REMOVED` = **0.000000000 mm³**
- `HW504_B` = **EXACT KEEP**
- `HW504_B_GEOMETRY_CHANGE` = **0**
- `N1 MODIFICATION` = **없음** — center/axis/ITS-1105 envelope 유지
- `N2 MODIFICATION` = **actuator axis 0.000°, switch roll -5.000°, distal service two-segment one-time bend**
- `N1/N2 CARRIER MODIFICATION` = 기존 충돌 bbox에 1.00 mm local relief, 기존 1.60 mm wall 유지, 3.20 mm lower broad-side bridge 추가
- `MINIMUM CLEARANCES`:
  - HW504 A ↔ carrier: **0.000000 mm**
  - HW504 B ↔ carrier: **2.350848 mm**
  - N1 ↔ N2: **2.391916 mm**
  - HW504 ↔ terminal/service: **0.000000 mm**
  - carrier ↔ local shell: **1.113872 mm**
  - N2 cap/opening diametral: **0.800000 mm** (frozen source result 재사용)
  - critical nominal wall: **1.60 mm**
- `ORIGINAL THUMB RETAINED` = **19 / 20**
- `THUMB REUSE RATIO` = **95.0%**
- `JOYSTICK KINEMATICS` = **UNCHANGED**
- `FINGER EXTERIOR` = **PRESERVED** — I2/I3/I4/M3/M4/N1/N2/N3 center 모두 0.000 mm
- `EXTERIOR SHELL` = **UNCHANGED** — geometry write 0

## Exact local gate

| Gate | Result |
|---|---:|
| all unintended penetration = 0 | HOLD |
| HW504 hard geometry ↔ carrier ≥ 0.80 mm | HOLD |
| terminal/service ≥ 0.80 mm | HOLD |
| switch-switch ≥ 1.20 mm | PASS |
| critical wall ≥ 1.20 mm | PASS |
| N2 seam diametral clearance ≥ 0.80 mm | PASS |
| HW504 A protected removal = 0 | PASS |

세부 pair별 penetration, AABB gate, exact closest point와 distance는 lightweight JSON에 기록했습니다.

## HOLD 원인

이번 단일 형상은 다음 exact 잔여 간섭 때문에 승인할 수 없습니다.

- HW504 A ↔ N2 body: **0.015189 mm³**
- HW504 A ↔ N2 terminal root 1/2: **0.031266 / 0.115074 mm³**
- HW504 B ↔ N2 terminal root 2: **0.401337 mm³**
- HW504 A ↔ redesigned carrier: **0.005690 mm³**
- HW504 ↔ terminal/service envelope 합계: **59.262475 mm³**

반면 HW504 B ↔ carrier **2.350848 mm**, N1 ↔ N2 **2.391916 mm**, carrier ↔ local shell **1.113872 mm**는 통과했습니다. N2 roll은 허용 절대 한계인 **-5.000°**까지 사용했지만 rigid terminal root 간섭을 제거하지 못했습니다. 따라서 동일 형상에 대한 추가 임의 trim이나 반복 search는 수행하지 않았습니다.

## Final verdict

- `OPTION C LOCAL GEOMETRY` = **HOLD**
- `HW504 A MINIMAL TRIM` = **PASS**
- `HW504 B EXACT REUSE` = **PASS**
- `N1/N2 INTERNAL FIT` = **HOLD**
- `JOYSTICK KINEMATICS` = **PASS**
- `ORIGINAL THUMB REUSE >=95%` = **PASS**
- `EXTERIOR CHANGE` = **0**

## 산출물

- local exact STEP: `build123d_workbench\out\option_c_local_exact_prototype\OPTION_C_LOCAL_EXACT_PROTOTYPE.step`
- lightweight JSON: `build123d_workbench\out\option_c_local_exact_prototype\option_c_local_exact_prototype.json`
- review renders: `renders\option_c_local_exact_prototype/01...08_*.png`

## STOP

이 prototype은 production CAD에 적용하지 않았습니다. **PASS 여부와 무관하게 여기서 STOP**하며, full shell 계산으로 넘어가지 않습니다.
