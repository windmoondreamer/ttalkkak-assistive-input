# 33. ITS-1105-6mm physical-sample design re-audit

- 일자: 2026-08-20
- 대상: 사용자 보유 **ITS-1105-6mm 실물 샘플**
- frozen CAD: `INDEX_FINAL_VALIDATED` / `03ede76e83b5c865d9a69c35`
- configuration: `default` frozen local mesh cache
- 실행: **LOCAL READ-ONLY / Onshape CAD WRITE 0 / registry WRITE 0**
- 최종: **INDEX GRADE 1 / CASE B 유지 / cardinal channel seed 확정 / CAD WRITE HOLD**

이 문서는 `docs/32_its1105_primary_switch_design_audit.md`의 physical-lot pending 항목 중 body와
actuator stack을 실측값으로 대체한다. `docs/32`의 비-cardinal terminal-roll seed는 실제 body가 6.4 mm
정사각 pocket 안에서 함께 회전해야 한다는 제약을 포함하지 않았으므로, 이번 결과가 그 seed를 대체한다.

## 1. 입력된 physical sample source of truth

| 항목 | 실측값 |
|---|---:|
| body X | 6.12 mm |
| body Y | 6.05 mm |
| housing height | 3.56 mm |
| total height | 6.00 mm |
| actuator diameter | 3.35 mm |
| actuator projection | 2.44 mm |
| travel | 0.25 ±0.10 mm (drawing) |
| terminals | 양쪽 2개씩 / 총 4-pin THT |

`TOTAL_H - HOUSING_H = 6.00 - 3.56 = 2.44 mm`로 actuator projection 실측과 정확히 일치한다.

Terminal policy도 다음처럼 고정한다.

- body 바로 옆 factory fixed root: **rigid / bending 금지**
- 그 이후 distal pin: **조립 전 1회 성형 허용**
- direct wiring / pre-solder: **허용**
- 네 terminal의 exact position/profile/section은 이번 입력에 없으므로, channel 계산에서는 계속 drawing
  nominal `4.5 pitch / 7.9 outer width / 0.3×0.7 metal / 1.8 fixed-root depth`를 사용한다.

## 2. 6.4 pocket 실측 body fit

축정렬 상태의 측당 기하 여유:

| 방향 | 계산 | side clearance |
|---|---:|---:|
| X | `(6.40 - 6.12) / 2` | **0.140 mm** |
| Y | `(6.40 - 6.05) / 2` | **0.175 mm** |

actuator는 Ø3.35 mm, 기존 bore는 Ø4.50 mm이므로 radial clearance는
`(4.50 - 3.35) / 2 = 0.575 mm`이고 coaxial geometry는 PASS다.

### 2.1 body rotation constraint

6.12×6.05 body를 6.4×6.4 pocket에서 회전시키면 projected width가 증가한다. 1° grid에서 exact
intersection 없이 들어가는 0…179° roll은 다음뿐이다.

```text
0, 1, 2, 88, 89, 90, 91, 92, 178, 179°
```

180° 대칭을 포함하면 0…359°에서 20개다. 따라서 `docs/32`의 I1 170°와 I4 80°는 terminal만 보면
가능하지만 **실측 body + 6.4 pocket 조합에서는 사용할 수 없다.**

## 3. INDEX cardinal-roll joint solution

실물 조립 및 FDM pocket 여유를 우선해 0°/90° cardinal 방향만 허용하고 다음 gate를 동시에 계산했다.

1. pocket exact fit
2. body-to-body SAT ≥1.20 mm
3. fixed root가 다른 switch body, RWID, RZKD, screw를 침범하지 않음
4. split/external/channel web ≥1.50 mm
5. fixed root는 rigid 상태로 channel 안에 완전히 수용

유일한 0…179° cardinal PASS 조합은 다음이다.

| button | selected roll | 180° symmetric equivalent |
|---|---:|---:|
| I1 | **0°** | 180° |
| I2 | **0°** | 180° |
| I3 | **90°** | 270° |
| I4 | **90°** | 270° |

### 3.1 body SAT

| pair | separation |
|---|---:|
| I1-I2 | 1.332843 mm |
| I2-I3 | **1.237899 mm** |
| I1-I3 | 6.620760 mm |
| I3-I4 | 4.112661 mm |

minimum `1.237899 mm ≥ 1.20 mm`로 PASS다. 여유는 0.037899 mm로 크지 않으므로 center/axis를
CAD WRITE 중 임의 이동하지 않는다.

BODY_X/BODY_Y가 terminal drawing 축과 반대로 매핑된 경우도 별도로 계산했다. 동일 roll 조합이
PASS하며 minimum body SAT는 `1.226755 mm`, governing channel web은 `1.646526 mm`다. 따라서 X/Y
축 라벨 해석을 바꿔도 결론은 유지된다.

### 3.2 fixed-root/channel web

| gate | result |
|---|---:|
| I1 individual root margin | 2.257462 mm |
| I2 individual root margin | 2.257462 mm |
| I3 individual root margin | 2.153866 mm |
| I4 individual root margin | 2.257462 mm |
| I1-I2 channel web | **1.636953 mm** |
| I2-I3 channel web | 2.040068 mm |
| I3-I4 channel web | 5.364730 mm |
| governing web | **1.636953 mm PASS** |
| symmetric channel clearance while preserving 1.50 web | **0.068477 mm/channel** |

실측 housing rear는 INDEX axis depth `5.30 + 3.56 = 8.86 mm`다. 따라서 fixed-root channel은
`8.86…12.50 mm`의 open-rear 경로로 계획한다.

정확-fit 각도를 모두 허용하면 `179° / 178° / 88° / 88°`에서 governing web `1.789898 mm`를 얻지만,
최소 pocket side clearance가 `0.036293 mm`뿐이다. 출력 오차와 탈착성을 고려한 coupon 검증 전에는
이 해를 선택하지 않고, side clearance 0.140 mm를 유지하는 cardinal 해를 우선한다.

## 4. rear retention 실측 확정

| 항목 | 값 |
|---|---:|
| measured body rear | 8.86 mm |
| current RWID/RZKD pad front | 11.15 mm |
| spacer 없는 gap | 2.29 mm |
| separate spacer seed | **2.44 mm** |
| body rear + spacer | 11.30 mm |
| current pad에 대한 preload | **0.15 mm** |

따라서 `docs/32`의 2.40 mm nominal shim을 **2.44 mm physical-sample seed**로 갱신한다. spacer는
retainer와 함께 이동하지 않는 별도 중앙 service part로 유지한다. RWID/RZKD pad extension은 기존
service travel을 악화시키므로 계속 제외한다.

## 5. cap / actuator stack

actuator free top은 INDEX axis depth `5.30 - 2.44 = 2.86 mm`다. 현 cap underside와의 normal-direction
free gap은 다음과 같다.

| button | measured free gap | 0.05 mm free-clearance용 boss | max travel용 local stop recess |
|---|---:|---:|---:|
| I1 | 0.132009 | 0.082009 | 0.184337 |
| I2 | 0.132009 | 0.082009 | 0.184337 |
| I3 | 0.132008 | 0.082008 | 0.184337 |
| I4 | 0.256925 | 0.206925 | 0.199624 |

마지막 두 열은 prototype free clearance를 **0.05 mm**로 둔 계산 seed다. 0.15 mm minimum travel 시
필요 cap displacement는 I1-I3 `0.193287 mm`, I4 `0.199839 mm`로 현재 0.20 mm stop 안에 수치상
들어간다. 그러나 거의 경계이므로 production freeze가 아니라 cap coupon/조립 시험용 parameter다.

## 6. recommended terminal and wiring sequence

1. continuity test로 `1-2 common / 3-4 common`을 실물 확인
2. selected cardinal roll에 맞춘 jig에서 fixed root 뒤 distal pin만 1회 pre-form
3. 서로 다른 common group에서 한 핀씩 골라 wire pre-solder
4. solder joint와 unused terminal을 각각 절연
5. wire부터 open-rear channel에 통과
6. switch body를 6.4 seat에 축정렬 삽입
7. 2.44 mm rear spacer 삽입
8. RWID/RZKD 체결
9. 0.15/0.25/0.35 mm stroke와 electrical actuation 확인

`1+2` 또는 `3+4`는 switching pair가 아니므로 direct-wiring pair로 사용하지 않는다.

## 7. MIDDLE same-SKU recheck

MIDDLE `h3p1_w1` seed에 measured height 3.56 mm와 orientation-independent conservative 6.12 mm square
footprint를 적용했다.

| gate | 기존 nominal front lip 고정 | measured-body front lip 조정 |
|---|---:|---:|
| front lip parameter | 2.231617 | **2.263597** |
| actual minimum front lip | 0.470947 FAIL | **0.500000 PASS** |
| minimum body SAT | 1.364640 PASS | **1.369703 PASS** |
| minimum divider | 1.034066 PASS | **1.039129 PASS** |
| minimum split wall | 1.513915 PASS | **1.524163 PASS** |
| frozen INDEX clearance | 0.520601 | **0.514580 PASS** |
| collision count | 0 | **0** |
| robust 0.50 gate | FAIL | **PASS** |

필요 front-lip 증가는 **0.031981 mm**다. MIDDLE은 아직 CAD가 없으므로 이 값은 신규 holder parameter에
처음부터 반영할 수 있다. 결론은 **ITS-1105-6mm same SKU conditional GO**다.

## 8. 남은 measurement / prototype gate

이번 입력으로 body와 actuator stack uncertainty는 해소됐지만 다음은 아직 남아 있다.

- fixed-root 실제 시작점, profile, maximum envelope
- pin spacing / width / thickness 실측
- 단일 샘플이 아닌 여러 샘플의 min/max
- 6.4/6.5/6.6/6.7 pocket coupon
- `0/0/90/90°` terminal-channel coupon
- wire gauge, insulation OD, solder-fillet envelope
- 사용자의 명시적 CAD WRITE 승인

Registry에는 이번 작업에서 쓰지 않았다. 다음 반영 시 status는 `PHYSICAL SAMPLE MEASURED / ROOT AND
COUPON PENDING`이 정확하다.

## 9. final decision

- physical body/actuator measurement: **ACCEPTED**
- INDEX pocket/body geometry: **PASS, cardinal roll required**
- INDEX modification grade: **GRADE 1 / CASE B 유지**
- selected terminal rolls: **I1 0° / I2 0° / I3 90° / I4 90°**
- rear spacer seed: **2.44 mm**
- MIDDLE same SKU: **CONDITIONAL GO**
- Onshape CAD WRITE: **HOLD**
- registry WRITE: **HOLD**

HOLD는 geometry failure가 아니라 root/pin 실측, coupon, wiring envelope 및 명시적 write 승인 미완료 때문이다.
`INDEX_FINAL_VALIDATED` geometry는 계속 freeze한다.

## 재현 파일

- `cad_dump/its1105_physical_sample_reaudit.json`
- `scripts/audit_its1105_physical_sample.py`

모든 결과는 frozen local meshes와 analytic OBB/SAT를 사용했으며 CAD mutation path는 없다.
