"""동결 레퍼런스 STEP 임포트 / 검사 / 무변경 왕복 (§9).

STEP 이 없으면 **아무 형상도 만들지 않고** 필요한 파일을 알려주고 종료한다 (§8).
Onshape API 호출 0건.

실행:
    .venv-build123d/Scripts/python lower_adapter/local_cad/build123d/import_reference.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402


def report_missing(req, opt):
    print("=" * 78)
    print("동결 레퍼런스 STEP 없음 — 형상 작업을 시작하지 않는다")
    print("=" * 78)
    print(f"\n  경로: {P.REFERENCE_DIR}\n")
    if req:
        print("  [필수 · 없음]")
        for n in req:
            print(f"     - {n}")
    if opt:
        print("\n  [선택 · 없음]")
        for n in opt:
            print(f"     - {n}")
    print("\n  내보내기 방법: reference/STEP_EXPORT_REQUEST.md")
    print("  (기계 코어를 근사 치수나 tessellation 캐시에서 재건하지 않는다)")


def inspect_one(key, path):
    shape, d = G.import_step(path, os.path.basename(path))
    print(G.fmt(d))
    print(f"      bbox  X[{d['bbox_min'][0]:9.3f},{d['bbox_max'][0]:9.3f}] "
          f"Y[{d['bbox_min'][1]:9.3f},{d['bbox_max'][1]:9.3f}] "
          f"Z[{d['bbox_min'][2]:9.3f},{d['bbox_max'][2]:9.3f}]")
    print(f"      center ({d['center'][0]:.3f}, {d['center'][1]:.3f}, "
          f"{d['center'][2]:.3f})")
    # 부품별 내역
    sol = G.solids_of(shape)
    if 1 < len(sol) <= 12:
        for i, s in enumerate(sol):
            bb = s.bounding_box()
            print(f"        solid {i:>2d}  {bb.size.X:8.3f} x {bb.size.Y:8.3f} x "
                  f"{bb.size.Z:8.3f}   vol {float(s.volume):12,.2f}")
    # 무변경 왕복
    ok, a, b, det = G.roundtrip(shape, os.path.splitext(os.path.basename(path))[0])
    tag = "PASS" if ok else "FAIL"
    note = "  (중첩 Compound -> 평탄화 후 왕복)" if det.get("flattened") else ""
    print(f"      roundtrip [{tag}] solid {a['solids']}->{b['solids']}  "
          f"bbox delta {det['bbox_delta_mm']:.3e} mm  "
          f"vol rel delta {det['volume_rel_delta']:.3e}{note}")
    return {"key": key, "path": path, "describe": d, "roundtrip_ok": ok,
            "roundtrip": det, "solid_count": len(sol)}


def main():
    req, opt = P.missing_references()
    have = [(k, P.reference_path(k)) for k in P.REFERENCES
            if os.path.exists(P.reference_path(k))]

    if req:
        report_missing(req, opt)
        if have:
            print("\n  [있는 파일은 그대로 검사한다]")
        else:
            return 2

    if not have:
        return 2

    print("=" * 78)
    print("동결 레퍼런스 검사 (§9)")
    print("=" * 78)
    print(f"  허용 오차: bbox {P.TOL_ROUNDTRIP_BBOX:.1e} mm, "
          f"volume rel {P.TOL_ROUNDTRIP_VOL:.1e}\n")
    out = []
    for key, path in have:
        try:
            out.append(inspect_one(key, path))
        except Exception as e:                            # noqa: BLE001
            print(f"  [FAIL] {os.path.basename(path)}  {type(e).__name__}: {e}")
            out.append({"key": key, "path": path, "error": str(e)})
        print()

    os.makedirs(P.REPORTS_DIR, exist_ok=True)
    json.dump(out, open(os.path.join(P.REPORTS_DIR, "reference_inspect.json"),
                        "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("저장: lower_adapter/local_cad/reports/reference_inspect.json")

    bad = [o for o in out if o.get("error") or not o.get("roundtrip_ok", False)]
    return 1 if (bad or req) else 0


if __name__ == "__main__":
    sys.exit(main())
