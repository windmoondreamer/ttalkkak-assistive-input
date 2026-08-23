"""build123d 스모크 테스트 (Phase 0, §3).

A primitive / B boolean / C fillet / D loft / E export / F re-import roundtrip.
STEP 레퍼런스가 없어도 여기까지는 진행한다. Onshape API 호출 0건.

실행:
    .venv-build123d/Scripts/python lower_adapter/local_cad/build123d/smoke_test.py
"""
from __future__ import annotations

import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402

RESULTS = []


def step(name):
    def deco(fn):
        def run(*a, **k):
            try:
                out = fn(*a, **k)
                RESULTS.append((name, True, out if isinstance(out, str) else ""))
                print(f"  [PASS] {name:<44s} {out if isinstance(out, str) else ''}")
                return out
            except Exception as e:                        # noqa: BLE001
                RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
                print(f"  [FAIL] {name:<44s} {type(e).__name__}: {e}")
                traceback.print_exc(limit=3)
                return None
        return run
    return deco


def main():
    import build123d as bd
    from build123d import (Axis, Box, BuildPart, BuildSketch, Cylinder, Plane,
                           RectangleRounded, fillet, loft)

    smoke_dir = os.path.join(P.LOCAL_CAD, "export")
    print("=" * 78)
    print("build123d 스모크 테스트")
    print("=" * 78)
    print(f"  build123d {bd.__version__}   python {sys.version.split()[0]}")
    print(f"  실행 인터프리터: {sys.executable}")
    print()

    state = {}

    # ---------------- A. primitive ----------------
    @step("A. primitive  Box 10 x 20 x 30")
    def a():
        b = Box(10, 20, 30)
        d = G.describe(b, "box")
        state["box"] = b
        assert d["solids"] == 1, d["solids"]
        assert abs(d["volume"] - 6000.0) < 1e-6, d["volume"]
        assert [round(v, 6) for v in d["size"]] == [10.0, 20.0, 30.0], d["size"]
        return f"vol {d['volume']:.1f} mm3, bbox {d['size']}"
    a()

    # ---------------- B. boolean ----------------
    @step("B. boolean    Box - Cylinder (관통홀)")
    def b():
        holed = state["box"] - Cylinder(radius=3.0, height=40.0)
        d = G.describe(holed, "holed")
        state["holed"] = holed
        import math
        expect = 6000.0 - math.pi * 9.0 * 30.0
        assert d["solids"] == 1, d["solids"]
        assert abs(d["volume"] - expect) / expect < 1e-3, (d["volume"], expect)
        return f"vol {d['volume']:.2f} (해석 {expect:.2f})"
    b()

    # ---------------- C. fillet ----------------
    @step("C. fillet     수직 모서리 4개 R1.5")
    def c():
        holed = state["holed"]
        # 의미 기반 선택: Z 축에 평행한 외곽 수직 모서리 (§10)
        verts = holed.edges().filter_by(Axis.Z).group_by(Axis.Z)[-1]
        verts = holed.edges().filter_by(Axis.Z)
        outer = [e for e in verts
                 if abs(e.center().X) > 4.0 and abs(e.center().Y) > 9.0]
        assert len(outer) == 4, f"수직 외곽 모서리 {len(outer)}개"
        f = fillet(outer, radius=1.5)
        d = G.describe(f, "filleted")
        state["filleted"] = f
        assert d["solids"] == 1
        assert d["volume"] < G.describe(holed, "x")["volume"]
        return f"모서리 {len(outer)}개, vol {d['volume']:.2f}"
    c()

    # ---------------- D. loft ----------------
    @step("D. loft       rounded 40x30 -> 20x24, 높이 25")
    def d():
        with BuildPart() as lp:
            with BuildSketch(Plane.XY):
                RectangleRounded(40, 30, 6)
            with BuildSketch(Plane.XY.offset(25)):
                RectangleRounded(20, 24, 4)
            loft()
        part = lp.part
        dd = G.describe(part, "loft")
        state["loft"] = part
        assert dd["solids"] == 1, dd["solids"]
        assert dd["volume"] > 0
        assert abs(dd["size"][2] - 25.0) < 1e-6, dd["size"]
        return f"vol {dd['volume']:.2f}, bbox {[round(v,2) for v in dd['size']]}"
    d()

    # ---------------- E. export ----------------
    @step("E. export     STEP / STL / BREP")
    def e():
        out = G.export_all(state["loft"], "SMOKE_LOFT")
        for k in ("step", "stl"):
            assert os.path.exists(out[k]), out
        sizes = {k: os.path.getsize(v) for k, v in out.items()
                 if isinstance(v, str) and os.path.exists(v)}
        state["export"] = out
        return " ".join(f"{k} {v/1024:.0f}KB" for k, v in sizes.items())
    e()

    # ---------------- F. re-import roundtrip ----------------
    @step("F. roundtrip  STEP 재임포트 (solid/bbox/volume)")
    def f():
        ok, orig, back, det = G.roundtrip(state["loft"], "SMOKE_LOFT")
        state["roundtrip"] = det
        msg = (f"solid {orig['solids']}->{back['solids']}  "
               f"bbox delta {det['bbox_delta_mm']:.3e} mm  "
               f"vol rel delta {det['volume_rel_delta']:.3e}")
        assert ok, msg
        return msg
    f()

    # ---------------- 부가: STL manifold ----------------
    @step("G. STL        watertight / manifold 검사")
    def g():
        p = state["export"]["stl"]
        r = G.stl_check(p)
        state["stl"] = r
        assert r["watertight"], r
        return f"{r['triangles']} tri, non-manifold edge {r['non_manifold_edges']}"
    g()

    # ---------------- 요약 ----------------
    npass = sum(1 for _, ok, _ in RESULTS if ok)
    print()
    print("=" * 78)
    print(f"결과: PASS {npass} / {len(RESULTS)}")
    print("=" * 78)

    os.makedirs(P.REPORTS_DIR, exist_ok=True)
    json.dump({"build123d": bd.__version__,
               "python": sys.version.split()[0],
               "executable": sys.executable,
               "results": [{"step": n, "pass": ok, "detail": d}
                           for n, ok, d in RESULTS],
               "roundtrip": state.get("roundtrip"),
               "stl": state.get("stl")},
              open(os.path.join(P.REPORTS_DIR, "smoke_test.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    print("저장: lower_adapter/local_cad/reports/smoke_test.json")
    return 0 if npass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
