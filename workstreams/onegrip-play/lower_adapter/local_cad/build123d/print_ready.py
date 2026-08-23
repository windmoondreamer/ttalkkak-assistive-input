"""PRINT_READY 파생 모델 조립.

REV D product body 를 **강체 변환만** 해서 print orientation 에 놓고
(형상 수정 0), 그 위에 CAD sacrificial support 를 **별도 solid 로** 얹는다.

  MAIN     Rx -90  -> CUT FACE UP
  ARMREST  Rx -90  -> CUT FACE DOWN

산출:
  {nm}_PRINT_READY_{mat}.step                product + support (solid 분리 유지)
  HOUSING_V4_{nm}_PRINT_READY_{mat}.stl      슬라이서 투입용 (multi-shell 허용)
  {nm}_PRODUCT_ONLY_{mat}.step               body-only 대조군 (support 제거 상태)
"""
from __future__ import annotations
import os
import sys
import json
import math
import hashlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                       # noqa: E402
import geometry_utils as G                   # noqa: E402
import build123d as bd                       # noqa: E402
from OCP.BRepTools import BRepTools          # noqa: E402

LOCAL = os.path.dirname(HERE)
DUMP = os.path.join(os.path.dirname(LOCAL), "cad_dump")
PARTS = {"MAIN": ("HOUSING_V4_MAIN_PRINT_REV_D", "CUT FACE UP"),
         "ARMREST": ("HOUSING_V4_ARMREST_PRINT_REV_D", "CUT FACE DOWN")}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def stl_qc(path):
    T = G.read_stl_tris(path)
    q = np.round(T.reshape(-1, 3), 5)
    _u, inv = np.unique(q, axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    ed = {}
    for t in inv:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            k = (t[a], t[b]) if t[a] < t[b] else (t[b], t[a])
            ed[k] = ed.get(k, 0) + 1
    bnd = sum(1 for v in ed.values() if v == 1)
    nmf = sum(1 for v in ed.values() if v > 2)
    d = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    return {"tri": int(len(T)), "boundary": bnd, "nonmanifold": nmf,
            "degenerate": int((d < 1e-9).sum()),
            "watertight": bool(bnd == 0 and nmf == 0)}


def main():
    mat = sys.argv[1] if len(sys.argv) > 1 else "PLA"
    out = {}
    print("=== PRINT_READY 조립 (%s) ===" % mat)
    for nm, (fn, lab) in PARTS.items():
        sp = os.path.join(P.EXPORT_STEP, "%s_CUSTOM_SUPPORT_%s.step" % (nm, mat))
        z0, ang = np.load(os.path.join(DUMP, "_sup_z0_%s.npy" % nm))
        prod = bd.import_step(os.path.join(P.EXPORT_STEP, fn + ".step")).solids()[0]
        v_before = float(prod.volume)
        pp = prod.rotate(bd.Axis.X, float(ang)).moved(bd.Location((0, 0, -z0)))
        v_after = float(pp.volume)
        bb = pp.bounding_box()
        print("\n--- %s  (%s, Rx %+.0f) ---" % (nm, lab, ang))
        print("  product 부피  %.6f -> %.6f   (차 %.3e mm3, 강체변환)"
              % (v_before, v_after, abs(v_after - v_before)))
        print("  print bbox   %.3f x %.3f x %.3f   바닥 z=%.6f"
              % (bb.size.X, bb.size.Y, bb.size.Z, bb.min.Z))
        r = {"orientation": lab, "rot_x": float(ang),
             "product_volume": v_after,
             "rigid_delta_mm3": abs(v_after - v_before),
             "print_bbox": [bb.size.X, bb.size.Y, bb.size.Z],
             "bed_z": bb.min.Z}

        # body-only 대조군 = support 제거 후 남는 것
        BRepTools.Clean_s(pp.wrapped)
        bd.export_step(pp, os.path.join(P.EXPORT_STEP,
                                        "%s_PRODUCT_ONLY_%s.step" % (nm, mat)))

        if os.path.exists(sp):
            sup = bd.import_step(sp)
            ssol = sup.solids()
            sv = sum(float(s.volume) for s in ssol)
            comp = bd.Compound(children=[pp] + list(ssol))
            r["support_volume"] = sv
            r["support_solids"] = len(ssol)
            print("  support      solid %d개 / %.1f mm3 (%.1f g PLA)"
                  % (len(ssol), sv, sv * 1.24e-3))
        else:
            comp = bd.Compound(children=[pp])
            r["support_volume"] = 0.0
            r["support_solids"] = 0
            print("  support      없음")

        BRepTools.Clean_s(comp.wrapped)
        ps = os.path.join(P.EXPORT_STEP, "%s_PRINT_READY_%s.step" % (nm, mat))
        bd.export_step(comp, ps)
        BRepTools.Clean_s(comp.wrapped)
        pt = os.path.join(P.EXPORT_STL,
                          "HOUSING_V4_%s_PRINT_READY_%s.stl" % (nm, mat))
        bd.export_stl(comp, pt, tolerance=0.03, angular_tolerance=0.2)
        q = stl_qc(pt)
        print("  STL  tri %d · 경계 %d · 비다양체 %d · degen %d · watertight %s"
              % (q["tri"], q["boundary"], q["nonmanifold"], q["degenerate"],
                 q["watertight"]))
        r["stl"] = q
        r["print_ready_step"] = os.path.basename(ps)
        r["print_ready_stl"] = os.path.basename(pt)
        r["stl_sha"] = sha(pt)
        out[nm] = r

    json.dump(out, open(os.path.join(LOCAL, "reports",
                                     "16_print_ready_%s.json" % mat), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nsaved: reports/16_print_ready_%s.json" % mat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
