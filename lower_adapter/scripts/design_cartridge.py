"""OPTION C 카트리지 설계 상수 생성 + 사전 검증 (CAD WRITE 없음).

- 스톡 고정부/이동부 실측 -> 덱 개구부 / 캐리어 포켓 / 나사 스택업 확정
- 결과를 lower_adapter/cad_dump/cartridge_constants.json 에 저장
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

OUT = sg.OUT
SEAT_Z = sg.SEAT_Z
PIVOT = np.array(sg.PIVOT)
UP_LOCAL = np.array([0.0, 0.3420201433256687, 0.9396926207859084])   # 월드 수직(그립좌표)
HAND_REF = np.array([-8.960946, -13.645934, -6.000])                 # docs/03~05 정의

TRAVEL = 10.0            # deg
FDM = 1.5                # mm/side, 덱 개구부
CLR_POCKET = 0.30        # mm/side, 포켓 끼움

# 이동부 / 고정부 (프레임 판정은 verify_stock_frames.py 로 확인)
FIXED = ["Base <1>", "Roll_holder <1>", "Roll_holder_2 <1>", "Spacer <1>"]


def rotm(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def main():
    N = sg.load(neutral=True)
    keys = list(N)
    roll_only = ["Roll <1>"]
    grip_frame = [k for k in keys
                  if k not in FIXED and k not in roll_only
                  and not k.startswith(("micro", "atmega", "MICRO_"))]

    print("이동부(GRIP 프레임):", len(grip_frame), "개")
    print("이동부(ROLL 프레임):", roll_only)
    print("고정부:", FIXED)

    # ---------- 1. 스톡 인터페이스 상수 ----------
    B = N["Base <1>"].reshape(-1, 3)
    BASE_BOT = B[:, 2].min()
    BASE_TOP = B[:, 2].max()
    print(f"\nBase Z [{BASE_BOT:.4f}, {BASE_TOP:.4f}]  두께 {BASE_TOP-BASE_BOT:.3f}")

    # 본체 / 꼬리 경계
    at_bot = B[np.abs(B[:, 2] - BASE_BOT) < 1e-3]
    wide = at_bot[np.abs(at_bot[:, 0]) > 20]
    JUNC_Y = wide[:, 1].min()
    tail = at_bot[at_bot[:, 1] < JUNC_Y - 0.01]
    body = at_bot[at_bot[:, 1] >= JUNC_Y - 0.01]
    BODY = [body[:, 0].min(), body[:, 0].max(), body[:, 1].min(), body[:, 1].max()]
    TAIL = [tail[:, 0].min(), tail[:, 0].max(), tail[:, 1].min(), tail[:, 1].max()]
    print(f"본체 X[{BODY[0]:.4f},{BODY[1]:.4f}] Y[{BODY[2]:.4f},{BODY[3]:.4f}]  "
          f"{BODY[1]-BODY[0]:.3f} x {BODY[3]-BODY[2]:.3f}")
    print(f"꼬리 X[{TAIL[0]:.4f},{TAIL[1]:.4f}] Y[{TAIL[2]:.4f},{TAIL[3]:.4f}]  "
          f"{TAIL[1]-TAIL[0]:.3f} x {JUNC_Y-TAIL[2]:.3f}")

    # ---------- 2. 모션 포락선 ----------
    cfgs = [("neutral", 0, 0), ("X+10", TRAVEL, 0), ("X-10", -TRAVEL, 0),
            ("Y+10", 0, TRAVEL), ("Y-10", 0, -TRAVEL),
            ("X+10Y+10", TRAVEL, TRAVEL), ("X+10Y-10", TRAVEL, -TRAVEL),
            ("X-10Y+10", -TRAVEL, TRAVEL), ("X-10Y-10", -TRAVEL, -TRAVEL)]

    def moved(beta, alpha):
        """beta = pitch(X축), alpha = roll(Y축).  ROLL 프레임은 alpha 만."""
        Ry = rotm("y", alpha)
        R = Ry @ rotm("x", beta)
        out = {}
        for k in grip_frame:
            P = N[k].reshape(-1, 3)
            out[k] = (P - PIVOT) @ R.T + PIVOT
        for k in roll_only:
            P = N[k].reshape(-1, 3)
            out[k] = (P - PIVOT) @ Ry.T + PIVOT
        return out

    ALL = {c[0]: moved(c[1], c[2]) for c in cfgs}

    # 덱 평면 후보별 필요 개구
    print("\n덱 높이별 필요 개구 (9개 자세 합집합, FDM 여유 미포함)")
    print(f"{'덱Z(착좌면대비)':>16s} {'Xmin':>8s} {'Xmax':>8s} {'Ymin':>8s} {'Ymax':>8s} "
          f"{'크기':>16s}  {'덱위 고정부':>10s}")
    deck_tab = {}
    for rec in (12.0, 9.0, 6.0, 3.0, 0.0, -3.0, -6.0, -9.0, -12.0):
        z = SEAT_Z + rec
        xs, ys = [], []
        for c, parts in ALL.items():
            for k, P in parts.items():
                sel = P[np.abs(P[:, 2] - z) < 1.5]
                if len(sel):
                    xs += [sel[:, 0].min(), sel[:, 0].max()]
                    ys += [sel[:, 1].min(), sel[:, 1].max()]
        if not xs:
            continue
        # 덱 위로 올라오는 고정부
        above = sum(int((N[k].reshape(-1, 3)[:, 2] > z).any()) for k in FIXED)
        deck_tab[rec] = (min(xs), max(xs), min(ys), max(ys), above)
        print(f"{rec:16.1f} {min(xs):8.2f} {max(xs):8.2f} {min(ys):8.2f} {max(ys):8.2f} "
              f"{max(xs)-min(xs):7.2f} x {max(ys)-min(ys):6.2f}  {above:10d}")

    # 채택 덱: 착좌면 +6
    REC = 6.0
    DECK_Z = SEAT_Z + REC
    x0, x1, y0, y1, _ = deck_tab[REC]

    # 덱 두께 전체(6mm)에 걸친 개구 필요 -> 덱 상/하면 사이 최대
    zt, zb = DECK_Z, DECK_Z - 6.0
    xs, ys = [], []
    for c, parts in ALL.items():
        for k, P in parts.items():
            sel = P[(P[:, 2] > zb - 0.5) & (P[:, 2] < zt + 0.5)]
            if len(sel):
                xs += [sel[:, 0].min(), sel[:, 0].max()]
                ys += [sel[:, 1].min(), sel[:, 1].max()]
    OPEN = [min(xs) - FDM, max(xs) + FDM, min(ys) - FDM, max(ys) + FDM]
    print(f"\n채택 덱 Z = {DECK_Z:.4f} (착좌면 +{REC})  두께 6.0")
    print(f"  덱 두께 구간 필요 개구  X[{min(xs):.2f},{max(xs):.2f}] Y[{min(ys):.2f},{max(ys):.2f}]")
    print(f"  + FDM {FDM}/side ->     X[{OPEN[0]:.2f},{OPEN[1]:.2f}] Y[{OPEN[2]:.2f},{OPEN[3]:.2f}]"
          f"  = {OPEN[1]-OPEN[0]:.2f} x {OPEN[3]-OPEN[2]:.2f}")

    # ---------- 3. 최저점 / 높이 ----------
    fixed_low = min((N[k].reshape(-1, 3) @ UP_LOCAL).min() for k in FIXED)
    elec = np.concatenate([N[k].reshape(-1, 3) for k in keys
                           if k.startswith(("micro", "atmega", "MICRO_"))])
    elec_low = (elec @ UP_LOCAL).min()
    deck_h = DECK_Z            # 그립 Z (덱 법선 방향)
    print(f"\n월드수직 좌표 (UP_LOCAL 투영)")
    print(f"  HAND_REF                 {HAND_REF @ UP_LOCAL:10.4f}")
    print(f"  덱 상면 중심             {np.array([0,0,DECK_Z]) @ UP_LOCAL:10.4f}")
    print(f"  스톡 고정부 최저         {fixed_low:10.4f}")
    print(f"  전장(USB) 최저           {elec_low:10.4f}")
    print(f"  피벗                     {PIVOT @ UP_LOCAL:10.4f}")
    print(f"\n  (1) 덱 -> HAND_REF (덱 법선) = {HAND_REF[2] - DECK_Z:8.4f} mm")
    print(f"  (3) 덱 -> 스톡 피벗 (덱 법선) = {DECK_Z - PIVOT[2]:8.4f} mm")

    C = {
        "SEAT_Z": SEAT_Z, "DECK_REC": REC, "DECK_Z": DECK_Z, "DECK_T": 6.0,
        "PIVOT": PIVOT.tolist(), "UP_LOCAL": UP_LOCAL.tolist(),
        "HAND_REF": HAND_REF.tolist(), "TRAVEL": TRAVEL, "FDM": FDM,
        "BASE_BOT": float(BASE_BOT), "BASE_TOP": float(BASE_TOP),
        "BODY": [float(v) for v in BODY], "TAIL": [float(v) for v in TAIL],
        "JUNC_Y": float(JUNC_Y),
        "OPENING": [float(v) for v in OPEN],
        "C1": [0.35443, 60.32524], "C2": [0.35443, -6.94683],
        "TAP_D": 3.000, "TAP_TOP_Z": -136.4565, "TAP_BOTTOM_Z": -123.4565,
        "SLOT_W": 3.4, "SLOT_L": 11.4,
        "CLR_POCKET": CLR_POCKET,
        "fixed_low_world": float(fixed_low), "elec_low_world": float(elec_low),
    }
    json.dump(C, io.open(os.path.join(OUT, "cartridge_constants.json"), "w",
                         encoding="utf-8"), indent=1)
    # 자세별 메시 저장 (검증용)
    np.savez_compressed(os.path.join(OUT, "motion_configs.npz"),
                        **{f"{c}|{k}": v for c, parts in ALL.items()
                           for k, v in parts.items()})
    print("\n저장: cartridge_constants.json / motion_configs.npz")


if __name__ == "__main__":
    main()


def keepout():
    """덱 아래 이동부 keep-out 프리즘 + 다리 배치 여유 계산."""
    import numpy as np
    C = json.load(io.open(os.path.join(OUT, "cartridge_constants.json"), encoding="utf-8"))
    z = np.load(os.path.join(OUT, "motion_configs.npz"))
    DECK_Z, SEAT = C["DECK_Z"], C["SEAT_Z"]
    BASE_TOP = C["BASE_TOP"]

    print("\n덱 아래 이동부 단면 (Z 별, 9자세 합집합)")
    print(f"{'Z':>10s} {'착좌면대비':>10s} {'Xmin':>8s} {'Xmax':>8s} {'Ymin':>8s} "
          f"{'Ymax':>8s} {'크기':>16s}")
    P = np.concatenate([z[k] for k in z.files])
    zs = np.arange(DECK_Z - 6.0, BASE_TOP - 0.5, -2.0)
    gx0 = gx1 = gy0 = gy1 = None
    prev = None
    for zz in zs:
        sel = P[np.abs(P[:, 2] - zz) < 1.0]
        if not len(sel):
            continue
        a, b, c2, d = sel[:, 0].min(), sel[:, 0].max(), sel[:, 1].min(), sel[:, 1].max()
        gx0 = a if gx0 is None else min(gx0, a)
        gx1 = b if gx1 is None else max(gx1, b)
        gy0 = c2 if gy0 is None else min(gy0, c2)
        gy1 = d if gy1 is None else max(gy1, d)
        line = f"{a:8.2f} {b:8.2f} {c2:8.2f} {d:8.2f} {b-a:7.2f} x {d-c2:6.2f}"
        if line != prev:
            print(f"{zz:10.2f} {zz-SEAT:10.2f} {line}")
            prev = line
    print(f"\n덱 아래 전체 keep-out  X[{gx0:.2f},{gx1:.2f}] Y[{gy0:.2f},{gy1:.2f}]"
          f"  = {gx1-gx0:.2f} x {gy1-gy0:.2f}")
    K = [gx0 - C["FDM"], gx1 + C["FDM"], gy0 - C["FDM"], gy1 + C["FDM"]]
    print(f"+ FDM {C['FDM']}/side ->   X[{K[0]:.2f},{K[1]:.2f}] Y[{K[2]:.2f},{K[3]:.2f}]"
          f"  = {K[1]-K[0]:.2f} x {K[3]-K[2]:.2f}")
    C["KEEPOUT"] = [float(v) for v in K]
    json.dump(C, io.open(os.path.join(OUT, "cartridge_constants.json"), "w",
                         encoding="utf-8"), indent=1)


if len(sys.argv) > 1 and sys.argv[1] == "keepout":
    keepout()
