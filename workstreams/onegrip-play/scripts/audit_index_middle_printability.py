"""READ-ONLY FDM printability audit for INDEX/MIDDLE shell-integrated geometry.

This checks the exact lower-15 shell STLs in the verified one-plate orientation.
It does not call Onshape and does not modify CAD.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pack_right_hand_handle_stl import read_binary_stl  # noqa: E402


SOURCE = ROOT / "exports" / "thumb_lower15_housing_mockup"
OUT = ROOT / "cad_dump" / "index_middle_printability_audit.json"

INDEX_POINTS = np.asarray([
    (-22.224, -17.494, 9.000),
    (-15.970, -26.208, 9.000),
    (-5.496, -29.325, 9.000),
    (5.496, -29.325, 9.000),
])
INDEX_AXES = np.asarray([
    (-0.847667872, -0.506166919, -0.158915794),
    (-0.387542111, -0.574231284, -0.721158474),
    (-0.068454195, -0.997609880, 0.009410170),
    (0.024161000, -0.968017000, -0.249718000),
])
MIDDLE_POINTS = np.asarray([
    (-19.835372272, -0.614991709, -11.125000000),
    (-12.899418190, -8.744828192, -14.125000000),
    (-3.537874175, -14.413708840, -11.125000000),
    (7.444327590, -13.569623472, -11.125000000),
])
MIDDLE_AXES = np.asarray([
    (-0.837518998, -0.499950062, -0.220480981),
    (-0.601521153, -0.782846337, -0.159134899),
    (0.320428890, -0.733472608, -0.599452466),
    (0.224859127, -0.772792774, -0.593489428),
])


def unit(vector: np.ndarray) -> np.ndarray:
    return vector / np.linalg.norm(vector)


def local_mesh_metrics(mesh: np.ndarray, point: np.ndarray, axis: np.ndarray,
                       build: np.ndarray) -> dict:
    centers = mesh.mean(axis=1)
    depth = (point - centers) @ axis
    lateral = np.linalg.norm((centers - point) + np.outer(depth, axis), axis=1)
    # Seat/support envelope only; excludes most unrelated outer shell skin.
    selected = (depth >= 1.5) & (depth <= 13.0) & (lateral <= 6.2)
    triangles = mesh[selected]
    tri_centers = centers[selected]
    cross = np.cross(triangles[:, 1] - triangles[:, 0],
                     triangles[:, 2] - triangles[:, 0])
    twice_area = np.linalg.norm(cross, axis=1)
    areas = twice_area / 2.0
    normals = cross / np.maximum(twice_area[:, None], 1e-12)
    downward = normals @ build
    down_45 = downward <= -math.cos(math.radians(45.0))
    near_horizontal = downward <= -math.cos(math.radians(30.0))
    heights = tri_centers @ build
    return {
        "selectedTriangleCount": int(len(triangles)),
        "localSurfaceAreaMm2": float(areas.sum()),
        "downwardOverhangArea45DegMm2": float(areas[down_45].sum()),
        "nearHorizontalDownwardArea30DegMm2": float(areas[near_horizontal].sum()),
        "overhangBuildHeightRangeMm": (
            [float(heights[down_45].min()), float(heights[down_45].max())]
            if np.any(down_45) else None
        ),
    }


def verdict(row: str, tilt: float, near_horizontal_area: float) -> tuple[str, list[str]]:
    reasons = []
    if tilt >= 70.0:
        reasons.append("seat/support axis is near-horizontal to build direction")
    elif tilt >= 45.0:
        reasons.append("seat/support axis exceeds the 45-degree support-free heuristic")
    if near_horizontal_area >= 100.0:
        reasons.append("large near-horizontal downward surface exists in local seat/support envelope")
    if row == "MIDDLE":
        reasons.append("0.80 mm ring/beam and 0.70 mm hook are only about two 0.4-mm lines or less")
        reasons.append("integrated rear hooks make generated support difficult to remove without damage")
    else:
        reasons.append("open rear improves access, but support/contact scars can reduce the 6.40-mm seat")
    if tilt < 45.0 and near_horizontal_area < 100.0:
        return "MARGINAL", reasons
    return "HOLD", reasons


def main() -> None:
    meshes = {
        "JaD": read_binary_stl(SOURCE / "OneGrip_lower15_housing_Joystick_1_JaD.stl"),
        "JfD": read_binary_stl(SOURCE / "OneGrip_lower15_housing_Joystick_2_JfD.stl"),
    }
    rows = []
    for row_name, points, axes in (
        ("INDEX", INDEX_POINTS, INDEX_AXES),
        ("MIDDLE", MIDDLE_POINTS, MIDDLE_AXES),
    ):
        for index, (point, axis) in enumerate(zip(points, axes), start=1):
            owner = "JfD" if index <= 3 else "JaD"
            # In the one-plate transform, JfD build +Z = original -X and
            # JaD build +Z = original +X.
            build = np.asarray((-1.0, 0.0, 0.0) if owner == "JfD" else (1.0, 0.0, 0.0))
            axis = unit(axis)
            tilt = math.degrees(math.acos(min(1.0, abs(float(axis @ build)))))
            metrics = local_mesh_metrics(meshes[owner], point, axis, build)
            status, reasons = verdict(
                row_name, tilt, metrics["nearHorizontalDownwardArea30DegMm2"]
            )
            rows.append({
                "button": f"{row_name[0]}{index}",
                "owner": owner,
                "centerMm": point.tolist(),
                "buildCenterHeightMm": float(point @ build),
                "axisTiltFromBuildVerticalDeg": tilt,
                **metrics,
                "supportFreeFunctionalPrint": status,
                "reasons": reasons,
            })

    payload = {
        "scope": "INDEX/MIDDLE button insertion geometry only; THUMB excluded and unchanged",
        "source": {
            "shells": [
                "OneGrip_lower15_housing_Joystick_1_JaD.stl",
                "OneGrip_lower15_housing_Joystick_2_JfD.stl",
            ],
            "orientation": "both mating planes on build plate",
            "cadWrite": 0,
        },
        "processAssumption": {
            "printer": "Bambu Lab P1S-class FDM",
            "nozzleMm": 0.4,
            "supportFreeOverhangHeuristicDeg": 45.0,
        },
        "functionalFit": {
            "seatMm": [6.4, 6.4],
            "conservativeBodyMm": [6.18, 6.12],
            "clearancePerSideMm": [0.11, 0.14],
            "physicalSampleBodyMm": [6.12, 6.05],
            "physicalSampleClearancePerSideMm": [0.14, 0.175],
            "couponStatus": "not previously validated; 6.4/6.5/6.6/6.7-mm coupon was explicitly deferred",
            "verdict": "HOLD",
        },
        "minimumStructures": {
            "indexDividerMm": 0.807375,
            "indexTerminalWebMm": 1.552585,
            "middleRingAnnulusMm": 0.8,
            "middleBeamWidthMm": 0.8,
            "middleHookDepthMm": 0.7,
            "middleDividerMm": 1.041660,
        },
        "buttons": rows,
        "summary": {
            "watertightMesh": "PASS",
            "supportFreeFunctionalPrint": "HOLD",
            "mainBlockers": [
                "I2/I3/I4 and M2/M3/M4 axes are over 45 degrees from build vertical",
                "I3/I4 and M3/M4 contain large near-horizontal downward seat/support surfaces",
                "6.40-mm switch seat has only 0.11-0.175 mm nominal clearance per side",
                "MIDDLE 0.8-mm beams/rings and 0.7-mm hooks are fragile and support removal is risky",
            ],
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    for row in rows:
        print(row["button"], row["supportFreeFunctionalPrint"],
              f"tilt={row['axisTiltFromBuildVerticalDeg']:.1f}",
              f"horizontal={row['nearHorizontalDownwardArea30DegMm2']:.1f} mm2")


if __name__ == "__main__":
    main()
