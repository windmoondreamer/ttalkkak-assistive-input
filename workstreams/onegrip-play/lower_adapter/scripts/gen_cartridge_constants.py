"""OPTION C 최종 설계 상수 생성 + FS 상수 블록 출력 (CAD WRITE 없음)."""
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
UP = np.array(C["UP_LOCAL"])
HAND = np.array(C["HAND_REF"])
PIV = np.array(C["PIVOT"])


def wz(p):
    """월드 수직 높이."""
    return float(np.asarray(p) @ UP)


def main():
    N = sg.load(neutral=True)
    BODY, TAIL = C["BODY"], C["TAIL"]
    CX = 0.5 * (BODY[0] + BODY[1])
    CY = 0.5 * (BODY[2] + BODY[3])
    BASE_BOT = C["BASE_BOT"]
    BASE_TOP = C["BASE_TOP"]

    # ---------- 캐리어 ----------
    POCK_CLR = 0.30
    POCK_D = 3.0                       # 포켓 깊이 (Base 측면 포착량)
    POCK_X = (BODY[1] - BODY[0]) + 2 * POCK_CLR
    POCK_Y = (BODY[3] - BODY[2]) + 2 * POCK_CLR
    TAIL_W = (TAIL[1] - TAIL[0]) + 2 * POCK_CLR
    CAR_TOP = BASE_BOT + POCK_D        # 캐리어 상면 (립에 닿는 면)
    CAR_FLOOR_T = 6.0                  # 포켓 바닥 아래 살
    CAR_T = POCK_D + CAR_FLOOR_T       # 전체 두께
    CAR_BOT = BASE_BOT - CAR_FLOOR_T

    FIT = 0.20                         # 캐리어 외곽 <-> 하우징 내경
    LIP_CLR = 1.00                     # 립 내경 <-> Base 옆면
    LIP_IN = max(POCK_X, POCK_Y) + 2 * (LIP_CLR - POCK_CLR) + 2 * POCK_CLR
    LIP_IN = (BODY[1] - BODY[0]) + 2 * LIP_CLR          # 102.0
    LIP_W = 8.0                        # 립 반경방향 폭 (M3 인서트 수용)
    HOUSE_IN = LIP_IN + 2 * LIP_W      # 118.0
    CAR_OUT = HOUSE_IN - 2 * FIT       # 117.6
    WALL_T = 9.0
    HOUSE_OUT = HOUSE_IN + 2 * WALL_T  # 136.0
    LIP_T = 4.0                        # 립 두께(Z)

    SCR_R = 0.5 * (LIP_IN + HOUSE_IN) / 2 + LIP_IN / 4   # placeholder
    SCR_R = 0.25 * LIP_IN + 0.25 * HOUSE_IN              # = (LIP_IN/2 + HOUSE_IN/2)/2
    INSERT_D, INSERT_L = 4.0, 8.0

    # ---------- 덱 ----------
    DECK_Z, DECK_T = C["DECK_Z"], C["DECK_T"]
    OP = C["OPENING"]
    OP_CX, OP_CY = 0.5 * (OP[0] + OP[1]), 0.5 * (OP[2] + OP[3])
    OP_W, OP_H = OP[1] - OP[0], OP[3] - OP[2]

    # ---------- 지면 ----------
    USB_CLR = 6.0
    low_stock = min(wz(N[k].reshape(-1, 3).T.T) if False else
                    float((N[k].reshape(-1, 3) @ UP).min())
                    for k in N if k.startswith(("micro", "atmega", "MICRO_", "Base <")))
    GROUND = low_stock - USB_CLR

    print("=" * 74)
    print("OPTION C 설계 상수 (그립 Part Studio 좌표, mm)")
    print("=" * 74)
    print(f"  중심          CX={CX:.5f}  CY={CY:.5f}")
    print(f"  Base 본체     {BODY[1]-BODY[0]:.3f} x {BODY[3]-BODY[2]:.3f}   밑면 Z={BASE_BOT:.4f}")
    print(f"  Base 꼬리     {TAIL[1]-TAIL[0]:.3f} 폭, Y {TAIL[2]:.3f} .. {C['JUNC_Y']:.3f}")
    print(f"\n  [CARRIER]")
    print(f"   포켓        {POCK_X:.3f} x {POCK_Y:.3f}  깊이 {POCK_D:.1f}  (여유 {POCK_CLR}/side)")
    print(f"   꼬리 슬롯    폭 {TAIL_W:.3f}  (-Y 로 관통)")
    print(f"   외곽        {CAR_OUT:.3f} x {CAR_OUT:.3f}   두께 {CAR_T:.1f}")
    print(f"   상면 Z      {CAR_TOP:.4f}   밑면 Z {CAR_BOT:.4f}")
    print(f"   포켓 바닥 Z  {BASE_BOT:.4f}")
    print(f"\n  [HOUSING]")
    print(f"   덱 상면 Z   {DECK_Z:.4f}  (착좌면 +{C['DECK_REC']:.1f})  두께 {DECK_T:.1f}")
    print(f"   덱 개구     {OP_W:.3f} x {OP_H:.3f}  중심 ({OP_CX:.3f}, {OP_CY:.3f})")
    print(f"   내경 프리즘  {HOUSE_IN:.3f}    벽 {WALL_T:.1f}   외곽 {HOUSE_OUT:.3f}")
    print(f"   립 내경     {LIP_IN:.3f}  폭 {LIP_W:.1f}  두께 {LIP_T:.1f}  밑면 Z {CAR_TOP:.4f}")
    print(f"   Base 통과 여유 {(LIP_IN-(BODY[1]-BODY[0]))/2:.3f} mm/side")
    print(f"   캐리어 fit   {FIT:.2f} mm/side")
    print(f"   나사 반경    {SCR_R:.3f}  (립 밴드 {LIP_IN/2:.1f}~{HOUSE_IN/2:.1f})")
    print(f"   인서트      M3 열간, ⌀{INSERT_D:.1f} x {INSERT_L:.1f}")
    print(f"\n  [지면]")
    print(f"   스톡 최저 (월드수직)  {low_stock:.4f}")
    print(f"   USB 여유             {USB_CLR:.1f}")
    print(f"   지면 평면 (월드수직)  {GROUND:.4f}")

    # ---------- 나사 스택업 ----------
    TAP_TOP = C["TAP_TOP_Z"]
    TAP_BOT = C["TAP_BOTTOM_Z"]
    dCB = 3.5
    # 헤드 지지면 Z = 캐리어 밑면 + dCB
    Zhb = CAR_BOT + dCB
    print(f"\n  [C1/C2 나사]")
    print(f"   캐리어 카운터보어 깊이 {dCB:.1f}  헤드 지지면 Z = {Zhb:.4f}")
    print(f"   헤드 위 재료          {BASE_BOT - Zhb:.3f} mm (포켓 바닥까지)")
    for L in (16, 20, 22, 25, 30):
        tip = Zhb + L
        E = tip - TAP_TOP
        clr = TAP_BOT - tip
        ok = "OK " if (E >= 5.999 and clr >= 0.5) else "   "
        print(f"   M3x{L:<3d}  물림 {E:6.3f}   블라인드 여유 {clr:6.3f}  {ok}")
    Lmin = 6.0 + TAP_TOP - Zhb
    Lmax = TAP_BOT - Zhb
    print(f"   -> 필요 길이 범위 {Lmin:.3f} .. {Lmax:.3f} mm")

    D = dict(C)
    D.update({
        "CX": CX, "CY": CY,
        "POCK_X": POCK_X, "POCK_Y": POCK_Y, "POCK_D": POCK_D, "POCK_CLR": POCK_CLR,
        "TAIL_W": TAIL_W, "CAR_TOP": CAR_TOP, "CAR_T": CAR_T, "CAR_BOT": CAR_BOT,
        "CAR_FLOOR_T": CAR_FLOOR_T,
        "CAR_OUT": CAR_OUT, "FIT": FIT,
        "LIP_IN": LIP_IN, "LIP_W": LIP_W, "LIP_T": LIP_T,
        "HOUSE_IN": HOUSE_IN, "WALL_T": WALL_T, "HOUSE_OUT": HOUSE_OUT,
        "SCR_R": SCR_R, "INSERT_D": INSERT_D, "INSERT_L": INSERT_L,
        "OP_CX": OP_CX, "OP_CY": OP_CY, "OP_W": OP_W, "OP_H": OP_H,
        "USB_CLR": USB_CLR, "GROUND": GROUND, "LOW_STOCK": low_stock,
        "CB_D": dCB, "SCREW_LMIN": Lmin, "SCREW_LMAX": Lmax,
    })
    json.dump(D, io.open(os.path.join(OUT, "cartridge_constants.json"), "w",
                         encoding="utf-8"), indent=1)
    print("\n저장: cartridge_constants.json")


if __name__ == "__main__":
    main()
