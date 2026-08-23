"""C1/C2 나사 구멍의 Z 별 반경 프로파일 — 관통/탭 구간을 실측으로 가른다.

수직 레이(+Z) 를 (r, theta) 격자에서 쏘아 재료 구간을 얻고,
그걸로 각 Z 의 '재료가 시작되는 최소 반경' 을 만든다. CAD WRITE 없음.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import stock_geom as sg                                  # noqa: E402


def z_spans(P, xy):
    """(N,2) XY 각각에 대해 +Z 레이의 재료 구간 [(z0,z1),...] 리스트."""
    v0, v1, v2 = P[:, 0], P[:, 1], P[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    d = np.array([0.0, 0.0, 1.0])
    h = np.cross(d, e2)
    a = (e1 * h).sum(1)
    m = np.abs(a) > 1e-12
    f = np.where(m, 1.0 / np.where(m, a, 1.0), 0.0)
    out = []
    for x, y in xy:
        s = np.stack([x - v0[:, 0], y - v0[:, 1], -1e4 - v0[:, 2]], 1)
        u = f * (s * h).sum(1)
        q = np.cross(s, e1)
        v = f * (q * d).sum(1)
        t = f * (e2 * q).sum(1)
        ok = m & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
        ts = np.sort(t[ok]) - 1e4
        ts = [z for i, z in enumerate(ts) if i == 0 or z - ts[i - 1] > 1e-4]
        out.append([(ts[i], ts[i + 1]) for i in range(0, len(ts) - 1, 2)])
    return out


def profile(P, cx, cy, zs, rmax=8.0, nr=41, nth=24):
    rr = np.linspace(0.0, rmax, nr)
    th = np.linspace(0, 2 * np.pi, nth, endpoint=False)
    xy = [(cx + r * np.cos(t), cy + r * np.sin(t)) for r in rr for t in th]
    sp = z_spans(P, xy)
    occ = np.zeros((len(zs), nr, nth), bool)
    for i, spans in enumerate(sp):
        ir, it = divmod(i, nth)
        for z0, z1 in spans:
            occ[:, ir, it] |= (zs >= z0) & (zs <= z1)
    frac = occ.mean(2)                       # (Z, r)
    rmin = np.full(len(zs), np.nan)
    for i in range(len(zs)):
        hit = np.where(frac[i] > 0.5)[0]
        if len(hit):
            rmin[i] = rr[hit[0]]
    return frac[:, 0], rmin


def main():
    N = sg.load(neutral=True)
    parts = {"Base": N["Base <1>"], "Roll_holder": N["Roll_holder <1>"],
             "Roll_holder_2": N["Roll_holder_2 <1>"], "Spacer": N["Spacer <1>"],
             "Roll": N["Roll <1>"], "Pitch": N["Pitch <1>"]}
    st = json.load(io.open(os.path.join(sg.OUT, "c1c2_stackup.json"), encoding="utf-8"))
    zs = np.arange(-152.0, -94.0, 0.25)
    res = {}

    for name in ("C1", "C2"):
        o = np.array(st[name]["origin"])
        cx, cy = o[0], o[1]
        print("=" * 88)
        print(f"{name}  XY = ({cx:.3f}, {cy:.3f})    나사 부품 원점 Z = {o[2]:.3f}")
        print("=" * 88)
        pr = {k: profile(P, cx, cy, zs) for k, P in parts.items()}
        keep = [k for k in parts if not np.all(np.isnan(pr[k][1]))]
        print(f"{'Z':>9s}  " + "  ".join(f"{k:>16s}" for k in keep))
        prev = None
        for i, z in enumerate(zs):
            cells = []
            for k in keep:
                c0, r = pr[k]
                cells.append("SOLID(중심막힘)  " if c0[i] > 0.5 else
                             (f"hole r={r[i]:5.2f}     " if not np.isnan(r[i])
                              else "  (없음)          "))
            line = "  ".join(cells)
            if line != prev:
                print(f"{z:9.2f}  {line}")
                prev = line
        res[name] = {k: {"center_solid": pr[k][0].tolist(),
                         "rmin": [None if np.isnan(x) else float(x) for x in pr[k][1]]}
                     for k in keep}
        print()
    res["zs"] = zs.tolist()
    json.dump(res, io.open(os.path.join(sg.OUT, "c1c2_hole_profile.json"), "w",
                           encoding="utf-8"))


if __name__ == "__main__":
    main()
