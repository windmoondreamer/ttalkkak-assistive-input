"""Deterministic simplified INDEX/MIDDLE carrier study (no CAD or network writes)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
from PIL import ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_middle_prewrite as geom  # noqa: E402
import audit_middle_its1105_design as middle  # noqa: E402
import audit_its1105_physical_sample as physical  # noqa: E402
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402


OUT_JSON = ROOT / "cad_dump" / "simplified_finger_carrier_design.json"
OUT_RENDER = ROOT / "renders" / "simplified_finger_carrier_design.png"
SOURCE = ROOT / "exports" / "thumb_lower15_housing_mockup"
PARTS = ROOT / "exports" / "full_exterior_minimal_mockup" / "source_stl"

INDEX_POINTS = np.asarray(geom.INDEX_CENTERS, dtype=float)
INDEX_AXES = np.asarray([
    (-0.847667872, -0.506166919, -0.158915794),
    (-0.387542111, -0.574231284, -0.721158474),
    (-0.068454195, -0.997609880, 0.009410170),
    (0.024161000, -0.968017000, -0.249718000),
])
MIDDLE_POINTS = np.asarray([
    (-19.835372272, -0.614991709, -11.125000000),
    (-12.899418190, -8.744828192, -14.125000000),
    (-3.537874175, -14.413708840, -11.125000000),
    (7.444327590, -13.569623472, -11.125000000),
])
MIDDLE_AXES = np.asarray([
    (-0.837518998, -0.499950062, -0.220480981),
    (-0.601521153, -0.782846337, -0.159134899),
    (0.320428890, -0.733472608, -0.599452466),
    (0.224859127, -0.772792774, -0.593489428),
])

BACKPLANE_DEPTH = 14.50
POST_SIZE = 3.60
BEAM_WIDTH = 3.20
BEAM_THICKNESS = 4.00
MIDDLE_BODY_REAR = 8.839587617
INDEX_BODY_REAR = 8.86
DOGLEG = np.asarray((-3.181, 5.414, -1.125), dtype=float)


def unit_rows(rows: np.ndarray) -> np.ndarray:
    return rows / np.linalg.norm(rows, axis=1)[:, None]


INDEX_AXES = unit_rows(INDEX_AXES)
MIDDLE_AXES = unit_rows(MIDDLE_AXES)
INDEX_NODES = INDEX_POINTS - INDEX_AXES * BACKPLANE_DEPTH
MIDDLE_NODES = MIDDLE_POINTS - MIDDLE_AXES * BACKPLANE_DEPTH


LINK_DATA = [
    ("JfD I3-to-M3", INDEX_NODES[2], MIDDLE_NODES[2],
     np.asarray((0.211301290, 0.731289520, 0.648511680))),
    ("JfD M3 dogleg A", MIDDLE_NODES[2], DOGLEG,
     np.asarray((-0.843215940, 0.490299570, -0.220438680))),
    ("JfD M3 dogleg B", DOGLEG, MIDDLE_NODES[1],
     np.asarray((0.995963070, -0.022796690, -0.086820900))),
    ("JfD M2-to-M1", MIDDLE_NODES[1], MIDDLE_NODES[0],
     np.asarray((0.847015100, 0.382384410, 0.369252730))),
    ("JaD I4-to-M4", INDEX_NODES[3], MIDDLE_NODES[3],
     np.asarray((0.041113690, 0.761210510, 0.647200300))),
]


def link_boxes():
    return [
        (name, middle.segment_box(p0, p1, x_axis, BEAM_WIDTH, BEAM_THICKNESS))
        for name, p0, p1, x_axis in LINK_DATA
    ]


def body_and_root_boxes():
    index_bodies = [
        physical.physical_body_box(i, (0, 0, 90, 90)[i], physical.BODY_X, physical.BODY_Y)
        for i in range(4)
    ]
    middle_bodies = [
        middle.obb_rect(
            MIDDLE_POINTS[i],
            middle.rotated_axes(MIDDLE_AXES[i], (90, 90, 0, 0)[i]),
            6.18, 6.12, 3.56, 5.279587617,
        )
        for i in range(4)
    ]
    roots = []
    for i in range(4):
        roots.extend(physical.physical_root_boxes(i, (0, 0, 90, 90)[i], physical.BODY_X))
    for i in range(4):
        roots.extend(middle.root_channels(
            MIDDLE_POINTS[i], MIDDLE_AXES[i], (90, 90, 0, 0)[i],
            5.279587617, 12.279587617,
        ))
    return index_bodies + middle_bodies, roots


def post_box(point: np.ndarray, axis: np.ndarray, rear: float):
    return middle.obb_rect(
        point, geom.frame(axis), POST_SIZE, POST_SIZE,
        BACKPLANE_DEPTH - rear + 0.20, rear - 0.10,
    )


def audit():
    bodies, roots = body_and_root_boxes()
    shells = {
        "JfD": read_binary_stl(SOURCE / "OneGrip_lower15_housing_Joystick_2_JfD.stl"),
        "JaD": read_binary_stl(SOURCE / "OneGrip_lower15_housing_Joystick_1_JaD.stl"),
    }
    retainers = {
        "JfD": read_binary_stl(PARTS / "Joystick - Part 17.stl"),
        "JaD": read_binary_stl(PARTS / "Joystick - Part 18.stl"),
    }
    rows = []
    minimum_body = float("inf")
    minimum_root = float("inf")
    minimum_shell = float("inf")
    minimum_screw = float("inf")
    for index, (name, box) in enumerate(link_boxes()):
        body_clearance = min(geom.sat_signed(box, target) for target in bodies)
        root_clearance = min(geom.sat_signed(box, target) for target in roots)
        owner = "JfD" if index < 4 else "JaD"
        shell_hit = geom.mesh_box_intersects(shells[owner], box)
        shell_clearance = 0.0 if shell_hit else geom.mesh_box_distance(shells[owner], box)
        screw = min(
            geom.cylinder_gap_x(box, np.asarray(point), x_range, radius)
            for point, x_range, radius in geom.SCREWS.values()
        )
        minimum_body = min(minimum_body, body_clearance)
        minimum_root = min(minimum_root, root_clearance)
        minimum_shell = min(minimum_shell, shell_clearance)
        minimum_screw = min(minimum_screw, screw)
        rows.append({
            "name": name,
            "bodyClearanceMm": float(body_clearance),
            "terminalRootClearanceMm": float(root_clearance),
            "shellCollision": bool(shell_hit),
            "shellClearanceMm": float(shell_clearance),
            "screwClearanceMm": float(screw),
        })

    anchor_hits = {
        "JfD_RWID": bool(geom.mesh_box_intersects(retainers["JfD"], link_boxes()[0][1])),
        "JaD_RZKD": bool(geom.mesh_box_intersects(retainers["JaD"], link_boxes()[4][1])),
    }
    post_root = {}
    for row_name, points, axes, rear in (
        ("I", INDEX_POINTS, INDEX_AXES, INDEX_BODY_REAR),
        ("M", MIDDLE_POINTS, MIDDLE_AXES, MIDDLE_BODY_REAR),
    ):
        for index in range(4):
            box = post_box(points[index], axes[index], rear)
            post_root[f"{row_name}{index + 1}"] = float(
                min(geom.sat_signed(box, target) for target in roots)
            )

    hard_pass = bool(
        minimum_body > 0.0
        and minimum_root > 0.0
        and minimum_shell >= 0.20
        and minimum_screw >= 2.50
        and min(post_root.values()) >= 1.0
        and all(anchor_hits.values())
    )
    return {
        "scope": "simplified finger internals; THUMB unchanged",
        "cadWrite": 0,
        "architecture": {
            "independentFingerSolidsBefore": 18,
            "independentFingerSolidsAfter": 10,
            "removed": "eight independent spacers",
            "retained": "eight external caps + RWID/RZKD identities",
            "middleShellChange": "remove 0.80-mm beams and 0.70-mm hooks; keep open-rear 6.40-mm seats",
            "carrierChange": "extend RWID and RZKD with central contact posts and two backbones",
        },
        "dimensionsMm": {
            "backplaneDepth": BACKPLANE_DEPTH,
            "contactPost": [POST_SIZE, POST_SIZE],
            "backbone": [BEAM_WIDTH, BEAM_THICKNESS],
            "middlePocket": [6.40, 6.40],
            "commonVisibleCap": [7.60, 7.60],
            "commonCapExposureTarget": 1.40,
            "middleOpeningTarget": [8.00, 8.00],
        },
        "linkAudit": rows,
        "postToTerminalRootClearanceMm": post_root,
        "retainerPositiveOverlap": anchor_hits,
        "minimums": {
            "bodyClearanceMm": float(minimum_body),
            "terminalRootClearanceMm": float(minimum_root),
            "shellClearanceMm": float(minimum_shell),
            "screwClearanceMm": float(minimum_screw),
            "postToTerminalRootClearanceMm": float(min(post_root.values())),
        },
        "hardGatePass": hard_pass,
    }


def carrier_meshes():
    rows = []
    for index, (_, box) in enumerate(link_boxes()):
        rows.append(("JfD" if index < 4 else "JaD", render.obb_triangles(box)))
    for points, axes, rear in (
        (INDEX_POINTS, INDEX_AXES, INDEX_BODY_REAR),
        (MIDDLE_POINTS, MIDDLE_AXES, MIDDLE_BODY_REAR),
    ):
        for index, (point, axis) in enumerate(zip(points, axes)):
            rows.append(("JfD" if index < 3 else "JaD",
                         render.obb_triangles(post_box(point, axis, rear))))
    return rows


def render_design(report):
    explode = 24.0
    jad = read_binary_stl(SOURCE / "OneGrip_lower15_housing_Joystick_1_JaD.stl")
    jfd = read_binary_stl(SOURCE / "OneGrip_lower15_housing_Joystick_2_JfD.stl")
    rwid = read_binary_stl(PARTS / "Joystick - Part 17.stl")
    rzkd = read_binary_stl(PARTS / "Joystick - Part 18.stl")
    objects = [
        (render.shifted(jfd, -explode), (44, 83, 107)),
        (render.shifted(jad, explode), (52, 96, 119)),
        (render.shifted(rwid, -explode), (177, 183, 190)),
        (render.shifted(rzkd, explode), (207, 151, 63)),
    ]
    for owner, mesh in carrier_meshes():
        dx = -explode if owner == "JfD" else explode
        color = (217, 72, 165) if owner == "JfD" else (50, 185, 213)
        objects.append((render.shifted(mesh, dx), color))
    image, _ = render.rasterize(objects)
    draw = ImageDraw.Draw(image)
    draw.text((48, 34), "SIMPLIFIED FINGER INTERNALS / TWO CARRIERS", font=render.font(36, True),
              fill=(241, 246, 249, 255))
    draw.text((50, 80), "8 SPACERS REMOVED / MIDDLE HOOKS REMOVED / POCKETS UNCHANGED",
              font=render.font(19), fill=(181, 199, 211, 255))
    draw.rounded_rectangle((48, render.HEIGHT - 110, 1185, render.HEIGHT - 42), radius=14,
                           fill=(8, 13, 20, 225), outline=(78, 100, 116, 230), width=2)
    draw.text((70, render.HEIGHT - 92),
              "RWID extended carrier", font=render.font(17, True), fill=(226, 91, 181, 255))
    draw.text((330, render.HEIGHT - 92),
              "RZKD extended carrier", font=render.font(17, True), fill=(61, 194, 219, 255))
    draw.text((610, render.HEIGHT - 92),
              f"min shell {report['minimums']['shellClearanceMm']:.3f} mm",
              font=render.font(17), fill=(224, 231, 236, 255))
    draw.text((850, render.HEIGHT - 92),
              "LOCAL STUDY / CAD WRITE 0", font=render.font(17, True), fill=(229, 188, 77, 255))
    OUT_RENDER.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUT_RENDER, quality=96)


def main():
    report = audit()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    render_design(report)
    print(json.dumps(report, indent=2))
    print(f"render -> {OUT_RENDER}")
    if not report["hardGatePass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
