"""retainer 를 '홀더 클러스터의 음형'으로 만들었을 때 실제 web 단면을 복셀로 측정한다."""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from axis_opt import frame, obb, load_tris
from verify_f2 import P, AX, NAMES, BLANK_TO

CLR = 0.2                      # 홀더 대비 여유
SCREW_CLR = 1.0
AXv = [frame(AX[i])[2] for i in range(4)]
HOLD = [obb(P[i], AX[i], 12.4 + 2 * CLR, (BLANK_TO - 2.8) + 2 * CLR, 2.8 - CLR) for i in range(4)]
SCREWB = (np.array([0.0, -14.45, 23.07]), np.array([1.0, 0.0, 0.0]), 3.5, -6.0, 10.0)


def in_obb(pts, box):
    c, A, h = box
    d = (pts - c) @ A.T
    return np.all(np.abs(d) <= h, axis=1)


def in_screw(pts):
    ap, ad, r, lo, hi = SCREWB
    d = pts - ap
    s = d @ ad
    perp = np.linalg.norm(d - np.outer(s, ad), axis=1)
    return (perp <= r + SCREW_CLR) & (s >= lo - SCREW_CLR) & (s <= hi + SCREW_CLR)


class MeshIn:
    DIRS = np.array([[0.3714, 0.5571, 0.7428], [-0.8018, 0.2673, 0.5345], [0.4082, -0.8165, 0.4082]])

    def __init__(self, names):
        T = load_tris(*names)
        self.V0 = T[:, 0]
        self.E1 = T[:, 1] - T[:, 0]
        self.E2 = T[:, 2] - T[:, 0]
        self.DIRS = self.DIRS / np.linalg.norm(self.DIRS, axis=1, keepdims=True)

    def inside_batch(self, pts, chunk=400):
        out = np.zeros(len(pts), bool)
        for i0 in range(0, len(pts), chunk):
            P0 = pts[i0:i0 + chunk]
            votes = np.zeros(len(P0), int)
            for d in self.DIRS:
                pv = np.cross(d, self.E2)
                det = (self.E1 * pv).sum(1)
                ok = np.abs(det) > 1e-12
                inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
                cnt = np.zeros(len(P0), int)
                for k, p in enumerate(P0):
                    tv = p - self.V0
                    u = (tv * pv).sum(1) * inv
                    qv = np.cross(tv, self.E1)
                    v = (d * qv).sum(1) * inv
                    t = (self.E2 * qv).sum(1) * inv
                    h = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-7)
                    cnt[k] = h.sum()
                votes += (cnt % 2 == 1).astype(int)
            out[i0:i0 + chunk] = votes >= 2
        return out
