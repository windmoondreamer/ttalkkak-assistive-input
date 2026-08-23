"""선정 후보 축에 대한 최종 종합 평가표 (READ ONLY)."""
import sys, json, math, os
sys.path.insert(0, os.path.dirname(__file__))
from axis_opt import *
from axis_eval import *
import numpy as np


def pocket_x(i, a, sign):
    c, A, h = obb(P[i], a, POCKET, SW + 0.2, SW_FRONT)
    xs = [(c + A.T @ (np.array([p, q, r], float) * h))[0]
          for p in (-1, 1) for q in (-1, 1) for r in (-1, 1)]
    return max(xs) if sign > 0 else min(xs)


def report(nm, A):
    B = [obb(P[i], A[i], SW, SW, SW_FRONT) for i in range(4)]
    print(f"\n########## {nm} ##########")
    cl = {}
    for i, j in PAIRS:
        hit, v = sat(B[i], B[j])
        cl[(i, j)] = -v if hit else exact_gap(B[i], B[j])
    print("  스위치 몸체 여유: " + "  ".join(f"{NAMES[i]}-{NAMES[j]} {cl[(i,j)]:6.3f}" for i, j in PAIRS))
    mn = min(cl.values())
    print(f"     -> 최소 {mn:.3f} mm,  포켓 사이 칸막이 {mn-0.4:.3f} mm")
    print(f"  {'':4}{'축':>32}{'dev':>8}{'캡쐐기':>8}{'측하중':>8}{'보어-개구':>10}"
          f"{'홀더앞-캡':>10}{'나사B':>7}{'외피돌출':>9}{'분할면벽':>9}")
    rows = []
    for i in range(4):
        a = A[i]
        d = math.degrees(math.acos(np.clip(np.dot(N0[i], a), -1, 1)))
        pr, fr = protrusion(i, a)
        px = pocket_x(i, a, +1 if DOM[i] else -1)
        wall = -px if DOM[i] else px
        rows.append(dict(name=NAMES[i], axis=list(map(float, a)), dev=d,
                         wedge=CAP_W * math.tan(math.radians(d)),
                         side=math.tan(math.radians(d)),
                         bore=bore_vs_opening(i, a), capint=holder_front_vs_cap(i, a),
                         screw=screw_gap(i, a), prot=pr, protfrac=fr, splitwall=wall,
                         rear=rear_in_wall(i, a)))
        r = rows[-1]
        print(f"  {NAMES[i]:<4}({a[0]:+.4f},{a[1]:+.4f},{a[2]:+.4f}){d:7.2f}°{r['wedge']:8.2f}"
              f"{r['side']:8.2f}{r['bore']:10.3f}{r['capint']:10.3f}{r['screw']:7.2f}"
              f"{r['prot']:9.2f}{wall:9.2f}")
    return dict(name=nm, clr={f"{NAMES[i]}-{NAMES[j]}": cl[(i, j)] for i, j in PAIRS},
                minclr=mn, rows=rows)
