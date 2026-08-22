"""Render the validated integrated V3 STEP/reference set without rebuilding CAD."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np
from build123d import import_step
from PIL import Image, ImageDraw

from .finger_layout_reset import triangles
from .finger_thumb_integrated_v3 import (
    CHOSEN_FASTENER_OPTION,
    FASTENER_OPTIONS,
    build_boss_half,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_integrated_v3"
RENDER_DIR = ROOT / "renders" / "finger_thumb_integrated_v3"
REFERENCE = OUT_DIR / "FINGER_THUMB_INTEGRATED_V3_REFERENCE.step"

sys.path.insert(0, str(ROOT / "scripts"))
import render_index_its_audit as render  # noqa: E402


SHELL_A = (43, 83, 107)
SHELL_B = (54, 100, 125)
CAP = (63, 207, 137)
THUMB = (231, 143, 52)
BACKPLATE = (187, 113, 46)
SWITCH = (235, 183, 74)
ROOT_METAL = (224, 91, 88)
WIRE = (186, 92, 230)
THUMB_WIRE = (232, 89, 160)
N_FRONT = (74, 198, 214)
N_REAR = (54, 151, 226)
OTHER_CARRIER = (92, 151, 226)
SEAT = (111, 218, 174)
BOSS = (238, 106, 79)
SCREW = (255, 71, 76)


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
    draw.rounded_rectangle((28, 22, 1170, 116), radius=14, fill=(7, 12, 19, 229), outline=(80, 107, 124, 230), width=2)
    draw.text((48, 34), title, font=render.font(34, True), fill=(245, 249, 251, 255))
    draw.text((50, 80), subtitle, font=render.font(18), fill=(183, 202, 213, 255))
    draw.rounded_rectangle((28, render.HEIGHT - 111, render.WIDTH - 28, render.HEIGHT - 28), radius=14, fill=(7, 12, 19, 229), outline=(80, 107, 124, 230), width=2)
    draw.text((48, render.HEIGHT - 92), footer, font=render.font(17, True), fill=(244, 202, 111, 255))
    x = 48
    for label, color in legend:
        draw.ellipse((x, render.HEIGHT - 56, x + 15, render.HEIGHT - 41), fill=(*color, 255))
        draw.text((x + 23, render.HEIGHT - 61), label, font=render.font(14), fill=(226, 235, 240, 255))
        x += max(140, len(label) * 8 + 48)


def save_scene(filename, objects, title, subtitle, footer, legend=(), matrix=None):
    shown = transformed(objects, matrix) if matrix is not None else objects
    image, projection = render.rasterize(shown)
    annotate(image, title, subtitle, footer, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / filename
    image.convert("RGB").save(path, quality=96)
    return image, projection, path


def wireframe(image, projection, meshes, matrix=None, color=(116, 197, 225, 60), divisor=650):
    draw = ImageDraw.Draw(image, "RGBA")
    for mesh in meshes:
        work = mesh @ matrix.T if matrix is not None else mesh
        stride = max(1, len(work) // divisor)
        for triangle in work[::stride]:
            points = render.project(triangle, projection)
            draw.line([tuple(points[0]), tuple(points[1]), tuple(points[2]), tuple(points[0])], fill=color, width=1)


def contact_sheet(paths: list[Path]) -> Path:
    cells = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        image.thumbnail((430, 323), Image.Resampling.LANCZOS)
        cells.append((path.name, image.copy()))
    cols, cell_w, cell_h = 2, 470, 370
    rows = math.ceil(len(cells) / cols)
    sheet = Image.new("RGB", (cols * cell_w, 70 + rows * cell_h), (9, 15, 22))
    draw = ImageDraw.Draw(sheet)
    draw.text((28, 17), "ONEGRIP PLAY / INTEGRATED V3 / VISUAL QC", font=render.font(28, True), fill=(242, 247, 250))
    for index, (name, image) in enumerate(cells):
        x = (index % cols) * cell_w + 20
        y = (index // cols) * cell_h + 62
        sheet.paste(image, (x, y))
        draw.text((x + 4, y + 328), name, font=render.font(14), fill=(202, 216, 225))
    path = RENDER_DIR / "00_contact_sheet.png"
    sheet.save(path, quality=96)
    return path


def main() -> None:
    audit = json.loads((OUT_DIR / "finger_thumb_integrated_v3_validation.json").read_text(encoding="utf-8"))
    clearances = audit["clearances"]
    construction = audit["construction"]
    reference = import_step(REFERENCE)
    rows = [(child.label, triangles(child)) for child in reference.children]
    pick = lambda predicate: [mesh for label, mesh in rows if predicate(label)]

    shells = pick(lambda label: label.startswith(("JAD_FINGER_THUMB", "JFD_FINGER_THUMB")))
    caps = pick(lambda label: label.endswith("_cap"))
    thumb_backplate = pick(lambda label: label == "Backplate")
    thumb_controls = pick(lambda label: label.startswith("Button_") or label == "PushBtn")
    thumb_mechanism = pick(lambda label: label in ("HW504_B", "Small_joystick_attachment"))
    n_front = pick(lambda label: "shared_shell_captured_front_carrier" in label)
    n_rear = pick(lambda label: "removable_rear_restraint" in label)
    other_carriers = pick(lambda label: "carrier" in label and "N1_N2_V3" not in label)
    switches = pick(lambda label: "ITS1105" in label)
    roots = pick(lambda label: "_root_" in label)
    finger_wires = pick(lambda label: "wire_service" in label or "_V3_formed_" in label or "_V3_solder_" in label or "_V3_wire_" in label)
    n_wires = pick(lambda label: label.startswith(("N1_V3_", "N2_V3_")))
    thumb_wires = pick(lambda label: label.startswith("THUMB_V3_wiring"))
    screws = pick(lambda label: label.startswith("V3_M3_class_screw"))
    n_switches = pick(lambda label: label.startswith(("N1_ITS", "N2_ITS", "N1_root", "N2_root")))
    n_caps = pick(lambda label: label in ("N1_cap", "N2_cap"))

    seats = [triangles(import_step(OUT_DIR / "JaD.step")), triangles(import_step(OUT_DIR / "JfD.step"))]
    boss_shapes = []
    for index, (y, z) in enumerate(FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION], 1):
        boss_shapes.extend((triangles(build_boss_half(index, y, z, "JaD")), triangles(build_boss_half(index, y, z, "JfD"))))

    exterior = [
        (shells[0], SHELL_A), (shells[1], SHELL_B),
        *[(mesh, CAP) for mesh in caps],
        *[(mesh, BACKPLATE) for mesh in thumb_backplate],
        *[(mesh, THUMB) for mesh in thumb_controls],
        *[(mesh, THUMB) for mesh in thumb_mechanism],
    ]
    internal = [
        *[(mesh, BACKPLATE) for mesh in thumb_backplate],
        *[(mesh, THUMB) for mesh in thumb_controls],
        *[(mesh, THUMB) for mesh in thumb_mechanism],
        *[(mesh, N_FRONT) for mesh in n_front],
        *[(mesh, N_REAR) for mesh in n_rear],
        *[(mesh, OTHER_CARRIER) for mesh in other_carriers],
        *[(mesh, SWITCH) for mesh in switches],
        *[(mesh, ROOT_METAL) for mesh in roots],
        *[(mesh, WIRE) for mesh in finger_wires],
        *[(mesh, THUMB_WIRE) for mesh in thumb_wires],
        *[(mesh, BOSS) for mesh in boss_shapes],
        *[(mesh, SCREW) for mesh in screws],
    ]

    rear = rot_z(140.0)
    close = rot_x(-14.0) @ rot_z(124.0)
    side = rot_x(10.0) @ rot_z(76.0)
    paths: list[Path] = []

    _, _, path = save_scene(
        "01_complete_exterior.png", exterior,
        "INTEGRATED V3 / COMPLETE EXTERIOR",
        "FROZEN 8 FINGER CAPS + RIGID THUMB TARGET (0,+12.25,-21.00) mm",
        "USER-FACING LAYOUT DIFFERENCE = 0.000 mm",
        (("V3 shell", SHELL_B), ("Finger caps", CAP), ("lowered thumb", THUMB)), rear,
    )
    paths.append(path)

    image, projection, path = save_scene(
        "02_transparent_complete_internals.png", internal,
        "TRANSPARENT COMPLETE INTERNALS",
        "8 ITS-1105 / 6 CARRIER PARTS / SPLIT THUMB SEAT / 3-POINT FASTENING / WIRING",
        "OCCT CLEARANCE AND FRAGMENT GATES = PASS",
        (("carrier", OTHER_CARRIER), ("switch", SWITCH), ("wire", WIRE), ("seat", SEAT), ("boss", BOSS), ("screw", SCREW)), rear,
    )
    wireframe(image, projection, shells, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    _, _, path = save_scene(
        "03_n1_n2_closeup.png",
        [*[(mesh, N_FRONT) for mesh in n_front], *[(mesh, N_REAR) for mesh in n_rear], *[(mesh, SWITCH) for mesh in n_switches], *[(mesh, CAP) for mesh in n_caps], *[(mesh, WIRE) for mesh in n_wires], *[(mesh, BACKPLATE) for mesh in thumb_backplate]],
        "N1/N2 SHARED FRONT SEAT + REMOVABLE REAR RESTRAINT",
        f"HARD-TO-THUMB {clearances['N1HardToThumb']['minimumClearanceMm']:.3f} / {clearances['N2HardToThumb']['minimumClearanceMm']:.3f} mm; WIRING {clearances['N1WiringToThumb']['minimumClearanceMm']:.3f} / {clearances['N2WiringToThumb']['minimumClearanceMm']:.3f} mm",
        f"N2 OPPOSITE-SHELL CLEARANCE {clearances['N2CarrierToOppositeJaD']['minimumClearanceMm']:.3f} mm / EXTERNAL CENTERS UNCHANGED",
        (("front carrier", N_FRONT), ("rear restraint", N_REAR), ("switch/root", SWITCH), ("wire", WIRE), ("thumb backplate", BACKPLATE)), close,
    )
    paths.append(path)

    _, _, path = save_scene(
        "04_thumb_seating_backplate.png",
        [*[(mesh, SEAT) for mesh in seats], *[(mesh, BACKPLATE) for mesh in thumb_backplate], *[(mesh, THUMB) for mesh in thumb_controls], *[(mesh, THUMB) for mesh in thumb_mechanism]],
        "THUMB SPLIT SEATING FLANGE / THREE CONFORMAL PADS",
        f"CONTINUOUS 1.60 mm FRAME / POSITIVE SHELL OVERLAP {construction['seatToShellPositiveOverlapMm3']['JaD']:.2f} + {construction['seatToShellPositiveOverlapMm3']['JfD']:.2f} mm3",
        "RIGID MODULE LIFTS OUT AFTER SHELL OPENING; NO ADHESIVE REQUIRED",
        (("split seat halves", SEAT), ("exact Backplate", BACKPLATE), ("thumb controls", THUMB)), close,
    )
    paths.append(path)

    _, _, path = save_scene(
        "05_new_screw_boss_architecture.png",
        [*[(mesh, BOSS) for mesh in boss_shapes], *[(mesh, SCREW) for mesh in screws], *[(mesh, BACKPLATE) for mesh in thumb_backplate], *[(mesh, THUMB) for mesh in thumb_mechanism]],
        "OPTION C / REDISTRIBUTED POSTERIOR 3-POINT FASTENING",
        "SCREW AXES +X / (Y,Z)=(10,35),(25,8),(15.8,-21.35) mm",
        "SCREW-TO-THUMB 5.349 mm / BOSS-TO-THUMB 3.499 mm / RADIAL WALL 1.80 mm",
        (("boss + 3.20 mm web", BOSS), ("M3-class screw envelope", SCREW), ("thumb mechanism", THUMB)), side,
    )
    paths.append(path)

    exploded_carriers = []
    all_carriers = [*n_front, *n_rear, *other_carriers]
    for index, mesh in enumerate(all_carriers):
        delta = ((index - 2.5) * 15.0, 0.0, (index % 2) * 9.0)
        color = N_FRONT if index == 0 else N_REAR if index == 1 else OTHER_CARRIER
        exploded_carriers.append((moved(mesh, delta), color))
    _, _, path = save_scene(
        "06_finger_carriers_exploded.png", exploded_carriers,
        "FINGER CARRIER GROUPING / SIX SERVICE PARTS",
        "N FRONT + N REAR / I2-I3 / M4-N3 / I4 / M3",
        "BROAD FDM WALLS; NO HOOKS, FLOATING RIBS OR TANGENT-ONLY BRIDGES",
        (("N shared front", N_FRONT), ("N rear restraint", N_REAR), ("other groups", OTHER_CARRIER)), rear,
    )
    paths.append(path)

    thumb_exploded = [
        *[(moved(mesh, (-24, 0, 0)), SEAT) for mesh in seats[:1]],
        *[(moved(mesh, (24, 0, 0)), SEAT) for mesh in seats[1:]],
        *[(mesh, BACKPLATE) for mesh in thumb_backplate],
        *[(moved(mesh, (0, 0, 9)), THUMB) for mesh in thumb_controls],
        *[(moved(mesh, (0, 0, -8)), THUMB) for mesh in thumb_mechanism],
    ]
    _, _, path = save_scene(
        "07_thumb_exploded.png", thumb_exploded,
        "THUMB MODULE / SERVICE EXPLODED VIEW",
        "SPLIT SEAT HALVES OPEN; RIGID CONTROL CLUSTER REMAINS UNMODIFIED",
        "BACKPLATE SEATS ON THREE CONFORMAL PADS AND IS CAPTURED BY SHELL CLOSURE",
        (("seat half", SEAT), ("Backplate", BACKPLATE), ("thumb controls/mechanism", THUMB)), close,
    )
    paths.append(path)

    _, _, path = save_scene(
        "08_wiring_routes.png",
        [*[(mesh, WIRE) for mesh in finger_wires], *[(mesh, THUMB_WIRE) for mesh in thumb_wires], *[(mesh, ROOT_METAL) for mesh in roots], *[(mesh, BOSS) for mesh in boss_shapes], *[(mesh, SWITCH) for mesh in switches]],
        "FINGER + THUMB WIRING ROUTES",
        "FIXED ROOT -> ONE-TIME FORMED LEAD -> SOLDER -> INSULATED WIRE -> POSTERIOR CORRIDOR",
        "FINGER WIRE-TO-BOSS 15.900 mm / THUMB WIRE-TO-BOSS 10.049 mm",
        (("Finger wire", WIRE), ("thumb corridor", THUMB_WIRE), ("terminal root", ROOT_METAL), ("boss", BOSS)), side,
    )
    paths.append(path)

    closing = [
        (moved(shells[0], (24, 0, 0)), SHELL_A),
        (moved(shells[1], (-24, 0, 0)), SHELL_B),
        *[(mesh, N_FRONT) for mesh in n_front], *[(mesh, N_REAR) for mesh in n_rear],
        *[(mesh, BACKPLATE) for mesh in thumb_backplate], *[(mesh, THUMB) for mesh in thumb_controls],
        *[(mesh, SCREW) for mesh in screws],
    ]
    _, _, path = save_scene(
        "09_shell_closing_view.png", closing,
        "SHELL CLOSING VIEW",
        f"JfD LOCATES N CARRIER; JaD PROVIDES {clearances['N2CarrierToOppositeJaD']['minimumClearanceMm']:.3f} mm N2 SERVICE RELIEF",
        "CLOSURE CAPTURES N REAR RESTRAINT AND SPLIT THUMB FLANGE BEFORE SCREW INSTALL",
        (("JaD/JfD", SHELL_B), ("N carrier", N_FRONT), ("thumb", THUMB), ("screw", SCREW)), rear,
    )
    paths.append(path)

    service = [
        (moved(shells[0], (34, 0, 0)), SHELL_A),
        (moved(shells[1], (-34, 0, 0)), SHELL_B),
        *[(moved(mesh, (0, 18, 16)), THUMB) for mesh in [*thumb_backplate, *thumb_controls, *thumb_mechanism]],
        *[(moved(mesh, (-8, -5, -15)), N_REAR) for mesh in n_rear],
        *[(moved(mesh, (0, -4, -8)), N_FRONT) for mesh in n_front],
        *[(moved(mesh, (0, -25, 0)), SCREW) for mesh in screws],
    ]
    _, _, path = save_scene(
        "10_service_disassembly.png", service,
        "SERVICE / DISASSEMBLY SEQUENCE",
        "REMOVE 3 SCREWS -> OPEN SHELLS -> LIFT THUMB -> REMOVE N RESTRAINT -> WITHDRAW SWITCHES",
        "ALL PRIMARY MODULES ARE REOPENABLE; STRUCTURAL ADHESIVE = 0",
        (("shell halves", SHELL_B), ("thumb module", THUMB), ("N service parts", N_FRONT), ("screws", SCREW)), rear,
    )
    paths.append(path)

    sheet = contact_sheet(paths)
    print(json.dumps({"gates": audit["gates"], "renders": [str(path) for path in paths], "contactSheet": str(sheet)}, indent=2))


if __name__ == "__main__":
    main()
