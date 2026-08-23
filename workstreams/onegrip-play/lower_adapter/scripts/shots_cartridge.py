"""OPTION C 조립 측면/정면 합성도 (월드 프레임)."""
import io
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
from matplotlib.collections import PolyCollection        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import stock_geom as sg                                  # noqa: E402
from verify_cartridge import C, fetch                    # noqa: E402

UP = np.array(C["UP_LOCAL"])
HAND = np.array(C["HAND_REF"])
PIV = np.array(C["PIVOT"])


def frame(view):
    """월드 정사영 축 (u=수평, v=수직=UP)."""
    v = UP
    if view == "side":
        u = np.cross(np.array([1.0, 0, 0]), v)
        u = np.array([0.0, v[2], -v[1]])
    else:
        u = np.array([1.0, 0.0, 0.0])
    u = u / np.linalg.norm(u)
    return u, v


def draw(ax, P, u, v, color, alpha, z=1, lw=0.0):
    T = np.stack([P.reshape(-1, 3) @ u, P.reshape(-1, 3) @ v], 1).reshape(-1, 3, 2)
    ax.add_collection(PolyCollection(T, facecolors=color, edgecolors="none",
                                     alpha=alpha, zorder=z, linewidths=lw))


def main():
    M = fetch()
    CAR = M["JHD"]
    HOUSE = [M[k] for k in M if k != "JHD"][0]
    N = sg.load(neutral=True)
    FIXED = ("Base <1>", "Roll_holder <1>", "Roll_holder_2 <1>", "Spacer <1>")
    MOVING = ("Roll <1>", "Pitch <1>", "Spring_holder <1>")
    GRIP = ("Joystick_1 <1>", "Joystick_2 <1>", "Backplate <1>",
            "Small_joystick_attachment <1>")
    ELEC = [k for k in N if k.startswith(("micro", "atmega", "MICRO_"))]

    fig, axes = plt.subplots(1, 2, figsize=(17, 10))
    gz = float((HOUSE.reshape(-1, 3) @ UP).min())
    deck_w = float(np.array([C["CX"], C["CY"], C["DECK_Z"]]) @ UP)
    hand_w = float(HAND @ UP)

    for ax, view in zip(axes, ("side", "front")):
        u, v = frame(view)
        for k in GRIP:
            draw(ax, N[k], u, v, "#9aa7b4", 0.85, 1)
        for k in MOVING:
            draw(ax, N[k], u, v, "#2e9e5b", 0.95, 3)
        for k in FIXED:
            draw(ax, N[k], u, v, "#7b3fa0", 0.95, 2)
        for k in ELEC:
            draw(ax, N[k], u, v, "#d94f2b", 1.0, 4)
        draw(ax, CAR, u, v, "#2b6cb0", 0.95, 5)
        draw(ax, HOUSE, u, v, "#c9a227", 0.55, 0)

        # 덱 평면 / 지면 / HAND_REF
        ax.axhline(gz, color="k", lw=1.4, zorder=6)
        ax.text(-95, gz - 5, "지면 (20 deg)", fontsize=9)
        p0 = np.array([C["CX"], C["CY"], C["DECK_Z"]])
        d = np.array([1.0, 0.0, 0.0]) if view == "front" else np.array([0.0, 1.0, 0.0])
        pa, pb = p0 - d * 85, p0 + d * 85
        ax.plot([pa @ u, pb @ u], [pa @ v, pb @ v], "k--", lw=1.5, zorder=7)
        ax.plot([HAND @ u], [hand_w], "k*", ms=16, zorder=8)
        ax.annotate("", xy=(HAND @ u, hand_w), xytext=(HAND @ u, gz),
                    arrowprops=dict(arrowstyle="<->", lw=1.2))
        ax.text(HAND @ u + 3, (hand_w + gz) / 2,
                f"{hand_w - gz:.1f} mm\n(지면 -> HAND_REF)", fontsize=9)
        ax.annotate("", xy=(HAND @ u - 22, hand_w), xytext=(HAND @ u - 22, deck_w),
                    arrowprops=dict(arrowstyle="<->", lw=1.2, color="#b03030"))
        ax.text(HAND @ u - 62, (hand_w + deck_w) / 2,
                f"{HAND[2] - C['DECK_Z']:.2f} mm\n(덱 -> HAND_REF)",
                fontsize=9, color="#b03030")

        ax.set_aspect("equal")
        ax.set_xlim(-110, 110)
        ax.set_ylim(gz - 22, hand_w + 78)
        ax.grid(alpha=0.25)
        ax.set_title("측면 (X 에서 본 YZ)" if view == "side" else "정면 (Y 에서 본 XZ)")
        ax.set_ylabel("world vertical [mm]")

    from matplotlib.patches import Patch
    axes[0].legend(handles=[
        Patch(fc="#9aa7b4", label="OneGrip (frozen)"),
        Patch(fc="#2e9e5b", label="STOCK moving (Roll/Pitch/Spring_holder)"),
        Patch(fc="#7b3fa0", label="STOCK fixed (Base/Roll_holder/Spacer)"),
        Patch(fc="#d94f2b", label="STOCK electronics (Pro Micro / USB)"),
        Patch(fc="#2b6cb0", label="NEW  CARRIER_PLATE"),
        Patch(fc="#c9a227", alpha=0.55, label="NEW  DECK_HOUSING")],
        loc="upper left", fontsize=9)
    fig.suptitle("OneGrip Play — OPTION C 스톡 짐벌 카트리지 (20 deg deck, "
                 "GRIP_AXIS perp DECK = 90.000000 deg)", fontsize=13)
    fig.tight_layout()
    out = os.path.join(sg.OUT, "shot_cartridge.png")
    fig.savefig(out, dpi=115)
    print("saved", out)


if __name__ == "__main__":
    main()
