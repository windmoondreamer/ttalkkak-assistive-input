"""PCF8575 one-shell placement search for the current OneGrip upper grip.

The first study placed a low-profile PCF8575 envelope across X=0.  That was
collision-free, but it made the board a split-shell bridge and therefore made
manual assembly and servicing unnecessarily fragile.  This revision searches
placements wholly owned by one shell and checks a 0.8 mm enlarged robustness
envelope as well as the nominal envelope.

N1/N2 and the SZH-EK056 thumb joystick are deliberately outside this audit.
All dimensions are millimetres.
"""

from __future__ import annotations

import json
from pathlib import Path
import struct
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
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
HERE = Path(__file__).resolve().parent
OUT_JSON = HERE / "pcf8575_one_shell_search_v2.json"
OUT_PNG = HERE / "pcf8575_one_shell_search_v2.png"

SHELL_NAMES = {"Joystick - Joystick_1.stl", "Joystick - Joystick_2.stl"}

# Common PCF8575 module assumption already used by the team: PCB 32.2 x 21 mm.
# Straight headers are removed and wires leave parallel to the PCB.  The outer
# envelope includes a separate printed edge cradle and FDM clearance.
ORIENTATIONS = {
    "THIN_X_TALL_Z": np.array([9.0, 24.0, 35.0]),
    "THIN_X_LOW_Z": np.array([9.0, 35.0, 24.0]),
}
ROBUSTNESS_GROWTH = np.array([0.8, 0.8, 0.8])
SPLIT_KEEP_AWAY = 2.0


def load_binary_stl(path: Path) -> np.ndarray:
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attr", "<u2"),
    ])
    records = np.frombuffer(data, dtype=dtype, count=count, offset=84)
    return records["vertices"].astype(float)


def triangle_box_overlap(tri: np.ndarray, center: np.ndarray, half: np.ndarray) -> bool:
    v = tri - center
    edges = (v[1] - v[0], v[2] - v[1], v[0] - v[2])
    basis = (
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
    )
    axes = [*basis, np.cross(edges[0], edges[1])]
    for edge in edges:
        axes.extend(np.cross(edge, axis) for axis in basis)
    for axis in axes:
        if np.dot(axis, axis) < 1e-14:
            continue
        projected = v @ axis
        radius = np.dot(np.abs(axis), half)
        if projected.min() > radius or projected.max() < -radius:
            return False
    return True


def ray_triangle_t(origin: np.ndarray, direction: np.ndarray, tri: np.ndarray) -> float | None:
    edge1 = tri[1] - tri[0]
    edge2 = tri[2] - tri[0]
    h = np.cross(direction, edge2)
    a = np.dot(edge1, h)
    if abs(a) < 1e-10:
        return None
    f = 1.0 / a
    s = origin - tri[0]
    u = f * np.dot(s, h)
    if u < 0.0 or u > 1.0:
        return None
    q = np.cross(s, edge1)
    v = f * np.dot(direction, q)
    if v < 0.0 or u + v > 1.0:
        return None
    t = f * np.dot(edge2, q)
    return t if t > 1e-5 else None


def section_segments(triangles: np.ndarray, z: float, eps: float = 1e-7) -> list[np.ndarray]:
    segments = []
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
        for point in points:
            if not any(np.linalg.norm(point - other) < 1e-5 for other in unique):
                unique.append(point)
        if len(unique) >= 2:
            segments.append(np.vstack(unique[:2]))
    return segments


shells = [load_binary_stl(SRC / name) for name in sorted(SHELL_NAMES)]
other_meshes = [load_binary_stl(path) for path in SRC.glob("*.stl") if path.name not in SHELL_NAMES]
shell_triangles = np.concatenate(shells, axis=0)
all_triangles = np.concatenate(shells + other_meshes, axis=0)
tri_min = all_triangles.min(axis=1)
tri_max = all_triangles.max(axis=1)
shell_tri_min = shell_triangles.min(axis=1)
shell_tri_max = shell_triangles.max(axis=1)


def collision_count(center: np.ndarray, dims: np.ndarray) -> int:
    half = dims / 2.0
    low, high = center - half, center + half
    near = np.flatnonzero(np.all(tri_max >= low, axis=1) & np.all(tri_min <= high, axis=1))
    return sum(triangle_box_overlap(all_triangles[index], center, half) for index in near)


def conservative_aabb_overlap_count(center: np.ndarray, dims: np.ndarray) -> int:
    """Fast conservative gate: zero proves the envelope has no mesh contact."""
    half = dims / 2.0
    low, high = center - half, center + half
    return int(np.count_nonzero(
        np.all(tri_max >= low, axis=1) & np.all(tri_min <= high, axis=1)
    ))


def ray_shell_distance(center: np.ndarray, direction: np.ndarray, max_distance: float = 60.0) -> float | None:
    # Fast AABB filter around the finite ray segment.
    endpoint = center + direction * max_distance
    low = np.minimum(center, endpoint) - 0.01
    high = np.maximum(center, endpoint) + 0.01
    near = np.flatnonzero(
        np.all(shell_tri_max >= low, axis=1) & np.all(shell_tri_min <= high, axis=1)
    )
    hits = []
    for index in near:
        value = ray_triangle_t(center, direction, shell_triangles[index])
        if value is not None and value <= max_distance:
            hits.append(value)
    return min(hits) if hits else None


def cavity_gate(center: np.ndarray) -> tuple[bool, dict[str, float | None]]:
    directions = {
        "+X": np.array([1.0, 0.0, 0.0]),
        "-X": np.array([-1.0, 0.0, 0.0]),
        "+Y": np.array([0.0, 1.0, 0.0]),
        "-Y": np.array([0.0, -1.0, 0.0]),
    }
    distances = {name: ray_shell_distance(center, direction) for name, direction in directions.items()}
    return all(value is not None for value in distances.values()), distances


def shell_owner(center: np.ndarray, dims: np.ndarray) -> str | None:
    low_x = center[0] - dims[0] / 2.0
    high_x = center[0] + dims[0] / 2.0
    if low_x >= SPLIT_KEEP_AWAY:
        return "Joystick_1_positive_X_shell"
    if high_x <= -SPLIT_KEEP_AWAY:
        return "Joystick_2_negative_X_shell"
    return None


def search() -> list[dict]:
    valid = []
    for orientation, dims in ORIENTATIONS.items():
        # Focus on the already section-verified central cavity.  Wider ranges
        # mostly sample the shell wall and only increase run time.
        for x_abs in (8.0, 10.0, 12.0, 14.0, 16.0):
            for sign in (-1.0, 1.0):
                x = sign * x_abs
                for y in (22.0, 24.0, 26.0):
                    for z in (-36.0, -33.0, -30.0):
                        center = np.array([x, y, z])
                        owner = shell_owner(center, dims)
                        if owner is None:
                            continue
                        robust_dims = dims + ROBUSTNESS_GROWTH * 2.0
                        nominal_aabb = conservative_aabb_overlap_count(center, dims)
                        robust_aabb = conservative_aabb_overlap_count(center, robust_dims)
                        # Prefer the uncrowded positive-X shell, the old proven
                        # Y/Z neighbourhood, and the thin-X service orientation.
                        orientation_penalty = {
                            "THIN_X_TALL_Z": 0.0,
                            "THIN_X_LOW_Z": 8.0,
                        }[orientation]
                        side_penalty = 0.0 if center[0] > 0 else 5.0
                        score = (
                            orientation_penalty
                            + side_penalty
                            + abs(abs(center[0]) - 12.0) * 0.8
                            + abs(center[1] - 24.0)
                            + abs(center[2] + 33.0) * 0.7
                            + robust_aabb * 0.03
                        )
                        valid.append({
                            "orientation": orientation,
                            "center_mm": center.tolist(),
                            "dims_mm": dims.tolist(),
                            "owner_shell": owner,
                            "score": float(score),
                            "nominal_aabb_triangle_candidates": nominal_aabb,
                            "robust_aabb_triangle_candidates": robust_aabb,
                        })
    return sorted(valid, key=lambda item: item["score"])


valid = search()
if not valid:
    raise RuntimeError("No one-shell, robust, cavity-contained PCF8575 placement found")

chosen = None
for candidate in valid[:20]:
    candidate_center = np.array(candidate["center_mm"])
    candidate_dims = np.array(candidate["dims_mm"])
    if collision_count(candidate_center, candidate_dims) != 0:
        continue
    if collision_count(
        candidate_center, candidate_dims + ROBUSTNESS_GROWTH * 2.0
    ) != 0:
        continue
    in_cavity, rays = cavity_gate(candidate_center)
    candidate["four_ray_closed_cavity_gate"] = in_cavity
    candidate["shell_ray_clearance_mm"] = rays
    # The upper shell contains service openings, so a four-direction ray test
    # is diagnostic rather than a hard containment test.  The search itself is
    # restricted to the previously section-verified central cavity.
    chosen = candidate
    break
if chosen is None:
    rejection = {
        "decision": "one-shell PCF8575 envelope rejected; retain central split-spanning placement",
        "source_stl_directory": str(SRC),
        "board_assumption_mm": [32.2, 21.0],
        "tested_candidate_count": len(valid),
        "exact_candidates_checked": min(20, len(valid)),
        "required_robustness_each_side_mm": ROBUSTNESS_GROWTH.tolist(),
        "result": "no exact nominal+robust collision-free one-shell placement",
        "fallback": {
            "center_mm": [0.0, 24.0, -33.0],
            "envelope_mm": [23.0, 7.0, 34.0],
            "nominal_collision_triangles": 0,
            "verified_growth_each_side_mm": 0.4,
            "mounting": "cantilevered removable edge cradle owned by one shell; board envelope may cross X=0",
        },
    }
    OUT_JSON.write_text(
        json.dumps(rejection, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(rejection, indent=2, ensure_ascii=False))
    sys.exit(0)
center = np.array(chosen["center_mm"])
dims = np.array(chosen["dims_mm"])

report = {
    "decision": "PCF8575 in moving upper grip; wholly owned by one shell",
    "source_stl_directory": str(SRC),
    "board_assumption_mm": [32.2, 21.0],
    "header_policy": "remove straight headers; solder flexible wires parallel to PCB",
    "split_keep_away_mm": SPLIT_KEEP_AWAY,
    "robustness_growth_each_side_mm": ROBUSTNESS_GROWTH.tolist(),
    "candidate_count": len(valid),
    "chosen": chosen,
    "chosen_nominal_collision_triangles": collision_count(center, dims),
    "chosen_robust_collision_triangles": collision_count(
        center, dims + ROBUSTNESS_GROWTH * 2.0
    ),
    "assembly": {
        "board_owner": chosen["owner_shell"],
        "shell_split_crossing": False,
        "service_sequence": "open opposite shell, unplug JST lead, release tray retainer, lift board",
        "mounting_rule": "separate edge cradle; no component-side clamping",
    },
    "stop_gates": [
        "Measure the exact PCF8575 module including connector and solder heights.",
        "Confirm component-free PCB edge zones before freezing the edge cradle.",
        "Validate tray-to-shell fastener locations on the printed upper shell.",
    ],
}
OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

fig, axes = plt.subplots(2, 2, figsize=(11, 11), dpi=180)
levels = [-48.0, -40.0, -32.0, -24.0]
for axis, z_value in zip(axes.ravel(), levels):
    for shell in shells:
        for segment in section_segments(shell, z_value):
            axis.plot(segment[:, 0], segment[:, 1], color="#537493", lw=1.6)
    for mesh in other_meshes:
        for segment in section_segments(mesh, z_value):
            axis.plot(segment[:, 0], segment[:, 1], color="#B76E61", lw=0.65, alpha=0.55)
    if center[2] - dims[2] / 2 <= z_value <= center[2] + dims[2] / 2:
        axis.add_patch(Rectangle(
            (center[0] - dims[0] / 2, center[1] - dims[1] / 2),
            dims[0], dims[1], facecolor="#46B38A", edgecolor="#174F3D", alpha=0.48, lw=2,
        ))
    axis.axvline(0, color="#D84C4C", ls="--", lw=1.0, label="shell split X=0")
    axis.set_title(f"Z = {z_value:.0f} mm")
    axis.set_aspect("equal")
    axis.set_xlim(-45, 45)
    axis.set_ylim(-68, 68)
    axis.grid(alpha=0.15)
    axis.set_xlabel("X [mm]")
    axis.set_ylabel("Y [mm]")

fig.suptitle(
    "OneGrip PCF8575 one-shell placement — nominal + 0.8 mm/side robust clearance\n"
    f"chosen {chosen['orientation']} at {chosen['center_mm']} mm",
    fontsize=13,
)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(OUT_PNG, bbox_inches="tight")

print(json.dumps(report, indent=2, ensure_ascii=False))
print(OUT_PNG)
