"""컨포멀 하우징 최종 상수 생성 (CAD WRITE 없음).

내부(캐비티)는 포락선 밴드, 외피는 그 위로 **단조 테이퍼** 로 만든다.
   outer(z) = max_{z' >= z} interior(z')  + 2*wall
단조로 만들어야 (a) 벽 두께가 균일하고 (b) 인쇄 가능하고 (c) 허리가 안 생긴다.

바닥은 두 평면으로 자른다.
   P1 지면 (월드 수평)          — 평평한 접지면
   P2 무릎면 (+Y 쪽으로 상승)    — 스톡이 없는 +Y 하부 쐐기를 잘라낸다
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
C = json.load(io.open(os.path.join(OUT, "cartridge_constants.json"), encoding="utf-8"))
B = json.load(io.open(os.path.join(OUT, "conformal_bands.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
HAND = np.array(C["HAND_REF"])
PIV = np.array(C["PIVOT"])
DECK_Z = C["DECK_Z"]

WALL = 5.0            # 일반 외피
WALL_STRUCT = 6.0     # 하중 경로 (캐리어 마운트 / 접지)
BOTTOM_WALL = 4.0     # 꼬리 바닥
FLOOR_CLR = 5.0       # 캐리어 상면 ~ Base 밑면 사이 (포켓 3 + 살)
KNEE_ANGLE = 34.0     # 무릎면이 수평과 이루는 각
KNEE_Y = 18.0         # 접지 평탄부가 끝나는 grip Y


def uhat():
    """월드 수평 중 grip +Y 를 향하는 단위벡터 (grip 좌표)."""
    y = np.array([0.0, 1.0, 0.0])
    u = y - (y @ UP) * UP
    return u / np.linalg.norm(u)


def wz(p):
    return float(np.asarray(p) @ UP)


def main():
    N = sg.load(neutral=True)
    main_b = B["main"]
    tail_b = B["tail"]

    # ---------- 1. 내부(캐비티) 밴드 ----------
    # 밴드 목록을 그대로 쓰되, 인접 밴드 폭 차이가 작으면 병합해 단순화한다.
    cav = []
    for m in main_b:
        cav.append(dict(m))
    # 병합
    merged = []
    for m in cav:
        if merged and (abs(m["x1"] - merged[-1]["x1"]) < 3 and
                       abs(m["x0"] - merged[-1]["x0"]) < 3 and
                       abs(m["y1"] - merged[-1]["y1"]) < 4 and
                       abs(m["y0"] - merged[-1]["y0"]) < 4):
            p = merged[-1]
            p["z1"] = m["z1"]
            p["x0"] = min(p["x0"], m["x0"])
            p["x1"] = max(p["x1"], m["x1"])
            p["y0"] = min(p["y0"], m["y0"])
            p["y1"] = max(p["y1"], m["y1"])
        else:
            merged.append(dict(m))
    cav = merged

    print("=" * 92)
    print("CAVITY (내부) 밴드")
    print("=" * 92)
    for m in cav:
        print(f"  Z {m['z0']:8.2f}..{m['z1']:8.2f}  X {m['x0']:6.1f}..{m['x1']:6.1f}  "
              f"Y {m['y0']:6.1f}..{m['y1']:6.1f}   {m['x1']-m['x0']:5.1f} x "
              f"{m['y1']-m['y0']:5.1f}")

    # ---------- 2. 외피 = 위쪽 최대의 단조 포락 + 벽 ----------
    outer = []
    for i, m in enumerate(cav):
        above = cav[i:]
        x0 = min(a["x0"] for a in above) - WALL
        x1 = max(a["x1"] for a in above) + WALL
        y0 = min(a["y0"] for a in above) - WALL
        y1 = max(a["y1"] for a in above) + WALL
        outer.append({"z0": m["z0"], "z1": m["z1"],
                      "x0": x0, "x1": x1, "y0": y0, "y1": y1})
    # 외피도 병합
    om = []
    for o in outer:
        if om and all(abs(o[k] - om[-1][k]) < 1e-6 for k in ("x0", "x1", "y0", "y1")):
            om[-1]["z1"] = o["z1"]
        else:
            om.append(dict(o))
    outer = om

    print("\n" + "=" * 92)
    print(f"OUTER (외피) 밴드   wall = {WALL}")
    print("=" * 92)
    for o in outer:
        print(f"  Z {o['z0']:8.2f}..{o['z1']:8.2f}  X {o['x0']:6.1f}..{o['x1']:6.1f}  "
              f"Y {o['y0']:6.1f}..{o['y1']:6.1f}   {o['x1']-o['x0']:5.1f} x "
              f"{o['y1']-o['y0']:5.1f}")

    # ---------- 3. 꼬리 ----------
    tx0 = min(t["x0"] for t in tail_b)
    tx1 = max(t["x1"] for t in tail_b)
    ty0 = min(t["y0"] for t in tail_b)
    tz0 = min(t["z0"] for t in tail_b)
    tz1 = max(t["z1"] for t in tail_b)
    TAIL = {"x0": tx0, "x1": tx1, "y0": ty0, "z0": tz0, "z1": tz1}
    TAIL_OUT = {"x0": tx0 - WALL, "x1": tx1 + WALL, "y0": ty0 - WALL,
                "z0": tz0 - BOTTOM_WALL, "z1": tz1}
    print(f"\nTAIL 내부  X {tx0:.1f}..{tx1:.1f}  Y {ty0:.1f}..  Z {tz0:.1f}..{tz1:.1f}"
          f"   {tx1-tx0:.1f} 폭")
    print(f"TAIL 외피  X {TAIL_OUT['x0']:.1f}..{TAIL_OUT['x1']:.1f}  "
          f"Y {TAIL_OUT['y0']:.1f}..   {TAIL_OUT['x1']-TAIL_OUT['x0']:.1f} 폭")

    # ---------- 4. 바닥 평면 ----------
    stock_low = B["stock_low_world"]
    GROUND = stock_low - BOTTOM_WALL
    u = uhat()
    th = np.radians(KNEE_ANGLE)
    n_knee = -np.sin(th) * u + np.cos(th) * UP           # 재료 쪽 법선
    knee_pt = None
    # 무릎선: grip Y = KNEE_Y, 지면 위
    # 그 점의 grip 좌표를 구한다 (Z 는 지면 평면 위 조건에서)
    zk = (GROUND - UP[1] * KNEE_Y) / UP[2]
    knee_pt = np.array([0.0, KNEE_Y, zk])
    d_knee = float(knee_pt @ n_knee)
    d_ground = GROUND

    print(f"\n지면 평면    n = UP_LOCAL,  d = {d_ground:.4f}  (스톡 최저 {stock_low:.4f}, "
          f"바닥살 {BOTTOM_WALL})")
    print(f"무릎 평면    각 {KNEE_ANGLE} deg,  grip Y = {KNEE_Y} 에서 지면과 만남")
    print(f"             n = ({n_knee[0]:.6f}, {n_knee[1]:.6f}, {n_knee[2]:.6f})  "
          f"d = {d_knee:.4f}")
    print(f"             무릎점 grip = ({knee_pt[0]:.3f}, {knee_pt[1]:.3f}, {knee_pt[2]:.3f})")

    # ---------- 5. 캐리어 ----------
    BASE_BOT = C["BASE_BOT"]
    CAR_TOP = BASE_BOT + C["POCK_D"]                 # 포켓 3.0
    CAR_BOT = BASE_BOT - FLOOR_CLR - 1.0             # 살 6.0
    CAR_BOT = BASE_BOT - 6.0
    cav_bot = cav[0]
    CAR = {"x0": cav_bot["x0"], "x1": cav_bot["x1"],
           "y0": cav_bot["y0"], "y1": cav_bot["y1"],
           "top": CAR_TOP, "bot": CAR_BOT}
    print(f"\nCARRIER  X {CAR['x0']:.1f}..{CAR['x1']:.1f}  Y {CAR['y0']:.1f}..{CAR['y1']:.1f}"
          f"  Z {CAR_BOT:.4f}..{CAR_TOP:.4f}   {CAR['x1']-CAR['x0']:.1f} x "
          f"{CAR['y1']-CAR['y0']:.1f} x {CAR_TOP-CAR_BOT:.1f}")

    # ---------- 6. 예상 치수 ----------
    ox0 = min(o["x0"] for o in outer)
    ox1 = max(o["x1"] for o in outer)
    oy0 = min(o["y0"] for o in outer)
    oy1 = max(o["y1"] for o in outer)
    py0 = min(oy0, TAIL_OUT["y0"])
    deck_w = wz([0, C["CY"], DECK_Z])
    print("\n" + "=" * 92)
    print("예상 외형")
    print("=" * 92)
    print(f"  본체 plan       X {ox0:.1f}..{ox1:.1f}  Y {oy0:.1f}..{oy1:.1f}"
          f"   {ox1-ox0:.1f} x {oy1-oy0:.1f}")
    print(f"  꼬리 포함 plan   X {ox0:.1f}..{ox1:.1f}  Y {py0:.1f}..{oy1:.1f}"
          f"   {ox1-ox0:.1f} x {oy1-py0:.1f}")
    print(f"  (A) 경사면 -> HAND_REF          {HAND[2]-DECK_Z:8.4f} mm")
    print(f"  (H) 스톡 피벗 -> 경사면          {DECK_Z-PIV[2]:8.4f} mm")
    # 최고점 = 덱 평면의 +Y 끝
    top_hi = max(wz([0, oy1, DECK_Z]), wz([0, py0, DECK_Z]))
    print(f"  (F) 최대 높이 (지면 -> 덱 +Y 끝)  {top_hi-GROUND:8.4f} mm")
    print(f"      (지면 -> 덱 중심)           {deck_w-GROUND:8.4f} mm")
    print(f"  (B) 지면 -> HAND_REF            {wz(HAND)-GROUND:8.4f} mm")
    print(f"  (D) 스톡 돌출 (지면 아래)         {max(0.0, GROUND-stock_low):8.4f} mm")
    print(f"  (C) 스톡 최저 -> 하우징 바닥      {stock_low-GROUND:8.4f} mm")

    D = {
        "WALL": WALL, "WALL_STRUCT": WALL_STRUCT, "BOTTOM_WALL": BOTTOM_WALL,
        "cavity": cav, "outer": outer, "tail": TAIL, "tail_out": TAIL_OUT,
        "GROUND": GROUND, "d_ground": d_ground,
        "KNEE_ANGLE": KNEE_ANGLE, "KNEE_Y": KNEE_Y,
        "n_knee": n_knee.tolist(), "d_knee": d_knee, "knee_pt": knee_pt.tolist(),
        "carrier": CAR, "DECK_Z": DECK_Z, "stock_low_world": stock_low,
        "plan": [ox0, ox1, py0, oy1],
    }
    json.dump(D, io.open(os.path.join(OUT, "conformal_constants.json"), "w",
                         encoding="utf-8"), indent=1)
    print("\n저장: conformal_constants.json")


if __name__ == "__main__":
    main()
