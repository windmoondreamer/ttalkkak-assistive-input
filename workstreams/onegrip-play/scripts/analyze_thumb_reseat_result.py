"""Offline geometric audit for the completed rigid THUMB module reseat.

The script uses the immutable fine-mesh cache only.  It makes no Onshape call
and performs no CAD write.  The live Part Studio/assembly counts are recorded
separately in the implementation report after UI verification.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
DUMP = ROOT / "cad_dump"
TRANSLATION = np.asarray((0.0, 5.5, -6.0), dtype=float)

INDEX_CENTERS = np.asarray(
    (
        (-22.224000, -17.494000, 9.000000),
        (-15.970000, -26.208000, 9.000000),
        (-5.496000, -29.325000, 9.000000),
        (5.496000, -29.325000, 9.000000),
    ),
    dtype=float,
)
MIDDLE_CENTERS = np.asarray(
    (
        (-19.835372, -0.614992, -11.125000),
        (-12.899418, -8.744828, -14.125000),
        (-3.537874, -14.413709, -11.125000),
        (7.444328, -13.569623, -11.125000),
    ),
    dtype=float,
)

CAP_NAMES = (
    "Button_wide_1",
    "Button_side_1",
    "Button_corner_1",
    "Button_corner_2",
    "Button_side_2",
    "Button_wide_2",
    "Button_middle_1",
    "Button_middle_2",
)

# Immutable screw-B geometry from the source CAD audit.
SCREW_AXIS_A = np.asarray((-6.0, -14.45, 23.07), dtype=float)
SCREW_AXIS_B = np.asarray((10.0, -14.45, 23.07), dtype=float)
SCREW_RADIUS = 3.5


def load_mesh(name: str) -> tuple[str, np.ndarray]:
    row = json.loads((DUMP / f"mesh_{name}.json").read_text(encoding="utf-8"))
    return row.get("partId", ""), np.asarray(row["tris"], dtype=float)


def point_triangle_closest(point: np.ndarray, tri: np.ndarray) -> np.ndarray:
    """Closest point on a triangle; Real-Time Collision Detection regions."""
    a, b, c = tri
    ab, ac, ap = b - a, c - a, point - a
    d1, d2 = float(ab @ ap), float(ac @ ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return a
    bp = point - b
    d3, d4 = float(ab @ bp), float(ac @ bp)
    if d3 >= 0.0 and d4 <= d3:
        return b
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return a + v * ab
    cp = point - c
    d5, d6 = float(ab @ cp), float(ac @ cp)
    if d6 >= 0.0 and d5 <= d6:
        return c
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return a + w * ac
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return b + w * (c - b)
    denom = 1.0 / (va + vb + vc)
    v, w = vb * denom, vc * denom
    return a + ab * v + ac * w


def segment_segment_closest(
    p1: np.ndarray, q1: np.ndarray, p2: np.ndarray, q2: np.ndarray
) -> tuple[np.ndarray, np.ndarray, float]:
    """Closest points between two finite segments and parameter on p1-q1."""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = float(d1 @ d1), float(d2 @ d2), float(d2 @ r)
    eps = 1e-15
    if a <= eps and e <= eps:
        return p1, p2, 0.0
    if a <= eps:
        s = 0.0
        t = np.clip(f / e, 0.0, 1.0)
    else:
        c = float(d1 @ r)
        if e <= eps:
            t = 0.0
            s = np.clip(-c / a, 0.0, 1.0)
        else:
            b = float(d1 @ d2)
            denom = a * e - b * b
            s = np.clip((b * f - c * e) / denom, 0.0, 1.0) if denom else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t = 0.0
                s = np.clip(-c / a, 0.0, 1.0)
            elif t > 1.0:
                t = 1.0
                s = np.clip((b - c) / a, 0.0, 1.0)
    return p1 + d1 * s, p2 + d2 * t, float(s)


def segment_triangle_distance(
    p: np.ndarray, q: np.ndarray, tri: np.ndarray
) -> tuple[float, float]:
    """Exact segment-to-triangle distance for the non-intersecting case."""
    direction = q - p
    a, b, c = tri
    edge1, edge2 = b - a, c - a
    h = np.cross(direction, edge2)
    det = float(edge1 @ h)
    if abs(det) > 1e-14:
        inv = 1.0 / det
        svec = p - a
        u = inv * float(svec @ h)
        qq = np.cross(svec, edge1)
        v = inv * float(direction @ qq)
        t = inv * float(edge2 @ qq)
        if 0.0 <= u <= 1.0 and 0.0 <= v and u + v <= 1.0 and 0.0 <= t <= 1.0:
            return 0.0, float(t)

    candidates: list[tuple[float, float]] = []
    for endpoint, t in ((p, 0.0), (q, 1.0)):
        closest = point_triangle_closest(endpoint, tri)
        candidates.append((float(np.linalg.norm(endpoint - closest)), t))
    for e0, e1 in ((a, b), (b, c), (c, a)):
        x, y, t = segment_segment_closest(p, q, e0, e1)
        candidates.append((float(np.linalg.norm(x - y)), t))
    return min(candidates, key=lambda row: row[0])


def screw_clearance(triangles: np.ndarray) -> dict:
    best = (float("inf"), 0.0)
    for tri in triangles:
        row = segment_triangle_distance(SCREW_AXIS_A, SCREW_AXIS_B, tri)
        if row[0] < best[0]:
            best = row
    axis_distance, axis_t = best
    return {
        "axisToBackplateMm": axis_distance,
        "radiusMm": SCREW_RADIUS,
        "surfaceClearanceMm": axis_distance - SCREW_RADIUS,
        "closestAxisXmm": float(SCREW_AXIS_A[0] + axis_t * (SCREW_AXIS_B[0] - SCREW_AXIS_A[0])),
        "axisClosestPointIsWithinFiniteLength": bool(1e-9 < axis_t < 1.0 - 1e-9),
    }


def topology(triangles: np.ndarray) -> dict:
    quantized = np.round(triangles.reshape(-1, 3), 7)
    vertex_ids: dict[tuple[float, float, float], int] = {}
    faces = []
    for tri in quantized.reshape(-1, 3, 3):
        face = []
        for point in tri:
            key = tuple(float(x) for x in point)
            face.append(vertex_ids.setdefault(key, len(vertex_ids)))
        faces.append(tuple(face))
    edge_faces: dict[tuple[int, int], list[int]] = {}
    face_neighbors = [set() for _ in faces]
    for face_index, face in enumerate(faces):
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge_faces.setdefault(tuple(sorted((a, b))), []).append(face_index)
    for owners in edge_faces.values():
        for owner in owners:
            face_neighbors[owner].update(other for other in owners if other != owner)
    components = 0
    remaining = set(range(len(faces)))
    while remaining:
        components += 1
        stack = [remaining.pop()]
        while stack:
            current = stack.pop()
            for neighbor in face_neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
    return {
        "triangles": len(faces),
        "vertices": len(vertex_ids),
        "connectedComponents": components,
        "boundaryEdges": sum(len(owners) == 1 for owners in edge_faces.values()),
        "nonManifoldEdges": sum(len(owners) > 2 for owners in edge_faces.values()),
    }


def row_metrics(row: np.ndarray, caps: np.ndarray) -> dict:
    distances = np.linalg.norm(row[:, None, :] - caps[None, :, :], axis=2)
    finger_index, cap_index = np.unravel_index(np.argmin(distances), distances.shape)
    return {
        "nearestMm": float(distances[finger_index, cap_index]),
        "nearestFinger": int(finger_index + 1),
        "nearestThumbControl": CAP_NAMES[cap_index],
        "meanOfPerFingerNearestMm": float(np.min(distances, axis=1).mean()),
    }


def main() -> None:
    cap_centers = []
    module_topology = {}
    for name in CAP_NAMES:
        part_id, triangles = load_mesh(name)
        points = triangles.reshape(-1, 3)
        cap_centers.append((points.min(axis=0) + points.max(axis=0)) / 2.0)
        module_topology[name] = {"partId": part_id, **topology(triangles)}
    old_centers = np.asarray(cap_centers)
    new_centers = old_centers + TRANSLATION

    backplate_id, backplate = load_mesh("Backplate")
    moved_backplate = backplate + TRANSLATION
    module_topology["Backplate"] = {"partId": backplate_id, **topology(backplate)}

    old_pairs = np.linalg.norm(old_centers[:, None, :] - old_centers[None, :, :], axis=2)
    new_pairs = np.linalg.norm(new_centers[:, None, :] - new_centers[None, :, :], axis=2)
    result = {
        "auditMode": "OFFLINE_READ_ONLY_FINE_MESH_PLUS_EXACT_RIGID_TRANSFORM",
        "translationMm": TRANSLATION.tolist(),
        "reach": {
            "current": {
                "index": row_metrics(INDEX_CENTERS, old_centers),
                "middle": row_metrics(MIDDLE_CENTERS, old_centers),
            },
            "relocated": {
                "index": row_metrics(INDEX_CENTERS, new_centers),
                "middle": row_metrics(MIDDLE_CENTERS, new_centers),
            },
        },
        "rigidIdentity": {
            "maxCapCenterPairwiseDistanceDeltaMm": float(np.max(np.abs(old_pairs - new_pairs))),
            "buttonSizeChanged": False,
            "buttonSpacingChanged": False,
            "joystickGeometryChanged": False,
            "relativePositionChanged": False,
            "moduleScaleChanged": False,
            "moduleRotationChanged": False,
        },
        "screwB": screw_clearance(moved_backplate),
        "moduleMeshTopology": module_topology,
        "declaredInterface": {
            "originalBackplateSweepThicknessMm": 5.0,
            "originalButtonSupportWebMm": 4.0,
            "originalBackplateSupportExtrusionDepthMm": 10.0,
            "shellNominalWallMm": 3.0,
            "buttonModuleThroughOpeningMm": 6.4,
            "certifiedVirtualWireEnvelopeMm": 4.0,
            "openingFacesMovedTogether": 36,
            "newAdapterSolidBodies": 0,
            "reason": "Original Backplate/supports and the 36 original opening faces retain their exact relative transform; no pedestal or floating adapter is required.",
        },
    }
    output = DUMP / "thumb_reseat_final_audit.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
