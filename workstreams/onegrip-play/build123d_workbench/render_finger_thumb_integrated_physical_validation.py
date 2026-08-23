"""Render the integrated Finger + lowered Thumb physical validation kit."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np
from build123d import import_step
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_integrated_physical_validation"
V3_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_integrated_v3"
RENDER_DIR = OUT_DIR / "renders"
REFERENCE = OUT_DIR / "FINGER_THUMB_INTEGRATED_FUNCTIONAL_SECTION.step"

sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402

from .finger_layout_reset import triangles  # noqa: E402
from .finger_thumb_integrated_v3 import (  # noqa: E402
    CHOSEN_FASTENER_OPTION,
    FASTENER_OPTIONS,
    build_boss_half,
)


SHELL_A = (42, 78, 98)
SHELL_B = (53, 96, 117)
CAP = (54, 207, 133)
THUMB = (225, 139, 47)
BACKPLATE = (194, 111, 38)
N_FRONT = (49, 184, 200)
N_REAR = (174, 79, 202)
CARRIER = (76, 132, 210)
SWITCH = (238, 184, 66)
WIRE = (195, 69, 205)
THUMB_WIRE = (228, 68, 120)
BOSS = (221, 102, 75)
SCREW = (245, 75, 76)
PLATE_A = (78, 160, 204)
PLATE_B = (81, 193, 142)
GHOST = (104, 196, 225)
SEAT = (94, 214, 167)


def rot_z(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0)))


def rot_x(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c)))


def moved(mesh: np.ndarray, delta) -> np.ndarray:
    return mesh + np.asarray(delta, dtype=float)


def transformed(objects, matrix):
    return [(mesh @ matrix.T, color) for mesh, color in objects]


def annotate(image: Image.Image, title: str, subtitle: str, footer: str, legend=()) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((28, 22, 1260, 112), radius=14, fill=(7, 12, 19, 230), outline=(80, 105, 120, 220), width=2)
    draw.text((48, 34), title, font=render.font(34, True), fill=(244, 248, 250, 255))
    draw.text((50, 79), subtitle, font=render.font(17), fill=(181, 199, 210, 255))
    draw.rounded_rectangle((28, render.HEIGHT - 110, render.WIDTH - 28, render.HEIGHT - 28), radius=14, fill=(7, 12, 19, 226), outline=(70, 94, 110, 220), width=2)
    draw.text((48, render.HEIGHT - 96), footer, font=render.font(17, True), fill=(244, 198, 91, 255))
    x = 48
    for label, color in legend:
        draw.ellipse((x, render.HEIGHT - 60, x + 16, render.HEIGHT - 44), fill=(*color, 255))
        draw.text((x + 24, render.HEIGHT - 66), label, font=render.font(14), fill=(225, 234, 239, 255))
        x += max(155, len(label) * 8 + 48)


def save_scene(filename, objects, title, subtitle, footer, legend=(), matrix=None):
    if matrix is not None:
        objects = transformed(objects, matrix)
    image, projection = render.rasterize(objects)
    annotate(image, title, subtitle, footer, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / filename
    image.convert("RGB").save(path, quality=96)
    return image, projection, path


def shell_wireframe(image, projection, meshes, matrix=None):
    draw = ImageDraw.Draw(image, "RGBA")
    for mesh in meshes:
        work = mesh @ matrix.T if matrix is not None else mesh
        stride = max(1, len(work) // 55)
        for triangle in work[::stride]:
            points = render.project(triangle, projection)
            draw.line([tuple(points[0]), tuple(points[1]), tuple(points[2]), tuple(points[0])], fill=(*GHOST, 48), width=1)


def contact_sheet(paths: list[Path]) -> Path:
    columns, cell_w, cell_h = 3, 470, 390
    rows = math.ceil(len(paths) / columns)
    sheet = Image.new("RGB", (columns * cell_w, 78 + rows * cell_h), (9, 15, 23))
    draw = ImageDraw.Draw(sheet)
    draw.text((28, 18), "FINGER + LOWERED THUMB / PHYSICAL VALIDATION KIT / VISUAL QC", font=render.font(29, True), fill=(242, 247, 250))
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
    audit = json.loads((OUT_DIR / "finger_thumb_integrated_physical_validation.json").read_text(encoding="utf-8"))
    source = import_step(REFERENCE)
    rows = [(child.label, triangles(child)) for child in source.children]
    pick = lambda predicate: [mesh for label, mesh in rows if predicate(label)]

    shell_meshes = [
        read_binary_stl(OUT_DIR / "JAD_VALIDATION_SECTION.stl"),
        read_binary_stl(OUT_DIR / "JFD_VALIDATION_SECTION.stl"),
    ]
    caps = pick(lambda label: label.endswith("_cap"))
    n_caps = pick(lambda label: label in ("N1_cap", "N2_cap"))
    n_front = pick(lambda label: "shared_shell_captured_front_carrier" in label)
    n_rear = pick(lambda label: "removable_rear_restraint" in label)
    other_carriers = pick(lambda label: "carrier" in label and "N1_N2_V3" not in label)
    switches = pick(lambda label: "ITS1105" in label)
    n_switches = pick(lambda label: label.startswith(("N1_ITS", "N2_ITS")))
    thumb_backplate = pick(lambda label: label == "Backplate")
    thumb_controls = pick(lambda label: label.startswith("Button_") or label == "PushBtn")
    thumb_mechanism = pick(lambda label: label in ("HW504_B", "Small_joystick_attachment"))
    finger_wires = pick(lambda label: label.endswith("wire_service_envelope") or label.startswith(("N1_V3_", "N2_V3_")))
    n_wires = pick(lambda label: label.startswith(("N1_V3_", "N2_V3_")))
    thumb_wires = pick(lambda label: label.startswith("THUMB_V3_wiring_corridor_"))
    screws = pick(lambda label: label.startswith("V3_M3_class_screw_"))

    seats = [triangles(import_step(V3_DIR / "JaD.step")), triangles(import_step(V3_DIR / "JfD.step"))]
    bosses = []
    for index, (y, z) in enumerate(FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION], 1):
        bosses.extend((triangles(build_boss_half(index, y, z, "JaD")), triangles(build_boss_half(index, y, z, "JfD"))))

    rear = rot_z(140.0)
    close = rot_x(-14.0) @ rot_z(124.0)
    side = rot_x(12.0) @ rot_z(78.0)
    paths: list[Path] = []

    assembled = [
        (shell_meshes[0], SHELL_A), (shell_meshes[1], SHELL_B),
        *[(mesh, CAP) for mesh in caps],
        *[(mesh, BACKPLATE) for mesh in thumb_backplate],
        *[(mesh, THUMB) for mesh in [*thumb_controls, *thumb_mechanism]],
    ]
    _, _, path = save_scene(
        "01_assembled_validation_section.png", assembled,
        "ASSEMBLED INTEGRATED FUNCTIONAL SECTION",
        "1:1 V3 INTERFACES / 8 FINGER CAPS / LOWERED THUMB / THREE OPTION-C BOSSES",
        "FULL PRODUCTION SHELL IS NOT INCLUDED",
        (("cropped shell", SHELL_B), ("Finger caps", CAP), ("thumb module", THUMB)), rear,
    )
    paths.append(path)

    exploded = [
        (moved(shell_meshes[0], (34, 0, 0)), SHELL_A),
        (moved(shell_meshes[1], (-34, 0, 0)), SHELL_B),
        *[(moved(mesh, (0, -8, 0)), N_FRONT) for mesh in n_front],
        *[(moved(mesh, (0, -14, 0)), N_REAR) for mesh in n_rear],
        *[(moved(mesh, (0, 10, 0)), CARRIER) for mesh in other_carriers],
        *[(moved(mesh, (0, 18, 12)), THUMB) for mesh in [*thumb_backplate, *thumb_controls, *thumb_mechanism]],
        *[(moved(mesh, (0, -22, 0)), CAP) for mesh in caps],
    ]
    _, _, path = save_scene(
        "02_exploded_validation_section.png", exploded,
        "EXPLODED VALIDATION SECTION",
        "SHELLS / SIX CARRIER PARTS / EIGHT CAPS / RIGID THUMB REFERENCE",
        "ASSEMBLY ORDER REMAINS IDENTICAL TO V3",
        (("shell", SHELL_B), ("N front/rear", N_FRONT), ("other carriers", CARRIER), ("thumb", THUMB)), rear,
    )
    paths.append(path)

    internals = [
        *[(mesh, N_FRONT) for mesh in n_front], *[(mesh, N_REAR) for mesh in n_rear],
        *[(mesh, CARRIER) for mesh in other_carriers], *[(mesh, SWITCH) for mesh in switches],
        *[(mesh, WIRE) for mesh in finger_wires], *[(mesh, THUMB_WIRE) for mesh in thumb_wires],
        *[(mesh, BACKPLATE) for mesh in thumb_backplate], *[(mesh, THUMB) for mesh in [*thumb_controls, *thumb_mechanism]],
        *[(mesh, BOSS) for mesh in bosses], *[(mesh, SCREW) for mesh in screws],
    ]
    image, projection, path = save_scene(
        "03_transparent_internals.png", internals,
        "TRANSPARENT INTERNALS",
        "8 ITS-1105 / 6 CARRIER PARTS / THUMB SEAT / WIRING / 3-POINT FASTENING",
        "DIGITAL MOTION, CLOSURE, WIRING AND FRAGMENT GATES = PASS",
        (("carrier", CARRIER), ("switch", SWITCH), ("wire", WIRE), ("boss", BOSS), ("screw", SCREW)), rear,
    )
    shell_wireframe(image, projection, shell_meshes, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    n_scene = [
        *[(mesh, N_FRONT) for mesh in n_front], *[(mesh, N_REAR) for mesh in n_rear],
        *[(mesh, CAP) for mesh in n_caps], *[(mesh, SWITCH) for mesh in n_switches],
        *[(mesh, WIRE) for mesh in n_wires], *[(mesh, BACKPLATE) for mesh in thumb_backplate],
    ]
    _, _, path = save_scene(
        "04_n1_n2_physical_region.png", n_scene,
        "N1/N2 CRITICAL PHYSICAL REGION",
        "SHARED FRONT RING / REMOVABLE REAR RESTRAINT / TERMINAL EXITS / N2 SEAM CAPTURE",
        "N2 OPPOSITE-SHELL DIGITAL CLEARANCE 1.054 mm / PHYSICAL JAM TEST REQUIRED",
        (("front carrier", N_FRONT), ("rear restraint", N_REAR), ("ITS", SWITCH), ("wire", WIRE)), close,
    )
    paths.append(path)

    thumb_scene = [
        *[(mesh, SEAT) for mesh in seats], *[(mesh, BACKPLATE) for mesh in thumb_backplate],
        *[(mesh, THUMB) for mesh in [*thumb_controls, *thumb_mechanism]],
    ]
    _, _, path = save_scene(
        "05_thumb_seat_physical_region.png", thumb_scene,
        "LOWERED THUMB PHYSICAL SEAT",
        "1.60 mm SPLIT FLANGE / 42x64 OUTER / 34x56 INNER / THREE 5 mm PADS",
        "TEST INSERT / FULL SEATING / ROCKING / CLOSED-SHELL RETENTION / REMOVAL",
        (("seat halves", SEAT), ("Backplate", BACKPLATE), ("thumb hardware", THUMB)), close,
    )
    paths.append(path)

    screw_scene = [
        *[(mesh, BOSS) for mesh in bosses], *[(mesh, SCREW) for mesh in screws],
        *[(mesh, BACKPLATE) for mesh in thumb_backplate], *[(mesh, THUMB) for mesh in thumb_mechanism],
    ]
    _, _, path = save_scene(
        "06_three_screw_bosses.png", screw_scene,
        "OPTION C / THREE SCREW-BOSS PHYSICAL TEST",
        "+X AXES / (Y,Z)=(10,35),(25,8),(15.8,-21.35) mm / M3x16 CANDIDATE",
        "CHECK DRIVER ACCESS / CLAMP / CRACKING / REPEATED DISASSEMBLY",
        (("boss + web", BOSS), ("M3 envelope", SCREW), ("thumb", THUMB)), side,
    )
    paths.append(path)

    wiring_scene = [
        *[(mesh, WIRE) for mesh in finger_wires], *[(mesh, THUMB_WIRE) for mesh in thumb_wires],
        *[(mesh, SWITCH) for mesh in switches], *[(mesh, BOSS) for mesh in bosses],
    ]
    _, _, path = save_scene(
        "07_wiring_physical_routes.png", wiring_scene,
        "FINGER + THUMB PHYSICAL WIRING ROUTES",
        "RECOMMENDED INSULATED OD 0.8-1.2 mm / N INDIVIDUAL MAX 1.6 / THUMB BUNDLE MAX 2.8",
        "CLOSE BOTH SHELLS WITH REAL WIRES: PINCH MUST BE NONE",
        (("Finger wiring", WIRE), ("thumb corridor", THUMB_WIRE), ("switch", SWITCH), ("boss", BOSS)), side,
    )
    paths.append(path)

    plate_a = read_binary_stl(OUT_DIR / "VALIDATION_PLATE_A.stl")
    _, _, path = save_scene(
        "08_print_orientation.png", [(plate_a, PLATE_A)],
        "PLATE A / SHELL PRINT ORIENTATION",
        "X=0 SEAM FACES ON BED / SCREW AXES UP / 202 x 80 mm",
        "NO SUPPORT ON CAP GUIDES, N2 SEAM, THUMB PADS OR SCREW BORES",
        (("two shell sections", PLATE_A),), rot_x(15.0),
    )
    paths.append(path)

    plate_b = read_binary_stl(OUT_DIR / "VALIDATION_PLATE_B.stl")
    plates = [(plate_a, PLATE_A), (moved(plate_b, (0, -58, 0)), PLATE_B)]
    _, _, path = save_scene(
        "09_validation_print_plates.png", plates,
        "VALIDATION PRINT PLATES A + B",
        "A: TWO SHELL SECTIONS / B: FIT COUPON + 6 CARRIERS + 8 CAPS",
        "FUNCTIONAL ORIENTATION TAKES PRIORITY OVER ONE-PLATE PACKING",
        (("Plate A", PLATE_A), ("Plate B", PLATE_B)), rot_x(15.0),
    )
    paths.append(path)

    contact = contact_sheet(paths)
    print(json.dumps({
        "renders": [str(path) for path in paths],
        "contactSheet": str(contact),
        "verdict": audit["verdict"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
