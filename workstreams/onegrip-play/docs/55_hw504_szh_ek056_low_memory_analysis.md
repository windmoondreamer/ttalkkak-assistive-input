# OneGrip Play — HW504 / SZH-EK056 low-memory local analysis

Date: 2026-08-23  
Mode: **LOW-MEMORY / LOCAL ANALYSIS ONLY / production geometry write 0**

## 1. Executive answer

```text
HW504 ↔ SZH-EK056 = LIKELY COMPATIBLE

Candidate A shell-only = FAIL (existing result)

Smallest functional change = Option C MIXED
  HW504 A non-protected local trim: 39.883946 mm³
  Finger protected-region relocation: 33.018146 mm³
  HW504 B: KEEP exact
  Thumb kinematic datum change: 0 intended
```

`SAME`이 아니라 `LIKELY COMPATIBLE`인 이유는 SZH-EK056 판매처가 대표사진만 제공하고
제조 시점별 hardware revision 변경 가능성을 명시하며, workspace에도 실물 측정 registry가 없기
때문이다. 구매품 실측 전에는 PCB·홀·shaft datum을 production CAD datum으로 확정하면 안 된다.

## 2. RAM and scope compliance

- full JaD/JfD shell boolean: `0`
- full shell STEP export: `0`
- complete assembly export: `0`
- new OCCT boolean: `0`
- multiprocessing: `0`
- STEP load/tessellation during this analysis: `0`
- production geometry modification: `0`
- render: `960 × 640`, 세 장을 순차 생성 후 즉시 release

기존 `original_thumb_module_reuse_audit.json`과
`hw504_minimal_change_candidates.json`의 collision/datum 결과만 read-only로 사용했다.

## 3. Hardware identity check

### 3.1 Source CAD HW504

원본 CAD의 `HW504_B`는 하나의 joystick module을 이루는 두 solid다.

| Solid | Inferred role | Source-local bbox | Exact volume |
|---|---|---:|---:|
| JFH / HW504 A | fixed PCB/body/potentiometer/support | `27.0 × 14.25 × 38.9 mm` | `1461.114276 mm³` |
| JFD / HW504 B | moving gimbal/stick body | `17.0 × 19.0 × 13.0 mm` | `767.120862 mm³` |

Observed topology:

- rectangular breakout board/support plate
- four approximately `Ø3.2 mm` mounting holes
- two orthogonal potentiometer housings
- central stick shaft and axial push-switch structure
- intersecting orthogonal pivot journals
- five-pin edge-header layout in the source visual reference

### 3.2 SZH-EK056 comparison

The [SZH-EK056 product listing](https://www.icbanq.com/P008113513) gives
`34.5 × 26 × 38 mm`, 11 g, a standard PS2 joystick structure and a representative product
image. The image has the same four-hole board, five-pin header, two orthogonal potentiometers,
central shaft and push switch as the source CAD.

A controlled drawing is not supplied for that SKU. A mechanically comparable dual-axis module
document specifies a `34.0 × 26.3 × 1.6 mm` PCB, `39.4 × 27.5 × 32.9 mm` enclosing envelope,
four `Ø3 mm` mounting holes, two 10 kΩ potentiometers, an axial push switch and ±33° travel:
[Dual Axis Analogue Joystick Module PDF](https://www.auselectronicsdirect.com.au/assets/brochures/TA0051.pdf).

The [DeviceMart SZH-EK056 page](https://www.devicemart.co.kr/goods/view?no=1287087)
explicitly warns that the photograph is representative and that hardware revisions can change.

### 3.3 Verdict

| Check | Result |
|---|---|
| overall family/envelope | match within listing/document variation |
| PCB topology | visual match |
| mounting holes | 4 holes, nominal `Ø3.0` vs CAD approximately `Ø3.2` |
| X/Y potentiometer layout | match |
| center shaft / push switch | match |
| exact hole centers and shaft height | **UNKNOWN until physical measurement** |
| final verdict | **LIKELY COMPATIBLE** |

필수 실측은 PCB L/W/T, 네 hole center/diameter, neutral shaft center/height, pot/switch maximum
envelope, X/Y travel, axial push travel이다.

## 4. Existing collision constraint

Candidate A는 기존 exact 결과에서 이미 실패했다. HW504 전체와 frozen N1/N2의 Finger 침투는
`72.902092 mm³`다.

| Region | Non-protected | Protected | Total |
|---|---:|---:|---:|
| HW504 A ↔ Finger | `39.883946` | `6.328468` | `46.212414 mm³` |
| HW504 B ↔ Finger | `0.000000` | `26.689679` | `26.689679 mm³` |
| **Total** | **39.883946** | **33.018146** | **72.902092 mm³** |

HW504 B의 N2 switch `0.320370 mm³`와 shared carrier `26.369309 mm³`는 **100% protected
region 내부**다. 따라서 HW504 B local trim은 original pivot/contact/kinematic geometry를 건드린다.

## 5. Option comparison

### Option A — Finger-side minimal modification

- 바뀌는 부품: N1/N2 internal switch envelopes, N1/N2 shared carrier
- 최소 이론 changed region: `72.902092 mm³`
- original Thumb reuse: local 비교 기준 `20/20 exact`
- Finger 영향: 큰 local repackaging; external centers/axes는 동결
- Thumb kinematics 영향: `0 intended`
- 추천: **FALLBACK**

Thumb는 전부 유지하지만 충돌 부담 전부를 Finger에 넘기므로 Finger-side 변경량이 가장 크다.

### Option B — HW504-side minimal modification

- 바뀌는 부품: HW504 A, HW504 B
- 최소 이론 changed region: `72.902092 mm³`
- protected material at risk: `33.018146 mm³`
- original Thumb reuse: `18/20 exact`
- Finger 영향: `0`
- Thumb kinematics 영향: **NONZERO / high risk**
- 추천: **REJECT**

HW504 B 충돌이 전부 protected region이므로 frozen kinematics 조건과 양립하지 않는다.

### Option C — mixed minimal modification

- 바뀌는 부품:
  - HW504 A의 nonfunctional/support bulk만 `39.883946 mm³` trim 대상
  - N2 internal switch envelope와 N1/N2 shared carrier의 protected-side `33.018146 mm³` 재배치 대상
- HW504 B: **exact KEEP**
- original Thumb exact reuse: `19/20 = 95.0%`
- protected Thumb datum reuse: `100%`
- Finger 영향: N2 packaging/shared carrier의 localized internal change; exterior center/axis `0`
- Thumb kinematics 영향: `0 intended`
- 추천: **YES — next local exact test**

각 collision 영역을 기능적으로 덜 민감한 쪽에 배분하므로 C가 가장 작은 기능 변경이다.

## 6. Outputs

- `build123d_workbench/out/hw504_low_memory_analysis/hw504_low_memory_analysis.json`
- `renders/hw504_low_memory_analysis/01_collision_section.png`
- `renders/hw504_low_memory_analysis/02_hw504_b_n1_n2_closeup.png`
- `renders/hw504_low_memory_analysis/03_option_abc_comparison.png`

새 STEP는 생성하지 않았다.

## 7. STOP gate

```text
RECOMMENDED NEXT TEST = OPTION C, ONE LOCAL CROP ONLY
LOCAL EXACT BOOLEAN RUN = NOT EXECUTED
PRODUCTION GEOMETRY MODIFICATION = 0
STOP — await user approval and physical SZH-EK056 measurements
```
