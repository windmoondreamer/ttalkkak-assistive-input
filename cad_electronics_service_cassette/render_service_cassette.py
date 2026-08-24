"""Offline preview of the serviceable dual-board cassette."""

from __future__ import annotations

import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import FancyBboxPatch
import numpy as np


HERE = Path(__file__).resolve().parent
OUT = HERE / "export"
PREVIEW = HERE / "service_cassette_preview.png"

matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False


def read_stl(path):
    with open(path, "rb") as f:
        first = f.read(5)
        f.seek(0)
        if first == b"solid":
            vertices = []
            for line in f:
                parts = line.split()
                if parts and parts[0] == b"vertex":
                    vertices.append([float(v) for v in parts[1:4]])
            return np.asarray(vertices).reshape(-1, 3, 3)
        f.seek(80)
        count = struct.unpack("<I", f.read(4))[0]
        triangles = np.empty((count, 3, 3))
        for i in range(count):
            data = struct.unpack("<12fH", f.read(50))
            triangles[i] = np.asarray(data[3:12]).reshape(3, 3)
        return triangles


def frame(view):
    w = np.asarray(view, dtype=float)
    w /= np.linalg.norm(w)
    up = np.array([0.0, 0.0, 1.0])
    if abs(w @ up) > 0.95:
        up = np.array([0.0, 1.0, 0.0])
    u = np.cross(up, w)
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    return u, v, w


def add_mesh(ax, triangles, view, color, alpha=1.0):
    u, v, w = frame(view)
    normals = np.cross(triangles[:, 1] - triangles[:, 0],
                       triangles[:, 2] - triangles[:, 0])
    lengths = np.maximum(np.linalg.norm(normals, axis=1), 1e-12)
    normals = normals / lengths[:, None]
    keep = (normals @ w) < 0
    tris = triangles[keep]
    normals = normals[keep]
    depth = tris.mean(axis=1) @ w
    order = np.argsort(-depth)
    tris, normals = tris[order], normals[order]
    light = np.array([-0.3, -0.4, 0.86])
    light /= np.linalg.norm(light)
    shade = np.clip(0.42 + 0.58 * np.abs(normals @ light), 0, 1)
    base = np.asarray(matplotlib.colors.to_rgb(color))
    colors = np.clip(base[None, :] * shade[:, None], 0, 1)
    points = tris.reshape(-1, 3)
    poly = np.stack([points @ u, points @ v], axis=1).reshape(-1, 3, 2)
    ax.add_collection(PolyCollection(poly, facecolors=colors,
                                     edgecolors="none", alpha=alpha))


def setup_limits(ax, meshes, view, margin=4):
    u, v, _ = frame(view)
    points = np.vstack([m.reshape(-1, 3) for m in meshes])
    xs, ys = points @ u, points @ v
    ax.set_xlim(xs.min() - margin, xs.max() + margin)
    ax.set_ylim(ys.min() - margin, ys.max() + margin)
    ax.set_aspect("equal")
    ax.axis("off")


def main():
    body = read_stl(OUT / "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_BODY_V4.stl")
    lid = read_stl(OUT / "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_LID_V4.stl")
    rp = read_stl(OUT / "RP2040_ZERO_USER_MEASURED_SURROGATE.stl")
    power = read_stl(OUT / "POWER_BOARD_PCB_SURROGATE.stl")

    # Explode the lid to the right and slightly upward in the isometric panel.
    lid_exploded = lid + np.array([42.0, 3.0, 5.0])

    fig = plt.figure(figsize=(14, 8), facecolor="#f5f6f8")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0], wspace=0.05)
    iso = fig.add_subplot(gs[0, 0])
    top = fig.add_subplot(gs[0, 1])

    view_iso = np.array([-0.9, -1.2, 0.78])
    for mesh, color, alpha in (
        (body, "#d8dde5", 1.0),
        (rp, "#32a8a0", 1.0),
        (power, "#e6a64c", 1.0),
        (lid_exploded, "#bcc5d1", 0.95),
    ):
        add_mesh(iso, mesh, view_iso, color, alpha)
    setup_limits(iso, [body, rp, power, lid_exploded], view_iso, 5)
    iso.set_title("단층 서비스 카세트 — 분해 조립도", fontsize=18,
                  fontweight="bold", loc="left", pad=14)

    view_top = np.array([0.0, 0.0, 1.0])
    for mesh, color in ((body, "#d8dde5"), (rp, "#32a8a0"), (power, "#e6a64c")):
        add_mesh(top, mesh, view_top, color)
    setup_limits(top, [body], view_top, 3)
    top.set_title("위에서 각각 삽입", fontsize=17, fontweight="bold", pad=14)

    # Caption blocks are intentionally plain and workshop-like, not AI-rendered.
    fig.text(0.055, 0.075,
             "RP2040-Zero\n삽입 방향 여유 +1.20 mm",
             fontsize=12, color="#157b76", linespacing=1.4,
             bbox=dict(boxstyle="round,pad=0.55", fc="white", ec="#32a8a0", lw=1.4))
    fig.text(0.235, 0.075,
             "전원보드 90° 회전\n외벽 단자 개구 삭제",
             fontsize=12, color="#a66512", linespacing=1.4,
             bbox=dict(boxstyle="round,pad=0.55", fc="white", ec="#e6a64c", lw=1.4))
    fig.text(0.45, 0.075,
             "4× M3 수직 체결\n보드 아래 숨은 나사 없음",
             fontsize=12, color="#354052", linespacing=1.4,
             bbox=dict(boxstyle="round,pad=0.55", fc="white", ec="#8c98a8", lw=1.4))
    fig.text(0.73, 0.075,
             "외형 36 × 45 × 14 mm\n본체·뚜껑 모두 서포트 없이 출력",
             fontsize=12, color="#354052", linespacing=1.4,
             bbox=dict(boxstyle="round,pad=0.55", fc="white", ec="#8c98a8", lw=1.4))

    fig.savefig(PREVIEW, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(PREVIEW)


if __name__ == "__main__":
    main()
