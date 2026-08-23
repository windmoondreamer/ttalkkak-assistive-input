"""Base 밑면 윤곽 정밀 측정 — 캐리어 포켓 / 회전 구속 근거."""
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


def main():
    N = sg.load(neutral=True)
    B = N["Base <1>"]
    V = B.reshape(-1, 3)
    BOT = V[:, 2].min()

    step = 0.25
    xs = np.arange(-52, 52.001, step)
    ys = np.arange(-68, 79.001, step)
    print("Base 밑면 Z=BOT+0.01 재료 맵 계산 중...")
    z = BOT + 0.01
    occ = np.zeros((len(ys), len(xs)), bool)
    for j, y in enumerate(ys):
        sp = z_spans(B, [(x, y) for x in xs])
        occ[j] = [any(a <= z <= b for a, b in s) for s in sp]

    np.save(os.path.join(sg.OUT, "base_bottom_occ.npy"), occ)

    # 본체(Y >= -22) 와 꼬리(Y < -22) 분리
    print(f"\n{'Y':>8s}  {'Xmin':>8s} {'Xmax':>8s} {'폭':>7s}")
    prev = None
    for j, y in enumerate(ys):
        if not occ[j].any():
            row = None
        else:
            i = np.where(occ[j])[0]
            row = (xs[i[0]], xs[i[-1]])
        key = None if row is None else (round(row[0], 2), round(row[1], 2))
        if key != prev:
            if row is None:
                print(f"{y:8.2f}   (재료 없음)")
            else:
                print(f"{y:8.2f}  {row[0]:8.3f} {row[1]:8.3f} {row[1]-row[0]:7.3f}")
            prev = key

    # 180deg 회전 대칭성: 도심 기준 회전 후 일치도
    ii, jj = np.where(occ)
    P = np.stack([xs[jj], ys[ii]], 1)
    c = P.mean(0)
    print(f"\n밑면 도심 = ({c[0]:.4f}, {c[1]:.4f})")
    # occ 를 도심 중심으로 180도 회전시켜 비교
    gi = np.round((2 * c[1] - ys[ii]) / step).astype(int) + int(round((ys[0]) / -step))
    # 인덱스 매핑 다시 (간단히 배열 뒤집기 + 시프트)
    R = occ[::-1, ::-1]
    # 도심 정렬 시프트
    ci = (len(ys) - 1) - 2 * int(round((c[1] - ys[0]) / step))
    cj = (len(xs) - 1) - 2 * int(round((c[0] - xs[0]) / step))
    Rs = np.zeros_like(occ)
    for j in range(len(ys)):
        sj = j + ci
        if 0 <= sj < len(ys):
            for i in range(len(xs)):
                si = i + cj
                if 0 <= si < len(xs):
                    Rs[j, i] = R[sj, si]
    mism = np.logical_xor(occ, Rs).sum() * step * step
    print(f"180도 회전 불일치 면적 = {mism:.1f} mm^2 "
          f"(전체 {occ.sum()*step*step:.1f} mm^2 의 {100*mism/occ.sum()/step/step:.1f}%)")
    print("  -> 불일치가 크면 포켓만으로 뒤집힌 조립이 물리적으로 막힌다")

    json.dump({"bottom_z": float(BOT), "step": step,
               "x0": float(xs[0]), "y0": float(ys[0]),
               "centroid": c.tolist(),
               "rot180_mismatch_mm2": float(mism)},
              io.open(os.path.join(sg.OUT, "base_outline.json"), "w",
                      encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
