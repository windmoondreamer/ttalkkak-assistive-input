"""Verify the exported current cassette body and lid directly from STEP."""

from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq


HERE = Path(__file__).resolve().parent
OUT = HERE / "export"
BODY_STEP = OUT / "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_BODY_V4.step"
LID_STEP = OUT / "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_LID_V4.step"
REPORT = OUT / "body_lid_fit_report.json"

BODY_H = 12.0
LID_GAP = 0.20
BOSS_CENTERS = ((-15.0, -8.725), (15.0, -8.725), (-15.0, 12.575), (15.0, 12.575))


def load_one(path: Path) -> cq.Shape:
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise RuntimeError(f"Expected one valid STEP solid: {path}")
    return solids[0]


def volume(shape: cq.Shape) -> float:
    return float(shape.Volume())


def probe_cylinder(x: float, y: float, radius: float, z0: float, height: float) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .center(x, y)
        .circle(radius)
        .extrude(height)
        .val()
        .translate((0.0, 0.0, z0))
    )


def main() -> None:
    body = load_one(BODY_STEP)
    lid = load_one(LID_STEP)
    body_bb = body.BoundingBox()
    lid_bb = lid.BoundingBox()

    lid_installed = lid.translate((0.0, 0.0, body_bb.zmax + LID_GAP - lid_bb.zmin))
    assembly_overlap = volume(body.intersect(lid_installed))

    screw_checks = []
    for x, y in BOSS_CENTERS:
        lid_probe = probe_cylinder(x, y, 1.50, lid_bb.zmin - 0.2, lid_bb.zlen + 0.4)
        body_probe = probe_cylinder(x, y, 1.10, body_bb.zmax - 6.8, 7.0)
        lid_blockage = volume(lid.intersect(lid_probe))
        body_blockage = volume(body.intersect(body_probe))
        screw_checks.append(
            {
                "center_mm": [x, y],
                "lid_clear_hole_blockage_mm3": round(lid_blockage, 6),
                "body_pilot_hole_blockage_mm3": round(body_blockage, 6),
                "aligned": lid_blockage < 1.0e-5 and body_blockage < 1.0e-5,
            }
        )

    footprint_match = all(
        abs(value) < 1.0e-6
        for value in (
            body_bb.xmin - lid_bb.xmin,
            body_bb.xmax - lid_bb.xmax,
            body_bb.ymin - lid_bb.ymin,
            body_bb.ymax - lid_bb.ymax,
        )
    )
    result = {
        "body_step": BODY_STEP.name,
        "lid_step": LID_STEP.name,
        "body_bbox_mm": [body_bb.xlen, body_bb.ylen, body_bb.zlen],
        "lid_bbox_mm": [lid_bb.xlen, lid_bb.ylen, lid_bb.zlen],
        "outer_footprint_match": footprint_match,
        "body_lid_assembled_overlap_mm3": assembly_overlap,
        "assembly_gap_mm": LID_GAP,
        "screw_checks": screw_checks,
        "all_four_screws_aligned": all(item["aligned"] for item in screw_checks),
        "rp2040_pocket_length_mm": 24.35,
        "explanation": (
            "The RP2040 insertion pocket was lengthened internally; the cassette "
            "outer length remained 45 mm. The lid already uses the same current "
            "36 x 45 mm footprint and shared screw centers."
        ),
    }
    if not footprint_match or assembly_overlap > 1.0e-5 or not result["all_four_screws_aligned"]:
        raise RuntimeError(json.dumps(result, indent=2))
    REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
