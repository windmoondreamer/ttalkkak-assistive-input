"""특정 (x,y) 컬럼에서 리브가 왜 안 세워졌는지 단계별로 찍는다."""
from __future__ import annotations
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import custom_support as CS                  # noqa: E402

nm = sys.argv[1] if len(sys.argv) > 1 else "ARMREST"
fn, ang = CS.PARTS[nm]
GAP = CS.MATERIAL["PLA"]["gap_z"]
prod = CS.load(fn)
Tp = CS.tris_of(prod) @ CS.rot_x(ang).T
z0 = Tp.reshape(-1, 3)[:, 2].min()
Tp[:, :, 2] -= z0
ray = CS.Ray(Tp)
R = CS.rot_x(ang)
zone = CS.ZONE[nm]
pitch = CS.RIB_PITCH[nm]
V = Tp.reshape(-1, 3)
ys = np.arange(V[:, 1].min() + 0.5 + pitch / 2, V[:, 1].max() - 0.5, pitch)

print("=== %s 컬럼 진단 (pitch %.1f, 행 %d개) ===" % (nm, pitch, len(ys)))
print("   행 y = %s ... %s" % (np.round(ys[:3], 1), np.round(ys[-3:], 1)))

dB = CS.RIB_T / 2 + CS.LAT_CLR
stat = {}
for yk in ys:
    cnt = {"컬럼없음": 0, "높이부족": 0, "천장아님": 0, "FORBID": 0,
           "측면막힘": 0, "OK": 0}
    for x in np.arange(V[:, 0].min() + 0.5, V[:, 0].max() - 0.5, 1.0):
        zc, nzc = ray.hit(float(x), float(yk))
        if len(zc) == 0:
            cnt["컬럼없음"] += 1
            continue
        side = [CS.free_intervals(ray.hit(float(x), float(yk + d))[0])
                for d in (-dB, dB)]
        best = None
        for (a, b, ci) in CS.free_intervals(zc):
            if b - a < CS.MIN_H + GAP:
                best = best or "높이부족"
                continue
            if nzc[ci] > -CS.DOWN_COS:
                best = best or "천장아님"
                continue
            g = np.array([x, yk, b + z0]) @ R
            if zone(g) == "FORBID":
                best = "FORBID"
                continue
            if not all(any(aa - 0.05 <= a + 0.3 and bb + 0.05 >= b - 0.3
                           for (aa, bb, _c) in fi) for fi in side):
                best = "측면막힘"
                continue
            best = "OK"
            break
        cnt[best or "높이부족"] += 1
    stat[float(yk)] = cnt

for yk, c in stat.items():
    if c["OK"] or c["FORBID"] or c["측면막힘"] or c["천장아님"]:
        print("   y %+8.1f  " % yk
              + "  ".join("%s %d" % (k, v) for k, v in c.items() if v))
