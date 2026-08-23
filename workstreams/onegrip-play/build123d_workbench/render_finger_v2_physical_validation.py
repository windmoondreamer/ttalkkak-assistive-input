"""Render the generated Finger V2 physical validation kit."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "finger_v2_physical_validation"
RENDER_DIR = OUT_DIR / "renders"
sys.path.insert(0, str(ROOT / "scripts"))

from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402

from .finger_controls_v2 import (  # noqa: E402
    BUTTON_ORDER,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
    wire_envelope,
)
from .finger_layout_reset import triangles  # noqa: E402
from .finger_v2_physical_validation import load_controls  # noqa: E402


SHELL_A = (40, 76, 96)
SHELL_B = (52, 93, 113)
FIT = (83, 174, 221)
CAP = (57, 202, 130)
SWITCH = (225, 166, 65)
ROOT = (205, 184, 112)
WIRE = (237, 72, 91)
CARRIER = (202, 79, 171)
GHOST = (95, 184, 218)


def rot_z(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0)))


def rot_x(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c)))


def transformed(objects, matrix):
    return [(mesh @ matrix.T, color) for mesh, color in objects]


def translated(mesh: np.ndarray, delta) -> np.ndarray:
    return mesh + np.asarray(delta, dtype=float)


def annotate(image: Image.Image, title: str, subtitle: str, legend=()) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((28, 22, 1260, 112), radius=14, fill=(7, 12, 19, 228), outline=(80, 105, 120, 220), width=2)
    draw.text((48, 34), title, font=render.font(36, True), fill=(244, 248, 250, 255))
    draw.text((50, 79), subtitle, font=render.font(18), fill=(181, 199, 210, 255))
    if legend:
        x = 45
        y = render.HEIGHT - 82
        draw.rounded_rectangle((28, render.HEIGHT - 105, render.WIDTH - 28, render.HEIGHT - 30), radius=14, fill=(7, 12, 19, 224), outline=(70, 94, 110, 220), width=2)
        for label, color in legend:
            draw.ellipse((x, y, x + 18, y + 18), fill=(*color, 255))
            draw.text((x + 27, y - 5), label, font=render.font(16), fill=(228, 236, 241, 255))
            x += max(190, len(label) * 9 + 62)


def save_scene(filename, objects, title, subtitle, legend=(), matrix=None):
    if matrix is not None:
        objects = transformed(objects, matrix)
    image, projection = render.rasterize(objects)
    annotate(image, title, subtitle, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / filename
    image.convert("RGB").save(path, quality=96)
    return image, projection, path


def shell_wireframe(image, projection, meshes, matrix=None):
    draw = ImageDraw.Draw(image, "RGBA")
    for mesh in meshes:
        work = mesh @ matrix.T if matrix is not None else mesh
        stride = max(1, len(work) // 45)
        for triangle in work[::stride]:
            points = render.project(triangle, projection)
            draw.line([tuple(points[0]), tuple(points[1]), tuple(points[2]), tuple(points[0])], fill=(*GHOST, 44), width=1)


def tolerance_chart(validation: dict) -> Image.Image:
    image = Image.new("RGB", (render.WIDTH, render.HEIGHT), (12, 18, 27))
    draw = ImageDraw.Draw(image)
    annotate(image, "FDM TOLERANCE PROBE", "WORST CORRELATED ERROR: CAVITY SHRINK + MATING PART GROW")
    rows = validation["toleranceProbe"]
    columns = ("-0.20", "-0.10", "+0.00", "+0.10", "+0.20")
    x0, y0 = 170, 220
    col_w, row_h = 220, 135
    draw.text((45, y0 + 36), "SWITCH / POCKET", font=render.font(21, True), fill=(230, 237, 242))
    draw.text((45, y0 + row_h + 36), "CAP / 8.0 OPENING", font=render.font(21, True), fill=(230, 237, 242))
    draw.text((45, y0 + 2 * row_h + 36), "CAP / N2 8.4", font=render.font(21, True), fill=(230, 237, 242))
    colors = {"PASS": (55, 190, 118), "MARGINAL": (239, 166, 58), "INTERFERENCE": (229, 73, 84)}
    for column, key in enumerate(columns):
        x = x0 + column * col_w
        draw.text((x + 65, y0 - 55), f"{key} mm", font=render.font(20, True), fill=(197, 213, 223))
        values = (
            rows["switchPocket"][key],
            rows["capOpening"][key]["standard"],
            rows["capOpening"][key]["N2"],
        )
        for index, value in enumerate(values):
            y = y0 + index * row_h
            status = value["classification"]
            draw.rounded_rectangle((x, y, x + 190, y + 92), radius=12, fill=colors[status], outline=(240, 245, 248), width=2)
            clearance = value.get("diametralClearanceXmm", value.get("diametralClearanceMm", 0.0))
            draw.text((x + 17, y + 13), status, font=render.font(22, True), fill=(8, 13, 19))
            draw.text((x + 17, y + 52), f"gap {clearance:+.2f} mm", font=render.font(17), fill=(8, 13, 19))
    draw.rounded_rectangle((120, 720, render.WIDTH - 120, 930), radius=18, fill=(7, 12, 19), outline=(87, 113, 130), width=2)
    draw.text((150, 755), "MOST SENSITIVE: 6.40 POCKET vs 6.18 BODY_X", font=render.font(28, True), fill=(244, 248, 250))
    draw.text((150, 815), "+/-0.10 mm correlated error -> pocket is marginal", font=render.font(22), fill=(239, 183, 91))
    draw.text((150, 860), "+/-0.20 mm correlated error -> physical interference possible", font=render.font(22), fill=(239, 106, 114))
    return image


def make_contact_sheet(paths: list[Path]) -> Path:
    columns = 3
    cell_w, cell_h = 470, 390
    rows = math.ceil(len(paths) / columns)
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h + 78), (9, 15, 23))
    draw = ImageDraw.Draw(sheet)
    draw.text((28, 18), "FINGER V2 PHYSICAL VALIDATION KIT / VISUAL QC", font=render.font(30, True), fill=(242, 247, 250))
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((440, 330), Image.Resampling.LANCZOS)
        x = (index % columns) * cell_w + 15
        y = (index // columns) * cell_h + 72
        sheet.paste(image, (x, y))
        draw.text((x + 8, y + 338), path.name, font=render.font(15), fill=(205, 218, 226))
    output = RENDER_DIR / "00_contact_sheet.png"
    sheet.save(output, quality=96)
    return output


def main() -> None:
    validation = json.loads((OUT_DIR / "finger_v2_physical_validation.json").read_text(encoding="utf-8"))
    controls, depths = load_controls()
    rear = rot_z(140.0)

    fit = read_binary_stl(OUT_DIR / "ITS_POCKET_FIT_COUPON.stl")
    one_shells = [
        read_binary_stl(OUT_DIR / "ONE_BUTTON_I4_JAD_SHELL.stl"),
        read_binary_stl(OUT_DIR / "ONE_BUTTON_I4_JFD_CLOSURE.stl"),
    ]
    n2_shells = [
        read_binary_stl(OUT_DIR / "N2_SEAM_JAD_SHELL.stl"),
        read_binary_stl(OUT_DIR / "N2_SEAM_JFD_SHELL.stl"),
    ]
    full_shells = [
        read_binary_stl(OUT_DIR / "FINGER_V2_SECTION_JAD_SHELL.stl"),
        read_binary_stl(OUT_DIR / "FINGER_V2_SECTION_JFD_SHELL.stl"),
    ]
    carriers = {
        name: read_binary_stl(OUT_DIR / f"KIT_{name}.stl")
        for name in (
            "N1_N2_shared_carrier",
            "I2_I3_shared_carrier",
            "M4_N3_shared_carrier",
            "I4_carrier",
            "M3_carrier",
        )
    }
    caps = {name: read_binary_stl(OUT_DIR / f"KIT_{name}_cap.stl") for name in BUTTON_ORDER}
    switches = {}
    roots = {}
    wires = {}
    for name in BUTTON_ORDER:
        datum = controls[name]
        switches[name] = np.concatenate((
            triangles(switch_body(datum, depths[name])),
            triangles(switch_actuator(datum, depths[name])),
        ))
        roots[name] = np.concatenate([triangles(shape) for shape in terminal_root_cutters(datum, depths[name])])
        wires[name] = triangles(wire_envelope(datum, depths[name]))

    paths: list[Path] = []
    _, _, path = save_scene(
        "01_its_pocket_fit_coupon.png",
        [(fit, FIT)],
        "KIT A / ITS-1105 POCKET FIT COUPON",
        "6.30 / 6.35 / 6.40 / 6.45 / 6.50 mm / RAISED LABELS / 6.40 FRAMED",
        (("flat base / no support", FIT),),
        rot_x(5.0),
    )
    paths.append(path)

    i4_scene = [
        (one_shells[0], SHELL_A),
        (one_shells[1], SHELL_B),
        (carriers["I4_carrier"], CARRIER),
        (caps["I4"], CAP),
        (switches["I4"], SWITCH),
        (roots["I4"], ROOT),
    ]
    _, _, path = save_scene(
        "02_one_button_function_coupon.png", i4_scene,
        "KIT B / I4 ONE-BUTTON FUNCTION COUPON",
        "PRODUCTION SHELL WALL + 8.0 OPENING + 7.6 CAP + I4 CARRIER + ITS ENVELOPE",
        (("cropped JaD/JfD", SHELL_B), ("production carrier", CARRIER), ("ITS", SWITCH), ("cap", CAP)),
        rear,
    )
    paths.append(path)

    n2_scene = [
        (n2_shells[0], SHELL_A),
        (n2_shells[1], SHELL_B),
        (carriers["N1_N2_shared_carrier"], CARRIER),
        (caps["N2"], CAP),
        (switches["N2"], SWITCH),
        (wires["N2"], WIRE),
    ]
    _, _, path = save_scene(
        "03_n2_seam_coupon_closed.png", n2_scene,
        "KIT C / N2 SEAM COUPON / CLOSED",
        "X=0 CENTER / 8.4 OPENING / BOTH PRODUCTION SHELL INTERFACES / JfD CARRIER",
        (("JaD/JfD crop", SHELL_B), ("N1/N2 carrier", CARRIER), ("N2 ITS", SWITCH), ("wire exit", WIRE)),
        rear,
    )
    paths.append(path)

    n2_exploded = [
        (translated(n2_shells[0], (7.0, 0.0, 0.0)), SHELL_A),
        (translated(n2_shells[1], (-7.0, 0.0, 0.0)), SHELL_B),
        (translated(carriers["N1_N2_shared_carrier"], (0.0, 5.0, 0.0)), CARRIER),
        (translated(switches["N2"], (0.0, -4.0, 0.0)), SWITCH),
        (translated(caps["N2"], unit(controls["N2"].axis) * 8.0), CAP),
    ]
    _, _, path = save_scene(
        "04_n2_seam_coupon_exploded.png", n2_exploded,
        "N2 SEAM COUPON / EXPLODED",
        "PRINT SHELL PIECES SEPARATELY -> PRELOAD SWITCH -> CLOSE JaD/JfD -> TEST JAM/RUB",
        (("shell halves", SHELL_B), ("carrier", CARRIER), ("ITS", SWITCH), ("cap", CAP)),
        rear,
    )
    paths.append(path)

    full_exterior = [
        (full_shells[0], SHELL_A),
        (full_shells[1], SHELL_B),
        *[(mesh, CAP) for mesh in caps.values()],
    ]
    _, _, path = save_scene(
        "05_full_functional_section_exterior.png", full_exterior,
        "KIT D / 8-BUTTON FUNCTIONAL SECTION / EXTERIOR",
        "1:1 PRODUCTION CURVATURE + OPENINGS / FULL JOYSTICK SHELL NOT INCLUDED",
        (("cropped production shell", SHELL_B), ("8 production caps", CAP)),
        rear,
    )
    paths.append(path)

    internal = [
        *[(mesh, CARRIER) for mesh in carriers.values()],
        *[(mesh, SWITCH) for mesh in switches.values()],
        *[(mesh, ROOT) for mesh in roots.values()],
        *[(mesh, WIRE) for mesh in wires.values()],
        *[(mesh, CAP) for mesh in caps.values()],
    ]
    image, projection, path = save_scene(
        "06_full_functional_section_internal.png", internal,
        "KIT D / TRANSPARENT 8-SWITCH INTERNAL",
        "5 CARRIERS / 8 ITS / ROOT + WIRE SERVICE ENVELOPES",
        (("carrier", CARRIER), ("ITS", SWITCH), ("fixed roots", ROOT), ("wire", WIRE), ("cap", CAP)),
        rear,
    )
    shell_wireframe(image, projection, full_shells, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    # Three I4 motion states are separated laterally for an unambiguous visual.
    motion_scene = []
    for index, (state, travel) in enumerate((('REST', 0.0), ('PARTIAL', 0.175), ('FULL', 0.35))):
        lateral = np.asarray(((index - 1) * 32.0, 0.0, 0.0))
        datum = controls["I4"]
        motion_scene.extend((
            (translated(one_shells[0], lateral), SHELL_A),
            (translated(carriers["I4_carrier"], lateral), CARRIER),
            (translated(switches["I4"], lateral), SWITCH),
            (translated(caps["I4"], lateral - unit(datum.axis) * travel), CAP),
        ))
    _, _, path = save_scene(
        "07_cap_motion_rest_partial_full.png", motion_scene,
        "CAP MOTION / REST -> PARTIAL -> FULL ACTUATION",
        "I4 PRODUCTION GEOMETRY / 0.000 / 0.175 / 0.350 mm / HARD INTERSECTION 0",
        (("shell", SHELL_A), ("carrier", CARRIER), ("ITS", SWITCH), ("moving cap", CAP)),
        rear,
    )
    paths.append(path)

    chart = tolerance_chart(validation)
    path = RENDER_DIR / "08_tolerance_probe.png"
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    chart.save(path, quality=96)
    paths.append(path)

    plate = read_binary_stl(OUT_DIR / "VALIDATION_PRINT_PLATE.stl")
    _, _, path = save_scene(
        "09_validation_print_plate.png", [(plate, FIT)],
        "VALIDATION PRINT PLATE / 20 COMPONENTS",
        "189.21 x 106.66 x 25.04 mm / 6 mm NOMINAL GAP / INDIVIDUAL PARTS REMAIN DISCONNECTED",
        (("kit parts", FIT),),
        rot_x(12.0),
    )
    paths.append(path)

    contact = make_contact_sheet(paths)
    print(contact)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
