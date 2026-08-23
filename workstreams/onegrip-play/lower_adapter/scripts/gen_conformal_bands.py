"""포락선 -> FeatureScript 용 밴드(Z 구간별 둥근 사각) 목록으로 양자화.

MAIN 체인 (Y >= SPLIT) 과 TAIL 체인 (Y < SPLIT) 으로 나눈다.
각 밴드는 그 구간 포락선의 **최대 사각** 이므로 항상 보수적(포함)이다.
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

OUT = sg.OUT
C = json.load(io.open(os.path.join(OUT, "cartridge_constants.json"), encoding="utf-8"))
SPLIT = -30.0            # MAIN / TAIL 경계
DECK_Z = C["DECK_Z"]
UP = np.array(C["UP_LOCAL"])


def band_rects(occ, zs, xs, ys, lo, hi, jsel):
    """Z 구간 [lo,hi] 에서 지정 Y 영역의 최대 사각."""
    k = (zs >= lo - 1e-9) & (zs <= hi + 1e-9)
    sub = occ[k][:, jsel, :]
    if not sub.any():
        return None
    _, jj, ii = np.where(sub)
    yv = ys[jsel]
    return (float(xs[ii.min()]), float(xs[ii.max()]),
            float(yv[jj.min()]), float(yv[jj.max()]))


def main():
    z = np.load(os.path.join(OUT, "conformal_envelope.npz"))
    zs, xs, ys, ext = z["zs"], z["xs"], z["ys"], z["ext"]
    jsplit = int(round((SPLIT - ys[0]) / (ys[1] - ys[0])))
    sel_main = slice(jsplit, None)
    sel_tail = slice(0, jsplit)

    zlo = float(zs[[bool(ext[k].any()) for k in range(len(zs))]].min())
    print(f"포락선 Z 범위 [{zlo:.2f}, {DECK_Z:.2f}]   MAIN/TAIL 경계 Y = {SPLIT}")

    # 밴드 경계 — 형상 변화가 큰 지점에 맞춰 수동 구획
    edges = [zlo, -143.0, -137.0, -132.0, -126.0, -116.0, -106.0, -98.0,
             -90.0, -84.0, -80.0, -76.0, -72.0, -68.0, -65.0, -63.0, DECK_Z]
    edges = sorted(set(round(e, 4) for e in edges))

    main, tail = [], []
    print("\nMAIN 체인")
    print(f"{'z0':>9s} {'z1':>9s} | {'X':>17s} {'Y':>17s} {'크기':>15s}")
    for a, b in zip(edges[:-1], edges[1:]):
        r = band_rects(ext, zs, xs, ys, a, b, sel_main)
        if r is None:
            continue
        main.append({"z0": a, "z1": b, "x0": r[0], "x1": r[1], "y0": r[2], "y1": r[3]})
        print(f"{a:9.2f} {b:9.2f} | {r[0]:7.1f}..{r[1]:7.1f} {r[2]:7.1f}..{r[3]:7.1f} "
              f"{r[1]-r[0]:6.1f} x {r[3]-r[2]:6.1f}")

    print("\nTAIL 체인")
    for a, b in zip(edges[:-1], edges[1:]):
        r = band_rects(ext, zs, xs, ys, a, b, sel_tail)
        if r is None:
            continue
        tail.append({"z0": a, "z1": b, "x0": r[0], "x1": r[1], "y0": r[2], "y1": r[3]})
        print(f"{a:9.2f} {b:9.2f} | {r[0]:7.1f}..{r[1]:7.1f} {r[2]:7.1f}..{r[3]:7.1f} "
              f"{r[1]-r[0]:6.1f} x {r[3]-r[2]:6.1f}")

    # 캐비티 부피 (밴드 근사)
    vol = sum((m["x1"] - m["x0"]) * (m["y1"] - m["y0"]) * (m["z1"] - m["z0"])
              for m in main)
    vol += sum((t["x1"] - t["x0"]) * (t["y1"] - t["y0"]) * (t["z1"] - t["z0"])
               for t in tail)
    print(f"\n밴드 근사 캐비티 부피 = {vol/1000:.1f} cm3  (실 포락선 266.3 cm3)")

    # 월드수직 최저 (스톡 전체)
    N = sg.load(neutral=True)
    low = min(float((N[k].reshape(-1, 3) @ UP).min()) for k in N)
    print(f"스톡 월드수직 최저 = {low:.4f}")

    json.dump({"main": main, "tail": tail, "split": SPLIT, "z_low": zlo,
               "deck_z": DECK_Z, "cavity_vol_mm3": vol, "stock_low_world": low},
              io.open(os.path.join(OUT, "conformal_bands.json"), "w", encoding="utf-8"),
              indent=1)
    print("\n저장: conformal_bands.json")


if __name__ == "__main__":
    main()
