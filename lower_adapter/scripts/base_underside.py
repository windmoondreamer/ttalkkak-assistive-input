"""Base 밑면 지도 — 카트리지 캐리어 접촉면 / 전장 릴리프 범위 확정."""
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


def first_hit_up(P, xy, z0=-160.0):
    """+Z 로 쏘아 처음 만나는 면의 Z (없으면 nan)."""
    v0, v1, v2 = P[:, 0], P[:, 1], P[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    d = np.array([0.0, 0.0, 1.0])
    h = np.cross(d, e2)
    a = (e1 * h).sum(1)
    m = np.abs(a) > 1e-12
    f = np.where(m, 1.0 / np.where(m, a, 1.0), 0.0)
    out = np.full(len(xy), np.nan)
    lastz = np.full(len(xy), np.nan)
    for i, (x, y) in enumerate(xy):
        s = np.stack([x - v0[:, 0], y - v0[:, 1], z0 - v0[:, 2]], 1)
        u = f * (s * h).sum(1)
        q = np.cross(s, e1)
        v = f * (q * d).sum(1)
        t = f * (e2 * q).sum(1)
        ok = m & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 0)
        if ok.any():
            tt = np.sort(t[ok])
            out[i] = z0 + tt[0]
            lastz[i] = z0 + tt[-1]
    return out, lastz


def main():
    N = sg.load(neutral=True)
    B = N["Base <1>"]
    V = B.reshape(-1, 3)
    lo, hi = V.min(0), V.max(0)
    BOT = lo[2]
    print(f"Base bbox X[{lo[0]:.3f},{hi[0]:.3f}] Y[{lo[1]:.3f},{hi[1]:.3f}] "
          f"Z[{lo[2]:.3f},{hi[2]:.3f}]")

    step = 0.5
    xs = np.arange(lo[0] + step / 2, hi[0], step)
    ys = np.arange(lo[1] + step / 2, hi[1], step)
    XY = [(x, y) for y in ys for x in xs]
    first, _ = first_hit_up(B, XY)
    F = first.reshape(len(ys), len(xs))

    flat = np.abs(F - BOT) < 0.05
    solid = ~np.isnan(F)
    print(f"\n격자 {len(xs)} x {len(ys)} @ {step} mm")
    print(f"  Base 투영 면적            {solid.sum()*step*step:9.1f} mm^2")
    print(f"  밑면 평면(Z={BOT:.4f}) 면적 {flat.sum()*step*step:9.1f} mm^2 "
          f"({100*flat.sum()/max(solid.sum(),1):.1f}%)")

    # 밑면보다 위로 들어간(리세스) 영역
    rec = solid & ~flat
    if rec.any():
        zr = F[rec]
        print(f"  리세스 영역               {rec.sum()*step*step:9.1f} mm^2  "
              f"Z {zr.min():.3f} ~ {zr.max():.3f} (밑면 위 {zr.min()-BOT:+.3f} ~ {zr.max()-BOT:+.3f})")
        # 리세스 레벨 분포
        vals, cnt = np.unique(np.round(zr, 2), return_counts=True)
        top = sorted(zip(cnt, vals), reverse=True)[:8]
        print("    주요 레벨: " + ", ".join(f"Z={v:.2f}({c*step*step:.0f}mm2)" for c, v in top))

    # 구멍(재료 없음) 영역
    holes = np.isnan(F)
    print(f"  구멍/개구 영역             {holes.sum()*step*step:9.1f} mm^2")

    # 전장 릴리프 필요 범위 (밑면 아래로 튀어나온 전장 부품)
    env = json.load(io.open(os.path.join(sg.OUT, "wiring_envelope.json"), encoding="utf-8"))
    el, eh = np.array(env["mcu_usb_bbox"][0]), np.array(env["mcu_usb_bbox"][1])
    print(f"\n전장(MCU/USB) X[{el[0]:.2f},{eh[0]:.2f}] Y[{el[1]:.2f},{eh[1]:.2f}] "
          f"Z[{el[2]:.2f},{eh[2]:.2f}]")
    print(f"  밑면 아래로 {BOT-el[2]:.3f} mm 돌출")

    # ASCII 지도
    print("\n밑면 지도 (2mm 격자): '=' 평면접촉  '-' 리세스  '.' 구멍  ' ' 없음")
    sx = max(1, int(round(2.0 / step)))
    for j in range(len(ys) - 1, -1, -sx):
        row = []
        for i in range(0, len(xs), sx):
            if np.isnan(F[j, i]):
                row.append('.')
            elif flat[j, i]:
                row.append('=')
            else:
                row.append('-')
        print(f"  Y={ys[j]:7.1f} |" + "".join(row))
    print("           X= " + f"{xs[0]:.0f} .. {xs[-1]:.0f}")

    np.save(os.path.join(sg.OUT, "base_underside_first.npy"), F)
    json.dump({"bottom_z": float(BOT), "step": step,
               "x0": float(xs[0]), "y0": float(ys[0]),
               "flat_area": float(flat.sum() * step * step),
               "proj_area": float(solid.sum() * step * step)},
              io.open(os.path.join(sg.OUT, "base_underside.json"), "w",
                      encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
