"""Offline housing-first study for an additional 15 mm THUMB-cluster drop.

The current Stage-D 30-part Onshape STL export is the only geometry source.
INDEX/MIDDLE holders, switches, screws and wiring are deliberately outside this
stage's acceptance gate, matching the user's housing-first instruction.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
from PIL import ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402
import render_index_its_audit as render  # noqa: E402


SOURCE = ROOT / "exports" / "full_exterior_minimal_mockup" / "source_stl"
OUT_JSON = ROOT / "cad_dump" / "thumb_lower15_housing_study.json"
OUT_RENDER = ROOT / "renders" / "thumb_lower15_housing_seed.png"

CAPS = (
    "Button_wide_1", "Button_side_1", "Button_corner_1",
    "Button_corner_2", "Button_side_2", "Button_wide_2",
    "Button_middle_1", "Button_middle_2",
)
CURRENT_FROM_ORIGINAL = np.asarray((0.0, 5.5, -6.0), dtype=float)
ADDITIONAL_Z = -15.0


def path(name: str) -> Path:
    return SOURCE / f"Joystick - {name}.stl"


def unique_points(triangles: np.ndarray) -> np.ndarray:
    return np.unique(np.round(triangles.reshape(-1, 3), 5), axis=0)


def center(triangles: np.ndarray) -> np.ndarray:
    points = triangles.reshape(-1, 3)
    return (points.min(axis=0) + points.max(axis=0)) * 0.5


def nearest_distance(point: np.ndarray, target: np.ndarray) -> float:
    delta = target - point
    return float(np.sqrt(np.min(np.einsum("ij,ij->i", delta, delta))))


def sampled_mesh_distance(first: np.ndarray, second_points: np.ndarray, maximum: int = 900) -> float:
    points = unique_points(first)
    if len(points) > maximum:
        points = points[np.linspace(0, len(points) - 1, maximum, dtype=int)]
    best = np.inf
    for offset in range(0, len(points), 12):
        block = points[offset:offset + 12]
        delta = block[:, None, :] - second_points[None, :, :]
        squared = np.einsum("ijk,ijk->ij", delta, delta)
        best = min(best, float(np.sqrt(squared.min())))
    return best


def render_seed(meshes: dict[str, np.ndarray], additional: np.ndarray) -> None:
    objects = [
        (meshes["Joystick_1"], (68, 118, 147)),
        (meshes["Joystick_2"], (79, 132, 158)),
    ]
    # Current caps remain as translucent-looking dark references; the proposed
    # rigid cluster is rendered in amber.  The geometry itself is not written.
    for name in CAPS:
        objects.append((meshes[name], (75, 82, 91)))
    objects.append((meshes["Backplate"] + additional, (153, 121, 64)))
    for name in CAPS:
        objects.append((meshes[name] + additional, (230, 155, 63)))
    image, _ = render.rasterize(objects)
    draw = ImageDraw.Draw(image)
    draw.text((48, 35), "THUMB CLUSTER / ADDITIONAL -15 mm HOUSING SEED",
              font=render.font(35, True), fill=(242, 246, 249, 255))
    draw.text((50, 82),
              f"CURRENT (0,+5.5,-6)  ->  TARGET TOTAL (0,{CURRENT_FROM_ORIGINAL[1] + additional[1]:+.1f},-21) mm",
              font=render.font(20), fill=(176, 196, 208, 255))
    draw.text((50, render.HEIGHT - 67),
              "HOUSING-FIRST STUDY / INDEX-MIDDLE INTERNALS EXCLUDED",
              font=render.font(19, True), fill=(221, 180, 93, 255))
    OUT_RENDER.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUT_RENDER, quality=96)


def main() -> None:
    required = ("Joystick_1", "Joystick_2", "Backplate") + CAPS
    meshes = {name: read_binary_stl(path(name)) for name in required}
    shell = np.concatenate((meshes["Joystick_1"], meshes["Joystick_2"]))
    shell_points = unique_points(shell)
    cap_centers = {name: center(meshes[name]) for name in CAPS}
    current_distances = {
        name: nearest_distance(cap_centers[name], shell_points) for name in CAPS
    }

    candidates = []
    for additional_y in np.arange(0.0, 12.01, 0.25):
        delta = np.asarray((0.0, additional_y, ADDITIONAL_Z))
        distances = {
            name: nearest_distance(cap_centers[name] + delta, shell_points) for name in CAPS
        }
        residual = np.asarray([
            distances[name] - current_distances[name] for name in CAPS
        ])
        # Preserve current cap-to-shell radial relation across all eight caps;
        # worst-cap error is weighted to prevent one side floating away.
        score = float(np.sqrt(np.mean(residual ** 2)) + 0.55 * np.max(np.abs(residual)))
        candidates.append({
            "additionalYmm": float(additional_y),
            "additionalZmm": ADDITIONAL_Z,
            "score": score,
            "rmsRadialRelationErrorMm": float(np.sqrt(np.mean(residual ** 2))),
            "maxRadialRelationErrorMm": float(np.max(np.abs(residual))),
            "centerToShellVertexMm": distances,
        })
    candidates.sort(key=lambda row: row["score"])
    best = candidates[0]
    additional = np.asarray((0.0, best["additionalYmm"], ADDITIONAL_Z))
    total = CURRENT_FROM_ORIGINAL + additional

    moved_backplate = meshes["Backplate"] + additional
    backplate_gap = sampled_mesh_distance(moved_backplate, shell_points)
    result = {
        "mode": "OFFLINE_HOUSING_FIRST_NO_CAD_WRITE",
        "source": "current Main Stage-D 30-part STL ZIP",
        "instruction": "additional 15 mm drop; ignore INDEX/MIDDLE internal parts for this stage",
        "currentTranslationFromOriginalMm": CURRENT_FROM_ORIGINAL.tolist(),
        "requestedAdditionalTranslationMm": [0.0, None, ADDITIONAL_Z],
        "recommendedAdditionalTranslationMm": additional.tolist(),
        "recommendedTotalTranslationFromOriginalMm": total.tolist(),
        "method": "preserve current eight-cap center-to-shell vertex relation while sweeping additional Y in 0.25 mm steps",
        "bestCandidate": best,
        "nextCandidates": candidates[1:6],
        "currentCapCenterToShellVertexMm": current_distances,
        "movedBackplateSampledShellGapMm": backplate_gap,
        "housingGate": {
            "rigidClusterRelativeGeometry": "PRESERVED",
            "additionalZmm": ADDITIONAL_Z,
            "oldOpeningsMustHeal": True,
            "newOpeningsMustFollowSameTransform": True,
            "shellHalvesRemainOriginalBodies": True,
            "newOrphanSolidAllowed": False,
            "indexMiddleInternalCollisionGate": "DEFERRED BY USER",
            "screwWiringHardwareGate": "DEFERRED BY USER",
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    render_seed(meshes, additional)
    print(json.dumps({
        "recommendedAdditionalMm": additional.tolist(),
        "recommendedTotalMm": total.tolist(),
        "score": best["score"],
        "backplateSampledShellGapMm": backplate_gap,
        "json": str(OUT_JSON),
        "render": str(OUT_RENDER),
    }, indent=2))


if __name__ == "__main__":
    main()
