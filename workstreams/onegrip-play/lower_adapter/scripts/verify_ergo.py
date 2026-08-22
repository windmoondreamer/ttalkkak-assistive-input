"""W2 인체공학 외피 검증 + 측정. GET only."""
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
T = json.load(io.open(os.path.join(OUT, "ergo_target.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
UH = np.array([0.0, 0.9396926207859084, -0.3420201433256687])
HAND = np.array(C["HAND_REF"])
PIV = np.array(C["PIVOT"])
DECK = C["DECK_Z"]
STOCK_PS = "df9a32f1f239bc71a732f5d3"
FIXED = ("Base <1>", "Roll_holder <1>", "Roll_holder_2 <1>", "Spacer <1>")
CACHE = os.path.join(OUT, "ergo_meshes.npz")
PAD_ANGLE, PAD_LEN, PAD_W, ANCHOR_Y = 7.0, 85.0, 86.0, -20.0

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
                    ("chordTolerance", "0.0003")], timeout=300).json()
        tri = sg._tris(j) * 1000.0
        out[p["partId"]] = tri.astype(np.float32)
        print(f"   {p['partId']:<6s} tri {len(tri)}")
    np.savez_compressed(CACHE, **out)
    return {k: v.astype(np.float64) for k, v in out.items()}


def main():
    M = fetch("--fetch" in sys.argv)
    vols = {k: float(np.abs((np.cross(M[k][:, 0], M[k][:, 1]) * M[k][:, 2]).sum() / 6))
            for k in M}
    SH, CAR = M[max(vols, key=vols.get)], M[min(vols, key=vols.get)]
    N = sg.load(neutral=True)
    MC = np.load(os.path.join(OUT, "motion_configs.npz"))

    V = SH.reshape(-1, 3)
    n = np.cross(SH[:, 1] - SH[:, 0], SH[:, 2] - SH[:, 0])
    # |cross| 은 삼각형 넓이의 **2배**다. 면적은 나누고,
    # 법선 정규화는 원래 크기로 해야 한다 (여기서 한 번 틀려서 접지면적이 9배로 나왔다).
    mag = np.linalg.norm(n, axis=1)
    ar = mag / 2.0
    nn = n / np.maximum(mag[:, None], 1e-12)
    cen = SH.mean(1)

    print("=" * 78)
    print("1. 인체공학 기준면 (변경 없어야 한다)")
    print("=" * 78)
    top = (np.abs(cen[:, 2] - DECK) < 1e-3) & (nn[:, 2] > 0.5)
    chk(top.sum() > 4, "20도 인체공학 기준면 존재", f"삼각형 {int(top.sum())}, "
        f"면적 {ar[top].sum():.1f} mm2")
    nd = (nn[top] * ar[top, None]).sum(0) / ar[top].sum()
    nd = nd / np.linalg.norm(nd)
    a_up = np.degrees(np.arccos(np.clip(float(nd @ UP), -1, 1)))
    a_ax = np.degrees(np.arccos(np.clip(float(nd @ np.array([0, 0, 1.0])), -1, 1)))
    chk(abs(a_up - 20.0) < 1e-4, "기준면 vs 월드 수평 = 20.000000 deg", f"{a_up:.9f}")
    chk(a_ax < 1e-4, "그립 중립축 ⟂ 기준면 = 90.000000 deg", f"{90 - a_ax:.9f}")
    chk(abs(float(HAND[2]) - (-6.0)) < 1e-9,
        "HAND_REF 변화 = 0", f"{np.round(HAND, 6).tolist()} (코어 미수정)")
    chk(UP[1] > 0, "TOP -> -Y 유지", f"UP={np.round(UP, 6).tolist()}")

    print("\n" + "=" * 78)
    print("2. 손목 받침면")
    print("=" * 78)
    # 패드 평면 (설계값으로 재구성)
    au = ANCHOR_Y * UH[1] + DECK * UH[2]
    ah = ANCHOR_Y * UP[1] + DECK * UP[2]
    fu = au - PAD_LEN
    fh = ah - PAD_LEN * np.tan(np.radians(PAD_ANGLE))
    fy, fz = fu * UH[1] + fh * UP[1], fu * UH[2] + fh * UP[2]
    dy, dz = fy - ANCHOR_Y, fz - DECK
    ln = np.hypot(dy, dz)
    npad = np.array([0.0, dz / ln, -dy / ln])
    dpad = npad @ np.array([0.0, ANCHOR_Y, DECK])
    # 패드 평면은 무한하므로 평면 조건만으로는 다른 면까지 걸린다.
    # 실제 손목이 닿는 면 = 패드 평면 + 패드 평면상 XY 범위 안.
    onpad = ((np.abs(cen @ npad - dpad) < 0.2) & (nn @ npad > 0.95)
             & (np.abs(cen[:, 0]) <= PAD_W / 2 + 0.5)
             & (cen[:, 1] >= fy - 0.5) & (cen[:, 1] <= ANCHOR_Y + 0.5))
    area = float(ar[onpad].sum())
    chk(area > 3000, "손목 받침면 실측 면적", f"{area:,.0f} mm2 "
        f"(설계 {PAD_W}x{PAD_LEN} 라운드 = {PAD_W*PAD_LEN*0.88:,.0f})")
    pa = np.degrees(np.arccos(np.clip(float(npad @ UP), -1, 1)))
    chk(abs(pa - PAD_ANGLE) < 0.01, "받침면 상승각", f"{pa:.4f} deg (설계 {PAD_ANGLE})")
    P = cen[onpad]
    if len(P):
        pw = P @ UP
        print(f"        받침면 지면 위 {pw.min()-K['GROUND']:.1f} .. "
              f"{pw.max()-K['GROUND']:.1f} mm   HAND_REF 아래 "
              f"{float(HAND@UP)-pw.max():.1f} .. {float(HAND@UP)-pw.min():.1f} mm")

    print("\n" + "=" * 78)
    print("3. 스톡 보존 / 코어 동일성")
    print("=" * 78)
    chk(T["ps_eid"] not in (STOCK_PS, wc.EID_JOYSTICK, "8945f7ac4100dfd52a8c8dba"),
        "신규 Part Studio 에만 생성", T["ps_eid"])
    r = session().get(f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{STOCK_PS}",
                      params=[("configuration", "default")], timeout=180)
    st = sorted(x["partId"] for x in r.json() if x.get("bodyType") == "solid")
    chk(st == ["JJD", "JaD", "JmD", "RKCD", "ROCD", "RRBD", "RYBD"],
        "스톡 Base Part Studio solid 7개 무변화", str(st))
    cl, ch = bbox(CAR)
    chk(abs((ch[0] - cl[0]) - 118.0) < 0.05 and abs(ch[2] - K["CAR_TOP"]) < 0.01,
        "BOTTOM_CARRIER 코어와 동일", f"{ch[0]-cl[0]:.2f} x {ch[1]-cl[1]:.2f} x "
        f"{ch[2]-cl[2]:.2f}, Z top {ch[2]:.4f}")

    print("\n" + "=" * 78)
    print("4. 모션 간섭 (9자세)")
    print("=" * 78)
    VC = voxels(CAR, 1.5)
    chk(int(inside_mesh(SH, VC).sum()) == 0, "캐리어 <-> 외피",
        f"{int(inside_mesh(SH, VC).sum())} 복셀")
    for k in FIXED:
        Vk = voxels(N[k], 2.0)
        a = int(inside_mesh(CAR, Vk).sum())
        b = int(inside_mesh(SH, Vk).sum())
        chk(a == 0 and b == 0, f"{k.split()[0]} <-> 캐리어 / 외피", f"{a} / {b}")
    for c in sorted(set(k.split("|")[0] for k in MC.files)):
        Q = np.concatenate([MC[k].reshape(-1, 3) for k in MC.files
                            if k.startswith(c + "|")])
        Q = Q[(Q[:, 2] > K["CAR_BOT"] - 5)]
        Q = Q[:: max(1, len(Q) // 25000)]
        h = int(inside_mesh(SH, Q).sum())
        cc = int(inside_mesh(CAR, Q).sum())
        chk(h == 0 and cc == 0, f"이동부 <-> 외피/캐리어 [{c}]", f"{h} / {cc}")
    E = np.concatenate([N[k].reshape(-1, 3) for k in N
                        if k.startswith(("micro", "atmega", "MICRO_"))])
    E = E[:: max(1, len(E) // 12000)]
    chk(int(inside_mesh(SH, E).sum()) == 0 and int(inside_mesh(CAR, E).sum()) == 0,
        "전장(Arduino/USB) <-> 외피 / 캐리어",
        f"{int(inside_mesh(SH, E).sum())} / {int(inside_mesh(CAR, E).sum())}")

    print("\n" + "=" * 78)
    print("5. 서비스 / 접지 / 배선")
    print("=" * 78)
    stockpts = np.concatenate([voxels(N[k], 2.5) for k in FIXED])
    grp = np.concatenate([VC[::2], stockpts])
    blocked = None
    for t in np.arange(0.0, 100.1, 2.0):
        Q = grp.copy()
        Q[:, 2] -= t
        if int(inside_mesh(SH, Q).sum()):
            blocked = float(t)
            break
    chk(blocked is None, "모듈+캐리어 -Z 인출 0..100 mm",
        "무충돌" if blocked is None else f"t={blocked} 차단")
    gz = float((V @ UP).min())
    sw = np.concatenate([N[k].reshape(-1, 3) for k in N]) @ UP
    chk(int((sw < gz - 1e-6).sum()) == 0, "지지 평면 아래 스톡 돌출 없음",
        f"최저 스톡 {sw.min():.4f} vs 지면 {gz:.4f}  (여유 {sw.min()-gz:+.3f})")
    # USB 경로: 커넥터 앞 -> -X 측면 밖까지 재료가 없는가
    usb = np.array([0.14, -63.0, -151.2])
    path = [usb + np.array([0, -1.0, 0]) * t for t in np.arange(0, 13, 1.0)]
    path += [np.array([-x, -70.0, -151.2]) for x in np.arange(0, 75, 2.0)]
    P2 = np.array(path)
    blocked2 = int(inside_mesh(SH, P2).sum()) + int(inside_mesh(CAR, P2).sum())
    chk(blocked2 == 0, "USB 플러그 -> -X 측면 인출 경로 개방",
        f"{blocked2} / {len(P2)} 지점 차단")

    print("\n" + "=" * 78)
    print("6. 최종 측정")
    print("=" * 78)
    hl, hh = bbox(SH)
    wpad_pts = cen[onpad]
    res = {
        "경사 인체공학면 -> HAND_REF": HAND[2] - DECK,
        "고정 외부 바닥 -> HAND_REF": float(HAND @ UP) - gz,
        "스톡 최저 -> 하우징 바닥": float(sw.min()) - gz,
        "STOCK_PROTRUSION_BELOW_HOUSING": max(0.0, gz - float(sw.min())),
        "스톡 피벗 -> 인체공학면": DECK - PIV[2],
    }
    for k, v in res.items():
        print(f"   {k:<40s} {v:10.4f} mm")
    print(f"   {'외형 W x L x 최대높이':<40s} {hh[0]-hl[0]:.1f} x {hh[1]-hl[1]:.1f} x "
          f"{float((V@UP).max())-gz:.1f} mm")
    gb = nn @ UP < -0.9999
    foot = V[np.abs(V @ UP - gz) < 0.05]
    print(f"   {'접지 풋프린트':<40s} "
          f"{foot[:,0].max()-foot[:,0].min():.1f} x {foot[:,1].max()-foot[:,1].min():.1f}"
          f" mm  (면적 {ar[gb].sum():,.0f} mm2)")
    print(f"   {'손목 받침 유효 면적':<40s} {area:,.0f} mm2")
    print(f"   {'외피 부피 / 캐리어':<40s} {vols[max(vols, key=vols.get)]:,.0f} / "
          f"{vols[min(vols, key=vols.get)]:,.0f} mm3")
    print(f"   {'코어(495,615) 대비 추가':<40s} "
          f"{vols[max(vols, key=vols.get)]-495615:+,.0f} mm3")

    print("\n" + "=" * 78)
    print(f"결과: PASS {len(PASS)}  /  FAIL {len(FAIL)}")
    for f in FAIL:
        print("   FAIL:", f)
    print("=" * 78)
    json.dump({"pass": PASS, "fail": FAIL,
               "dims": {k: float(v) for k, v in res.items()},
               "pad_area": area, "volumes": vols, "ground": gz,
               "wlh": [float(hh[0]-hl[0]), float(hh[1]-hl[1]),
                       float(float((V@UP).max())-gz)]},
              io.open(os.path.join(OUT, "ergo_verify.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
