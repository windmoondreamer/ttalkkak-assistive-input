"""Rebuild a low-memory SZH-EK056 / black-PCB KY-023 packaging reference.

This is an independent web/photo reference.  It never imports or modifies any
OneGrip production geometry.  Exact internal mechanics are intentionally out of
scope; the result is for packaging, mounting-hole prototyping and coarse clearance.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from build123d import Align, Axis, Box, Compound, Cone, Cylinder, Location, Shape, Sphere, export_step
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation
from OCP.TopLoc import TopLoc_Location
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
STEP_PATH = ROOT / "local_cad" / "reference" / "SZH_EK056_WEB_REFERENCE.step"
JSON_PATH = ROOT / "local_cad" / "reference" / "SZH_EK056_WEB_REFERENCE.json"
RENDER_DIR = ROOT / "renders" / "szh_ek056_web_reference"

# ---------------------------------------------------------------- dimensions
# Datum: PCB centre in X/Y; PCB top surface Z=0; +X away from header; +Y to
# the upper mounting-hole row in the recovered top photograph.

PCB_X = 34.5
# source: SZH-EK056 reseller listing (34.5 x 26 x 38 mm)
# confidence: MEDIUM (SKU-linked source dimension, not a controlled drawing)
PCB_Y = 26.0
# source: SZH-EK056 reseller listing and visually matching KY-023 documents
# confidence: MEDIUM
PCB_T = 1.6
# source: common FR4 module construction / prior comparable reference
# confidence: LOW-MEDIUM

MOUNT_HOLE_D = 3.0
# source: rectified top/bottom photographs; practical 0.5 mm class
# confidence: MEDIUM
MOUNT_HOLE_CENTRES = ((-12.0, 9.95), (14.5, 9.95), (-12.0, -9.5), (14.5, -9.5))
# source: two independent, visually matching ProtoSupplies top/bottom photographs
# confidence: MEDIUM; PHOTO-DERIVED
MOUNT_PITCH_X = 26.5
MOUNT_PITCH_Y = 19.45

JOY_X = 0.4
JOY_Y = 2.0
# source: top-photo homography
# confidence: MEDIUM; PHOTO-DERIVED

GIMBAL_X = 17.5
GIMBAL_Y = 16.6
GIMBAL_H = 11.0
# plan source: top-photo homography; height source: visual side-photo proxy
# confidence: plan MEDIUM, height LOW

X_POT_X = 5.2
X_POT_Y = 13.2
X_POT_H = 8.5
X_POT_CENTRE = (11.1, 2.0)
# source: right-hand housing in rectified top photograph
# confidence: plan MEDIUM, height LOW

Y_POT_X = 10.5
Y_POT_Y = 5.0
Y_POT_H = 8.5
Y_POT_CENTRE = (0.5, 10.6)
# source: upper housing in rectified top photograph (partially boot-obscured)
# confidence: plan LOW-MEDIUM, height LOW

PUSH_X = 10.5
PUSH_Y = 7.0
PUSH_H = 5.0
PUSH_CENTRE = (0.5, -9.2)
# source: lower white/metal push-switch housing in top photograph
# confidence: plan MEDIUM, height LOW

HEADER_PIN_COUNT = 5
HEADER_PITCH = 2.54
HEADER_PIN_D = 0.64
HEADER_X_MIN = -23.2
HEADER_X_MAX = -14.4
HEADER_Y_CENTRE = -0.25
HEADER_Z_CENTRE = 2.0
# source: pin count/pitch are standard-interface source facts; placement is photo-derived
# confidence: count/pitch HIGH, 3D bend envelope LOW-MEDIUM

PIVOT_Z = 11.5
SHAFT_D = 4.8
SHAFT_TOP_Z = 25.0
CAP_MAX_D = 22.0
OVERALL_TOP_Z = 38.0
MAX_TILT_DEG = 25.0
# source: 38 mm from SZH-EK056 reseller listing; remaining shaft/pivot/tilt values are
# packaging inferences from side photographs and the PS2-class mechanism family
# confidence: overall height MEDIUM, shaft/pivot/tilt LOW

STATIC_BASE_MIN = (-23.3, -13.0, -2.8)
STATIC_BASE_MAX = (17.25, 13.0, 12.8)
# source: nominal model extents plus visible solder/pin allowance
# confidence: MEDIUM for plan, LOW-MEDIUM for Z


def moved(shape: Shape, x: float, y: float, z: float) -> Shape:
    return shape.moved(Location((x, y, z)))


def labelled(shape: Shape, label: str) -> Shape:
    shape.label = label
    return shape


def box_at(sx: float, sy: float, sz: float, x: float, y: float, z0: float, label: str) -> Shape:
    return labelled(
        moved(Box(sx, sy, sz, align=(Align.CENTER, Align.CENTER, Align.MIN)), x, y, z0),
        label,
    )


def build_reference() -> tuple[Compound, dict[str, Shape], Shape, Shape]:
    pcb = moved(Box(PCB_X, PCB_Y, PCB_T, align=(Align.CENTER, Align.CENTER, Align.MIN)), 0, 0, -PCB_T)
    for x, y in MOUNT_HOLE_CENTRES:
        cutter = moved(Cylinder(MOUNT_HOLE_D / 2.0, PCB_T + 0.4, align=(Align.CENTER, Align.CENTER, Align.MIN)), x, y, -PCB_T - 0.2)
        pcb = pcb - cutter
    pcb = labelled(pcb.clean(), "PCB_34P5_X_26_PHOTO_PATTERN")

    gimbal = box_at(GIMBAL_X, GIMBAL_Y, GIMBAL_H, JOY_X, JOY_Y, 0.0, "CENTRAL_GIMBAL_ENVELOPE")
    x_pot = box_at(X_POT_X, X_POT_Y, X_POT_H, *X_POT_CENTRE, 0.0, "X_AXIS_POT_HOUSING")
    y_pot = box_at(Y_POT_X, Y_POT_Y, Y_POT_H, *Y_POT_CENTRE, 0.0, "Y_AXIS_POT_HOUSING")
    push = box_at(PUSH_X, PUSH_Y, PUSH_H, *PUSH_CENTRE, 0.0, "PUSH_SWITCH_HOUSING")

    shaft = labelled(
        moved(Cylinder(SHAFT_D / 2.0, SHAFT_TOP_Z - GIMBAL_H, align=(Align.CENTER, Align.CENTER, Align.MIN)), JOY_X, JOY_Y, GIMBAL_H),
        "JOYSTICK_SHAFT_INFERRED",
    )
    cap_lower = moved(Cone(CAP_MAX_D / 2.0, 7.8, 11.0, align=(Align.CENTER, Align.CENTER, Align.MIN)), JOY_X, JOY_Y, 17.0)
    cap_top = moved(Sphere(8.0), JOY_X, JOY_Y, 30.0)
    cap = labelled((cap_lower + cap_top).clean(), "REMOVABLE_CAP_NOMINAL_ENVELOPE")

    header_body = box_at(2.6, 12.4, 3.0, -15.7, HEADER_Y_CENTRE, 0.0, "HEADER_INSULATOR")
    pins = []
    pin_x = (HEADER_X_MIN + HEADER_X_MAX) / 2.0
    pin_len = HEADER_X_MAX - HEADER_X_MIN
    for index in range(HEADER_PIN_COUNT):
        y = HEADER_Y_CENTRE + (index - 2) * HEADER_PITCH
        pin = Cylinder(HEADER_PIN_D / 2.0, pin_len, align=(Align.CENTER, Align.CENTER, Align.CENTER)).rotate(Axis.Y, 90)
        pins.append(labelled(moved(pin, pin_x, y, HEADER_Z_CENTRE), f"HEADER_PIN_{index + 1}"))
    header = labelled(Compound(children=[header_body, *pins]), "HEADER_1X5_2P54_ENVELOPE")

    parts = {
        "pcb": pcb,
        "gimbal": gimbal,
        "x_pot": x_pot,
        "y_pot": y_pot,
        "push_switch": push,
        "shaft": shaft,
        "cap": cap,
        "header": header,
    }
    nominal = labelled(Compound(children=list(parts.values())), "NOMINAL_REFERENCE")

    bx0, by0, bz0 = STATIC_BASE_MIN
    bx1, by1, bz1 = STATIC_BASE_MAX
    static_base = box_at(bx1 - bx0, by1 - by0, bz1 - bz0, (bx0 + bx1) / 2.0, 0.0, bz0, "STATIC_BASE_BOUND")
    static_handle = labelled(
        moved(Cylinder(CAP_MAX_D / 2.0, OVERALL_TOP_Z - PIVOT_Z, align=(Align.CENTER, Align.CENTER, Align.MIN)), JOY_X, JOY_Y, PIVOT_Z),
        "STATIC_NEUTRAL_HANDLE_BOUND",
    )
    static_envelope = labelled(Compound(children=[static_base, static_handle]), "STATIC_CLEARANCE_ENVELOPE")

    # Axisymmetric sweep approximation for all azimuths to MAX_TILT_DEG.  Radii
    # are local neutral-profile radius + axial travel*sin(tilt), not an arbitrary box.
    sweep_a = moved(Cone(4.5, 13.5, 10.0, align=(Align.CENTER, Align.CENTER, Align.MIN)), JOY_X, JOY_Y, PIVOT_Z)
    sweep_b = moved(Cone(13.5, 16.8, 9.0, align=(Align.CENTER, Align.CENTER, Align.MIN)), JOY_X, JOY_Y, PIVOT_Z + 10.0)
    sweep_c = moved(Cone(16.8, 19.3, OVERALL_TOP_Z - PIVOT_Z - 19.0, align=(Align.CENTER, Align.CENTER, Align.MIN)), JOY_X, JOY_Y, PIVOT_Z + 19.0)
    moving_envelope = labelled((sweep_a + sweep_b + sweep_c).clean(), "MOVING_CLEARANCE_ENVELOPE_25DEG_INFERRED")

    reference = labelled(Compound(children=[nominal, static_envelope, moving_envelope]), "SZH_EK056_WEB_REFERENCE")
    return reference, parts, static_envelope, moving_envelope


# -------------------------------------------------------------- raster render

def unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n < 1.0e-12:
        raise ValueError("zero camera vector")
    return v / n


def triangles(shape: Shape, tolerance: float = 0.22, angular: float = 0.12) -> np.ndarray:
    shape.mesh(tolerance, angular)
    rows = []
    for face in shape.faces():
        loc = TopLoc_Location()
        poly = BRep_Tool.Triangulation_s(face.wrapped, loc)
        if poly is None:
            continue
        tr = loc.Transformation()
        points = [poly.Node(i).Transformed(tr) for i in range(1, poly.NbNodes() + 1)]
        reverse = face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
        for tri in poly.Triangles():
            ids = [tri.Value(i) - 1 for i in (1, 2, 3)]
            if reverse:
                ids[1], ids[2] = ids[2], ids[1]
            rows.append([[points[j].X(), points[j].Y(), points[j].Z()] for j in ids])
    return np.asarray(rows, dtype=float)


def font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def render_scene(
    path: Path,
    solids: list[tuple[np.ndarray, tuple[int, int, int]]],
    camera_offset: tuple[float, float, float],
    title: str,
    subtitle: str,
    transparent: list[tuple[np.ndarray, tuple[int, int, int, int]]] | None = None,
    up_hint: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> None:
    width, height, ss = 1400, 960, 2
    w, h = width * ss, height * ss
    all_rows = [*solids, *[(mesh, color[:3]) for mesh, color in (transparent or [])]]
    fit = np.concatenate([mesh.reshape(-1, 3) for mesh, _ in all_rows])
    target = 0.5 * (fit.min(axis=0) + fit.max(axis=0))
    camera = target + np.asarray(camera_offset, float)
    forward = unit(target - camera)
    hint = unit(np.asarray(up_hint, float))
    right = unit(np.cross(forward, hint))
    up = unit(np.cross(right, forward))
    rel = fit - camera
    px = rel @ right
    py = rel @ up
    scale = min(w * 0.82 / max(float(np.ptp(px)), 1.0), h * 0.70 / max(float(np.ptp(py)), 1.0))
    ox = w / 2.0 - scale * float(px.min() + px.max()) / 2.0
    oy = h / 2.0 + scale * float(py.min() + py.max()) / 2.0 + 30.0

    grad = np.linspace(0.0, 1.0, h)[:, None, None]
    bg = np.repeat(((1.0 - grad) * np.array([8, 14, 21]) + grad * np.array([26, 37, 49])).astype(np.uint8), w, axis=1)
    image = Image.fromarray(bg, "RGB").convert("RGBA")
    light = unit(np.asarray((0.2, -0.45, 0.87), float))
    polys = []
    for mesh, base in solids:
        r = mesh - camera
        xx = r @ right * scale + ox
        yy = -(r @ up) * scale + oy
        depth = np.mean(r @ forward, axis=1)
        normals = np.cross(mesh[:, 1] - mesh[:, 0], mesh[:, 2] - mesh[:, 0])
        norm = np.linalg.norm(normals, axis=1)
        norm[norm < 1.0e-12] = 1.0
        normals /= norm[:, None]
        shade = np.clip(0.56 + 0.44 * np.abs(normals @ light), 0.4, 1.0)
        for i in range(len(mesh)):
            color = tuple(int(base[c] * shade[i]) for c in range(3)) + (255,)
            points = [(float(xx[i, j]), float(yy[i, j])) for j in range(3)]
            polys.append((float(depth[i]), points, color))
    polys.sort(key=lambda row: row[0], reverse=True)
    draw = ImageDraw.Draw(image, "RGBA")
    for _, points, color in polys:
        draw.polygon(points, fill=color)
    if transparent:
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer, "RGBA")
        for mesh, color in transparent:
            r = mesh - camera
            xx = r @ right * scale + ox
            yy = -(r @ up) * scale + oy
            depth = np.mean(r @ forward, axis=1)
            order = np.argsort(depth)[::-1]
            for i in order:
                ld.polygon([(float(xx[i, j]), float(yy[i, j])) for j in range(3)], fill=color)
        image = Image.alpha_composite(image, layer)

    image = image.resize((width, height), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((24, 20, width - 24, 118), radius=15, fill=(5, 10, 16, 235), outline=(83, 112, 129, 240), width=2)
    draw.text((48, 34), title, font=font(34, True), fill=(244, 248, 251, 255))
    draw.text((49, 79), subtitle, font=font(18), fill=(185, 205, 216, 255))
    draw.rounded_rectangle((24, height - 76, width - 24, height - 18), radius=13, fill=(5, 10, 16, 235), outline=(83, 112, 129, 240), width=2)
    draw.text((48, height - 59), "WEB/PHOTO REFERENCE — NOT FOR SUB-0.5 mm FINAL COLLISION", font=font(18, True), fill=(255, 206, 102, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, optimize=True)


def build_renders(parts: dict[str, Shape], static: Shape, moving: Shape) -> None:
    colors = {
        "pcb": (42, 128, 92), "gimbal": (190, 198, 204), "x_pot": (53, 58, 67),
        "y_pot": (53, 58, 67), "push_switch": (238, 237, 220), "shaft": (208, 179, 83),
        "cap": (51, 56, 64), "header": (204, 170, 75),
    }
    meshes = {name: triangles(shape) for name, shape in parts.items()}
    rows = [(meshes[name], colors[name]) for name in parts]
    subtitle = f"PCB {PCB_X:.1f} x {PCB_Y:.1f} / holes {MOUNT_PITCH_X:.2f} x {MOUNT_PITCH_Y:.2f} / rebuilt reference"
    views = [
        ("TOP", (0.0, 0.0, 100.0), (0.0, 1.0, 0.0)),
        ("BOTTOM", (0.0, 0.0, -100.0), (0.0, 1.0, 0.0)),
        ("FRONT", (0.0, -100.0, 22.0), (0.0, 0.0, 1.0)),
        ("SIDE", (100.0, 0.0, 22.0), (0.0, 0.0, 1.0)),
        ("ISO", (70.0, -90.0, 68.0), (0.0, 0.0, 1.0)),
    ]
    for index, (name, camera, hint) in enumerate(views, 1):
        render_scene(RENDER_DIR / f"{index:02d}_{name.lower()}.png", rows, camera, f"SZH-EK056 WEB REFERENCE / {name}", subtitle, up_hint=hint)
    render_scene(
        RENDER_DIR / "06_static_moving_envelope.png",
        rows,
        (70.0, -90.0, 68.0),
        "STATIC / MOVING CLEARANCE ENVELOPES",
        f"cyan=static neutral / orange=all-azimuth {MAX_TILT_DEG:.0f} deg inferred sweep",
        transparent=[(triangles(static, 0.35), (61, 198, 232, 52)), (triangles(moving, 0.35), (255, 144, 66, 72))],
    )


def bbox(shape: Shape) -> list[list[float]]:
    b = shape.bounding_box()
    return [[round(float(v), 4) for v in (b.min.X, b.min.Y, b.min.Z)], [round(float(v), 4) for v in (b.max.X, b.max.Y, b.max.Z)]]


def main() -> None:
    STEP_PATH.parent.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    reference, parts, static, moving = build_reference()
    export_step(reference, STEP_PATH)
    record = {
        "name": "SZH_EK056_WEB_REFERENCE",
        "modelType": "REBUILT WEB-REFERENCE",
        "exactSzhEk056CadFound": False,
        "datum": "PCB centre XY; PCB top Z=0",
        "sourceDimensionMm": {"skuLinkedOverall": [34.5, 26.0, 38.0], "genericMatching": [34.0, 26.0, 32.0]},
        "photoDerivedMm": {
            "pcb": [PCB_X, PCB_Y, PCB_T], "mountPitch": [MOUNT_PITCH_X, MOUNT_PITCH_Y],
            "mountCentres": MOUNT_HOLE_CENTRES, "joystickCentre": [JOY_X, JOY_Y],
            "gimbalXY": [GIMBAL_X, GIMBAL_Y], "xPotXY": [X_POT_X, X_POT_Y],
            "yPotXY": [Y_POT_X, Y_POT_Y], "pushSwitchXY": [PUSH_X, PUSH_Y],
        },
        "inferredMm": {"pivotZ": PIVOT_Z, "shaftD": SHAFT_D, "shaftTopZ": SHAFT_TOP_Z, "maxTiltDeg": MAX_TILT_DEG},
        "bboxNominalMm": bbox(Compound(children=list(parts.values()))),
        "bboxStaticEnvelopeMm": bbox(static),
        "bboxMovingEnvelopeMm": bbox(moving),
        "suitability": {"generalPackaging": True, "mountingDesign": "PROTOTYPE_ONLY", "sub0p5FinalCollision": False},
    }
    JSON_PATH.write_text(json.dumps(record, indent=2), encoding="utf-8")
    build_renders(parts, static, moving)
    print(f"STEP: {STEP_PATH}")
    print(f"JSON: {JSON_PATH}")
    print(f"renders: {RENDER_DIR}")
    print(json.dumps(record["suitability"], indent=2))


if __name__ == "__main__":
    main()
