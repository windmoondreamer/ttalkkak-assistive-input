"""Orient and safely pack the right-hand OneGrip printable solids onto FDM plates.

The input is the per-part binary STL ZIP exported from Onshape.  Only numpy and
Pillow are used so the workflow stays reproducible in the bundled runtime.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
import random
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "exports" / "right_hand_handle_parts" / "individual_stl"
DEFAULT_OUTPUT = ROOT / "exports" / "right_hand_handle_parts" / "plates"

ROLE_NAMES = {
    "Part 13": "I1_cap",
    "Part 14": "I2_cap",
    "Part 15": "I3_cap",
    "Part 16": "I4_cap",
    "Part 17": "shared_retainer_RWID",
    "Part 18": "I4_retainer_RZKD",
    "Part 19": "I1_spacer",
    "Part 20": "I2_spacer",
    "Part 21": "I3_spacer",
    "Part 22": "I4_spacer",
    "Part 23": "M1_spacer",
    "Part 24": "M1_cap",
    "Part 25": "M2_spacer",
    "Part 26": "M2_cap",
    "Part 27": "M3_spacer",
    "Part 28": "M3_cap",
    "Part 29": "M4_spacer",
    "Part 30": "M4_cap",
}


def display_name(path: Path) -> str:
    name = path.stem.removeprefix("Joystick - ")
    return ROLE_NAMES.get(name, name)


def read_binary_stl(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    if len(raw) < 84:
        raise ValueError(f"STL too short: {path}")
    count = struct.unpack_from("<I", raw, 80)[0]
    expected = 84 + count * 50
    if len(raw) != expected:
        raise ValueError(f"Expected binary STL ({expected} bytes), got {len(raw)}: {path}")
    dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attribute", "<u2"),
    ])
    records = np.frombuffer(raw, dtype=dtype, count=count, offset=84)
    triangles = np.asarray(records["vertices"], dtype=np.float64).copy()
    if not np.isfinite(triangles).all():
        raise ValueError(f"Non-finite coordinate: {path}")
    return triangles


def write_binary_stl(path: Path, triangles: np.ndarray, header: str) -> None:
    triangles = np.asarray(triangles, dtype=np.float64)
    edge_a = triangles[:, 1] - triangles[:, 0]
    edge_b = triangles[:, 2] - triangles[:, 0]
    normals = np.cross(edge_a, edge_b)
    lengths = np.linalg.norm(normals, axis=1)
    valid = lengths > 1e-15
    normals[valid] /= lengths[valid, None]
    normals[~valid] = 0.0
    dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attribute", "<u2"),
    ])
    records = np.zeros(len(triangles), dtype=dtype)
    records["normal"] = normals.astype(np.float32)
    records["vertices"] = triangles.astype(np.float32)
    encoded_header = header.encode("ascii", errors="replace")[:80].ljust(80, b" ")
    with path.open("wb") as stream:
        stream.write(encoded_header)
        stream.write(struct.pack("<I", len(records)))
        stream.write(records.tobytes())


def connected_component_count(triangles: np.ndarray, tolerance: float = 1e-4) -> int:
    """Count disconnected triangle components through quantized shared vertices."""
    count = len(triangles)
    parent = np.arange(count, dtype=np.int32)
    rank = np.zeros(count, dtype=np.uint8)

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = int(parent[index])
        return index

    def union(first: int, second: int) -> None:
        first_root = find(first)
        second_root = find(second)
        if first_root == second_root:
            return
        if rank[first_root] < rank[second_root]:
            first_root, second_root = second_root, first_root
        parent[second_root] = first_root
        if rank[first_root] == rank[second_root]:
            rank[first_root] += 1

    owners: dict[tuple[int, int, int], int] = {}
    quantized = np.rint(triangles / tolerance).astype(np.int64)
    for triangle_index, triangle in enumerate(quantized):
        for vertex in triangle:
            key = (int(vertex[0]), int(vertex[1]), int(vertex[2]))
            other = owners.setdefault(key, triangle_index)
            union(triangle_index, other)
    return len({find(index) for index in range(count)})


def normalized(vector: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(vector))
    if length < 1e-12:
        raise ValueError("Cannot normalize zero vector")
    return vector / length


def signed_permutation_bases(seed: np.ndarray):
    for permutation in itertools.permutations(range(3)):
        permuted = seed[:, permutation]
        for signs in itertools.product((-1.0, 1.0), repeat=3):
            basis = permuted * np.asarray(signs)[None, :]
            if np.linalg.det(basis) > 0.999:
                yield basis


def candidate_bases(triangles: np.ndarray) -> list[np.ndarray]:
    points = triangles.reshape(-1, 3)
    centered = points - points.mean(axis=0)
    covariance = centered.T @ centered / max(len(centered), 1)
    values, vectors = np.linalg.eigh(covariance)
    pca = vectors[:, np.argsort(values)[::-1]]
    if np.linalg.det(pca) < 0:
        pca[:, 2] *= -1

    candidates: list[np.ndarray] = []
    candidates.extend(signed_permutation_bases(pca))
    candidates.extend(signed_permutation_bases(np.eye(3)))

    edge_a = triangles[:, 1] - triangles[:, 0]
    edge_b = triangles[:, 2] - triangles[:, 0]
    cross = np.cross(edge_a, edge_b)
    twice_area = np.linalg.norm(cross, axis=1)
    ranked = np.argsort(twice_area)[::-1]
    unique_normals: list[np.ndarray] = []
    for index in ranked:
        if twice_area[index] < 1e-8:
            continue
        normal = cross[index] / twice_area[index]
        if all(abs(float(np.dot(normal, other))) < math.cos(math.radians(4.0))
               for other in unique_normals):
            unique_normals.append(normal)
        if len(unique_normals) >= 36:
            break

    for normal in unique_normals:
        for sign in (-1.0, 1.0):
            z_axis = normal * sign
            projections = [axis - z_axis * float(np.dot(axis, z_axis)) for axis in pca.T]
            x_axis = max(projections, key=lambda item: float(np.linalg.norm(item)))
            x_axis = normalized(x_axis)
            y_axis = normalized(np.cross(z_axis, x_axis))
            x_axis = normalized(np.cross(y_axis, z_axis))
            candidates.append(np.column_stack((x_axis, y_axis, z_axis)))
            candidates.append(np.column_stack((y_axis, -x_axis, z_axis)))

    deduped: list[np.ndarray] = []
    for basis in candidates:
        key = tuple(np.round(basis.reshape(-1), 5))
        if not any(tuple(np.round(existing.reshape(-1), 5)) == key for existing in deduped):
            deduped.append(basis)
    return deduped


def orient_for_print(triangles: np.ndarray, usable: float) -> dict:
    points = triangles.reshape(-1, 3)
    center = points.mean(axis=0)
    tri_area = np.linalg.norm(
        np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]),
        axis=1,
    ) * 0.5
    candidates = []
    for basis in candidate_bases(triangles):
        transformed = (triangles - center) @ basis
        minimum = transformed.reshape(-1, 3).min(axis=0)
        maximum = transformed.reshape(-1, 3).max(axis=0)
        dims = maximum - minimum
        if dims[0] > usable or dims[1] > usable:
            continue
        local_z = transformed[:, :, 2]
        bottom = float(minimum[2])
        contact_mask = np.max(np.abs(local_z - bottom), axis=1) <= 0.20
        contact_area = float(tri_area[contact_mask].sum())
        footprint = max(float(dims[0] * dims[1]), 1e-9)
        contact_ratio = contact_area / footprint
        max_dim = max(float(dims.max()), 1e-9)
        height_ratio = float(dims[2]) / max_dim
        score = (
            0.68 * height_ratio
            + 0.20 * (footprint / (usable * usable))
            - 0.12 * min(contact_ratio / 0.25, 1.0)
        )
        candidates.append((score, -contact_area, float(dims[2]), basis, transformed, dims,
                           contact_area, contact_ratio))
    if not candidates:
        raise ValueError("No print orientation fits the usable plate")
    max_contact_area = max(item[6] for item in candidates)
    if max_contact_area >= 0.5:
        minimum_contact_area = max(0.5, max_contact_area * 0.20)
        stable_candidates = [item for item in candidates if item[6] >= minimum_contact_area]
        if stable_candidates:
            candidates = stable_candidates
    candidates.sort(key=lambda item: item[:3])
    score, _, _, basis, transformed, dims, contact_area, contact_ratio = candidates[0]
    minimum = transformed.reshape(-1, 3).min(axis=0)
    transformed -= minimum
    return {
        "triangles": transformed,
        "basis": basis,
        "dims": dims,
        "contactArea": contact_area,
        "maxCandidateContactArea": max_contact_area,
        "contactRatio": contact_ratio,
        "orientationScore": score,
    }


def intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw - 1e-9 and ax + aw > bx + 1e-9 and ay < by + bh - 1e-9 and ay + ah > by + 1e-9


def contained(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax >= bx - 1e-9 and ay >= by - 1e-9 and ax + aw <= bx + bw + 1e-9 and ay + ah <= by + bh + 1e-9


def split_free_rectangles(free_rectangles, used):
    ux, uy, uw, uh = used
    uright, utop = ux + uw, uy + uh
    result = []
    for free in free_rectangles:
        if not intersects(free, used):
            result.append(free)
            continue
        fx, fy, fw, fh = free
        fright, ftop = fx + fw, fy + fh
        if ux > fx:
            result.append((fx, fy, ux - fx, fh))
        if uright < fright:
            result.append((uright, fy, fright - uright, fh))
        if uy > fy:
            result.append((fx, fy, fw, uy - fy))
        if utop < ftop:
            result.append((fx, utop, fw, ftop - utop))
    result = [rect for rect in result if rect[2] > 0.1 and rect[3] > 0.1]
    pruned = []
    for index, rect in enumerate(result):
        if any(index != other and contained(rect, candidate) for other, candidate in enumerate(result)):
            continue
        pruned.append(rect)
    return pruned


def placement_options(plate, width, height):
    options = []
    for free_index, (x, y, free_w, free_h) in enumerate(plate["free"]):
        for rotate, (item_w, item_h) in enumerate(((width, height), (height, width))):
            if item_w <= free_w + 1e-9 and item_h <= free_h + 1e-9:
                leftover_area = free_w * free_h - item_w * item_h
                short_side = min(free_w - item_w, free_h - item_h)
                long_side = max(free_w - item_w, free_h - item_h)
                options.append(((leftover_area, short_side, long_side), free_index,
                                (x, y, item_w, item_h), bool(rotate)))
    return options


def pack_once(items, usable, gap, order):
    plates = []
    for item_index in order:
        item = items[item_index]
        packed_w = float(item["dims"][0]) + gap
        packed_h = float(item["dims"][1]) + gap
        choices = []
        for plate_index, plate in enumerate(plates):
            for option in placement_options(plate, packed_w, packed_h):
                choices.append((option[0], plate_index, option))
        if choices:
            _, plate_index, option = min(choices, key=lambda choice: choice[0])
        else:
            plate_index = len(plates)
            plates.append({"free": [(0.0, 0.0, usable, usable)], "placements": []})
            options = placement_options(plates[-1], packed_w, packed_h)
            if not options:
                raise ValueError(f"Part does not fit plate: {item['name']} {item['dims']}")
            option = min(options, key=lambda candidate: candidate[0])
        _, _, used, rotated = option
        plate = plates[plate_index]
        plate["free"] = split_free_rectangles(plate["free"], used)
        plate["placements"].append({"item": item_index, "cell": used, "rotated90": rotated})
    return plates


def pack_items(items, usable, gap, trials=600):
    rng = random.Random(1105)
    indices = list(range(len(items)))
    orders = [
        sorted(indices, key=lambda i: float(items[i]["dims"][0] * items[i]["dims"][1]), reverse=True),
        sorted(indices, key=lambda i: float(max(items[i]["dims"][:2])), reverse=True),
        sorted(indices, key=lambda i: float(sum(items[i]["dims"][:2])), reverse=True),
    ]
    areas = np.asarray([float(item["dims"][0] * item["dims"][1]) for item in items])
    for _ in range(trials):
        jitter = np.asarray([rng.uniform(0.75, 1.25) for _ in items])
        orders.append(list(np.argsort(-(areas * jitter))))
    best = None
    best_score = None
    for order in orders:
        plates = pack_once(items, usable, gap, order)
        extents = []
        for plate in plates:
            right = max((placement["cell"][0] + placement["cell"][2]
                         for placement in plate["placements"]), default=0.0)
            top = max((placement["cell"][1] + placement["cell"][3]
                       for placement in plate["placements"]), default=0.0)
            extents.append(right * top)
        score = (len(plates), sum(extents), max(extents, default=0.0))
        if best_score is None or score < best_score:
            best_score = score
            best = plates
    return best


def transform_placement(item, placement, margin, gap):
    triangles = item["triangles"].copy()
    if placement["rotated90"]:
        x = triangles[:, :, 0].copy()
        triangles[:, :, 0] = -triangles[:, :, 1]
        triangles[:, :, 1] = x
        minimum = triangles.reshape(-1, 3).min(axis=0)
        triangles -= minimum
    x, y, _, _ = placement["cell"]
    triangles[:, :, 0] += margin + x + gap / 2.0
    triangles[:, :, 1] += margin + y + gap / 2.0
    return triangles


def font(size=20, bold=False):
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def render_layout(path, plate, items, bed, margin, gap, index, total):
    scale = 3.2
    border = 70
    size = int(round(bed * scale))
    image = Image.new("RGB", (size + border * 2, size + border * 2 + 80), (20, 27, 34))
    draw = ImageDraw.Draw(image)
    x0, y0 = border, border + 55
    draw.rectangle((x0, y0, x0 + size, y0 + size), fill=(49, 58, 66), outline=(202, 211, 218), width=3)
    safe = margin * scale
    draw.rectangle((x0 + safe, y0 + safe, x0 + size - safe, y0 + size - safe),
                   outline=(91, 166, 204), width=2)
    colors = [(68, 143, 181), (219, 139, 57), (83, 166, 128), (180, 105, 145), (156, 149, 71)]
    for order, placement in enumerate(plate["placements"]):
        item = items[placement["item"]]
        cell_x, cell_y, cell_w, cell_h = placement["cell"]
        actual_w = float(item["dims"][1] if placement["rotated90"] else item["dims"][0])
        actual_h = float(item["dims"][0] if placement["rotated90"] else item["dims"][1])
        px = x0 + (margin + cell_x + gap / 2.0) * scale
        py = y0 + (margin + cell_y + gap / 2.0) * scale
        color = colors[order % len(colors)]
        draw.rounded_rectangle((px, py, px + actual_w * scale, py + actual_h * scale),
                               radius=5, fill=color, outline=(235, 241, 245), width=2)
        label = item["name"]
        label_font = font(13 if len(label) > 18 else 15, True)
        bbox = draw.textbbox((0, 0), label, font=label_font)
        if bbox[2] - bbox[0] > actual_w * scale - 6:
            label = str(order + 1)
            label_font = font(15, True)
            bbox = draw.textbbox((0, 0), label, font=label_font)
        draw.text((px + (actual_w * scale - (bbox[2] - bbox[0])) / 2,
                   py + (actual_h * scale - (bbox[3] - bbox[1])) / 2 - 2),
                  label, font=label_font, fill=(249, 251, 252))
    title = f"ONEGRIP RIGHT HAND  /  PLATE {index:02d} OF {total:02d}"
    draw.text((border, 20), title, font=font(27, True), fill=(240, 244, 247))
    draw.text((border, y0 + size + 18),
              f"BED {bed:.0f} x {bed:.0f} mm  |  EDGE {margin:.0f} mm  |  PART GAP {gap:.0f} mm  |  {len(plate['placements'])} PARTS",
              font=font(18), fill=(182, 197, 207))
    image.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bed", type=float, default=256.0)
    parser.add_argument("--margin", type=float, default=8.0)
    parser.add_argument("--gap", type=float, default=10.0)
    args = parser.parse_args()

    usable = args.bed - 2.0 * args.margin
    if usable <= 0 or args.gap <= 0:
        raise ValueError("Invalid bed, margin, or gap")
    paths = sorted(args.input.glob("*.stl"))
    if len(paths) != 30:
        raise ValueError(f"Expected 30 STL parts, found {len(paths)}")
    args.output.mkdir(parents=True, exist_ok=True)

    items = []
    for path in paths:
        triangles = read_binary_stl(path)
        orientation = orient_for_print(triangles, usable)
        items.append({
            "name": display_name(path),
            "source": path.name,
            "triangleCount": len(triangles),
            **orientation,
        })

    plates = pack_items(items, usable, args.gap)
    manifest = {
        "source": "Onshape RIGHT_HAND_MIRROR / Joystick Part Studio",
        "configuration": "default",
        "partCount": len(items),
        "plateCount": len(plates),
        "bedMm": [args.bed, args.bed],
        "usableMm": [usable, usable],
        "edgeMarginMm": args.margin,
        "minimumPartGapMm": args.gap,
        "plates": [],
    }

    for plate_index, plate in enumerate(plates, start=1):
        transformed_meshes = []
        plate_record = {"index": plate_index, "parts": []}
        occupied_boxes = []
        for placement in plate["placements"]:
            item = items[placement["item"]]
            transformed = transform_placement(item, placement, args.margin, args.gap)
            transformed_meshes.append(transformed)
            minimum = transformed.reshape(-1, 3).min(axis=0)
            maximum = transformed.reshape(-1, 3).max(axis=0)
            box = [float(minimum[0]), float(minimum[1]), float(maximum[0]), float(maximum[1])]
            occupied_boxes.append((item["name"], box))
            plate_record["parts"].append({
                "name": item["name"],
                "source": item["source"],
                "triangles": item["triangleCount"],
                "rotated90OnPlate": placement["rotated90"],
                "bboxMinMm": [float(value) for value in minimum],
                "bboxMaxMm": [float(value) for value in maximum],
                "sizeMm": [float(value) for value in maximum - minimum],
                "estimatedBedContactAreaMm2": item["contactArea"],
                "maximumCandidateBedContactAreaMm2": item["maxCandidateContactArea"],
                "orientationBasis": [[float(value) for value in row] for row in item["basis"]],
            })

        minimum_clearance = float("inf")
        for first_index, (first_name, first) in enumerate(occupied_boxes):
            for second_name, second in occupied_boxes[first_index + 1:]:
                x_gap = max(second[0] - first[2], first[0] - second[2], 0.0)
                y_gap = max(second[1] - first[3], first[1] - second[3], 0.0)
                clearance = math.hypot(x_gap, y_gap)
                minimum_clearance = min(minimum_clearance, clearance)
                if x_gap < args.gap - 1e-4 and y_gap < args.gap - 1e-4:
                    raise AssertionError(f"Unsafe gap: {first_name} / {second_name}: {x_gap}, {y_gap}")
        combined = np.concatenate(transformed_meshes, axis=0)
        minimum = combined.reshape(-1, 3).min(axis=0)
        maximum = combined.reshape(-1, 3).max(axis=0)
        if minimum[0] < args.margin - 1e-4 or minimum[1] < args.margin - 1e-4:
            raise AssertionError("Plate edge margin violated")
        if maximum[0] > args.bed - args.margin + 1e-4 or maximum[1] > args.bed - args.margin + 1e-4:
            raise AssertionError("Plate boundary violated")
        if maximum[2] > args.bed + 1e-4:
            raise AssertionError("Build height violated")
        components = connected_component_count(combined)
        if components != len(plate["placements"]):
            raise AssertionError(
                f"Expected {len(plate['placements'])} disconnected parts, got {components}"
            )

        stl_name = f"OneGrip_RightHand_Handle_plate_{plate_index:02d}_of_{len(plates):02d}.stl"
        preview_name = f"OneGrip_RightHand_Handle_plate_{plate_index:02d}_layout.png"
        write_binary_stl(args.output / stl_name, combined,
                         f"OneGrip RH handle plate {plate_index}/{len(plates)}; gap {args.gap}mm")
        render_layout(args.output / preview_name, plate, items, args.bed, args.margin,
                      args.gap, plate_index, len(plates))
        plate_record["stl"] = stl_name
        plate_record["preview"] = preview_name
        plate_record["bboxMinMm"] = [float(value) for value in minimum]
        plate_record["bboxMaxMm"] = [float(value) for value in maximum]
        plate_record["triangleCount"] = int(len(combined))
        plate_record["connectedComponents"] = components
        plate_record["minimumPartClearanceMm"] = minimum_clearance
        manifest["plates"].append(plate_record)

    (args.output / "layout_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "parts": len(items),
        "plates": len(plates),
        "output": str(args.output),
        "partsPerPlate": [len(plate["placements"]) for plate in plates],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
