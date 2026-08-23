"""Render the local-only Finger V2 + lowered-thumb feasibility evidence.

This script consumes the STEP/JSON results of finger_thumb_joint_feasibility.
It does not rebuild or modify production CAD.
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


ROOT = Path(__file__).resolve().parents[1]
STUDY_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_joint_feasibility"
FINGER_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
LOWER15_DIR = ROOT / "exports" / "thumb_lower15_housing_mockup"
RENDER_DIR = ROOT / "renders" / "finger_thumb_joint_feasibility"
REFERENCE = STUDY_DIR / "FINGER_THUMB_JOINT_FEASIBILITY_REFERENCE.step"

sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402


BG = (9, 15, 22)
SHELL_A = (43, 82, 105)
SHELL_B = (52, 97, 121)
LOWER_SHELL_A = (61, 113, 145)
LOWER_SHELL_B = (72, 130, 158)
CAP = (70, 210, 142)
THUMB_ORIGINAL = (114, 127, 137)
THUMB_TARGET = (236, 146, 54)
SWITCH = (230, 177, 69)
CARRIER_OLD = (224, 95, 106)
CARRIER_NEW = (83, 197, 211)
ROOT_METAL = (239, 87, 89)
WIRE = (190, 92, 230)
SCREW = (255, 71, 76)


def rot_z(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0)))


def rot_x(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c)))


def apply_matrix(objects, matrix):
    return [(mesh @ matrix.T, color) for mesh, color in objects]


def moved_mesh(mesh: np.ndarray, delta) -> np.ndarray:
    return mesh + np.asarray(delta, dtype=float)


def annotate(image: Image.Image, title: str, subtitle: str, footer: str, legend=()) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((28, 22, 1172, 116), radius=14, fill=(7, 12, 19, 228), outline=(83, 108, 124, 230), width=2)
    draw.text((48, 34), title, font=render.font(34, True), fill=(245, 249, 251, 255))
    draw.text((50, 80), subtitle, font=render.font(18), fill=(183, 202, 213, 255))
    draw.rounded_rectangle((28, render.HEIGHT - 111, render.WIDTH - 28, render.HEIGHT - 28), radius=14, fill=(7, 12, 19, 228), outline=(83, 108, 124, 230), width=2)
    draw.text((48, render.HEIGHT - 92), footer, font=render.font(17, True), fill=(244, 202, 111, 255))
    x = 48
    for label, color in legend:
        draw.ellipse((x, render.HEIGHT - 56, x + 15, render.HEIGHT - 41), fill=(*color, 255))
        draw.text((x + 23, render.HEIGHT - 61), label, font=render.font(14), fill=(226, 235, 240, 255))
        x += max(145, len(label) * 8 + 48)


def save_scene(filename: str, objects, title: str, subtitle: str, footer: str, legend=(), matrix=None):
    shown = apply_matrix(objects, matrix) if matrix is not None else objects
    image, projection = render.rasterize(shown)
    annotate(image, title, subtitle, footer, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / filename
    image.convert("RGB").save(path, quality=96)
    return image, projection, path


def wireframe(image, projection, meshes, matrix=None, color=(115, 196, 225, 55), stride_divisor=500):
    draw = ImageDraw.Draw(image, "RGBA")
    for mesh in meshes:
        work = mesh @ matrix.T if matrix is not None else mesh
        stride = max(1, len(work) // stride_divisor)
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
    sheet = Image.new("RGB", (cols * cell_w, 70 + rows * cell_h), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((28, 17), "ONEGRIP PLAY / FINGER-THUMB JOINT FEASIBILITY / HOLD EVIDENCE", font=render.font(27, True), fill=(242, 247, 250))
    for index, (name, image) in enumerate(cells):
        x = (index % cols) * cell_w + 20
        y = (index // cols) * cell_h + 62
        sheet.paste(image, (x, y))
        draw.text((x + 4, y + 328), name, font=render.font(14), fill=(202, 216, 225))
    path = RENDER_DIR / "00_contact_sheet.png"
    sheet.save(path, quality=96)
    return path


def main() -> None:
    report_data = json.loads((STUDY_DIR / "finger_thumb_joint_feasibility.json").read_text(encoding="utf-8"))
    target = np.asarray(report_data["hardFreeze"]["thumbTranslationMm"], dtype=float)
    robust = report_data["fixedScrews"]["loweringSweep"]["maxRobustTranslationMm"]

    reference = import_step(REFERENCE)
    rows = [(child.label, triangles(child)) for child in reference.children]
    pick = lambda predicate: [mesh for label, mesh in rows if predicate(label)]

    shells = pick(lambda label: label in ("JAD_FINGER_V2", "JFD_FINGER_V2"))
    caps = pick(lambda label: label.endswith("_cap"))
    target_thumb = pick(lambda label: label in {
        "Backplate", "PushBtn", "HW504_B", "Small_joystick_attachment",
        "Button_wide_2", "Button_side_2", "Button_corner_1", "Button_middle_1",
        "Button_corner_2", "Button_wide_1", "Button_middle_2", "Button_side_1",
    })
    original_thumb = [moved_mesh(mesh, -target) for mesh in target_thumb]
    screws = pick(lambda label: label.startswith("Hex_socket_head_cap_screw"))
    carriers_new = pick(lambda label: label in ("N1_low_profile_individual_carrier", "N2_low_profile_individual_carrier"))
    carriers_other = pick(lambda label: "carrier" in label and label not in ("N1_low_profile_individual_carrier", "N2_low_profile_individual_carrier"))
    switches = pick(lambda label: "ITS1105_body" in label or "ITS1105_actuator" in label)
    n_switches = pick(lambda label: label.startswith(("N1_ITS", "N2_ITS")))
    n_roots = pick(lambda label: label.startswith(("N1_root", "N2_root")))
    n_wiring = pick(lambda label: label.startswith(("N1_formed", "N1_solder", "N1_insulated", "N2_formed", "N2_solder", "N2_insulated")))
    all_roots = pick(lambda label: "_root_" in label)
    all_wires = pick(lambda label: "wire" in label or "formed_lead" in label or "solder" in label)
    n_caps = pick(lambda label: label in ("N1_cap", "N2_cap"))

    old_shared = triangles(import_step(FINGER_DIR / "N1_N2_shared_carrier.step"))
    lower_shells = [
        read_binary_stl(LOWER15_DIR / "OneGrip_lower15_housing_Joystick_1_JaD.stl"),
        read_binary_stl(LOWER15_DIR / "OneGrip_lower15_housing_Joystick_2_JfD.stl"),
    ]

    rear = rot_z(140.0)
    close = rot_x(-15.0) @ rot_z(125.0)
    side = rot_x(8.0) @ rot_z(75.0)
    paths: list[Path] = []

    _, _, path = save_scene(
        "01_original_thumb_plus_finger_v2.png",
        [(shells[0], SHELL_A), (shells[1], SHELL_B), *[(mesh, CAP) for mesh in caps], *[(mesh, THUMB_ORIGINAL) for mesh in original_thumb]],
        "ORIGINAL THUMB + APPROVED FINGER V2",
        "EXTERIOR BUTTON CENTERS I2 I3 I4 M3 M4 N1 N2 N3 REMAIN FROZEN",
        "REFERENCE ONLY / PRODUCTION FINGER V2 AND PHYSICAL VALIDATION KIT UNCHANGED",
        (("Finger V2 shell", SHELL_B), ("8 frozen caps", CAP), ("original thumb", THUMB_ORIGINAL)), rear,
    )
    paths.append(path)

    _, _, path = save_scene(
        "02_target_exterior_overlay.png",
        [(lower_shells[0], LOWER_SHELL_A), (lower_shells[1], LOWER_SHELL_B), *[(mesh, CAP) for mesh in caps], *[(mesh, THUMB_TARGET) for mesh in target_thumb]],
        "TARGET EXTERIOR OVERLAY / FULL LOWERING",
        "RIGID THUMB DELTA (0,+12.25,-21.00) mm + LATEST APPROVED 8-CAP LAYOUT",
        "VISUAL FEASIBILITY OVERLAY ONLY / LOWER-15 SHELL INTERFACE IS NOT PRODUCTION CAD",
        (("lower-15 shell mesh", LOWER_SHELL_B), ("8 frozen caps", CAP), ("target thumb", THUMB_TARGET)), rear,
    )
    paths.append(path)

    image, projection, path = save_scene(
        "03_transparent_joint_internals.png",
        [*[(mesh, THUMB_TARGET) for mesh in target_thumb], *[(mesh, CARRIER_NEW) for mesh in carriers_new], *[(mesh, (80, 156, 226)) for mesh in carriers_other], *[(mesh, SWITCH) for mesh in switches], *[(mesh, ROOT_METAL) for mesh in all_roots], *[(mesh, WIRE) for mesh in all_wires], *[(mesh, SCREW) for mesh in screws]],
        "TRANSPARENT JOINT ENVELOPE",
        "EXACT THUMB / 8 SWITCHES / SIX-CARRIER PROPOSAL / ROOTS / WIRES / FIXED SCREWS",
        "RED AND PURPLE ZONES DRIVE HOLD; SHELLS SHOWN AS WIREFRAME",
        (("target thumb", THUMB_TARGET), ("carrier", CARRIER_NEW), ("switch", SWITCH), ("terminal roots", ROOT_METAL), ("wire", WIRE), ("fixed screw", SCREW)), rear,
    )
    wireframe(image, projection, shells, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    _, _, path = save_scene(
        "04_n1_n2_closeup.png",
        [*[(mesh, CAP) for mesh in n_caps], *[(mesh, CARRIER_NEW) for mesh in carriers_new], *[(mesh, SWITCH) for mesh in n_switches], *[(mesh, ROOT_METAL) for mesh in n_roots], *[(mesh, WIRE) for mesh in n_wiring], *[(mesh, THUMB_TARGET) for mesh in target_thumb]],
        "N1 / N2 SPECIAL PACKAGING CLOSE-UP",
        "N1 ROOT PENETRATION 0.074884 mm3 / N2 WIRE MIN GAP 0.139748 mm",
        "BOTH FAIL THE 0.80 mm ROBUST SERVICE-CLEARANCE GATE",
        (("new C-collars", CARRIER_NEW), ("switch", SWITCH), ("terminal roots", ROOT_METAL), ("formed wiring", WIRE), ("thumb", THUMB_TARGET)), close,
    )
    paths.append(path)

    _, _, path = save_scene(
        "05_thumb_vs_fixed_screws.png",
        [*[(mesh, THUMB_TARGET) for mesh in target_thumb], *[(mesh, SCREW) for mesh in screws[:2]]],
        "TARGET THUMB VS UNCHANGED FIXED SCREWS",
        "TARGET MIN CLEARANCE 0.000 mm / TWO INTERSECTING SCREW PAIRS",
        f"2.50 mm GATE HOLDS ONLY TO DELTA ({robust[0]:.3f},{robust[1]:.3f},{robust[2]:.3f}) mm",
        (("target rigid thumb", THUMB_TARGET), ("unchanged screws / blocker", SCREW)), side,
    )
    paths.append(path)

    _, _, path = save_scene(
        "06_old_shared_vs_new_carriers.png",
        [(old_shared, CARRIER_OLD), *[(mesh, CARRIER_NEW) for mesh in carriers_new], *[(mesh, SWITCH) for mesh in n_switches], *[(mesh, CAP) for mesh in n_caps]],
        "N1/N2 CARRIER ARCHITECTURE COMPARISON",
        "OLD SHARED REAR-PLATE CARRIER VS TWO 1.60 mm LOW-PROFILE C-COLLARS",
        "NEW CARRIERS ARE VALID SINGLE SOLIDS, BUT CLEARANCE GATES STILL FAIL",
        (("old shared carrier", CARRIER_OLD), ("new individual collars", CARRIER_NEW), ("switch", SWITCH), ("frozen caps", CAP)), close,
    )
    paths.append(path)

    _, _, path = save_scene(
        "07_n1_n2_wiring_envelope.png",
        [*[(mesh, SWITCH) for mesh in n_switches], *[(mesh, ROOT_METAL) for mesh in n_roots], *[(mesh, WIRE) for mesh in n_wiring], *[(mesh, CARRIER_NEW) for mesh in carriers_new], *[(mesh, THUMB_TARGET) for mesh in target_thumb]],
        "N1/N2 ONE-BEND WIRING ENVELOPE",
        "FOUR FORMED LEADS + PRE-SOLDER + INSULATED TANGENT ROUTE PER SWITCH",
        "CONTINUITY CONCEPT EXISTS; TARGET CLEARANCE IS NOT ROBUST",
        (("switch", SWITCH), ("fixed roots", ROOT_METAL), ("formed/soldered wire", WIRE), ("carrier", CARRIER_NEW)), side,
    )
    paths.append(path)

    image, projection, path = save_scene(
        "08_shell_closure_feasibility.png",
        [*[(mesh, CAP) for mesh in caps], *[(mesh, CARRIER_NEW) for mesh in carriers_new], *[(mesh, SWITCH) for mesh in n_switches], *[(mesh, WIRE) for mesh in n_wiring], *[(mesh, THUMB_TARGET) for mesh in target_thumb], *[(mesh, SCREW) for mesh in screws]],
        "SHELL CLOSURE / ASSEMBLY FEASIBILITY",
        "N1/N2 LOAD FROM SEAM; N2 CAPTURED BY OPPOSITE SHELL; THUMB INSTALLED LAST",
        "ASSEMBLY = HOLD: SCREW AND SERVICE-CLEARANCE BLOCKERS REMAIN",
        (("shell wireframe", LOWER_SHELL_B), ("target thumb", THUMB_TARGET), ("N carriers", CARRIER_NEW), ("wiring", WIRE), ("screw", SCREW)), rear,
    )
    wireframe(image, projection, lower_shells, rear, color=(120, 201, 230, 62), stride_divisor=650)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    image, projection, path = save_scene(
        "09_original_vs_target_overlay.png",
        [*[(mesh, THUMB_ORIGINAL) for mesh in original_thumb], *[(mesh, THUMB_TARGET) for mesh in target_thumb], *[(mesh, CAP) for mesh in caps]],
        "ORIGINAL VS TARGET RIGID THUMB OVERLAY",
        "GRAY = ORIGINAL / ORANGE = (0,+12.25,-21.00) mm TARGET / GREEN = FROZEN FINGER CAPS",
        "TARGET POSITION IS ERGONOMIC INTENT ONLY; EXACT JOINT GATE = HOLD",
        (("original thumb", THUMB_ORIGINAL), ("target thumb", THUMB_TARGET), ("frozen caps", CAP)), rear,
    )
    wireframe(image, projection, shells, rear)
    image.convert("RGB").save(path, quality=96)
    paths.append(path)

    sheet = contact_sheet(paths)
    print(json.dumps({"renders": [str(path) for path in paths], "contactSheet": str(sheet)}, indent=2))


if __name__ == "__main__":
    main()
