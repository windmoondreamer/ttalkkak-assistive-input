"""CAD sacrificial support 검증.

  A. support 가 제품 내부를 침범하지 않는다
  B. SUPPORT_FOR_SUPPORT = 0   (support 자체의 미지지 아래보기)
  C. chunk 별 volume / bbox / removal opening / direction / 최소 통과 여유
  D. TRUE TRAPPED SUPPORT = 0
  E. product body 무변경 증명 (sha256)
"""
from __future__ import annotations
import os
import sys
import json
import math
import hashlib

import numpy as np
import scipy.ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                       # noqa: E402
import geometry_utils as G                   # noqa: E402
import build123d as bd                       # noqa: E402

LOCAL = os.path.dirname(HERE)
DUMP = os.path.join(os.path.dirname(LOCAL), "cad_dump")
VOX = 1.5

PARTS = {"MAIN": "HOUSING_V4_MAIN_PRINT_REV_D",
         "ARMREST": "HOUSING_V4_ARMREST_PRINT_REV_D"}

# Rx -90 print frame 기준 개구부.  (이름, 축, 인출 방향)
OPENINGS = {
    "MAIN": [("DECK_OPENING", "+Y", "+Y 방향으로 빼낸다"),
             ("CARRIER_OPENING", "-Y", "-Y 방향으로 빼낸다"),
             ("CUT_FACE_TOP", "+Z", "절단면(위)으로 들어올린다")],
    "ARMREST": [("UNDERSIDE_OPEN", "+Y", "+Y 방향으로 빼낸다"),
                ("FRONT_OPEN", "-Y", "-Y 방향으로 빼낸다"),
                ("TOP_OPEN", "+Z", "위로 들어올린다")],
}


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def tris(sh, tol=0.05):
    f = os.path.join(P.EXPORT_STL, "_sv.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.3)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


class Col:
    """XY 버킷 수직 광선 -> 컬럼별 표면 교차 z."""

    def __init__(self, T, cell=6.0):
        self.T = T
        self.cell = cell
        self.lo = T.reshape(-1, 3).min(0)[:2]
        i0 = np.floor((T.min(1)[:, :2] - self.lo) / cell).astype(int)
        i1 = np.floor((T.max(1)[:, :2] - self.lo) / cell).astype(int)
        self.b = {}
        for k in range(len(T)):
            for i in range(i0[k, 0], i1[k, 0] + 1):
                for j in range(i0[k, 1], i1[k, 1] + 1):
                    self.b.setdefault((i, j), []).append(k)

    def hit(self, x, y):
        i = int(math.floor((x - self.lo[0]) / self.cell))
        j = int(math.floor((y - self.lo[1]) / self.cell))
        idx = self.b.get((i, j))
        if not idx:
            return np.zeros(0)
        t = self.T[idx]
        v0, v1, v2 = t[:, 0], t[:, 1], t[:, 2]
        e1, e2 = v1 - v0, v2 - v0
        d = np.array([0.0, 0.0, 1.0])
        pv = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, pv)
        m = np.abs(det) > 1e-12
        inv = np.zeros(len(t))
        inv[m] = 1.0 / det[m]
        o = np.array([x, y, -1e4])
        tv = o - v0
        u = np.einsum("ij,ij->i", tv, pv) * inv
        qv = np.cross(tv, e1)
        w = np.einsum("j,ij->i", d, qv) * inv
        tt = np.einsum("ij,ij->i", e2, qv) * inv
        ok = m & (u >= 0) & (w >= 0) & (u + w <= 1) & (tt > 0)
        z = np.sort(-1e4 + tt[ok])
        if len(z) == 0:
            return z
        return z[np.concatenate(([True], np.diff(z) > 1e-4))]


def rasterize(col, org, shp, vox):
    M = np.zeros(shp, bool)
    zc = org[2] + (np.arange(shp[2]) + 0.5) * vox
    for i in range(shp[0]):
        x = org[0] + (i + 0.5) * vox
        for j in range(shp[1]):
            y = org[1] + (j + 0.5) * vox
            z = col.hit(x, y)
            if len(z) < 2:
                continue
            for k in range(0, len(z) - 1, 2):
                M[i, j, (zc >= z[k]) & (zc <= z[k + 1])] = True
    return M


ST = np.ones((3, 3, 3), bool)


def main():
    mat = sys.argv[1] if len(sys.argv) > 1 else "PLA"
    out = {}
    print("=== SUPPORT VALIDATION (%s) ===" % mat)
    for nm, fn in PARTS.items():
        sp = os.path.join(P.EXPORT_STEP, "%s_CUSTOM_SUPPORT_%s.step" % (nm, mat))
        if not os.path.exists(sp):
            print("\n--- %s : support 없음 ---" % nm)
            continue
        z0, ang = np.load(os.path.join(DUMP, "_sup_z0_%s.npy" % nm))
        prod = bd.import_step(os.path.join(P.EXPORT_STEP, fn + ".step")).solids()[0]
        Tp = tris(prod) @ rot_x(ang).T
        Tp[:, :, 2] -= z0
        sup = bd.import_step(sp)
        ssol = sup.solids()
        Ts = tris(sup, 0.03)
        print("\n--- %s  (Rx %+.0f)  BREP chunk %d개 ---" % (nm, ang, len(ssol)))
        r = {"brep_chunks": len(ssol),
             "support_volume_mm3": sum(float(s.volume) for s in ssol)}

        pc = Col(Tp)
        sc = Col(Ts)
        ctr = Ts.mean(1)

        # A. 침범
        inside, depth = 0, []
        for p in ctr:
            z = pc.hit(p[0], p[1])
            if len(z) and np.searchsorted(z, p[2]) % 2 == 1:
                d = float(np.min(np.abs(z - p[2])))
                if d > 0.02:
                    inside += 1
                    depth.append(d)
        dmax = max(depth) if depth else 0.0
        real = sum(1 for d in depth if d > 0.10)   # 0.10 이하는 tessellation 잡음
        print("  A. 제품 내부 support 삼각형 중심 : %d / %d   최대깊이 %.4f mm"
              % (inside, len(ctr), dmax))
        print("     0.10mm 초과(실침범) : %d   [%s]"
              % (real, "PASS" if real == 0 else "FAIL"))
        r["intrusion_pts"] = int(inside)
        r["intrusion_real"] = int(real)
        r["intrusion_max_depth"] = dmax

        # B. SUPPORT_FOR_SUPPORT
        n = np.cross(Ts[:, 1] - Ts[:, 0], Ts[:, 2] - Ts[:, 0])
        mg = np.linalg.norm(n, axis=1)
        nz = np.where(mg > 1e-12, n[:, 2] / np.maximum(mg, 1e-12), 0.0)
        area = 0.5 * mg
        dn = (nz < -0.7071) & (ctr[:, 2] > 0.35)
        LEDGE_R = 0.45          # 노즐 폭 1개 이내의 미세 단은 자립한다

        def _inside(col, px, py, zq):
            zz = col.hit(px, py)
            return len(zz) > 0 and (int(np.searchsorted(zz, zq)) % 2 == 1)

        def has_below(px, py, pz):
            """바로 아래에 **재료가 있나** — 표면 교차점이 아니라 내부 판정.

            (교차점만 보면 리브 몸통처럼 연속 재료 안에 있는 점이
             '아래에 아무것도 없다'로 잡힌다. 세 번째로 밟은 측정 결함.)
            """
            for d in (0.10, 0.30, 0.55):
                if _inside(pc, px, py, pz - d) or _inside(sc, px, py, pz - d):
                    return True
            return False

        fa = 0.0
        ledge = 0.0
        float_pts = []
        for k in np.where(dn)[0]:
            p = ctr[k]
            if has_below(p[0], p[1], p[2]):
                continue
            # 계단 머리처럼 0.45mm 이내에 받침이 있으면 자립 미세 단이다
            if any(has_below(p[0] + LEDGE_R * math.cos(t),
                             p[1] + LEDGE_R * math.sin(t), p[2])
                   for t in np.arange(0.0, 6.28, 0.7854)):
                ledge += area[k]
                continue
            fa += area[k]
            float_pts.append([float(p[0]), float(p[1]), float(p[2])])
        print("  B. SUPPORT_FOR_SUPPORT 뜬 아래보기 면적 : %.3f mm2   [%s]"
              % (fa, "PASS" if fa < 1.0 else "FAIL"))
        print("     (자립 미세 단 <=0.45mm : %.3f mm2 — 계단 머리, 별도 집계)"
              % ledge)
        r["support_for_support_mm2"] = float(fa)
        r["micro_ledge_mm2"] = float(ledge)
        if float_pts:
            a_ = np.array(float_pts)
            print("     뜬 위치  z %.1f~%.1f  x %.1f~%.1f  y %.1f~%.1f"
                  % (a_[:, 2].min(), a_[:, 2].max(), a_[:, 0].min(),
                     a_[:, 0].max(), a_[:, 1].min(), a_[:, 1].max()))

        # C/D. voxel 인출 통로
        V = np.vstack([Tp.reshape(-1, 3), Ts.reshape(-1, 3)])
        org = V.min(0) - VOX
        shp = tuple(np.ceil((V.max(0) + VOX - org) / VOX).astype(int))
        print("  voxel %s @ %.1f mm" % (shp, VOX))
        SOL = rasterize(pc, org, shp, VOX)
        SUP = rasterize(sc, org, shp, VOX)
        free = ~SOL
        dist = ndi.distance_transform_edt(free, sampling=VOX)
        lab, ncl = ndi.label(SUP & free, structure=ST)
        print("  C. voxel chunk %d개" % ncl)
        ops = []
        for (nmo, ax, dirn) in OPENINGS[nm]:
            m = np.zeros(shp, bool)
            if ax == "+Y":
                m[:, -1, :] = True
            elif ax == "-Y":
                m[:, 0, :] = True
            elif ax == "+Z":
                m[:, :, -1] = True
            ops.append((nmo, dirn, m & free))
        bands = {}
        for rr in np.arange(20.0, 0.19, -0.4):
            bands[round(rr, 1)] = free & (dist >= rr)
        rows, trapped = [], 0
        for c in range(1, ncl + 1):
            cm = lab == c
            volc = float(cm.sum()) * VOX ** 3
            if volc < 8.0:
                continue
            idx = np.argwhere(cm)
            bb = ((idx.max(0) - idx.min(0) + 1) * VOX).astype(float)
            best = None
            for (nmo, dirn, om) in ops:
                got = 0.0
                for rr in sorted(bands, reverse=True):
                    L2, _ = ndi.label(bands[rr] | cm, structure=ST)
                    a = set(np.unique(L2[cm]).tolist()) - {0}
                    b = set(np.unique(L2[om]).tolist()) - {0}
                    if a & b:
                        got = rr
                        break
                if got > 0 and (best is None or got > best[2]):
                    best = (nmo, dirn, got)
            if best is None:
                trapped += 1
                rows.append({"vol": volc, "bbox": bb.tolist(),
                             "opening": None, "dir": None, "clear": 0.0})
            else:
                rows.append({"vol": volc, "bbox": bb.tolist(),
                             "opening": best[0], "dir": best[1],
                             "clear": float(best[2])})
        rows.sort(key=lambda q: -q["vol"])
        for q in rows[:16]:
            print("    %9.0f mm3  bbox %6.1f x %6.1f x %6.1f  -> %-16s "
                  "통과여유 %4.1f mm" % (q["vol"], q["bbox"][0], q["bbox"][1],
                                     q["bbox"][2], q["opening"] or "TRAPPED",
                                     q["clear"]))
        if len(rows) > 16:
            print("    ... 외 %d개" % (len(rows) - 16))
        print("  D. TRUE TRAPPED SUPPORT = %d   [%s]"
              % (trapped, "PASS" if trapped == 0 else "FAIL"))
        r["trapped"] = trapped
        r["voxel_chunks"] = ncl
        r["chunk_rows"] = rows

        r["product_step_sha"] = sha(os.path.join(P.EXPORT_STEP, fn + ".step"))
        r["product_stl_sha"] = sha(os.path.join(P.EXPORT_STL, fn + ".stl"))
        print("  E. product sha  step %s / stl %s"
              % (r["product_step_sha"], r["product_stl_sha"]))
        out[nm] = r

    json.dump(out, open(os.path.join(LOCAL, "reports",
                                     "16_support_validate_%s.json" % mat),
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nsaved: reports/16_support_validate_%s.json" % mat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
