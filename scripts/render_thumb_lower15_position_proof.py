"""Render an unambiguous Stage-D -> additional lower-15 position proof.

This image proves the exact rigid-body displacement only.  The shell is a dark
spatial reference; final relocated shell openings must be read from the saved
Onshape version THUMB_LOWER15_HOUSING_V1.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import render_thumb_reseat_overlay as base


ROOT = Path(__file__).resolve().parent.parent
STAGE_D = np.asarray((0.0, 5.5, -6.0), dtype=float)
LOWER15_TOTAL = np.asarray((0.0, 12.25, -21.0), dtype=float)
ADDITIONAL = LOWER15_TOTAL - STAGE_D


def main() -> None:
    tr = base.camera_transform()
    shells = [base.load("INDEX_FINAL_JfD"), base.load("INDEX_FINAL_JaD")]
    backplate = base.load("Backplate")
    caps = [base.load(name) for name in base.CAP_NAMES]

    old_backplate = backplate + STAGE_D
    new_backplate = backplate + LOWER15_TOTAL
    old_caps = [mesh + STAGE_D for mesh in caps]
    new_caps = [mesh + LOWER15_TOTAL for mesh in caps]

    # Dark spatial reference only.  Do not interpret the cached openings as the
    # final opening B-rep; Onshape is the source of truth for those faces.
    scene = [
        (shells[0], (39, 61, 78)),
        (shells[1], (45, 70, 88)),
    ]
    image = base.rasterize(scene, tr)
    new_solids = [(new_backplate, (205, 133, 40))]
    new_solids += [(mesh, (245, 126, 35)) for mesh in new_caps]
    image = Image.alpha_composite(image, base.rasterize(new_solids, tr, transparent=True))

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Stage-D is the magenta dashed ghost; the new total position is solid.
    base.dashed_polygon(
        draw,
        base.convex_hull(base.project(old_backplate.reshape(-1, 3), tr)),
        (236, 83, 176, 245),
        5,
        13,
    )
    for mesh in old_caps:
        base.dashed_polygon(
            draw,
            base.convex_hull(base.project(mesh.reshape(-1, 3), tr)),
            (247, 125, 205, 240),
            4,
            10,
        )

    old_center = old_backplate.reshape(-1, 3).mean(axis=0)
    new_center = new_backplate.reshape(-1, 3).mean(axis=0)
    old_p, new_p = base.project(np.asarray((old_center, new_center)), tr)
    draw.line((tuple(old_p), tuple(new_p)), fill=(255, 219, 92, 255), width=7)
    draw.ellipse((old_p[0]-8, old_p[1]-8, old_p[0]+8, old_p[1]+8), fill=(236, 83, 176, 255))
    draw.ellipse((new_p[0]-9, new_p[1]-9, new_p[0]+9, new_p[1]+9), fill=(245, 126, 35, 255))

    mid = (old_p + new_p) * 0.5
    draw.rounded_rectangle(
        (mid[0]-145, mid[1]-40, mid[0]+190, mid[1]+54),
        radius=12,
        fill=(9, 14, 21, 225),
        outline=(255, 219, 92, 255),
        width=3,
    )
    draw.text((mid[0]-126, mid[1]-29), "ADDITIONAL MOVE", font=base.font(20, True), fill=(255, 233, 139, 255))
    draw.text((mid[0]-126, mid[1]+2), "Y +6.75 / Z -15.00 mm", font=base.font(21, True), fill=(255, 255, 255, 255))

    draw.text((46, 32), "THUMB CLUSTER / ADDITIONAL 15 mm LOWER", font=base.font(39, True), fill=(243, 247, 250, 255))
    draw.text(
        (48, 82),
        "MAGENTA = PREVIOUS STAGE-D   /   ORANGE = THUMB_LOWER15_HOUSING_V1 TARGET",
        font=base.font(20),
        fill=(186, 203, 215, 255),
    )
    draw.rounded_rectangle((46, base.HEIGHT-125, 1110, base.HEIGHT-43), radius=14, fill=(9, 14, 21, 225), outline=(84, 105, 120, 230), width=2)
    draw.text((70, base.HEIGHT-107), "POSITION PROOF ONLY", font=base.font(18, True), fill=(255, 202, 83, 255))
    draw.text((70, base.HEIGHT-77), "Final relocated opening B-rep source: Onshape THUMB_LOWER15_HOUSING_V1", font=base.font(17), fill=(180, 198, 210, 255))

    image = Image.alpha_composite(image, overlay)
    out = ROOT / "renders" / "thumb_lower15_position_proof.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(out, quality=96)
    print(f"wrote {out} {image.size} additional={ADDITIONAL.tolist()}")


if __name__ == "__main__":
    main()
