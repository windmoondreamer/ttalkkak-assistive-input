# INDEX/MIDDLE 단순 공용 캐리어 V1

날짜: 2026-08-21  
Onshape document: `a21e64f36bc61df760d4587c`  
workspace: `ef6a7b3ccc45186203e4d2ca`  
Part Studio: `425d9199b59cfb1efd9ddc35`

## 1. 버전

| 구분 | 이름 | versionId |
|---|---|---|
| 변경 전 체크포인트 | `PRE_MIDDLE_INDEX_STYLE_REBUILD` | Onshape version history에 생성 확인 |
| 완료 버전 | `FINGER_SIMPLIFIED_CARRIER_V1` | `f51e9d9a868db9ef0fcd4b06` |

완료 버전 URL:

`https://cad.onshape.com/documents/a21e64f36bc61df760d4587c/v/f51e9d9a868db9ef0fcd4b06/e/425d9199b59cfb1efd9ddc35`

## 2. M2가 지저분하게 보인 원인

기존 MIDDLE 전용 구조에는 버튼마다 다음 형상이 있었다.

- 폭 `0.80 mm`의 후면 레일 2개
- 깊이 `0.70 mm`의 후크 2개
- 독립 원통 스페이서 1개
- 스위치 축과 외피 법선이 다른 상태에서 기울어진 `10 mm` 지지링

특히 M2에서는 기울어진 레일·후크와 지지링 모서리가 외피를 관통하거나 접선에 가까운 결합을 만들었다. 그 결과 외부에서 얇은 띠와 삼각 쐐기처럼 보였고 FDM 출력 시 지저분한 잔여 형상이 될 수 있었다.

## 3. 적용 구조

THUMB 구조와 위치는 변경하지 않았다. INDEX의 포켓·캡·배선 채널·RWID/RZKD 체결부도 유지했다.

M1~M4는 다음 원칙으로 한 번에 재구성했다.

| 항목 | 최종 값 / 구조 |
|---|---|
| 스위치 중심·누름축 | 기존 ITS-1105 M1~M4 그대로 |
| 포켓 | `6.40 x 6.40 mm`, 기존 실물 삽입 합격 치수 유지 |
| 외부 개구부 | `8.00 x 8.00 mm` |
| 캡 | `7.60 x 7.60 mm`, 외부 노출 `1.40 mm` |
| 캡 내부 | 중앙 `Ø3.0 mm` 누름봉 1개만 유지 |
| 삭제 | MIDDLE 레일, 후크, 스톱 러그, 독립 스페이서 |
| 홀더 front trim | 외피 법선 기준 표면에서 `2.20 mm` 안쪽 |
| 공용 접촉 포스트 | `3.60 x 3.60 mm` |
| 공용 캐리어 깊이 | 버튼 기준 `14.50 mm` |
| 캐리어 골격 | `3.20 x 4.00 mm` |

공용 캐리어는 두 개만 사용한다.

- `RWID`: I1~I3와 M1~M3의 후면 접촉 포스트/골격을 흡수
- `RZKD`: I4와 M4의 후면 접촉 포스트/골격을 흡수

기존 RWID/RZKD 나사 귀, 서비스 릴리프 및 배선 슬롯은 제거하지 않았다. 신규 골격은 기존 리테이너에 양의 체적 겹침을 갖는 추가 재료다.

## 4. 형상 수 변화

| 항목 | 변경 전 | 변경 후 |
|---|---:|---:|
| Part Studio feature count | 202 | 203 |
| solid part count | 30 | 22 |
| INDEX/MIDDLE 독립 스페이서 | 8 | 0 |
| MIDDLE 독립 캡 | 4 | 4 |
| 공용 후면 캐리어 | RWID/RZKD | RWID/RZKD 유지·확장 |

파트 감소 `-8`은 독립 스페이서 8개 제거에 정확히 대응한다. 새 MIDDLE 캡 4개는 억제된 기존 MIDDLE 캡 4개를 대체하므로 순증감이 없다.

## 5. 수치 간섭 감사

로컬 보수적 OBB/mesh 감사 결과:

| 항목 | 최소 여유 |
|---|---:|
| 캐리어 ↔ 스위치 몸체 | `2.740250 mm` |
| 캐리어 ↔ 단자 고정 루트 | `0.855870 mm` |
| 캐리어 ↔ 쉘 | `0.249822 mm` |
| 캐리어 ↔ 나사 | `5.794511 mm` |
| 접촉 포스트 ↔ 단자 루트 | `1.192190 mm` |

RWID와 RZKD 양쪽 모두 캐리어 시작부의 positive volumetric overlap을 확인했다.

## 6. 외부 출력성 확인

front trim 적용 전에는 M2 지지링 모서리가 정면에서 삼각선으로 보였다. 외피 법선 기준 `2.20 mm` front trim을 추가한 뒤:

- M2 주변 얇은 띠 제거
- 삼각 쐐기/외피 관통 제거
- 외부에는 사각 캡만 노출
- M1~M4 레일·후크 0개
- MIDDLE 캡은 INDEX와 같은 `7.6 mm` 제품군 언어로 통일

검증 이미지:

- `renders/finger_simplified_front.png`
- `renders/finger_simplified_iso.png`

## 7. 재생성·조립

| 검사 | 결과 |
|---|---|
| 새 단순화 피처 FeatureScript 알림 | 0 |
| Part Studio regeneration | PASS |
| Part Studio parts | 22 |
| Assembly components | 25 |
| 기존 assembly tree 참조 누락 표시 | 없음 |
| THUMB 변경 | 없음 |

## 8. 최종 판정

`FINGER_SIMPLIFIED_CARRIER_V1`은 M2의 지저분한 외부 형상을 제거하고, MIDDLE을 INDEX 방식의 단순 캡/포켓 언어로 맞춘 최소 복잡도 구현이다.

CAD WRITE RESULT = PASS  
M2 EXTERNAL PROTRUSION = REMOVED  
INDEPENDENT FINGER SPACERS = 0  
FINAL VERSION = `f51e9d9a868db9ef0fcd4b06`
