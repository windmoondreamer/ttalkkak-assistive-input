"""OPTION C 최종 검증 — §14 게이트 전항목.

GET only (Onshape 쓰기 없음).
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import stock_geom as sg                                  # noqa: E402
from onshape.client import BASE, session                 # noqa: E402
from onshape import write_client as wc                   # noqa: E402

OUT = sg.OUT
C = json.load(io.open(os.path.join(OUT, "cartridge_constants.json"), encoding="utf-8"))
T = json.load(io.open(os.path.join(OUT, "cartridge_target.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
HAND = np.array(C["HAND_REF"])
PIV = np.array(C["PIVOT"])
CACHE = os.path.join(OUT, "cartridge_meshes.npz")
STOCK_PS = "df9a32f1f239bc71a732f5d3"
FIXED = ("Base <1>", "Roll_holder <1>", "Roll_holder_2 <1>", "Spacer <1>")

PASS, FAIL = [], []


def chk(ok, label, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label:<50s} {detail}")
    return ok


def fetch(force=False):
    if os.path.exists(CACHE) and not force:
        z = np.load(CACHE)
        return {k: z[k].astype(np.float64) for k in z.files}
    r = session().get(f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{T['ps_eid']}",
                      params=[("configuration", "default")], timeout=180)
    r.raise_for_status()
    out = {}
    for p in r.json():
        if p.get("bodyType") != "solid":
            continue
        j = session().get(
            f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{T['ps_eid']}/tessellatedfaces",
            params=[("partId", p["partId"]), ("angleTolerance", "0.09"),
                    ("chordTolerance", "0.0002")], timeout=300).json()
        tri = sg._tris(j) * 1000.0
        out[p["partId"]] = tri.astype(np.float32)
        print(f"   {p['partId']:<6s} {str(p.get('name')):<10s} tri {len(tri)}")
    np.savez_compressed(CACHE, **out)
    return {k: v.astype(np.float64) for k, v in out.items()}


def bbox(P):
    Q = np.asarray(P).reshape(-1, 3)
    return Q.min(0), Q.max(0)


def inside_mesh(P, pts):
    """+Z 레이 패리티 (P 는 닫힌 삼각형망). pts (N,3) -> bool. XY 격자 가속."""
    pts = np.asarray(pts, dtype=float)
    v0, v1, v2 = P[:, 0], P[:, 1], P[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    d = np.array([0.0, 0.0, 1.0])
    h = np.cross(d, e2)
    a = (e1 * h).sum(1)
    m = np.abs(a) > 1e-12
    f = np.where(m, 1.0 / np.where(m, a, 1.0), 0.0)

    # 삼각형 XY bbox 로 셀 버킷 구성
    tlo = P[:, :, :2].min(1)
    thi = P[:, :, :2].max(1)
    lo = tlo.min(0)
    hi = thi.max(0)
    cell = 6.0
    nx = max(1, int(np.ceil((hi[0] - lo[0]) / cell)))
    ny = max(1, int(np.ceil((hi[1] - lo[1]) / cell)))
    buckets = {}
    ia0 = np.clip(((tlo[:, 0] - lo[0]) / cell).astype(int), 0, nx - 1)
    ia1 = np.clip(((thi[:, 0] - lo[0]) / cell).astype(int), 0, nx - 1)
    ja0 = np.clip(((tlo[:, 1] - lo[1]) / cell).astype(int), 0, ny - 1)
    ja1 = np.clip(((thi[:, 1] - lo[1]) / cell).astype(int), 0, ny - 1)
    for t in range(len(P)):
        for i in range(ia0[t], ia1[t] + 1):
            for j in range(ja0[t], ja1[t] + 1):
                buckets.setdefault((i, j), []).append(t)
    buckets = {k: np.array(v) for k, v in buckets.items()}

    res = np.zeros(len(pts), bool)
    pi = np.clip(((pts[:, 0] - lo[0]) / cell).astype(int), -1, nx)
    pj = np.clip(((pts[:, 1] - lo[1]) / cell).astype(int), -1, ny)
    for n in range(len(pts)):
        idx = buckets.get((pi[n], pj[n]))
        if idx is None:
            continue
        p = pts[n]
        s = p - v0[idx]
        u = f[idx] * (s * h[idx]).sum(1)
        q = np.cross(s, e1[idx])
        v = f[idx] * (q * d).sum(1)
        t = f[idx] * (e2[idx] * q).sum(1)
        ok = m[idx] & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-9)
        # 공유 모서리를 정확히 스치면 같은 t 가 2번 잡혀 패리티가 뒤집힌다.
        # (인서트 ⌀4 원기둥 접선에 복셀이 정확히 놓이면 발생 — 실측 확인)
        tt = np.sort(t[ok])
        if len(tt):
            tt = tt[np.concatenate(([True], np.diff(tt) > 1e-4))]
        res[n] = (len(tt) % 2) == 1
    return res


def voxels(P, step):
    lo, hi = bbox(P)
    g = [np.arange(lo[k] + step / 2, hi[k], step) for k in range(3)]
    G = np.stack(np.meshgrid(*g, indexing="ij"), -1).reshape(-1, 3)
    return G[inside_mesh(P, G)]


def main():
    force = "--fetch" in sys.argv
    M = fetch(force)
    CAR = M["JHD"]
    HOUSE = [M[k] for k in M if k != "JHD"][0]
    HOUSE_ID = [k for k in M if k != "JHD"][0]
    N = sg.load(neutral=True)
    MC = np.load(os.path.join(OUT, "motion_configs.npz"))

    print("=" * 78)
    print("1. 기하 — 20도 / 직교 / 방향")
    print("=" * 78)
    V = HOUSE.reshape(-1, 3)
    n = np.cross(HOUSE[:, 1] - HOUSE[:, 0], HOUSE[:, 2] - HOUSE[:, 0])
    ar = np.linalg.norm(n, axis=1)
    nn = n / np.maximum(ar[:, None], 1e-12)
    cz = HOUSE.mean(1)[:, 2]
    deck = (np.abs(cz - C["DECK_Z"]) < 1e-3) & (nn[:, 2] > 0.5)
    chk(deck.sum() > 4, "덱 상면(경사 외피) 존재", f"삼각형 {int(deck.sum())}")
    ndeck = (nn[deck] * ar[deck, None]).sum(0) / ar[deck].sum()
    ndeck = ndeck / np.linalg.norm(ndeck)
    ang_up = np.degrees(np.arccos(np.clip(float(ndeck @ UP), -1, 1)))
    ang_ax = np.degrees(np.arccos(np.clip(float(ndeck @ np.array([0, 0, 1.0])), -1, 1)))
    chk(abs(ang_up - 20.0) < 1e-4, "덱 vs 월드 수평 = 20.000000 deg",
        f"{ang_up:.9f} deg  (면적 {ar[deck].sum():.1f} mm2)")
    chk(ang_ax < 1e-4, "그립 중립축 ⟂ 실제 덱면 = 90.000000 deg",
        f"{90.0 - ang_ax:.9f} deg")
    gb = (nn @ UP < -0.9999)
    chk(gb.any(), "지면 접촉면 법선 = -UP_LOCAL", f"면적 {ar[gb].sum():.1f} mm2")
    chk(UP[1] > 0, "TOP -> -Y 방향 유지", f"UP={np.round(UP, 6).tolist()}")

    print("\n" + "=" * 78)
    print("2. 스톡 보존")
    print("=" * 78)
    chk(T["ps_eid"] not in (STOCK_PS, wc.EID_JOYSTICK),
        "신규 Part Studio 에만 생성", T["ps_eid"])
    r = session().get(f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{STOCK_PS}",
                      params=[("configuration", "default")], timeout=180)
    stock = sorted(x["partId"] for x in r.json() if x.get("bodyType") == "solid")
    chk(stock == ["JJD", "JaD", "JmD", "RKCD", "ROCD", "RRBD", "RYBD"],
        "스톡 Base Part Studio solid 7개 그대로", str(stock))
    lo_b, hi_b = bbox(N["Base <1>"])
    chk(abs(lo_b[2] - C["BASE_BOT"]) < 1e-4 and abs(hi_b[0] - lo_b[0] - 100.0) < 1e-3,
        "스톡 Base 형상 무변화 (밑면 Z / 100x100)",
        f"Z {lo_b[2]:.4f}  {hi_b[0]-lo_b[0]:.3f}x{hi_b[1]-lo_b[1]:.3f}")

    print("\n" + "=" * 78)
    print("3. 장착 끼움")
    print("=" * 78)
    lo, hi = bbox(CAR)
    chk(abs((hi[0] - lo[0]) - C["CAR_OUT"]) < 0.02,
        "캐리어 외곽 = 117.600", f"{hi[0]-lo[0]:.3f} x {hi[1]-lo[1]:.3f}")
    chk(abs(hi[2] - C["CAR_TOP"]) < 0.01 and abs(lo[2] - C["CAR_BOT"]) < 0.01,
        "캐리어 Z 범위", f"[{lo[2]:.4f}, {hi[2]:.4f}]")
    hl, hh = bbox(HOUSE)
    chk(abs((hh[0] - hl[0]) - C["HOUSE_OUT"]) < 0.02,
        f"하우징 외곽 X = {C['HOUSE_OUT']:.3f}", f"{hh[0]-hl[0]:.3f} x {hh[1]-hl[1]:.3f}")
    chk(abs(C["HOUSE_IN"] - C["CAR_OUT"] - 2 * C["FIT"]) < 1e-6,
        "캐리어 <-> 하우징 스피곳 끼움 0.20 mm/side",
        f"{(C['HOUSE_IN']-C['CAR_OUT'])/2:.3f}")
    chk(abs((C["POCK_X"] - 100.0) / 2 - 0.30) < 1e-6,
        "스톡 Base <-> 캐리어 포켓 0.30 mm/side",
        f"포켓 {C['POCK_X']:.3f} x {C['POCK_Y']:.3f}, 깊이 {C['POCK_D']:.1f}")

    print("\n" + "=" * 78)
    print("4. 간섭 (중립 + ±10 X/Y + 코너 4)")
    print("=" * 78)
    VC = voxels(CAR, 1.2)
    print(f"   캐리어 복셀 {len(VC)}")
    hit = int(inside_mesh(HOUSE, VC).sum())
    chk(hit == 0, "캐리어 <-> 하우징 간섭", f"{hit} 복셀")

    for k in FIXED:
        Vk = voxels(N[k], 2.0)
        a = int(inside_mesh(CAR, Vk).sum())
        b = int(inside_mesh(HOUSE, Vk).sum())
        chk(a == 0 and b == 0, f"{k.split()[0]} <-> 캐리어 / 하우징",
            f"{a} / {b} 복셀 ({len(Vk)})")

    cfgs = sorted(set(k.split("|")[0] for k in MC.files))
    for c in cfgs:
        pts = [MC[k].reshape(-1, 3) for k in MC.files if k.startswith(c + "|")]
        Q = np.concatenate(pts)
        Q = Q[(Q[:, 2] > C["CAR_BOT"] - 5) & (Q[:, 2] < C["DECK_Z"] + 5)]
        Q = Q[:: max(1, len(Q) // 25000)]
        h = int(inside_mesh(HOUSE, Q).sum())
        cc = int(inside_mesh(CAR, Q).sum())
        chk(h == 0 and cc == 0, f"이동부 <-> 하우징/캐리어 [{c}]",
            f"{h} / {cc}  (표본 {len(Q)})")

    E = np.concatenate([N[k].reshape(-1, 3) for k in N
                        if k.startswith(("micro", "atmega", "MICRO_"))])
    E = E[:: max(1, len(E) // 12000)]
    a = int(inside_mesh(CAR, E).sum())
    b = int(inside_mesh(HOUSE, E).sum())
    chk(a == 0 and b == 0, "전장 / 배선 <-> 캐리어 / 하우징",
        f"{a} / {b}  (표본 {len(E)})")

    print("\n" + "=" * 78)
    print("5. 서비스성 — 카트리지+캐리어 하방 인출")
    print("=" * 78)
    stockpts = np.concatenate([voxels(N[k], 2.5) for k in FIXED])
    grp = np.concatenate([VC[:: 3], stockpts])
    blocked = None
    for t in np.arange(0.0, 100.1, 2.0):
        Q = grp.copy()
        Q[:, 2] -= t
        nh = int(inside_mesh(HOUSE, Q).sum())
        if nh:
            blocked = (float(t), nh)
            break
    chk(blocked is None, "카트리지+캐리어 -Z 인출 0..100 mm 무충돌",
        "무충돌" if blocked is None else f"t={blocked[0]} 에서 {blocked[1]} 복셀")

    # 나사 접근성: C1/C2 와 캐리어 나사 아래로 공구 경로
    print("\n   나사 접근 (아래에서 -Z 방향 공구 경로, ⌀6 드라이버)")
    for lab, xy in (("C1", C["C1"]), ("C2", C["C2"])):
        col = None
        for t in np.arange(0.0, 120.1, 2.0):
            ring = []
            for a2 in np.linspace(0, 2 * np.pi, 12, endpoint=False):
                ring.append([xy[0] + 3.0 * np.cos(a2), xy[1] + 3.0 * np.sin(a2),
                             C["CAR_BOT"] - t])
            R2 = np.array(ring)
            if int(inside_mesh(HOUSE, R2).sum()) or int(inside_mesh(CAR, R2).sum()):
                col = float(t)
                break
        chk(col is None or col > 40.0, f"{lab} 드라이버 접근",
            "무간섭 120mm" if col is None else f"{col:.0f} mm 에서 간섭")

    print("\n" + "=" * 78)
    print("6. 최종 치수")
    print("=" * 78)
    gz = float((V @ UP).min())
    deck_world = float(np.array([C["CX"], C["CY"], C["DECK_Z"]]) @ UP)
    hand_world = float(HAND @ UP)
    cart_keys = [k for k in N if k.startswith(("micro", "atmega", "MICRO_", "Base <",
                                               "Roll_holder", "Spacer"))]
    stock_low = float(min((N[k].reshape(-1, 3) @ UP).min() for k in cart_keys))
    stock_low_z = float(min(N[k].reshape(-1, 3)[:, 2].min() for k in cart_keys))
    car_low = float((CAR.reshape(-1, 3) @ UP).min())
    res = {
        "경사 덱 -> HAND_REF (덱 법선)": HAND[2] - C["DECK_Z"],
        "고정 지지 바닥 -> HAND_REF (월드수직)": hand_world - gz,
        "덱 -> 스톡 짐벌 피벗 (덱 법선)": C["DECK_Z"] - PIV[2],
        "덱 -> 스톡 짐벌 최저점 (덱 법선)": C["DECK_Z"] - stock_low_z,
        "덱 아래 카트리지 돌출 (월드수직)": deck_world - stock_low,
        "전체 높이 (지면 -> 덱 상면, 월드수직)": deck_world - gz,
        "지면 -> 카트리지 최저 (여유)": stock_low - gz,
        "지면 -> 캐리어 밑면 (여유)": car_low - gz,
    }
    for k, v in res.items():
        print(f"   {k:<42s} {v:10.4f} mm")
    print(f"   {'하우징 풋프린트':<42s} {hh[0]-hl[0]:.3f} x {hh[1]-hl[1]:.3f} mm")
    print(f"   {'하우징 높이 (그립 Z 범위)':<42s} {hh[2]-hl[2]:.3f} mm")
    print(f"   {'덱 개구':<42s} {C['OP_W']:.3f} x {C['OP_H']:.3f} mm (R8)")
    print(f"   {'캐리어':<42s} {hi[0]-lo[0]:.3f} x {hi[1]-lo[1]:.3f} x "
          f"{hi[2]-lo[2]:.3f} mm")
    print(f"   {'캐리어 두께 (포켓 바닥 아래)':<42s} {C['CAR_FLOOR_T']:.3f} mm")
    print(f"   {'최소 구조 벽 두께':<42s} {C['WALL_T']:.3f} mm (하우징 벽)")

    chk(res["지면 -> 카트리지 최저 (여유)"] >= C["USB_CLR"] - 0.1,
        f"지면 여유 >= usb_clearance ({C['USB_CLR']:.1f})",
        f"{res['지면 -> 카트리지 최저 (여유)']:.3f} mm")

    print("\n" + "=" * 78)
    print(f"결과: PASS {len(PASS)}  /  FAIL {len(FAIL)}")
    for f in FAIL:
        print("   FAIL:", f)
    print("=" * 78)
    json.dump({"pass": PASS, "fail": FAIL,
               "house_partId": HOUSE_ID,
               "dims": {k: float(v) for k, v in res.items()},
               "deck_angle_world": float(ang_up),
               "grip_axis_vs_deck": float(90.0 - ang_ax),
               "footprint": [float(hh[0] - hl[0]), float(hh[1] - hl[1])],
               "carrier": [float(hi[0] - lo[0]), float(hi[1] - lo[1]),
                           float(hi[2] - lo[2])]},
              io.open(os.path.join(OUT, "cartridge_verify.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
