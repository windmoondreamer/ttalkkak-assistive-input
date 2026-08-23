"""OneGrip Play — 로컬 인체공학 외피 파라미터 (build123d).

편집 대상은 **W2 인체공학 파라미터뿐**이다.
FROZEN_* 값은 Onshape 에서 검증된 기계 관계이며 **참조/검증용**이다.
STEP 레퍼런스가 있을 때는 언제나 STEP 형상이 우선이고, 여기 숫자는
스케일/좌표 검증과 리포트 대조에만 쓴다. 이 값으로 코어를 재건하지 않는다.

단위: mm, deg
"""
from __future__ import annotations

import os

# ===========================================================================
#  경로
# ===========================================================================
HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_CAD = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(LOCAL_CAD))

REFERENCE_DIR = os.path.join(LOCAL_CAD, "reference")
EXPORT_STEP = os.path.join(LOCAL_CAD, "export", "step")
EXPORT_STL = os.path.join(LOCAL_CAD, "export", "stl")
EXPORT_BREP = os.path.join(LOCAL_CAD, "export", "brep")
PREVIEW_DIR = os.path.join(LOCAL_CAD, "preview")
REPORTS_DIR = os.path.join(LOCAL_CAD, "reports")

# 기대하는 동결 레퍼런스 (reference/STEP_EXPORT_REQUEST.md 참조)
REFERENCES = {
    "stock_gimbal": ("STOCK_GIMBAL_REFERENCE.step", True),
    "conformal_core": ("CONFORMAL_CORE_REFERENCE.step", True),
    "assembly": ("ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step", True),
    "onegrip": ("ONEGRIP_REFERENCE.step", False),
    "electronics": ("ELECTRONICS_REFERENCE.step", False),
    "bottom_carrier": ("BOTTOM_CARRIER_REFERENCE.step", False),
}

# ===========================================================================
#  W2 인체공학 파라미터  (편집 대상)
# ===========================================================================
WRIST_PAD_ANGLE = 7.0       # deg.  평가 범위 5 / 7 / 9
WRIST_PAD_LENGTH = 85.0     # mm.   평가 범위 70 / 85 / 100
WRIST_PAD_WIDTH = 86.0      # mm
WRIST_PAD_RADIUS = 16.0     # mm.   평면상 코너 반경
WRIST_ANCHOR_Y = -20.0      # mm.   패드가 시작하는 grip Y

EDGE_FILLET = 3.0           # mm.   사용자 접촉 모서리 (실패 시 2.5 -> 2.0)
FRONT_RAKE = 5.0            # deg.  앞면 기울기 (아래가 앞으로)

# 셸 살 두께 (최종 STEP 과 하중 경로를 보고 조정 가능)
SHELL_WALL = 5.0            # mm.   일반 외피
WRIST_WALL = 6.0            # mm.   손목 접촉면
NECK_WALL = 4.5             # mm.   손목 넥 최소

# 평가용 스윕 (실물 테스트 시 이 값들만 바꾼다)
WRIST_ANGLE_SWEEP = (5.0, 7.0, 9.0)
WRIST_LENGTH_SWEEP = (70.0, 85.0, 100.0)

# ===========================================================================
#  FROZEN — Onshape 에서 검증된 기계 관계 (참조/검증용, 재건용 아님)
# ===========================================================================
# 좌표계: 그립(Joystick) Part Studio 프레임.
FROZEN_SEAT_Z = -67.878507          # 상체 착좌 평면
FROZEN_DECK_Z = -61.878507          # 20도 인체공학 기준면 (= 착좌면 + 6.0)
FROZEN_SOCKET_XY = (0.0, 27.269160)  # 그립 중심축
FROZEN_PIVOT = (0.0, 27.275842, -114.860854)   # 스톡 짐벌 피벗
FROZEN_HAND_REF = (-8.960946, -13.645934, -6.000)  # 중지 버튼행 도심

# 20도 경사. TOP -> -Y.  UP_LOCAL = 그립 좌표에서 본 월드 수직.
FROZEN_TILT_DEG = 20.0
FROZEN_UP_LOCAL = (0.0, 0.3420201433256687, 0.9396926207859084)
FROZEN_U_HAT = (0.0, 0.9396926207859084, -0.3420201433256687)  # 월드 수평(+Y쪽)
FROZEN_GROUND_WORLD_H = -171.326109   # 지면 평면 (월드 수직 좌표)

FROZEN_TRAVEL_DEG = 10.0              # 짐벌 ±10 deg

# 검증 목표 (Onshape W2 결과. 재구성 대상이 아니라 대조용)
TARGET_DECK_TO_HAND = 55.8785         # 경사면 -> HAND_REF
TARGET_GROUND_TO_HAND = 161.0208      # 지면 -> HAND_REF
TARGET_PROTRUSION = 0.0               # 하우징 아래 스톡 돌출
TARGET_WLH = (128.6, 219.7, 139.9)    # 외형 W x L x H
TARGET_WRIST_AREA = 7173.0            # mm2

# ===========================================================================
#  검증 허용 오차
# ===========================================================================
TOL_ANGLE_DEG = 1e-4        # 20.000 / 90.000 판정
TOL_LENGTH_MM = 1e-3        # 좌표 일치
TOL_ROUNDTRIP_VOL = 1e-6    # STEP 왕복 부피 상대 오차
TOL_ROUNDTRIP_BBOX = 1e-6   # STEP 왕복 bbox 절대 오차 (mm)

# ===========================================================================
#  캐시 (정밀 CAD source 로 사용 금지 — 시각 대조 / 충돌 교차검사 전용)
# ===========================================================================
CACHE_DIR = os.path.join(ROOT, "lower_adapter", "cad_dump")
CACHE_MOTION = os.path.join(CACHE_DIR, "motion_configs.npz")
CACHE_STOCK_MESH = os.path.join(CACHE_DIR, "stock_full.npz")
CACHE_CORE_MESH = os.path.join(CACHE_DIR, "conformal_meshes.npz")
CACHE_ERGO_MESH = os.path.join(CACHE_DIR, "ergo_meshes.npz")
CACHE_FRAMES = os.path.join(CACHE_DIR, "stock_frames.json")


def reference_path(key: str) -> str:
    name, _required = REFERENCES[key]
    return os.path.join(REFERENCE_DIR, name)


def missing_references():
    """없는 필수/선택 레퍼런스를 (필수, 선택) 로 나눠 돌려준다."""
    req, opt = [], []
    for key, (name, required) in REFERENCES.items():
        if not os.path.exists(os.path.join(REFERENCE_DIR, name)):
            (req if required else opt).append(name)
    return req, opt

# 공동 keep-out 을 부풀리는 양 [mm]. 0 이면 밴드 경계가 안쪽 loft 면과 정확히
# 겹쳐 OCC 가 두께 0 shell 을 남긴다 (invalid solid -> 이후 boolean 전부 무효).
PROT_EPS = 0.1

# BOTTOM_CARRIER 실측 부피 [mm3] (STEP 레퍼런스, 동결).
FROZEN_CARRIER_VOL = 90177.998830
