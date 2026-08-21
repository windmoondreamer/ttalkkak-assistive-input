"""READ-ONLY MIDDLE rigid-row centre+axis search.

Stage 1 transfers the docs/27 independent-axis tangent offsets to every
re-seated rigid-row candidate.  It is a coarse feasibility/ranking pass used
to select translations for full axis re-optimization; it does not mutate CAD.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_middle_prewrite as geom  # noqa: E402


FRONT = 5.3


class SurfaceProjector:
    def __init__(self):
        self.shell = geom.Mesh(["Joystick_1_baseline", "Joystick_2_baseline"])
        self.centres: dict[float, np.ndarray] = {}

    def project(self, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        z = float(target[2])
        key = round(z, 6)
        if key not in self.centres:
            self.centres[key] = geom.axis_center(self.shell, z)
        centre = self.centres[key]
        theta = math.atan2(target[0] - centre[0], -(target[1] - centre[1]))
        point, normal, _ = geom.outer_point(self.shell, centre, z, theta)
        return np.asarray(point), geom.unit(normal)


def tangent_parameters(normal: np.ndarray, axis: np.ndarray) -> np.ndarray:
    local = geom.frame(normal)
    denominator = float(np.dot(axis, local[2]))
    return np.asarray((np.dot(axis, local[0]) / denominator, np.dot(axis, local[1]) / denominator))


def transferred_axis(normal: np.ndarray, params: np.ndarray) -> np.ndarray:
    return geom.axis_from_tangent(normal, params)


def build_boxes(points: np.ndarray, axes: np.ndarray):
    switches = [geom.obb(points[i], axes[i], geom.SWITCH, geom.SWITCH, FRONT) for i in range(4)]
    pockets = [geom.obb(points[i], axes[i], geom.POCKET, geom.SWITCH + 0.2, FRONT) for i in range(4)]
    holders = [
        geom.obb(
            points[i], axes[i], geom.HOLDER_WIDTH,
            geom.HOLDER_TO - geom.HOLDER_FROM, geom.HOLDER_FROM,
        )
        for i in range(4)
    ]
    return switches, pockets, holders


def evaluate(points, normals, axes, forbidden_meshes, exact_clearance=False):
    switches, pockets, holders = build_boxes(points, axes)
    switch_sat = [geom.sat_signed(switches[i], switches[j]) for i, j in geom.KEY_PAIRS]
    dividers = [geom.sat_signed(pockets[i], pockets[j]) for i, j in geom.ADJ_PAIRS]
    p3x = geom.corners(pockets[2])[:, 0]
    p4x = geom.corners(pockets[3])[:, 0]
    split = (-float(p3x.max()), float(p4x.min()))
    lips = [geom.lip_min(points[i], normals[i], axes[i], FRONT) for i in range(4)]
    pitch = [float(np.linalg.norm(points[i + 1] - points[i])) for i in range(3)]
    screw = []
    for box in holders:
        screw.append(
            min(
                geom.cylinder_gap_x(box, np.asarray(point), x_range, radius)
                for point, x_range, radius in geom.SCREWS.values()
            )
        )

    collisions = []
    clearance = []
    for i in range(4):
        row = {"switch": False, "pocket": False, "holder": False}
        row_clear = {"switch": float("inf"), "pocket": float("inf"), "holder": float("inf")}
        for label, box in (("switch", switches[i]), ("pocket", pockets[i]), ("holder", holders[i])):
            for mesh in forbidden_meshes:
                hit = geom.mesh_box_intersects(mesh, box)
                row[label] |= hit
                if exact_clearance and not hit:
                    row_clear[label] = min(row_clear[label], geom.mesh_box_distance(mesh, box))
                elif hit:
                    row_clear[label] = 0.0
        collisions.append(row)
        clearance.append(row_clear)

    continuous_margins = np.asarray(
        [
            *(value - 1.2 for value in switch_sat),
            *(value - 0.8 for value in dividers),
            *(value - 1.5 for value in split),
            *(value - 2.5 for value in screw),
            *(value - 0.5 for value in lips),
            *(value - 10.5 for value in pitch),
            *(11.5 - value for value in pitch),
        ],
        dtype=float,
    )
    collision_count = sum(sum(int(value) for value in row.values()) for row in collisions)
    violation = float(np.sum(np.maximum(-continuous_margins, 0.0) ** 2) + collision_count * 100.0)
    return {
        "axes": axes.tolist(),
        "switchSatMm": switch_sat,
        "dividerMm": dividers,
        "splitWallMm": split,
        "screwMm": screw,
        "lipMm": lips,
        "pitchMm": pitch,
        "collision": collisions,
        "clearanceMm": clearance,
        "collisionCount": collision_count,
        "continuousMargins": continuous_margins.tolist(),
        "violation": violation,
        "maxDeviationDeg": max(
            math.degrees(math.acos(np.clip(float(np.dot(normals[i], axes[i])), -1.0, 1.0)))
            for i in range(4)
        ),
        "feasible": collision_count == 0 and bool(np.all(continuous_margins >= -1e-8)),
    }


def main() -> None:
    prior = json.loads((ROOT / "cad_dump" / "middle_prewrite_axis_optimization.json").read_text(encoding="utf-8"))
    nominal_points = np.asarray([prior["centers"][name] for name in geom.NAMES])
    nominal_normals = np.asarray([prior["normals"][name] for name in geom.NAMES])
    prior_axes = np.asarray([prior["optimizedAxes"][name] for name in geom.NAMES])
    tangent = np.asarray([tangent_parameters(nominal_normals[i], prior_axes[i]) for i in range(4)])
    projector = SurfaceProjector()
    forbidden = [
        geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
        geom.load_triangles("INDEX_FINAL_RWID"),
        geom.load_triangles("INDEX_FINAL_RZKD"),
    ]

    rows = []
    total = 0
    for dz in np.arange(-8.0, 2.0001, 1.0):
        for dy in np.arange(-6.0, 6.0001, 1.0):
            for dx in np.arange(-4.0, 4.0001, 1.0):
                translation = np.asarray((dx, dy, dz), float)
                derived = [projector.project(nominal_points[i] + translation) for i in range(4)]
                points = np.asarray([row[0] for row in derived])
                normals = np.asarray([row[1] for row in derived])
                axes = np.asarray([transferred_axis(normals[i], tangent[i]) for i in range(4)])
                result = evaluate(points, normals, axes, forbidden, exact_clearance=False)
                rows.append(
                    {
                        "translationMm": translation.tolist(),
                        "translationNormMm": float(np.linalg.norm(translation)),
                        "points": points.tolist(),
                        "normals": normals.tolist(),
                        **result,
                    }
                )
                total += 1
                if total % 100 == 0:
                    feasible = sum(int(row["feasible"]) for row in rows)
                    best = min(rows, key=lambda row: (row["violation"], row["translationNormMm"]))
                    print(
                        f"{total} candidates feasible={feasible} bestV={best['violation']:.3f} "
                        f"bestD={best['translationMm']}",
                        flush=True,
                    )

    ranked = sorted(rows, key=lambda row: (not row["feasible"], row["translationNormMm"], abs(row["translationMm"][2]), row["maxDeviationDeg"]))
    closest = sorted(rows, key=lambda row: (row["violation"], row["translationNormMm"]))[:80]
    payload = {
        "method": "rigid translation + surface re-seat + transferred docs/27 tangent-axis offsets",
        "grid": {"dx": [-4, 4, 1], "dy": [-6, 6, 1], "dz": [-8, 2, 1]},
        "candidateCount": len(rows),
        "feasibleCount": sum(int(row["feasible"]) for row in rows),
        "feasible": [row for row in ranked if row["feasible"]][:80],
        "closestByViolation": closest,
    }
    output = ROOT / "cad_dump" / "middle_joint_rigid_coarse.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {output} feasible={payload['feasibleCount']}")
    for row in (payload["feasible"][:10] or closest[:10]):
        print(
            row["translationMm"], "norm", round(row["translationNormMm"], 3),
            "feasible", row["feasible"], "collision", row["collisionCount"],
            "minSAT", round(min(row["switchSatMm"]), 3),
            "minDiv", round(min(row["dividerMm"]), 3),
            "minSplit", round(min(row["splitWallMm"]), 3),
            "pitch", [round(v, 3) for v in row["pitchMm"]],
        )


if __name__ == "__main__":
    main()
