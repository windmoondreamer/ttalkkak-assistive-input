"""MIDDLE M1..M4 pre-write geometry audit (local computation only).

The script performs no network request and contains no Onshape mutation code.
It consumes the frozen local tessellation caches, derives the MIDDLE surface
centres/normals, runs independent-axis minimax searches, and writes a compact
JSON audit used by docs/27.
"""
from __future__ import annotations

import bisect
import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from mesh_probe import Mesh, axis_center, contour, outer_point  # noqa: E402


ROW_Z = -6.0
ARC_S = (-27.5, -16.5, -5.5, 5.5)
NAMES = ("M1", "M2", "M3", "M4")
KEY_PAIRS = ((0, 1), (1, 2), (0, 2), (2, 3))
ADJ_PAIRS = ((0, 1), (1, 2), (2, 3))
SWITCH = 6.0
POCKET = 6.4
SHELL_WALL = 3.0
TRIM_DEPTH = 2.8
HOLDER_WIDTH = 12.4
HOLDER_FROM = 2.8
HOLDER_TO = 12.5
INDEX_CENTERS = np.asarray(
    [
        (-22.224, -17.494, 9.000),
        (-15.970, -26.208, 9.000),
        (-5.496, -29.325, 9.000),
        (5.496, -29.325, 9.000),
    ],
    dtype=float,
)
INDEX_AXES = np.asarray(
    [
        (-0.851033, -0.500047, -0.160298),
        (-0.393870, -0.571110, -0.720208),
        (-0.069850, -0.997555, 0.002429),
        (0.024161, -0.968017, -0.249718),
    ],
    dtype=float,
)
SCREWS = {
    "A": ((0.0, -41.87, 45.98), (-6.0, 10.0), 3.5),
    "B": ((0.0, -14.45, 23.07), (-6.0, 10.0), 3.5),
    "C": ((0.0, 15.80, -21.35), (-6.0, 10.0), 3.5),
}


def unit(v: np.ndarray) -> np.ndarray:
    return np.asarray(v, dtype=float) / np.linalg.norm(v)


def frame(axis: np.ndarray) -> np.ndarray:
    z = unit(axis)
    u = np.cross((0.0, 0.0, 1.0), z)
    if np.linalg.norm(u) < 1e-9:
        u = np.cross((0.0, 1.0, 0.0), z)
    u = unit(u)
    v = np.cross(z, u)
    return np.asarray((u, v, z))


def obb(point: np.ndarray, axis: np.ndarray, size: float, length: float, front: float):
    axes = frame(axis)
    center = np.asarray(point) - axes[2] * (front + length / 2.0)
    half = np.asarray((size / 2.0, size / 2.0, length / 2.0))
    return center, axes, half


def corners(box) -> np.ndarray:
    c, axes, h = box
    return np.asarray(
        [c + axes.T @ (np.asarray((x, y, z), float) * h)
         for x in (-1.0, 1.0) for y in (-1.0, 1.0) for z in (-1.0, 1.0)]
    )


def sat_signed(box_a, box_b) -> float:
    """Full 15-axis OBB SAT: positive separation, negative penetration MTD."""
    ca, aa, ha = box_a
    cb, ab, hb = box_b
    delta = cb - ca
    axes = [*aa, *ab]
    for va in aa:
        for vb in ab:
            cross = np.cross(va, vb)
            length = np.linalg.norm(cross)
            if length > 1e-10:
                axes.append(cross / length)
    directions = np.asarray(axes)
    ra = np.sum(ha[:, None] * np.abs(aa @ directions.T), axis=0)
    rb = np.sum(hb[:, None] * np.abs(ab @ directions.T), axis=0)
    gaps = np.abs(directions @ delta) - ra - rb
    best = float(np.max(gaps))
    return best if best > 0.0 else -float(np.min(-gaps))


def segment_segment_distance(p1, q1, p2, q2) -> float:
    """Exact closest distance between two finite 3-D line segments."""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e = float(np.dot(d1, d1)), float(np.dot(d2, d2))
    f = float(np.dot(d2, r))
    eps = 1e-15
    if a <= eps and e <= eps:
        return float(np.linalg.norm(p1 - p2))
    if a <= eps:
        s, t = 0.0, np.clip(f / e, 0.0, 1.0)
    else:
        c = float(np.dot(d1, r))
        if e <= eps:
            t, s = 0.0, np.clip(-c / a, 0.0, 1.0)
        else:
            b = float(np.dot(d1, d2))
            denom = a * e - b * b
            s = np.clip((b * f - c * e) / denom, 0.0, 1.0) if denom > eps else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t, s = 0.0, np.clip(-c / a, 0.0, 1.0)
            elif t > 1.0:
                t, s = 1.0, np.clip((b - c) / a, 0.0, 1.0)
    return float(np.linalg.norm((p1 + d1 * s) - (p2 + d2 * t)))


EDGE_IDS = (
    (0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3),
    (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7),
)


def point_box_distance(point: np.ndarray, box) -> float:
    c, axes, h = box
    local = axes @ (point - c)
    return float(np.linalg.norm(np.maximum(np.abs(local) - h, 0.0)))


def box_distance(box_a, box_b) -> float:
    """Exact Euclidean OBB distance (vertex-face and edge-edge cases)."""
    if sat_signed(box_a, box_b) <= 0.0:
        return 0.0
    va, vb = corners(box_a), corners(box_b)
    best = min(
        min(point_box_distance(p, box_b) for p in va),
        min(point_box_distance(p, box_a) for p in vb),
    )
    for ia, ja in EDGE_IDS:
        for ib, jb in EDGE_IDS:
            best = min(best, segment_segment_distance(va[ia], va[ja], vb[ib], vb[jb]))
    return float(best)


def point_triangle_distance(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Closest point distance, Real-Time Collision Detection region tests."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = float(np.dot(ab, ap)), float(np.dot(ac, ap))
    if d1 <= 0.0 and d2 <= 0.0:
        return float(np.linalg.norm(ap))
    bp = p - b
    d3, d4 = float(np.dot(ab, bp)), float(np.dot(ac, bp))
    if d3 >= 0.0 and d4 <= d3:
        return float(np.linalg.norm(bp))
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return float(np.linalg.norm(p - (a + v * ab)))
    cp = p - c
    d5, d6 = float(np.dot(ab, cp)), float(np.dot(ac, cp))
    if d6 >= 0.0 and d5 <= d6:
        return float(np.linalg.norm(cp))
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return float(np.linalg.norm(p - (a + w * ac)))
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return float(np.linalg.norm(p - (b + w * (c - b))))
    denom = 1.0 / (va + vb + vc)
    v, w = vb * denom, vc * denom
    return float(np.linalg.norm(p - (a + ab * v + ac * w)))


def triangle_box_intersects(triangle: np.ndarray, box) -> bool:
    c, axes, h = box
    tri = (triangle - c) @ axes.T
    edges = (tri[1] - tri[0], tri[2] - tri[1], tri[0] - tri[2])
    test_axes = [np.eye(3)[i] for i in range(3)]
    normal = np.cross(edges[0], edges[1])
    if np.linalg.norm(normal) > 1e-12:
        test_axes.append(unit(normal))
    for edge in edges:
        for basis in np.eye(3):
            cross = np.cross(edge, basis)
            if np.linalg.norm(cross) > 1e-12:
                test_axes.append(unit(cross))
    for direction in test_axes:
        proj = tri @ direction
        radius = float(np.dot(h, np.abs(direction)))
        if proj.min() > radius + 1e-10 or proj.max() < -radius - 1e-10:
            return False
    return True


def triangle_box_distance(triangle: np.ndarray, box) -> float:
    if triangle_box_intersects(triangle, box):
        return 0.0
    box_vertices = corners(box)
    best = min(point_box_distance(p, box) for p in triangle)
    best = min(best, *(point_triangle_distance(p, *triangle) for p in box_vertices))
    tri_edges = ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0]))
    for p, q in tri_edges:
        for i, j in EDGE_IDS:
            best = min(best, segment_segment_distance(p, q, box_vertices[i], box_vertices[j]))
    return float(best)


def mesh_box_distance(triangles: np.ndarray, box) -> float:
    """Exact triangle-soup to OBB distance, AABB-pruned."""
    if len(triangles) == 0:
        return float("inf")
    box_vertices = corners(box)
    bmin, bmax = box_vertices.min(axis=0), box_vertices.max(axis=0)
    tmin, tmax = triangles.min(axis=1), triangles.max(axis=1)
    delta = np.maximum(np.maximum(tmin - bmax, bmin - tmax), 0.0)
    lower = np.linalg.norm(delta, axis=1)
    order = np.argsort(lower)
    best = float("inf")
    for idx in order:
        if lower[idx] >= best:
            break
        best = min(best, triangle_box_distance(triangles[idx], box))
        if best <= 1e-10:
            return 0.0
    return best


def mesh_box_intersects(triangles: np.ndarray, box) -> bool:
    """Vectorized exact triangle/AABB SAT after transforming into box space."""
    c, axes, h = box
    tri = (triangles - c) @ axes.T
    alive = np.ones(len(tri), dtype=bool)
    for axis_index in range(3):
        lo = tri[:, :, axis_index].min(axis=1)
        hi = tri[:, :, axis_index].max(axis=1)
        alive &= (lo <= h[axis_index] + 1e-10) & (hi >= -h[axis_index] - 1e-10)
    if not alive.any():
        return False
    tri = tri[alive]
    edges = np.stack((tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 1], tri[:, 0] - tri[:, 2]), axis=1)
    normals = np.cross(edges[:, 0], edges[:, 1])
    plane = np.einsum("ni,ni->n", normals, tri[:, 0])
    radius = np.abs(normals) @ h
    alive = np.abs(plane) <= radius + 1e-10
    if not alive.any():
        return False
    tri, edges = tri[alive], edges[alive]
    alive = np.ones(len(tri), dtype=bool)
    basis = np.eye(3)
    for edge_index in range(3):
        for basis_axis in basis:
            edge = edges[:, edge_index]
            directions = np.cross(edge, basis_axis)
            length = np.linalg.norm(directions, axis=1)
            valid = length > 1e-12
            directions[valid] /= length[valid, None]
            projection = np.einsum("nvi,ni->nv", tri, directions)
            radius = np.abs(directions) @ h
            separated = valid & (
                (projection.min(axis=1) > radius + 1e-10)
                | (projection.max(axis=1) < -radius - 1e-10)
            )
            alive &= ~separated
            if not alive.any():
                return False
            tri, edges = tri[alive], edges[alive]
            alive = np.ones(len(tri), dtype=bool)
    return bool(len(tri))


def segment_box_distance(p0: np.ndarray, p1: np.ndarray, box) -> float:
    """Exact line-segment to OBB distance via convex one-dimensional search."""
    c, axes, h = box
    a, b = axes @ (p0 - c), axes @ (p1 - c)

    def distance_at(t: float) -> float:
        q = a + (b - a) * t
        return float(np.linalg.norm(np.maximum(np.abs(q) - h, 0.0)))

    lo, hi = 0.0, 1.0
    for _ in range(100):
        m1, m2 = lo + (hi - lo) / 3.0, hi - (hi - lo) / 3.0
        if distance_at(m1) <= distance_at(m2):
            hi = m2
        else:
            lo = m1
    return distance_at((lo + hi) / 2.0)


def cylinder_gap_x(box, point, x_range, radius) -> float:
    p0 = np.asarray((x_range[0], point[1], point[2]), float)
    p1 = np.asarray((x_range[1], point[1], point[2]), float)
    return max(segment_box_distance(p0, p1, box) - radius, 0.0)


def exact_surface_point(mesh: Mesh, z: float, target_s: float, cont) -> tuple[np.ndarray, np.ndarray]:
    centre = axis_center(mesh, z)
    arc = [row[0] for row in cont]
    index = min(max(bisect.bisect_left(arc, target_s), 1), len(cont) - 1)
    left, right = cont[index - 1], cont[index]
    f = (target_s - left[0]) / (right[0] - left[0])
    x = left[1] + f * (right[1] - left[1])
    y = left[2] + f * (right[2] - left[2])
    theta = math.atan2(x - centre[0], -(y - centre[1]))
    point, normal, _ = outer_point(mesh, centre, z, theta)
    return np.asarray(point), unit(normal)


def axis_from_tangent(normal: np.ndarray, params: np.ndarray) -> np.ndarray:
    local = frame(normal)
    return unit(local[2] + params[0] * local[0] + params[1] * local[1])


def deviation_deg(params: np.ndarray) -> float:
    return math.degrees(math.atan(float(np.linalg.norm(params))))


def lip_min(point: np.ndarray, normal: np.ndarray, axis: np.ndarray, front: float) -> float:
    u, v, z = frame(axis)
    return min(
        -float(np.dot(point - z * front + u * x + v * y - point, normal)) - TRIM_DEPTH
        for x in (-SWITCH / 2.0, SWITCH / 2.0)
        for y in (-SWITCH / 2.0, SWITCH / 2.0)
    )


def optimize_axes(points: np.ndarray, normals: np.ndarray, front_lip: float, seed: int = 2701):
    front = SHELL_WALL + front_lip
    rng = np.random.default_rng(seed + int(front_lip * 100))
    dim, pop_size, generations = 8, 120, 180
    low, high = -0.65, 0.65

    def evaluate(vector: np.ndarray, detail: bool = False):
        params = vector.reshape(4, 2)
        axes = np.asarray([axis_from_tangent(normals[i], params[i]) for i in range(4)])
        switch_boxes = [obb(points[i], axes[i], SWITCH, SWITCH, front) for i in range(4)]
        pocket_boxes = [obb(points[i], axes[i], POCKET, SWITCH + 0.2, front) for i in range(4)]
        switch_gaps = [sat_signed(switch_boxes[i], switch_boxes[j]) for i, j in KEY_PAIRS]
        divider_gaps = [sat_signed(pocket_boxes[i], pocket_boxes[j]) for i, j in ADJ_PAIRS]
        pocket_x = [corners(box)[:, 0] for box in pocket_boxes]
        split_walls = [-float(pocket_x[2].max()), float(pocket_x[3].min())]
        lips = [lip_min(points[i], normals[i], axes[i], front) for i in range(4)]
        margins = np.asarray(
            [*(g - 1.20 for g in switch_gaps),
             *(g - 0.80 for g in divider_gaps),
             *(g - 1.50 for g in split_walls),
             *(g - 0.50 for g in lips)],
            dtype=float,
        )
        violation = float(np.sum(np.maximum(-margins, 0.0) ** 2))
        devs = [deviation_deg(p) for p in params]
        score = max(devs) + 2_000_000.0 * violation
        if detail:
            return {
                "axes": axes,
                "deviations": devs,
                "switchSat": switch_gaps,
                "dividerSat": divider_gaps,
                "splitWalls": split_walls,
                "lipMinimum": lips,
                "margins": margins,
                "violation": violation,
                "score": score,
                "switchBoxes": switch_boxes,
                "pocketBoxes": pocket_boxes,
            }
        return score

    pop = rng.uniform(low, high, (pop_size, dim))
    pop[0] = 0.0
    scores = np.asarray([evaluate(v) for v in pop])
    for generation in range(generations):
        factor = 0.78 if generation < generations * 0.65 else 0.48
        cross_rate = 0.88
        for i in range(pop_size):
            choices = rng.choice(pop_size - 1, 3, replace=False)
            choices = np.where(choices >= i, choices + 1, choices)
            a, b, c = pop[choices]
            mutant = np.clip(a + factor * (b - c), low, high)
            mask = rng.random(dim) < cross_rate
            mask[rng.integers(dim)] = True
            trial = np.where(mask, mutant, pop[i])
            score = evaluate(trial)
            if score < scores[i]:
                pop[i], scores[i] = trial, score
        # Re-seed the worst tail around the current best to resolve active boundaries.
        if generation and generation % 80 == 0:
            best = pop[int(np.argmin(scores))].copy()
            tail = np.argsort(scores)[-30:]
            scale = 0.08 * (1.0 - generation / generations) + 0.008
            for i in tail:
                pop[i] = np.clip(best + rng.normal(0.0, scale, dim), low, high)
                scores[i] = evaluate(pop[i])
    best = pop[int(np.argmin(scores))].copy()

    # Deterministic shrinking random refinement.
    current_score = evaluate(best)
    for scale in (0.04, 0.02, 0.01, 0.004, 0.0015, 0.0005):
        for _ in range(1400):
            trial = np.clip(best + rng.normal(0.0, scale, dim), low, high)
            score = evaluate(trial)
            if score < current_score:
                best, current_score = trial, score
    return best, evaluate(best, detail=True)


def center_axis_ray(full_mesh: Mesh, point: np.ndarray, axis: np.ndarray):
    """Centre-line wall and next-obstruction distances along the proposed axis."""
    origin = point + axis * 3.0
    hits = full_mesh.hits_dedup(origin, -axis)
    sequence = [(float(t - 3.0), full_mesh.names[full_mesh.owner[idx]]) for t, idx in hits]
    sequence = [row for row in sequence if row[0] > -0.10]
    wall = sequence[1][0] - sequence[0][0] if len(sequence) >= 2 else float("nan")
    obstruction = sequence[2][0] if len(sequence) >= 3 else float("inf")
    return wall, obstruction, sequence[:6]


def load_triangles(name: str) -> np.ndarray:
    path = ROOT / "cad_dump" / f"mesh_{name}.json"
    return np.asarray(json.loads(path.read_text(encoding="utf-8"))["tris"], dtype=float)


def main() -> None:
    shell = Mesh(["Joystick_1_baseline", "Joystick_2_baseline"])
    full = Mesh(["Joystick_1_baseline", "Joystick_2_baseline", "Backplate", "Small_joystick_attachment"])
    cross_section = contour(shell, ROW_Z, n=2400, span=math.pi * 0.55)
    derived = [exact_surface_point(shell, ROW_Z, s, cross_section) for s in ARC_S]
    points = np.asarray([row[0] for row in derived])
    normals = np.asarray([row[1] for row in derived])

    baseline_boxes = [obb(points[i], normals[i], SWITCH, SWITCH, SHELL_WALL + 0.8) for i in range(4)]
    baseline = {
        f"{NAMES[i]}-{NAMES[j]}": sat_signed(baseline_boxes[i], baseline_boxes[j])
        for i, j in KEY_PAIRS
    }

    candidates = {}
    for front_lip in (0.8, 1.5, 2.3):
        vector, detail = optimize_axes(points, normals, front_lip)
        candidates[str(front_lip)] = (vector, detail)
        print(
            f"lip={front_lip:.1f} maxdev={max(detail['deviations']):.5f} "
            f"minSAT={min(detail['switchSat']):.6f} minDivider={min(detail['dividerSat']):.6f} "
            f"split={min(detail['splitWalls']):.6f} minLip={min(detail['lipMinimum']):.6f} "
            f"violation={detail['violation']:.3e}",
            flush=True,
        )

    feasible = [
        (float(lip), vector, detail)
        for lip, (vector, detail) in candidates.items()
        if detail["violation"] < 2e-10
    ]
    if not feasible:
        chosen_lip, vector, chosen = min(
            ((float(lip), vector, detail) for lip, (vector, detail) in candidates.items()),
            key=lambda row: row[2]["violation"],
        )
    else:
        # Prefer the shallowest front lip that passes every constraint.
        chosen_lip, vector, chosen = min(feasible, key=lambda row: row[0])

    axes = chosen["axes"]
    front = SHELL_WALL + chosen_lip
    switch_boxes = chosen["switchBoxes"]
    pocket_boxes = chosen["pocketBoxes"]
    holder_boxes = [obb(points[i], axes[i], HOLDER_WIDTH, HOLDER_TO - HOLDER_FROM, HOLDER_FROM) for i in range(4)]

    exact_switch = {
        f"{NAMES[i]}-{NAMES[j]}": {
            "satSeparationMm": sat_signed(switch_boxes[i], switch_boxes[j]),
            "euclideanMm": box_distance(switch_boxes[i], switch_boxes[j]),
        }
        for i, j in KEY_PAIRS
    }
    dividers = {
        f"{NAMES[i]}-{NAMES[j]}": {
            "satSeparationMm": sat_signed(pocket_boxes[i], pocket_boxes[j]),
            "euclideanMm": box_distance(pocket_boxes[i], pocket_boxes[j]),
        }
        for i, j in ADJ_PAIRS
    }

    screw_rows = {}
    for i, box in enumerate(holder_boxes):
        per = {
            name: cylinder_gap_x(box, np.asarray(point), x_range, radius)
            for name, (point, x_range, radius) in SCREWS.items()
        }
        screw_rows[NAMES[i]] = per

    index_holder_boxes = [
        obb(INDEX_CENTERS[i], unit(INDEX_AXES[i]), HOLDER_WIDTH, HOLDER_TO - HOLDER_FROM, HOLDER_FROM)
        for i in range(4)
    ]
    index_switch_boxes = [
        obb(INDEX_CENTERS[i], unit(INDEX_AXES[i]), SWITCH, SWITCH, 5.3) for i in range(4)
    ]
    index_box_rows = {}
    for i, box in enumerate(holder_boxes):
        holder_gaps = [box_distance(box, other) for other in index_holder_boxes]
        switch_gaps = [box_distance(switch_boxes[i], other) for other in index_switch_boxes]
        index_box_rows[NAMES[i]] = {
            "nearestIndexHolder": f"I{int(np.argmin(holder_gaps)) + 1}",
            "holderClearanceMm": min(holder_gaps),
            "nearestIndexSwitch": f"I{int(np.argmin(switch_gaps)) + 1}",
            "switchClearanceMm": min(switch_gaps),
        }

    rwid = load_triangles("INDEX_FINAL_RWID")
    rzkd = load_triangles("INDEX_FINAL_RZKD")
    retainer_rows = {}
    for i, box in enumerate(holder_boxes):
        retainer_rows[NAMES[i]] = {
            "RWIDmm": mesh_box_distance(rwid, box),
            "RZKDmm": mesh_box_distance(rzkd, box),
        }

    # Final positive fastening proxies that are unioned into the frozen shells.
    w = unit(np.asarray((-0.4734, -0.8350, -0.2805)))
    anchor_b = np.asarray((-4.52, -15.38, 1.97))
    shared_boss = obb(anchor_b - w * ((0.5 + 5.2) / 2.0), w, 5.0, 4.7, 0.0)
    i4_u = frame(unit(INDEX_AXES[3]))[0]
    i4_anchor = INDEX_CENTERS[3] + i4_u * 7.0
    i4_boss = obb(i4_anchor, unit(INDEX_AXES[3]), 6.0, 4.5, 8.0)
    fastening_rows = {
        NAMES[i]: {
            "sharedBossBProxyMm": box_distance(holder_boxes[i], shared_boss),
            "i4BossProxyMm": box_distance(holder_boxes[i], i4_boss),
        }
        for i in range(4)
    }

    thumb_names = [
        "Backplate", "Small_joystick_attachment", "Button_corner_1", "Button_side_1",
        "Button_wide_1", "Button_middle_1", "Button_corner_2", "Button_side_2",
        "Button_wide_2", "Button_middle_2",
    ]
    thumb_meshes = {name: load_triangles(name) for name in thumb_names}
    thumb_rows = {}
    for i, box in enumerate(holder_boxes):
        values = {name: mesh_box_distance(tris, box) for name, tris in thumb_meshes.items()}
        nearest = min(values, key=values.get)
        thumb_rows[NAMES[i]] = {"nearest": nearest, "clearanceMm": values[nearest]}

    feasibility = {}
    for i in range(4):
        wall, obstruction, sequence = center_axis_ray(full, points[i], axes[i])
        bore_clearance = 4.0 - 2.25 / max(math.cos(math.radians(chosen["deviations"][i])), 1e-6)
        rear_center = points[i] - axes[i] * HOLDER_TO
        rear_forward = full.hits_dedup(rear_center + axes[i] * 0.01, -axes[i])
        rear_exit = float(rear_forward[0][0]) if rear_forward else float("inf")
        feasibility[NAMES[i]] = {
            "wallMm": wall,
            "nextObstructionDepthMm": obstruction,
            "availableBehindWallMm": obstruction - wall if math.isfinite(obstruction) else float("inf"),
            "stemBoreOpeningClearanceConservativeMm": bore_clearance,
            "rearAxisOpenDistanceMm": rear_exit,
            "raySequence": sequence,
        }

    clear_nbr = {}
    for i, j in ADJ_PAIRS:
        clear_nbr[f"{NAMES[i]}-{NAMES[j]}"] = {
            f"{NAMES[i]}HolderVs{NAMES[j]}PocketSatMm": sat_signed(holder_boxes[i], pocket_boxes[j]),
            f"{NAMES[j]}HolderVs{NAMES[i]}PocketSatMm": sat_signed(holder_boxes[j], pocket_boxes[i]),
            "required": (
                sat_signed(holder_boxes[i], pocket_boxes[j]) <= 0.0
                or sat_signed(holder_boxes[j], pocket_boxes[i]) <= 0.0
            ),
        }

    result = {
        "method": {
            "mode": "LOCAL READ-ONLY; Onshape CAD WRITE 0",
            "sourceVersion": "03ede76e83b5c865d9a69c35",
            "configuration": "default",
            "surfaceMesh": ["Joystick_1_baseline", "Joystick_2_baseline"],
            "rowZmm": ROW_Z,
            "contourSamplesEachSide": 2400,
            "switchSat": "full 15-axis OBB SAT",
            "axisFamily": "independent 2-DOF tangent coordinates for each unit axis",
        },
        "centers": {NAMES[i]: points[i].tolist() for i in range(4)},
        "normals": {NAMES[i]: normals[i].tolist() for i in range(4)},
        "centerDistancesMm": {
            f"{NAMES[i]}-{NAMES[i + 1]}": float(np.linalg.norm(points[i + 1] - points[i]))
            for i in range(3)
        },
        "baselineSatMm": baseline,
        "candidateSummary": {
            lip: {
                "axes": detail["axes"].tolist(),
                "deviationsDeg": detail["deviations"],
                "maxDeviationDeg": max(detail["deviations"]),
                "minimumSwitchSatMm": min(detail["switchSat"]),
                "minimumDividerSatMm": min(detail["dividerSat"]),
                "minimumSplitWallMm": min(detail["splitWalls"]),
                "minimumActualLipMm": min(detail["lipMinimum"]),
                "violation": detail["violation"],
            }
            for lip, (_, detail) in candidates.items()
        },
        "selectedFrontLipMm": chosen_lip,
        "selectedSwitchFrontDepthMm": front,
        "optimizedAxes": {NAMES[i]: axes[i].tolist() for i in range(4)},
        "deviationsDeg": {NAMES[i]: chosen["deviations"][i] for i in range(4)},
        "maxDeviationDeg": max(chosen["deviations"]),
        "optimizedSwitchClearance": exact_switch,
        "pocketDividers": dividers,
        "splitWallsMm": {"M3": chosen["splitWalls"][0], "M4": chosen["splitWalls"][1]},
        "actualFrontLipMinimumMm": {NAMES[i]: chosen["lipMinimum"][i] for i in range(4)},
        "screwClearanceMm": screw_rows,
        "indexBoxClearance": index_box_rows,
        "indexRetainerClearance": retainer_rows,
        "indexFasteningClearance": fastening_rows,
        "originalThumbClearance": thumb_rows,
        "holderFeasibility": feasibility,
        "clearNbr": clear_nbr,
        "holderArchitecture": "short seat + open rear cavity + separate holder body + CLEARNBR + holder-only split clip + target-first union",
    }
    output = ROOT / "cad_dump" / "middle_prewrite_axis_optimization.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
