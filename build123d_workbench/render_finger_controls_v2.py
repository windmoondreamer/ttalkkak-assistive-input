"""Render the validated local Finger V2 export set without rebuilding CAD."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np
from build123d import Location, Vector, import_step
from PIL import Image, ImageDraw

from .finger_controls_v2 import (
    BUTTON_ORDER,
    ControlDatum,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
    wire_envelope,
)
from .finger_layout_reset import THUMB_STEP, triangles


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
RENDER_DIR = ROOT / "renders" / "finger_controls_v2"
MARKER_STEP = ROOT / "build123d_workbench" / "out" / "finger_layout_reset" / "FINGER_LAYOUT_EXTERNAL_MARKERS_8.step"

sys.path.insert(0, str(ROOT / "scripts"))
import render_index_its_audit as render  # noqa: E402


SHELL_A = (39, 74, 94)
SHELL_B = (48, 88, 109)
THUMB = (80, 101, 116)
THUMB_TARGET = (238, 83, 77)
CAP = (56, 198, 128)
SWITCH = (224, 164, 61)
ROOT_METAL = (204, 181, 109)
WIRE = (236, 75, 92)
CARRIER_COLORS = {
    "N1_N2_shared_carrier": (201, 78, 171),
    "I2_I3_shared_carrier": (77, 169, 232),
    "M4_N3_shared_carrier": (54, 196, 201),
    "I4_carrier": (120, 111, 221),
    "M3_carrier": (238, 116, 77),
}


def load_controls() -> tuple[dict[str, ControlDatum], dict[str, float]]:
    data = json.loads((OUT_DIR / "finger_controls_v2_source_manifest.json").read_text(encoding="utf-8"))
    controls = {
        name: ControlDatum(
            name=name,
            center=tuple(row["centerMm"]),
            shell_normal=tuple(row["shellNormal"]),
            axis=tuple(row["axis"]),
            owner=row["owner"],
            kind=row["kind"],
            cap_u=tuple(row["capU"]),
            switch_u=tuple(row["switchU"]),
            roll_deg=float(row["rollDeg"]),
        )
        for name, row in data["controls"].items()
    }
    return controls, {name: float(value) for name, value in data["frontDepthsMm"].items()}


def rot_z(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0)))


def rot_x(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c)))


def rotate_objects(objects, matrix):
    return [(mesh @ matrix.T, color) for mesh, color in objects]


def translated(mesh: np.ndarray, delta) -> np.ndarray:
    return mesh + np.asarray(delta, dtype=float)


def annotate(image: Image.Image, title: str, subtitle: str, legend=()) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((28, 22, 1180, 112), radius=14, fill=(7, 12, 19, 224), outline=(80, 105, 120, 220), width=2)
    draw.text((48, 34), title, font=render.font(36, True), fill=(244, 248, 250, 255))
    draw.text((50, 79), subtitle, font=render.font(18), fill=(181, 199, 210, 255))
    if legend:
        x = 45
        y = render.HEIGHT - 82
        draw.rounded_rectangle((28, render.HEIGHT - 105, render.WIDTH - 28, render.HEIGHT - 30), radius=14, fill=(7, 12, 19, 224), outline=(70, 94, 110, 220), width=2)
        for label, color in legend:
            draw.ellipse((x, y, x + 18, y + 18), fill=(*color, 255))
            draw.text((x + 27, y - 5), label, font=render.font(16), fill=(228, 236, 241, 255))
            x += max(190, len(label) * 9 + 60)


def save_scene(filename: str, objects, title: str, subtitle: str, legend=(), matrix=None):
    if matrix is not None:
        objects = rotate_objects(objects, matrix)
    image, projection = render.rasterize(objects)
    annotate(image, title, subtitle, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / filename
    image.convert("RGB").save(path, quality=96)
    return image, projection, path


def shell_wireframe(image, projection, shell_meshes, centers, matrix=None, radius=28.0):
    draw = ImageDraw.Draw(image, "RGBA")
    centers = np.asarray(centers, dtype=float)
    if matrix is not None:
        centers = centers @ matrix.T
    for mesh in shell_meshes:
        work = mesh @ matrix.T if matrix is not None else mesh
        centroids = work.mean(axis=1)
        distances = np.min(np.linalg.norm(centroids[:, None, :] - centers[None, :, :], axis=2), axis=1)
        local = work[distances <= radius]
        stride = max(1, len(local) // 140)
        for triangle in local[::stride]:
            points = render.project(triangle, projection)
            draw.line([tuple(points[0]), tuple(points[1]), tuple(points[2]), tuple(points[0])], fill=(93, 182, 218, 38), width=1)


def label_centers(image, projection, controls, matrix=None, selected=BUTTON_ORDER):
    draw = ImageDraw.Draw(image, "RGBA")
    for index, name in enumerate(selected):
        point = np.asarray(controls[name].center) + unit(controls[name].axis) * 1.8
        if matrix is not None:
            point = point @ matrix.T
        xy = render.project(point[None, :], projection)[0]
        x, y = float(xy[0]), float(xy[1])
        ox = -42 if index % 2 == 0 else 18
        oy = -46 if index % 3 else 18
        draw.line((x, y, x + ox, y + oy), fill=(244, 246, 248, 190), width=2)
        draw.rounded_rectangle((x + ox - 4, y + oy - 5, x + ox + 38, y + oy + 24), radius=6, fill=(7, 12, 19, 224), outline=(220, 230, 236, 220), width=1)
        draw.text((x + ox + 4, y + oy - 3), name, font=render.font(15, True), fill=(244, 248, 250, 255))


def make_contact_sheet(paths: list[Path]) -> Path:
    thumbs = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        image.thumbnail((470, 352), Image.Resampling.LANCZOS)
        thumbs.append((path.name, image.copy()))
    columns = 2
    cell_w, cell_h = 500, 395
    rows = math.ceil(len(thumbs) / columns)
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h + 78), (10, 16, 24))
    draw = ImageDraw.Draw(sheet)
    draw.text((28, 18), "ONEGRIP PLAY / FINGER CONTROLS V2 / VISUAL QC", font=render.font(30, True), fill=(242, 247, 250))
    for index, (name, image) in enumerate(thumbs):
        x = (index % columns) * cell_w + 15
        y = (index // columns) * cell_h + 72
        sheet.paste(image, (x, y))
        draw.text((x + 8, y + 357), name, font=render.font(16), fill=(205, 218, 226))
    path = RENDER_DIR / "00_contact_sheet.png"
    sheet.save(path, quality=96)
    return path


def main() -> None:
    controls, depths = load_controls()
    jad = import_step(OUT_DIR / "JAD_FINGER_V2.step")
    jfd = import_step(OUT_DIR / "JFD_FINGER_V2.step")
    shell_meshes = [triangles(jad), triangles(jfd)]
    thumb = import_step(THUMB_STEP)
    thumb_meshes = [triangles(solid) for solid in thumb.solids() if solid.bounding_box().max.X < 50.0]
    carriers = {name: import_step(OUT_DIR / f"{name}.step") for name in CARRIER_COLORS}
    caps = {name: import_step(OUT_DIR / f"{name}_cap.step") for name in BUTTON_ORDER}
    carrier_meshes = {name: triangles(shape) for name, shape in carriers.items()}
    cap_meshes = {name: triangles(shape) for name, shape in caps.items()}

    switch_meshes = {}
    root_meshes = {}
    wire_meshes = {}
    for name in BUTTON_ORDER:
        datum = controls[name]
        body = switch_body(datum, depths[name])
        actuator = switch_actuator(datum, depths[name])
        switch_meshes[name] = np.concatenate((triangles(body), triangles(actuator)))
        root_meshes[name] = np.concatenate([triangles(shape) for shape in terminal_root_cutters(datum, depths[name])])
        wire_meshes[name] = triangles(wire_envelope(datum, depths[name]))

    exterior = [
        (shell_meshes[0], SHELL_A),
        (shell_meshes[1], SHELL_B),
        *[(mesh, THUMB) for mesh in thumb_meshes],
        *[(mesh, CAP) for mesh in cap_meshes.values()],
    ]
    internal = [
        *[(mesh, CARRIER_COLORS[name]) for name, mesh in carrier_meshes.items()],
        *[(mesh, SWITCH) for mesh in switch_meshes.values()],
        *[(mesh, ROOT_METAL) for mesh in root_meshes.values()],
        *[(mesh, CAP) for mesh in cap_meshes.values()],
    ]
    centers = [controls[name].center for name in BUTTON_ORDER]
    paths: list[Path] = []

    rear = rot_z(140.0)
    image, projection, path = save_scene(
        "01_final_cap_view.png", exterior,
        "FINAL 8-CAP EXTERIOR / APPROVED LAYOUT PRESERVED",
        "7.6 mm CAPS / 8.0 mm NOMINAL OPENINGS / N2 8.4 mm SEAM RELIEF",
        (("clean shell + openings", SHELL_B), ("final caps", CAP), ("original thumb", THUMB)),
        rear,
    )
    label_centers(image, projection, controls, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    thumb_lower_target = np.asarray((0.0, 12.25, -21.0), dtype=float)
    thumb_basis_overlay = [
        *[(mesh, CAP) for mesh in cap_meshes.values()],
        *[(mesh, THUMB) for mesh in thumb_meshes],
        *[(translated(mesh, thumb_lower_target), THUMB_TARGET) for mesh in thumb_meshes],
    ]
    image, projection, path = save_scene(
        "11_thumb_original_vs_max_lower_target.png",
        thumb_basis_overlay,
        "THUMB BASIS REALITY CHECK / ORIGINAL VS MAX-LOWER TARGET",
        "SHELL WIREFRAME / GRAY = V2 BASIS / RED = STUDY ONLY / DELTA (0,+12.25,-21.00) mm",
        (
            ("validated original-thumb reference", THUMB),
            ("max-lower target; internals NOT validated", THUMB_TARGET),
            ("Finger V2 caps", CAP),
        ),
        rear,
    )
    thumb_centers = [mesh.reshape(-1, 3).mean(axis=0) for mesh in thumb_meshes]
    overlay_centers = [
        *centers,
        *thumb_centers,
        *[center + thumb_lower_target for center in thumb_centers],
    ]
    shell_wireframe(image, projection, shell_meshes, overlay_centers, rear, radius=55.0)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    image, projection, path = save_scene(
        "02_transparent_shell_all_switches.png", internal,
        "TRANSPARENT SHELL / ALL 8 ITS-1105 SWITCHES",
        "AXIS MATCH <= 4 DEG / 5 CARRIERS / FIXED ROOTS SHOWN",
        (("carrier", (201, 78, 171)), ("ITS housing", SWITCH), ("fixed roots", ROOT_METAL), ("cap", CAP)),
        rear,
    )
    shell_wireframe(image, projection, shell_meshes, centers, rear)
    label_centers(image, projection, controls, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    for filename, angle, title in (
        ("03_left_oblique_internal.png", 112.0, "LEFT OBLIQUE / INTERNAL"),
        ("04_right_oblique_internal.png", 168.0, "RIGHT OBLIQUE / INTERNAL"),
    ):
        matrix = rot_z(angle)
        image, projection, path = save_scene(
            filename, internal, title,
            "OPPOSITE-END SWITCH PRELOAD / BROAD REAR PLATES / NO SNAP HOOKS",
            (("shared + independent carriers", (201, 78, 171)), ("ITS-1105", SWITCH), ("caps", CAP)),
            matrix,
        )
        shell_wireframe(image, projection, shell_meshes, centers, matrix)
        image.convert("RGB").save(path, quality=96)
        paths.append(path)

    exploded = []
    group_buttons = {
        "N1_N2_shared_carrier": ("N1", "N2"),
        "I2_I3_shared_carrier": ("I2", "I3"),
        "M4_N3_shared_carrier": ("M4", "N3"),
        "I4_carrier": ("I4",),
        "M3_carrier": ("M3",),
    }
    for carrier_name, names in group_buttons.items():
        mean_axis = unit(np.mean([unit(controls[name].axis) for name in names], axis=0))
        exploded.append((translated(carrier_meshes[carrier_name], -mean_axis * 5.0), CARRIER_COLORS[carrier_name]))
        for name in names:
            exploded.append((translated(switch_meshes[name], unit(controls[name].axis) * 4.0), SWITCH))
            exploded.append((translated(cap_meshes[name], unit(controls[name].axis) * 11.0), CAP))
    _, _, path = save_scene(
        "05_carrier_exploded.png", exploded,
        "5-CARRIER ARCHITECTURE / EXPLODED",
        "3 SHARED PAIRS + I4 SINGLE + M3 SINGLE / 13 PRINTABLE PARTS",
        (("carrier", (201, 78, 171)), ("ITS-1105", SWITCH), ("push-on cap", CAP)),
        rear,
    )
    paths.append(path)

    upper_names = ("N1", "N2")
    upper = [
        (carrier_meshes["N1_N2_shared_carrier"], CARRIER_COLORS["N1_N2_shared_carrier"]),
        *[(switch_meshes[name], SWITCH) for name in upper_names],
        *[(cap_meshes[name], CAP) for name in upper_names],
        *[(wire_meshes[name], WIRE) for name in upper_names],
    ]
    image, projection, path = save_scene(
        "06_n1_n2_seam_closeup.png", upper,
        "N1 / N2 UPPER REGION + SEAM CLOSE-UP",
        "N2 CENTER X=0 / JfD CARRIER / 0.4 mm PER-SIDE CAP CLEARANCE",
        (("N1/N2 one-piece carrier", CARRIER_COLORS["N1_N2_shared_carrier"]), ("switch", SWITCH), ("wire envelope", WIRE)),
        rear,
    )
    shell_wireframe(image, projection, shell_meshes, [controls[name].center for name in upper_names], rear, radius=18.0)
    label_centers(image, projection, controls, rear, upper_names)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    n3_scene = [
        (carrier_meshes["M4_N3_shared_carrier"], CARRIER_COLORS["M4_N3_shared_carrier"]),
        (switch_meshes["M4"], SWITCH),
        (switch_meshes["N3"], SWITCH),
        (cap_meshes["N3"], CAP),
        (wire_meshes["N3"], WIRE),
    ]
    n3_matrix = rot_z(175.0)
    image, projection, path = save_scene(
        "07_n3_closeup.png", n3_scene,
        "N3 CURVED-SURFACE CLOSE-UP",
        "4.0 DEG INTERNAL AXIS TILT / 1.359 mm WORST-PAIR SWITCH CLEARANCE",
        (("M4/N3 carrier", CARRIER_COLORS["M4_N3_shared_carrier"]), ("N3 ITS", SWITCH), ("wire relief", WIRE)),
        n3_matrix,
    )
    shell_wireframe(image, projection, shell_meshes, [controls["N3"].center], n3_matrix, radius=18.0)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    wiring = [
        *[(mesh, CARRIER_COLORS[name]) for name, mesh in carrier_meshes.items()],
        *[(mesh, SWITCH) for mesh in switch_meshes.values()],
        *[(mesh, ROOT_METAL) for mesh in root_meshes.values()],
        *[(mesh, WIRE) for mesh in wire_meshes.values()],
    ]
    _, _, path = save_scene(
        "08_wiring_concept.png", wiring,
        "TERMINAL ROOT + WIRING SERVICE CONCEPT",
        "RIGID ROOT RELIEFS / 4.0 x 3.2 mm REAR EXITS / DISTAL LEADS PRE-FORMABLE",
        (("ITS body", SWITCH), ("fixed roots", ROOT_METAL), ("wire service envelope", WIRE)),
        rear,
    )
    paths.append(path)

    service = []
    for carrier_name, names in group_buttons.items():
        owner = controls[names[0]].owner
        shift = np.asarray((10.0, 0.0, 0.0)) if owner == "JfD" else np.asarray((-10.0, 0.0, 0.0))
        service.append((translated(carrier_meshes[carrier_name], shift), CARRIER_COLORS[carrier_name]))
        for name in names:
            service.append((translated(switch_meshes[name], shift), SWITCH))
            service.append((translated(root_meshes[name], shift), ROOT_METAL))
    service.extend((mesh, CAP) for mesh in cap_meshes.values())
    image, projection, path = save_scene(
        "09_assembly_service_view.png", service,
        "ASSEMBLY / SERVICE VIEW",
        "PRELOAD SWITCHES OUTSIDE SHELL -> ROUTE WIRES -> INSERT MODULES FROM CENTRAL SEAM",
        (("JfD modules +X exploded", (77, 169, 232)), ("JaD modules -X exploded", (54, 196, 201)), ("caps stay exterior", CAP)),
        rear,
    )
    shell_wireframe(image, projection, shell_meshes, centers, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    marker = import_step(MARKER_STEP)
    marker_meshes = [triangles(solid) for solid in marker.solids()]
    image, projection, path = save_scene(
        "10_approved_overlay.png", exterior,
        "APPROVED MARKER -> FINAL CAP OVERLAY",
        "CENTER DELTA = 0.000 mm FOR ALL 8 BUTTONS / RED WIREFRAME = DOCS/45 MARKER",
        (("final cap", CAP), ("approved marker outline", (240, 67, 73))),
        rear,
    )
    draw = ImageDraw.Draw(image, "RGBA")
    for mesh in marker_meshes:
        work = mesh @ rear.T
        stride = max(1, len(work) // 90)
        for triangle in work[::stride]:
            points = render.project(triangle, projection)
            draw.line([tuple(points[0]), tuple(points[1]), tuple(points[2]), tuple(points[0])], fill=(244, 65, 72, 170), width=2)
    label_centers(image, projection, controls, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    contact = make_contact_sheet(paths)
    print(contact)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
