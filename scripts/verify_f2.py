"""F2 재생성 결과를 실제 CAD 형상에서 검증한다 (READ ONLY 계산)."""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from axis_opt import (Solid, load_tris, sat, exact_gap, obb, frame, P, N0, NAMES, DOM,
                      SW, POCKET, CAP_W, BORE, HOLDER_W, SHELL_WALL)

# ---- F2 확정 축 (FS 에 기록된 값과 동일) ----
AX = [np.array(v, float) for v in (
    (-0.851033, -0.500047, -0.160298),
    (-0.393870, -0.571110, -0.720208),
    (-0.069850, -0.997555, 0.002429),
    (0.024161, -0.968017, -0.249718))]

LIP = 2.3
SW_FRONT = SHELL_WALL + LIP          # 4.5
SW_REAR = SW_FRONT + 6.0             # 10.5
SEAT_TO = SW_REAR + 0.2              # 10.7
BLANK_FROM = 2.8
BLANK_TO = SEAT_TO + 1.0             # 12.5

_S = {}


def shell(which="both"):
    if which not in _S:
        names = {"both": ("JfD_v3", "JaD_v3"), "dom": ("JfD_v3",), "opp": ("JaD_v3",)}[which]
        _S[which] = Solid(load_tris(*names))
    return _S[which]


def switch_box(i, size=SW, length=SW, front=SW_FRONT):
    return obb(P[i], AX[i], size, length, front)


def sample_box(box, n=7):
    c, A, h = box
    out = []
    g = [np.linspace(-1, 1, n) for _ in range(3)]
    for a in g[0]:
        for b in g[1]:
            for d in g[2]:
                out.append(c + A.T @ (np.array([a, b, d]) * h))
    return out
