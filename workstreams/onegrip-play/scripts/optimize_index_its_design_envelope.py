"""READ-ONLY constrained INDEX axis refinement for the ITS design envelope.

Centers, external cap/opening datums, split ownership, screw geometry and the
6.4 seat are fixed.  Only small F2-axis perturbations are searched.  The
fixed-root channel uses drawing nominal metal dimensions and the user-approved
rigid-root / one-time-formable-distal policy.  No HTTP or CAD mutation exists.
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
import audit_its1105_primary_switch as channel  # noqa: E402
import audit_stock_6x6_switch as stock  # noqa: E402


DESIGN_X, DESIGN_Y, HOUSING_H = 6.18, 6.12, 3.56
ROBUST_X, ROBUST_Y = 6.20, 6.15
POCKET, SEAT_LENGTH, SEAT_FRONT = 6.40, 6.20, 5.30
HOLDER_WIDTH, HOLDER_FROM, HOLDER_TO = 12.40, 2.80, 12.50
BODY_GATE, BODY_SEARCH_TARGET = 1.20, 1.21
DIVIDER_GATE, SPLIT_GATE = 0.7999, 1.4999
SCREW_GATE, TERMINAL_GATE = 2.50, 1.50
ROLLS = (0, 0, 90, 90)
BASE_AXES = np.asarray([geom.unit(axis) for axis in geom.INDEX_AXES])
BASE_FRAMES = np.asarray([geom.frame(axis) for axis in BASE_AXES])


def perturbed_axis(index: int, tangent_deg: tuple[float, float]):
    p, q = (math.tan(math.radians(value)) for value in tangent_deg)
    u, v, z = BASE_FRAMES[index]
    return geom.unit(z + p * u + q * v)


def deviation_deg(index: int, axis: np.ndarray):
    return math.degrees(math.acos(np.clip(float(np.dot(BASE_AXES[index], axis)), -1.0, 1.0)))


def rolled_frame(axis: np.ndarray, roll_deg: float):
    u0, v0, z = geom.frame(axis)
    theta = math.radians(roll_deg)
    return np.asarray((
        math.cos(theta) * u0 + math.sin(theta) * v0,
        -math.sin(theta) * u0 + math.cos(theta) * v0,
        z,
    ))


def rectangular_box(index: int, axis: np.ndarray, roll_deg: float, sx: float, sy: float,
                    length: float, front: float):
    axes = rolled_frame(axis, roll_deg)
    center = geom.INDEX_CENTERS[index] - axes[2] * (front + length / 2.0)
    return center, axes, np.asarray((sx / 2.0, sy / 2.0, length / 2.0))


def axis_box(index: int, axis: np.ndarray, size: float, length: float, front: float):
    axes = geom.frame(axis)
    center = geom.INDEX_CENTERS[index] - axes[2] * (front + length / 2.0)
    return center, axes, np.asarray((size / 2.0, size / 2.0, length / 2.0))


def lip_min(index: int, axis: np.ndarray, width: float = POCKET):
    point = geom.INDEX_CENTERS[index]
    normal = geom.unit(stock.INDEX_NORMALS[index])
    u, v, z = geom.frame(axis)
    return min(
        -float(np.dot(point - z * SEAT_FRONT + u * x + v * y - point, normal)) - HOLDER_FROM
        for x in (-width / 2.0, width / 2.0)
        for y in (-width / 2.0, width / 2.0)
    )


def individual_metrics(index: int, axis: np.ndarray):
    pocket = axis_box(index, axis, POCKET, SEAT_LENGTH, SEAT_FRONT)
    holder = axis_box(index, axis, HOLDER_WIDTH, HOLDER_TO - HOLDER_FROM, HOLDER_FROM)
    corners = geom.corners(pocket)
    split = float("inf")
    if index == 2:
        split = -float(corners[:, 0].max())
    elif index == 3:
        split = float(corners[:, 0].min())
    screw = min(
        geom.cylinder_gap_x(holder, np.asarray(point), x_range, radius)
        for point, x_range, radius in geom.SCREWS.values()
    )
    return {"pocket": pocket, "holder": holder, "splitMm": split,
            "screwMm": float(screw), "frontLipMm": lip_min(index, axis)}


def pair_metrics(i: int, ai: np.ndarray, j: int, aj: np.ndarray, sx: float, sy: float):
    bi = rectangular_box(i, ai, ROLLS[i], sx, sy, HOUSING_H, SEAT_FRONT)
    bj = rectangular_box(j, aj, ROLLS[j], sx, sy, HOUSING_H, SEAT_FRONT)
    pi = axis_box(i, ai, POCKET, SEAT_LENGTH, SEAT_FRONT)
    pj = axis_box(j, aj, POCKET, SEAT_LENGTH, SEAT_FRONT)
    return float(geom.sat_signed(bi, bj)), float(geom.sat_signed(pi, pj))


def candidates(index: int, span_deg: float = 1.20, step_deg: float = 0.16):
    values = np.arange(-span_deg, span_deg + step_deg / 2.0, step_deg)
    rows = []
    for p in values:
        for q in values:
            axis = perturbed_axis(index, (float(p), float(q)))
            metrics = individual_metrics(index, axis)
            if metrics["screwMm"] < SCREW_GATE - 1e-7:
                continue
            if metrics["frontLipMm"] < 0.80 - 1e-7:
                continue
            if index in (2, 3) and metrics["splitMm"] < SPLIT_GATE - 1e-7:
                continue
            rows.append({
                "axis": axis,
                "paramsDeg": (float(p), float(q)),
                "deviationDeg": deviation_deg(index, axis),
                **metrics,
            })
    rows.sort(key=lambda row: (row["deviationDeg"], abs(row["paramsDeg"][0]) + abs(row["paramsDeg"][1])))
    return rows


def compatible(left_index: int, left, right_index: int, right):
    body, divider = pair_metrics(
        left_index, left["axis"], right_index, right["axis"], DESIGN_X, DESIGN_Y
    )
    return body >= BODY_SEARCH_TARGET - 1e-8 and divider >= DIVIDER_GATE - 1e-8, body, divider


def search():
    pools = [candidates(i) if i < 3 else [{
        "axis": BASE_AXES[i], "paramsDeg": (0.0, 0.0), "deviationDeg": 0.0,
        **individual_metrics(i, BASE_AXES[i]),
    }] for i in range(4)]

    best_i1 = {}
    for i2, row2 in enumerate(pools[1]):
        for i1, row1 in enumerate(pools[0]):
            ok, body, divider = compatible(0, row1, 1, row2)
            if ok:
                best_i1[i2] = (i1, body, divider)
                break

    best = None
    tested = 0
    for i2, row2 in enumerate(pools[1]):
        if i2 not in best_i1:
            continue
        i1, body12, div12 = best_i1[i2]
        row1 = pools[0][i1]
        for i3, row3 in enumerate(pools[2]):
            tested += 1
            ok23, body23, div23 = compatible(1, row2, 2, row3)
            if not ok23:
                continue
            body13, _ = pair_metrics(0, row1["axis"], 2, row3["axis"], DESIGN_X, DESIGN_Y)
            body34, div34 = pair_metrics(2, row3["axis"], 3, BASE_AXES[3], DESIGN_X, DESIGN_Y)
            if min(body13, body34) < BODY_GATE - 1e-8 or div34 < DIVIDER_GATE - 1e-8:
                continue
            axes = [row1["axis"], row2["axis"], row3["axis"], BASE_AXES[3]]
            deviations = [deviation_deg(i, axes[i]) for i in range(4)]
            min_body = min(body12, body23, body13, body34)
            min_divider = min(div12, div23, div34)
            objective = (max(deviations), sum(deviations), -min_body, -min_divider)
            if best is None or objective < best[0]:
                best = (objective, axes, (body12, body23, body13, body34),
                        (div12, div23, div34), deviations,
                        (row1["paramsDeg"], row2["paramsDeg"], row3["paramsDeg"], (0.0, 0.0)))
    return pools, tested, best


def root_boxes(index: int, axis: np.ndarray, roll_deg: float, body_x: float):
    point = geom.INDEX_CENTERS[index]
    u, v, z = rolled_frame(axis, roll_deg)
    rear = SEAT_FRONT + HOUSING_H
    metal_u, metal_v, pitch_v, outer, depth = 0.3, 0.7, 4.5, 7.9, 1.8
    start_u, knee_u = body_x / 2.0 + metal_u / 2.0, (outer - metal_u) / 2.0
    boxes = []
    for su in (-1.0, 1.0):
        for sv in (-1.0, 1.0):
            p0 = point + u * (su * start_u) + v * (sv * pitch_v / 2.0) - z * rear
            p1 = point + u * (su * knee_u) + v * (sv * pitch_v / 2.0) - z * (rear + depth)
            direction = geom.unit(p1 - p0)
            cross_t = geom.unit(np.cross(direction, v))
            boxes.append(((p0 + p1) / 2.0, np.asarray((v, cross_t, direction)),
                          np.asarray((metal_v / 2.0, metal_u / 2.0, np.linalg.norm(p1 - p0) / 2.0))))
    return boxes


def full_metrics(axes, sx: float, sy: float):
    bodies = [rectangular_box(i, axes[i], ROLLS[i], sx, sy, HOUSING_H, SEAT_FRONT) for i in range(4)]
    pockets = [axis_box(i, axes[i], POCKET, SEAT_LENGTH, SEAT_FRONT) for i in range(4)]
    holders = [axis_box(i, axes[i], HOLDER_WIDTH, HOLDER_TO - HOLDER_FROM, HOLDER_FROM) for i in range(4)]
    body = {f"I{i + 1}-I{j + 1}": float(geom.sat_signed(bodies[i], bodies[j])) for i, j in geom.KEY_PAIRS}
    divider = {f"I{i + 1}-I{j + 1}": float(geom.sat_signed(pockets[i], pockets[j])) for i, j in geom.ADJ_PAIRS}
    split = {"I3": -float(geom.corners(pockets[2])[:, 0].max()),
             "I4": float(geom.corners(pockets[3])[:, 0].min())}
    screw = {
        f"I{i + 1}": min(geom.cylinder_gap_x(holders[i], np.asarray(point), xr, radius)
                          for point, xr, radius in geom.SCREWS.values())
        for i in range(4)
    }
    roots = [root_boxes(i, axes[i], ROLLS[i], sx) for i in range(4)]
    rwid, rzkd = geom.load_triangles("INDEX_FINAL_RWID"), geom.load_triangles("INDEX_FINAL_RZKD")
    individual = {}
    static_clear = {}
    for i in range(4):
        ext = channel.local_external_web(i, roots[i])
        spl = channel.split_web(i, roots[i])
        individual[f"I{i + 1}"] = float(min(ext, spl))
        static_clear[f"I{i + 1}"] = not any(
            geom.mesh_box_intersects(rwid, box) or geom.mesh_box_intersects(rzkd, box)
            for box in roots[i]
        ) and stock.screw_collisions(roots[i]) == 0
    root_pairs = {
        f"I{i + 1}-I{j + 1}": float(channel.pair_gap(roots[i], roots[j]))
        for i, j in ((0, 1), (1, 2), (2, 3))
    }
    governing_terminal = min(*individual.values(), *root_pairs.values())
    return {
        "bodySatMm": body,
        "minimumBodySatMm": min(body.values()),
        "dividerSatLowerBoundMm": divider,
        "minimumDividerMm": min(divider.values()),
        "splitWallMm": split,
        "minimumSplitWallMm": min(split.values()),
        "screwClearanceMm": screw,
        "minimumScrewClearanceMm": min(screw.values()),
        "frontLipMm": {f"I{i + 1}": lip_min(i, axes[i]) for i in range(4)},
        "terminalIndividualMarginMm": individual,
        "terminalAdjacentWebMm": root_pairs,
        "minimumTerminalWebMm": governing_terminal,
        "terminalRetainerAndScrewClear": static_clear,
        "symmetricChannelClearanceAt1p50WebMm": max((governing_terminal - TERMINAL_GATE) / 2.0, 0.0),
    }


def main():
    pools, tested, best = search()
    if best is None:
        raise RuntimeError("No <=1.2 degree axis refinement satisfies the design envelope")
    _, axes, _, _, deviations, params = best
    design = full_metrics(axes, DESIGN_X, DESIGN_Y)
    robust = full_metrics(axes, ROBUST_X, ROBUST_Y)
    payload = {
        "method": {
            "mode": "LOCAL READ-ONLY / CAD WRITE 0",
            "centersFixed": True,
            "seatMm": [POCKET, POCKET],
            "rollsDeg": dict(zip(("I1", "I2", "I3", "I4"), ROLLS)),
            "search": "0.16-degree deterministic tangent grid, <=1.20 degree; I4 fixed",
            "bodySearchTargetMm": BODY_SEARCH_TARGET,
            "poolSizes": [len(pool) for pool in pools],
            "testedI2I3Pairs": tested,
        },
        "baseAxes": {f"I{i + 1}": BASE_AXES[i].tolist() for i in range(4)},
        "refinedAxes": {f"I{i + 1}": axes[i].tolist() for i in range(4)},
        "tangentParametersDeg": {f"I{i + 1}": list(params[i]) for i in range(4)},
        "axisDeviationFromFrozenF2Deg": {f"I{i + 1}": deviations[i] for i in range(4)},
        "designEnvelope": {"bodyMm": [DESIGN_X, DESIGN_Y, HOUSING_H], **design},
        "robustnessProbe": {"bodyMm": [ROBUST_X, ROBUST_Y, HOUSING_H], **robust},
        "decision": {
            "designPass": bool(
                design["minimumBodySatMm"] >= BODY_GATE - 1e-7
                and design["minimumDividerMm"] >= DIVIDER_GATE - 1e-7
                and design["minimumSplitWallMm"] >= SPLIT_GATE - 1e-7
                and design["minimumScrewClearanceMm"] >= SCREW_GATE - 1e-7
                and design["minimumTerminalWebMm"] >= TERMINAL_GATE - 1e-7
                and all(design["terminalRetainerAndScrewClear"].values())
            ),
            "robustnessClass": (
                "PASS" if robust["minimumBodySatMm"] >= BODY_GATE
                else "marginal" if robust["minimumBodySatMm"] >= 1.10 else "FAIL"
            ),
            "largeLayoutChangeRequired": False,
        },
    }
    path = ROOT / "cad_dump" / "its1105_index_design_envelope_optimization.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {path}")
    print(json.dumps({
        "axes": payload["refinedAxes"],
        "deviation": payload["axisDeviationFromFrozenF2Deg"],
        "design": {k: design[k] for k in ("minimumBodySatMm", "minimumDividerMm", "minimumSplitWallMm", "minimumScrewClearanceMm", "minimumTerminalWebMm")},
        "robust": robust["minimumBodySatMm"],
        "decision": payload["decision"],
    }, indent=2))


if __name__ == "__main__":
    main()
