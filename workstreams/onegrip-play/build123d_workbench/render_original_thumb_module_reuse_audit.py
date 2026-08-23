"""Render the analysis-only original Thumb cartridge reuse audit."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np
from build123d import import_step
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation
from OCP.TopLoc import TopLoc_Location
from PIL import Image, ImageDraw

from .finger_layout_reset import TESSELLATION_ANGLE, TESSELLATION_TOLERANCE
from .original_thumb_module_reuse_audit import (
    COLLISION_OUTPUT,
    FASTENING_OUTPUT,
    FINGER_REFERENCE,
    JAD_SHELL,
    JFD_SHELL,
    LOWERED_OUTPUT,
    ORIGINAL_OUTPUT,
    OUT_DIR,
    REPORT_OUTPUT,
)


ROOT = Path(__file__).resolve().parents[1]
RENDER_DIR = ROOT / "renders" / "original_thumb_module_reuse_audit"
CURRENT_RENDER_DIR = ROOT / "renders" / "integrated_exterior_lowered_thumb_v1"
VISUAL_SHELL = (
    ROOT / "build123d_workbench" / "out" / "integrated_exterior_lowered_thumb_v1"
    / "EXTERIOR_FIRST_LOWERED_THUMB_VISUAL_REFERENCE.stl"
)

sys.path.insert(0, str(ROOT / "scripts"))
import render_index_its_audit as render  # noqa: E402
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402


BG = (9, 15, 22)
SHELL = (51, 92, 116)
SHELL_WIRE = (112, 201, 231, 62)
BACKPLATE = (116, 133, 146)
CAP = (240, 145, 45)
PUSHBUTTON = (236, 190, 72)
JOYSTICK = (70, 176, 225)
SUPPORT = (87, 210, 159)
FINGER_SWITCH = (93, 201, 147)
FINGER_CARRIER = (87, 143, 189)
FINGER_CAP = (50, 216, 143)
SCREW = (239, 78, 82)
COLLISION = (255, 45, 60)
ORIGINAL_GHOST = (99, 108, 118)
TEXT = (243, 248, 251)
MUTED = (177, 198, 210)
THUMB_NORMAL = np.asarray((0.00017647, 0.60270162, 0.79796662), dtype=float)


def safe_triangles(shape) -> np.ndarray:
    shape.mesh(TESSELLATION_TOLERANCE, TESSELLATION_ANGLE)
    rows = []
    for face in shape.faces():
        location = TopLoc_Location()
        poly = BRep_Tool.Triangulation_s(face.wrapped, location)
        if poly is None:
            continue
        transform = location.Transformation()
        points = [
            poly.Node(index).Transformed(transform)
            for index in range(1, poly.NbNodes() + 1)
        ]
        reverse = face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
        for triangle in poly.Triangles():
            indices = [triangle.Value(index) - 1 for index in (1, 2, 3)]
            if reverse:
                indices[1], indices[2] = indices[2], indices[1]
            rows.append([
                [points[index].X(), points[index].Y(), points[index].Z()]
                for index in indices
            ])
    if not rows:
        raise RuntimeError("shape produced no renderable triangles")
    return np.asarray(rows, dtype=float)


def part_color(name: str) -> tuple[int, int, int]:
    if "BACKPLATE" in name:
        return BACKPLATE
    if "_CAP__" in name:
        return CAP
    if "PUSHBTN" in name:
        return PUSHBUTTON
    if "HW504" in name:
        return JOYSTICK
    if "SMALL_ATTACHMENT" in name:
        return SUPPORT
    return (170, 180, 188)


def load_children(path: Path) -> list[tuple[str, np.ndarray]]:
    shape = import_step(path)
    return [(child.label, safe_triangles(child)) for child in shape.children]


def annotate(
    image: Image.Image,
    title: str,
    subtitle: str,
    footer: str,
    legend=(),
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle(
        (28, 22, render.WIDTH - 28, 116), radius=14,
        fill=(7, 12, 19, 230), outline=(79, 108, 126, 235), width=2,
    )
    draw.text((48, 34), title, font=render.font(32, True), fill=(*TEXT, 255))
    draw.text((50, 79), subtitle, font=render.font(17), fill=(*MUTED, 255))
    draw.rounded_rectangle(
        (28, render.HEIGHT - 111, render.WIDTH - 28, render.HEIGHT - 28), radius=14,
        fill=(7, 12, 19, 230), outline=(79, 108, 126, 235), width=2,
    )
    draw.text((48, render.HEIGHT - 92), footer, font=render.font(16, True), fill=(245, 205, 116, 255))
    x = 48
    for label, color in legend:
        draw.ellipse((x, render.HEIGHT - 57, x + 15, render.HEIGHT - 42), fill=(*color, 255))
        draw.text((x + 22, render.HEIGHT - 62), label, font=render.font(13), fill=(226, 235, 240, 255))
        x += max(145, len(label) * 7 + 50)


def save_scene(filename: str, objects, title: str, subtitle: str, footer: str, legend=()):
    image, projection = render.rasterize(objects)
    annotate(image, title, subtitle, footer, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / filename
    image.convert("RGB").save(path, quality=96)
    return image, projection, path


def wireframe(image: Image.Image, projection, meshes, color=SHELL_WIRE, stride_divisor=900) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    for mesh in meshes:
        stride = max(1, len(mesh) // stride_divisor)
        for triangle in mesh[::stride]:
            points = render.project(triangle, projection)
            draw.line(
                [tuple(points[0]), tuple(points[1]), tuple(points[2]), tuple(points[0])],
                fill=color, width=1,
            )


def draw_world_label(
    image: Image.Image,
    projection,
    point,
    label: str,
    offset=(30, -25),
    color=(235, 241, 245),
    small=False,
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    px, py = render.project(np.asarray([point], dtype=float), projection)[0]
    tx, ty = float(px + offset[0]), float(py + offset[1])
    font = render.font(12 if small else 15, not small)
    box = draw.textbbox((tx, ty), label, font=font)
    pad = 5
    draw.line((px, py, tx, ty + 7), fill=(*color, 220), width=2)
    draw.rounded_rectangle(
        (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad), radius=6,
        fill=(7, 12, 19, 220), outline=(*color, 220), width=1,
    )
    draw.text((tx, ty), label, font=font, fill=(*color, 255))


def decorated_copy(source: Path, destination: Path, title: str, detail: str) -> Path:
    image = Image.open(source).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle(
        (28, image.height - 116, image.width - 28, image.height - 28), radius=14,
        fill=(7, 12, 19, 232), outline=(79, 108, 126, 235), width=2,
    )
    draw.text((48, image.height - 99), title, font=render.font(21, True), fill=(*TEXT, 255))
    draw.text((50, image.height - 62), detail, font=render.font(15), fill=(245, 205, 116, 255))
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(destination, quality=96)
    return destination


def contact_sheet(paths: list[Path]) -> Path:
    cells = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        image.thumbnail((360, 270), Image.Resampling.LANCZOS)
        cells.append((path.name, image.copy()))
    cols, cell_w, cell_h = 3, 400, 320
    rows = math.ceil(len(cells) / cols)
    sheet = Image.new("RGB", (cols * cell_w, 76 + rows * cell_h), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (28, 18), "ONEGRIP PLAY / ORIGINAL THUMB MODULE REUSE AUDIT / ANALYSIS ONLY",
        font=render.font(27, True), fill=TEXT,
    )
    for index, (name, image) in enumerate(cells):
        x = (index % cols) * cell_w + 20
        y = (index // cols) * cell_h + 64
        sheet.paste(image, (x, y))
        draw.text((x + 3, y + 277), name, font=render.font(12), fill=(202, 216, 225))
    path = RENDER_DIR / "00_contact_sheet.png"
    sheet.save(path, quality=96)
    return path


def main() -> None:
    report_data = json.loads(REPORT_OUTPUT.read_text(encoding="utf-8"))
    original = load_children(ORIGINAL_OUTPUT)
    lowered = load_children(LOWERED_OUTPUT)
    screws = load_children(FASTENING_OUTPUT)
    collisions = [
        row for row in load_children(COLLISION_OUTPUT)
        if "COLLISION__" in row[0]
    ]
    finger = load_children(FINGER_REFERENCE)
    finger_switches = [row for row in finger if row[0].endswith("_ITS1105_reference")]
    finger_carriers = [row for row in finger if "carrier" in row[0].lower()]
    finger_caps = [row for row in finger if row[0].endswith("_cap")]
    exact_shells = [safe_triangles(import_step(JAD_SHELL)), safe_triangles(import_step(JFD_SHELL))]
    visual_shell = read_binary_stl(VISUAL_SHELL)

    original_objects = [(mesh, part_color(name)) for name, mesh in original]
    lowered_objects = [(mesh, part_color(name)) for name, mesh in lowered]
    screw_objects = [(mesh, SCREW) for _, mesh in screws]
    switch_objects = [(mesh, FINGER_SWITCH) for _, mesh in finger_switches]
    carrier_objects = [(mesh, FINGER_CARRIER) for _, mesh in finger_carriers]
    cap_objects = [(mesh, FINGER_CAP) for _, mesh in finger_caps]
    collision_objects = [(mesh, COLLISION) for _, mesh in collisions]

    paths: list[Path] = []
    print("[render 1/12] current frozen exterior", flush=True)
    paths.append(decorated_copy(
        CURRENT_RENDER_DIR / "05_full_oblique.png",
        RENDER_DIR / "01_current_final_exterior.png",
        "CURRENT EXTERIOR = PRESERVED",
        "LATEST FINGER 8 + MAXIMUM-LOWERED THUMB / NO EXTERIOR CHANGE IN THIS AUDIT",
    ))

    print("[render 2/12] isolated original cartridge", flush=True)
    _, _, path = save_scene(
        "02_original_thumb_cartridge_isolated.png", original_objects,
        "ORIGINAL OPEN-SOURCE THUMB CARTRIDGE",
        "20 EXACT PARTS / SCALE 1.000 / BACKPLATE + 8 CAPS + 8 PUSHBTN + HW504(2 SOLIDS) + ATTACHMENT",
        "SOURCE GEOMETRY ONLY / NO CUSTOM V3 SEAT, CARRIER, FASTENING OR WIRING",
        (("Backplate", BACKPLATE), ("8 caps", CAP), ("8 PushBtn", PUSHBUTTON), ("HW504", JOYSTICK)),
    )
    paths.append(path)

    print("[render 3/12] exploded cartridge", flush=True)
    exploded = []
    for name, mesh in original:
        work = mesh.copy()
        if "_CAP__" in name:
            work += THUMB_NORMAL * 10.0
        elif "PUSHBTN" in name:
            work -= THUMB_NORMAL * 7.0
        elif "BACKPLATE" in name:
            work -= THUMB_NORMAL * 17.0
        elif "HW504" in name:
            work += np.asarray((10.0 if name.endswith("_1") else -10.0, 0.0, 0.0))
        elif "SMALL_ATTACHMENT" in name:
            work += THUMB_NORMAL * 18.0
        exploded.append((work, part_color(name)))
    image, projection, path = save_scene(
        "03_original_thumb_cartridge_exploded.png", exploded,
        "ORIGINAL THUMB CARTRIDGE / EXPLODED",
        "EXPLODE TRANSFORMS ARE RENDER-ONLY / RELATIVE PRODUCTION GEOMETRY REMAINS UNCHANGED",
        "BACKPLATE INTEGRATES THE ORIGINAL BUTTON SUPPORT / RETAINER ARCHITECTURE",
        (("Backplate/support", BACKPLATE), ("caps", CAP), ("switches", PUSHBUTTON), ("joystick", JOYSTICK)),
    )
    paths.append(path)

    print("[render 4/12] approved rigid lowering", flush=True)
    _, _, path = save_scene(
        "04_lowered_original_thumb_cartridge.png",
        [(mesh, ORIGINAL_GHOST) for _, mesh in original] + lowered_objects,
        "ENTIRE ORIGINAL CARTRIDGE / RIGID LOWERING",
        "GRAY = ORIGINAL / COLOR = DX 0.00, DY +12.25, DZ -21.00 mm",
        "SCALE 1.000 / ROTATION CHANGE 0 DEG / RELATIVE-GEOMETRY RESIDUAL 1.42e-14 mm",
        (("original", ORIGINAL_GHOST), ("lowered cartridge", CAP), ("HW504", JOYSTICK)),
    )
    paths.append(path)

    print("[render 5/12] current exterior plus cartridge", flush=True)
    _, _, path = save_scene(
        "05_current_exterior_plus_original_cartridge.png",
        [(visual_shell, SHELL), *cap_objects, *lowered_objects],
        "CURRENT EXTERIOR + LOWERED ORIGINAL CARTRIDGE",
        "OPAQUE INSTALL VIEW / INTERNAL PARTS ARE PRESENT BUT NATURALLY OCCLUDED BY THE FROZEN SHELL",
        "EXTERIOR SURFACE MODIFICATION = 0 / ALIGNMENT PASS / INTERNAL COLLISION AUDIT REMAINS HOLD",
        (("frozen exterior", SHELL), ("Finger caps", FINGER_CAP), ("original Thumb", CAP)),
    )
    paths.append(path)

    print("[render 6/12] transparent shell", flush=True)
    image, projection, path = save_scene(
        "06_transparent_shell_with_original_cartridge.png", lowered_objects,
        "TRANSPARENT CURRENT SHELL + ORIGINAL CARTRIDGE",
        "EXACT JaD/JfD REVIEW SHELLS SHOWN AS WIREFRAME / CARTRIDGE IS EXACT B-REP",
        "REDESIGN HAS NOT BEEN APPLIED; WIREFRAME REVEALS THE UNALTERED INTERNAL OVERLAY",
        (("shell wireframe", SHELL), ("Backplate", BACKPLATE), ("buttons", PUSHBUTTON), ("HW504", JOYSTICK)),
    )
    wireframe(image, projection, exact_shells)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    print("[render 7/12] joystick alignment close-up", flush=True)
    paths.append(decorated_copy(
        CURRENT_RENDER_DIR / "06_thumb_region_closeup.png",
        RENDER_DIR / "07_joystick_alignment_closeup.png",
        "JOYSTICK ALIGNMENT = PASS",
        f"CENTER ERROR {report_data['alignment']['joystickCenterErrorMm']:.3e} mm / CIRCULAR RECESS + SPLIT OPENING SHARE THE SAME RIGID TRANSFORM",
    ))

    print("[render 8/12] button alignment close-up", flush=True)
    button_path = decorated_copy(
        CURRENT_RENDER_DIR / "06_thumb_region_closeup.png",
        RENDER_DIR / "08_thumb_button_alignment_closeup.png",
        "THUMB BUTTON ALIGNMENT = PASS",
        f"MAX BUTTON CENTER ERROR {report_data['alignment']['maximumButtonCenterErrorMm']:.3e} mm / TRAVEL-AXIS ERROR 0.000 deg",
    )
    button_image = Image.open(button_path).convert("RGBA")
    draw = ImageDraw.Draw(button_image, "RGBA")
    button_pixels = ((822, 486), (523, 595), (778, 657), (975, 604), (578, 738), (1050, 731), (872, 800), (684, 844))
    for index, (x, y) in enumerate(button_pixels, 1):
        draw.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(7, 12, 19, 220), outline=(*CAP, 255), width=2)
        draw.text((x - 5, y - 10), str(index), font=render.font(15, True), fill=(255, 244, 221, 255))
    button_image.convert("RGB").save(button_path, quality=96)
    paths.append(button_path)

    print("[render 9/12] Thumb vs Finger internals", flush=True)
    _, _, path = save_scene(
        "09_thumb_vs_finger_internals.png",
        [*lowered_objects, *carrier_objects, *switch_objects, *collision_objects],
        "ORIGINAL THUMB VS PRESENT FINGER INTERNAL REFERENCES",
        "RED = EXACT POSITIVE-VOLUME INTERSECTION / N1-N2 SWITCHES AND SHARED CARRIER DRIVE THE HOLD",
        f"FINGER CONFLICT = PRESENT / TOTAL SWITCH {report_data['collisionMatrix']['E_thumbCartridgeVsFingerSwitches']['penetrationVolumeMm3']:.3f} mm3 / CARRIER {report_data['collisionMatrix']['F_thumbCartridgeVsFingerCarriers']['penetrationVolumeMm3']:.3f} mm3",
        (("Thumb", CAP), ("Finger switch", FINGER_SWITCH), ("Finger carrier", FINGER_CARRIER), ("collision", COLLISION)),
    )
    paths.append(path)

    print("[render 10/12] shell collision map", flush=True)
    shell_collision_meshes = [mesh for name, mesh in collisions if "__SHELL__" in name]
    image, projection, path = save_scene(
        "10_thumb_vs_shell_collision_map.png",
        [*lowered_objects, *[(mesh, COLLISION) for mesh in shell_collision_meshes]],
        "ORIGINAL THUMB VS CURRENT EXACT REVIEW SHELL",
        "RED = EXACT COMMON B-REP / BACKPLATE + HW504 COMPONENT 1 INTERSECT THE UNCHANGED SHELL",
        f"TOTAL SHELL PENETRATION {report_data['collisionMatrix']['fullCartridgeVsShell']['penetrationVolumeMm3']:.3f} mm3 / NO RELIEF AUTO-GENERATED",
        (("cartridge", CAP), ("exact collision", COLLISION), ("shell wireframe", SHELL)),
    )
    wireframe(image, projection, exact_shells, color=(140, 211, 236, 75), stride_divisor=1000)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    print("[render 11/12] original fastening", flush=True)
    _, _, path = save_scene(
        "11_original_fastening_geometry.png", [*lowered_objects, *screw_objects, *collision_objects],
        "ORIGINAL FASTENING GEOMETRY / ANALYSIS ONLY",
        "THREE M3 SHELL-SIDE AXES REMAIN FIXED; TWO EXACT COLLISION PAIRS OCCUR AT THE LOWERED TARGET",
        f"PENETRATION {report_data['fasteningReuseAnalysis']['targetPenetrationVolumeMm3']:.3f} mm3 / VERDICT = SHELL-SIDE ADAPTER REQUIRED",
        (("original cartridge", CAP), ("original M3 screw", SCREW), ("collision", COLLISION)),
    )
    paths.append(path)

    print("[render 12/12] full annotated internal overview", flush=True)
    image, projection, path = save_scene(
        "12_full_internal_overview.png",
        [*lowered_objects, *carrier_objects, *switch_objects, *screw_objects, *collision_objects],
        "FULL INTERNAL OVERVIEW / ORIGINAL REUSE AUDIT",
        "PART NAMES ARE DIRECTLY ANNOTATED / SHELL IS WIREFRAME / RED IS EXACT COLLISION",
        f"ORIGINAL THUMB REUSE RATIO = {report_data['reuse']['originalThumbReuseRatioPercent']:.1f}% / STOP BEFORE REDESIGN",
        (("Thumb", CAP), ("Finger", FINGER_SWITCH), ("fastener", SCREW), ("collision", COLLISION)),
    )
    wireframe(image, projection, exact_shells, color=(132, 203, 231, 62), stride_divisor=950)

    part_centers = {
        row["partName"]: 0.5 * (
            np.asarray(row["bboxMm"]["min"], dtype=float)
            + np.asarray(row["bboxMm"]["max"], dtype=float)
        )
        for row in report_data["partList"]
    }
    joystick_center = 0.5 * (
        part_centers["THUMB_JOYSTICK_HW504_COMPONENT_1"]
        + part_centers["THUMB_JOYSTICK_HW504_COMPONENT_2"]
    )
    draw_world_label(image, projection, joystick_center, "JOYSTICK", (42, -38), JOYSTICK)
    draw_world_label(image, projection, part_centers["THUMB_BACKPLATE"], "THUMB BACKPLATE", (-180, -25), BACKPLATE)
    draw_world_label(image, projection, part_centers["THUMB_BACKPLATE"], "BUTTON SUPPORT", (-175, 18), SUPPORT, small=True)
    cap_names = [row["partName"] for row in report_data["partList"] if row["category"] == "thumbCap"]
    cap_offsets = ((-95, -55), (-75, -32), (35, -55), (-115, 4), (-80, 4), (35, 4), (-115, 45), (35, 45))
    for index, (name, offset) in enumerate(zip(cap_names, cap_offsets), 1):
        draw_world_label(image, projection, part_centers[name], f"BUTTON {index}", offset, CAP, small=True)
    if screws:
        draw_world_label(image, projection, screws[1][1].reshape(-1, 3).mean(axis=0), "ORIGINAL FASTENER", (32, -15), SCREW)
    if finger_switches:
        n1 = next(mesh for name, mesh in finger_switches if name.startswith("N1_"))
        draw_world_label(image, projection, n1.reshape(-1, 3).mean(axis=0), "FINGER SWITCH", (34, 20), FINGER_SWITCH)
    draw_world_label(image, projection, np.asarray((30.0, 0.0, 15.0)), "SHELL", (35, -18), (140, 211, 236))
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    sheet = contact_sheet(paths)
    print(json.dumps({"renders": [str(path.relative_to(ROOT)) for path in paths], "contactSheet": str(sheet.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
