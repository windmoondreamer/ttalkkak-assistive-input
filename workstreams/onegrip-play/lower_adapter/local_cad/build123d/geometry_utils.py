"""build123d 공통 유틸 — STEP 메타데이터 / bbox / 부피 / 왕복 비교.

Onshape API 를 호출하지 않는다. 순수 로컬 OpenCascade 작업이다.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import parameters as P    # noqa: E402


def b3d():
    """build123d 를 늦게 임포트한다 (미설치 시 명확한 안내)."""
    try:
        import build123d as bd
    except ImportError as e:                       # noqa: BLE001
        raise SystemExit(
            "build123d 가 없다. 격리 환경으로 실행할 것:\n"
            "  .venv-build123d/Scripts/python "
            "lower_adapter/local_cad/build123d/<script>.py\n"
            f"(원인: {e})")
    return bd


# ---------------------------------------------------------------- 측정

def solids_of(shape):
    """Compound / Part / Solid 어느 쪽이 와도 Solid 리스트로."""
    try:
        return list(shape.solids())
    except Exception:                              # noqa: BLE001
        return [shape]


def describe(shape, name="shape"):
    """solid 수 / bbox / 부피 / 중심을 dict 로."""
    sol = solids_of(shape)
    bb = shape.bounding_box()
    vol = sum(float(s.volume) for s in sol)
    c = shape.center()
    return {
        "name": name,
        "solids": len(sol),
        "bbox_min": [float(bb.min.X), float(bb.min.Y), float(bb.min.Z)],
        "bbox_max": [float(bb.max.X), float(bb.max.Y), float(bb.max.Z)],
        "size": [float(bb.size.X), float(bb.size.Y), float(bb.size.Z)],
        "volume": vol,
        "center": [float(c.X), float(c.Y), float(c.Z)],
    }


def fmt(d):
    return (f"  {d['name']:<34s} solid {d['solids']:>3d}  "
            f"{d['size'][0]:8.3f} x {d['size'][1]:8.3f} x {d['size'][2]:8.3f}  "
            f"vol {d['volume']:14,.2f} mm3")


def bbox_delta(a, b):
    return max(max(abs(a["bbox_min"][i] - b["bbox_min"][i]) for i in range(3)),
               max(abs(a["bbox_max"][i] - b["bbox_max"][i]) for i in range(3)))


def volume_rel_delta(a, b):
    if a["volume"] == 0:
        return abs(b["volume"])
    return abs(a["volume"] - b["volume"]) / abs(a["volume"])


def compare(a, b, tol_bbox=None, tol_vol=None):
    """원본 vs 왕복본. (통과여부, 상세) 반환."""
    tol_bbox = P.TOL_ROUNDTRIP_BBOX if tol_bbox is None else tol_bbox
    tol_vol = P.TOL_ROUNDTRIP_VOL if tol_vol is None else tol_vol
    db = bbox_delta(a, b)
    dv = volume_rel_delta(a, b)
    ds = a["solids"] == b["solids"]
    ok = ds and db <= tol_bbox and dv <= tol_vol
    return ok, {"solid_match": ds, "bbox_delta_mm": db, "volume_rel_delta": dv,
                "tol_bbox_mm": tol_bbox, "tol_volume_rel": tol_vol}


# ---------------------------------------------------------------- 입출력

def import_step(path, name=None):
    bd = b3d()
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    shape = bd.import_step(path)
    return shape, describe(shape, name or os.path.basename(path))


def export_all(shape, stem, step_dir=None, stl_dir=None, brep_dir=None,
               tolerance=0.02, angular_tolerance=0.1):
    """STEP(설계 마스터) / STL(슬라이싱) / BREP 를 한 번에 내보낸다."""
    bd = b3d()
    out = {}
    step_dir = step_dir or P.EXPORT_STEP
    stl_dir = stl_dir or P.EXPORT_STL
    brep_dir = brep_dir or P.EXPORT_BREP
    for d in (step_dir, stl_dir, brep_dir):
        os.makedirs(d, exist_ok=True)

    # **STEP 을 쓰기 전에** 기존 tessellation 을 지운다.
    # (1) 남아 있으면 STEP 에 메시가 섞여 들어가 edges 가 1,180 대신 165,939 로
    #     보고된다. (2) 지우지 않으면 `export_stl` 의 tolerance 가 무시된다
    #     (실측: 0.010 과 0.030 이 둘 다 300,635 삼각형).
    from OCP.BRepTools import BRepTools
    BRepTools.Clean_s(shape.wrapped)

    p = os.path.join(step_dir, f"{stem}.step")
    bd.export_step(shape, p)
    out["step"] = p
    p = os.path.join(stl_dir, f"{stem}.stl")
    bd.export_stl(shape, p, tolerance=tolerance,
                  angular_tolerance=angular_tolerance)
    out["stl"] = p
    try:
        p = os.path.join(brep_dir, f"{stem}.brep")
        bd.export_brep(shape, p)
        out["brep"] = p
    except Exception as e:                         # noqa: BLE001
        out["brep_error"] = str(e)
    return out


def roundtrip(shape, stem, tmp_dir=None):
    """STEP 으로 내보냈다 다시 읽어 원본과 비교한다.

    build123d 0.11.1 의 `export_step` 은 **3단 이상 중첩된 Compound**
    (Onshape 어셈블리를 import_step 한 결과) 를 쓰지 못하고
    `RuntimeError: Failed to write STEP file` 을 낸다.
    label 을 전부 채워도 실패하고, solid 를 1단으로 재구성하면 성공한다.
    -> 입력 STEP 의 문제가 아니라 exporter 제약이다.
    실패하면 평탄화해서 **형상 왕복**(solid/bbox/volume)만 검증하고 그 사실을 기록한다.
    """
    bd = b3d()
    tmp_dir = tmp_dir or P.EXPORT_STEP
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, f"{stem}_ROUNDTRIP.step")
    flattened = False
    try:
        bd.export_step(shape, path)
    except RuntimeError:
        flattened = True
        bd.export_step(bd.Compound(children=list(shape.solids())), path)
    back = bd.import_step(path)
    a = describe(shape, stem)
    b = describe(back, stem + "_ROUNDTRIP")
    ok, detail = compare(a, b)
    detail["path"] = path
    detail["flattened"] = flattened
    return ok, a, b, detail


# ---------------------------------------------------------------- STL 검사

def stl_check(path):
    """STL 이 watertight/manifold 인지 가볍게 확인 (외부 의존 없음)."""
    import struct
    with open(path, "rb") as f:
        head = f.read(5)
        f.seek(0)
        if head == b"solid":
            tris = []
            v = []
            for line in f:
                s = line.split()
                if s and s[0] == b"vertex":
                    v.append(tuple(round(float(x), 6) for x in s[1:4]))
                    if len(v) == 3:
                        tris.append(tuple(v))
                        v = []
        else:
            f.seek(80)
            n = struct.unpack("<I", f.read(4))[0]
            tris = []
            for _ in range(n):
                d = struct.unpack("<12fH", f.read(50))
                tris.append(tuple(tuple(round(d[3 + 3 * k + j], 6) for j in range(3))
                                  for k in range(3)))
    edges = {}
    for t in tris:
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            key = (a, b) if a < b else (b, a)
            edges[key] = edges.get(key, 0) + 1
    bad = sum(1 for c in edges.values() if c != 2)
    return {"triangles": len(tris), "edges": len(edges),
            "non_manifold_edges": bad, "watertight": bad == 0}


# ---------------------------------------------------------------- 메시 충돌 (교차검사용)

def read_stl_tris(path):
    """STL -> (N,3,3) 삼각형.  **정밀 CAD source 가 아니라 충돌 교차검사용**이다."""
    import struct
    import numpy as np
    with open(path, "rb") as f:
        head = f.read(5)
        f.seek(0)
        if head == b"solid":
            v = []
            for line in f:
                s = line.split()
                if s and s[0] == b"vertex":
                    v.append([float(x) for x in s[1:4]])
            return np.array(v, dtype=float).reshape(-1, 3, 3)
        f.seek(80)
        n = struct.unpack("<I", f.read(4))[0]
        t = np.empty((n, 3, 3))
        for i in range(n):
            d = struct.unpack("<12fH", f.read(50))
            t[i] = np.array(d[3:12]).reshape(3, 3)
        return t


def mesh_inside(tris, pts, cell=6.0):
    """+Z 레이 패리티 내부 판정 (XY 버킷 가속).

    공유 모서리를 정확히 스치면 같은 t 가 두 번 잡혀 패리티가 뒤집히므로
    교차점 중복을 제거한다.
    """
    import numpy as np
    pts = np.asarray(pts, dtype=float)
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    d = np.array([0.0, 0.0, 1.0])
    h = np.cross(d, e2)
    a = (e1 * h).sum(1)
    m = np.abs(a) > 1e-12
    f = np.where(m, 1.0 / np.where(m, a, 1.0), 0.0)
    tlo = tris[:, :, :2].min(1)
    thi = tris[:, :, :2].max(1)
    lo, hi = tlo.min(0), thi.max(0)
    nx = max(1, int(np.ceil((hi[0] - lo[0]) / cell)))
    ny = max(1, int(np.ceil((hi[1] - lo[1]) / cell)))
    buckets = {}
    i0 = np.clip(((tlo[:, 0] - lo[0]) / cell).astype(int), 0, nx - 1)
    i1 = np.clip(((thi[:, 0] - lo[0]) / cell).astype(int), 0, nx - 1)
    j0 = np.clip(((tlo[:, 1] - lo[1]) / cell).astype(int), 0, ny - 1)
    j1 = np.clip(((thi[:, 1] - lo[1]) / cell).astype(int), 0, ny - 1)
    for t in range(len(tris)):
        for i in range(i0[t], i1[t] + 1):
            for j in range(j0[t], j1[t] + 1):
                buckets.setdefault((i, j), []).append(t)
    buckets = {k: np.array(v) for k, v in buckets.items()}
    res = np.zeros(len(pts), bool)
    pi = np.clip(((pts[:, 0] - lo[0]) / cell).astype(int), -1, nx)
    pj = np.clip(((pts[:, 1] - lo[1]) / cell).astype(int), -1, ny)
    for n in range(len(pts)):
        idx = buckets.get((pi[n], pj[n]))
        if idx is None:
            continue
        s = pts[n] - v0[idx]
        u = f[idx] * (s * h[idx]).sum(1)
        q = np.cross(s, e1[idx])
        vv = f[idx] * (q * d).sum(1)
        tt = f[idx] * (e2[idx] * q).sum(1)
        ok = m[idx] & (u >= 0) & (vv >= 0) & (u + vv <= 1) & (tt > 1e-9)
        z = np.sort(tt[ok])
        if len(z):
            z = z[np.concatenate(([True], np.diff(z) > 1e-4))]
        res[n] = (len(z) % 2) == 1
    return res


def shape_valid(shape):
    """BRepCheck_Analyzer 유효성."""
    from OCP.BRepCheck import BRepCheck_Analyzer
    return bool(BRepCheck_Analyzer(shape.wrapped).IsValid())


def shell_volumes(shape):
    """solid 를 이루는 shell 별 |부피| 목록."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    out = []
    for sh in shape.shells():
        g = GProp_GProps()
        BRepGProp.VolumeProperties_s(sh.wrapped, g)
        out.append((sh, abs(g.Mass())))
    return out


def heal(shape, min_void=1.0, label="", fill_voids=False):
    """불리언 잔해 제거.

    OCC 는 동일면 접합(coincident-face) 불리언에서 종잇장 두께의 **내부 공동
    shell** 을 남기는 일이 있다. 그 solid 는 `BRepCheck_Analyzer` 에서 invalid
    이고, 이후 모든 boolean 이 조용히 빈 결과를 돌려준다 (간섭 검사가 통째로
    무의미해진다). 여기서 (1) min_void 미만의 공동 shell 을 버리고
    (2) ShapeFix_Shape 로 다듬은 뒤 (3) 유효성을 다시 확인한다.
    """
    import numpy as _np
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid
    from OCP.ShapeFix import ShapeFix_Shape
    from OCP.TopoDS import TopoDS
    bd = b3d()

    tag = f"[heal{(' ' + label) if label else ''}]"
    sv = shell_volumes(shape)
    dropped = []
    obj = shape
    if len(sv) > 1:
        vols = [v for _s, v in sv]
        outer = int(_np.argmax(vols))
        thr = float("inf") if fill_voids else min_void
        keep, dropped = [], []
        for i, (sh, v) in enumerate(sv):
            if i == outer:
                keep.append(sh)
                continue
            # **부피가 아니라 두께로 판별한다.** 동일면 접합 잔해는 넓지만
            # 종잇장이라 부피 임계값을 넘길 수 있다
            # (실측: 101.6 x 3.77 x 1.19 mm = 58.8 mm3).
            b = sh.bounding_box()
            thin = min(float(b.size.X), float(b.size.Y),
                       float(b.size.Z)) < 2.0
            if v < thr or thin:
                dropped.append(v)
            else:
                keep.append(sh)
        if dropped:
            mk = BRepBuilderAPI_MakeSolid()
            for sh in keep:
                mk.Add(TopoDS.Shell_s(sh.wrapped))
            obj = bd.Solid(mk.Solid())
            print(f"  {tag} sliver 공동 shell {len(dropped)}개 제거 "
                  f"({', '.join(f'{v:.3f}' for v in dropped)} mm3)")

    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_ShapeEnum
    fx = ShapeFix_Shape(obj.wrapped)
    fx.Perform()
    ex = TopExp_Explorer(fx.Shape(), TopAbs_ShapeEnum.TopAbs_SOLID)
    fs = []
    while ex.More():
        fs.append(bd.Solid(TopoDS.Solid_s(ex.Current())))
        ex.Next()
    if len(fs) == 1:
        obj = fs[0]
    elif len(fs) > 1:
        raise SystemExit(f"STOP - {tag} ShapeFix 결과가 solid {len(fs)}개로 "
                         "분할됐다. 근사 우회 금지 (§25).")

    ok = shape_valid(obj)
    print(f"  {tag} valid={ok}  shells={len(list(obj.shells()))}  "
          f"faces={len(list(obj.faces()))}  vol={float(obj.volume):,.4f}")
    if not ok:
        from OCP.BRepCheck import BRepCheck_Analyzer
        print(f"  {tag} --- 진단 ---")
        for i, (sh, v) in enumerate(shell_volumes(obj)):
            b = sh.bounding_box()
            print(f"    shell[{i}] faces={len(list(sh.faces())):4d} "
                  f"|vol|={v:12,.3f}  size {b.size.X:7.2f} x {b.size.Y:7.2f} "
                  f"x {b.size.Z:7.2f}  @ ({b.center().X:.2f},"
                  f"{b.center().Y:.2f},{b.center().Z:.2f})")
        for i, f in enumerate(obj.faces()):
            if BRepCheck_Analyzer(f.wrapped).IsValid():
                continue
            b = f.bounding_box()
            print(f"    invalid face[{i}] area={float(f.area):10,.4f} "
                  f"size {b.size.X:7.3f} x {b.size.Y:7.3f} x {b.size.Z:7.3f} "
                  f"@ ({b.center().X:.2f},{b.center().Y:.2f},{b.center().Z:.2f})")
        raise SystemExit(f"STOP - {tag} 치유 후에도 invalid solid. "
                         "근사 우회 금지 (§25). 원인부터 해결할 것.")
    return obj
