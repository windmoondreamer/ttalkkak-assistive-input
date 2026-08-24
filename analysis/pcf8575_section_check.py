from pathlib import Path
import struct

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


CURRENT = Path(
    r"C:\Users\guest2\Desktop\ttalkkak-assistive-input-add-onegrip-play-cad-workspace"
    r"\workstreams\onegrip-play\exports\full_exterior_minimal_mockup\source_stl"
)
FALLBACK = Path(
    r"C:\Users\guest2\Desktop\ttalkkak-assistive-input-codex-full-workspace-checkpoint-20260823"
    r"\exports\full_exterior_minimal_mockup\source_stl"
)
SRC = CURRENT if CURRENT.exists() else FALLBACK
OUT = Path(r"C:\Users\guest2\Documents\재활기기 공모전\analysis\pcf8575_sections.png")


def load(name: str) -> np.ndarray:
    data = (SRC / name).read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attr", "<u2"),
    ])
    records = np.frombuffer(data, dtype=dtype, count=count, offset=84)
    return records["vertices"].astype(float)


def section_segments(triangles: np.ndarray, z: float, eps: float = 1e-7) -> list[np.ndarray]:
    out = []
    for tri in triangles:
        points = []
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            da, db = a[2] - z, b[2] - z
            if abs(da) < eps and abs(db) < eps:
                points.extend([a[:2], b[:2]])
            elif da * db <= 0 and abs(da - db) > eps:
                t = da / (da - db)
                if -eps <= t <= 1 + eps:
                    points.append((a + t * (b - a))[:2])
        unique = []
        for p in points:
            if not any(np.linalg.norm(p - q) < 1e-5 for q in unique):
                unique.append(p)
        if len(unique) >= 2:
            out.append(np.vstack(unique[:2]))
    return out


shells = [load("Joystick - Joystick_1.stl"), load("Joystick - Joystick_2.stl")]
others = []
for path in SRC.glob("*.stl"):
    if path.name in {"Joystick - Joystick_1.stl", "Joystick - Joystick_2.stl"}:
        continue
    others.append(load(path.name))

# Low-profile installation envelope for the common 32.2 x 21 mm PCB.
# Straight pin headers are removed and wires exit parallel to the PCB.
# Board stands vertically across the split plane: X width 23, Y depth 7, Z height 34.
box_w, box_d, box_h = 23.0, 7.0, 34.0


def triangle_box_overlap(tri: np.ndarray, center: np.ndarray, half: np.ndarray) -> bool:
    v = tri - center
    edges = (v[1] - v[0], v[2] - v[1], v[0] - v[2])
    axes = [
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
        np.cross(edges[0], edges[1]),
    ]
    basis = axes[:3]
    for edge in edges:
        axes.extend(np.cross(edge, axis) for axis in basis)
    for axis in axes:
        if np.dot(axis, axis) < 1e-14:
            continue
        proj = v @ axis
        radius = np.dot(np.abs(axis), half)
        if proj.min() > radius or proj.max() < -radius:
            return False
    return True


all_triangles = np.concatenate(shells + others, axis=0)
tri_min = all_triangles.min(axis=1)
tri_max = all_triangles.max(axis=1)


def collision_count(center: np.ndarray, dims: np.ndarray) -> int:
    half = dims / 2.0
    lo, hi = center - half, center + half
    near = np.flatnonzero(np.all(tri_max >= lo, axis=1) & np.all(tri_min <= hi, axis=1))
    return sum(triangle_box_overlap(all_triangles[i], center, half) for i in near)


candidate_dims = np.array([box_w, box_d, box_h])
candidates = []
for x in (0.0,):
    for y in (24.0, 25.0, 26.0):
        for z in (-33.0,):
            center = np.array([x, y, z])
            count = collision_count(center, candidate_dims)
            if count == 0:
                candidates.append(center)

if candidates:
    # Choose the position with the most wire clearance from the inner wall.
    chosen = min(candidates, key=lambda c: abs(c[0]) * 2 + abs(c[1] - 24.0) + abs(c[2] + 33.0))
else:
    chosen = np.array([0.0, 24.0, -33.0])

print(f"candidate_count={len(candidates)}")
print(f"chosen_center_mm={chosen.tolist()}")
print(f"chosen_dims_mm={candidate_dims.tolist()}")
print(f"chosen_collision_triangles={collision_count(chosen, candidate_dims)}")
for extra_each_side in (0.2, 0.4, 0.8):
    expanded = candidate_dims + 2 * extra_each_side
    print(
        f"expanded_{extra_each_side:.1f}mm_each_side_collision_triangles="
        f"{collision_count(chosen, expanded)}"
    )

fig, axes = plt.subplots(2, 2, figsize=(11, 11), dpi=180)
levels = [-50.0, -40.0, -30.0, -20.0]

for ax, z in zip(axes.ravel(), levels):
    for mesh, color, width in [(shells[0], "#6688aa", 1.8), (shells[1], "#6688aa", 1.8)]:
        for line_xy in section_segments(mesh, z):
            ax.plot(line_xy[:, 0], line_xy[:, 1], color=color, lw=width)
    for mesh in others:
        for line_xy in section_segments(mesh, z):
            ax.plot(line_xy[:, 0], line_xy[:, 1], color="#b96b61", lw=0.8, alpha=0.65)
    if chosen[2] - box_h / 2 <= z <= chosen[2] + box_h / 2:
        x0, x1 = chosen[0] - box_w / 2, chosen[0] + box_w / 2
        y0, y1 = chosen[1] - box_d / 2, chosen[1] + box_d / 2
        ax.add_patch(plt.Rectangle((x0, y0), box_w, box_d, facecolor="#5D8372", edgecolor="#315D4A", alpha=0.36, lw=2))
    ax.axhline(0, color="#dddddd", lw=0.6)
    ax.axvline(0, color="#dddddd", lw=0.6)
    ax.set_title(f"Z = {z:.0f} mm (XY section)")
    ax.set_aspect("equal")
    ax.set_xlim(-45, 45)
    ax.set_ylim(-68, 68)
    ax.grid(alpha=0.15)
    ax.set_xlabel("X [mm]")
    ax.set_ylabel("Y [mm]")

fig.suptitle("OneGrip upper grip cross-sections — PCF8575 placement search", fontsize=15)
fig.tight_layout(rect=(0, 0, 1, 0.965))
fig.savefig(OUT, bbox_inches="tight")
print(OUT)
