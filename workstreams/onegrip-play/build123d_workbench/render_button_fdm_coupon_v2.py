"""Render the independent button FDM coupon V2 print map and mechanism section."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from build123d import Align, Axis, Box, import_step
from PIL import Image, ImageDraw

from .button_fdm_coupon import (
    BASE_Z_MM,
    CRADLE_OUTER_MM,
    GUIDE_ROW_Y_MM,
    SHOULDER_BOTTOM_REL_MM,
    STATION_X_MM,
    CouponConfig,
    build_coupon,
    build_cradle_station,
    build_guide_deck,
    build_cap,
    build_retention_clip,
    mechanism_levels,
    moved,
)
from .finger_layout_reset import triangles


ROOT = Path(__file__).resolve().parents[1]
RENDER_DIR = ROOT / "renders" / "button_fdm_coupon"
OPEN_SOURCE_THUMB = (
    ROOT / "build123d_workbench" / "out" / "finger_thumb_joint_feasibility"
    / "THUMB_TARGET_EXACT_MODULE.step"
)

sys.path.insert(0, str(ROOT / "scripts"))
import render_index_its_audit as render  # noqa: E402


BASE = (74, 111, 131)
DECK = (64, 187, 178)
CAP = (235, 109, 85)
CLIP = (246, 198, 74)
SWITCH = (215, 151, 54)


def mesh(shape):
    return triangles(shape)


def annotate(image: Image.Image, title: str, subtitle: str, rows: list[str]) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((24, 20, 1476, 114), radius=14, fill=(7, 12, 19, 226), outline=(81, 105, 120, 220), width=2)
    draw.text((44, 30), title, font=render.font(34, True), fill=(245, 248, 250, 255))
    draw.text((46, 76), subtitle, font=render.font(18), fill=(182, 201, 211, 255))
    y = 144
    for index, row in enumerate(rows, 1):
        draw.ellipse((34, y - 2, 64, y + 28), fill=(236, 91, 76, 242), outline=(255, 255, 255, 235), width=2)
        draw.text((44, y + 1), str(index), font=render.font(18, True), fill=(255, 255, 255, 255))
        draw.rounded_rectangle((76, y - 5, 545, y + 32), radius=8, fill=(7, 12, 19, 212))
        draw.text((90, y + 1), row, font=render.font(17, True), fill=(239, 244, 247, 255))
        y += 43


def canonical_open_source_switch():
    source = import_step(OPEN_SOURCE_THUMB)
    occurrence = next(child for child in source.children if child.label == "PushBtn")
    canonical = occurrence.moved(occurrence.location.inverse())
    # Original actuation axis is +Y.  Rotate it to coupon +Z.
    return canonical.rotate(Axis.X, 90.0)


def render_print_layout(config: CouponConfig) -> Image.Image:
    _, base, deck, caps, clips = build_coupon(config)
    objects = [
        (mesh(base), BASE),
        (mesh(deck), DECK),
        *[(mesh(shape), CAP) for shape in caps],
        *[(mesh(shape), CLIP) for shape in clips],
    ]
    image, _ = render.rasterize(objects)
    annotate(
        image,
        "BUTTON FDM COUPON V2 / SUPPLIED PRINT ORIENTATION",
        "No support: open cradles, guide-deck cavities face upward during printing",
        [
            "P ROW / 6.30–6.50 body gauges",
            "G ROW / top-load open pin cradles",
            "GUIDE DECK / print top-face-down, flip after print",
            "CAPS / pad-face-down",
            "C-CLIPS / flat retention parts",
        ],
    )
    return image


def render_mechanism_section(config: CouponConfig) -> Image.Image:
    levels = mechanism_levels(config)
    x = STATION_X_MM[2]
    y = GUIDE_ROW_Y_MM
    cradle = build_cradle_station(config, x, y)
    deck = build_guide_deck(config)
    crop = moved(
        Box(CRADLE_OUTER_MM, CRADLE_OUTER_MM, levels["deckTop"] + 0.20, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        x,
        y,
        -0.10,
    )
    deck_station = (deck & crop).clean()
    # Remove the viewer-side half only in the render to expose the clip/tail.
    viewer_cut = moved(
        Box(CRADLE_OUTER_MM + 0.40, CRADLE_OUTER_MM / 2.0 + 0.40, levels["deckTop"] + 0.40, align=(Align.CENTER, Align.MIN, Align.MIN)),
        x,
        y - CRADLE_OUTER_MM / 2.0 - 0.20,
        -0.20,
    )
    deck_section = (deck_station - viewer_cut).clean()

    switch = moved(canonical_open_source_switch(), x=x, y=y, z=levels["switchRear"])
    cap = moved(build_cap(config), x=x, y=y, z=levels["actuatorTop"])
    clip = moved(
        build_retention_clip(),
        x=x,
        y=y,
        z=levels["actuatorTop"] + SHOULDER_BOTTOM_REL_MM,
    )

    # Recenter the local mechanism for the fixed software camera.
    objects = []
    for shape, color in ((cradle, BASE), (switch, SWITCH), (deck_section, DECK), (cap, CAP), (clip, CLIP)):
        objects.append((mesh(moved(shape, x=-x, y=-y, z=-BASE_Z_MM)), color))
    image, _ = render.rasterize(objects)
    annotate(
        image,
        "G4.80 ASSEMBLED SECTION / EXACT OPEN-SOURCE PUSHBTN OVERLAY",
        "Front half of guide deck hidden in this render only; output CAD remains complete",
        [
            "EXACT SWITCH / four Ø1.00 front posts included",
            "UNCUT FORMED PINS / open below and on four sides",
            "CENTRAL REAR SUPPORT / 4.00 mm pedestal",
            "FULL ROUND GUIDE / Ø4.80 shown",
            "C-CLIP / captured inside 6.80 cavity",
            "0.350 STOP / clip floor + cap-pad face",
        ],
    )
    return image


def main() -> None:
    config = CouponConfig()
    left = render_print_layout(config).convert("RGB")
    right = render_mechanism_section(config).convert("RGB")
    combined = Image.new("RGB", (left.width + right.width, left.height), (12, 18, 27))
    combined.paste(left, (0, 0))
    combined.paste(right, (left.width, 0))
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    path = RENDER_DIR / "BUTTON_FDM_TEST_COUPON_V2_MAP.png"
    combined.save(path, quality=96)
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
