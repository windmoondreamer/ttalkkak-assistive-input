"""Generate the six required visual-QC views for the build123d redesign."""

from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np
from PIL import ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402
import audit_middle_its1105_design as legacy  # noqa: E402

RENDER_DIR = ROOT / "renders" / "middle_redesign_build123d"
OUT_DIR = ROOT / "build123d_workbench" / "out" / "middle_redesign"
SHELL_DIR = ROOT / "exports" / "thumb_lower15_housing_mockup"
OLD_PARTS = ROOT / "exports" / "full_exterior_minimal_mockup" / "source_stl"
DATUM_NAMES = ("M1", "M2", "M3", "M4")

SHELL_COLOR_A = (35, 68, 87)
SHELL_COLOR_B = (42, 79, 99)
INDEX_COLOR = (49, 164, 224)
CAP_COLOR = (73, 205, 132)
CARRIER_COLOR = (223, 87, 172)
M4_COLOR = (55, 195, 221)
SWITCH_COLOR = (218, 172, 73)


def load_new(name: str) -> np.ndarray:
    return read_binary_stl(OUT_DIR / f"{name}.stl")


def load_old_part(number: int) -> np.ndarray:
    return read_binary_stl(OLD_PARTS / f"Joystick - Part {number}.stl")


def translated(mesh: np.ndarray, offset) -> np.ndarray:
    return mesh + np.asarray(offset, dtype=float)


def rotated(mesh: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return mesh @ matrix.T


def rotate_objects(objects, matrix):
    return [(rotated(mesh, matrix), color) for mesh, color in objects]


def rot_z(angle_deg: float) -> np.ndarray:
    angle = math.radians(angle_deg)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0)))


def rot_x(angle_deg: float) -> np.ndarray:
    angle = math.radians(angle_deg)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c)))


def annotate(image, title: str, subtitle: str, legend=()):
    draw = ImageDraw.Draw(image)
    draw.text((48, 34), title, font=render.font(37, True), fill=(242, 247, 250, 255))
    draw.text((50, 80), subtitle, font=render.font(19), fill=(176, 197, 210, 255))
    if legend:
        x = 55
        y = render.HEIGHT - 76
        draw.rounded_rectangle(
            (38, render.HEIGHT - 102, render.WIDTH - 38, render.HEIGHT - 34),
            radius=14,
            fill=(8, 13, 20, 225),
            outline=(78, 103, 119, 230),
            width=2,
        )
        for label, color in legend:
            draw.ellipse((x, y, x + 18, y + 18), fill=(*color, 255))
            draw.text((x + 26, y - 6), label, font=render.font(16), fill=(227, 235, 240, 255))
            x += max(205, len(label) * 10 + 66)


def save_scene(filename: str, objects, title: str, subtitle: str, legend=()):
    image, projection = render.rasterize(objects)
    annotate(image, title, subtitle, legend)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / filename
    image.convert("RGB").save(path, quality=96)
    return path, image, projection


def shell_wireframe(image, projection, meshes, centers, matrix=None):
    """Overlay a sparse ghost shell as a transparent internal-view cue."""
    draw = ImageDraw.Draw(image, "RGBA")
    for mesh in meshes:
        if matrix is not None:
            mesh = rotated(mesh, matrix)
        centroids = mesh.mean(axis=1)
        distance = np.min(
            np.linalg.norm(centroids[:, None, :] - centers[None, :, :], axis=2),
            axis=1,
        )
        local = mesh[distance <= 22.0]
        stride = max(1, len(local) // 80)
        sample = local[::stride]
        for triangle in sample:
            points = render.project(triangle, projection)
            draw.line(
                [tuple(points[0]), tuple(points[1]), tuple(points[2]), tuple(points[0])],
                fill=(75, 165, 200, 24),
                width=1,
            )


def main() -> None:
    validation = __import__("json").loads(
        (OUT_DIR / "middle_redesign_validation.json").read_text(encoding="utf-8")
    )
    datums = validation["datums"]
    jad = read_binary_stl(SHELL_DIR / "OneGrip_lower15_housing_Joystick_1_JaD.stl")
    jfd = read_binary_stl(SHELL_DIR / "OneGrip_lower15_housing_Joystick_2_JfD.stl")
    old_index_caps = [load_old_part(number) for number in (13, 14, 15, 16)]
    caps = [load_new(f"{name}_cap") for name in DATUM_NAMES]
    switches = [load_new(f"{name}_ITS1105_reference") for name in DATUM_NAMES]
    shared = load_new("M1_M2_M3_shared_carrier")
    m4 = load_new("M4_single_carrier")
    cap_pads = []
    for name in DATUM_NAMES:
        row = datums[name]
        axes = legacy.rotated_axes(np.asarray(row["axis"]), row["rollDeg"])
        box = legacy.obb_rect(
            np.asarray(row["centerMm"]), axes, 7.60, 7.60, 1.20, -1.00
        )
        cap_pads.append(render.obb_triangles(box))

    # 1. Exterior perspective.  Rotate 180 degrees so the middle normals face
    # the fixed reproducible software camera.
    exterior_matrix = rot_z(180.0)
    exterior = [
        (jad, SHELL_COLOR_A),
        (jfd, SHELL_COLOR_B),
        *[(mesh, INDEX_COLOR) for mesh in old_index_caps],
        *[(mesh, CAP_COLOR) for mesh in cap_pads],
    ]
    save_scene(
        "01_exterior_perspective.png",
        rotate_objects(exterior, exterior_matrix),
        "MIDDLE REDESIGN / EXTERIOR PERSPECTIVE",
        "7.6 mm CAPS / 8.0 mm OPENING TARGET / 1.0 mm NOMINAL EXPOSURE",
        (("frozen shell reference", SHELL_COLOR_B), ("INDEX caps", INDEX_COLOR), ("new MIDDLE caps", CAP_COLOR)),
    )

    # 2. External-language comparison with shell hidden.
    comparison = [
        *[(mesh, INDEX_COLOR) for mesh in old_index_caps],
        *[(mesh, CAP_COLOR) for mesh in cap_pads],
    ]
    save_scene(
        "02_index_middle_comparison.png",
        rotate_objects(comparison, exterior_matrix),
        "INDEX + MIDDLE / EXTERNAL LANGUAGE",
        "CONTINUOUS M1-M2-M3 | M4 ROW / M2 DOGLEG REMOVED",
        (("existing INDEX 7.6 mm", INDEX_COLOR), ("new MIDDLE 7.6 mm", CAP_COLOR)),
    )

    # 3. Internal view: exact internal parts plus a sparse alpha wireframe of
    # both shell references.  This is visually transparent without altering
    # or re-tessellating the shell geometry.
    internal_objects = [
        (shared, CARRIER_COLOR),
        (m4, M4_COLOR),
        *[(mesh, SWITCH_COLOR) for mesh in switches],
        *[(mesh, CAP_COLOR) for mesh in caps],
    ]
    image, projection = render.rasterize(internal_objects)
    shell_wireframe(
        image,
        projection,
        (jad, jfd),
        np.asarray([datums[name]["centerMm"] for name in DATUM_NAMES]),
    )
    annotate(
        image,
        "TRANSPARENT SHELL / INTERNAL ARCHITECTURE",
        "ONE 3-SWITCH CARRIER + ONE M4 CARRIER / OPEN REAR WIRING SIDE",
        (("shared carrier", CARRIER_COLOR), ("M4 carrier", M4_COLOR), ("ITS-1105", SWITCH_COLOR), ("ghost shell", (75, 165, 200))),
    )
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(RENDER_DIR / "03_transparent_internal.png", quality=96)

    # 4. Shared carrier exploded along each switch axis.
    shared_scene = [(shared, CARRIER_COLOR)]
    for name, switch, cap in zip(DATUM_NAMES[:3], switches[:3], caps[:3]):
        outward = np.asarray(datums[name]["axis"])
        shared_scene.append((translated(switch, outward * 6.0), SWITCH_COLOR))
        shared_scene.append((translated(cap, outward * 13.0), CAP_COLOR))
    save_scene(
        "04_m1_m3_shared_carrier_exploded.png",
        rotate_objects(shared_scene, rot_z(180.0)),
        "M1-M3 SHARED CARRIER / EXPLODED",
        "STRAIGHT INSERTION / BROAD REAR STOPS / TERMINAL SIDE CLEARANCE",
        (("one-piece carrier", CARRIER_COLOR), ("ITS-1105", SWITCH_COLOR), ("captured caps", CAP_COLOR)),
    )

    # 5. M4 separate carrier exploded.
    outward = np.asarray(datums["M4"]["axis"])
    m4_scene = [
        (m4, M4_COLOR),
        (translated(switches[3], outward * 6.0), SWITCH_COLOR),
        (translated(caps[3], outward * 13.0), CAP_COLOR),
    ]
    save_scene(
        "05_m4_carrier_exploded.png",
        rotate_objects(m4_scene, rot_z(180.0)),
        "M4 INDEPENDENT CARRIER / EXPLODED",
        "SAME CAP / OPENING / ACTUATION LANGUAGE AS M1-M3",
        (("one-piece M4 carrier", M4_COLOR), ("ITS-1105", SWITCH_COLOR), ("M4 cap", CAP_COLOR)),
    )

    # 6. Finger-facing cap view.  A small pitch brings both rows close to a
    # frontal orthographic-like composition while preserving world spacing.
    finger_matrix = rot_x(-12.0) @ rot_z(180.0)
    save_scene(
        "06_finger_facing.png",
        rotate_objects(comparison, finger_matrix),
        "FINGER-FACING VIEW",
        "UNIFORM CAP SIZE / NATURAL ROW ALIGNMENT / NO M3 EXCEPTION BOSS",
        (("INDEX", INDEX_COLOR), ("MIDDLE", CAP_COLOR)),
    )

    for path in sorted(RENDER_DIR.glob("*.png")):
        print(path)


if __name__ == "__main__":
    main()
