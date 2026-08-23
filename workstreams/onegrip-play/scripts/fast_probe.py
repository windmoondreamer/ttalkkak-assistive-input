"""국소 삼각형만 추려 point-in-solid / 광선을 빠르게 계산한다 (READ ONLY)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from axis_opt import load_tris

DIRS = np.array([[0.3714, 0.5571, 0.7428],
                 [-0.8018, 0.2673, 0.5345],
                 [0.4082, -0.8165, 0.4082]])
DIRS = DIRS / np.linalg.norm(DIRS, axis=1, keepdims=True)


class Local:
    """center 주변 radius 안의 삼각형 + 그 광선이 통과할 수 있는 모든 삼각형을 남긴다.

    패리티 판정에는 광선 전체 경로의 삼각형이 필요하므로, 국소 절단 대신
    '광선 방향으로 무한히 뻗은 기둥' 안의 삼각형만 남긴다.
    """

    def __init__(self, names, center, radius):
        T = load_tris(*names)
        c = np.asarray(center, float)
        keep = np.zeros(len(T), bool)
        cen = T.mean(axis=1)
        for d in DIRS:
            w = cen - c
            perp = w - np.outer(w @ d, d)
            keep |= (np.linalg.norm(perp, axis=1) <= radius)
        self.T = T[keep]
        self.V0 = self.T[:, 0]
        self.E1 = self.T[:, 1] - self.V0
        self.E2 = self.T[:, 2] - self.V0
        self.n = len(self.T)

    def _cross(self, pt, d):
        pv = np.cross(d, self.E2); det = (self.E1 * pv).sum(1)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = pt - self.V0
        u = (tv * pv).sum(1) * inv
        qv = np.cross(tv, self.E1)
        v = (d * qv).sum(1) * inv
        t = (self.E2 * qv).sum(1) * inv
        return ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-7), t

    def inside(self, pt):
        votes = 0
        for d in DIRS:
            hit, _ = self._cross(np.asarray(pt, float), d)
            votes += int(hit.sum() % 2 == 1)
        return votes >= 2

    def first_hit(self, pt, d, lim=1e9):
        d = np.asarray(d, float); d = d / np.linalg.norm(d)
        hit, t = self._cross(np.asarray(pt, float), d)
        ts = t[hit]
        ts = ts[ts < lim]
        return float(ts.min()) if len(ts) else None


    def ray_ts(self, pt, d):
        """광선과 국소 메시의 모든 교차 t (정렬)."""
        d = np.asarray(d, float); d = d / np.linalg.norm(d)
        hit, t = self._cross(np.asarray(pt, float), d)
        return np.sort(t[hit])
