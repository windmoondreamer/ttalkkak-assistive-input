"""컨포멀 매립 하우징 최종 검증 (§22) + 측정 (§18). GET only."""
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
from verify_cartridge import bbox, inside_mesh, voxels    # noqa: E402

OUT = sg.OUT
C = json.load(io.open(os.path.join(OUT, "cartridge_constants.json"), encoding="utf-8"))
K = json.load(io.open(os.path.join(OUT, "conformal_constants.json"), encoding="utf-8"))
T = json.load(io.open(os.path.join(OUT, "conformal_target.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
HAND = np.array(C["HAND_REF"])
PIV = np.array(C["PIVOT"])
DECK_Z = C["DECK_Z"]
STOCK_PS = "df9a32f1f239bc71a732f5d3"
FIXED = ("Base <1>", "Roll_holder <1>", "Roll_holder_2 <1>", "Spacer <1>")
CACHE = os.path.join(OUT, "conformal_meshes.npz")

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
        print(f"   {p['partId']:<6s} tri {len(tri)}")
    np.savez_compressed(CACHE, **out)
    return {k: v.astype(np.float64) for k, v in out.items()}


def main():
    M = fetch("--fetch" in sys.argv)
    keys = sorted(M, key=lambda k: -len(M[k].reshape(-1, 3)))
    vols = {k: float(np.abs((np.cross(M[k][:, 0], M[k][:, 1]) * M[k][:, 2]).sum() / 6))
            for k in M}
    HOUSE_ID = max(vols, key=vols.get)
    CAR_ID = min(vols, key=vols.get)
    HOUSE, CAR = M[HOUSE_ID], M[CAR_ID]
    N = sg.load(neutral=True)
    MC = np.load(os.path.join(OUT, "motion_configs.npz"))

    print("=" * 78)
    print("1. 인체공학 기하 — 20.000 / 90.000 / TOP -> -Y")
    print("=" * 78)
    V = HOUSE.reshape(-1, 3)
    n = np.cross(HOUSE[:, 1] - HOUSE[:, 0], HOUSE[:, 2] - HOUSE[:, 0])
    # |cross| 은 삼각형 넓이의 **2배**다. 면적은 나누고,
    # 법선 정규화는 원래 크기로 해야 한다 (여기서 한 번 틀려서 접지면적이 9배로 나왔다).
    mag = np.linalg.norm(n, axis=1)
    ar = mag / 2.0
    nn = n / np.maximum(mag[:, None], 1e-12)
    cz = HOUSE.mean(1)[:, 2]
    top = (np.abs(cz - DECK_Z) < 1e-3) & (nn[:, 2] > 0.5)
    chk(top.sum() > 4, "경사 외피(인체공학 기준면) 존재", f"삼각형 {int(top.sum())}, "
        f"면적 {ar[top].sum():.1f} mm2")
    nd = (nn[top] * ar[top, None]).sum(0) / ar[top].sum()
    nd = nd / np.linalg.norm(nd)
    a_up = np.degrees(np.arccos(np.clip(float(nd @ UP), -1, 1)))
    a_ax = np.degrees(np.arccos(np.clip(float(nd @ np.array([0, 0, 1.0])), -1, 1)))
    chk(abs(a_up - 20.0) < 1e-4, "외피 vs 월드 수평 = 20.000000 deg", f"{a_up:.9f}")
    chk(a_ax < 1e-4, "그립 중립축 ⟂ 실제 외피면 = 90.000000 deg", f"{90 - a_ax:.9f}")
    gb = nn @ UP < -0.9999
    chk(gb.any(), "접지면 법선 = -UP_LOCAL", f"면적 {ar[gb].sum():.1f} mm2")
    chk(UP[1] > 0, "TOP -> -Y 유지", f"UP={np.round(UP, 6).tolist()}")

    print("\n" + "=" * 78)
    print("2. 스톡 보존")
    print("=" * 78)
    chk(T["ps_eid"] not in (STOCK_PS, wc.EID_JOYSTICK), "신규 Part Studio 에만 생성",
        T["ps_eid"])
    r = session().get(f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{STOCK_PS}",
                      params=[("configuration", "default")], timeout=180)
    st = sorted(x["partId"] for x in r.json() if x.get("bodyType") == "solid")
    chk(st == ["JJD", "JaD", "JmD", "RKCD", "ROCD", "RRBD", "RYBD"],
        "스톡 Base Part Studio solid 7개 무변화", str(st))
    lo_b, hi_b = bbox(N["Base <1>"])
    chk(abs(lo_b[2] - C["BASE_BOT"]) < 1e-4, "스톡 Base 밑면 Z 무변화", f"{lo_b[2]:.4f}")

    print("\n" + "=" * 78)
    print("3. 간섭 (중립 + ±10 X/Y + 코너 4)")
    print("=" * 78)
    VC = voxels(CAR, 1.5)
    hit = int(inside_mesh(HOUSE, VC).sum())
    chk(hit == 0, "캐리어 <-> 하우징", f"{hit} 복셀 ({len(VC)})")
    for k in FIXED:
        Vk = voxels(N[k], 2.0)
        a = int(inside_mesh(CAR, Vk).sum())
        b = int(inside_mesh(HOUSE, Vk).sum())
        chk(a == 0 and b == 0, f"{k.split()[0]} <-> 캐리어 / 하우징", f"{a} / {b}")
    for c in sorted(set(k.split("|")[0] for k in MC.files)):
        Q = np.concatenate([MC[k].reshape(-1, 3) for k in MC.files
                            if k.startswith(c + "|")])
        Q = Q[(Q[:, 2] > K["CAR_BOT"] - 5) & (Q[:, 2] < DECK_Z + 5)]
        Q = Q[:: max(1, len(Q) // 25000)]
        h = int(inside_mesh(HOUSE, Q).sum())
        cc = int(inside_mesh(CAR, Q).sum())
        chk(h == 0 and cc == 0, f"이동부 <-> 하우징/캐리어 [{c}]", f"{h} / {cc}")
    E = np.concatenate([N[k].reshape(-1, 3) for k in N
                        if k.startswith(("micro", "atmega", "MICRO_"))])
    E = E[:: max(1, len(E) // 12000)]
    a = int(inside_mesh(CAR, E).sum())
    b = int(inside_mesh(HOUSE, E).sum())
    chk(a == 0 and b == 0, "전장(Arduino/USB) <-> 캐리어 / 하우징", f"{a} / {b}")

    print("\n" + "=" * 78)
    print("4. 서비스 — 스톡 모듈 + 캐리어 하방 인출")
    print("=" * 78)
    stockpts = np.concatenate([voxels(N[k], 2.5) for k in FIXED])
    grp = np.concatenate([VC[::2], stockpts])
    blocked = None
    for t in np.arange(0.0, 100.1, 2.0):
        Q = grp.copy()
        Q[:, 2] -= t
        nh = int(inside_mesh(HOUSE, Q).sum())
        if nh:
            blocked = (float(t), nh)
            break
    chk(blocked is None, "모듈+캐리어 -Z 인출 0..100 mm 무충돌",
        "무충돌" if blocked is None else f"t={blocked[0]} 에서 {blocked[1]}")

    print("\n" + "=" * 78)
    print("5. 접지면 아래 돌출")
    print("=" * 78)
    gz = float((V @ UP).min())
    stock_all = np.concatenate([N[k].reshape(-1, 3) for k in N])
    sw = stock_all @ UP
    below = int((sw < gz - 1e-6).sum())
    chk(below == 0, "지지 평면 아래로 나오는 스톡 부품 없음",
        f"{below} 정점,  최저 스톡 {sw.min():.4f} vs 지면 {gz:.4f}")
    cw = CAR.reshape(-1, 3) @ UP
    chk(cw.min() >= gz - 1e-6, "캐리어도 지지 평면 위",
        f"{cw.min():.4f}")

    print("\n" + "=" * 78)
    print("6. §18 측정")
    print("=" * 78)
    hl, hh = bbox(HOUSE)
    cl, ch = bbox(CAR)
    stock_low_w = float(sw.min())
    dims = {
        "A 경사 인체공학면 -> HAND_REF": HAND[2] - DECK_Z,
        "B 고정 외부 하우징 바닥 -> HAND_REF": float(HAND @ UP) - gz,
        "C 스톡 최저점 -> 하우징 바닥": stock_low_w - gz,
        "D STOCK_PROTRUSION_BELOW_FINAL_HOUSING": max(0.0, gz - stock_low_w),
        "H 스톡 피벗 -> 경사 인체공학면": DECK_Z - PIV[2],
    }
    for k, v in dims.items():
        print(f"   {k:<44s} {v:10.4f} mm")
    print(f"   {'E 내부 공동 (최대 폭 x 길이 x 깊이)':<44s} "
          f"{max(m['x1'] - m['x0'] for m in K['cav']):.1f} x "
          f"{max(m['y1'] - m['y0'] for m in K['cav']):.1f} x "
          f"{DECK_Z - K['cav'][0]['z0']:.1f} mm")
    print(f"   {'F 외부 하우징 (W x L x 최대높이)':<44s} "
          f"{hh[0] - hl[0]:.1f} x {hh[1] - hl[1]:.1f} x "
          f"{float((V @ UP).max()) - gz:.1f} mm")
    # 접지 footprint
    foot = V[np.abs(V @ UP - gz) < 0.05]
    fw = (foot[:, 0].max() - foot[:, 0].min()) if len(foot) else 0
    fl = (foot[:, 1].max() - foot[:, 1].min()) if len(foot) else 0
    print(f"   {'G 접지 풋프린트':<44s} {fw:.1f} x {fl:.1f} mm  "
          f"(면적 {ar[gb].sum():.0f} mm2)")
    print(f"   {'I 스톡 둘레 벽 두께 (설계)':<44s} {K['WALL']:.1f} mm "
          f"(스커트 {K['SKIRT_T']:.1f}, 플랜지 {K['FLANGE']:.1f})")
    print(f"   {'캐리어':<44s} {ch[0] - cl[0]:.1f} x {ch[1] - cl[1]:.1f} x "
          f"{ch[2] - cl[2]:.1f} mm")
    print(f"   {'부피 (하우징 / 캐리어)':<44s} {vols[HOUSE_ID]:.0f} / "
          f"{vols[CAR_ID]:.0f} mm3   PLA {vols[HOUSE_ID]*1.24e-3:.0f} / "
          f"{vols[CAR_ID]*1.24e-3:.0f} g")

    print("\n" + "=" * 78)
    print(f"결과: PASS {len(PASS)}  /  FAIL {len(FAIL)}")
    for f in FAIL:
        print("   FAIL:", f)
    print("=" * 78)
    json.dump({"pass": PASS, "fail": FAIL, "dims": {k: float(v) for k, v in dims.items()},
               "house_id": HOUSE_ID, "carrier_id": CAR_ID,
               "volumes": vols, "ground_world": gz,
               "footprint": [float(hh[0] - hl[0]), float(hh[1] - hl[1])],
               "max_height": float(float((V @ UP).max()) - gz),
               "deck_angle": float(a_up), "perp": float(90 - a_ax)},
              io.open(os.path.join(OUT, "conformal_verify.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
