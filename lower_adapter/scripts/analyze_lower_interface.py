"""OneGrip 하부 경사 어댑터 — 상체 하단 인터페이스 실측 (READ ONLY).

    python lower_adapter/scripts/analyze_lower_interface.py [--fetch-asm]

`lower_adapter/docs/00_architecture_analysis.md` 의 모든 수치를 재생성한다.

입력:  <root>/cad_dump/mesh_*.json          (상체 워크플로가 만든 공용 메시 캐시. 읽기만)
출력:  <root>/lower_adapter/cad_dump/*.npy  (이 서브시스템 전용 파생 데이터)

Onshape 접근은 `--fetch-asm` 일 때 assembly occurrence transform GET 1회뿐이다.
POST/PUT/DELETE 를 절대 사용하지 않는다.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SHARED_DUMP = os.path.join(ROOT, "cad_dump")          # 공용 메시 (읽기 전용)
OUT = os.path.join(ROOT, "lower_adapter", "cad_dump")  # 이 서브시스템 산출물
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)

from mesh_probe import Mesh  # noqa: E402

SHELLS = ["INDEX_FINAL_JaD", "INDEX_FINAL_JfD"]
BASELINE = ["Joystick_1_baseline", "Joystick_2_baseline"]

# 상체 하단 인터페이스 (이 스크립트가 검증하는 값)
FLANGE_Z = -67.878507
BOSS_Z = -73.878507
MOUNT_ORIGIN = np.array([0.0, 27.269160, FLANGE_Z])

# 엄지 패널 버튼 캡 8개 중심 (mesh 기반, grip 좌표)
CAPS = {
    "corner_1": (10.315, -0.003, 40.636), "side_1": (10.906, -7.739, 47.572),
    "wide_1": (8.126, -17.156, 55.723), "middle_1": (0.000, -7.706, 47.599),
    "corner_2": (-10.314, -0.003, 40.637), "side_2": (-10.904, -7.738, 47.572),
    "wide_2": (-8.126, -17.156, 55.723), "middle_2": (0.000, 0.565, 40.346),
}
SCREWS = {"S1": (-41.863, 45.981), "S2": (-14.441, 23.064), "S3": (15.801, -21.354)}


# ---------- 공용 ----------

def load_tris(name):
    with open(os.path.join(SHARED_DUMP, f"mesh_{name}.json"), encoding="utf-8") as f:
        return np.asarray(json.load(f)["tris"], dtype=float)


def cast(mesh, origin, direction):
    """정렬된 교차 거리 배열."""
    hits = mesh.raycast(origin, direction)
    hits = hits[0] if isinstance(hits, tuple) else hits
    try:
        t = np.asarray([h[0] for h in hits], dtype=float)
    except Exception:
        t = np.asarray(hits, dtype=float)
    return np.sort(t)


def rot_x(rad):
    c, s = np.cos(rad), np.sin(rad)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def volume_centroid(tris):
    """발산정리. watertight 메시에서만 유효하다."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    v = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
    total = v.sum()
    return total, (((a + b + c) / 4.0) * v[:, None]).sum(0) / total


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ---------- A. 바닥 레이캐스트 맵 ----------

def bottom_map(mesh):
    head("A. 바닥면 맵 (+Z ray, 1.0 mm 격자)")
    xs = np.arange(-40, 40.01, 1.0)
    ys = np.arange(-15, 66.01, 1.0)
    first = np.full((len(ys), len(xs)), np.nan)
    n_hit = np.zeros((len(ys), len(xs)), dtype=int)
    for i, y in enumerate(ys):
        for k, x in enumerate(xs):
            t = cast(mesh, [x, y, -200.0], [0, 0, 1.0])
            if t.size:
                first[i, k] = t.min() - 200.0
                n_hit[i, k] = t.size
    np.save(os.path.join(OUT, "bot_first.npy"), first)
    np.save(os.path.join(OUT, "bot_n.npy"), n_hit)

    flange = np.isfinite(first) & (np.abs(first - FLANGE_Z) < 0.01)
    boss = np.isfinite(first) & (np.abs(first - BOSS_Z) < 0.01)
    below = np.isfinite(first) & (first < FLANGE_Z - 0.01)
    yi, xi = np.nonzero(boss)
    print(f"  플랜지 평면 Z={FLANGE_Z:+.6f} 셀 {flange.sum()}")
    print(f"  보스 끝면   Z={BOSS_Z:+.6f} 셀 {boss.sum()}  "
          f"X[{xs[xi].min():.1f},{xs[xi].max():.1f}] Y[{ys[yi].min():.1f},{ys[yi].max():.1f}]")
    print(f"  플랜지면보다 아래인 셀 {below.sum()} — 전부 보스면인가: "
          f"{np.array_equal(np.unique(np.round(first[below], 4)), np.array([BOSS_Z]))}")
    print(f"  보스 돌출량 = {FLANGE_Z - BOSS_Z:.3f} mm")
    return first


# ---------- B. 플랜지 윤곽 / 외피 프로파일 ----------

def flange_outline(mesh, z=-66.5, step=1.0):
    head("B. 플랜지 윤곽 + 외피 프로파일 (반경 방향 inward ray)")
    cx, cy, r0 = 0.0, 26.0, 150.0
    pts = []
    for th in np.deg2rad(np.arange(0, 360, step)):
        d = np.array([-np.cos(th), -np.sin(th), 0.0])
        o = np.array([cx + r0 * np.cos(th), cy + r0 * np.sin(th), z])
        r = r0 - cast(mesh, o, d)[0]
        pts.append([cx + r * np.cos(th), cy + r * np.sin(th)])
    P = np.array(pts)
    np.save(os.path.join(OUT, "flange_outline.npy"), P)

    x, y = P[:, 0], P[:, 1]
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    cr = x * y2 - x2 * y
    area = cr.sum() / 2
    gx = ((x + x2) * cr).sum() / (6 * area)
    gy = ((y + y2) * cr).sum() / (6 * area)
    print(f"  면적 {abs(area):.1f} mm2   도심 ({gx:.3f}, {gy:.3f})")
    print(f"  X {x.max() - x.min():.3f} mm   Y {y.max() - y.min():.3f} mm")

    def radius_at(cx0, cy0, ang):
        v = P - np.array([cx0, cy0])
        a = np.mod(np.arctan2(v[:, 1], v[:, 0]), 2 * np.pi)
        rr = np.linalg.norm(v, axis=1)
        o = np.argsort(a)
        return np.interp(np.mod(ang, 2 * np.pi), a[o], rr[o])

    ang = np.deg2rad(np.arange(0, 360, 2.0))
    d180 = np.abs(radius_at(gx, gy, ang) - radius_at(gx, gy, ang + np.pi))
    dmir = np.abs(radius_at(0.0, gy, ang) - radius_at(0.0, gy, np.pi - ang))
    print(f"  180deg 회전대칭 오차: 평균 {d180.mean():.3f}  최대 {d180.max():.3f} mm  <-- 회전방지 경고")
    print(f"  X=0 거울대칭 오차  : 평균 {dmir.mean():.4f}  최대 {dmir.max():.4f} mm")

    zl = [-67.5, -65, -60, -55, -50, -45, -40, -30, -20]
    prof = []
    for zz in zl:
        rs = []
        for th in np.deg2rad(np.arange(0, 360, 5)):
            d = np.array([-np.cos(th), -np.sin(th), 0.0])
            o = np.array([cx + r0 * np.cos(th), cy + r0 * np.sin(th), zz])
            t = cast(mesh, o, d)
            rs.append(r0 - t[0] if t.size else np.nan)
        prof.append(rs)
    np.save(os.path.join(OUT, "outer_prof.npy"), np.array(prof))
    print("  Z별 반경(min/max):", "  ".join(
        f"{zz:.0f}:{np.nanmin(p):.1f}-{np.nanmax(p):.1f}" for zz, p in zip(zl, prof)))

    for zz in (-64.4, -64.0, -63.5, -63.0):
        rs = np.array([radius_at(gx, gy, t) for t in np.deg2rad(np.arange(0, 360, 10))])
        body = []
        for th in np.deg2rad(np.arange(0, 360, 10)):
            d = np.array([-np.cos(th), -np.sin(th), 0.0])
            o = np.array([cx + r0 * np.cos(th), cy + r0 * np.sin(th), zz])
            t = cast(mesh, o, d)
            body.append(r0 - t[0] if t.size else np.nan)
        ov = rs - np.array(body)
        print(f"  Z={zz:7.2f} 립 오버행 min {np.nanmin(ov):5.2f}  max {np.nanmax(ov):5.2f} mm")
    return P


# ---------- C. 소켓 보어 ----------

def socket(mesh):
    head("C. 소켓 보어 — 단면 / 축 / 깊이")
    y0 = MOUNT_ORIGIN[1]
    rows, cxs, cys = [], [], []
    for z in np.arange(-73.6, -53.0, 0.5):
        o = np.array([0.0, y0, z])
        xm = -cast(mesh, o, [-1, 0, 0])[0]
        xp = cast(mesh, o, [1, 0, 0])[0]
        ym = y0 - cast(mesh, o, [0, -1, 0])[0]
        yp = y0 + cast(mesh, o, [0, 1, 0])[0]
        rows.append((z, xm, xp, ym, yp))
        cxs.append((xm + xp) / 2)
        cys.append((ym + yp) / 2)
    R = np.array(rows)
    cxs, cys, zz = np.array(cxs), np.array(cys), R[:, 0]
    px = np.polyfit(zz, cxs, 1)
    py = np.polyfit(zz, cys, 1)
    dev = np.degrees(np.arctan(np.hypot(px[0], py[0])))
    print(f"  단면 폭  {np.unique(np.round(R[:, 2] - R[:, 1], 4))} mm")
    print(f"  단면 깊이 {np.unique(np.round(R[:, 4] - R[:, 3], 4))} mm")
    print(f"  보어 중심 X mean {cxs.mean():.6f} std {cxs.std():.2e}")
    print(f"  보어 중심 Y mean {cys.mean():.6f} std {cys.std():.2e}")
    print(f"  축 기울기 dX/dZ {px[0]:+.2e}  dY/dZ {py[0]:+.2e}  -> +Z 에서 {dev:.6f} deg")

    xs = np.arange(-18, 18.001, 0.25)
    ys = np.arange(6, 49.001, 0.25)
    first = np.full((len(ys), len(xs)), np.nan)
    last = np.full((len(ys), len(xs)), np.nan)
    for i, y in enumerate(ys):
        for k, x in enumerate(xs):
            t = cast(mesh, [x, y, -200.0], [0, 0, 1.0])
            if t.size:
                first[i, k] = t.min() - 200.0
                last[i, k] = t.max() - 200.0
    np.save(os.path.join(OUT, "socket_first.npy"), first)
    np.save(os.path.join(OUT, "socket_last.npy"), last)
    X, Y = np.meshgrid(xs, ys)
    blind = first[(X > -10.4) & (X < 10.4) & (Y > 14.6) & (Y < 39.9)]
    print(f"  직진 보어 상단(막힌 끝) Z = {blind.min():.4f}  -> 직진 깊이 {blind.min() - BOSS_Z:.3f} mm")
    return np.array([px[0], py[0], 1.0]) / np.linalg.norm([px[0], py[0], 1.0])


# ---------- D. 플랜지 평면 적합 / 수직도 ----------

def perpendicularity(first_map, axis):
    head("D. 플랜지 평면 ⟂ 중심축")
    xs = np.arange(-40, 40.01, 1.0)
    ys = np.arange(-15, 66.01, 1.0)
    X, Y = np.meshgrid(xs, ys)
    m = np.isfinite(first_map) & (np.abs(first_map - FLANGE_Z) < 0.01)
    P = np.column_stack([X[m], Y[m], first_map[m]])
    A = np.column_stack([P[:, 0], P[:, 1], np.ones(len(P))])
    coef, *_ = np.linalg.lstsq(A, P[:, 2], rcond=None)
    n = np.array([-coef[0], -coef[1], 1.0])
    n /= np.linalg.norm(n)
    ang = np.degrees(np.arccos(abs(float(np.dot(n, axis)))))
    print(f"  표본 {len(P)}  z = {coef[0]:+.2e} x {coef[1]:+.2e} y {coef[2]:+.6f}")
    print(f"  법선 = ({n[0]:+.9f}, {n[1]:+.9f}, {n[2]:.9f})   max residual {np.abs(A @ coef - P[:, 2]).max():.2e} mm")
    print(f"  angle(flange normal, socket axis) = {ang:.6f} deg   <-- 0 이면 이미 완전 수직")
    return n


# ---------- E. 나사 / 엄지 패널 / CG ----------

def screws(mesh):
    head("E1. 쉘 결합 나사 3개 (X축 ray)")
    for k, (y, z) in SCREWS.items():
        t = cast(mesh, [-80.0, y, z], [1, 0, 0]) - 80.0
        print(f"  {k} (Y {y:+8.3f}, Z {z:+8.3f})  플랜지면 위 {z - FLANGE_Z:7.2f} mm   X 교차 {np.round(t, 3)}")


def thumb_panel():
    head("E2. 엄지 패널 법선 (버튼 캡 8개 평면적합)")
    P = np.array(list(CAPS.values()))
    C = P.mean(0)
    _, S, Vt = np.linalg.svd(P - C)
    n = Vt[2]
    if n[2] < 0:
        n = -n
    print(f"  centroid ({C[0]:.3f}, {C[1]:.3f}, {C[2]:.3f})")
    print(f"  normal   ({n[0]:+.6f}, {n[1]:+.6f}, {n[2]:+.6f})   residual sigma {S[2] / np.sqrt(len(P)):.4f} mm")
    print(f"  수직(+Z)에서 {np.degrees(np.arccos(n[2])):.2f} deg  "
          f"-> 작동면은 {'+Y' if n[1] > 0 else '-Y'} 쪽을 향한다")
    return n


def centroid():
    head("E3. 무게중심")
    names = SHELLS + ["Backplate", "INDEX_FINAL_RWID", "INDEX_FINAL_RZKD"] + [
        f"Button_{a}_{b}" for a in ("corner", "side", "wide", "middle") for b in ("1", "2")]
    total, mom = 0.0, np.zeros(3)
    for nm in names:
        if not os.path.exists(os.path.join(SHARED_DUMP, f"mesh_{nm}.json")):
            print(f"  [skip] {nm}")
            continue
        v, c = volume_centroid(load_tris(nm))
        total += v
        mom += v * c
    cg = mom / total
    print(f"  부피 {total:.1f} mm3   CG ({cg[0]:+.3f}, {cg[1]:+.3f}, {cg[2]:+.3f})")
    print(f"  플랜지면 위 {cg[2] - FLANGE_Z:.2f} mm   중심축에서 dY {cg[1] - MOUNT_ORIGIN[1]:+.3f} mm")
    print("  주의: Onshape massproperties 의 centroid 는 재질 미지정(hasMass:false)이라 bbox 중심을 준다.")
    return cg


# ---------- F. 경사 ----------

def tilt(cg, panel_n):
    head("F. 경사각별 기하 (MOUNT_ORIGIN 기준, RotX(+t) = TOP -> -Y)")
    V = np.unique(np.round(np.vstack(
        [load_tris(n) for n in SHELLS + ["Backplate"]]).reshape(-1, 3), 3), axis=0)
    P = np.load(os.path.join(OUT, "flange_outline.npy"))
    F3 = np.column_stack([P[:, 0], P[:, 1], np.full(len(P), FLANGE_Z)])
    d = cg - MOUNT_ORIGIN
    print(f"  CG rel MOUNT_ORIGIN: dY {d[1]:+.4f}  dZ {d[2]:+.4f}")
    print(f"  균형점(TOP->+Y): {np.degrees(np.arctan2(-d[1], d[2])):.3f} deg")
    for sign, lbl in ((+1, "TOP -> -Y (확정)"), (-1, "TOP -> +Y")):
        print(f"\n  [{lbl}]")
        print("   theta   axis n                          dip(mm)  seat Zspan  CG dY   panel/vert  아래침범")
        for deg in (0, 15, 20, 25, 30):
            R = rot_x(sign * np.deg2rad(deg))
            n = R @ np.array([0, 0, 1.0])
            W = (V - MOUNT_ORIGIN) @ R.T + MOUNT_ORIGIN
            S = (F3 - MOUNT_ORIGIN) @ R.T + MOUNT_ORIGIN
            sd = (W - MOUNT_ORIGIN) @ n           # 착좌면 기준 부호거리
            g = R @ d
            t = R @ panel_n
            print(f"   {deg:5.1f}   ({n[0]:.6f}, {n[1]:+.6f}, {n[2]:.6f})  "
                  f"{MOUNT_ORIGIN[2] - W[:, 2].min():7.3f}  {S[:, 2].max() - S[:, 2].min():9.3f}  "
                  f"{g[1]:+7.3f}  {np.degrees(np.arccos(np.clip(t[2], -1, 1))):7.2f}deg  "
                  f"{(sd < -6.001).sum():4d}")
    print("\n  '아래침범' = 착좌면 아래 6.001 mm 를 넘는 정점 수. 0 이면 보스 외 돌출 없음 = 간섭 불가")


# ---------- G. baseline 대조 / assembly transform ----------

def baseline_check():
    head("G1. 원본 baseline 과 하단 인터페이스 대조")
    for names, lbl in ((BASELINE, "baseline"), (SHELLS, "INDEX_FINAL")):
        m = Mesh(names)
        y0 = MOUNT_ORIGIN[1]
        o = np.array([0.0, y0, -60.0])
        xm = -cast(m, o, [-1, 0, 0])[0]
        xp = cast(m, o, [1, 0, 0])[0]
        ym = y0 - cast(m, o, [0, -1, 0])[0]
        yp = y0 + cast(m, o, [0, 1, 0])[0]
        zb = cast(m, [12.0, 45.0, -200], [0, 0, 1])[0] - 200
        zf = cast(m, [30.0, 26.0, -200], [0, 0, 1])[0] - 200
        print(f"  {lbl:12s} 소켓 {xp - xm:.4f} x {yp - ym:.4f}   보스면 {zb:.4f}   플랜지면 {zf:.4f}")


def fetch_asm():
    head("G2. Complete assembly occurrence transform (GET 1회)")
    from onshape.client import BASE, ELEMENTS, SOURCE, session
    s = session()
    r = s.get(f"{BASE}/assemblies/d/{SOURCE['did']}/w/{SOURCE['wid']}/e/{ELEMENTS['asm_Complete']}",
              params={"includeMateFeatures": "false", "includeMateConnectors": "false",
                      "includeNonSolids": "false"}, timeout=300)
    r.raise_for_status()
    root = r.json()["rootAssembly"]
    want = {"MPpVRghU853h7Ys92": "Joystick_1", "MlfnTWIWLTYiLR/KI": "Joystick_2",
            "Mzp/j2NAQT3qhdcr0": "Pitch", "MP2hGBo49o50S+UrZ": "Roll",
            "MP/Wspndz73XKFs/J": "Base", "MwI74fwgA2YOUxBKP": "Backplate"}
    out = {}
    for occ in root["occurrences"]:
        key = want.get(occ["path"][-1])
        if key and key not in out:
            T = np.array(occ["transform"]).reshape(4, 4)
            T[:3, 3] *= 1000.0
            out[key] = T
    with open(os.path.join(OUT, "asm_transforms.json"), "w") as f:
        json.dump({k: v.tolist() for k, v in out.items()}, f, indent=1)

    G, Pt = out["Joystick_1"], out["Pitch"]
    Gi = np.eye(4)
    Gi[:3, :3] = G[:3, :3].T
    Gi[:3, 3] = -G[:3, :3].T @ G[:3, 3]
    GP = Gi @ Pt
    print(f"  Pitch -> Grip  R=\n{np.round(GP[:3, :3], 6)}")
    print(f"                 t = ({GP[0, 3]:.4f}, {GP[1, 3]:.4f}, {GP[2, 3]:.4f}) mm")
    for lbl, p in (("post tip", [0, 26.636, 61.600]), ("post shoulder", [0, 26.636, 31.600]),
                   ("post -X-Y", [-10.136, 14.0, 61.6]), ("post +X+Y", [10.136, 39.272, 61.6]),
                   ("pitch pivot", [0, 26.6, 0.0])):
        q = GP[:3, :3] @ np.asarray(p, float) + GP[:3, 3]
        print(f"    {lbl:14s} -> ({q[0]:+8.3f}, {q[1]:8.3f}, {q[2]:9.3f})")


def main():
    os.makedirs(OUT, exist_ok=True)
    mesh = Mesh(SHELLS)
    print(f"root  = {ROOT}")
    print(f"mesh  = {SHARED_DUMP} (read only)")
    print(f"out   = {OUT}")
    first = bottom_map(mesh)
    flange_outline(mesh)
    axis = socket(mesh)
    perpendicularity(first, axis)
    screws(mesh)
    panel_n = thumb_panel()
    cg = centroid()
    tilt(cg, panel_n)
    baseline_check()
    if "--fetch-asm" in sys.argv:
        fetch_asm()
    else:
        print("\n(assembly transform 은 캐시 사용. 재조회하려면 --fetch-asm)")


if __name__ == "__main__":
    main()
