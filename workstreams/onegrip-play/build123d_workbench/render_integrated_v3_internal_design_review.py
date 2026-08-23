"""Internal-design review renders for Finger + lowered Thumb Integrated V3.

The renderer consumes existing V3 STEP data and creates PNG explanations only.
No STL, print plate, mockup, or production CAD is exported.
"""

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
    build_fastener_screw,
)
from .integrated_v3_internal_design_review import (
    JAD_STEP,
    JFD_STEP,
    REFERENCE_STEP,
    SOURCE_DIR,
    apply_final_fastener_bores,
    center_box,
    route_from_points,
)


ROOT = Path(__file__).resolve().parents[1]
REVIEW_JSON = ROOT / "build123d_workbench" / "out" / "finger_thumb_integrated_v3_internal_review" / "integrated_v3_internal_design_review.json"
RENDER_DIR = ROOT / "renders" / "finger_thumb_integrated_v3_internal_review"

sys.path.insert(0, str(ROOT / "scripts"))
import render_index_its_audit as render  # noqa: E402


SHELL_A = (40, 76, 96)
SHELL_B = (53, 94, 117)
CAP = (55, 196, 132)
THUMB = (223, 137, 48)
BACKPLATE = (172, 101, 41)
SWITCH = (231, 177, 68)
ROOT_METAL = (226, 83, 76)
WIRE_BAD = (239, 73, 88)
WIRE_FINGER = (173, 88, 222)
WIRE_THUMB = (226, 82, 154)
WIRE_CANDIDATE = (78, 215, 166)
N_FRONT = (62, 196, 211)
N_REAR = (43, 144, 219)
CARRIER_1 = (81, 137, 225)
CARRIER_2 = (118, 108, 225)
CARRIER_3 = (92, 177, 207)
CARRIER_4 = (152, 109, 213)
SEAT = (101, 211, 165)
BOSS = (235, 101, 72)
SCREW = (255, 66, 70)
BORE = (92, 226, 188)
ELECTRONICS = (238, 201, 91)
BATTERY = (112, 205, 112)


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
    draw.rounded_rectangle((24, 18, render.WIDTH - 24, 112), radius=13, fill=(7, 12, 19, 231), outline=(74, 105, 124, 235), width=2)
    draw.text((44, 30), title, font=render.font(31, True), fill=(245, 249, 251, 255))
    draw.text((45, 76), subtitle, font=render.font(17), fill=(182, 203, 214, 255))
    draw.rounded_rectangle((24, render.HEIGHT - 112, render.WIDTH - 24, render.HEIGHT - 24), radius=13, fill=(7, 12, 19, 231), outline=(74, 105, 124, 235), width=2)
    draw.text((44, render.HEIGHT - 92), footer, font=render.font(16, True), fill=(244, 198, 103, 255))
    x = 44
    for label, color in legend:
        draw.ellipse((x, render.HEIGHT - 57, x + 14, render.HEIGHT - 43), fill=(*color, 255))
        draw.text((x + 21, render.HEIGHT - 61), label, font=render.font(13), fill=(226, 235, 240, 255))
        x += max(120, len(label) * 7 + 42)


def save_scene(filename, objects, title, subtitle, footer, legend=(), matrix=None):
    shown = transformed(objects, matrix) if matrix is not None else objects
    image, projection = render.rasterize(shown)
    annotate(image, title, subtitle, footer, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / filename
    image.convert("RGB").save(path, quality=96)
    return image, projection, path


def wireframe(image, projection, meshes, matrix=None, color=(111, 194, 224, 70), divisor=800):
    draw = ImageDraw.Draw(image, "RGBA")
    for mesh in meshes:
        work = mesh @ matrix.T if matrix is not None else mesh
        stride = max(1, len(work) // divisor)
        for triangle in work[::stride]:
            points = render.project(triangle, projection)
            draw.line([tuple(points[0]), tuple(points[1]), tuple(points[2]), tuple(points[0])], fill=color, width=1)


def callouts(image, projection, rows, matrix=None):
    draw = ImageDraw.Draw(image, "RGBA")
    for label, point, text_xy, color in rows:
        work = np.asarray(point, dtype=float)
        if matrix is not None:
            work = work @ matrix.T
        anchor = render.project(np.asarray([work]), projection)[0]
        tx, ty = text_xy
        text_box = draw.textbbox((tx, ty), label, font=render.font(14, True))
        draw.rounded_rectangle((text_box[0] - 6, text_box[1] - 4, text_box[2] + 6, text_box[3] + 4), radius=5, fill=(7, 12, 19, 225), outline=(*color, 240), width=2)
        draw.text((tx, ty), label, font=render.font(14, True), fill=(240, 246, 249, 255))
        edge_x = text_box[2] + 6 if anchor[0] > tx else text_box[0] - 6
        edge_y = 0.5 * (text_box[1] + text_box[3])
        draw.line((edge_x, edge_y, float(anchor[0]), float(anchor[1])), fill=(*color, 235), width=2)
        draw.ellipse((float(anchor[0]) - 4, float(anchor[1]) - 4, float(anchor[0]) + 4, float(anchor[1]) + 4), fill=(*color, 255))


def mesh_center(mesh: np.ndarray) -> np.ndarray:
    points = mesh.reshape((-1, 3))
    return 0.5 * (points.min(axis=0) + points.max(axis=0))


def contact_sheet(paths: list[Path]) -> Path:
    cells = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        image.thumbnail((405, 304), Image.Resampling.LANCZOS)
        cells.append((path.name, image.copy()))
    cols, cell_w, cell_h = 3, 435, 348
    rows = math.ceil(len(cells) / cols)
    sheet = Image.new("RGB", (cols * cell_w, 72 + rows * cell_h), (9, 15, 22))
    draw = ImageDraw.Draw(sheet)
    draw.text((26, 17), "ONEGRIP PLAY / INTEGRATED V3 INTERNAL DESIGN REVIEW", font=render.font(27, True), fill=(242, 247, 250))
    for index, (name, image) in enumerate(cells):
        x = (index % cols) * cell_w + 15
        y = (index // cols) * cell_h + 62
        sheet.paste(image, (x, y))
        draw.text((x + 4, y + 309), name, font=render.font(12), fill=(202, 216, 225))
    path = RENDER_DIR / "00_contact_sheet.png"
    sheet.save(path, quality=96)
    return path


def main() -> None:
    audit = json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    reference = import_step(REFERENCE_STEP)
    jad = import_step(JAD_STEP)
    jfd = import_step(JFD_STEP)
    jad_bored, jfd_bored, _ = apply_final_fastener_bores(jad, jfd)

    children = {index: child for index, child in enumerate(reference.children)}
    rows = [(child.label, triangles(child)) for child in children.values()]
    pick = lambda predicate: [mesh for label, mesh in rows if predicate(label)]
    pick_named = lambda exact: next(mesh for label, mesh in rows if label == exact)

    shell_meshes = [pick_named("JAD_FINGER_THUMB_INTEGRATED_V3"), pick_named("JFD_FINGER_THUMB_INTEGRATED_V3")]
    jad_mesh, jfd_mesh = shell_meshes
    caps = pick(lambda label: label.endswith("_cap"))
    switches = pick(lambda label: "ITS1105" in label)
    roots = pick(lambda label: "_root_" in label)
    thumb_backplate = pick(lambda label: label == "Backplate")
    thumb_controls = pick(lambda label: label.startswith("Button_") or label == "PushBtn")
    thumb_mechanism = pick(lambda label: label in ("HW504_B", "Small_joystick_attachment"))
    current_finger_wires = pick(lambda label: "wire_service_envelope" in label or "_V3_formed_" in label or "_V3_solder_" in label or "_V3_wire_" in label)
    current_thumb_wires = pick(lambda label: label.startswith("THUMB_V3_wiring_corridor"))
    penetrating_n1_wires = pick(lambda label: label in audit["wiring"]["currentN1ShellPenetratingSegments"])

    carrier_rows = [
        ("N1/N2 front carrier", pick_named("N1_N2_V3_shared_shell_captured_front_carrier"), N_FRONT),
        ("N1/N2 rear restraint", pick_named("N1_N2_V3_removable_rear_restraint"), N_REAR),
        ("I2/I3 carrier", pick_named("I2_I3_shared_C_channel_carrier"), CARRIER_1),
        ("M4/N3 carrier", pick_named("M4_N3_shared_C_channel_carrier"), CARRIER_2),
        ("I4 carrier", pick_named("I4_C_channel_carrier"), CARRIER_3),
        ("M3 carrier", pick_named("M3_C_channel_carrier"), CARRIER_4),
    ]
    carrier_meshes = [mesh for _, mesh, _ in carrier_rows]
    n_caps = pick(lambda label: label in ("N1_cap", "N2_cap"))
    n_switches = pick(lambda label: label.startswith(("N1_ITS", "N2_ITS", "N1_root", "N2_root")))
    n_wires = pick(lambda label: label.startswith(("N1_V3_", "N2_V3_")))

    seats = [triangles(import_step(SOURCE_DIR / "JaD.step")), triangles(import_step(SOURCE_DIR / "JfD.step"))]
    bosses = []
    screws = []
    boss_shapes = []
    screw_shapes = []
    for index, (y, z) in enumerate(FASTENER_OPTIONS[CHOSEN_FASTENER_OPTION], 1):
        for owner in ("JaD", "JfD"):
            shape = build_boss_half(index, y, z, owner)
            boss_shapes.append(shape)
            bosses.append(triangles(shape))
        screw = build_fastener_screw(index, y, z)
        screw_shapes.append(screw)
        screws.append(triangles(screw))

    finger_candidate_shapes = route_from_points(((0.0, 4.0, -16.0), (0.0, 4.0, -24.0), (0.0, 9.0, -40.0)), 4.0, "REVIEW_finger_shared_trunk")
    thumb_candidate_shapes = route_from_points(((9.0, 12.0, 4.0), (8.0, 7.0, -12.0), (6.0, 10.0, -32.0), (6.0, 18.0, -45.0)), 3.2, "REVIEW_thumb_inboard_trunk")
    finger_candidate = [triangles(shape) for shape in finger_candidate_shapes]
    thumb_candidate = [triangles(shape) for shape in thumb_candidate_shapes]
    electronics = [
        triangles(center_box((27.0, 17.0, 6.0), (0.0, 20.0, -40.0), "MCU_IO_CONNECTOR_RESERVE")),
        triangles(center_box((16.0, 18.0, 7.0), (0.0, 27.0, -51.0), "COMPACT_BATTERY_RESERVE")),
    ]

    rear = rot_x(-8.0) @ rot_z(142.0)
    left = rot_x(-10.0) @ rot_z(118.0)
    right = rot_x(8.0) @ rot_z(64.0)
    section_view = rot_x(4.0) @ rot_z(90.0)
    paths: list[Path] = []

    internal = [
        *[(mesh, color) for _, mesh, color in carrier_rows],
        *[(mesh, SWITCH) for mesh in switches], *[(mesh, ROOT_METAL) for mesh in roots],
        *[(mesh, BACKPLATE) for mesh in thumb_backplate], *[(mesh, THUMB) for mesh in [*thumb_controls, *thumb_mechanism]],
        *[(mesh, WIRE_FINGER) for mesh in current_finger_wires], *[(mesh, WIRE_THUMB) for mesh in current_thumb_wires],
        *[(mesh, SEAT) for mesh in seats], *[(mesh, BOSS) for mesh in bosses], *[(mesh, SCREW) for mesh in screws],
    ]
    image, projection, path = save_scene(
        "01_transparent_full_assembly.png", internal,
        "TRANSPARENT FULL ASSEMBLY / CURRENT V3",
        "8 SWITCHES / 6 SERVICE PARTS / THUMB SEAT / 3 FASTENERS / CURRENT WIRING ENVELOPES",
        "DIGITAL FIT PASSED, BUT MECHANICAL ARCHITECTURE REVIEW = REVISE",
        (("carrier", CARRIER_1), ("switch", SWITCH), ("thumb", THUMB), ("wire", WIRE_FINGER), ("boss/screw", BOSS)), rear,
    )
    wireframe(image, projection, shell_meshes, rear)
    image.convert("RGB").save(path, quality=96); paths.append(path)

    _, _, path = save_scene(
        "02_JaD_removed.png",
        [(jfd_mesh, SHELL_B), *internal],
        "JaD REMOVED / JfD LOCATING-SIDE VIEW",
        "I2/I3 + M3 + N1/N2 LOCATING GEOMETRY AND TERMINAL ROUTES",
        "N2 FRONT LOCATOR IS SOUND; LOOSE REAR RESTRAINT AND N1 WIRE/SHELL CROSSING REQUIRE REVISION",
        (("JfD", SHELL_B), ("N front", N_FRONT), ("N rear", N_REAR), ("wire issue", WIRE_BAD)), left,
    ); paths.append(path)

    _, _, path = save_scene(
        "03_JfD_removed.png",
        [(jad_mesh, SHELL_A), *internal],
        "JfD REMOVED / JaD CAPTURE-SIDE VIEW",
        "I4 + M4/N3 + THUMB SEAT + POSTERIOR BOSS NETWORK",
        "JaD IS CLEARANCE/CAPTURE FOR N2; CURRENT THUMB TRUNK DOES NOT ENTER THE LOWER HANDLE",
        (("JaD", SHELL_A), ("JaD carriers", CARRIER_2), ("thumb seat", SEAT), ("boss", BOSS)), right,
    ); paths.append(path)

    carrier_objects = [(mesh, color) for _, mesh, color in carrier_rows]
    image, projection, path = save_scene(
        "04_all_carriers_highlighted_annotated.png", carrier_objects,
        "ALL SIX CARRIER/SERVICE PARTS / ANNOTATED",
        "FOUR ESTABLISHED GROUPS KEEP AS-IS / N FRONT+REAR PAIR REQUIRES A BROAD POSITIVE KEY",
        "PART COUNT 6 IS NOT THE PROBLEM; THE N REAR RESTRAINT HAS NO POSITIVE LOCATION BEFORE CLOSURE",
        tuple((label.split()[0], color) for label, _, color in carrier_rows), rear,
    )
    label_positions = [(44, 145), (44, 205), (44, 265), (900, 145), (900, 205), (900, 265)]
    callouts(image, projection, [(label, mesh_center(mesh), pos, color) for (label, mesh, color), pos in zip(carrier_rows, label_positions)], rear)
    image.convert("RGB").save(path, quality=96); paths.append(path)

    n_front_mesh, n_rear_mesh = carrier_rows[0][1], carrier_rows[1][1]
    n_exploded = [
        (moved(n_front_mesh, (0, 0, -6)), N_FRONT),
        (moved(n_rear_mesh, (0, 15, 10)), N_REAR),
        *[(mesh, SWITCH) for mesh in n_switches], *[(mesh, CAP) for mesh in n_caps],
        *[(mesh, WIRE_BAD if any(np.array_equal(mesh, bad) for bad in penetrating_n1_wires) else WIRE_FINGER) for mesh in n_wires],
    ]
    _, _, path = save_scene(
        "05_N1_N2_exploded.png", n_exploded,
        "N1/N2 EXPLODED / FRONT LOCATOR + LOOSE REAR STOP",
        "REAR->SHELL 0.925 mm / TERMINAL ROOT CLEARANCE 0.506 mm / POSITIVE REAR KEY COUNT 0",
        "KEEP TWO-STAGE SERVICE CONCEPT; ADD >=1.60 mm BROAD KEY, >=3 mm ENGAGEMENT, 0.25-0.40 mm CLOSED FLOAT",
        (("front carrier", N_FRONT), ("rear restraint", N_REAR), ("switch/root", SWITCH), ("shell-crossing N1 wire", WIRE_BAD)), left,
    ); paths.append(path)

    _, _, path = save_scene(
        "06_thumb_seat_isolated.png",
        [*[(mesh, SEAT) for mesh in seats], *[(mesh, BACKPLATE) for mesh in thumb_backplate], *[(mesh, THUMB) for mesh in [*thumb_controls, *thumb_mechanism]]],
        "THUMB SEAT ISOLATED / THREE-POINT DATUM",
        "42x64 / 34x56 FRAME / 1.60 mm / THREE 5 mm PADS / 4.8 mm REACH",
        "THREE-POINT PLANE = GOOD; EXACT 0 mm CONTACT + NO DEFINED OPPOSING PRELOAD = TOLERANCE RISK",
        (("split seat", SEAT), ("Backplate", BACKPLATE), ("thumb module", THUMB)), left,
    ); paths.append(path)

    image, projection, path = save_scene(
        "07_screws_bosses_isolated.png",
        [*[(mesh, BOSS) for mesh in bosses], *[(mesh, SCREW) for mesh in screws]],
        "FASTENING / CURRENT BOSS ENVELOPE + REVIEW-ONLY FINAL BORE",
        "CURRENT SCREW-SHELL INTERSECTION 8.091 / 137.015 / 74.118 mm3",
        "FINAL-BOOLEAN BORE CANDIDATE = 0 / 0 / 0 mm3; HEAD SHOULDER 1.70 mm; INSERT WALL 2.30 mm",
        (("boss/web", BOSS), ("M3 screw", SCREW), ("candidate bore", BORE)), right,
    )
    wireframe(image, projection, [triangles(jad_bored), triangles(jfd_bored)], right, color=(*BORE, 85), divisor=1050)
    image.convert("RGB").save(path, quality=96); paths.append(path)

    image, projection, path = save_scene(
        "08_finger_wiring_only.png",
        [*[(mesh, WIRE_FINGER) for mesh in current_finger_wires], *[(mesh, WIRE_BAD) for mesh in penetrating_n1_wires], *[(mesh, WIRE_CANDIDATE) for mesh in finger_candidate], *[(mesh, ROOT_METAL) for mesh in roots]],
        "FINGER WIRING ONLY / CURRENT ENVELOPES + CLEAN TRUNK SEED",
        "N1 FOUR JfD CROSSINGS TOTAL 48.037 mm3 / CURRENT MODEL HAS NO COMPLETE TRUNK TO ELECTRONICS",
        "REVIEW TRUNK ENVELOPE 4 mm: PENETRATION 0 / MIN CLEARANCE 4.410 mm; FINAL BRANCHES STILL REQUIRED",
        (("current local envelope", WIRE_FINGER), ("shell crossing", WIRE_BAD), ("candidate trunk", WIRE_CANDIDATE), ("terminal root", ROOT_METAL)), left,
    )
    wireframe(image, projection, shell_meshes, left)
    image.convert("RGB").save(path, quality=96); paths.append(path)

    image, projection, path = save_scene(
        "09_thumb_wiring_only.png",
        [*[(mesh, WIRE_THUMB) for mesh in current_thumb_wires], *[(mesh, WIRE_CANDIDATE) for mesh in thumb_candidate], (electronics[0], ELECTRONICS), (electronics[1], BATTERY)],
        "THUMB WIRING ONLY / OUTSIDE ROUTE VS INBOARD HARNESS SEED",
        "CURRENT LOWER CORRIDOR X=22.4..25.6; SHELL OUTER X~+19.17 AT Z=-35 -> OUTSIDE BY >=3.23 mm",
        "INBOARD 3.2 mm HARNESS: PENETRATION 0 / CLEARANCE 0.929 mm; EXACT THUMB PCB BRANCH REMAINS HARDWARE-DEPENDENT",
        (("current outside route", WIRE_THUMB), ("candidate inboard", WIRE_CANDIDATE), ("board reserve", ELECTRONICS), ("battery reserve", BATTERY)), right,
    )
    wireframe(image, projection, shell_meshes, right)
    image.convert("RGB").save(path, quality=96); paths.append(path)

    exploded = [
        (moved(jad_mesh, (42, 0, 0)), SHELL_A), (moved(jfd_mesh, (-42, 0, 0)), SHELL_B),
        *[(moved(mesh, ((index - 2.5) * 11, -13, (index % 2) * 8)), color) for index, (_, mesh, color) in enumerate(carrier_rows)],
        *[(moved(mesh, (0, 18, 20)), THUMB) for mesh in [*thumb_backplate, *thumb_controls, *thumb_mechanism]],
        *[(moved(mesh, (0, -18, -16)), SCREW) for mesh in screws],
        *[(mesh, ELECTRONICS) for mesh in electronics],
    ]
    _, _, path = save_scene(
        "10_full_exploded_mechanical.png", exploded,
        "FULL EXPLODED MECHANICAL VIEW",
        "SHELLS / SIX SERVICE PARTS / THUMB MODULE / THREE FASTENERS / LOWER ELECTRONICS RESERVES",
        "RECOMMENDED BASELINE ORDER: FASTENER BORE -> N REAR KEY -> WIRING TRUNKS -> THUMB PRELOAD -> PHYSICAL TEST",
        (("shell", SHELL_B), ("carrier", CARRIER_1), ("thumb", THUMB), ("screw", SCREW), ("electronics reserve", ELECTRONICS)), rear,
    ); paths.append(path)

    def clipped_shells(center_y: float, size_y: float, candidate=False):
        source = (jad_bored, jfd_bored) if candidate else (jad, jfd)
        slab = center_box((100.0, size_y, 180.0), (0.0, center_y, 0.0), f"section_{center_y}")
        result = []
        for shape in source:
            common = (shape & slab).clean()
            if common.solids():
                result.append(triangles(common))
        return result

    section_a_shell = clipped_shells(-27.0, 26.0)
    _, _, path = save_scene(
        "11_section_A_N1_N2_thumb.png",
        [*[(mesh, SHELL_B) for mesh in section_a_shell], (n_front_mesh, N_FRONT), (n_rear_mesh, N_REAR), *[(mesh, SWITCH) for mesh in n_switches], *[(mesh, BACKPLATE) for mesh in thumb_backplate]],
        "SECTION A / N1-N2 + THUMB",
        "N2 OPPOSITE JaD 1.054 mm / REAR->SHELL 0.925 mm / REAR->TERMINAL ROOT 0.506 mm",
        "SECTION RESULT: FRONT LOCATOR ACCEPT / REAR RESTRAINT REVISE",
        (("section wall", SHELL_B), ("front locator", N_FRONT), ("rear restraint", N_REAR), ("thumb", BACKPLATE)), section_view,
    ); paths.append(path)

    section_b_shell = clipped_shells(-12.0, 34.0)
    _, _, path = save_scene(
        "12_section_B_middle_finger_carriers.png",
        [*[(mesh, SHELL_B) for mesh in section_b_shell], *[(mesh, color) for _, mesh, color in carrier_rows[2:]], *[(mesh, SWITCH) for mesh in switches]],
        "SECTION B / MIDDLE FINGER CARRIERS",
        "CARRIER WALL 1.60 mm / SWITCH-SWITCH MIN 1.359 mm / CARRIER-THUMB MIN 1.715 mm",
        "I2/I3, I4, M3, M4/N3 C-CHANNEL ARCHITECTURES = KEEP AS-IS",
        (("section wall", SHELL_B), ("carrier", CARRIER_1), ("switch", SWITCH)), section_view,
    ); paths.append(path)

    section_c_shell = clipped_shells(17.0, 24.0, candidate=True)
    _, _, path = save_scene(
        "13_section_C_thumb_seat_screw_boss.png",
        [*[(mesh, SHELL_B) for mesh in section_c_shell], *[(mesh, SEAT) for mesh in seats], *[(mesh, BOSS) for mesh in bosses], *[(mesh, SCREW) for mesh in screws], *[(mesh, BACKPLATE) for mesh in thumb_backplate]],
        "SECTION C / THUMB SEAT + SCREW/BOSS",
        "SEAT 1.60 mm / BOSS OUTER R4.60 / HEAD SHOULDER 1.70 / INSERT RADIAL WALL 2.30 mm",
        "BORE BOOLEAN ORDER CORRECTED IN REVIEW CANDIDATE; CLAMP DISTRIBUTION STILL REQUIRES REDESIGN",
        (("candidate section", SHELL_B), ("seat", SEAT), ("boss", BOSS), ("screw", SCREW)), section_view,
    ); paths.append(path)

    sheet = contact_sheet(paths)
    print(json.dumps({"renders": [str(path) for path in paths], "contactSheet": str(sheet), "count": len(paths)}, indent=2))


if __name__ == "__main__":
    main()
