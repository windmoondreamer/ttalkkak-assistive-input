"""C1/C2 구멍의 Z 단면 실제 형상 (원/사각 판별 + 치수)."""
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


def section(P, z, cx, cy, half=7.0, n=141):
    g = np.linspace(-half, half, n)
    xy = [(cx + a, cy + b) for a in g for b in g]
    sp = z_spans(P, xy)
    solid = np.array([any(a <= z <= b for a, b in s) for s in sp]).reshape(n, n)
    return g, solid


def report(P, z, cx, cy, label, half=7.0, n=141):
    g, S = section(P, z, cx, cy, half, n)
    hole = ~S
    # 중심에서 연결된 빈 영역만
    n2 = len(g)
    c = n2 // 2
    if S[c, c]:
        print(f"  {label:<28s} Z={z:9.3f}   중심이 재료로 막힘")
        return None
    stack = [(c, c)]
    seen = np.zeros_like(hole)
    seen[c, c] = True
    while stack:
        i, j = stack.pop()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < n2 and 0 <= b < n2 and hole[a, b] and not seen[a, b]:
                seen[a, b] = True
                stack.append((a, b))
    xs, ys = np.where(seen)
    if len(xs) == 0:
        return None
    w = g[xs.max()] - g[xs.min()]
    h = g[ys.max()] - g[ys.min()]
    area = seen.sum() * (g[1] - g[0]) ** 2
    # 원이면 area = pi r^2, 사각이면 w*h
    r_eq = np.sqrt(area / np.pi)
    fill = area / (w * h) if w * h > 0 else 0
    shape = "원형" if fill < 0.85 else ("사각" if fill > 0.93 else "?")
    print(f"  {label:<28s} Z={z:9.3f}   {w:6.3f} x {h:6.3f} mm  "
          f"면적 {area:7.3f}  충전율 {fill:.3f} -> {shape}"
          + (f"  (D_eq {2*r_eq:.3f})" if shape == "원형" else ""))
    return {"w": float(w), "h": float(h), "area": float(area),
            "fill": float(fill), "shape": shape}


def main():
    N = sg.load(neutral=True)
    st = json.load(io.open(os.path.join(sg.OUT, "c1c2_stackup.json"), encoding="utf-8"))
    out = {}
    for name, holder in (("C1", "Roll_holder"), ("C2", "Roll_holder_2")):
        o = np.array(st[name]["origin"])
        cx, cy = o[0], o[1]
        print("=" * 76)
        print(f"{name}  XY=({cx:.4f}, {cy:.4f})")
        print("=" * 76)
        d = {}
        d["base_cb"] = report(N["Base <1>"], -149.50, cx, cy, "Base 카운터보어 하부")
        d["base_cb2"] = report(N["Base <1>"], -146.60, cx, cy, "Base 카운터보어 상부")
        d["base_thru"] = report(N["Base <1>"], -145.50, cx, cy, "Base 관통부")
        d["base_top"] = report(N["Base <1>"], -132.00, cx, cy, "Base 상단")
        d["spacer"] = report(N["Spacer <1>"], -140.00, cx, cy, "Spacer 관통")
        d["tap_lo"] = report(N[f"{holder} <1>"], -135.50, cx, cy, f"{holder} 탭 하단")
        d["tap_mid"] = report(N[f"{holder} <1>"], -129.00, cx, cy, f"{holder} 탭 중간")
        d["tap_hi"] = report(N[f"{holder} <1>"], -124.00, cx, cy, f"{holder} 탭 상단")
        out[name] = d
        print()
    json.dump(out, io.open(os.path.join(sg.OUT, "c1c2_xsection.json"), "w",
                           encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
