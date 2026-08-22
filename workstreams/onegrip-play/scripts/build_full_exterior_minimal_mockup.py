"""Build a current-Main exterior validation mockup from one Onshape STL ZIP.

The script never mixes cached meshes or mirrored exports.  Every displayed CAD
part is read from ``exports/full_exterior_minimal_mockup/source_stl``, which is
the 30-part ZIP exported from the live Joystick Part Studio after Stage D.

Two STL outputs are intentional:

* ``Exterior_Alignment_Check`` preserves every selected source triangle and
  coordinate exactly.  It is the geometry/position source of truth.
* ``Exterior_Mockup_SlicerUnion`` adds small, closed, positive-overlap bridge
  cylinders.  Modern slicers union these overlapping shells into one rigid
  non-functional handling mockup.  No source part is moved or rescaled.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import (  # noqa: E402
    read_binary_stl,
    write_binary_stl,
)
import render_index_its_audit as render  # noqa: E402


OUT = ROOT / "exports" / "full_exterior_minimal_mockup"
SOURCE = OUT / "source_stl"
SOURCE_ZIP = OUT / "Joystick_Current_Main_StageD.zip"
RENDER_DIR = OUT / "renders"

SHELLS = ("Joystick_1", "Joystick_2")
BACKPLATE = ("Backplate",)
THUMB_CAPS = (
    "Button_wide_1", "Button_side_1", "Button_corner_1",
    "Button_corner_2", "Button_side_2", "Button_wide_2",
    "Button_middle_1", "Button_middle_2",
)
INDEX_CAPS = ("Part 13", "Part 14", "Part 15", "Part 16")
MIDDLE_CAPS = ("Part 24", "Part 26", "Part 28", "Part 30")
EXTERIOR = SHELLS + BACKPLATE + THUMB_CAPS + INDEX_CAPS + MIDDLE_CAPS

ROLE = {
    "Part 13": "INDEX I1 cap",
    "Part 14": "INDEX I2 cap",
    "Part 15": "INDEX I3 cap",
    "Part 16": "INDEX I4 cap",
    "Part 24": "MIDDLE M1 cap",
    "Part 26": "MIDDLE M2 cap",
    "Part 28": "MIDDLE M3 cap",
    "Part 30": "MIDDLE M4 cap",
}

COLORS = {
    "Joystick_1": (67, 113, 142),
    "Joystick_2": (82, 132, 160),
    "Backplate": (116, 128, 142),
}


def source_path(name: str) -> Path:
    return SOURCE / f"Joystick - {name}.stl"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mesh_volume(triangles: np.ndarray) -> float:
    signed = np.einsum(
        "ij,ij->i",
        triangles[:, 0],
        np.cross(triangles[:, 1], triangles[:, 2]),
    ).sum() / 6.0
    return abs(float(signed))


def topology(triangles: np.ndarray, tolerance: float = 1e-5) -> dict:
    quantized = np.rint(triangles / tolerance).astype(np.int64)
    edge_counts: dict[tuple[tuple[int, int, int], tuple[int, int, int]], int] = {}
    for triangle in quantized:
        keys = [tuple(int(value) for value in vertex) for vertex in triangle]
        for first, second in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((keys[first], keys[second])))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    counts = np.fromiter(edge_counts.values(), dtype=np.int32)
    return {
        "boundaryEdges": int(np.count_nonzero(counts == 1)),
        "nonManifoldEdges": int(np.count_nonzero(counts > 2)),
    }


def cylinder_between(
    start: np.ndarray,
    end: np.ndarray,
    radius: float,
    segments: int = 20,
) -> np.ndarray:
    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)
    axis = end - start
    length = float(np.linalg.norm(axis))
    if length < 1e-8:
        raise ValueError("Bridge endpoints coincide")
    axis /= length
    seed = np.asarray((1.0, 0.0, 0.0))
    if abs(float(np.dot(seed, axis))) > 0.85:
        seed = np.asarray((0.0, 1.0, 0.0))
    u = np.cross(axis, seed)
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    angles = np.arange(segments) * (2.0 * math.pi / segments)
    circle = np.cos(angles)[:, None] * u + np.sin(angles)[:, None] * v
    ring_a = start + radius * circle
    ring_b = end + radius * circle
    triangles = []
    for index in range(segments):
        nxt = (index + 1) % segments
        triangles.append((ring_a[index], ring_b[index], ring_b[nxt]))
        triangles.append((ring_a[index], ring_b[nxt], ring_a[nxt]))
        triangles.append((start, ring_a[nxt], ring_a[index]))
        triangles.append((end, ring_b[index], ring_b[nxt]))
    return np.asarray(triangles, dtype=float)


def unique_points(triangles: np.ndarray) -> np.ndarray:
    points = np.round(triangles.reshape(-1, 3), 6)
    return np.unique(points, axis=0)


def nearest_vertex(point: np.ndarray, target_points: np.ndarray) -> tuple[np.ndarray, float]:
    delta = target_points - np.asarray(point, dtype=float)
    squared = np.einsum("ij,ij->i", delta, delta)
    index = int(np.argmin(squared))
    return target_points[index], math.sqrt(float(squared[index]))


def sampled_vertex_gap(first: np.ndarray, second: np.ndarray) -> float:
    """Return a conservative vertex-sample sanity distance, not a B-rep gap."""
    a = unique_points(first)
    b = unique_points(second)
    if len(a) > 512:
        a = a[np.linspace(0, len(a) - 1, 512, dtype=int)]
    if len(b) > 60000:
        b = b[np.linspace(0, len(b) - 1, 60000, dtype=int)]
    best = math.inf
    for offset in range(0, len(a), 16):
        block = a[offset:offset + 16]
        delta = block[:, None, :] - b[None, :, :]
        squared = np.einsum("ijk,ijk->ij", delta, delta)
        best = min(best, math.sqrt(float(squared.min())))
    return best


def seam_bridges(shell_a: np.ndarray, shell_b: np.ndarray) -> list[dict]:
    """Place three internal cross-seam pins on large x=0 closure faces."""
    candidates = []
    for triangle in shell_a:
        if float(np.max(np.abs(triangle[:, 0]))) > 2e-4:
            continue
        area = 0.5 * float(np.linalg.norm(np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])))
        if area < 2.0:
            continue
        candidates.append((area, triangle.mean(axis=0)))
    candidates.sort(key=lambda row: row[0], reverse=True)
    chosen: list[np.ndarray] = []
    for _area, center in candidates:
        if all(float(np.linalg.norm(center[1:] - other[1:])) > 24.0 for other in chosen):
            chosen.append(center)
        if len(chosen) == 3:
            break
    if not chosen:
        # Deterministic fallback in the thick central handle region.
        chosen = [np.asarray((0.0, 8.0, 18.0))]
    records = []
    for index, center in enumerate(chosen, start=1):
        start = center.copy()
        end = center.copy()
        start[0] = -1.6
        end[0] = 1.6
        records.append({
            "name": f"shell seam bridge {index}",
            "start": start,
            "end": end,
            "radiusMm": 1.25,
            "triangles": cylinder_between(start, end, 1.25),
        })
    return records


def bridge_to_target(
    name: str,
    mesh: np.ndarray,
    target_points: np.ndarray,
    radius: float,
) -> dict:
    low = mesh.reshape(-1, 3).min(axis=0)
    high = mesh.reshape(-1, 3).max(axis=0)
    center = (low + high) * 0.5
    surface, distance = nearest_vertex(center, target_points)
    direction = surface - center
    direction /= max(float(np.linalg.norm(direction)), 1e-12)
    # The start remains well inside the cap/body.  The end penetrates the
    # target by 1.2 mm, satisfying the positive-overlap print-mockup gate.
    start = center - direction * 0.35
    end = surface + direction * 1.20
    return {
        "name": name,
        "start": start,
        "end": end,
        "radiusMm": radius,
        "centerToNearestTargetVertexMm": distance,
        "positiveTargetPenetrationMm": 1.20,
        "triangles": cylinder_between(start, end, radius),
    }


def render_full(meshes: dict[str, np.ndarray], path: Path) -> None:
    objects = []
    for name in EXTERIOR:
        if name in SHELLS:
            color = COLORS[name]
        elif name == "Backplate":
            color = COLORS[name]
        elif name in THUMB_CAPS:
            color = (219, 151, 67)
        elif name in INDEX_CAPS:
            color = (84, 174, 210)
        else:
            color = (101, 185, 126)
        objects.append((meshes[name], color))
    image, _projection = render.rasterize(objects)
    draw = ImageDraw.Draw(image)
    draw.text((48, 36), "ONEGRIP CURRENT MAIN / EXTERIOR MOCKUP",
              font=render.font(37, True), fill=(241, 245, 248, 255))
    draw.text((50, 83), "STAGE-D  /  19 LIVE PART-STUDIO SOLIDS  /  NO CACHED GEOMETRY",
              font=render.font(20, False), fill=(174, 194, 207, 255))
    draw.rounded_rectangle((48, render.HEIGHT - 105, 940, render.HEIGHT - 40),
                           radius=13, fill=(10, 15, 22, 215),
                           outline=(86, 105, 118, 220), width=2)
    legend = (
        ((74, 123, 151), "shells"),
        ((116, 128, 142), "Backplate"),
        ((219, 151, 67), "thumb caps"),
        ((84, 174, 210), "INDEX caps"),
        ((101, 185, 126), "MIDDLE caps"),
    )
    x = 70
    for color, label in legend:
        draw.ellipse((x, render.HEIGHT - 84, x + 21, render.HEIGHT - 63), fill=(*color, 255))
        draw.text((x + 30, render.HEIGHT - 89), label, font=render.font(17),
                  fill=(226, 234, 240, 255))
        x += 170
    image.convert("RGB").save(path, quality=96)


def render_opposite(meshes: dict[str, np.ndarray], path: Path) -> None:
    """Render the opposite shell side; the 180-degree Z rotation is preview-only."""
    objects = []
    for name in EXTERIOR:
        preview_mesh = meshes[name].copy()
        preview_mesh[:, :, :2] *= -1.0
        if name in SHELLS:
            color = COLORS[name]
        elif name == "Backplate":
            color = COLORS[name]
        elif name in THUMB_CAPS:
            color = (219, 151, 67)
        elif name in INDEX_CAPS:
            color = (84, 174, 210)
        else:
            color = (101, 185, 126)
        objects.append((preview_mesh, color))
    image, _projection = render.rasterize(objects)
    draw = ImageDraw.Draw(image)
    draw.text((48, 36), "ONEGRIP CURRENT MAIN / FINGER-CONTROL SIDE",
              font=render.font(37, True), fill=(241, 245, 248, 255))
    draw.text((50, 83), "PREVIEW-ONLY 180 DEG VIEW  /  STL COORDINATES ARE UNCHANGED",
              font=render.font(20, False), fill=(174, 194, 207, 255))
    image.convert("RGB").save(path, quality=96)


def detail_mesh(triangles: np.ndarray, low: np.ndarray, high: np.ndarray) -> np.ndarray:
    center = triangles.mean(axis=1)
    keep = np.all((center >= low) & (center <= high), axis=1)
    return triangles[keep]


def render_details(meshes: dict[str, np.ndarray], path: Path) -> None:
    shell = np.concatenate([meshes[name] for name in SHELLS])
    panels = []
    regions = (
        ("THUMB OPENINGS / CAPS", np.asarray((-24.0, -22.0, 23.0)), np.asarray((24.0, 17.0, 57.0)), THUMB_CAPS),
        ("INDEX + MIDDLE OPENINGS / CAPS", np.asarray((-30.0, -38.0, -22.0)), np.asarray((18.0, 10.0, 22.0)), INDEX_CAPS + MIDDLE_CAPS),
    )
    for title, low, high, caps in regions:
        objects = [(detail_mesh(shell, low, high), (76, 129, 158))]
        for name in caps:
            color = (219, 151, 67) if name in THUMB_CAPS else ((84, 174, 210) if name in INDEX_CAPS else (101, 185, 126))
            objects.append((meshes[name], color))
        image, _ = render.rasterize(objects)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((35, 28, 730, 84), radius=12, fill=(8, 13, 20, 220),
                               outline=(103, 124, 139, 220), width=2)
        draw.text((56, 40), title, font=render.font(25, True), fill=(239, 244, 248, 255))
        panels.append(image.convert("RGB").resize((750, 562), Image.Resampling.LANCZOS))
    canvas = Image.new("RGB", (1500, 562), (13, 19, 27))
    canvas.paste(panels[0], (0, 0))
    canvas.paste(panels[1], (750, 0))
    canvas.save(path, quality=96)


def main() -> None:
    missing = [name for name in EXTERIOR if not source_path(name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing current-Main STL sources: {missing}")
    meshes = {name: read_binary_stl(source_path(name)) for name in EXTERIOR}
    if len(list(SOURCE.glob("*.stl"))) != 30:
        raise RuntimeError("Current-Main source set must contain exactly 30 STL files")

    part_report = {}
    for name, triangles in meshes.items():
        points = triangles.reshape(-1, 3)
        part_report[name] = {
            "role": ROLE.get(name, name),
            "triangles": int(len(triangles)),
            "bboxMinMm": points.min(axis=0).tolist(),
            "bboxMaxMm": points.max(axis=0).tolist(),
            "volumeMm3": mesh_volume(triangles),
            **topology(triangles),
        }
        if part_report[name]["boundaryEdges"] or part_report[name]["nonManifoldEdges"]:
            raise RuntimeError(f"Source STL topology failed for {name}: {part_report[name]}")

    alignment = np.concatenate([meshes[name] for name in EXTERIOR])
    alignment_path = OUT / "OneGrip_Current_Main_Exterior_Alignment_Check.stl"
    write_binary_stl(
        alignment_path,
        alignment,
        "OneGrip current Main Stage-D exact exterior alignment / 19 solids",
    )

    shell_mesh = np.concatenate([meshes[name] for name in SHELLS])
    shell_points = unique_points(shell_mesh)
    backplate_points = unique_points(meshes["Backplate"])
    thumb_target_points = np.concatenate((shell_points, backplate_points))

    bridges = seam_bridges(meshes["Joystick_1"], meshes["Joystick_2"])
    bridges.append(bridge_to_target("Backplate to shell", meshes["Backplate"], shell_points, 1.10))
    for name in THUMB_CAPS:
        bridges.append(bridge_to_target(f"{name} to module", meshes[name], thumb_target_points, 0.72))
    for name in INDEX_CAPS + MIDDLE_CAPS:
        bridges.append(bridge_to_target(f"{ROLE[name]} to shell", meshes[name], shell_points, 0.72))

    bridge_triangles = np.concatenate([record["triangles"] for record in bridges])
    printable = np.concatenate((alignment, bridge_triangles))
    printable_path = OUT / "OneGrip_Current_Main_Exterior_Mockup_SlicerUnion.stl"
    write_binary_stl(
        printable_path,
        printable,
        "OneGrip current Main Stage-D exterior handling mockup / overlap bridges",
    )

    cap_gap_sanity = {}
    for name in THUMB_CAPS:
        cap_gap_sanity[name] = sampled_vertex_gap(meshes[name], np.concatenate((shell_mesh, meshes["Backplate"])))
    for name in INDEX_CAPS + MIDDLE_CAPS:
        cap_gap_sanity[name] = sampled_vertex_gap(meshes[name], shell_mesh)

    manifest = {
        "source": {
            "document": "OneGrip_Play_V1",
            "workspace": "Main",
            "partStudio": "Joystick",
            "stage": "Stage D",
            "zip": SOURCE_ZIP.name,
            "zipSha256": sha256(SOURCE_ZIP),
            "sourceStlCount": 30,
            "coordinatePolicy": "all selected triangles preserved in original current-Main coordinates",
        },
        "selection": {
            "selectedExteriorSolids": list(EXTERIOR),
            "selectedCount": len(EXTERIOR),
            "excluded": {
                "Small_joystick_attachment": "Part Studio staging position; assembly mate transform is not present in this ZIP",
                "Part 17/18": "internal retainers",
                "Part 19/20/21/22/23/25/27/29": "internal spacers",
            },
        },
        "outputs": {
            "alignment": {
                "file": alignment_path.name,
                "triangles": int(len(alignment)),
                "sha256": sha256(alignment_path),
                "purpose": "exact multi-solid position/alignment validation",
            },
            "printableMockup": {
                "file": printable_path.name,
                "triangles": int(len(printable)),
                "sha256": sha256(printable_path),
                "purpose": "non-functional handling mockup; enable union-overlapping-volumes in slicer",
                "bridgeCount": len(bridges),
                "bridgePolicy": "closed cylinders with 1.2 mm positive target penetration; no source part moved",
            },
        },
        "partAudit": part_report,
        "capToOpeningSanity": {
            "method": "sampled source-mesh vertex proximity; sanity check only",
            "distanceMm": cap_gap_sanity,
            "primaryGate": "all shells and caps come from one 30-solid current-Main Part Studio export with zero transforms",
        },
        "bridges": [
            {key: (value.tolist() if isinstance(value, np.ndarray) else value)
             for key, value in record.items() if key != "triangles"}
            for record in bridges
        ],
        "limitations": [
            "This is a non-functional exterior handling mockup; buttons are immobilized by sacrificial bridges.",
            "The printable STL contains closed overlapping shells, not a CAD B-rep boolean union. Enable slicer union/merge overlapping volumes.",
            "Small_joystick_attachment is intentionally omitted because its assembly mate transform is not encoded in the Part Studio ZIP.",
        ],
    }
    (OUT / "mockup_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    render_full(meshes, RENDER_DIR / "OneGrip_Current_Main_Exterior_Mockup.png")
    render_opposite(meshes, RENDER_DIR / "OneGrip_Current_Main_Finger_Control_Side.png")
    render_details(meshes, RENDER_DIR / "OneGrip_Current_Main_Opening_Cap_Details.png")
    print(json.dumps({
        "alignment": str(alignment_path),
        "printable": str(printable_path),
        "selected": len(EXTERIOR),
        "bridges": len(bridges),
        "triangles": {"alignment": len(alignment), "printable": len(printable)},
        "renders": [str(path) for path in sorted(RENDER_DIR.glob("*.png"))],
    }, indent=2))


if __name__ == "__main__":
    main()
