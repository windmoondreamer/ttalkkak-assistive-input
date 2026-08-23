# SZH-EK056 web/photo mechanical reference

## 결론

```text
EXACT SZH-EK056 SOURCE FOUND = NO
MODEL TYPE = REBUILT WEB-REFERENCE
PCB SIZE = 34.5 x 26.0 x 1.6 mm nominal
MOUNTING HOLE PATTERN = 26.50 x 19.45 mm PHOTO-DERIVED
JOYSTICK CENTER = PCB datum (+0.40, +2.00) mm PHOTO-DERIVED
X POT ENVELOPE = 5.2 x 13.2 mm at (+11.1, +2.0) mm PHOTO-DERIVED
Y POT ENVELOPE = 10.5 x 5.0 mm at (+0.5, +10.6) mm PHOTO-DERIVED
PIVOT / SHAFT DATA = pivot Z 11.5, shaft dia 4.8, max tilt 25 deg INFERRED
HEADER DATA = 1x5, 2.54 mm pitch; X -23.2..-14.4 mm nominal envelope
SUITABLE FOR GENERAL PACKAGING = YES
SUITABLE FOR MOUNTING DESIGN = YES — adjustable/prototype mounting only
SUITABLE FOR SUB-0.5 mm FINAL COLLISION = NO
```

이 결과는 OneGrip production assembly를 불러오지 않고 SZH-EK056 reference만 직렬·저메모리로 생성한 것이다. N1/N2, finger carrier, thumb, shell, wiring 및 production boolean은 수정하지 않았고 충돌 판정도 수행하지 않았다.

## 중단 작업 복구

요청에 적힌 `build123d/szh_photo_measure.py`는 실제로 `lower_adapter/local_cad/build123d/szh_photo_measure.py`에 남아 있었다. 복구 시점에는 image load, crop/zoom, grid, autolevel, homography/apply helper까지 구현되어 있었고, 픽 좌표나 mm 결과 파일은 없었다.

로컬 원본은 `lower_adapter/local_cad/reference/szh_ek056_web/`에서 확인했다.

- `icbanq_main.jpg`: SZH-EK056 SKU와 직접 연결된 DeviceMart 워터마크 사진. exact product-family evidence이나 사선 사진이라 정밀 평면 측정에는 쓰지 않았다.
- `ps_Joystick-Module-Connections-1.jpg`, `ps_Joystick-Module-Back.jpg`: black-PCB KY-023/Keyes 계열과 시각적으로 일치하는 near-orthographic 상·하면. 호모그래피 측정의 주 자료다.
- 나머지 ProtoSupplies 사진: 높이와 부품 정체 확인용 matching reference다.
- `mantech_KY023.pdf`, `atrinelec_joystick.pdf`: generic KY-023 문서다. 정확한 SZH-EK056 도면이 아니다.
- `D202X_R4.pdf`: 대형 JH-D202X 산업용 조이스틱 문서로 판정하여 모든 목표 치수에서 제외했다.

기존 crop/grid는 보존했고, 이어서 다음 재현 가능한 결과를 생성했다.

- `lower_adapter/local_cad/reference/szh_ek056_web/measure/szh_photo_measurements.json`
- `top_annotated.png`, `bottom_annotated.png`
- `top_rectified_34p5x26.png`, `bottom_rectified_34p5x26.png`

재생성 명령:

```powershell
.venv-build123d\Scripts\python.exe lower_adapter\local_cad\build123d\szh_photo_measure.py analyze lower_adapter\local_cad\reference\szh_ek056_web lower_adapter\local_cad\reference\szh_ek056_web\measure
.venv-build123d\Scripts\python.exe build123d_workbench\szh_ek056_web_reference.py
```

## 공개 CAD 조사

정상적으로 접근 가능한 exact SZH-EK056 STEP/STP/SolidWorks/KiCad mechanical model은 찾지 못했다.

| 후보 | 결과 | 채택 여부 |
|---|---|---|
| [DeviceMart SZH-EK056](https://www.devicemart.co.kr/goods/view?no=1287087) | exact SKU 판매 페이지. 대표 이미지는 참조용이며 제조 시기별 hardware revision 변경 가능성을 명시 | SKU/리비전 근거만 채택 |
| [ICbanQ SZH-EK056](https://www.icbanq.com/P008113513) | exact SKU 이미지/판매 페이지, controlled drawing 없음 | 시각 근거만 채택 |
| [GrabCAD KY-023](https://grabcad.com/library/ky-023-joystick-module-1) | 공개 페이지 접근이 403. 우회하지 않음. 공개 인덱스상 제작자도 1:1이 아니며 보유품 간 홀 간격 차이를 경고 | 제외 |
| [Thingiverse KY-023 mockup](https://www.thingiverse.com/thing:7014864) | rough mesh, gold pins 및 치수 provenance 없음 | 제외 |
| [Printables KY-023 rough-in](https://www.printables.com/model/498437-arduino-ky-023-joystick-module-mockup) | 제작자 보유품용 rough-in, 제조 편차 경고 | 제외 |
| [EasyEDA KY-023 explore](https://easyeda.com/index.php/explore/ky-023) / [OSHWLab project](https://oshwlab.com/adrirobot/ky-023-xy-axis-joystick-module) | PCB 프로젝트는 있으나 신뢰 가능한 enclosure STEP/기계 도면 없음 | 제외 |
| [Soldered joystick breakout hardware](https://github.com/SolderedElectronics/Joystick-2-axis-with-pushbutton-breakout-hardware-design) | STEP은 있으나 38 x 38 mm 보라색 PCB revision으로 target과 다름 | body-class 참고만 가능, 모델 입력에서는 제외 |

## 치수 계층과 신뢰도

서로 다른 KY-023 revision의 수치를 평균하지 않았다. 34.5 x 26 mm를 목표 사진 평면의 한 calibration hypothesis로 고정하고, 다른 revision 수치는 비교 근거로만 남겼다.

### SOURCE-DERIVED VALUES

| 값 | 출처 | 신뢰도 / 사용 |
|---|---|---|
| 34.5 x 26 x 38 mm | [SZH-EK056 SKU-linked reseller listing](https://m.shinsegaetvshopping.com/display/detail/1000332084) | MEDIUM. SKU 연결은 있으나 controlled drawing이 아니다. PCB X/Y와 전체 높이 seed로 사용 |
| 34.0 x 26.0 x 32.0 mm | [Mantech generic KY-023 PDF](https://www.mantech.co.za/Datasheets/Products/KY-023-220909A.pdf) | LOW-MEDIUM. 시각적으로 matching이나 exact SKU가 아니다. 같은 PDF의 다른 페이지에 40 x 26 x 32 mm가 있어 평균하지 않음 |
| 34 x 39 x 26 mm | [Joy-IT COM-KY023JM](https://www.joy-it.net/en/products/COM-KY023JM) | LOW for target. 축 순서/리비전 차이 증거로만 사용 |
| PCB 40 x 22 mm | [ProtoSupplies joystick module](https://protosupplies.com/product/joystick-module/) | LOW for target. 사진은 유용하지만 해당 페이지 치수는 다른 board revision임을 보여줌 |
| 5-pin, 2.54 mm interface | SKU/generic product descriptions and visible pin row | HIGH for count/pitch |

### PHOTO-DERIVED VALUES

PCB 중심을 `(0,0)`, PCB 상면을 `Z=0`, rectified top image의 오른쪽을 `+X`, 위쪽을 `+Y`로 정의했다. 수치는 script 결과에 소수점이 더 있어도 실질 정확도를 대략 0.5 mm class 이상으로 주장하지 않는다.

| 항목 | 채택값 | 신뢰도 |
|---|---:|---|
| PCB calibration plane | 34.5 x 26.0 mm | MEDIUM hypothesis |
| hole centres | `(-12.00,+9.95)`, `(+14.50,+9.95)`, `(-12.00,-9.50)`, `(+14.50,-9.50)` mm | MEDIUM |
| hole pitch X/Y | 26.50 x 19.45 mm | MEDIUM; top/bottom 사진 상호 확인 |
| nominal hole diameter | 3.0 mm | LOW-MEDIUM |
| joystick centre | `(+0.40,+2.00)` mm | MEDIUM |
| central gimbal plan envelope | 17.5 x 16.6 mm | MEDIUM |
| X potentiometer | 5.2 x 13.2 mm, centre `(+11.1,+2.0)` | MEDIUM |
| Y potentiometer | 10.5 x 5.0 mm, centre `(+0.5,+10.6)` | LOW-MEDIUM; boot에 일부 가림 |
| push switch housing | 10.5 x 7.0 mm, centre `(+0.5,-9.2)` | MEDIUM |
| header pin plan envelope | 약 8.8 x 12.2 mm | LOW-MEDIUM |

### INFERRED VALUES

- PCB thickness: 1.6 mm.
- central gimbal height: 11.0 mm.
- X/Y pot height: 8.5 mm; push-switch housing height: 5.0 mm.
- pivot: `(+0.4,+2.0,+11.5)` mm.
- shaft: diameter 4.8 mm, nominal top `Z=25.0` mm.
- cap maximum diameter 22 mm, overall top `Z=38.0` mm.
- motion: all-azimuth 25 degree seed. `MOVING_CLEARANCE_ENVELOPE`는 중립 cap 반경에 `(Z-pivotZ) * sin(25 deg)`를 더한 축대칭 sweep 근사다.

위 값은 실물 또는 exact actuator drawing이 나오면 반드시 교체해야 한다. script 최상단에 독립 parameter와 source/confidence 주석으로 분리했다.

### UNKNOWN VALUES

- 현재 입고되는 SZH-EK056 hardware revision의 실제 PCB 외곽, hole diameter 및 hole-centre 공차.
- 실물 shaft 직경/길이, 실제 pivot Z, 최대 기울기 및 cap 조립 공차.
- pot/switch/header의 정확한 Z 외곽, pin bend, 납땜 돌출과 mating connector 서비스 공간.
- joystick press travel, internal moving parts 및 pressed-state envelope.
- 38 mm 표기가 cap 포함 실제 수직 높이인지 판매자 nominal package height인지 여부.

## 생성 모델

`SZH_EK056_WEB_REFERENCE.step`에는 다음 라벨을 분리했다.

- `NOMINAL_REFERENCE`: PCB, 4 holes, X/Y POT, central gimbal, push switch, shaft, removable cap, 1x5 header.
- `STATIC_CLEARANCE_ENVELOPE`: neutral state base/handle packaging bound.
- `MOVING_CLEARANCE_ENVELOPE_25DEG_INFERRED`: 25 degree all-azimuth cap/shaft swept reference.

Nominal bbox는 약 `(-23.2,-13.0,-1.6)`에서 `(+17.25,+13.1,+38.0)` mm다. moving envelope의 최대 반경 때문에 전체 STEP bbox는 약 `(-23.3,-17.3,-2.8)`에서 `(+19.7,+21.3,+38.0)` mm다.

## 사용 판정

- `SUITABLE FOR GENERAL PACKAGING = YES`: static/moving envelope를 이용한 coarse packaging과 공간 예산에 적합하다.
- `SUITABLE FOR MOUNTING DESIGN = YES — PROTOTYPE ONLY`: slot, oversized pocket, replaceable adapter처럼 조정 가능한 초기 시제품에는 사용할 수 있다. 고정 금형/양산 홀 패턴 release에는 실물 캘리퍼 확인이 필요하다.
- `SUITABLE FOR SUB-0.5 mm FINAL COLLISION = NO`: 사진 보정, revision 불확실성, 추정 Z/tilt 때문에 금지한다.

이 단계에서 STOP하며 OneGrip geometry에 삽입하거나 production 충돌 판정을 수행하지 않는다.
