"""Final local-only evaluation of MIDDLE joint-search Options A/B/C."""
from __future__ import annotations

import heapq
import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_middle_prewrite as geom  # noqa: E402


def load_json(name: str):
    return json.loads((ROOT / "cad_dump" / name).read_text(encoding="utf-8"))


def feasible_rows(name: str):
    return [row for row in load_json(name)["results"] if row.get("feasible")]


def select_options():
    fine = feasible_rows("middle_joint_axis_rows_fine_v2.json")
    deep = feasible_rows("middle_joint_axis_rows_deep_v3.json")
    option_a = min(fine, key=lambda row: row["translationNormMm"])
    option_b = min(deep, key=lambda row: row["detail"]["maxDeviationDeg"])
    option_c = max(deep, key=lambda row: -abs(row["translationMm"][2] + 8.0))
    return {"A": option_a, "B": option_b, "C": option_c}


def build_surface_graph():
    triangles = np.concatenate(
        (geom.load_triangles("Joystick_1_baseline"), geom.load_triangles("Joystick_2_baseline")), axis=0
    )
    vertices, inverse = np.unique(np.round(triangles.reshape(-1, 3), 6), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    adjacency = [[] for _ in range(len(vertices))]
    for face in faces:
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            weight = float(np.linalg.norm(vertices[a] - vertices[b]))
            adjacency[a].append((int(b), weight))
            adjacency[b].append((int(a), weight))
    return vertices, adjacency


def nearest_vertex(vertices: np.ndarray, point: np.ndarray):
    distances = np.linalg.norm(vertices - point, axis=1)
    index = int(np.argmin(distances))
    return index, float(distances[index])


def dijkstra(adjacency, source: int, targets: set[int]):
    distances = {source: 0.0}
    queue = [(0.0, source)]
    pending = set(targets)
    result = {}
    while queue and pending:
        distance, node = heapq.heappop(queue)
        if distance != distances.get(node):
            continue
        if node in pending:
            result[node] = distance
            pending.remove(node)
        for neighbor, weight in adjacency[node]:
            candidate = distance + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    return result


def component_clearance(points: np.ndarray, axes: np.ndarray):
    components = {
        "frozenShellIndexSurface": geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
        "RWID": geom.load_triangles("INDEX_FINAL_RWID"),
        "RZKD": geom.load_triangles("INDEX_FINAL_RZKD"),
    }
    per_button = {}
    global_min = (float("inf"), None, None, None)
    for i, name in enumerate(geom.NAMES):
        boxes = {
            "switch": geom.obb(points[i], axes[i], geom.SWITCH, geom.SWITCH, 5.3),
            "pocket": geom.obb(points[i], axes[i], geom.POCKET, geom.SWITCH + 0.2, 5.3),
            "holder": geom.obb(
                points[i], axes[i], geom.HOLDER_WIDTH,
                geom.HOLDER_TO - geom.HOLDER_FROM, geom.HOLDER_FROM,
            ),
        }
        rows = {}
        for box_name, box in boxes.items():
            rows[box_name] = {}
            for component, triangles in components.items():
                hit = geom.mesh_box_intersects(triangles, box)
                distance = 0.0 if hit else geom.mesh_box_distance(triangles, box)
                rows[box_name][component] = {"collision": hit, "clearanceMm": distance}
                if distance < global_min[0]:
                    global_min = (distance, name, box_name, component)
        per_button[name] = rows
    return {
        "perButton": per_button,
        "globalMinimum": {
            "clearanceMm": global_min[0],
            "button": global_min[1],
            "envelope": global_min[2],
            "component": global_min[3],
        },
    }


def spacing_metrics(options, nominal_points):
    index_centers = geom.INDEX_CENTERS
    vertices, adjacency = build_surface_graph()
    all_middle = {"nominal": nominal_points}
    all_middle.update({key: np.asarray(row["points"], float) for key, row in options.items()})
    metrics = {label: {} for label in all_middle}
    index_nodes = []
    index_snap = []
    for point in index_centers:
        node, snap = nearest_vertex(vertices, point)
        index_nodes.append(node); index_snap.append(snap)
    middle_nodes = {
        label: [nearest_vertex(vertices, point) for point in points]
        for label, points in all_middle.items()
    }
    for i in range(4):
        targets = {middle_nodes[label][i][0] for label in all_middle}
        paths = dijkstra(adjacency, index_nodes[i], targets)
        for label, points in all_middle.items():
            delta = points[i] - index_centers[i]
            target_node, target_snap = middle_nodes[label][i]
            metrics[label][geom.NAMES[i]] = {
                "indexButton": f"I{i + 1}",
                "centerDistance3dMm": float(np.linalg.norm(delta)),
                "zDifferenceMm": float(delta[2]),
                "xyTangentialChordMm": float(np.linalg.norm(delta[:2])),
                "surfaceMeshGeodesicMm": float(paths.get(target_node, float("inf"))),
                "indexSnapErrorMm": index_snap[i],
                "middleSnapErrorMm": target_snap,
            }
    return metrics


def summarize_option(label, row, clearance, spacing):
    detail = row["detail"]
    axes = np.asarray(row["axisSolution"]["axes"], float)
    points = np.asarray(row["points"], float)
    pocket_boxes = [geom.obb(points[i], axes[i], geom.POCKET, geom.SWITCH + 0.2, 5.3) for i in range(4)]
    normals = np.asarray(row["normals"], float)
    # External caps retain the local surface/opening normal, as in INDEX; they
    # do not follow the independently tilted internal switch axis.  A 0.2 mm
    # surface slab is used for exact footprint SAT (nominal width remains 8 mm).
    cap_boxes = [geom.obb(points[i], normals[i], 8.0, 0.2, -0.1) for i in range(4)]
    cap_gaps = [geom.sat_signed(cap_boxes[i], cap_boxes[i + 1]) for i in range(3)]
    return {
        "translationMm": row["translationMm"],
        "translationNormMm": row["translationNormMm"],
        "tangentialCorrectionMm": row["tangentialCorrectionMm"],
        "longitudinalCorrectionMm": row["longitudinalCorrectionMm"],
        "perButtonDisplacementMm": row["perButtonDisplacementMm"],
        "centers": {geom.NAMES[i]: points[i].tolist() for i in range(4)},
        "normals": {geom.NAMES[i]: row["normals"][i] for i in range(4)},
        "axes": {geom.NAMES[i]: axes[i].tolist() for i in range(4)},
        "deviationsDeg": {geom.NAMES[i]: row["axisSolution"]["deviationsDeg"][i] for i in range(4)},
        "maxDeviationDeg": detail["maxDeviationDeg"],
        "pitchMm": row["pitchMm"],
        "minimumSwitchSatMm": min(detail["switchSatMm"]),
        "switchSatMm": detail["switchSatMm"],
        "minimumDividerMm": min(detail["dividerMm"]),
        "dividerMm": detail["dividerMm"],
        "minimumSplitWallMm": min(detail["splitWallMm"]),
        "splitWallMm": detail["splitWallMm"],
        "minimumScrewMm": min(detail["screwMm"]),
        "screwMm": detail["screwMm"],
        "minimumLipMm": min(detail["lipMm"]),
        "capPairSatMm": cap_gaps,
        "minimumCapSatMm": min(cap_gaps),
        "indexClearance": clearance,
        "spacing": spacing[label],
        "allHardGates": bool(
            min(detail["switchSatMm"]) >= 1.2
            and min(detail["dividerMm"]) >= 0.8
            and min(detail["splitWallMm"]) >= 1.5
            and min(detail["screwMm"]) >= 2.5
            and min(row["pitchMm"]) >= 10.5
            and max(row["pitchMm"]) <= 11.5
            and clearance["globalMinimum"]["clearanceMm"] > 0.0
            and min(cap_gaps) > 0.0
        ),
    }


def main() -> None:
    prior = load_json("middle_prewrite_axis_optimization.json")
    nominal_points = np.asarray([prior["centers"][name] for name in geom.NAMES])
    options = select_options()
    spacing = spacing_metrics(options, nominal_points)
    summaries = {}
    for label, row in options.items():
        points = np.asarray(row["points"], float)
        axes = np.asarray(row["axisSolution"]["axes"], float)
        clearance = component_clearance(points, axes)
        summaries[label] = summarize_option(label, row, clearance, spacing)

    coarse = load_json("middle_joint_rigid_coarse.json")
    closest_rigid = coarse["closestByViolation"][0]
    payload = {
        "method": {
            "mode": "READ-ONLY / Onshape CAD WRITE 0",
            "sourceVersion": "03ede76e83b5c865d9a69c35",
            "configuration": "default",
            "geometry": "frozen final JaD/JfD INDEX-changed surface + RWID + RZKD",
            "geodesic": "shortest-path over original-shell tessellation edges",
        },
        "nominalCenters": {geom.NAMES[i]: nominal_points[i].tolist() for i in range(4)},
        "nominalConflict": prior["indexRetainerClearance"],
        "rigidSearch": {
            "candidateCount": coarse["candidateCount"],
            "feasibleCount": coarse["feasibleCount"],
            "closestCollisionFreeTransferredAxisCandidate": closest_rigid,
        },
        "options": summaries,
        "nominalSpacing": spacing["nominal"],
        "decision": {
            "recommended": "B",
            "sixMmSwitchMaintainable": True,
            "hardwareFallbackNeeded": "CONDITIONAL_NOT_YET",
            "cadWrite": "HOLD",
            "holdReason": (
                "A/B minimum frozen-INDEX holder clearance is below tessellation resolution margin; "
                "C is robust but requires >=8 mm row translation and M2 -3 mm correction. "
                "Exact B-rep boolean/clearance validation and ergonomic approval are required before write."
            ),
        },
    }
    path = ROOT / "cad_dump" / "middle_center_axis_joint_optimization.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {path}")
    for label, row in summaries.items():
        print(
            label,
            "D", round(row["translationNormMm"], 3),
            "maxDev", round(row["maxDeviationDeg"], 3),
            "SAT", round(row["minimumSwitchSatMm"], 3),
            "divider", round(row["minimumDividerMm"], 3),
            "split", round(row["minimumSplitWallMm"], 3),
            "screw", round(row["minimumScrewMm"], 3),
            "index", round(row["indexClearance"]["globalMinimum"]["clearanceMm"], 4),
            "cap", round(row["minimumCapSatMm"], 3),
            "gates", row["allHardGates"],
        )


if __name__ == "__main__":
    main()
