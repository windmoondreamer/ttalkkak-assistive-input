"""§3 좌표계 정합 — 개별 STEP <-> 어셈블리 STEP 의 rigid transform 계산.

근사 translate/rotate 를 손으로 넣지 않는다. 전부 STEP 형상에서 유도한다.

중요한 관찰:
  Part Studio 의 부품 배치는 **layout 위치**이지 조립 위치가 아니다.
  실제로 Roll_holder / Roll_holder_2 / Spacer 는 어셈블리와 공통 평행이동을 갖는데
  Base 만 Z 로 7.0 mm (= Spacer 두께) 어긋난다.
  => 스톡 7개에 단일 변환을 걸면 안 된다.
     **어셈블리 형상이 진짜 조립 상태**이고, Base solid 하나를 다리로 프레임을 잇는다.

체인:
  1) Base PS  -> grip(core)  : Base solid 를 캐리어의 **포켓 바닥면**에 맞춘다.
                               포켓은 Base 를 받으려고 만든 물리적 피처라
                               STEP 만으로 유일하게 결정된다 (꼬리 슬롯이 회전을 확정).
  2) Base PS  -> assembly    : 축정렬 24 회전 탐색 + 중심 평행이동, 정점 거리로 채점.
  3) assembly -> grip        : (1) ∘ inv(2)

결과: reports/01_reference_alignment.json
Onshape API 호출 0건.
"""
from __future__ import annotations

import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402


# ------------------------------------------------------------------ 도우미

def verts(solid):
    return np.array([[v.X, v.Y, v.Z] for v in solid.vertices()], dtype=float)


def bbox_of(solid):
    b = solid.bounding_box()
    return (np.array([b.min.X, b.min.Y, b.min.Z]),
            np.array([b.max.X, b.max.Y, b.max.Z]))


def centroid(solid):
    c = solid.center()
    return np.array([c.X, c.Y, c.Z], dtype=float)


def apply_rt(R, t, X):
    return X @ R.T + t


def rot_angle_deg(R):
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1, 1))))


def axis_aligned_rotations():
    """det=+1 인 축정렬 회전 24개."""
    out = []
    for perm in itertools.permutations(range(3)):
        for sx, sy, sz in itertools.product((1, -1), repeat=3):
            R = np.zeros((3, 3))
            for row, col in enumerate(perm):
                R[row, col] = (sx, sy, sz)[row]
            if abs(np.linalg.det(R) - 1.0) < 1e-9:
                out.append(R)
    return out


def max_deviation(A, B, sub=250):
    """A 의 각 점에서 B 의 최근접 거리 최대값."""
    a = A[:: max(1, len(A) // sub)]
    d = np.sqrt(((a[:, None, :] - B[None, :, :]) ** 2).sum(-1)).min(1)
    return float(d.max())


# ------------------------------------------------------------------ 식별

def core_solids(core):
    sol = sorted(core.solids(), key=lambda s: float(s.volume))
    return sol[1], sol[0]          # housing, carrier


def carrier_pocket(carrier):
    """캐리어에서 Base 를 받는 포켓 바닥면(+Z 법선 평면 중 최하단)."""
    best = None
    for f in carrier.faces():
        try:
            n = f.normal_at()
        except Exception:                                  # noqa: BLE001
            continue
        if abs(n.Z - 1.0) > 1e-6:
            continue
        v = np.array([[p.X, p.Y, p.Z] for p in f.vertices()])
        if len(v) == 0:
            continue
        z = float(f.center().Z)
        cand = {"z": z, "area": float(f.area),
                "x0": float(v[:, 0].min()), "x1": float(v[:, 0].max()),
                "y0": float(v[:, 1].min()), "y1": float(v[:, 1].max())}
        if best is None or z < best["z"]:
            best = cand
    return best


def identify_stock(stock):
    out = []
    for i, s in enumerate(stock.solids()):
        lo, hi = bbox_of(s)
        out.append({"idx": i, "solid": s, "vol": float(s.volume),
                    "size": hi - lo, "lo": lo, "hi": hi, "cen": centroid(s)})
    name = {}
    base = max(out, key=lambda d: d["size"][0] * d["size"][1])
    name[base["idx"]] = "Base"
    rest = [d for d in out if d["idx"] not in name]
    pair = [d for d in rest
            if sum(1 for e in rest if abs(d["vol"] - e["vol"]) < 1e-6) > 1]
    for k, d in enumerate(sorted(pair, key=lambda d: d["cen"][1])):
        name[d["idx"]] = "Roll_holder_2" if k == 0 else "Roll_holder"
    rest = [d for d in rest if d["idx"] not in name]
    spacer = min(rest, key=lambda d: d["size"][2] / max(d["size"][1], 1e-9))
    name[spacer["idx"]] = "Spacer"
    rest = [d for d in rest if d["idx"] not in name]
    pitch = max(rest, key=lambda d: d["size"][2])
    name[pitch["idx"]] = "Pitch"
    rest = [d for d in rest if d["idx"] not in name]
    spring = max(rest, key=lambda d: d["size"][0])
    name[spring["idx"]] = "Spring_holder"
    for d in rest:
        if d["idx"] not in name:
            name[d["idx"]] = "Roll"
    for d in out:
        d["name"] = name[d["idx"]]
    return sorted(out, key=lambda d: d["idx"])


def tail_sign(base_solid):
    """Base 의 꼬리(좁은 쪽)가 로컬 +Y 인지 -Y 인지."""
    lo, hi = bbox_of(base_solid)
    v = verts(base_solid)
    q = 0.25 * (hi[1] - lo[1])

    def width(mask):
        return (v[mask, 0].max() - v[mask, 0].min()) if mask.any() else 0.0
    wlo = width(v[:, 1] < lo[1] + q)
    whi = width(v[:, 1] > hi[1] - q)
    return (-1 if wlo < whi else +1), wlo, whi


# ------------------------------------------------------------------ 메인

def main():
    bd = G.b3d()
    req, _ = P.missing_references()
    if req:
        print("STOP - 필수 레퍼런스 없음:", req)
        return 2

    print("=" * 78)
    print("3. 좌표계 정합")
    print("=" * 78)

    core = bd.import_step(P.reference_path("conformal_core"))
    stock = bd.import_step(P.reference_path("stock_gimbal"))
    asm = bd.import_step(P.reference_path("assembly"))

    housing, carrier = core_solids(core)
    print(f"\n[코어 분해]  HOUSING {float(housing.volume):,.2f}   "
          f"CARRIER {float(carrier.volume):,.2f} mm3")

    hlo, hhi = bbox_of(housing)
    dz = abs(hhi[2] - P.FROZEN_DECK_Z)
    print(f"[코어 프레임] HOUSING 상단 Z {hhi[2]:.6f} vs FROZEN_DECK_Z "
          f"{P.FROZEN_DECK_Z:.6f}  차 {dz:.2e} mm")
    core_is_grip = dz < 1e-3

    pk = carrier_pocket(carrier)
    print(f"[캐리어 포켓] Z {pk['z']:.4f}  X[{pk['x0']:.3f},{pk['x1']:.3f}] "
          f"Y[{pk['y0']:.3f},{pk['y1']:.3f}] = "
          f"{pk['x1']-pk['x0']:.3f} x {pk['y1']-pk['y0']:.3f}")

    st = identify_stock(stock)
    print("\n[스톡 식별]")
    for d in st:
        print(f"  s{d['idx']}  {d['name']:<14s} vol {d['vol']:11,.2f}  size "
              f"{d['size'][0]:7.3f} x {d['size'][1]:7.3f} x {d['size'][2]:7.3f}")
    base = next(d for d in st if d["name"] == "Base")
    tsign, wlo, whi = tail_sign(base["solid"])
    print(f"  Base 꼬리 (로컬) {'+Y' if tsign > 0 else '-Y'}  "
          f"(Y 하위폭 {wlo:.1f} / 상위폭 {whi:.1f})")

    # ---------------- 1) Base PS -> grip ----------------
    clr = 0.5 * ((pk["x1"] - pk["x0"]) - base["size"][0])
    print(f"\n[1) Base PS -> grip]  포켓 편측 여유 {clr:.4f} mm")
    chosen = None
    for deg in (0.0, 180.0):
        a = np.radians(deg)
        R = np.array([[np.cos(a), -np.sin(a), 0.0],
                      [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]])
        rc = np.array([base["lo"], base["hi"]]) @ R.T
        rlo, rhi = rc.min(0), rc.max(0)
        ts = tsign * (1 if deg == 0 else -1)
        t = np.zeros(3)
        t[0] = 0.5 * (pk["x0"] + pk["x1"]) - 0.5 * (rlo[0] + rhi[0])
        t[2] = pk["z"] - rlo[2]
        # 포켓은 Base **본체**(100) 를 받는다. 꼬리는 슬롯으로 빠진다.
        if ts < 0:
            t[1] = (pk["y1"] - clr) - rhi[1]
        else:
            t[1] = (pk["y0"] + clr) - rlo[1]
        if ts < 0:                       # 그립 프레임에서 꼬리는 -Y
            chosen = (deg, R, t)
    if chosen is None:
        print("  [FAIL] 꼬리를 -Y 로 보내는 회전 후보가 없다")
        return 1
    deg1, R1, t1 = chosen
    print(f"  Rz({deg1:.0f})  t = ({t1[0]:.6f}, {t1[1]:.6f}, {t1[2]:.6f})")

    bv = apply_rt(R1, t1, verts(base["solid"]))
    blo, bhi = bv.min(0), bv.max(0)
    print(f"  변환 후 Base bbox  X[{blo[0]:.4f},{bhi[0]:.4f}] "
          f"Y[{blo[1]:.4f},{bhi[1]:.4f}] Z[{blo[2]:.4f},{bhi[2]:.4f}]")
    print(f"  포켓 여유  -X {blo[0]-pk['x0']:+.4f}  +X {pk['x1']-bhi[0]:+.4f}"
          f"  +Y {pk['y1']-bhi[1]:+.4f}   바닥 오차 {blo[2]-pk['z']:+.2e}")
    fit_ok = (abs(blo[2] - pk["z"]) < 1e-6
              and abs((blo[0] - pk["x0"]) - clr) < 1e-6
              and abs((pk["y1"] - bhi[1]) - clr) < 1e-6)

    # ---------------- 2) Base PS -> assembly ----------------
    print("\n[2) Base solid : Part Studio -> assembly]")
    base_sub = [c for c in asm.children if c.label.startswith("Base_")][0]
    asm_sol = list(base_sub.solids())
    pairs = []
    for d in st:
        m = min(asm_sol, key=lambda s2: abs(float(s2.volume) - d["vol"]))
        pairs.append((d, m, abs(float(m.volume) - d["vol"]) / d["vol"]))
    print(f"  부피 매칭 최대 상대오차 {max(r for _, _, r in pairs):.2e}  (7/7)")
    base_asm = next(m for d, m, _ in pairs if d["name"] == "Base")

    Av, Bv = verts(base["solid"]), verts(base_asm)
    best = None
    for R in axis_aligned_rotations():
        t = centroid(base_asm) - R @ centroid(base["solid"])
        sc = max_deviation(apply_rt(R, t, Av), Bv)
        if best is None or sc < best[0]:
            best = (sc, R, t)
    score, R2, t2 = best
    print(f"  최적 축정렬 회전 {rot_angle_deg(R2):.6f} deg  정점 최대편차 "
          f"{score:.3e} mm")
    print(f"  t = ({t2[0]:.6f}, {t2[1]:.6f}, {t2[2]:.6f})")
    align_ok = score < 1e-6

    # PS layout 이 조립 상태와 다르다는 증거 (부품별 평행이동 비교)
    print("\n  [PS layout vs assembly 평행이동]  (동일하지 않으면 layout 위치다)")
    for d, m, _ in pairs:
        dt = centroid(m) - R2 @ d["cen"]
        print(f"    {d['name']:<14s} t = ({dt[0]:8.3f}, {dt[1]:8.3f}, {dt[2]:8.3f})"
              f"   Base 대비 차 {np.linalg.norm(dt - t2):8.3f} mm")

    # ---------------- 3) assembly -> grip ----------------
    R3 = R1 @ R2.T
    t3 = t1 - R3 @ t2
    print(f"\n[3) assembly -> grip]  회전 {rot_angle_deg(R3):.6f} deg")
    print(f"  t = ({t3[0]:.6f}, {t3[1]:.6f}, {t3[2]:.6f})")

    # 검증: 어셈블리의 Base 를 그립으로 보내면 포켓에 정확히 앉는가
    chk = apply_rt(R3, t3, Bv)
    clo, chi = chk.min(0), chk.max(0)
    err = max(abs(clo[0] - blo[0]), abs(chi[0] - bhi[0]),
              abs(clo[1] - blo[1]), abs(chi[1] - bhi[1]),
              abs(clo[2] - blo[2]), abs(chi[2] - bhi[2]))
    print(f"  검증: assembly Base -> grip  bbox 최대오차 {err:.3e} mm")

    # 어셈블리 전체를 그립 프레임으로 보냈을 때의 범위
    ab = asm.bounding_box()
    corners = np.array([[x, y, z] for x in (ab.min.X, ab.max.X)
                        for y in (ab.min.Y, ab.max.Y)
                        for z in (ab.min.Z, ab.max.Z)])
    gc = apply_rt(R3, t3, corners)
    print(f"  어셈블리 전체 -> grip bbox  X[{gc[:,0].min():.2f},{gc[:,0].max():.2f}] "
          f"Y[{gc[:,1].min():.2f},{gc[:,1].max():.2f}] "
          f"Z[{gc[:,2].min():.2f},{gc[:,2].max():.2f}]")

    out = {
        "core_is_grip_frame": bool(core_is_grip),
        "deck_z_delta_mm": float(dz),
        "carrier_pocket": pk,
        "pocket_clearance_per_side_mm": float(clr),
        "stock_names": {int(d["idx"]): d["name"] for d in st},
        "base_tail_sign_local": int(tsign),
        "T_basePS_to_grip": {"R": R1.tolist(), "t": t1.tolist(),
                             "rz_deg": float(deg1)},
        "T_baseSolid_PS_to_assembly": {
            "R": R2.tolist(), "t": t2.tolist(),
            "rot_deg": rot_angle_deg(R2),
            "vertex_max_deviation_mm": float(score)},
        "T_assembly_to_grip": {"R": R3.tolist(), "t": t3.tolist(),
                               "verify_bbox_max_err_mm": float(err)},
        "note": ("Part Studio 배치는 layout 위치다. 스톡 7개에 단일 변환을 걸 수 없고, "
                 "Base solid 하나를 다리로 assembly<->grip 을 잇는다. "
                 "형상은 어셈블리(진짜 조립 상태)에서 가져온다."),
        "fit_ok": bool(fit_ok), "align_ok": bool(align_ok),
        "verify_ok": bool(err < 1e-6),
    }
    os.makedirs(P.REPORTS_DIR, exist_ok=True)
    p = os.path.join(P.REPORTS_DIR, "01_reference_alignment.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\n저장: {p}")
    print("=" * 78)
    ok = core_is_grip and fit_ok and align_ok and err < 1e-6
    print("정합 " + ("OK" if ok else "확인 필요"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
