"""하부 어댑터 최종 검증 (GET only, 형상 변경 없음).

    python lower_adapter/scripts/verify_adapter.py [--fetch]

--fetch 를 주면 신규 4개 body 의 tessellation 을 새로 받아 캐시한다.
검증은 전부 로컬 메시 + 해석식으로 한다.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from onshape.client import BASE, session          # noqa: E402
from onshape import write_client as wc            # noqa: E402

OUT = os.path.join(ROOT, "lower_adapter", "cad_dump")
SHARED = os.path.join(ROOT, "cad_dump")
M2MM = 1000.0
PARTS = {"CRADLE": "JHD", "WEDGE": "RoBD", "RING_F": "RwCD", "RING_B": "RzDD"}
GRIP = ["INDEX_FINAL_JaD", "INDEX_FINAL_JfD"]

C = json.load(io.open(os.path.join(OUT, "adapter_constants.json"), encoding="utf-8"))
FLANGE_Z = C["FLANGE_Z"]
BOSS_Z = C["BOSS_Z"]
SOCKET_TOP = C["SOCKET_TOP"]
AXIS_Y = C["AXIS_Y"]
UP = np.array(C["UP_LOCAL"])
BASE_PT = np.array(C["BASE_PT"])
STACK_H = C["STACK_H"]


def fetch():
    t = json.load(io.open(os.path.join(OUT, "adapter_target.json"), encoding="utf-8"))
    s = session()
    for name, pid in PARTS.items():
        r = s.get(f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{t['ps_eid']}/tessellatedfaces",
                  params={"angleTolerance": 0.09, "chordTolerance": 0.15,
                          "partId": pid, "outputFaceAppearances": "false",
                          "configuration": "default"}, timeout=300)
        r.raise_for_status()
        tris = []
        for b in r.json().get("bodies", []):
            for f in b.get("faces", []):
                for fac in f.get("facets", []):
                    v = fac.get("vertices", [])
                    if len(v) == 3:
                        tris.append([[q["x"] * M2MM, q["y"] * M2MM, q["z"] * M2MM] for q in v])
        with io.open(os.path.join(OUT, f"mesh_{name}.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": name, "partId": pid, "tris": tris}, fh)
        print(f"  fetched {name:8s} {pid:5s} tris={len(tris)}")


def load(name, shared=False):
    d = SHARED if shared else OUT
    return np.asarray(json.load(io.open(os.path.join(d, f"mesh_{name}.json"),
                                        encoding="utf-8"))["tris"], dtype=float)


def props(T):
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    v = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
    V = v.sum()
    return V, (((a + b + c) / 4.0) * v[:, None]).sum(0) / V


def head(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def main():
    if "--fetch" in sys.argv:
        head("0. tessellation 캐시")
        fetch()

    M = {k: load(k) for k in PARTS}
    G = np.vstack([load(n, True) for n in GRIP])

    head("1. 생성된 부품")
    tot = 0.0
    for k, T in M.items():
        V, c = props(T)
        v = T.reshape(-1, 3)
        tot += V
        print(f"  {k:8s} {PARTS[k]:5s} 부피 {V:9.1f} mm3  "
              f"X[{v[:,0].min():7.2f},{v[:,0].max():7.2f}] "
              f"Y[{v[:,1].min():7.2f},{v[:,1].max():7.2f}] "
              f"Z[{v[:,2].min():8.2f},{v[:,2].max():8.2f}]")
    print(f"  {'합계':8s}       부피 {tot:9.1f} mm3  (PLA 1.24 g/cm3 -> 약 {tot * 1.24e-3:.0f} g)")

    head("2. 20도 검증 — 웨지 밑면 법선 vs 중심축")
    W = M["WEDGE"]
    n = np.cross(W[:, 1] - W[:, 0], W[:, 2] - W[:, 0])
    ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-9
    nn = n[ok] / ln[ok, None]
    area = ln[ok] / 2
    d = (W[ok].mean(1) - BASE_PT) @ UP
    sel = (np.abs(d) < 0.02) & (nn @ UP < -0.999)      # 기준면 위의 아래향 facet
    print(f"  기준면 facet {sel.sum()} 개, 면적 {area[sel].sum():.1f} mm2")
    if sel.sum():
        nb = (nn[sel] * area[sel, None]).sum(0)
        nb /= np.linalg.norm(nb)
        ang = np.degrees(np.arccos(abs(float(nb @ np.array([0, 0, 1.0])))))
        flat = np.degrees(np.arccos(np.clip(np.abs(nn[sel] @ (-UP)), -1, 1))).max()
        print(f"  밑면 법선 = ({nb[0]:+.6f}, {nb[1]:+.6f}, {nb[2]:+.6f})")
        print(f"  angle(밑면 법선, 소켓축 +Z) = {ang:.6f} deg   목표 20.000000")
        print(f"  밑면 평면도(최대 facet 편차) = {flat:.6f} deg")
        print(f"  판정 {'PASS' if abs(ang - 20.0) < 1e-3 else 'FAIL'}")

    head("3. 착좌면 / post / 보스 포켓")
    Cd = M["CRADLE"]
    cv = Cd.reshape(-1, 3)
    seat = cv[np.abs(cv[:, 2] - FLANGE_Z) < 1e-4]
    print(f"  착좌면 Z={FLANGE_Z:.6f} 정점 {len(seat)}  "
          f"X[{seat[:,0].min():.2f},{seat[:,0].max():.2f}] Y[{seat[:,1].min():.2f},{seat[:,1].max():.2f}]")
    top = cv[cv[:, 2] > C["POST_TOP"] - 1e-4]
    print(f"  post 상단 Z={C['POST_TOP']:.6f}  X[{top[:,0].min():.3f},{top[:,0].max():.3f}] "
          f"Y[{top[:,1].min():.3f},{top[:,1].max():.3f}]")
    pw = top[:, 0].max() - top[:, 0].min()
    pd = top[:, 1].max() - top[:, 1].min()
    print(f"  post 단면 {pw:.3f} x {pd:.3f}  (설계 {C['POST_W']:.3f} x {C['POST_D']:.3f})")
    print(f"  소켓 여유 X {(21.072 - pw) / 2:.3f}  Y {(25.672 - pd) / 2:.3f} mm/side")
    print(f"  보어 물림 {C['POST_TOP'] - BOSS_Z:.3f} mm / 직진보어 {SOCKET_TOP - BOSS_Z:.3f} mm")
    print(f"  post 끝 여유 {SOCKET_TOP - C['POST_TOP']:.3f} mm")

    head("4. 그립과의 간섭 (0.4 mm 복셀, 벡터화 parity)")

    def prep(T, cell=4.0):
        """+Z ray parity 전처리 + XY 격자 색인 (격자 없으면 삼각형 전수 비교라 매우 느리다)."""
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        den = ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
               - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1]))
        k = np.abs(den) > 1e-12
        a, b, c, den = a[k], b[k], c[k], den[k]
        xy = np.stack([a[:, :2], b[:, :2], c[:, :2]], 1)
        lo = xy.min(1)
        hi = xy.max(1)
        org = lo.min(0) - cell
        nx = int(np.ceil((hi[:, 0].max() - org[0]) / cell)) + 2
        ny = int(np.ceil((hi[:, 1].max() - org[1]) / cell)) + 2
        buckets = [[] for _ in range(nx * ny)]
        i0 = np.floor((lo - org) / cell).astype(int)
        i1 = np.floor((hi - org) / cell).astype(int)
        for t in range(len(a)):
            for gx in range(i0[t, 0], i1[t, 0] + 1):
                for gy in range(i0[t, 1], i1[t, 1] + 1):
                    buckets[gy * nx + gx].append(t)
        buckets = [np.asarray(v, dtype=np.int64) for v in buckets]
        return dict(a=a, b=b, c=c, den=den, org=org, cell=cell, nx=nx, ny=ny, bk=buckets)

    def inside(pre, P):
        a, b, c, den = pre["a"], pre["b"], pre["c"], pre["den"]
        org, cell, nx, ny = pre["org"], pre["cell"], pre["nx"], pre["ny"]
        gi = np.floor((P[:, :2] - org) / cell).astype(int)
        ok = (gi[:, 0] >= 0) & (gi[:, 0] < nx) & (gi[:, 1] >= 0) & (gi[:, 1] < ny)
        key = np.where(ok, gi[:, 1] * nx + gi[:, 0], 0)
        out = np.zeros(len(P), dtype=bool)
        order = np.argsort(key)
        ks = key[order]
        bounds = np.searchsorted(ks, np.unique(ks))
        uk = np.unique(ks)
        for u, s0 in zip(uk, bounds):
            e0 = np.searchsorted(ks, u, side="right")
            idx = order[s0:e0]
            idx = idx[ok[idx]]
            if len(idx) == 0:
                continue
            tri = pre["bk"][u]
            if len(tri) == 0:
                continue
            q = P[idx]
            aa, bb, cc, dd = a[tri], b[tri], c[tri], den[tri]
            px = q[:, 0][:, None] - aa[None, :, 0]
            py = q[:, 1][:, None] - aa[None, :, 1]
            e1x = (bb - aa)[None, :, 0]; e1y = (bb - aa)[None, :, 1]
            e2x = (cc - aa)[None, :, 0]; e2y = (cc - aa)[None, :, 1]
            u1 = (px * e2y - py * e2x) / dd[None, :]
            v1 = (py * e1x - px * e1y) / dd[None, :]
            inT = (u1 >= 0) & (v1 >= 0) & (u1 + v1 <= 1)
            zz = aa[None, :, 2] + u1 * (bb - aa)[None, :, 2] + v1 * (cc - aa)[None, :, 2]
            out[idx] = (np.count_nonzero(inT & (zz > q[:, 2][:, None]), axis=1) % 2) == 1
        return out

    preG = prep(G)
    gl, gh = G.reshape(-1, 3).min(0), G.reshape(-1, 3).max(0)
    step = 0.4
    total_bad = 0
    for k, T in M.items():
        preA = prep(T)
        v = T.reshape(-1, 3)
        lo = np.maximum(v.min(0), gl)
        hi = np.minimum(v.max(0), gh)
        if np.any(lo >= hi):
            print(f"  {k:8s} bbox 겹침 없음 -> 간섭 0   PASS")
            continue
        g = np.stack(np.meshgrid(
            np.arange(lo[0] + step / 2, hi[0], step),
            np.arange(lo[1] + step / 2, hi[1], step),
            np.arange(lo[2] + step / 2, hi[2], step), indexing="ij"), -1).reshape(-1, 3)
        ia = inside(preA, g)
        cand = g[ia]
        ig = inside(preG, cand) if len(cand) else np.zeros(0, dtype=bool)
        bad = int(ig.sum())
        total_bad += bad
        print(f"  {k:8s} 겹침영역 복셀 {len(g):7d}  어댑터 내부 {int(ia.sum()):7d}  "
              f"양쪽 내부(간섭) {bad:5d}   {'PASS' if bad == 0 else 'FAIL'}")
        if bad:
            bb = cand[ig]
            print(f"           X[{bb[:,0].min():.2f},{bb[:,0].max():.2f}] "
                  f"Y[{bb[:,1].min():.2f},{bb[:,1].max():.2f}] Z[{bb[:,2].min():.2f},{bb[:,2].max():.2f}]")
    print(f"  총 간섭 복셀 {total_bad}  ->  {'PASS' if total_bad == 0 else 'FAIL'}")

    head("5. 어댑터 부품 상호 간섭 (0.4 mm)")
    keys = list(M)
    pres = {k: prep(M[k]) for k in keys}
    for i2 in range(len(keys)):
        for j2 in range(i2 + 1, len(keys)):
            ka, kb = keys[i2], keys[j2]
            va, vb = M[ka].reshape(-1, 3), M[kb].reshape(-1, 3)
            lo = np.maximum(va.min(0), vb.min(0))
            hi = np.minimum(va.max(0), vb.max(0))
            if np.any(lo >= hi):
                print(f"  {ka:8s} vs {kb:8s}  bbox 겹침 없음 -> 0   PASS")
                continue
            g = np.stack(np.meshgrid(
                np.arange(lo[0] + step / 2, hi[0], step),
                np.arange(lo[1] + step / 2, hi[1], step),
                np.arange(lo[2] + step / 2, hi[2], step), indexing="ij"), -1).reshape(-1, 3)
            ia = inside(pres[ka], g)
            cd = g[ia]
            n = int(inside(pres[kb], cd).sum()) if len(cd) else 0
            print(f"  {ka:8s} vs {kb:8s}  복셀 {len(g):7d}  간섭 {n:5d}   "
                  f"{'PASS' if n == 0 else 'FAIL'}")

    head("6. 스택 높이 / 인터페이스")
    wv = M["WEDGE"].reshape(-1, 3)
    dmin = float(((wv - BASE_PT) @ UP).min())
    print(f"  기준면 아래로 내려간 웨지 재료 {max(-dmin, 0):.4f} mm   {'PASS' if dmin > -0.01 else 'FAIL'}")
    print(f"  MOUNT_ORIGIN 높이 (기준면 -> 착좌 평면) {STACK_H:.3f} mm")
    allv = np.vstack([m.reshape(-1, 3) for m in M.values()])
    hh = (allv - BASE_PT) @ UP
    gh2 = (G.reshape(-1, 3) - BASE_PT) @ UP
    print(f"  어댑터 높이 {hh.min():.3f} ~ {hh.max():.3f} mm")
    print(f"  그립 포함 전체 높이 {min(hh.min(), gh2.min()):.3f} ~ {max(hh.max(), gh2.max()):.3f} mm")
    print(f"  웨지 두께 {C['WEDGE_MIN']:.3f} ~ {C['WEDGE_MAX']:.3f} mm")


if __name__ == "__main__":
    main()
