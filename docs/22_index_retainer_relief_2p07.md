# INDEX retainer — service relief sweep 2.07 mm 적용 및 검증

- 일자 2026-08-19
- 승인 근거: docs/21 → "sweep 3.00 → 2.07 mm 변경 승인"
- 수정 피처: **`INDEX_retainer_service_relief`** (`F2M3epnJT0bImz7_16`) — sweep 길이만 변경
- 변경 내용: `0.5 mm × 6 (=3.00)` → **`0.345 mm × 6 (=2.07)`**
  (이산화는 결과에 영향 없음이 docs/21 에서 입증되어 step 수는 6 유지)
- **유지된 값:** fit clearance 0.25 / relief 반경 3.75 / X 범위 [−22, +1] /
  w = (−0.4734, −0.8350, −0.2805) / d_required 1.57 / margin 0.50 / d_service 2.07
- **손대지 않은 것:** pad, wiring slot, holder, shell, JaD/JfD, 나머지 retainer geometry

---

## A. regeneration — **PASS**

```
feature 169    OK 169 / ERROR 0 / WARNING 0 / INFO 4 (원본 Joystick_part_*_plane)
isComplete = true
```

## B. actual removed volume

| 상태 | 부피 |
|---|---|
| relief 전 | 2028.0 mm³ |
| sweep 3.00 | 1909.5 mm³ (제거 118.5) |
| **sweep 2.07 (현재)** | **1967.7 mm³ (제거 60.3)** |

예측 65.7 mm³ 대비 60.3 mm³ — 차이 5.4 mm³ (8 %)로, 0.4 mm 복셀 해상도 오차 범위다.
**현저한 불일치 아님.**

## C. RWID body integrity — **PASS**

| 항목 | 결과 |
|---|---|
| retainer body | **`RWID` 1개** |
| 연결성분 (복셀 0.4 mm, 30,878개) | **1** |
| split / fragment | **0 / 0** |
| `JaD` = Joystick_1 / `JfD` = Joystick_2 | 각 1 body |
| solid 총수 | 19 |

## D. actual maximum service travel — **2.24 mm (PASS)**

| | 값 |
|---|---|
| **최대 무충돌 이동** | **2.24 mm** |
| 요구 (d_service) | 2.07 mm → **+0.17 mm 여유** |
| 예측 | 2.42 mm |
| 그 뒤 첫 장애 | face `RSI+` (국소 쉘면) — **나사 B 보스가 아니다** |

예측(2.42)보다 낮은 이유: 예측은 나사 B 보스만 장애물로 두고 계산했으나,
sweep 을 줄이자 **다른 국소 쉘면(`RSI+`)이 2.24 mm 에서 먼저 나타났다.**
요구치는 여전히 충족한다.

## E. d_I1 / d_I2 / d_I3 — **1.56 mm**

retainer 전체가 네 보어에서 완전히 이탈하는 거리 = **1.56 mm**
(예측 1.56 ~ 1.57 과 일치)

## F. t = 2.07 mm disengagement — **PASS**

| | 보어 겹침 |
|---|---|
| I1 | **0** |
| I2 | **0** |
| I3 | **0** |
| I4 | 0 |

스위치 몸체 간섭: `t=0.00 : 78 (의도된 pad preload 접촉)` → `t=0.20 이후 전부 0`

## G ~ J. structural web — **최소 2.10 mm (PASS)**

| 연결 | relief 전 | sweep 3.00 | **sweep 2.07** |
|---|---|---|---|
| **I1-I2** | 2.28 | 1.54 | **2.10 mm** |
| **I2-I3** | 1.91 | 1.54 | **2.10 mm** |
| **I1-I3** | 1.91 | 1.97 | **2.15 mm** |
| **최소** | 1.91 | 1.54 | **2.10 mm** |

- GO 기준 **≥ 1.80 mm 충족** (여유 +0.30 mm)
- 예측 2.12 mm 와 0.02 mm 차이
- **sweep 3.00 대비 +0.56 mm 개선**, relief 전(1.91)보다도 높다

## K. pad retained area — **3개 모두 완전 회복**

접촉면 (스위치 뒷면 3.6 × 3.6, 225 표본):

| | relief 전 | sweep 3.00 | **sweep 2.07** | |
|---|---|---|---|---|
| I1 | 182 | 182 | **182** | 완전 회복 |
| **I2** | 194 | **191 (−1.3 %)** | **194** | **완전 회복** |
| I3 | 183 | 183 | **183** | 완전 회복 |

pad 돌출 구간 단면 (243 표본):

| | relief 전 | sweep 3.00 | **sweep 2.07** | |
|---|---|---|---|---|
| I1 | 191 | 191 | **191** | 완전 회복 |
| **I2** | 213 | **197 (−6.6 %)** | **213** | **완전 회복** |
| I3 | 168 | 168 | **168** | 완전 회복 |

→ **docs/20 에서 유일하게 줄었던 I2 pad 가 원래 값으로 완전히 돌아왔다.**

## L. wiring state — **완전 무변화**

| | relief 전 | sweep 3.00 | sweep 2.07 |
|---|---|---|---|
| I1 (−v) | 180/180 | 180/180 | **180/180** |
| I2 (+v) | 180/180 | 180/180 | **180/180** |
| I3 (−v) | 180/180 | 180/180 | **180/180** |

## M. fastening — **GO**

§8 게이트 전 항목 대조:

| 조건 | 요구 | 실측 | 판정 |
|---|---|---|---|
| regeneration ERROR | 0 | **0** | **PASS** |
| WARNING | 0 | **0** | **PASS** |
| RWID single body | 예 | **예** | **PASS** |
| service travel | ≥ 2.07 mm | **2.24 mm** | **PASS** |
| pad 3개 disengaged @ 2.07 | 예 | **0/0/0** | **PASS** |
| **minimum structural web** | **≥ 1.80 mm** | **2.10 mm** | **PASS** |
| wiring slots | 정상 | **완전 무변화** | **PASS** |
| pad contact | 정상 | **완전 회복** | **PASS** |

→ **전 항목 통과. fastening 단계 GO.**

### 다음 구현 대상

```
EAR_A′ = (-14.11, -4.03, +11.24)     retainer 본체에 직접 접함 (탭 길이 ~0), 쉘 보스 2.37 mm
EAR_B′ = ( -4.52, -15.38, +1.97)     retainer 본체에 직접 접함 (탭 길이 ~0), 쉘 보스 2.51 mm
```

기존 `Screw_holes` 는 수정하지 않는다. 신규 boss/ear 만 downstream feature 로 추가한다.
ear 추가 후 **0 ~ 2.07 mm service path 를 반드시 재검사**한다.

---

## 이번 변경으로 확인된 것

> **relief sweep 길이는 web 을 지배하는 유일한 변수였고,
> 필요·충분값(= d_service)으로 맞추자 web 이 relief 전보다도 좋아졌다.**
>
> - sweep 3.00 → web 1.54, pad I2 손실, 제거 118.5 mm³
> - **sweep 2.07 → web 2.10, pad 완전 회복, 제거 60.3 mm³**
>
> 과도한 sweep 이 순수한 손실이었음이 실물로 증명되었다.
