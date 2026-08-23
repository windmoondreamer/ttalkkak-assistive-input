"""Local geometry audit for the approved ITS-1105 MIDDLE implementation.

This is a deterministic, network-free design-envelope calculation.  It uses
the frozen h3p1_w1 centers/axes, the conservative measured-switch envelope,
and the live/frozen INDEX keep-out caches.  CAD creation is performed by a
separate atomic runner only after this file reports every hard gate as PASS.
"""
from __future__ import annotations

import json
import itertools
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_middle_low_profile as middle  # noqa: E402
import analyze_middle_prewrite as geom  # noqa: E402
import audit_stock_6x6_switch as stock  # noqa: E402


NAMES = ("M1", "M2", "M3", "M4")
BODY_X = 6.18
BODY_Y = 6.12
BODY_H = 3.56
POCKET = 6.40
ACTUATOR_PROJECTION = 2.44
ACTUATOR_DIAMETER = 3.35
CAP = 8.00
CAP_OPENING = 8.40
CAP_STOP_TRAVEL = 0.45
CAP_FREE_NORMAL = 0.05
# 10.0 leaves a structural 0.80 mm annulus outside the 8.40 cap guide.
# M3/M4 are split-trimmed in FeatureScript before union.
OUTER_SUPPORT = 10.00
TRIM_DEPTH = 2.80
SUPPORT_FROM = 2.20
SPACER = 2.44
ROOT_DEPTH = 1.80
ROOT_OUTER = 7.90
ROOT_PITCH = 4.50
METAL_U = 0.30
METAL_V = 0.70
CHANNEL_CLEARANCE = 0.08
ROLL_SEEDS = (0, 90)
KEY_PAIRS = ((0, 1), (1, 2), (0, 2), (2, 3))
ADJ_PAIRS = ((0, 1), (1, 2), (2, 3))


def obb_rect(point, axes, width_u, width_v, length, front):
    axes = np.asarray(axes, dtype=float)
    center = np.asarray(point, dtype=float) - axes[2] * (front + length / 2.0)
    return center, axes, np.asarray((width_u / 2.0, width_v / 2.0, length / 2.0))


def rotated_axes(axis, roll_deg):
    base = geom.frame(axis)
    angle = math.radians(roll_deg)
    u = math.cos(angle) * base[0] + math.sin(angle) * base[1]
    v = -math.sin(angle) * base[0] + math.cos(angle) * base[1]
    return np.asarray((u, v, base[2]))


def segment_box(p0, p1, x_axis, width_x, width_y):
    direction = geom.unit(p1 - p0)
    axes = np.asarray((geom.unit(x_axis), geom.unit(np.cross(direction, x_axis)), direction))
    return (p0 + p1) / 2.0, axes, np.asarray((width_x / 2.0, width_y / 2.0, np.linalg.norm(p1 - p0) / 2.0))


def root_channels(point, axis, roll_deg, body_front, channel_to):
    axes = rotated_axes(axis, roll_deg)
    rear = body_front + BODY_H
    start_u = BODY_X / 2.0 + METAL_U / 2.0
    knee_u = (ROOT_OUTER - METAL_U) / 2.0
    width_v = METAL_V + 2.0 * CHANNEL_CLEARANCE
    width_t = METAL_U + 2.0 * CHANNEL_CLEARANCE
    rows = []
    for sign_u in (-1.0, 1.0):
        for sign_v in (-1.0, 1.0):
            p0 = point + axes[0] * (sign_u * start_u) + axes[1] * (sign_v * ROOT_PITCH / 2.0) - axes[2] * (rear - 0.10)
            p1 = point + axes[0] * (sign_u * knee_u) + axes[1] * (sign_v * ROOT_PITCH / 2.0) - axes[2] * (rear + ROOT_DEPTH)
            p2 = point + axes[0] * (sign_u * knee_u) + axes[1] * (sign_v * ROOT_PITCH / 2.0) - axes[2] * channel_to
            root_dir = geom.unit(p1 - p0)
            rows.append(segment_box(p0, p1 + root_dir * 0.20, axes[1], width_v, width_t))
            rows.append(segment_box(p1 + axes[2] * 0.20, p2, axes[1], width_v, width_t))
    return rows


def support_boxes(point, axis, body_front, index=None):
    """Conservative OBB proxies for the ring and two rear snap beams/hooks."""
    u, v, z = geom.frame(axis)
    rear = body_front + BODY_H
    spacer_rear = rear + SPACER
    # The ring proxy deliberately includes the 6.4 pocket void.  This makes
    # INDEX/screw clearance conservative; actual CAD subtracts the passage.
    ring = obb_rect(point, (u, v, z), OUTER_SUPPORT, OUTER_SUPPORT, rear + 0.40 - SUPPORT_FROM, SUPPORT_FROM)
    rows = [ring]
    for sign in (-1.0, 1.0):
        rail_u = sign * 4.60
        hook_u = sign * 2.75
        if index == 2 and sign > 0:
            rail_u = 3.20
        if index == 3 and sign < 0:
            rail_u = -3.80
            hook_u = -2.50
        rail_center = point + u * rail_u
        rows.append(obb_rect(rail_center, (u, v, z), 0.80, 3.20, spacer_rear + 0.40 - SUPPORT_FROM, SUPPORT_FROM))
        hook_center = point + u * hook_u
        rows.append(obb_rect(hook_center, (u, v, z), 3.10, 3.20, 0.70, spacer_rear))
    if index == 2:
        anchor_center = point - u * 4.40
        rows.append(obb_rect(anchor_center, (u, v, z), 1.60, 1.60, 2.40, 1.20))
    return rows


def component_clearance(boxes, components):
    rows = {}
    global_min = (float("inf"), None, None)
    collision_count = 0
    for box_index, box in enumerate(boxes):
        rows[str(box_index)] = {}
        for name, mesh in components.items():
            hit = geom.mesh_box_intersects(mesh, box)
            distance = 0.0 if hit else geom.mesh_box_distance(mesh, box)
            collision_count += int(hit)
            rows[str(box_index)][name] = {"collision": bool(hit), "clearanceMm": float(distance)}
            if distance < global_min[0]:
                global_min = (distance, box_index, name)
    return {
        "perProxy": rows,
        "collisionCount": collision_count,
        "minimum": {"clearanceMm": float(global_min[0]), "proxyIndex": global_min[1], "component": global_min[2]},
    }


def select_rolls(points, axes, body_front, channel_to):
    """Select the best exact-pocket cardinal combination for terminal web."""
    rows = []
    for rolls in itertools.product(ROLL_SEEDS, repeat=4):
        roots = [root_channels(points[i], axes[i], rolls[i], body_front, channel_to) for i in range(4)]
        bodies = [
            obb_rect(points[i], rotated_axes(axes[i], rolls[i]), BODY_X, BODY_Y, BODY_H, body_front)
            for i in range(4)
        ]
        pair_web = {
            f"{NAMES[i]}-{NAMES[j]}": min(geom.sat_signed(a, b) for a in roots[i] for b in roots[j])
            for i, j in KEY_PAIRS
        }
        body_sat = {
            f"{NAMES[i]}-{NAMES[j]}": geom.sat_signed(bodies[i], bodies[j])
            for i, j in KEY_PAIRS
        }
        root_body = min(
            geom.sat_signed(root, bodies[j])
            for i in range(4) for j in range(4) if i != j for root in roots[i]
        )
        feasible = min(body_sat.values()) >= 1.20 - 1e-9 and root_body > 0.0
        rows.append({
            "rollsDeg": rolls,
            "betweenButtonTerminalWebMm": pair_web,
            "minimumBetweenButtonTerminalWebMm": min(pair_web.values()),
            "bodySatMm": body_sat,
            "minimumBodySatMm": min(body_sat.values()),
            "minimumRootToOtherBodyMm": root_body,
            "feasibleBodyAndRoot": feasible,
        })
    ranked = sorted(
        rows,
        key=lambda row: (
            row["feasibleBodyAndRoot"],
            row["minimumBetweenButtonTerminalWebMm"],
            row["minimumBodySatMm"],
            tuple(-value for value in row["rollsDeg"]),
        ),
        reverse=True,
    )
    return ranked[0], rows


def main():
    source = json.loads((ROOT / "cad_dump" / "h3p1_w1.json").read_text(encoding="utf-8"))
    points = np.asarray([source["centers"][name] for name in NAMES], dtype=float)
    normals = np.asarray([source["surfaceNormals"][name] for name in NAMES], dtype=float)
    axes = np.asarray([geom.unit(source["axisSolution"]["axes"][name]) for name in NAMES])

    # A square 6.18 broad phase certifies every possible mapping of the
    # measured 6.18 x 6.12 envelope.  Exact roll-oriented boxes are reported too.
    middle.FOOTPRINT = BODY_X
    middle.POCKET = POCKET
    front_lip = max(middle.required_front_lip(normals[i], axes[i]) for i in range(4))
    body_front = middle.front_depth(front_lip)
    body_rear = body_front + BODY_H
    spacer_rear = body_rear + SPACER
    channel_to = spacer_rear + 1.0

    roll_selection, roll_candidates = select_rolls(points, axes, body_front, channel_to)
    rolls = roll_selection["rollsDeg"]

    conservative_bodies = [geom.obb(points[i], axes[i], BODY_X, BODY_H, body_front) for i in range(4)]
    exact_body_boxes = [
        obb_rect(points[i], rotated_axes(axes[i], rolls[i]), BODY_X, BODY_Y, BODY_H, body_front)
        for i in range(4)
    ]
    pockets = [geom.obb(points[i], axes[i], POCKET, BODY_H + 0.20, body_front) for i in range(4)]
    cap_boxes = [obb_rect(points[i], geom.frame(normals[i]), CAP, CAP, 0.20, -0.10) for i in range(4)]
    roots = [root_channels(points[i], axes[i], rolls[i], body_front, channel_to) for i in range(4)]
    supports = [support_boxes(points[i], axes[i], body_front, i) for i in range(4)]

    conservative_sat = {f"{NAMES[i]}-{NAMES[j]}": float(geom.sat_signed(conservative_bodies[i], conservative_bodies[j])) for i, j in KEY_PAIRS}
    exact_sat = {f"{NAMES[i]}-{NAMES[j]}": float(geom.sat_signed(exact_body_boxes[i], exact_body_boxes[j])) for i, j in KEY_PAIRS}
    dividers = {f"{NAMES[i]}-{NAMES[j]}": float(geom.sat_signed(pockets[i], pockets[j])) for i, j in ADJ_PAIRS}
    split = {
        "JfD_M3": -float(geom.corners(pockets[2])[:, 0].max()),
        "JaD_M4": float(geom.corners(pockets[3])[:, 0].min()),
    }
    cap_gaps = {f"{NAMES[i]}-{NAMES[i + 1]}": float(geom.sat_signed(cap_boxes[i], cap_boxes[i + 1])) for i in range(3)}

    channel_pairs = {}
    for i, j in KEY_PAIRS:
        channel_pairs[f"{NAMES[i]}-{NAMES[j]}"] = min(geom.sat_signed(a, b) for a in roots[i] for b in roots[j])
    internal_channel_web = min(
        geom.sat_signed(roots[i][a], roots[i][b])
        for i in range(4) for a in range(len(roots[i])) for b in range(a + 1, len(roots[i]))
        if not ({a, b} in ({0, 1}, {2, 3}, {4, 5}, {6, 7}))
    )
    terminal_web = min(*channel_pairs.values(), internal_channel_web)

    screw_rows = {}
    for i in range(4):
        values = []
        for box in supports[i]:
            values.extend(
                geom.cylinder_gap_x(box, np.asarray(point), x_range, radius)
                for point, x_range, radius in geom.SCREWS.values()
            )
        screw_rows[NAMES[i]] = min(values)

    support_ownership = {
        "JfD_M3_mm": min(
            0.50,
            *(-float(geom.corners(box)[:, 0].max()) for box in supports[2][1:]),
        ),
        "JaD_M4_mm": min(
            0.50,
            *(float(geom.corners(box)[:, 0].min()) for box in supports[3][1:]),
        ),
    }

    components = {
        "INDEX_shell_keepout": geom.load_triangles("INDEX_FINAL_SHELL_KEEPOUT"),
        "RWID_live": geom.load_triangles("ITS_LIVE_RWID"),
        "RZKD_live": geom.load_triangles("ITS_LIVE_RZKD"),
    }
    clearance = {NAMES[i]: component_clearance(supports[i], components) for i in range(4)}
    clearance_min = min((row["minimum"]["clearanceMm"], name, row["minimum"]) for name, row in clearance.items())
    collision_count = sum(row["collisionCount"] for row in clearance.values())

    cosines = [float(np.dot(normals[i], axes[i])) for i in range(4)]
    usable_actuator = [(CAP_STOP_TRAVEL - CAP_FREE_NORMAL) * cosine for cosine in cosines]
    actuator_top = body_front - ACTUATOR_PROJECTION

    hard_pass = bool(
        min(conservative_sat.values()) >= 1.20 - 1e-9
        and min(dividers.values()) >= 0.80 - 1e-9
        and min(split.values()) >= 1.50 - 1e-9
        and min(support_ownership.values()) >= 0.50 - 1e-9
        and terminal_web >= 1.50 - 1e-9
        and min(screw_rows.values()) >= 2.50 - 1e-9
        and collision_count == 0
        and clearance_min[0] >= 0.50 - 1e-9
        and min(cap_gaps.values()) > 0.0
        and min(usable_actuator) >= 0.35 - 1e-9
    )

    payload = {
        "method": "local analytic OBB/SAT + exact triangle-to-OBB distance; no network; no CAD write",
        "sourceCandidate": "h3p1_w1",
        "designEnvelopeMm": [BODY_X, BODY_Y, BODY_H],
        "centers": {NAMES[i]: points[i].tolist() for i in range(4)},
        "surfaceNormals": {NAMES[i]: normals[i].tolist() for i in range(4)},
        "axes": {NAMES[i]: axes[i].tolist() for i in range(4)},
        "rollsDeg": dict(zip(NAMES, rolls)),
        "cardinalRollSelection": roll_selection,
        "cardinalRollCandidates": roll_candidates,
        "frontLipMm": front_lip,
        "bodyFrontDepthMm": body_front,
        "bodyRearDepthMm": body_rear,
        "spacerThicknessMm": SPACER,
        "spacerRearDepthMm": spacer_rear,
        "channelRearDepthMm": channel_to,
        "pocketSideClearanceMm": [(POCKET - BODY_X) / 2.0, (POCKET - BODY_Y) / 2.0],
        "bodySatConservative6p18SquareMm": conservative_sat,
        "bodySatExact6p18x6p12Mm": exact_sat,
        "minimumBodySatConservativeMm": min(conservative_sat.values()),
        "dividerMm": dividers,
        "minimumDividerMm": min(dividers.values()),
        "splitWallMm": split,
        "minimumSplitWallMm": min(split.values()),
        "supportSplitOwnershipMm": support_ownership,
        "terminalChannelWebMm": {"betweenButtons": channel_pairs, "withinButton": internal_channel_web, "minimum": terminal_web},
        "screwClearanceMm": screw_rows,
        "minimumScrewClearanceMm": min(screw_rows.values()),
        "indexClearance": {"perButton": clearance, "minimum": {"clearanceMm": clearance_min[0], "button": clearance_min[1], **clearance_min[2]}, "collisionCount": collision_count},
        "cap": {"nominalMm": CAP, "openingMm": CAP_OPENING, "pairGapMm": cap_gaps, "minimumPairGapMm": min(cap_gaps.values()), "axisNormalCosine": dict(zip(NAMES, cosines)), "freeNormalMm": CAP_FREE_NORMAL, "stopTravelNormalMm": CAP_STOP_TRAVEL, "usableActuatorTravelMm": dict(zip(NAMES, usable_actuator)), "minimumUsableActuatorTravelMm": min(usable_actuator), "actuatorTopDepthMm": actuator_top, "actuatorDiameterMm": ACTUATOR_DIAMETER},
        "rearSupport": "two integrated side snap beams/hooks plus independent 3.6 mm diameter spacer; rigid roots exit outside the central hook corridor",
        "hardGatePass": hard_pass,
    }
    output = ROOT / "cad_dump" / "its1105_middle_design_audit.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if not hard_pass:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
