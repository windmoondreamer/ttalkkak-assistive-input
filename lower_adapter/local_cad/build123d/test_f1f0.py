"""F1 (GROUND_TRANSITION R1.0 유지) vs F0 (그 필렛만 OFF) 비교.

형상 차이는 GROUND_TRANSITION 필렛 하나뿐이어야 한다.
STL 의 boundary / non-manifold 결함 원인을 격리한다.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402
import finalize_b as F                                    # noqa: E402

UP = np.array(P.FROZEN_UP_LOCAL)
UH = np.array(P.FROZEN_U_HAT)
GH = P.FROZEN_GROUND_WORLD_H
CASES = ["ERGO_HOUSING_W2_TEST_F1", "ERGO_HOUSING_W2_TEST_F0"]


def degenerate(tris, eps=1e-9):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    return int((np.linalg.norm(n, axis=1) / 2.0 < eps).sum())


def defect_edges(tris, nd=5, limit=6):
    key = np.round(tris, nd)
    cnt = {}
    for tr in key:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = (tuple(tr[a]), tuple(tr[b]))
            e = e if e[0] <= e[1] else (e[1], e[0])
            cnt[e] = cnt.get(e, 0) + 1
    out = []
    for k, v in cnt.items():
        if v == 2:
            continue
        c = 0.5 * (np.array(k[0]) + np.array(k[1]))
        out.append({"shared": v, "xyz": [round(float(x), 3) for x in c],
                    "u": round(float(c @ UH), 3),
                    "h": round(float(c @ UP) - GH, 3)})
        if len(out) >= limit:
            break
    return out


def main():
    bd = G.b3d()
    rep = {}
    for name in CASES:
        sp = os.path.join(P.EXPORT_STEP, name + ".step")
        st = os.path.join(P.EXPORT_STL, name + ".stl")
        if not os.path.exists(sp) or not os.path.exists(st):
            print(f"[건너뜀] {name} 산출물 없음")
            continue
        sols = bd.import_step(sp).solids()
        s0 = sols[0]
        bb = s0.bounding_box()
        tris = G.read_stl_tris(st)
        me = F.mesh_edges_report(tris, 5)
        r = {"solids": len(sols), "shells": len(list(s0.shells())),
             "faces": len(list(s0.faces())), "edges": len(list(s0.edges())),
             "valid": G.shape_valid(s0), "volume_mm3": float(s0.volume),
             "bbox": [round(float(bb.size.X), 4), round(float(bb.size.Y), 4),
                      round(float(bb.size.Z), 4)],
             "tri": int(len(tris)), "degenerate_tri": degenerate(tris), **me,
             "defects": defect_edges(tris)}
        rep[name[-2:]] = r
        print(f"\n[{name}]")
        print(f"  solid {r['solids']}  shells {r['shells']}  faces {r['faces']}"
              f"  edges {r['edges']}  valid={r['valid']}")
        print(f"  volume {r['volume_mm3']:,.4f}   bbox {r['bbox']}")
        print(f"  STL 삼각형 {r['tri']:,}  degenerate {r['degenerate_tri']}")
        print(f"  경계 {r['boundary_edges']}  비다양체 {r['nonmanifold_edges']}"
              f"  watertight {r['watertight']}")
        for d in r["defects"]:
            print(f"    결함 (공유 {d['shared']}회) {d['xyz']}  "
                  f"u {d['u']}  h {d['h']}")

    if len(rep) == 2:
        f1, f0 = rep["F1"], rep["F0"]
        print("\n" + "=" * 70)
        print(f"부피 차 (F1 - F0) = {f1['volume_mm3'] - f0['volume_mm3']:+.4f} mm3"
              f"   face 차 {f1['faces'] - f0['faces']:+d}")
        if f0["watertight"] and not f1["watertight"]:
            print("판정: 원인 = GROUND_TRANSITION R1.0 필렛  -> F0 채택")
        elif f0["watertight"] and f1["watertight"]:
            print("판정: 둘 다 watertight - 원인이 재현되지 않음")
        else:
            print("판정: F0 도 watertight=False -> 필렛 원인 아님. STOP 하고 topology 추적")
        print("=" * 70)
    json.dump(rep, open(os.path.join(P.REPORTS_DIR, "09_f1f0.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
