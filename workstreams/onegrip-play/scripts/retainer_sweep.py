"""retainer fit clearance sweep — 복셀 기반 (READ ONLY 계산)."""
import sys, os, math, json, time
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from axis_opt import frame, load_tris
from verify_f2 import P, AX, NAMES, BLANK_TO, SW_FRONT

STEP = 0.6
AXv = [frame(AX[i])[2] for i in range(4)]
SCREWB = (np.array([0.0, -14.45, 23.07]), np.array([1.0, 0.0, 0.0]), 3.5, -6.0, 10.0)

T = load_tris("JfD_v4", "JaD_v4")
V0 = T[:, 0]; E1 = T[:, 1] - T[:, 0]; E2 = T[:, 2] - T[:, 0]
A_, B_, C_ = T[:, 0], T[:, 1], T[:, 2]
AB, AC = B_ - A_, C_ - A_
DIRS = np.array([[0.3714, 0.5571, 0.7428], [-0.8018, 0.2673, 0.5345], [0.4082, -0.8165, 0.4082]])
DIRS = DIRS / np.linalg.norm(DIRS, axis=1, keepdims=True)


def inside(pt):
    votes = 0
    for d in DIRS:
        pv = np.cross(d, E2); det = (E1 * pv).sum(1); ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = pt - V0
        u = (tv * pv).sum(1) * inv
        qv = np.cross(tv, E1)
        v = (d * qv).sum(1) * inv
        t = (E2 * qv).sum(1) * inv
        votes += int((ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-7)).sum() % 2 == 1)
    return votes >= 2


def dist_surf(pt):
    APv = pt - A_
    d1 = (AB * APv).sum(1); d2 = (AC * APv).sum(1)
    BPv = pt - B_; d3 = (AB * BPv).sum(1); d4 = (AC * BPv).sum(1)
    CPv = pt - C_; d5 = (AB * CPv).sum(1); d6 = (AC * CPv).sum(1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    den = va + vb + vc
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(np.abs(den) > 1e-20, vb / den, 0.0)
        w = np.where(np.abs(den) > 1e-20, vc / den, 0.0)
    v = np.clip(v, 0, 1); w = np.clip(w, 0, 1)
    s = v + w; over = s > 1
    v = np.where(over, v / np.where(s > 0, s, 1), v)
    w = np.where(over, w / np.where(s > 0, s, 1), w)
    Q = A_ + AB * v[:, None] + AC * w[:, None]
    return float(np.sqrt(((pt - Q) ** 2).sum(1)).min())


def screw_dist(pts):
    ap, ad, r, lo, hi = SCREWB
    d = pts - ap; s = d @ ad
    perp = np.linalg.norm(d - np.outer(s, ad), axis=1)
    return np.sqrt(np.maximum(perp - r, 0) ** 2
                   + np.maximum(np.maximum(lo - s, 0), np.maximum(s - hi, 0)) ** 2)
