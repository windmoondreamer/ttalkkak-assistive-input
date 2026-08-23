"""Lay both lower-15 housing shells flat and pack them into one STL plate.

The mating plane of each shell is placed on Z=0.  A conservative raster/FFT
search rotates the second shell in 5 degree increments and enforces at least
8 mm projected spacing between the two disconnected watertight components.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import sys
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
from validate_thumb_housing_stl import analyze  # noqa: E402


SOURCE = ROOT / "exports" / "thumb_lower15_housing_mockup"
OUT = SOURCE / "one_plate"
JA_D = SOURCE / "OneGrip_lower15_housing_Joystick_1_JaD.stl"
JF_D = SOURCE / "OneGrip_lower15_housing_Joystick_2_JfD.stl"
OUT_STL = OUT / "OneGrip_lower15_housing_two_shells_one_plate.stl"
OUT_JSON = OUT / "layout.json"
OUT_VALIDATION = OUT / "mesh_validation.json"
OUT_PREVIEW = OUT / "OneGrip_lower15_housing_two_shells_one_plate_preview.png"
OUT_ZIP = OUT / "OneGrip_lower15_housing_two_shells_one_plate.zip"

RESOLUTION = 1.0
PART_GAP_MM = 8.0
BED_MARGIN_MM = 5.0
TARGET_BED_MM = 220.0


def orient_jad(mesh: np.ndarray) -> np.ndarray:
    # Proper rotation: new (X,Y,Z) = old (Y,Z,X).  The x=0 mating plane becomes
    # the build plane and the entire JaD shell remains at Z >= 0.
    return mesh[:, :, (1, 2, 0)].copy()


def orient_jfd(mesh: np.ndarray) -> np.ndarray:
    # Proper rotation with determinant +1: new (X,Y,Z) = (-Y,Z,-X).
    result = mesh[:, :, (1, 2, 0)].copy()
    result[:, :, 0] *= -1.0
    result[:, :, 2] *= -1.0
    return result


def rotate_z(mesh: np.ndarray, degrees: float) -> np.ndarray:
    radians = math.radians(degrees)
    cosine, sine = math.cos(radians), math.sin(radians)
    result = mesh.copy()
    x = mesh[:, :, 0]
    y = mesh[:, :, 1]
    result[:, :, 0] = cosine * x - sine * y
    result[:, :, 1] = sine * x + cosine * y
    return result


def raster_mask(mesh: np.ndarray, pad: int) -> tuple[np.ndarray, np.ndarray]:
    xy = mesh[:, :, :2]
    lower = np.floor(xy.reshape(-1, 2).min(axis=0) / RESOLUTION) * RESOLUTION
    upper = np.ceil(xy.reshape(-1, 2).max(axis=0) / RESOLUTION) * RESOLUTION
    size = np.ceil((upper - lower) / RESOLUTION).astype(int) + 1 + 2 * pad
    image = Image.new("L", (int(size[0]), int(size[1])), 0)
    draw = ImageDraw.Draw(image)
    offset = lower - pad * RESOLUTION
    for triangle in xy:
        points = [
            ((float(point[0]) - offset[0]) / RESOLUTION,
             (float(point[1]) - offset[1]) / RESOLUTION)
            for point in triangle
        ]
        draw.polygon(points, fill=255)
    return np.asarray(image, dtype=np.uint8) > 0, offset


def full_convolution(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    shape = (first.shape[0] + second.shape[0] - 1,
             first.shape[1] + second.shape[1] - 1)
    transformed_first = np.fft.rfftn(first.astype(float), s=shape, axes=(0, 1))
    transformed_second = np.fft.rfftn(second[::-1, ::-1].astype(float), s=shape, axes=(0, 1))
    return np.rint(
        np.fft.irfftn(transformed_first * transformed_second, s=shape, axes=(0, 1))
    ).astype(np.int64)


def best_pack(jad: np.ndarray, jfd: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    gap_pixels = int(math.ceil(PART_GAP_MM / RESOLUTION))
    first_mask, first_offset = raster_mask(jad, gap_pixels + 2)
    dilation_size = 2 * gap_pixels + 1
    first_dilated = np.asarray(
        Image.fromarray(first_mask.astype(np.uint8) * 255).filter(
            ImageFilter.MaxFilter(dilation_size)
        )
    ) > 0

    best = None
    for angle in range(0, 360, 5):
        rotated = rotate_z(jfd, angle)
        second_mask, second_offset = raster_mask(rotated, 1)
        overlap = full_convolution(first_dilated, second_mask)
        zero_rows, zero_cols = np.nonzero(overlap == 0)
        if len(zero_rows) == 0:
            continue
        ty = zero_rows - (second_mask.shape[0] - 1)
        tx = zero_cols - (second_mask.shape[1] - 1)
        width = np.maximum(first_mask.shape[1], tx + second_mask.shape[1]) - np.minimum(0, tx)
        height = np.maximum(first_mask.shape[0], ty + second_mask.shape[0]) - np.minimum(0, ty)
        maximum = np.maximum(width, height)
        area = width * height
        fits = (width * RESOLUTION + 2 * BED_MARGIN_MM <= TARGET_BED_MM) & (
            height * RESOLUTION + 2 * BED_MARGIN_MM <= TARGET_BED_MM
        )
        # Prefer a 220 mm square-bed fit, then the smallest longest side and area.
        fit_penalty = (~fits).astype(np.int64)
        order = np.lexsort((area, maximum, fit_penalty))
        index = int(order[0])
        candidate = (
            int(fit_penalty[index]),
            int(maximum[index]),
            int(area[index]),
            angle,
            int(tx[index]),
            int(ty[index]),
            int(width[index]),
            int(height[index]),
            rotated,
            second_offset,
        )
        if best is None or candidate[:3] < best[:3]:
            best = candidate

    if best is None:
        raise RuntimeError("no non-overlapping two-shell placement found")

    fit_penalty, _, _, angle, tx, ty, _, _, rotated, second_offset = best
    translation_xy = first_offset - second_offset + np.asarray((tx, ty)) * RESOLUTION
    second = rotated.copy()
    second[:, :, :2] += translation_xy
    first = jad.copy()

    all_points = np.concatenate((first.reshape(-1, 3), second.reshape(-1, 3)))
    lower = all_points.min(axis=0)
    shift = np.asarray((BED_MARGIN_MM - lower[0], BED_MARGIN_MM - lower[1], -lower[2]))
    first += shift
    second += shift
    final_points = np.concatenate((first.reshape(-1, 3), second.reshape(-1, 3)))
    final_lower = final_points.min(axis=0)
    final_upper = final_points.max(axis=0)
    layout = {
        "unit": "millimeter",
        "components": 2,
        "orientation": "both shell mating planes on Z=0",
        "jfdInPlaneRotationDeg": angle,
        "minimumProjectedGapMm": PART_GAP_MM,
        "bedMarginMm": BED_MARGIN_MM,
        "targetBedMm": [TARGET_BED_MM, TARGET_BED_MM],
        "boundsMm": [final_lower.tolist(), final_upper.tolist()],
        "footprintMm": (final_upper[:2] - final_lower[:2] + 2 * BED_MARGIN_MM).tolist(),
        "modelFootprintMm": (final_upper[:2] - final_lower[:2]).tolist(),
        "heightMm": float(final_upper[2] - final_lower[2]),
        "fitsTargetBed": bool(fit_penalty == 0),
    }
    return first, second, layout


def write_binary_stl(path: Path, meshes: list[np.ndarray]) -> None:
    triangles = np.concatenate(meshes, axis=0).astype(np.float32)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals[lengths > 0] /= lengths[lengths > 0, None]
    record = np.dtype([
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attribute", "<u2"),
    ])
    rows = np.zeros(len(triangles), dtype=record)
    rows["normal"] = normals
    rows["vertices"] = triangles
    header = b"OneGrip lower15 two-shell one-plate STL".ljust(80, b" ")
    path.write_bytes(header + struct.pack("<I", len(rows)) + rows.tobytes())


def font(size: int, bold: bool = False):
    path = r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"
    return ImageFont.truetype(path, size)


def preview(first: np.ndarray, second: np.ndarray, layout: dict) -> None:
    scale = 4.0
    width = int(math.ceil(layout["footprintMm"][0] * scale))
    height = int(math.ceil(layout["footprintMm"][1] * scale))
    canvas = Image.new("RGB", (width + 80, height + 170), (14, 20, 29))
    draw = ImageDraw.Draw(canvas)
    colors = ((68, 139, 176), (91, 170, 196))
    for mesh, color in ((first, colors[0]), (second, colors[1])):
        for triangle in mesh[:, :, :2]:
            points = [(40 + float(point[0]) * scale, 105 + float(point[1]) * scale) for point in triangle]
            draw.polygon(points, fill=color)
    draw.text((40, 24), "ONEGRIP LOWER-15 / TWO SHELLS / ONE PLATE", font=font(31, True), fill=(241, 246, 249))
    draw.text((42, 66), f"FOOTPRINT {layout['footprintMm'][0]:.1f} x {layout['footprintMm'][1]:.1f} mm  /  GAP >= {PART_GAP_MM:.0f} mm", font=font(19), fill=(186, 202, 214))
    draw.text((42, height + 125), "2 DISCONNECTED WATERTIGHT COMPONENTS / MATING PLANES ON BED", font=font(18, True), fill=(232, 188, 77))
    canvas.save(OUT_PREVIEW, quality=96)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jad = orient_jad(read_binary_stl(JA_D))
    jfd = orient_jfd(read_binary_stl(JF_D))
    first, second, layout = best_pack(jad, jfd)
    write_binary_stl(OUT_STL, [first, second])
    OUT_JSON.write_text(json.dumps(layout, indent=2), encoding="utf-8")
    validation = analyze(OUT_STL)
    validation.pop("printMeshGate", None)
    validation["onePlateGate"] = "PASS" if (
        validation["watertight"]
        and validation["windingConsistent"]
        and validation["degenerateTriangles"] == 0
        and validation["connectedComponents"] == 2
    ) else "HOLD"
    OUT_VALIDATION.write_text(json.dumps(validation, indent=2), encoding="utf-8")
    if validation["onePlateGate"] != "PASS":
        raise RuntimeError(json.dumps(validation, indent=2))
    preview(first, second, layout)
    package_files = [
        OUT_STL,
        OUT_JSON,
        OUT_VALIDATION,
        OUT / "README.md",
        OUT_PREVIEW,
    ]
    with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for package_file in package_files:
            if package_file.exists():
                archive.write(package_file, package_file.name)
    print(json.dumps(layout, indent=2))
    print(json.dumps(validation, indent=2))
    print(f"STL -> {OUT_STL}")
    print(f"PREVIEW -> {OUT_PREVIEW}")
    print(f"ZIP -> {OUT_ZIP}")


if __name__ == "__main__":
    main()
