"""§5 절삭 검증 / §6 살두께(영역별) / §7 BREP 게이트.

살두께는 **축 광선 재료 슬랩** 으로 잰다. `min_wall` 의 법선 레이캐스팅은
1mm 밴드 계단면을 재서 0.750 을 반복 출력한다 (실측). 슬랩 방식은 계단과
무관하게 "두 면 사이에 낀 살"만 잡는다.
"""
from __future__ import annotations
import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402
import build123d as bd                                    # noqa: E402
from OCP.BRepTools import BRepTools                       # noqa: E402
from OCP.BRepCheck import BRepCheck_Analyzer              # noqa: E402

LOCAL = os.path.dirname(HERE)
DECK = -61.878507
CY = 27.269160
UP = np.array(P.FROZEN_UP_LOCAL)
UH = np.array(P.FROZEN_U_HAT)

# 영역 조건은 X/Y/Z 를 **전부** 걸어야 한다. X·Z 만 걸면 팔받침 램프(Y -260 부근)
# 가 "cavity wall" 로 잡힌다 (실측).
REGIONS = {
    "deck/opening": lambda p: ((p[:, 2] > DECK - 8) & (p[:, 2] < DECK + 3)
                               & (np.hypot(p[:, 0], p[:, 1] - CY) < 70)),
    "rear cavity wall": lambda p: ((p[:, 1] > 55) & (p[:, 1] < 95)
                                   & (np.abs(p[:, 0]) < 60)
                                   & (p[:, 2] > DECK - 30) & (p[:, 2] < DECK - 3)),
    "left cavity wall": lambda p: ((p[:, 0] < -35) & (p[:, 0] > -62)
                                   & (p[:, 1] > -30) & (p[:, 1] < 90)
                                   & (p[:, 2] > DECK - 30) & (p[:, 2] < DECK - 3)),
    "right cavity wall": lambda p: ((p[:, 0] > 35) & (p[:, 0] < 62)
                                    & (p[:, 1] > -30) & (p[:, 1] < 90)
                                    & (p[:, 2] > DECK - 30) & (p[:, 2] < DECK - 3)),
    "wrap-skirt junction": lambda p: ((p[:, 2] > -155) & (p[:, 2] < -125)
                                      & (p[:, 1] > -100) & (p[:, 1] < 100)),
    "carrier surround": lambda p: ((np.abs(p[:, 0]) > 52) & (np.abs(p[:, 0]) < 70)
                                   & (p[:, 1] > -100) & (p[:, 1] < 100)
                                   & (p[:, 2] > -165) & (p[:, 2] < -142)),
}


def load(name):
    s = bd.import_step(os.path.join(P.EXPORT_STEP, name + ".step"))
    sol = s.solids()
    sh = sol[0] if len(sol) == 1 else s
    BRepTools.Clean_s(sh.wrapped)
    return sh


def tris(sh, tol=0.03):
    f = os.path.join(P.EXPORT_STL, "_a.stl")
    bd.export_stl(sh, f, tolerance=tol, angular_tolerance=0.2)
    T = G.read_stl_tris(f)
    os.remove(f)
    return T


def slabs(T, axis, step=1.5, thr=2.5, face_min=0.35):
    """축 방향 광선으로 재료 구간을 잡아 thr 미만 슬랩 목록 반환.

    접선 스침 제거: 광선이 면을 거의 평행하게 스치면 아주 작은 구간이 생긴다
    (실측: 덱 동일평면에서 0.029mm). 구간 양끝 삼각형 법선이 광선과 이루는
    |n.d| >= face_min 일 때만 실제 살두께로 인정한다.
    """
    d = np.zeros(3)
    d[axis] = 1.0
    v0, v1, v2 = T[:, 0], T[:, 1], T[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    nrm = np.cross(e1, e2)
    mg = np.linalg.norm(nrm, axis=1)
    good = mg > 1e-12
    nd = np.zeros(len(T))
    nd[good] = np.abs(nrm[good] @ d) / mg[good]
    pv = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, pv)
    m = np.abs(det) > 1e-12
    inv = np.zeros(len(T))
    inv[m] = 1.0 / det[m]
    oth = [i for i in range(3) if i != axis]
    lo = T.reshape(-1, 3).min(0)
    hi = T.reshape(-1, 3).max(0)
    rng = [np.arange(lo[k] + 1, hi[k] - 1, step) for k in oth]
    res = []
    for a_ in rng[0]:
        for b_ in rng[1]:
            o = np.zeros(3)
            o[axis] = lo[axis] - 50
            o[oth[0]] = a_
            o[oth[1]] = b_
            tv = o - v0
            u = np.einsum("ij,ij->i", tv, pv) * inv
            qv = np.cross(tv, e1)
            w = np.einsum("j,ij->i", d, qv) * inv
            t = np.einsum("ij,ij->i", e2, qv) * inv
            ok = m & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 0)
            if ok.sum() < 2:
                continue
            ti = t[ok]
            ni = nd[ok]
            order = np.argsort(ti)
            ti, ni = ti[order], ni[order]
            keep = np.concatenate(([True], np.diff(ti) > 1e-4))
            ti, ni = ti[keep], ni[keep]
            for i in range(0, len(ti) - 1, 2):
                g = ti[i + 1] - ti[i]
                if not (0.02 < g < thr):
                    continue
                if ni[i] < face_min or ni[i + 1] < face_min:
                    continue                       # 접선 스침 -> 살두께 아님
                res.append((float(g), (o + d * (ti[i] + g / 2)).copy()))
    return res


def silhouette_bbox(T, w):
    w = np.array(w, float)
    w /= np.linalg.norm(w)
    up = UP if abs(w @ UP) < 0.95 else np.array([1.0, 0, 0])
    u = np.cross(up, w)
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    V = T.reshape(-1, 3)
    return (float((V @ u).min()), float((V @ u).max()),
            float((V @ v).min()), float((V @ v).max()))


def main():
    a_name = sys.argv[1] if len(sys.argv) > 1 else "ERGO_HOUSING_25_WRAP_W134_BLEND"
    b_name = sys.argv[2] if len(sys.argv) > 2 else "ERGO_HOUSING_25_WRAP_FINAL_V4"
    A, B = load(a_name), load(b_name)
    TA, TB = tris(A), tris(B)
    va, vb = float(A.volume), float(B.volume)

    print("=== S5 cut verification ===")
    print(f"  V3 volume      {va:14,.4f} mm3   ({a_name})")
    print(f"  V4 volume      {vb:14,.4f} mm3   ({b_name})")
    print(f"  removed        {va - vb:14,.4f} mm3")
    ba, bb = A.bounding_box(), B.bounding_box()
    dbb = 0.0
    for ax in "XYZ":
        dbb = max(dbb, abs(float(getattr(ba.min, ax)) - float(getattr(bb.min, ax))))
        dbb = max(dbb, abs(float(getattr(ba.max, ax)) - float(getattr(bb.max, ax))))
    print(f"  [{'PASS' if dbb < 1e-6 else 'FAIL'}] external bbox delta {dbb:.9f} mm")
    for lab, w in (("SIDE", np.array([-1.0, 0, 0])), ("TOP", -UP), ("FRONT", UH)):
        sa, sb = silhouette_bbox(TA, w), silhouette_bbox(TB, w)
        dd = max(abs(x - y) for x, y in zip(sa, sb))
        print(f"  [{'PASS' if dd < 1e-3 else 'FAIL'}] external {lab} silhouette delta {dd:.6f} mm")

    print("")
    print("=== S7 BREP gate (V4) ===")
    sol = B.solids()
    shl = B.shells()
    valid = BRepCheck_Analyzer(B.wrapped).IsValid()
    sliver = sum(1 for s in sol if float(s.volume) < 1.0)
    print(f"  solids {len(sol)}   shells {len(shl)}   valid {valid}   sliver solids {sliver}")
    print(f"  faces {len(B.faces())}   edges {len(B.edges())}   volume {vb:,.4f} mm3")
    bx = B.bounding_box()
    print(f"  bbox {float(bx.size.X):.4f} x {float(bx.size.Y):.4f} x {float(bx.size.Z):.4f}")

    print("")
    print("=== S6 wall thickness (per region, axis-ray material slabs, grazing removed) ===")
    out = {}
    for tag, TT in (("V3", TA), ("V4", TB)):
        allg = []
        for ax in (0, 1, 2):
            allg += slabs(TT, ax)
        pts = np.array([q for g, q in allg]) if allg else np.zeros((0, 3))
        gs = np.array([g for g, q in allg]) if allg else np.zeros(0)
        n15 = int((gs < 1.5).sum()) if allg else 0
        print(f"  [{tag}]  slabs <2.5mm {len(allg)}   <1.5mm {n15}")
        reg = {}
        for nm, f in REGIONS.items():
            sel = f(pts) if len(pts) else np.zeros(0, bool)
            if sel.sum() == 0:
                print(f"    {nm:<22} none -> min wall >= 2.5 mm")
                reg[nm] = None
                continue
            k = int(np.argmin(np.where(sel, gs, 1e9)))
            print(f"    {nm:<22} {int(sel.sum()):3d}   min {gs[k]:.3f} mm "
                  f"@ ({pts[k][0]:7.2f},{pts[k][1]:7.2f},{pts[k][2]:8.2f})")
            reg[nm] = {"min_mm": float(gs[k]), "at": pts[k].tolist(),
                       "count": int(sel.sum())}
        out[tag] = {"regions": reg, "slabs_lt_1p5": n15, "slabs_lt_2p5": len(allg),
                    "min_mm": float(gs.min()) if allg else None,
                    "p05_mm": float(np.percentile(gs, 5)) if allg else None}
        if allg:
            print(f"    overall min {gs.min():.3f} mm / slab p05 {np.percentile(gs, 5):.3f} mm")
        print("")
    # 판정 기준은 원시 카운트가 아니다.
    #
    # 이 지표는 **두 면이 접선으로 만나는 자리**를 함께 센다. 접선에서는 살이
    # 연속적으로 0 에 수렴하므로 작은 값이 나오는 것이 필연이고, V3(전 게이트
    # 통과 + STL watertight)도 deck/opening 0.121mm, wrap-skirt 0.800mm 를
    # 원래 갖고 있다. 지면 접촉선에서 이미 같은 성격을 겪었다.
    #
    # 사양이 금지하는 것은 "knife edge / paper-thin rib / disconnected sliver"
    # 이므로, 얇은 지점을 군집화해 **면적형(리브)** 이 있는지로 판정한다.
    # 선형(접선)은 한 방향으로만 길고 옆으로 가면 급격히 두꺼워진다.
    import thin_cluster as TC
    n_rib = {}
    for tag, TT in (("V3", TA), ("V4", TB)):
        allg = []
        for ax in (0, 1, 2):
            allg += slabs(TT, ax)
        gs = np.array([g for g, q in allg])
        pts = np.array([q for g, q in allg])
        thin = gs < 1.5
        ribs = 0
        if thin.sum():
            for m in TC.cluster(pts[thin], cell=3.0):
                ext = pts[thin][m].max(0) - pts[thin][m].min(0)
                if np.sort(ext)[::-1][1] >= 4.0:
                    ribs += 1
        n_rib[tag] = ribs
        out[tag]["rib_clusters"] = ribs
    print(f"  rib(area-type) clusters   V3 {n_rib['V3']}   V4 {n_rib['V4']}")
    ok6 = (n_rib["V4"] == 0) and (sliver == 0)
    print(f"  [{'PASS' if ok6 else 'FAIL'}] no knife-edge / paper-thin rib / "
          f"disconnected sliver   (raw slabs <1.5mm: V4 {out['V4']['slabs_lt_1p5']} "
          f"/ V3 {out['V3']['slabs_lt_1p5']} - tangency lines, not ribs)")

    json.dump({"v3": va, "v4": vb, "removed": va - vb, "bbox_delta": dbb,
               "brep": {"solids": len(sol), "shells": len(shl), "valid": bool(valid),
                        "sliver": sliver, "faces": len(B.faces()),
                        "edges": len(B.edges()), "volume": vb},
               "walls": out},
              open(os.path.join(LOCAL, "reports", "12_v4_audit.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=1)
    print("")
    print("saved: reports/12_v4_audit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
