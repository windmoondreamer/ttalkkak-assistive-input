"""출력 자세에서 아래보기(overhang) 면을 전수 조사한다.

support 가 받친 곳 / 규칙으로 뺀 곳 / **아무것도 안 한 곳** 을 분리한다.

판정은 삼각형 **중심 하나가 아니라 면적 표본**으로 한다 — 큰 평면 삼각형
하나가 800 mm2 를 넘기도 하므로 중심 근접만 보면 틀린다.
"""
from __future__ import annotations
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                       # noqa: E402
import build123d as bd                       # noqa: E402
import custom_support as CS                  # noqa: E402
from support_validate import Col             # noqa: E402

nm = sys.argv[1] if len(sys.argv) > 1 else "ARMREST"
fn, ang = CS.PARTS[nm]

prod = CS.load(fn)
T = CS.tris_of(prod)
R = CS.rot_x(ang)
Tp = T @ R.T
z0 = Tp.reshape(-1, 3)[:, 2].min()
Tp[:, :, 2] -= z0
n = np.cross(Tp[:, 1] - Tp[:, 0], Tp[:, 2] - Tp[:, 0])
mg = np.linalg.norm(n, axis=1)
nz = np.where(mg > 1e-12, n[:, 2] / np.maximum(mg, 1e-12), 0.0)
area = 0.5 * mg
ctr = Tp.mean(1)

sc = None
sp = os.path.join(P.EXPORT_STEP, "%s_CUSTOM_SUPPORT_PLA.step" % nm)
if os.path.exists(sp):
    sc = Col(CS.tris_of(bd.import_step(sp), 0.03))

zone = CS.ZONE[nm]
V = Tp.reshape(-1, 3)
print("=== %s  overhang 감사 (Rx %+.0f, bed z=0) ===" % (nm, ang))
print("   print bbox  X %.1f~%.1f  Y %.1f~%.1f  Z %.1f~%.1f"
      % (V[:, 0].min(), V[:, 0].max(), V[:, 1].min(), V[:, 1].max(),
         V[:, 2].min(), V[:, 2].max()))
for lo, hi, lab in ((-1.01, -0.94, "0~20도 (거의 수평 천장)"),
                    (-0.94, -0.7071, "20~45도"),
                    (-0.7071, -0.5, "45~60도 (자립 가능)")):
    m = (nz > lo) & (nz <= hi)
    print("   %-24s 면적 %9.1f mm2  삼각형 %5d" % (lab, area[m].sum(), m.sum()))

need = (nz <= -0.7071) & (ctr[:, 2] > 0.35)
print("   support 필요 (45도 초과 & 플레이트 위) : %.1f mm2  삼각형 %d"
      % (area[need].sum(), need.sum()))

rng = np.random.default_rng(0)
PITCH = CS.RIB_PITCH[nm]
RMAX = PITCH / 2.0 + 0.6        # 리브 사이 중앙까지가 최대 브리지 절반
cat = {"FORBID": 0.0, "받침 있음": 0.0, "미지지": 0.0}
miss = []
bridge = []


def half_span(p):
    """이 점에서 가장 가까운 아래 받침까지의 수평 거리 (없으면 None)."""
    if sc is None:
        return None
    for d in np.arange(0.0, RMAX + 1e-9, 0.3):
        for s_ in ((0.0,) if d == 0 else (-d, d)):
            zs = sc.hit(p[0], p[1] + s_)
            lo = zs[zs < p[2]]
            if len(lo) and (p[2] - lo.max()) <= 1.2:
                return d
    return None


def sample(t, k):
    a = rng.random((k, 2))
    f = a.sum(1) > 1
    a[f] = 1 - a[f]
    return t[0] + a[:, :1] * (t[1] - t[0]) + a[:, 1:] * (t[2] - t[0])


for k in np.where(need)[0]:
    ns = int(np.clip(area[k] / 2.0, 6, 260))
    pts = sample(Tp[k], ns)
    w = area[k] / ns
    for p in pts:
        g = np.array([p[0], p[1], p[2] + z0]) @ R
        zz = zone(g)
        if zz == "FORBID":
            cat["FORBID"] += w
            continue
        d = half_span(p)
        if d is None:
            cat["미지지"] += w
            miss.append([p[0], p[1], p[2], w])
        else:
            cat["받침 있음"] += w
            bridge.append(d)

for k, v in cat.items():
    print("     %-12s %9.1f mm2" % (k, v))
if bridge:
    b = np.array(bridge)
    print("   받침까지 수평거리  평균 %.2f  최대 %.2f mm  (리브 피치 %.1f)"
          % (b.mean(), b.max(), PITCH))

if miss:
    a = np.array(miss)
    print("")
    print("   미지지 %.1f mm2 — 위치 요약" % a[:, 3].sum())
    print("     X %.1f~%.1f  Y %.1f~%.1f  Z %.1f~%.1f"
          % (a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max(),
             a[:, 2].min(), a[:, 2].max()))
    zb = np.round(a[:, 2] / 10.0) * 10
    for zv in np.unique(zb):
        m = zb == zv
        print("     z~%6.0f  %8.1f mm2   y %7.1f~%7.1f  x %7.1f~%7.1f"
              % (zv, a[m, 3].sum(), a[m, 1].min(), a[m, 1].max(),
                 a[m, 0].min(), a[m, 0].max()))
