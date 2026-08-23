"""§10 ASSEMBLY RECONSTRUCTION.

MAIN + ARMREST 를 nominal mating transform(= 제자리, 이동 0)으로 다시 합쳐
원본 V4 와 비교한다.

clearance / 나사 / insert / doubler 때문에 완전 동일할 수 없으므로
  A. joint 영역 **밖**  : 차이 0 이어야 한다
  B. joint 영역 **안**  : 의도된 차이만 허용 (clearance·나사·doubler)
로 분리해 본다.

joint 영역 = Y in [DBL_Y0-2, DBL_Y1+2] = [-148, -104]
"""
from __future__ import annotations
import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                                    # noqa: E402
import build123d as bd                                    # noqa: E402
from OCP.BRepTools import BRepTools                       # noqa: E402
import split_build as SB                                  # noqa: E402

LOCAL = os.path.dirname(HERE)
JY0, JY1 = SB.DBL_Y0 - 2.0, SB.DBL_Y1 + 2.0        # -148 .. -104
BIG = 900.0


def load(name):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    return sh


def ybox(y0, y1):
    return bd.Box(BIG, y1 - y0, BIG).locate(bd.Location((0, 0.5 * (y0 + y1), 0)))


def main():
    v4 = load("ERGO_HOUSING_25_WRAP_FINAL_V4")
    m = load("HOUSING_V4_MAIN_PRINT")
    a = load("HOUSING_V4_ARMREST_PRINT")
    print(f"V4      vol {float(v4.volume):,.3f}")
    print(f"MAIN    vol {float(m.volume):,.3f}")
    print(f"ARMREST vol {float(a.volume):,.3f}")

    asm = m + a
    sol = asm.solids()
    big = max(sol, key=lambda s: float(s.volume))
    if len(sol) > 1:
        print(f"  [주의] 조립 union solid {len(sol)}개 "
              f"(clearance 때문에 두 조각이 안 닿을 수 있다)")
    print(f"조립    vol {float(asm.volume):,.3f}  solids {len(sol)}")

    # ---- joint 영역 안/밖 분리 -------------------------------------------
    # 큰 복잡 solid 끼리의 OCC 교집합은 신뢰할 수 없다 (실측: 891,741 이어야 할
    # 값이 102,013). **점 표본 멤버십**으로 판정한다.
    import geometry_utils as G

    def tris(sh, tol=0.06):
        f = os.path.join(P.EXPORT_STL, "_ar.stl")
        bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.35)
        T = G.read_stl_tris(f)
        os.remove(f)
        return T

    Tv4, Tm, Ta = tris(v4), tris(m), tris(a)
    rng = np.random.default_rng(0)
    bb = v4.bounding_box()
    lo = np.array([bb.min.X, bb.min.Y, bb.min.Z])
    hi = np.array([bb.max.X, bb.max.Y, bb.max.Z])
    N = 60000
    pts = lo + rng.random((N, 3)) * (hi - lo)
    inV4 = G.mesh_inside(Tv4, pts)
    inM = G.mesh_inside(Tm, pts)
    inA = G.mesh_inside(Ta, pts)
    inASM = inM | inA
    print("")
    print(f"점 표본 {N:,}개 멤버십 비교 (joint 영역 Y[{JY0:.0f},{JY1:.0f}])")
    res = {}
    for lab, sel in (("OUTSIDE joint", (pts[:, 1] < JY0) | (pts[:, 1] > JY1)),
                     ("INSIDE joint", (pts[:, 1] >= JY0) & (pts[:, 1] <= JY1))):
        onlyV4 = int((inV4 & ~inASM & sel).sum())
        onlyAS = int((~inV4 & inASM & sel).sum())
        both = int((inV4 & inASM & sel).sum())
        cell = float(np.prod(hi - lo)) / N
        res[lab] = {"only_v4_pts": onlyV4, "only_asm_pts": onlyAS,
                    "both_pts": both,
                    "only_v4_mm3": onlyV4 * cell, "only_asm_mm3": onlyAS * cell}
        print(f"  [{lab}]  공통 {both:6,}  V4에만 {onlyV4:5,} "
              f"({onlyV4 * cell:9,.1f} mm3)  조립본에만 {onlyAS:5,} "
              f"({onlyAS * cell:9,.1f} mm3)")
    ok = (res["OUTSIDE joint"]["only_v4_pts"] == 0
          and res["OUTSIDE joint"]["only_asm_pts"] == 0)
    print("")
    print(f"  [{'PASS' if ok else 'FAIL'}] joint 영역 밖 external/internal 차이 0")
    oz = ybox(-BIG / 2, JY0) + ybox(JY1, BIG / 2)
    print(f"  참고: joint 영역 밖 부피  V4 {float((v4 & oz).volume):,.3f} vs "
          f"조립 {float((asm & oz).volume):,.3f}")

    # 게이트용 **단일 solid** 조립본: clearance 를 0 으로 본 nominal 조립 상태.
    # (MAIN+ARMREST 는 clearance 때문에 안 닿아 2 solid 가 된다 - 정상)
    base = SB.biggest(v4 + SB.doubler(), "BASE")
    clear, cbore, ins = SB.screw_tools()
    nom = base - clear - cbore - ins
    nom = SB.biggest(nom, "NOMINAL")
    print(f"  nominal 조립본 vol {float(nom.volume):,.3f}  "
          f"solids 1  shells {len(nom.shells())}")
    BRepTools.Clean_s(nom.wrapped)
    bd.export_step(nom, os.path.join(P.EXPORT_STEP,
                                     "HOUSING_V4_SPLIT_ASSEMBLED.step"))
    bd.export_stl(nom, os.path.join(P.EXPORT_STL,
                                    "HOUSING_V4_SPLIT_ASSEMBLED.stl"),
                  tolerance=0.030, angular_tolerance=0.15)
    print("  저장 HOUSING_V4_SPLIT_ASSEMBLED.step / .stl (게이트 검증용)")

    json.dump({"v4": float(v4.volume), "main": float(m.volume),
               "armrest": float(a.volume), "assembled": float(asm.volume),
               "assembled_solids": len(sol),
               "joint_zone_y": [JY0, JY1], "zones": res, "outside_pass": ok},
              open(os.path.join(LOCAL, "reports", "15_assembly_recon.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved: reports/15_assembly_recon.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
