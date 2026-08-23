"""침범 삼각형 위치 특정."""
from __future__ import annotations
import os
import sys
import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                       # noqa: E402
import geometry_utils as G                   # noqa: E402
import build123d as bd                       # noqa: E402
from support_validate import Col, rot_x, tris  # noqa: E402

LOCAL = os.path.dirname(HERE)
DUMP = os.path.join(os.path.dirname(LOCAL), "cad_dump")

nm = sys.argv[1] if len(sys.argv) > 1 else "MAIN"
fn = {"MAIN": "HOUSING_V4_MAIN_PRINT_REV_D",
      "ARMREST": "HOUSING_V4_ARMREST_PRINT_REV_D"}[nm]
z0, ang = np.load(os.path.join(DUMP, "_sup_z0_%s.npy" % nm))
prod = bd.import_step(os.path.join(P.EXPORT_STEP, fn + ".step")).solids()[0]
Tp = tris(prod) @ rot_x(ang).T
Tp[:, :, 2] -= z0
sup = bd.import_step(os.path.join(P.EXPORT_STEP,
                                  "%s_CUSTOM_SUPPORT_PLA.step" % nm))
Ts = tris(sup, 0.03)
pc = Col(Tp)
ctr = Ts.mean(1)
area = 0.5 * np.linalg.norm(np.cross(Ts[:, 1] - Ts[:, 0], Ts[:, 2] - Ts[:, 0]), axis=1)
bad = []
for k, p in enumerate(ctr):
    z = pc.hit(p[0], p[1])
    if len(z) and np.searchsorted(z, p[2]) % 2 == 1:
        d = float(np.min(np.abs(z - p[2])))
        if d > 0.10:
            bad.append((d, k))
bad.sort(reverse=True)
print("실침범 삼각형 %d개" % len(bad))
for d, k in bad[:20]:
    p = ctr[k]
    T = Ts[k]
    print("  깊이 %7.3f  중심 (%8.2f, %8.2f, %8.2f)  면적 %8.2f mm2"
          % (d, p[0], p[1], p[2], area[k]))
    print("     정점 " + " | ".join("(%.2f,%.2f,%.2f)" % tuple(v) for v in T))
    for v in T:
        z = pc.hit(v[0], v[1])
        ins = len(z) and np.searchsorted(z, v[2]) % 2 == 1
        print("       정점 내부? %s   교차 z %s"
              % (bool(ins), np.round(z, 2)[:8]))
