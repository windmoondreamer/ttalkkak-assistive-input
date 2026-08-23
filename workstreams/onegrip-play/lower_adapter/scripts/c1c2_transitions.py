"""C1/C2 축상 정확한 전이 Z 와 구멍 지름을 뽑는다."""
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
from probe_c1c2_holes import z_spans                     # noqa: E402


def ring_spans(P, cx, cy, r, nth=48):
    th = np.linspace(0, 2 * np.pi, nth, endpoint=False)
    xy = [(cx + r * np.cos(t), cy + r * np.sin(t)) for t in th]
    return z_spans(P, xy)


def bore_at(P, cx, cy, z, lo=0.5, hi=8.0, it=40):
    """Z 평면에서 중심 주위 재료가 시작되는 반경 (이분법)."""
    def solid_frac(r):
        sp = ring_spans(P, cx, cy, r, nth=32)
        return np.mean([any(a <= z <= b for a, b in s) for s in sp])
    if solid_frac(lo) > 0.5:
        return 0.0
    if solid_frac(hi) < 0.5:
        return np.nan
    a, b = lo, hi
    for _ in range(it):
        m = 0.5 * (a + b)
        if solid_frac(m) > 0.5:
            b = m
        else:
            a = m
    return 0.5 * (a + b)


def main():
    N = sg.load(neutral=True)
    st = json.load(io.open(os.path.join(sg.OUT, "c1c2_stackup.json"), encoding="utf-8"))
    parts = {"Base": N["Base <1>"], "Spacer": N["Spacer <1>"],
             "Roll_holder": N["Roll_holder <1>"],
             "Roll_holder_2": N["Roll_holder_2 <1>"]}
    res = {}
    for name, holder in (("C1", "Roll_holder"), ("C2", "Roll_holder_2")):
        o = np.array(st[name]["origin"])
        cx, cy = o[0], o[1]
        print("=" * 74)
        print(f"{name}  XY=({cx:.4f}, {cy:.4f})   나사부품 원점 Z={o[2]:.4f}")
        print("=" * 74)
        r = {}
        # 각 부품의 Z 범위
        for k in ("Base", "Spacer", holder):
            V = parts[k].reshape(-1, 3)
            print(f"  {k:<14s} Z [{V[:,2].min():10.4f}, {V[:,2].max():10.4f}]")
        # 중심축 재료 구간 -> 블라인드 끝
        sp = z_spans(parts[holder], [(cx, cy)])[0]
        print(f"  {holder} 중심축 재료 구간: "
              + ", ".join(f"[{a:.4f},{b:.4f}]" for a, b in sp))
        blind = sp[0][0] if sp else np.nan
        print(f"  -> 블라인드 홀 바닥 Z = {blind:.4f}")
        # 지름 측정
        Vb = parts["Base"].reshape(-1, 3)
        bot = Vb[:, 2].min()
        probes = [("Base 카운터보어", "Base", bot + 0.5),
                  ("Base 카운터보어", "Base", bot + 2.5),
                  ("Base 관통", "Base", bot + 4.5),
                  ("Base 관통", "Base", bot + 6.0),
                  ("Spacer 관통", "Spacer", -140.0),
                  (f"{holder} 탭", holder, -134.0),
                  (f"{holder} 탭", holder, -128.0),
                  (f"{holder} 탭", holder, blind + 0.5)]
        for lab, k, z in probes:
            rr = bore_at(parts[k], cx, cy, z)
            print(f"  {lab:<20s} Z={z:9.4f}  구멍 r={rr:7.4f}  (D={2*rr:7.4f})")
            r[f"{lab}@{z:.2f}"] = None if np.isnan(rr) else 2 * rr
        # Base 카운터보어 깊이: r>3 인 구간
        zs = np.arange(bot, bot + 8.0, 0.05)
        big = [z for z in zs if (bore_at(parts["Base"], cx, cy, z, 3.0, 8.0) or 0) > 0]
        res[name] = {"blind_bottom": float(blind), "base_bottom": float(bot),
                     "bores": r}
        print()
    json.dump(res, io.open(os.path.join(sg.OUT, "c1c2_transitions.json"), "w",
                           encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
