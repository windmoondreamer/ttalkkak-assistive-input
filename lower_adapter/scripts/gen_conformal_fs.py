"""컨포멀 하우징 FeatureScript 생성 (템플릿 + 실측 상수).

lower_adapter/cad/OneGrip_Conformal.fs.tmpl 의 //GENERATED 를 치환한다.
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
CAD = os.path.join(ROOT, "lower_adapter", "cad")
C = json.load(io.open(os.path.join(OUT, "cartridge_constants.json"), encoding="utf-8"))
B = json.load(io.open(os.path.join(OUT, "conformal_bands.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
HAND = np.array(C["HAND_REF"])
PIV = np.array(C["PIVOT"])

DECK_Z = C["DECK_Z"]
BASE_BOT = C["BASE_BOT"]
CAR_TOP = BASE_BOT + 3.0                 # 포켓 3.0
CAR_BOT = BASE_BOT - 6.0                 # 살 6.0
WALL = 5.0
FLANGE = 7.0                             # 캐리어 플랜지 (착좌 폭)
FIT = 0.30
SKIRT_T = 5.0
GROUND_CLR = 6.0                         # 스톡 최저 ~ 지면 (USB 플러그 여유, provisional)
KNEE_ANGLE = 34.0
KNEE_Y = 18.0
INSERT_D, INSERT_L = 4.0, 8.0
M3_CLR, M3_CB, CB_D = 3.4, 6.6, 3.5
C_SLOT_L = 11.4
USB_W = 16.0                             # -Y 포트 폭


def uhat():
    y = np.array([0.0, 1.0, 0.0])
    u = y - (y @ UP) * UP
    return u / np.linalg.norm(u)


def fs_arr(rows, prec=3):
    return "[" + ", ".join("[" + ", ".join(f"{v:.{prec}f}" for v in r) + "]"
                           for r in rows) + "]"


def main():
    cav_raw = B["main"]
    # ---- 캐비티 밴드 병합 ----
    cav = []
    for m in cav_raw:
        if cav and (abs(m["x1"] - cav[-1]["x1"]) < 3 and abs(m["x0"] - cav[-1]["x0"]) < 3
                    and abs(m["y1"] - cav[-1]["y1"]) < 4
                    and abs(m["y0"] - cav[-1]["y0"]) < 4):
            p = cav[-1]
            p["z1"] = m["z1"]
            p["x0"] = min(p["x0"], m["x0"]); p["x1"] = max(p["x1"], m["x1"])
            p["y0"] = min(p["y0"], m["y0"]); p["y1"] = max(p["y1"], m["y1"])
        else:
            cav.append(dict(m))
    cav[0]["z0"] = CAR_BOT                     # 캐리어까지 공동을 내린다
    # 최상단 두 밴드를 합친다. 덱 개구부를 테이퍼로 만들면 마지막 절삭이
    # BOOLEAN_NON_MANIFOLD_RESULT 로 실패한다 -> 곧은 개구부로 단순화.
    # (개구부가 82x77 -> 92x89 로 커지지만 thin-deck 안의 90.8x87.5 와 같은 급이다)
    top = cav.pop()
    cav[-1]["z1"] = DECK_Z
    cav[-1]["x0"] = min(cav[-1]["x0"], top["x0"])
    cav[-1]["x1"] = max(cav[-1]["x1"], top["x1"])
    cav[-1]["y0"] = min(cav[-1]["y0"], top["y0"])
    cav[-1]["y1"] = max(cav[-1]["y1"], top["y1"])

    # ---- 외피 = 위쪽 최대의 단조 포락 + 벽 ----
    outer = []
    # 밴드 i-1 까지 포함해야 한다.
    # 위쪽 밴드만 보면, 아래 밴드가 -Y 로 더 튀어나온 구간에서 외피 면과 공동 면이
    # Z 경계에서 정확히 동일 평면이 되어 **두께 0 의 칼날 모서리**가 생기고
    # opBoolean 이 BOOLEAN_NON_MANIFOLD_RESULT 로 실패한다 (실측 확인, band 2 @ Z=-126).
    for i, m in enumerate(cav):
        ab = cav[max(0, i - 1):]
        outer.append({"z0": m["z0"], "z1": m["z1"],
                      "x0": min(a["x0"] for a in ab) - WALL,
                      "x1": max(a["x1"] for a in ab) + WALL,
                      "y0": min(a["y0"] for a in ab) - WALL,
                      "y1": max(a["y1"] for a in ab) + WALL})
    om = []
    for o in outer:
        if om and all(abs(o[k] - om[-1][k]) < 1e-6 for k in ("x0", "x1", "y0", "y1")):
            om[-1]["z1"] = o["z1"]
        else:
            om.append(dict(o))
    outer = om

    # ---- 캐리어 / 스커트 ----
    cb = cav[0]
    CARRIER = [cb["x0"] - FLANGE, cb["x1"] + FLANGE,
               cb["y0"] - FLANGE, cb["y1"] + FLANGE]
    CAR_OPEN = [CARRIER[0] - FIT, CARRIER[1] + FIT,
                CARRIER[2] - FIT, CARRIER[3] + FIT]
    SKIRT = [CAR_OPEN[0] - SKIRT_T, CAR_OPEN[1] + SKIRT_T,
             CAR_OPEN[2] - SKIRT_T, CAR_OPEN[3] + SKIRT_T]

    # 외피 최하단 구간을 스커트 폭으로 넓힌다 (착좌 환형 + 접지 안정)
    outer[0] = {"z0": CAR_TOP, "z1": -137.0,
                "x0": SKIRT[0], "x1": SKIRT[1], "y0": SKIRT[2], "y1": SKIRT[3]}
    mid = {"z0": -137.0, "z1": -132.0,
           "x0": (SKIRT[0] + outer[1]["x0"]) / 2, "x1": (SKIRT[1] + outer[1]["x1"]) / 2,
           "y0": (SKIRT[2] + outer[1]["y0"]) / 2, "y1": (SKIRT[3] + outer[1]["y1"]) / 2}
    # outer[1] 은 mid 로 대체된다 (남겨두면 높이 0 밴드가 생긴다)
    outer = [outer[0], mid] + [dict(o) for o in outer[2:]]
    outer[2]["z0"] = -132.0

    # ---- 꼬리 ----
    tail = B["tail"]
    T_X0 = min(t["x0"] for t in tail)
    T_X1 = max(t["x1"] for t in tail)
    T_Y0 = min(t["y0"] for t in tail)
    # 꼬리 체인은 본체와 반드시 겹쳐야 한다. 상단 밴드에서 본체 y0 가 -25 까지
    # 올라오므로 -28 로 잡으면 Z -126..-121 에서 분리된다 (UNION 실패).
    T_Y1 = -20.0
    T_Y1_OUT = 0.0
    TAIL_CAV = [T_X0, T_X1, T_Y0, T_Y1]
    TAIL_CAV_Z = [CAR_BOT, max(t["z1"] for t in tail)]
    TAIL_OUT = [T_X0 - WALL, T_X1 + WALL, T_Y0 - WALL, T_Y1_OUT]
    TAIL_OUT_Z = [CAR_TOP, TAIL_CAV_Z[1] + WALL]
    TAIL_CAR_OPEN = [T_X0 - FIT - 2, T_X1 + FIT + 2, T_Y0 - FIT - 2, T_Y1]
    TAIL_SKIRT = [TAIL_CAR_OPEN[0] - SKIRT_T, TAIL_CAR_OPEN[1] + SKIRT_T,
                  TAIL_CAR_OPEN[2] - SKIRT_T, T_Y1_OUT]

    # ---- 바닥 평면 ----
    stock_low = B["stock_low_world"]
    GROUND = stock_low - GROUND_CLR
    u = uhat()
    th = np.radians(KNEE_ANGLE)
    n_knee = -np.sin(th) * u + np.cos(th) * UP
    zk = (GROUND - UP[1] * KNEE_Y) / UP[2]
    d_knee = float(np.array([0.0, KNEE_Y, zk]) @ n_knee)
    # 절단 도구가 확실히 아래에서 시작하도록
    ymin = min(SKIRT[2], TAIL_SKIRT[2])
    ymax = SKIRT[3]
    GROUND_ZMIN = min((GROUND - UP[1] * y) / UP[2] for y in (ymin, ymax)) - 5.0

    # ---- 나사 10개 (환형 착좌면) ----
    ccx = (cb["x0"] + cb["x1"]) / 2
    ccy = (cb["y0"] + cb["y1"]) / 2
    rx = (cb["x1"] + CARRIER[1]) / 2 - ccx
    ry = (cb["y1"] + CARRIER[3]) / 2 - ccy
    SCREWS = [(ccx + rx, ccy + 40), (ccx - rx, ccy + 40),
              (ccx + rx, ccy), (ccx - rx, ccy),
              (ccx + rx, ccy - 40), (ccx - rx, ccy - 40),
              (ccx + 28, ccy + ry), (ccx - 28, ccy + ry),
              (ccx + 28, ccy - ry), (ccx - 28, ccy - ry)]

    # ---- USB 포트 ----
    ez = json.load(io.open(os.path.join(OUT, "wiring_envelope.json"), encoding="utf-8"))
    usb_lo, usb_hi = ez["mcu_usb_bbox"]
    USB = {"cx": 0.354, "w": USB_W, "z0": usb_lo[2] - 3.0, "z1": usb_hi[2] + 3.0}

    # ---------- 출력 ----------
    L = []
    a = L.append
    a("// 스톡 실측 인터페이스 (변경 금지)")
    a(f"const CX = {C['CX']:.6f};")
    a(f"const CY = {C['CY']:.6f};")
    a(f"const BODY_W = 100.000;")
    a(f"const BODY_D = 100.000;")
    a(f"const BASE_BOT = {BASE_BOT:.6f};")
    a(f"const TAIL_CX = 0.354400;")
    a(f"const TAIL_W0 = 28.000;")
    a(f"const C_X = {C['C1'][0]:.6f};")
    a(f"const C1_Y = {C['C1'][1]:.6f};")
    a(f"const C2_Y = {C['C2'][1]:.6f};")
    a(f"const C_SLOT_L = {C_SLOT_L:.3f};")
    a("")
    a("// 구조")
    a(f"const CAR_TOP = {CAR_TOP:.6f};")
    a(f"const CAR_BOT = {CAR_BOT:.6f};")
    a(f"const SKIRT_T = {SKIRT_T:.3f};")
    a(f"const M3_CLR = {M3_CLR:.3f};")
    a(f"const M3_CB = {M3_CB:.3f};")
    a(f"const CB_D = {CB_D:.3f};")
    a(f"const INSERT_D = {INSERT_D:.3f};")
    a(f"const INSERT_L = {INSERT_L:.3f};")
    a("")
    a("// 컨포멀 공동 (Z 밴드별 실측 포락선)")
    a(f"const CAV = {fs_arr([[m['x0'], m['x1'], m['y0'], m['y1']] for m in cav])};")
    a(f"const CAV_Z = [" + ", ".join(f"{m['z0']:.4f}" for m in cav)
      + f", {cav[-1]['z1']:.4f}];")
    a("")
    a("// 외피 (위쪽 최대의 단조 포락 + 벽)")
    a(f"const OUTER = {fs_arr([[m['x0'], m['x1'], m['y0'], m['y1']] for m in outer])};")
    a(f"const OUTER_Z = [" + ", ".join(f"{m['z0']:.4f}" for m in outer)
      + f", {outer[-1]['z1']:.4f}];")
    a("")
    a("// 꼬리 (전장 / USB)")
    a(f"const TAIL_CAV = {fs_arr([TAIL_CAV])[1:-1]};")
    a(f"const TAIL_CAV_Z = [{TAIL_CAV_Z[0]:.4f}, {TAIL_CAV_Z[1]:.4f}];")
    a(f"const TAIL_OUT = {fs_arr([TAIL_OUT])[1:-1]};")
    a(f"const TAIL_OUT_Z = [{TAIL_OUT_Z[0]:.4f}, {TAIL_OUT_Z[1]:.4f}];")
    a(f"const TAIL_CAR_OPEN = {fs_arr([TAIL_CAR_OPEN])[1:-1]};")
    a(f"const TAIL_SKIRT = {fs_arr([TAIL_SKIRT])[1:-1]};")
    a("")
    a("// 캐리어 / 스커트")
    a(f"const CARRIER = {fs_arr([CARRIER])[1:-1]};")
    a(f"const CAR_OPEN = {fs_arr([CAR_OPEN])[1:-1]};")
    a(f"const SKIRT = {fs_arr([SKIRT])[1:-1]};")
    a(f"const SCREWS = {fs_arr(SCREWS)};")
    a("")
    a("// 바닥 절단 — 20도는 여기에만 존재한다")
    a(f"const N_GROUND = vector({UP[0]:.16f}, {UP[1]:.16f}, {UP[2]:.16f});")
    a(f"const D_GROUND = {GROUND:.6f};")
    a(f"const N_KNEE = vector({n_knee[0]:.16f}, {n_knee[1]:.16f}, {n_knee[2]:.16f});")
    a(f"const D_KNEE = {d_knee:.6f};")
    a(f"const GROUND_ZMIN = {GROUND_ZMIN:.4f};")
    a("")
    a("// USB / 케이블 포트")
    a(f"const USB_CX = {USB['cx']:.4f};")
    a(f"const USB_W = {USB['w']:.3f};")
    a(f"const USB_Z0 = {USB['z0']:.4f};")
    a(f"const USB_Z1 = {USB['z1']:.4f};")

    block = "\n".join(L)
    tmpl = io.open(os.path.join(CAD, "OneGrip_Conformal.fs.tmpl"),
                   encoding="utf-8").read()
    src = tmpl.replace("//GENERATED", block)
    io.open(os.path.join(CAD, "OneGrip_Conformal.fs"), "w",
            encoding="utf-8").write(src)

    # ---------- 요약 ----------
    print("=" * 92)
    print("CAVITY 밴드")
    for m in cav:
        print(f"  Z {m['z0']:9.3f}..{m['z1']:9.3f}  {m['x1']-m['x0']:6.1f} x "
              f"{m['y1']-m['y0']:6.1f}   X {m['x0']:6.1f}..{m['x1']:6.1f}  "
              f"Y {m['y0']:6.1f}..{m['y1']:6.1f}")
    print("\nOUTER 밴드")
    for m in outer:
        print(f"  Z {m['z0']:9.3f}..{m['z1']:9.3f}  {m['x1']-m['x0']:6.1f} x "
              f"{m['y1']-m['y0']:6.1f}   X {m['x0']:6.1f}..{m['x1']:6.1f}  "
              f"Y {m['y0']:6.1f}..{m['y1']:6.1f}")
    print(f"\nCARRIER  {CARRIER[1]-CARRIER[0]:.1f} x {CARRIER[3]-CARRIER[2]:.1f} x "
          f"{CAR_TOP-CAR_BOT:.1f}   Z {CAR_BOT:.4f}..{CAR_TOP:.4f}")
    print(f"SKIRT    {SKIRT[1]-SKIRT[0]:.1f} x {SKIRT[3]-SKIRT[2]:.1f}")
    print(f"TAIL     캐비티 {TAIL_CAV[1]-TAIL_CAV[0]:.1f} 폭, 외피 "
          f"{TAIL_OUT[1]-TAIL_OUT[0]:.1f} 폭, Y {TAIL_OUT[2]:.1f} 까지")
    print(f"지면     world {GROUND:.4f}  (스톡 최저 {stock_low:.4f} - {GROUND_CLR})")
    print(f"무릎     {KNEE_ANGLE} deg @ grip Y {KNEE_Y}   d={d_knee:.4f}")
    print(f"나사     {len(SCREWS)} x M3   반경 rx={rx:.2f} ry={ry:.2f}")
    px0 = min(SKIRT[0], TAIL_SKIRT[0])
    px1 = max(SKIRT[1], TAIL_SKIRT[1])
    py0 = min(SKIRT[2], TAIL_SKIRT[2], TAIL_OUT[2])
    py1 = SKIRT[3]
    print(f"\n예상 풋프린트  {px1-px0:.1f} x {py1-py0:.1f} mm")
    print(f"(A) 경사면 -> HAND_REF   {HAND[2]-DECK_Z:.4f}")
    print(f"(B) 지면 -> HAND_REF     {float(HAND @ UP) - GROUND:.4f}")
    print(f"(D) 지면 아래 스톡 돌출    {max(0.0, GROUND - stock_low):.4f}")
    print(f"(H) 스톡 피벗 -> 경사면    {DECK_Z - PIV[2]:.4f}")
    print("\n생성: lower_adapter/cad/OneGrip_Conformal.fs")

    json.dump({"cav": cav, "outer": outer, "CARRIER": CARRIER, "CAR_OPEN": CAR_OPEN,
               "SKIRT": SKIRT, "TAIL_CAV": TAIL_CAV, "TAIL_CAV_Z": TAIL_CAV_Z,
               "TAIL_OUT": TAIL_OUT, "TAIL_OUT_Z": TAIL_OUT_Z,
               "TAIL_SKIRT": TAIL_SKIRT, "TAIL_CAR_OPEN": TAIL_CAR_OPEN,
               "SCREWS": SCREWS, "GROUND": GROUND, "n_knee": n_knee.tolist(),
               "d_knee": d_knee, "CAR_TOP": CAR_TOP, "CAR_BOT": CAR_BOT,
               "USB": USB, "GROUND_CLR": GROUND_CLR, "WALL": WALL,
               "FLANGE": FLANGE, "SKIRT_T": SKIRT_T, "stock_low_world": stock_low},
              io.open(os.path.join(OUT, "conformal_constants.json"), "w",
                      encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
