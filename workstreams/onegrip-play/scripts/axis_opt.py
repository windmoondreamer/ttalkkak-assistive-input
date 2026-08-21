"""INDEX switch/holder axis 최적화 — 정확 SAT + 정확 OBB 최소거리 (READ ONLY, 계산 전용).

buttonn center / pitch / cap / 6x6x6 switch / 3+1 ownership 는 전부 고정.
holder axis 만 local surface normal 에서 reference axis 쪽으로 t 만큼 완화한다.
"""
import math
import numpy as np
from scipy.optimize import minimize

# ---- 승인된 버튼 배치 (변경 금지) ----
BTN = [
    ("I1", (-22.224, -17.494, 9.000), (-0.9291, -0.2385, -0.2828), True),
    ("I2", (-15.970, -26.208, 9.000), (-0.4724, -0.7368, -0.4838), True),
    ("I3", (-5.496, -29.325, 9.000), (-0.0383, -0.9556, -0.2921), True),
    ("I4", (5.496, -29.325, 9.000), (0.0383, -0.9556, -0.2921), False),
]
PAIRS = [(0, 1), (1, 2), (0, 2), (2, 3), (0, 3), (1, 3)]
KEY_PAIRS = [(0, 1), (1, 2), (0, 2), (2, 3)]

SW = 6.0            # 실물 스위치 몸체 6 x 6 x 6
SHELL_WALL = 3.0
LIP = 0.8
SW_FRONT = SHELL_WALL + LIP          # 3.8 : 스위치 앞면 깊이
POCKET = 6.4
CAP_W = 8.0                          # shell opening = cap 공칭
CAP_CLR = 0.2
CAP_H = 4.0
BORE = 4.5
HOLDER_W = POCKET + 2 * 3.0          # 12.4
BLANK_FROM, BLANK_TO = 2.8, 12.5

N0 = [np.array(n, float) / np.linalg.norm(n) for _, _, n, _ in BTN]
P = [np.array(p, float) for _, p, _, _ in BTN]
NAMES = [b[0] for b in BTN]
DOM = [b[3] for b in BTN]

REF_DOM = N0[0] + N0[1] + N0[2]
REF_DOM = REF_DOM / np.linalg.norm(REF_DOM)
REF_ALL = sum(N0)
REF_ALL = REF_ALL / np.linalg.norm(REF_ALL)


def axis(i, t, ref=None):
    ref = REF_DOM if ref is None else ref
    a = (1.0 - t) * N0[i] + t * ref
    return a / np.linalg.norm(a)


def dev(i, t, ref=None):
    return math.degrees(math.acos(np.clip(np.dot(N0[i], axis(i, t, ref)), -1.0, 1.0)))


def frame(a):
    z = a / np.linalg.norm(a)
    x = np.cross([0.0, 0.0, 1.0], z)
    x /= np.linalg.norm(x)
    return x, np.cross(z, x), z


def obb(p, a, size, length, front):
    """축 a 를 따라 깊이 front 부터 length 만큼 들어간 정사각 단면 박스."""
    u, v, z = frame(a)
    c = np.asarray(p, float) - z * (front + length / 2.0)
    return c, np.array([u, v, z]), np.array([size / 2, size / 2, length / 2])


def sat(A, B):
    """정확 SAT. 반환 (겹침?, 값).  겹치면 값 = 침투깊이(MTD), 아니면 최대 분리간극."""
    (ca, Aa, ha), (cb, Ab, hb) = A, B
    d = cb - ca
    axes = [Aa[i] for i in range(3)] + [Ab[j] for j in range(3)]
    for i in range(3):
        for j in range(3):
            x = np.cross(Aa[i], Ab[j])
            n = np.linalg.norm(x)
            if n > 1e-9:
                axes.append(x / n)
    mtd, best = 1e9, -1e9
    for ax in axes:
        ra = sum(ha[k] * abs(np.dot(Aa[k], ax)) for k in range(3))
        rb = sum(hb[k] * abs(np.dot(Ab[k], ax)) for k in range(3))
        gap = abs(np.dot(d, ax)) - (ra + rb)
        best = max(best, gap)
        if gap <= 0:
            mtd = min(mtd, -gap)
    return (False, best) if best > 0 else (True, mtd)


def exact_gap(A, B):
    """두 OBB 사이 정확한 최소거리 (볼록 QP). 겹치면 0."""
    (ca, Aa, ha), (cb, Ab, hb) = A, B

    def f(w):
        x = ca + Aa.T @ (w[:3] * ha)
        y = cb + Ab.T @ (w[3:] * hb)
        return float(np.dot(x - y, x - y))

    best = 1e9
    for seed in ((0, 0, 0, 0, 0, 0), (1, 1, 1, -1, -1, -1), (-1, 1, -1, 1, -1, 1)):
        r = minimize(f, np.array(seed, float), method="L-BFGS-B",
                     bounds=[(-1, 1)] * 6, options={"ftol": 1e-16, "gtol": 1e-14})
        best = min(best, r.fun)
    return math.sqrt(max(best, 0.0))


def switch_boxes(ts, ref=None):
    return [obb(P[i], axis(i, ts[i], ref), SW, SW, SW_FRONT) for i in range(4)]


def clearances(ts, ref=None, pairs=KEY_PAIRS, exact=False):
    B = switch_boxes(ts, ref)
    out = {}
    for i, j in pairs:
        hit, val = sat(B[i], B[j])
        if hit:
            out[(i, j)] = -val
        else:
            out[(i, j)] = exact_gap(B[i], B[j]) if exact else val
    return out


def min_clear(ts, ref=None, exact=False):
    return min(clearances(ts, ref, exact=exact).values())


# ================= 기하 검사 유틸 (READ ONLY) =================
import json as _json, os as _os

_DUMP = _os.path.join(_os.path.dirname(__file__), "..", "cad_dump")


def load_tris(*names):
    T = []
    for n in names:
        with open(_os.path.join(_DUMP, f"mesh_{n}.json"), encoding="utf-8") as f:
            T += _json.load(f)["tris"]
    return np.array(T, float)


class Solid:
    """광선 패리티 point-in-solid (3방향 다수결)."""
    DIRS = ((0.3714, 0.5571, 0.7428), (-0.8018, 0.2673, 0.5345), (0.4082, -0.8165, 0.4082))

    def __init__(self, tris):
        self.V0, V1, V2 = tris[:, 0], tris[:, 1], tris[:, 2]
        self.E1, self.E2 = V1 - self.V0, V2 - self.V0

    def inside(self, pt):
        votes = 0
        for dv in self.DIRS:
            dv = np.array(dv, float); dv /= np.linalg.norm(dv)
            pv = np.cross(dv, self.E2); det = (self.E1 * pv).sum(1)
            ok = np.abs(det) > 1e-12
            inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
            tv = pt - self.V0
            u = (tv * pv).sum(1) * inv
            qv = np.cross(tv, self.E1)
            v = (dv * qv).sum(1) * inv
            t = (self.E2 * qv).sum(1) * inv
            hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-7)
            votes += int(hit.sum() % 2 == 1)
        return votes >= 2


def cyl_gap(box, axis_pt, axis_dir, radius, xlo, xhi):
    """OBB 와 유한 원기둥 사이 최소거리 (0 이면 간섭)."""
    c, A, h = box
    ad = np.asarray(axis_dir, float); ad /= np.linalg.norm(ad)
    ap = np.asarray(axis_pt, float)

    def f(w):
        x = c + A.T @ (w[:3] * h)
        s = min(max(w[3], xlo), xhi)
        y = ap + ad * s
        d = x - y
        perp = d - np.dot(d, ad) * ad
        r = np.linalg.norm(perp)
        return max(r - radius, 0.0) ** 2 + 0.0

    best = 1e9
    for seed in ((0, 0, 0, 0.0), (1, 1, 1, xlo), (-1, -1, -1, xhi), (1, -1, 0, 0.0)):
        r = minimize(f, np.array(seed, float), method="L-BFGS-B",
                     bounds=[(-1, 1)] * 3 + [(xlo, xhi)], options={"ftol": 1e-16})
        best = min(best, r.fun)
    return math.sqrt(max(best, 0.0))
