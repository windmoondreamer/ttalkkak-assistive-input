# Lalboard finger cluster 분석 — OneGrip Play 3방향 모듈에 적용할 원리

> 조사일: 2026-08-13
>
> 조사 대상: 공식 [`JesusFreke/lalboard`](https://github.com/JesusFreke/lalboard) 저장소의 `v2.5.1` 태그와 공식 STL/3MF 서브모듈 [`JesusFreke/lalboard_stls`](https://github.com/JesusFreke/lalboard_stls)
>
> 소스 기준 커밋: `1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a` (`v2.5.1`)
>
> 소스와 짝을 이루는 출력물 커밋: `282d61ae3a4d06d4dba2590779023b716da62b45` (`v2.5.1`)
>
> 추가 비교 출력물 커밋: `cfd0534cea86e86224ba42f4a193078c626f1d7f` (`main`)
>
> 재현 경로: `references/lalboard-v2.5.1/`와 그 내부 `stls/`. 커밋과 분석 파일 SHA-256은 `references/reference-lock.json`에 고정했고 `references/fetch_lalboard_references.ps1`로 검증한다.
>
> 주의: 이 문서는 원본을 실제로 내려받아 Python 생성 코드, 3MF 내부 모델과 슬라이서 설정을 확인한 결과다. OneGrip에 제시하는 수치는 원본 치수와 **OneGrip용 권장 시작값**을 구분해 적었다. 이 조사 기준 출력물의 정식 커밋은 `282d61a`다. 뒤의 `cfd0534`에서도 이 문서가 사용한 5개 형상 파일의 SHA-256은 같지만, 두 커밋 전체가 동일하다고 주장하지 않는다.

## 1. 먼저 바로잡아야 할 점

첨부 요청에 적힌 `cluster.3mf`, `cluster_key_center.3mf`, `cluster_key_short.3mf`, `cluster_key_tall.3mf`는 현재 `lalboard` 본 저장소가 아니라, 본 저장소가 `stls` 서브모듈로 참조하는 별도 공식 저장소 `lalboard_stls`에 있다. 본 저장소에는 여러 부품을 한 판에 배치하고 슬라이서 설정까지 저장한 `configs/clusters.3mf`, `configs/keys_etc.3mf`도 있다.

또한 Lalboard finger cluster는 3방향 로커 하나가 아니다.

- 중앙의 독립 직선 이동 키 1개
- 중앙을 둘러싼 북·남·동·서 독립 회전 키 4개
- 총 5개의 서로 독립된 키

OneGrip는 이 가운데 **중앙 + 서쪽 + 동쪽**, 즉 `CENTER / LEFT / RIGHT` 원리만 가져오는 것이 정확하다. 5방향 원본을 통째로 축소하거나, 세 입력을 하나의 공통 로커로 합치는 것은 Lalboard의 핵심 장점인 독립성을 잃는다.

## 2. 확인한 공식 파일

| 용도 | 공식 파일 | 확인 내용 |
|---|---|---|
| 전체 생성 로직 | [`lalboard.py`](https://github.com/JesusFreke/lalboard/blob/1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a/lalboard.py) | 모든 실치수, 키 피벗, 자석 홈, 클러스터 지지대 생성 |
| finger body 진입점 | [`parts/cluster/cluster.py`](https://github.com/JesusFreke/lalboard/blob/1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a/parts/cluster/cluster.py) | `cluster_design()`을 호출해 본체 생성 |
| 조립 어셈블리 | [`parts/cluster_assembly/cluster_assembly.py`](https://github.com/JesusFreke/lalboard/blob/1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a/parts/cluster_assembly/cluster_assembly.py) | 중앙·4방향 키와 3점 지지대를 조립한 기준 모델 |
| 중앙 키 진입점 | [`parts/cluster_key_center/cluster_key_center.py`](https://github.com/JesusFreke/lalboard/blob/1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a/parts/cluster_key_center/cluster_key_center.py) | `center_key()` 호출 |
| 짧은 방향키 | [`parts/cluster_key_short/cluster_key_short.py`](https://github.com/JesusFreke/lalboard/blob/1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a/parts/cluster_key_short/cluster_key_short.py) | 동·서·남 키 |
| 긴 방향키 | [`parts/cluster_key_tall/cluster_key_tall.py`](https://github.com/JesusFreke/lalboard/blob/1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a/parts/cluster_key_tall/cluster_key_tall.py) | 북쪽 키 |
| 실제 출력 body | [`cluster.3mf`](https://github.com/JesusFreke/lalboard_stls/blob/282d61ae3a4d06d4dba2590779023b716da62b45/cluster.3mf) | 3MF 메시 경계와 단위 직접 측정 |
| 실제 중앙 키 | [`cluster_key_center.3mf`](https://github.com/JesusFreke/lalboard_stls/blob/282d61ae3a4d06d4dba2590779023b716da62b45/cluster_key_center.3mf) | 실제 출력 외형 측정 |
| 실제 짧은 키 | [`cluster_key_short.3mf`](https://github.com/JesusFreke/lalboard_stls/blob/282d61ae3a4d06d4dba2590779023b716da62b45/cluster_key_short.3mf) | 실제 출력 외형 측정 |
| 실제 긴 키 | [`cluster_key_tall.3mf`](https://github.com/JesusFreke/lalboard_stls/blob/282d61ae3a4d06d4dba2590779023b716da62b45/cluster_key_tall.3mf) | 실제 출력 외형 측정 |
| 키/클러스터 슬라이서 설정 | [`configs/keys_etc.3mf`](https://github.com/JesusFreke/lalboard/blob/1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a/configs/keys_etc.3mf), [`configs/clusters.3mf`](https://github.com/JesusFreke/lalboard/blob/1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a/configs/clusters.3mf) | 0.4 mm 노즐, 0.1 mm 층, PLA, 무서포트 등 확인 |

## 3. 실제 치수

### 3.1 공식 3MF 메시 경계

3MF 파일은 모두 `millimeter` 단위다. 압축 컨테이너 내부 `3D/3dmodel.model`의 모든 vertex를 읽어 얻은 bounding box는 다음과 같다.

| 부품 | 실제 메시 외형 크기 X × Y × Z |
|---|---:|
| cluster body | 24.900 × 43.900 × 8.000 mm |
| center key | 14.999 × 14.999 × 10.400 mm |
| short side key | 13.000 × 15.000 × 2.775 mm |
| tall side key | 13.000 × 21.000 × 4.538 mm |
| front mount clip | 7.000 × 15.500 × 9.575 mm |
| support base | 10.903 × 24.297 × 4.000 mm |

`cluster body`의 43.9 mm에는 앞·뒤 장착 연장부가 포함된다. 실제 손가락 주변의 기본 cluster core는 코드상 24.9 × 24.9 mm다.

### 3.2 코드에서 확인한 핵심 세부 치수

| 항목 | Lalboard 원본값 | 근거 |
|---|---:|---|
| side-key stem 폭 | 7.3 mm | `post_width = 7.3` |
| side-key stem/피벗 두께 | 1.8 mm | `key_thickness = 1.8` |
| side-key base guide 폭 | 7.6 mm | `post_hole_width = post_width + 0.3` |
| side-key well 폭 × 깊이 | 8.65 × 4.75 mm | `post_hole_width + 0.525×2`, `4.75` |
| side-key well 높이 | 8.0 mm | `key_well` |
| side-key 최대 회전각 | 12.5° | `vertical_key_base(pressed_key_angle=12.5)` |
| 짧은 키 접촉부 폭 × 높이 | 13 × 5 mm | `cluster_key_short()` |
| 긴 키 접촉부 폭 × 높이 | 13 × 11 mm, 접시각 10° | `cluster_key_tall()` |
| 접촉면 dish 생성 반경 | 15 mm | `key_dish = Cylinder(..., 15)` |
| retaining ridge 돌출/면 폭 | 0.3 / 0.3 mm | `retaining_ridge_design()` |
| stem의 위치결정 홈 | 깊이 0.7 mm, 폭 0.75 mm | `vertical_key_post()`, side key preset |
| center cap 직경 | 15 mm | `key_radius = 7.5` |
| center 이동량 | 1.7 mm | `key_travel = 1.7` |
| center guide post | 3.5 × 3.5 mm, 두 개 | `left_post`, `right_post` |
| center post 중심 간격 | 8.2 mm | 중심에서 ±4.1 mm |
| center guide hole | 4 × 4 mm, 두 개 | `center_key_left/right_hole` |
| cluster core | 24.9 × 24.9 mm | `base_cluster_design()` |

여기서 side-key의 stem 7.3 mm와 base guide 7.6 mm 차이는 전체 0.3 mm, 즉 이론상 한쪽 0.15 mm다. 이는 원본의 0.1 mm 레이어·정밀 튜닝을 전제로 한 값이므로 일반 PETG 0.2 mm 출력에 그대로 쓰면 끼거나 마찰 편차가 커질 가능성이 높다.

## 4. 손가락 중앙 지지와 세 방향 운동

### 4.1 중앙 지지

손끝은 15 mm 원형 center cap 위에 놓인다. 이것이 기준점이므로 사용자는 손가락 전체를 세 버튼 사이에서 왕복시키지 않는다.

center key는 다음 구조로 옆 흔들림과 회전을 억제한다.

1. 원형 cap 아래에 3.5 × 3.5 mm 사각 post가 두 개 있다.
2. post 두 개가 cluster의 4 × 4 mm guide hole 두 개를 통과한다.
3. 두 post의 중심은 8.2 mm 떨어져 있어 단일 stem보다 yaw가 억제된다.
4. 입력은 1.7 mm 직선 하강이다.

즉 중앙 키는 **손가락 받침과 중앙 입력을 겸하지만, 좌·우 입력의 공통 로커가 아니다.** 이것이 OneGrip에 가장 중요하게 가져와야 할 원리다.

### 4.2 LEFT / RIGHT 운동

Lalboard의 동·서 방향키는 각각 별도 부품이다. 손가락이 center cap에 머문 상태에서 손끝을 약간 roll하여 옆 접촉면을 누르면, 해당 키만 아래쪽의 독립 피벗을 중심으로 회전한다.

- LEFT: west key만 회전
- CENTER: center key만 직선 하강
- RIGHT: east key만 회전

원본 방향키의 최대 회전은 12.5°다. 사용자가 방향키 쪽으로 손가락 전체를 옮기는 것이 아니라, 중앙 지지 위에서 distal phalanx를 조금 굴려 측압을 만드는 방식이다.

OneGrip에서는 손가락이 수직 그립을 감싸므로 Lalboard의 평면 좌표를 그대로 복사하지 말고, 각 손끝의 지문면 법선에 맞춰 모듈 전체를 회전해야 한다. 그러나 각 모듈 내부의 상대 관계는 아래와 같이 유지한다.

```text
손끝을 바라본 단면

      LEFT paddle     RIGHT paddle
           \          /
            \ [ C ]  /
              center
              guide

L/R = 서로 다른 피벗 부품
C   = 두 guide-post를 가진 직선 부품
```

## 5. 피벗, 키 복귀, 클릭감

### 5.1 side-key 피벗

각 side key stem 끝에는 1.8 mm 두께에 해당하는 원통형 피벗이 일체로 생성된다. cluster body에는 이 피벗을 받는 V형 포켓과 회전 공간이 있다. 조립 시 피벗 축을 base의 피벗 축에 맞춘다. 공식 조립 함수 `_align_side_key()`도 두 피벗 축을 정렬한 뒤 중심을 일치시킨다.

base에는 0.3 mm retaining ridge가 있어 키가 빠지는 방향의 이탈을 억제한다. 이 ridge는 원본 0.1 mm 레이어에서 3개 층, 외곽선 폭 0.39 mm에서 약 한 줄 규모의 매우 작은 형상이다.

### 5.2 자석 복귀

원본은 스프링이나 접점 스위치를 쓰지 않는다. 키 stem과 cluster body의 자석이 다음 역할을 함께 한다.

- 중립 위치 유지
- 최초 움직임에서 높은 breakaway force 생성
- 누른 뒤 중립으로 snap-back
- 키를 별도 체결구 없이 분리·청소 가능하게 유지

공식 설명에 따르면 키를 처음 움직일 때 자석 사이 거리가 가장 가까워 힘이 가장 크고, 이탈 후 힘이 빠르게 감소한다. 따라서 일반 코일스프링과 달리 전단부에 촉각 피크가 몰린다. 원저자는 center key 자석을 약화해 대략 40–50 gf에서 약 25 gf로 낮춘 사례도 설명했지만, 이는 제작자 경험치이지 OneGrip의 목표 작동력으로 그대로 채택할 값은 아니다.

### 5.3 OneGrip에 그대로 복제하지 않을 부분

OneGrip는 광학 센서·자석·PCB를 쓰지 않고 일반 순간 스위치와 직접 배선을 사용한다. 따라서 자석 복귀를 억지로 복제하지 않는다.

- 각 paddle의 복귀는 해당 독립 스위치의 plunger/lever 복귀력으로 처리한다.
- paddle 피벗이 무겁거나 유격이 크면 작은 torsion spring만 추가한다.
- 중앙 키도 별도 스위치 하나로 받친다.
- 키 입력력을 스위치가 아니라 shell이 받도록 독립 hard stop을 둔다.

Lalboard에서 가져올 것은 **자석 자체가 아니라 독립 키, 짧은 roll 동작, 중앙 기준점, 로컬 피벗**이다.

## 6. 간섭과 오입력을 줄이는 원리

Lalboard는 소프트웨어 필터보다 기구적 분리를 우선한다.

1. 중앙과 방향키가 물리적으로 다른 부품이다.
2. 방향키마다 자체 피벗 축이 있다.
3. 중앙 키의 두 guide post가 좌우 흔들림을 억제한다.
4. 각 방향키 stem은 별도 key well에 들어간다.
5. key well과 stationary wall이 최대 회전 범위를 제한한다.
6. center cap이 손끝의 기준 위치를 유지해 다른 키까지 손가락을 이동할 필요를 없앤다.
7. 각 key cap은 오목한 cylindrical dish이고, 곡률·ridge가 촉각 경계를 만든다.

원본의 `pressed_key_angle=12.5°`는 body의 허용 형상을 생성하는 값이다. OneGrip에서 microswitch를 쓸 때는 이 형상을 그대로 switch stop으로 취급하면 안 된다. switch가 먼저 bottom-out하면 수명이 짧아지므로 다음 순서로 설계해야 한다.

```text
스위치 작동점 → 0.2~0.4 mm 추가 paddle 이동 → shell hard stop
                                      └ switch 허용 overtravel보다 작게
```

세 키가 동시에 움직일 수 있는 shared rocker Variant C는 Lalboard 원리를 따르지 않는다. 중심을 누를 때 좌·우가 함께 내려갈 수 있고, 좌를 눌렀을 때 center에 토크가 전달되므로 OneGrip의 오입력 억제 목표에 불리하다.

## 7. 조립과 유지보수

### 7.1 원본 key cluster

- side key 4개를 각 V-pivot well에 배치한다.
- center key의 두 post를 guide hole에 넣는다.
- 원본에서는 자석이 키를 유지하므로 key 고정 나사가 없다.
- IR LED/PT가 장착된 PCB는 cluster 아래에서 삽입하며 body의 screw/nut 구조로 고정한다.
- front mount clip과 뒤쪽 두 attachment가 cluster를 3점에서 지지한다.

### 7.2 원본 6자유도 조절

README와 생성 코드를 함께 확인하면 cluster마다 3개의 조절식 standoff가 있다.

- front / back-left / back-right 3점 지지
- 나사 길이 preset: 7, 11 mm
- base 높이 preset: 4, 6, 8, 14, 20 mm
- 인쇄 나사 pitch: 1.4 mm
- cluster 쪽 직육면체 자석: 1/8 × 1/8 × 1/16 inch, 즉 3.175 × 3.175 × 1.5875 mm
- 지지 나사 끝: 직경 5 mm 구형 자석을 받는 socket
- 3점 높이를 각각 바꾸면 제한된 범위에서 cluster의 위치와 자세를 6자유도로 조절
- lock nut로 높이 설정 후 유격과 회전을 잠금
- 자석식이므로 cluster만 들어내도 지지대 설정은 보존됨

이 기구는 탁상형 Lalboard에는 유용하지만, OneGrip의 좁고 수직인 grip 안에는 부품 수와 두께가 과도하다.

### 7.3 OneGrip용 조절 구조로 단순화

V1에는 Lalboard 3점 ball-magnet mount를 복제하지 않는다.

- 손가락 하나당 하나의 완성 cartridge
- cartridge 뒤에 세로 slot 2개
- M2.5 나사 2개로 본체 wall에 고정
- 전후 조절 총 16 mm, 즉 기준에서 ±8 mm
- 각도는 별도 wedge preset `-8° / 0° / +8°`로 시작
- 나중 revision에서 톱니형 sector + clamp screw로 연속 ±8° 조절
- cartridge만 교체 가능하게 하여 grip 본체를 재출력하지 않음

snap-fit 단독 고정은 반복 lateral 입력에서 헐거워질 수 있으므로 사용하지 않는다.

## 8. FDM 최소 형상 분석

### 8.1 공식 출력 설정

공식 `configs/*.3mf` 내부 PrusaSlicer 설정에서 다음을 확인했다.

- 0.4 mm nozzle
- layer height 0.1 mm
- PLA, 215 °C / bed 60 °C
- extrusion width 0.45 mm, external 0.39 mm
- 2 perimeters
- 30% cubic infill
- cluster와 finger center/short/tall key는 support off
- 첫 층 0.2 mm
- cluster v2는 뒤집어서 출력하여 key-well 상단을 평평하게 만드는 방향

README는 대부분 매우 불투명한 PLA를 권하고, 강도·내열이 필요한 ball-head screw 등 일부는 polycarbonate 계열을 요구한다. 이는 광학 검출을 쓰는 원본 조건이다. OneGrip는 광학 센서가 없으므로 불투명 PLA 조건은 필요 없고 PETG를 주재료로 사용할 수 있다.

### 8.2 원본에서 가장 민감한 형상

| 형상 | 원본값 | 0.4 mm 노즐 PETG 판단 |
|---|---:|---|
| retaining ridge | 0.3 mm | 한 extrusion line보다 작아 그대로 복제 금지 |
| pivot/stem 두께 | 1.8 mm | 출력은 가능하나 반복 하중·layer 방향에 민감 |
| groove 깊이 | 0.7 mm | 가능하지만 stringing과 elephant foot 보정 필요 |
| groove 폭 | 0.75 mm | 가능하지만 청소/후가공 필요 가능성 큼 |
| stem–guide 전체 차이 | 0.3 mm | PETG에는 너무 빡빡할 수 있음 |
| nut cavity 희생 천장 | 0.2 mm | 한 층을 뚫어내는 원본용 bridge trick |

### 8.3 OneGrip CAD의 안전한 시작 최소값

다음은 Lalboard 원본값이 아니라 OneGrip의 0.4 mm nozzle, 0.2 mm layer PETG prototype용 시작값이다.

| 항목 | 권장 시작값 |
|---|---:|
| 일반 구조벽 | 1.6 mm 이상, 하중부 2.0–2.4 mm |
| 독립 pivot shaft | Ø2.8–3.0 mm |
| pivot hole diametral clearance | 0.40–0.60 mm |
| 직선 guide 한쪽 clearance | 0.25–0.35 mm |
| moving paddle–shell 한쪽 gap | 0.35–0.50 mm |
| retaining lip | 두께 0.8 mm 이상, 높이 0.8 mm 이상 |
| hard-stop 접촉 폭 | 1.5 mm 이상 |
| M2.5 insert 주변 최소 육厚 | insert 외경 밖 1.5 mm 이상 |
| 긴 paddle 뿌리 두께 | 2.0–2.4 mm + fillet R1.0 이상 |
| 배선 통로 | 내경 2.5–3.0 mm 또는 3 × 4 mm 사각 |

이 값들은 프린터별 tolerance coupon으로 반드시 다시 보정한다. 같은 STL을 PLA에서 PETG로 바꾸면 마찰, 수축, stringing이 달라진다.

## 9. OneGrip에 적용할 기구 결론

### 채택할 원리

- `CENTER`와 `LEFT/RIGHT`를 완전히 독립된 세 부품으로 분리
- 중앙 pad가 손끝의 기준점과 center input을 겸함
- 좌우는 center 위에서 손끝 roll로 누르는 짧은 lateral paddle
- 좌우 각각 독립 로컬 pivot
- 오목한 접촉면과 촉각 ridge
- key마다 독립 hard stop
- cartridge 단위 교체
- 손가락별 위치·각도 preset

### 버릴 원리

- 북·남 두 방향키
- IR LED / phototransistor
- magnetic sensing
- 자석을 이용한 key return과 키 유지
- finger-cluster 전용 PCB
- 3점 ball-magnet 6DOF mount
- 0.3 mm retaining ridge와 0.15 mm/side의 빡빡한 원본 공차
- polycarbonate 인쇄 나사

### V1 권장 구조

OneGrip V1은 **Lalboard-style independent paddles**, 즉 Variant B가 가장 타당하다.

```text
cartridge shell
├─ LEFT paddle ─ local pivot ─ switch L ─ shell hard stop
├─ CENTER pad ─ dual guide ─ switch C ─ shell hard stop
├─ RIGHT paddle ─ local pivot ─ switch R ─ shell hard stop
└─ wiring exit + strain relief
```

다만 “Lalboard-style”은 원본 형상을 축소 복사한다는 뜻이 아니라, 세 입력을 독립된 운동쌍으로 분리한다는 뜻이다.

## 10. OneGrip P0에서 확인해야 할 치수

원본에서 기계적으로 검증된 값은 `center travel 1.7 mm`, `side rotation 12.5°`, `center cap Ø15 mm`, `side cap width 13 mm`다. 하지만 OneGrip는 수직 그립, 운동장애 사용자, 일반 microswitch라는 조건이 다르므로 다음 세트를 한 finger fixture에서 비교해야 한다.

| parameter | P0-1 | P0-2 | P0-3 |
|---|---:|---:|---:|
| center pad 폭 | 9 mm | 10 mm | 11 mm |
| center 총 이동 | 0.8 mm | 1.2 mm | 1.6 mm |
| side paddle 유효 회전 | 6° | 9° | 12° |
| side 접촉면과 center 가장자리 gap | 1.0 mm | 1.5 mm | 2.0 mm |
| center concavity depth | 0.5 mm | 0.8 mm | 1.1 mm |

선정 기준은 원본과 닮은 정도가 아니라, 손끝 중심 이동 1–2 mm 이내에서 L/C/R 각각 30회 입력 시 다음을 만족하는지다.

- 단일 입력 정확도 95% 이상
- 인접 오입력 5% 미만
- 눌렀다 놓은 후 100% 복귀
- switch가 hard stop 역할을 하지 않음
- ring/pinky에서 과도한 힘이나 통증 없음

## 11. Apache-2.0 라이선스와 attribution

### 11.1 확인 사실

공식 `lalboard` 저장소 루트 `LICENSE`와 각 Python 소스 상단에는 다음이 명시돼 있다.

- `Copyright 2019 Google LLC` 또는 파일에 따라 `Copyright 2020 Google LLC`
- Apache License, Version 2.0

분석한 `v2.5.1` checkout에는 별도 `NOTICE` 파일이 없다. `lalboard_stls` artifact 저장소에도 별도 `LICENSE`가 보이지 않지만, 본 저장소가 이를 공식 `stls` 서브모듈로 참조하며 이 출력물은 Apache-2.0 생성 소스에서 만들어졌다. 안전하게 배포하려면 artifact도 Lalboard의 Apache-2.0 object form으로 취급하고 부모 저장소의 저작권·라이선스를 함께 제공한다.

### 11.2 실제 geometry/code를 복사·변형할 때 해야 할 일

Apache-2.0 제4조에 따라 최소한 다음을 지킨다.

1. 배포물 수령자에게 Apache-2.0 전문 사본을 제공한다.
2. 수정한 파일에는 눈에 띄게 수정 사실을 표시한다.
3. 원본의 관련 copyright, patent, trademark, attribution notice를 유지한다.
4. upstream `NOTICE`가 있으면 그 내용을 유지해야 하나, 조사한 버전에는 `NOTICE`가 없다.
5. `Lalboard`나 `Google` 명칭을 제품 보증·제휴처럼 표현하지 않는다. 라이선스는 상표 사용권을 주지 않는다.

Apache-2.0은 수정 소스 전체 공개나 동일 라이선스 적용을 강제하는 copyleft 라이선스는 아니다. 그러나 가져온 원본 부분에 대한 위 의무는 남는다. 또한 특허소송을 제기하는 경우 라이선스의 특허 허여가 종료될 수 있는 조항이 있다.

### 11.3 OneGrip 저장소 권장 파일 구성

실제 저장소에는 다음을 포함했다.

```text
THIRD_PARTY_LICENSES/
└─ lalboard-Apache-2.0.txt               # Apache-2.0 전문
NOTICE-THIRD-PARTY.md                    # 실제 attribution
references/reference-lock.json          # 커밋과 SHA-256 잠금
references/fetch_lalboard_references.ps1 # 읽기 전용 스냅샷 재생성·검증
cad/finger-input-v1/THIRD_PARTY_NOTICES.md
```

OneGrip 자체 라이선스는 프로젝트 소유자가 별도로 선택해야 하므로 이 작업에서 임의로 부여하지 않았다.

이 저장소에 실제 반영한 문구는 `NOTICE-THIRD-PARTY.md`에 있다. 핵심은
형상이나 코드를 가져왔다고 오해될 수 있는 `adapted from` 대신, 기술 조사
대상임을 정확히 밝히는 것이다.

```text
The OneGrip Play finger-input design process reviewed the official
lalboard project:
https://github.com/JesusFreke/lalboard

lalboard copyright 2019–2020 Google LLC.
Licensed under the Apache License, Version 2.0.

OneGrip's CAD, source, and exported geometry are original and do not
contain copied Lalboard meshes or Python geometry. Lalboard was a design
reference for independent motion pairs and per-finger adjustment.
```

STL/STEP/3MF에는 주석을 넣기 어려우므로, 파일과 항상 함께 배포되는 README와 third-party notice에 수정 사실을 적고 파일명 또는 metadata에 `derived-from-lalboard`를 표시한다.

### 11.4 원리만 참고하고 geometry는 독립 생성할 때

Lalboard 파일의 vertex, sketch, 생성 코드, 고유 치수를 복사하지 않고 “중앙 고정 + 독립 lateral paddles”라는 아이디어만 참고하여 새 CAD를 만들었다면 파생저작물 판단은 달라질 수 있다. 그래도 공모전의 선행기술 공개와 투명성을 위해 기술적 영감의 출처는 밝히는 것이 좋다. 이는 법률 자문이 아니며, 상용화·특허출원 전에는 별도 검토가 필요하다.

## 12. 최종 판단

Lalboard가 OneGrip에 주는 가장 중요한 답은 “작은 공간에 세 기능을 우겨 넣는 법”이 아니라 다음이다.

> 손가락 끝의 기준 위치는 거의 고정하고, 중앙 직선 입력과 좌우 roll 입력을 서로 다른 guide와 pivot에 배분한다.

따라서 OneGrip의 V1 최종 후보는 shared rocker가 아니라 **독립 3-paddle cartridge**다. 중앙 pad는 dual-guide, 좌우는 각자 local pivot, 세 switch는 각자 hard stop을 가져야 한다. 원본의 자석·광학·PCB·정밀 0.1 mm 출력 조건은 일정과 제조 조건에 맞지 않으므로 제거하되, 이 운동학적 분리는 유지한다.

## 참고 링크

- [Lalboard 공식 저장소](https://github.com/JesusFreke/lalboard)
- [Lalboard 공식 출력물 저장소](https://github.com/JesusFreke/lalboard_stls)
- [Lalboard README의 키·조절 구조 설명](https://github.com/JesusFreke/lalboard/blob/1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a/README.md)
- [Lalboard 프로젝트 로그](https://hackaday.io/project/178232-lalboard-ergonomic-keyboard)
- [Apache License 2.0 전문 및 재배포 조건](https://www.apache.org/licenses/LICENSE-2.0)
