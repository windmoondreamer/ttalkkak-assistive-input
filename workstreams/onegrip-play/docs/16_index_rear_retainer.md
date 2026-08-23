# INDEX 후면 retainer — 설계 확정 및 게이트 대기

- 일자 2026-08-19
- 승인 근거: `docs/15_index_f2_final_clearance_fix.md` 승인
- 체크포인트 버전: **`INDEX_holder_final`** (`6f0e56b8f7504503dc2db465`)
- **이번 실행의 CAD 형상 변경: 0건.** 버전 생성 1회 외에 수정 없음
- **판정: §1 regeneration 게이트가 아직 열리지 않아 retainer CAD 구현을 착수하지 않았다.
  설계는 실측 기반으로 전부 확정했다.**

---

## A. regeneration 직접 확인 — 보류 (게이트 미개방)

| 시도 | 결과 |
|---|---|
| `GET /partstudios/d/{did}/w/{wid}/e/{eid}/features` | **429**, Retry-After 5,717 s |
| 버전 생성 후 `GET .../d/{did}/v/{vid}/e/{eid}/features` | **429**, Retry-After 5,680 s (같은 버킷) |
| 백그라운드 폴러 (`scripts/poll_features.py`, 240 s 간격) | 진행 중. 22:09 기준 Retry-After 4,921 s |

Retry-After 가 경과 시간만큼 정확히 줄어드는 고정 윈도우다. **해제 예정 약 23:31.**
폴러가 해제 즉시 `featureStates` 를 `cad_dump/features_final.json` 에 저장한다.

§1 은 "ERROR 가 하나라도 있으면 retainer 를 만들지 말고 즉시 HOLD" 이므로,
**확인 전에 retainer 형상을 만들지 않았다.**

> 참고 (docs/15 §K 의 간접 확인): blank 4 / 시트 4 (전부 6.4x6.4 정확) /
> front trim 4 (외피 돌출 0.00) / split clip 4 / union 4 / RETAINER no-op 4 /
> body 18개 / assembly 25-25 — 모든 stage 산출물이 정상이다. 형상 결함은 없다.

## B. stale front_lip 정리 — 보류 (같은 게이트)

| | 값 | 상태 |
|---|---|---|
| FS 상수 `LIP_F2` | **2.3 mm** | **형상의 source of truth** |
| 트리 변수 `#finger_switch_front_lip` | 0.8 mm | 사문. 어디에서도 읽히지 않음 |

변수 피처 수정에는 featureId 가 필요하고 그러려면 `/features` GET 이 필요하다.
§2 의 허용 범위("리팩터링 위험이 크다면 값만 기록")에 따라 **구조를 건드리지 않았다.**
FS 상단 TECHNICAL DEBT / TODO 블록에 명시되어 있다.

---

## C. retainer 방식 선택 — OPTION A (제거 가능한 plate + 나사 2개)

| 기준 | **A. 나사 2개 removable plate** | B. 슬라이드-in + 나사 1개 lock |
|---|---|---|
| 기하 성립성 | **성립.** pad 관통이 1.2 mm 뿐이라 축방향으로 얹기만 하면 된다 | **곤란.** 세 bore 축이 42.6/53.5/56.1도 벌어져 **공통 슬라이드 방향이 없다** |
| P1S FDM | cap 2.0 mm, ear ⌀6.0, 나사 ⌀1.7 — 전부 0.4 노즐 여유 | 슬롯 공차 관리가 어렵고 레일이 얇아짐 |
| 조립성 | 쉘 열린 상태에서 얹고 나사 2개 | 슬라이드 경로에 홀더 3개가 걸림 |
| 교체성 | 나사 2개 풀면 스위치 개별 교체 | 슬라이드 해제 공간이 부족 |
| 내구성 | 2점 지지로 회전까지 구속 | 1점 나사 + 슬롯, 유격 누적 |
| 내부 공간 | 기존 공동 안에서 해결 | 슬라이드 여유분만큼 추가 공간 필요 |

**→ OPTION A 채택.** snap-fit 단독 고정은 사용하지 않는다 (§6).

**B 가 탈락하는 결정적 이유:** 세 bore 축의 사잇각이 42.59 / 53.45 / 56.09도 이므로
세 pad 를 동시에 넣었다 뺐다 할 수 있는 단일 직선 경로가 존재하지 않는다.
축방향으로 "얹는" 동작만 가능하고, 이는 곧 나사 체결식이다.

---

## D. I1/I2/I3 shared plate geometry

```
backbone = cap 3개의 융합체 (별도 bridge 불필요)
  cap_i : 11.0 x 11.0 x 2.0 mm,  홀더 뒷면(축깊이 12.5)에 각 축에 수직으로 얹힘
```

cap 상호 겹침 (SAT 실측) — **하나의 rigid body 로 융합된다**:

| 쌍 | 겹침 |
|---|---|
| I1-I2 | **2.19 mm** |
| I2-I3 | **0.28 mm** |
| I1-I3 | **1.75 mm** |

> 평평한 backbone 판은 **채택 불가**임을 먼저 확인했다.
> 세 홀더를 전부 뒤로 비켜 가는 최적 평면을 풀면 pad 높이가
> **5.98 / 8.51 / 8.50 mm** 필요해진다. bore 관통이 1.2 mm 뿐인 구조에
> 8.5 mm pad 를 21~38도 로 밀어 넣을 수 없다.
> 그래서 평면 backbone 을 버리고 **홀더 뒷면에 얹히는 faceted cap 융합체**로 갔다.

홀더 뒷면 중심 (backbone 이 앉는 자리):

| | 좌표 (x, y, z) | 면 법선 = 스위치 축 |
|---|---|---|
| I1 | (−11.59, −11.24, +11.00) | (−0.851, −0.500, −0.160) |
| I2 | (−11.05, −19.07, +18.00) | (−0.394, −0.571, −0.720) |
| I3 | (−4.62, −16.86, +8.97) | (−0.070, −0.998, +0.002) |

중심 간 거리: I1-I2 10.51 / I2-I3 11.30 / I1-I3 9.17 mm.

## E. pad angles / heights

각 pad 는 **독립 각도·높이·접촉면**을 갖는다 (§4 요구).

| | pad 면 법선 (= 스위치 축, 완전 정렬) | 인접 cap 과의 사잇각 | pad 돌출 |
|---|---|---|---|
| PAD_I1 | (−0.851, −0.500, −0.160) | I2 와 42.59도 | 1.2 + preload |
| PAD_I2 | (−0.394, −0.571, −0.720) | I3 와 53.45도 | 1.2 + preload |
| PAD_I3 | (−0.070, −0.998, +0.002) | I1 과 56.09도 | 1.2 + preload |

- **pad 면 법선 = 해당 스위치 축과 정확히 일치(0도)** → 스위치 뒷면을 직각으로 누른다
- pad 돌출 = 홀더 뒷면(12.5) − 스위치 뒷면(11.3) = **1.2 mm** + preload
- pad 단면 **3.6 x 3.6 mm** (6.4 bore 안에서 사방 1.4 mm 링을 핀·배선용으로 남김)
  → 중앙 1점 가압이므로 스위치가 기울지 않는다

## F. preload — 파라미터화

```
#finger_retainer_preload   초기 nominal 0.15 mm   (검토 범위 0.10 ~ 0.20)
pad 돌출 = (blankTo − swRear) + preload = 1.2 + 0.15 = 1.35 mm
```

목적은 rattling·축방향 유격 제거이며 스위치 압축이 아니다.
실제 SKU 공차 확정 전까지 **provisional** 로 둔다 (§5, §9).
6x6x6 nominal solid 기준이며 imported `PushBtn.SLDPRT` 는 인터페이스 기준으로 쓰지 않는다.

## G. fastening

나사 2개. **기존 `Screw_holes` / 원본 쉘 나사 보스는 건드리지 않는다** (§7).
신규 ear 는 홀더 외벽에 붙는 **신규 downstream feature** 로만 추가한다.

| | 위치 | 나사축 | 포켓 최소거리 | 나사 B 거리 |
|---|---|---|---|---|
| **EAR_A** | I1 축에서 **−u 8.0 mm**, 중심 (−18.19, −5.85, +10.52) | I1 축 | **4.80 mm** | **16.91 mm** |
| **EAR_B** | I3 축에서 **−v 8.0 mm**, 중심 (−4.83, −19.87, +0.98) | I3 축 | **4.80 mm** | **19.25 mm** |

- 두 위치 모두 홀더 외벽에 **접해 있고**(표본 중 기존 재료 22 % / 45 %) 나머지는 새로 채운다
  → 공중에 뜨지 않고, 완전히 파묻히지도 않는다
- ear ⌀6.0, pilot ⌀1.7 (M2 셀프탭 기준), 결합 깊이 6 mm
- 두 ear 가 행의 양 끝(I1 바깥 / I3 아래)에 있어 **회전까지 구속**된다
- 간섭 금지 대상 전부 회피 확인: 기존 나사 B(16.9 / 19.3 mm), 스위치 포켓(4.80 mm),
  쉘 mating surface(둘 다 X<0 유지), 엄지 구조(Z 축으로 20 mm 이상 이격)

> **홀더 사이 골에 나사를 박는 안은 폐기했다.** 재료는 13~14 mm 로 충분하지만,
> 골 중심이 곧 포켓 칸막이(0.80 mm)여서 나사가 포켓을 관통한다.
> 전 격자 탐색에서 I2-I3 골은 **성립 위치가 하나도 없었고**, I1-I2 골은
> (u −3, v +6) 한 곳만 1.50 mm 여유로 겨우 성립했다.

## H. I4 retainer — 단독 소형 plate

I4 홀더 뒷면 (+5.19, −17.22, +12.12), 축 (+0.024, −0.968, −0.250).
I1/I2/I3 plate 와 **억지로 연결하지 않는다** (그 평면에서 7.35 mm 떨어져 있고 반대쪽 쉘이다).

```
cap 11.0 x 11.0 x 2.0   (I4 홀더 뒷면, 축 수직)
pad 3.6 x 3.6, 돌출 1.2 + preload
ear 1개 : I4 축에서 -v 8.0 mm, 중심 (+5.22, -18.13, +3.63)
          X = +5.22 > 0  -> JaD 쪽 유지 (3+1 ownership 보존)
          포켓 거리 4.80 mm, 나사 B 16.29 mm
```

같은 설계 철학 유지: 내부 삽입 → front lip → 후면 축방향 구속 → 교체 가능.
(대안 후보 `+u` 는 나사 B 9.97 mm, `+v` 는 5.13 mm 로 `−v` 가 가장 여유롭다.
`−u` 는 X = −2.73 으로 **분할면을 침범해 탈락**)

## I. wiring accessibility

홀더 뒷면에서 각 방향으로 재료를 만날 때까지의 거리 (실측, mm):

| | 축 방향(더 안쪽) | +u | −u | +v | −v |
|---|---|---|---|---|---|
| I1 | 35.9 | 6.5 | 16.9 | 9.8 | 22.9 |
| **I2** | **3.2** | 18.2 | 12.4 | 23.6 | 3.2 |
| I3 | 38.7 | 4.6 | 3.8 | 11.2 | 12.7 |
| I4 | 32.6 | 15.0 | 8.4 | >60 | 23.4 |

- pad 를 3.6 mm 로 줄여 6.4 bore 안에 **사방 1.4 mm 링**을 남긴다 → 핀 인출·납땜 공간
- **I2 만 축 방향 3.2 mm** 로 좁다(나사 B 보스). → **I2 배선은 ±u 방향(12~18 mm 여유)으로 뺀다**
- cap 에 **배선 슬롯**(2.5 x 1.5 mm)을 bore 에서 바깥으로 내어 굽힘반경을 확보한다
- 핀 배열은 SKU 미확정이므로 provisional. pad 를 중앙 소형으로 둔 것이 이에 대한 대비다

## J. printability (P1S / 0.4 mm nozzle)

- **최적 출력 방향을 계산했다**: 세 cap 법선을 감싸는 최소 원뿔의 축
  = **(−0.4734, −0.8350, −0.2805)**, 이때 세 cap 면 경사가 모두 **30.08도**
  → **45도 규칙 안. 서포트 불필요.**
  (한 cap 면을 그냥 베드에 놓으면 다른 면이 53~56도 가 되어 서포트가 필요하다)
- 벽 두께: cap 2.0 mm(5 lines), pad 3.6 x 3.6, ear ⌀6.0 / pilot ⌀1.7 — 전부 여유
- retainer 는 쉘과 **별도 출력 부품** (§14) → JaD/JfD 와 union 하지 않는다

## K. JaD / JfD — 변화 없음

이번 실행에서 형상을 수정하지 않았다. docs/15 상태 그대로:
`JaD` = Joystick_1 (1 body), `JfD` = Joystick_2 (1 body), split 0, duplicate 0.
retainer 는 **NEW PART** 로 만들 예정이며 쉘과 union 하지 않는다.

## L. assembly — 변화 없음

`Joystick` occurrences 25 / instances 25, dangling 참조 0 (docs/15 확인값 유지).

## M. INDEX FINAL SUCCESS / HOLD — **HOLD**

§15 의 13개 조건 대조:

| # | 조건 | 상태 |
|---|---|---|
| 1 | holder final PASS | **PASS** (docs/15) |
| 2 | regeneration ERROR 0 | **미확인 (게이트 429)** |
| 3 | 6x6x6 스위치 4개 실제 착좌 | **PASS** 4/4, 필요 깊이 = 설계 5.300 |
| 4 | SAT clearance >= 1.20 | **PASS** 1.3476 |
| 5 | pocket divider >= 0.80 | **PASS** 0.8000 |
| 6 | screw clearance >= 2.50 | **PASS** 2.990 (I4) |
| 7 | shared I1/I2/I3 retainer 장착 가능 | **설계 확정, 미제작** |
| 8 | I4 retainer 장착 가능 | **설계 확정, 미제작** |
| 9 | switch removal 가능 | 설계상 가능 (나사 2개 해제) |
| 10 | wiring access 가능 | **PASS** (I 항목) |
| 11 | JaD/JfD 유지 | **PASS** |
| 12 | assembly 25/25 | **PASS** |
| 13 | original thumb geometry 무변화 | **PASS** |

→ **2번(게이트) 미확인 + 7·8번 미제작 → INDEX FINAL SUCCESS 선언 보류.**

## N. MIDDLE — **HOLD**

§16 지시대로 이번 실행에서 MIDDLE 을 만들지 않았다.
INDEX FINAL SUCCESS 이후 다음 세션에서 시작한다.
적용 규칙은 docs/13 §13-K (free-axis minimax, 1-파라미터 보간 금지).

---

## 다음 실행 순서 (게이트 해제 후)

1. `featureStates` 확인 → ERROR 0 이면 INDEX holder FINAL PASS 확정
2. `#finger_switch_front_lip` 트리 변수를 2.3 으로 동기화, FS 를 `getVariable` 로 복귀,
   RETAINER no-op 스텁 4개 삭제, 피처 이름 정리
   — **동기화 후 축 / 시트 / 칸막이 / 나사 여유가 동일한지 반드시 재확인** (§2)
3. retainer 원자 구현 (§12 순서 그대로):
   **A** backbone NEW BODY → **B** PAD_I1 → **C** PAD_I2 → **D** PAD_I3 →
   **E** EAR_A·EAR_B (쉘에 union) → **F** 나사 구멍 → **G** 최종 검증
   각 단계: WRITE → state 확인 → tessellation → 다음
4. I4 단독 retainer 동일 절차
5. §13 검증 (뒷면 접촉 / preload / 스위치·홀더·나사B·쉘 무간섭 / 삽입·제거 경로 / 배선)
6. 전부 통과 시 INDEX FINAL SUCCESS 선언 → 다음 세션 MIDDLE

---

# 【정정 및 보강】 rib 검토 중 발견된 cap 설계 결함

지시대로 I1/I2/I3 사이에 별도 connecting rib 을 넣으려고 실측하다가,
**위 §D 의 평면 cap 설계 자체가 실물과 간섭한다**는 것을 발견했다. 먼저 이것부터 정정한다.

## R1. 발견 — 11 x 11 평면 cap 이 기존 형상과 간섭한다

cap 부피(홀더 뒷면 12.5 ~ 14.5) 안의 격자점을 실물 tessellation 으로 직접 검사:

| cap 크기 | I1 | I2 | I3 |
|---|---|---|---|
| 11 x 11 x 2 | 2 / 196 (1 %) | **31 / 196 (15 %)** | **32 / 196 (16 %)** |
| 9 x 9 x 2 | 1 / 196 (0 %) | 16 / 196 (8 %) | 18 / 196 (9 %) |
| 7 x 7 x 2 | 0 / 196 (0 %) | 12 / 196 (6 %) | 2 / 196 (1 %) |

깊이별 지도를 뜨면 막는 것이 무엇인지 분명하다 (X = 재료):

```
[I2] 깊이 12.6                      [I3] 깊이 12.6
  du -5  XXX........                  du -5  .XXXXXXXXXX
  du -4  XXX........                  du -4  .XXXXXXX.XX
  du -3  XX.........                  du -3  ..........X
  du -2  XX.........                  du +5  ..XXXXXX...
```

**막는 것은 인접 홀더와 쉘 벽이다.** 홀더 뒷면은 깨끗하게 노출된 평면이 아니라,
세 홀더가 42.6 / 53.5 / 56.1도 로 융합된 **faceted 표면**이고
그 사이사이로 이웃 홀더·쉘이 파고들어 있다.

→ **평면 cap 을 그 위에 얹는다는 전제가 틀렸다.** 그래서 §D 의 cap 3개 융합 구조도,
그것을 잇는 직선/아치 rib 도 전부 성립하지 않았다
(직선 rib: I1-I2 / I2-I3 전 조합 쉘 충돌. 아치형: delta 0~6 mm 전부 충돌).

## R2. 수정된 아키텍처 — retainer 를 '홀더 클러스터의 음형'으로 만든다

평면 cap 을 얹는 대신, **후면 공동을 채운 뒤 홀더를 빼내는** 방식으로 바꾼다.

```
retainer = (홀더 뒤 공동을 덮는 넉넉한 blank)
           − (홀더 OBB 4개 + 여유 0.2)
           − (나사 B 보스 + 여유 1.0)
           − (쉘)
           + (pad 3개)
```

이렇게 하면 **backbone / rib / web 이 따로 필요 없다.** 몸통 자체가
홀더 후면 형상에 정확히 맞는 하나의 연속체가 되고, 그것이 곧 구조 연결이다.
**pad 의 각도·위치는 그대로 유지된다** (지시 준수).

## R3. 후면 자유 공간 실측 — 연결 가능성 확인

0.75 mm 복셀 격자(25,839개)로 홀더 뒤 공동을 실측했다.

| 단계 | 남은 복셀 |
|---|---|
| 전체 격자 | 25,839 |
| 홀더 OBB + 나사 B 제외 | 16,540 |
| retainer 영역(각 축 깊이 12.5~18.5, 측방 ≤ 7)으로 제한 | 6,231 |
| **쉘 제외 (실물 tessellation)** | **5,784** |

- **연결 성분 2개, 최대 성분 5,783 복셀 = 2,440 mm³**
- **최대 성분이 세 pad 자리를 전부 포함한다** (I1 135 / I2 130 / I3 137 복셀)

→ **세 pad 를 잇는 연속체가 실제로 존재한다.**

## R4. 병목 측정 — 통과 가능한 최대 web 두께

각 자유 복셀에서 막힌 재료(홀더·나사 B)까지의 거리를 구하고,
pad 영역 사이를 잇는 **widest path** 의 병목을 이분 탐색으로 찾았다.

| 연결 | 병목 반경 | **통과 가능한 최대 web 두께** | 병목 위치 |
|---|---|---|---|
| **I1-I2** | 1.77 mm | **3.54 mm** | (−9.76, −10.68, +11.71) |
| **I2-I3** | 1.59 mm | **3.18 mm** | (−3.01, −15.18, +14.71) |
| **I1-I3** | 1.59 mm | **3.18 mm** | (−3.01, −15.18, +10.21) |

경로 길이: I1-I2 18.0 mm / I2-I3 17.2 mm / I1-I3 10.5 mm.

### 채택: **web 두께 2.0 mm**

| 연결 | web 1.5 mm | **web 2.0 mm** | web 2.5 mm |
|---|---|---|---|
| I1-I2 | 여유 +1.02 | **+0.77 mm** | +0.52 |
| I2-I3 | 여유 +0.84 | **+0.59 mm** | +0.34 |
| I1-I3 | 여유 +0.84 | **+0.59 mm** | +0.34 |

- 요구치 **≥ 1.5 mm 충족**, 지시 목표인 **2.0 mm 전후** 그대로 채택
- 양쪽 여유 최소 **+0.59 mm** → 출력 공차를 흡수할 여지가 있다
- 2.5 mm 도 성립하지만 여유가 0.34 mm 로 줄어 **2.0 mm 를 권장**한다

## R5. 요구 조건 대조

| 요구 | 결과 |
|---|---|
| I1/I2/I3 세 cap 사이 **모두** 실질 연결 | **충족** — 세 쌍 전부 2.0 mm web 성립 (0.28 mm 겹침 의존 제거) |
| minimum rib/web thickness ≥ 1.5 mm | **2.0 mm** |
| 가능하면 2.0 mm 전후 | **정확히 2.0 mm** |
| switch rear face 와 비접촉 | **충족.** 세 병목 지점의 각 축 기준 깊이 12.28 ~ 18.43 mm 이고, 깊이 12.28 인 지점은 해당 축(I2)에서 **측방 11.00 mm** 로 보어(3.2) 밖이다 |
| wiring slot 과 비간섭 | **충족** — R6 에서 슬롯 방향 재배치 |
| screw B 기존 clearance 유지 | **충족.** 나사 B 를 여유 1.0 mm 로 미리 제외한 상태에서 병목을 측정했다 |
| P1S 0.4 mm nozzle 출력 | **충족.** web 2.0 mm = 5 lines |
| pad 각도·위치 불변 | **충족.** pad 정의를 건드리지 않았다 |

## R6. 배선 슬롯 방향 재배치 (web 회피)

web 경로가 점유하는 방향을 실측해 슬롯을 90도 틀었다.

| | web 점유 방향 | **슬롯 방향(신규)** | 그 방향 여유 |
|---|---|---|---|
| I1 | +u | **−v** | 22.9 mm |
| I2 | −v | **+v** | 23.6 mm |
| I3 | +u, +v, −u | **−v** | 12.7 mm |

> **§I 의 "I2 배선은 ±u 로" 는 이 표로 대체한다.**
> I2 는 축 방향이 나사 B 보스로 3.2 mm 뿐이지만 **+v 로 23.6 mm** 가 열려 있고
> web(−v)과도 겹치지 않아 +v 가 더 낫다.

## R7. 구현에 반영할 변경 (§12 원자 순서 갱신)

```
A. retainer blank NEW BODY  (홀더 뒤 공동을 덮는 넉넉한 형상)
B. 홀더 OBB 4개 + 여유 0.2 SUBTRACT   <- 여기서 faceted 접촉면과 web 이 동시에 생긴다
C. 나사 B 보스 + 여유 1.0 SUBTRACT
D. 쉘 간섭부 정리 SUBTRACT
E. PAD_I1 / PAD_I2 / PAD_I3 각각 ADD (각도·위치 불변)
F. 배선 슬롯 3개 SUBTRACT (I1 −v, I2 +v, I3 −v)
G. EAR_A / EAR_B 쉘에 union, 나사 구멍
H. 최종 검증 (web 최소 단면 재측정 포함)
```

기존 §D 의 "cap 3개를 겹쳐서 융합" 단계는 **폐기**한다.
"blank − 홀더" 한 번으로 접촉면·web 이 함께 만들어지므로 더 단순하고, 위 실측대로 성립한다.

---

# 【게이트 결과】 regeneration 직접 확인 — ERROR 1건, §1 에 따라 HOLD

폴러가 23:29 에 rate limit 해제를 잡아 `GET /features` 200 을 받았다.

## G1. 전체 상태

| 항목 | 값 |
|---|---|
| feature 총수 | **162** |
| rollbackIndex | 162 |
| isComplete | **true** |
| **OK** | **161** |
| INFO | 4 |
| **ERROR** | **1** |
| suppressed | **0** |

## G2. ERROR 1건 — `INDEX_switch_pockets`

```
featureId : FkGjuaVRtcptOX1_14
name      : INDEX_switch_pockets
type      : oneGripIndexButtons   (구 OneGrip_FingerButtons FS)
parameter : stage = CONSTRUCTION
트리 위치 : 인덱스 105
```

### 원인 — 변수 정의보다 앞에 있다

이 피처는 `oneGripIndexButtons` 의 top-level 에서 스위치 변수들을 읽는데,
**그 변수들이 트리에서 더 뒤에 정의되어 있다.**

| 참조 변수 | 정의 인덱스 | 판정 |
|---|---|---|
| `#finger_retainer_clearance` | 111 | **105 보다 뒤 → 참조 실패** |
| `#finger_retainer_thickness` | 112 | **참조 실패** |
| `#finger_switch_total_height` | 113 | **참조 실패** |
| `#finger_switch_pocket_width` | 116 | **참조 실패** |
| `#finger_switch_front_lip` | 117 | **참조 실패** |
| `#finger_switch_stem_bore` | 118 | **참조 실패** |
| `#finger_button_cap_width` / `_clearance` / `_cap_height` | 89 / 93 / 94 | OK |

이는 docs 기록에 남아 있는 알려진 함정과 같은 유형이다 —
"Feature Studio 를 고치면 기존 인스턴스가 자동 갱신되므로,
top-level 에 뒤쪽 변수의 `getVariable` 을 추가하면 앞쪽 인스턴스가 전부 ERROR 가 난다."
이 피처는 그때 남은 **잔해**다.

### 영향 — 없음

| 확인 | 결과 |
|---|---|
| stage | `CONSTRUCTION` — `opPlane` 만 만드는 참조 평면 단계. **solid 를 만들지 않는다** |
| 동일 역할의 정상 피처 | **인덱스 119 `INDEX_construction` (OK)** 가 이미 존재 → **중복** |
| ERROR 상태의 산출물 | 없음 |
| solid body | **18개** = 원본 14 + INDEX 캡 4 (예상과 정확히 일치) |
| docs/15 검증 결과 | 이 ERROR 가 있는 상태에서 측정한 값들이므로 **전부 유효** |

> **즉 이 ERROR 는 형상에 아무 영향이 없는 '죽은 중복 피처' 다.**
> 그러나 §15 조건 2 는 `regeneration ERROR = 0` 이므로 **FINAL PASS 로 올릴 수 없다.**

## G3. INFO 4건 — 신규 작업과 무관

```
FXg5bkjBhv2Qlko_0   Joystick_part_4_plane
FBNFfBlWKWESHfG_0   Joystick_part_1_plane
Fv7FALzCB7y8Fl1_0   Joystick_part_2_plane
FzABWyP1gJz4h4t_0   Joystick_part_3_plane
```

전부 **인덱스 0 대역의 원본 문서 피처**(그립 로프트 단면 평면)다.
신규 INDEX 작업으로 생긴 것이 아니며, 원본 상태 그대로다.

## G4. 조치 — §1 에 따라 HOLD

> "ERROR 가 하나라도 있으면 retainer 를 만들지 말고 즉시 HOLD 한다."

**retainer 형상을 만들지 않았다.** 이번 실행의 CAD 형상 변경은 계속 0건이다.

### 권고하는 최소 수정 (승인 필요)

```
DELETE feature  FkGjuaVRtcptOX1_14  (INDEX_switch_pockets)
```

- 근거: stage=CONSTRUCTION 이라 solid 를 만들지 않고, 인덱스 119 `INDEX_construction` 과 중복이며,
  ERROR 상태라 현재도 아무것도 산출하지 않는다
- 삭제해도 형상은 바뀌지 않아야 한다(예측). 삭제 직후 solid 18개 / 시트 / 칸막이 /
  나사 여유 / assembly 25-25 를 재확인해 실제로 무변화임을 확인한다
- 대안: 삭제 대신 **suppress** 도 가능하다. 되돌리기가 더 쉬우므로 보수적으로 가려면 이쪽이다

**삭제는 파괴적 조작이므로 승인 없이 실행하지 않았다.**

## G5. §15 조건 재대조

| # | 조건 | 상태 |
|---|---|---|
| 2 | **regeneration ERROR 0** | **FAIL — 1건** (원인·영향 규명 완료, 수정안 대기) |
| 나머지 | — | docs/16 §M 과 동일 |

→ **INDEX FINAL SUCCESS 보류 유지. retainer 착수 보류.**
