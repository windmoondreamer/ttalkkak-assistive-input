"""실제 3D 메시 기반 내부 공간 검증 유틸 (READ ONLY, 로컬 캐시만 사용).

좌표계 (실측 확정):
    X = 좌우.  분할면 = X = 0.  Joystick_1 은 X>=0, Joystick_2 는 X<=0
    Y = 전후.  전면 = -Y 방향 (엄지 패널/Backplate 가 -Y 쪽, Pitch 가 +Y 쪽)
    Z = 그립축 (위가 +)

제공 기능:
    Mesh.raycast(origin, dir) -> 교차 거리 정렬 리스트
    outer_surface(Z, theta)   -> 외피 점 + 법선
    contour(Z)                -> 외피 윤곽 (호길이 파라미터화)
"""
import json
import math
import os

import numpy as np

DUMP = os.path.join(os.path.dirname(__file__), "..", "cad_dump")


class Mesh:
    def __init__(self, names):
        tris = []
        self.names = list(names)
        self.owner = []
        for i, n in enumerate(names):
            with open(os.path.join(DUMP, f"mesh_{n}.json"), encoding="utf-8") as f:
                t = json.load(f)["tris"]
            tris.extend(t)
            self.owner.extend([i] * len(t))
        self.T = np.asarray(tris, dtype=np.float64)      # (N,3,3)
        self.owner = np.asarray(self.owner)
        self.v0 = self.T[:, 0, :]
        self.e1 = self.T[:, 1, :] - self.v0
        self.e2 = self.T[:, 2, :] - self.v0
        self.n = np.cross(self.e1, self.e2)
        ln = np.linalg.norm(self.n, axis=1, keepdims=True)
        ln[ln == 0] = 1.0
        self.nn = self.n / ln

    def raycast(self, o, d, eps=1e-7):
        """Moller-Trumbore. (t, tri_index) 를 t 오름차순으로 반환 (t>eps)."""
        o = np.asarray(o, dtype=np.float64)
        d = np.asarray(d, dtype=np.float64)
        d = d / np.linalg.norm(d)
        pv = np.cross(d, self.e2)
        det = np.einsum("ij,ij->i", self.e1, pv)
        ok = np.abs(det) > 1e-12
        inv = np.zeros_like(det)
        inv[ok] = 1.0 / det[ok]
        tv = o - self.v0
        u = np.einsum("ij,ij->i", tv, pv) * inv
        qv = np.cross(tv, self.e1)
        v = np.einsum("ij,ij->i", np.broadcast_to(d, self.e1.shape), qv) * inv
        t = np.einsum("ij,ij->i", self.e2, qv) * inv
        hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > eps)
        idx = np.nonzero(hit)[0]
        order = np.argsort(t[idx])
        idx = idx[order]
        return list(zip(t[idx], idx))

    def hits_dedup(self, o, d, tol=1e-4):
        """같은 면을 두 삼각형으로 두 번 맞는 경우를 합친다."""
        out = []
        for t, i in self.raycast(o, d):
            if out and abs(t - out[-1][0]) < tol:
                continue
            out.append((t, i))
        return out


def axis_center(mesh, z):
    """해당 Z 높이에서 그립 단면의 대략적 중심 (외피 X/Y 범위의 중앙)."""
    zs = mesh.T[:, :, 2]
    sel = (zs.min(axis=1) <= z) & (zs.max(axis=1) >= z)
    if not sel.any():
        return None
    pts = mesh.T[sel].reshape(-1, 3)
    return np.array([0.0, 0.5 * (pts[:, 1].min() + pts[:, 1].max()), z])


def outer_point(mesh, center, z, theta):
    """center 에서 방위각 theta 로 쏜 레이의 가장 먼 교차점 = 외피."""
    d = np.array([math.sin(theta), -math.cos(theta), 0.0])   # theta=0 -> -Y (전면)
    hits = mesh.hits_dedup(center, d)
    if not hits:
        return None
    t, i = hits[-1]
    p = np.asarray(center) + t * d
    nrm = mesh.nn[i].copy()
    if np.dot(nrm, d) < 0:
        nrm = -nrm
    return p, nrm, t


def contour(mesh, z, n=1440, span=math.pi):
    """전면(theta=0)에서 좌우로 span 만큼 외피를 훑어 호길이 파라미터화.
    반환: [(s, x, y, nx, ny)] — s>0 은 +X 쪽, s<0 은 -X 쪽."""
    c = axis_center(mesh, z)
    if c is None:
        return []
    rows = []
    for k in range(-n, n + 1):
        th = span * k / n
        r = outer_point(mesh, c, z, th)
        if r is None:
            continue
        p, nrm, _ = r
        rows.append([th, p[0], p[1], nrm[0], nrm[1]])
    rows.sort(key=lambda r: r[0])
    # theta=0 지점을 s=0 으로 두고 누적 호길이
    i0 = min(range(len(rows)), key=lambda i: abs(rows[i][0]))
    s = [0.0] * len(rows)
    for i in range(i0 + 1, len(rows)):
        s[i] = s[i - 1] + math.dist(rows[i][1:3], rows[i - 1][1:3])
    for i in range(i0 - 1, -1, -1):
        s[i] = s[i + 1] - math.dist(rows[i][1:3], rows[i + 1][1:3])
    return [(s[i], rows[i][1], rows[i][2], rows[i][3], rows[i][4]) for i in range(len(rows))]


def at_s(cont, target):
    return min(cont, key=lambda r: abs(r[0] - target))


def probe_inward(mesh, p, n, max_depth=40.0):
    """외피 점 p 에서 -n 방향으로 쏘아 벽두께와 내부 장애물 거리를 구한다."""
    o = np.asarray(p) + np.asarray(n) * 1e-3
    hits = mesh.hits_dedup(o, -np.asarray(n))
    return [(float(t), mesh.names[mesh.owner[i]]) for t, i in hits if t <= max_depth]
