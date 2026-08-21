"""후보 axis 안에 대한 cap/opening/holder/screw 평가 (READ ONLY, 계산 전용)."""
import math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from axis_opt import *

SCREW_B = dict(pt=np.array([0.0, -14.45, 23.07]), dir=np.array([1.0, 0.0, 0.0]),
               r=3.5, xlo=-6.0, xhi=10.0)
CAP_BOT = SHELL_WALL - 0.2 - CAP_CLR      # 2.6 : 캡 밑면 깊이(n0 기준)
_SOLID = None


def solid():
    global _SOLID
    if _SOLID is None:
        _SOLID = Solid(load_tris("Joystick_1_baseline", "Joystick_2_baseline"))
    return _SOLID


def n0frame(i):
    return frame(N0[i])


def to_open(i, pts):
    """월드점 -> 개구부(원래 축 n0) 국소좌표 (x, y, depth)."""
    u0, v0, z0 = n0frame(i)
    d = np.asarray(pts) - P[i]
    return np.stack([d @ u0, d @ v0, -(d @ z0)], axis=-1)


def bore_vs_opening(i, a):
    """개구부를 그대로 둘 때, 새 축의 4.5 보어가 8x8 개구부 벽에 대해 갖는 최소 여유."""
    u, v, z = frame(a)
    worst = 9.9
    for s in np.linspace(0.0, SW_FRONT, 60):
        for th in np.linspace(0, 2 * math.pi, 72, endpoint=False):
            pt = P[i] - z * s + (u * math.cos(th) + v * math.sin(th)) * (BORE / 2)
            x, y, d = to_open(i, pt)
            if -0.05 <= d <= SHELL_WALL + 0.05:
                worst = min(worst, CAP_W / 2 - max(abs(x), abs(y)))
    return worst


def holder_front_vs_cap(i, a):
    """개구부 유지 시, holder 앞면이 캡 이동공간(깊이<2.6)을 침범하는가. 양수=여유."""
    u, v, z = frame(a)
    worst = 9.9
    g = np.linspace(-HOLDER_W / 2, HOLDER_W / 2, 25)
    for p in g:
        for q in g:
            pt = P[i] - z * BLANK_FROM + u * p + v * q
            x, y, d = to_open(i, pt)
            if abs(x) <= CAP_W / 2 and abs(y) <= CAP_W / 2:
                worst = min(worst, d - CAP_BOT)
    return worst


def holder_box(i, a):
    return obb(P[i], a, HOLDER_W, BLANK_TO - BLANK_FROM, BLANK_FROM)


def screw_gap(i, a):
    """holder OBB 와 유한 원기둥(나사 B 보스) 사이 정확 최소거리."""
    c, A, h = holder_box(i, a)
    ap, ad = SCREW_B["pt"], SCREW_B["dir"]
    rad, xlo, xhi = SCREW_B["r"], SCREW_B["xlo"], SCREW_B["xhi"]

    def f(w):
        x = c + A.T @ (w[:3] * h)
        d = x - ap
        s = float(np.dot(d, ad))
        dr = max(np.linalg.norm(d - s * ad) - rad, 0.0)
        ds = max(xlo - s, 0.0, s - xhi)
        return dr * dr + ds * ds

    best = 1e9
    for seed in ((0, 0, 0), (1, 1, 1), (-1, -1, -1), (1, -1, 1), (-1, 1, -1)):
        r = minimize(f, np.array(seed, float), method="L-BFGS-B",
                     bounds=[(-1, 1)] * 3, options={"ftol": 1e-16})
        best = min(best, r.fun)
    return math.sqrt(max(best, 0.0))


_TRIS = None


def _tris():
    global _TRIS
    if _TRIS is None:
        _TRIS = load_tris("Joystick_1_baseline", "Joystick_2_baseline")
    return _TRIS


def dist_to_surface(pt):
    """점에서 쉘 외피 메시까지의 최소거리 (부호 없음)."""
    T = _tris()
    A, B, C = T[:, 0], T[:, 1], T[:, 2]
    AB, AC, AP = B - A, C - A, pt - A
    d1 = (AB * AP).sum(1); d2 = (AC * AP).sum(1)
    BP = pt - B; d3 = (AB * BP).sum(1); d4 = (AC * BP).sum(1)
    CP = pt - C; d5 = (AB * CP).sum(1); d6 = (AC * CP).sum(1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    den = va + vb + vc
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(np.abs(den) > 1e-20, vb / den, 0.0)
        w = np.where(np.abs(den) > 1e-20, vc / den, 0.0)
    v = np.clip(v, 0, 1); w = np.clip(w, 0, 1)
    s = v + w
    over = s > 1
    v = np.where(over, v / np.where(s > 0, s, 1), v)
    w = np.where(over, w / np.where(s > 0, s, 1), w)
    Q = A + AB * v[:, None] + AC * w[:, None]
    return float(np.sqrt(((pt - Q) ** 2).sum(1)).min())


def holder_corners(i, a):
    c, A, h = holder_box(i, a)
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                out.append(c + A.T @ (np.array([sx, sy, sz], float) * h))
    return np.array(out)


def split_overshoot(i, a):
    """분할면 X=0 을 얼마나 넘는가 (양수 = 넘음 -> clip 필요)."""
    xs = holder_corners(i, a)[:, 0]
    return float(max(xs)) if DOM[i] else float(-min(xs))


def protrusion(i, a):
    """holder 앞면이 쉘 외곽을 뚫고 나오는 최대 깊이(mm). 0 이면 안전."""
    S = solid(); u, v, z = frame(a)
    g = np.linspace(-HOLDER_W / 2, HOLDER_W / 2, 9)
    worst = 0.0; nout = 0; tot = 0
    for p in g:
        for q in g:
            tot += 1
            base = P[i] - z * BLANK_FROM + u * p + v * q
            if S.inside(base):
                continue
            nout += 1
            worst = max(worst, dist_to_surface(base))
    return worst, nout / tot


def rear_in_wall(i, a):
    """holder 후방(깊이 10~12.5)이 쉘 벽 재료에 박혀 있는 비율 (배선/후면 접근성)."""
    S = solid(); u, v, z = frame(a)
    g = np.linspace(-POCKET / 2, POCKET / 2, 5)
    tot = hit = 0
    for s in (10.5, 11.5, 12.4):
        for p in g:
            for q in g:
                tot += 1
                if S.inside(P[i] - z * s + u * p + v * q):
                    hit += 1
    return hit / tot
