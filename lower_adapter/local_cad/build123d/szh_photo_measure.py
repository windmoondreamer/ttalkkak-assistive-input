"""
SZH-EK056 / KY-023 photo measurement helper.

READ-ONLY with respect to OneGrip production geometry.
This script only loads reference photographs and produces annotated
crops + a homography solver so that pixel picks can be converted to
millimetres on the PCB plane.

Usage:
  python szh_photo_measure.py grid   <img> <out> [step] [scale]
  python szh_photo_measure.py crop   <img> <out> x0 y0 x1 y1 [zoom] [step]
  python szh_photo_measure.py analyze <reference-photo-dir> <measure-out-dir>
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw

# ------------------------------------------------------------------ grid


def _draw_grid(im: Image.Image, step: int, off_x: float = 0.0,
               off_y: float = 0.0, zoom: float = 1.0) -> Image.Image:
    """Overlay a labelled pixel grid.  Labels are in ORIGINAL image pixels."""
    im = im.convert("RGB")
    d = ImageDraw.Draw(im)
    w, h = im.size

    # minor + major lines
    x = 0
    while x < w:
        orig = off_x + x / zoom
        major = (round(orig) % (step * 5)) < (1.0 / zoom)
        col = (255, 60, 60) if major else (0, 200, 255)
        d.line([(x, 0), (x, h)], fill=col, width=1)
        if major:
            d.text((x + 2, 2), f"{orig:.0f}", fill=(255, 255, 0))
        x += int(round(step * zoom))

    y = 0
    while y < h:
        orig = off_y + y / zoom
        major = (round(orig) % (step * 5)) < (1.0 / zoom)
        col = (255, 60, 60) if major else (0, 200, 255)
        d.line([(0, y), (w, y)], fill=col, width=1)
        if major:
            d.text((2, y + 2), f"{orig:.0f}", fill=(255, 255, 0))
        y += int(round(step * zoom))
    return im


def cmd_grid(argv):
    src, out = argv[0], argv[1]
    step = int(argv[2]) if len(argv) > 2 else 25
    scale = float(argv[3]) if len(argv) > 3 else 1.0
    im = Image.open(src)
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)),
                       Image.LANCZOS)
    _draw_grid(im, step, 0.0, 0.0, scale).save(out)
    print(f"{out}  {im.size}  step={step}px  scale={scale}")


def cmd_crop(argv):
    src, out = argv[0], argv[1]
    x0, y0, x1, y1 = (int(v) for v in argv[2:6])
    zoom = float(argv[6]) if len(argv) > 6 else 3.0
    step = int(argv[7]) if len(argv) > 7 else 10
    im = Image.open(src).crop((x0, y0, x1, y1))
    im = im.resize((int(im.width * zoom), int(im.height * zoom)),
                   Image.LANCZOS)
    # brighten: these boards are near-black on near-black
    if len(argv) <= 8 or argv[8] != "raw":
        im = _autolevel(im)
    _draw_grid(im, step, x0, y0, zoom).save(out)
    print(f"{out}  crop=({x0},{y0})-({x1},{y1})  zoom={zoom}  step={step}px")


def _autolevel(im: Image.Image) -> Image.Image:
    import numpy as np
    a = np.asarray(im.convert("RGB")).astype(float)
    lo, hi = np.percentile(a, 1.0), np.percentile(a, 99.0)
    if hi - lo < 1e-6:
        return im
    a = (a - lo) / (hi - lo) * 255.0
    return Image.fromarray(a.clip(0, 255).astype("uint8"))


# ------------------------------------------------------- homography (mm)


def homography(src_pts, dst_pts):
    """Solve H so that H @ [x,y,1] ~ [X,Y,1].  4+ correspondences."""
    import numpy as np
    A = []
    for (x, y), (X, Y) in zip(src_pts, dst_pts):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y, -X])
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y, -Y])
    A = np.asarray(A, float)
    _, _, vt = np.linalg.svd(A)
    H = vt[-1].reshape(3, 3)
    return H / H[2, 2]


def apply_h(H, pts):
    import numpy as np
    p = np.asarray(pts, float)
    p = np.hstack([p, np.ones((len(p), 1))])
    q = (H @ p.T).T
    return q[:, :2] / q[:, 2:3]


# ------------------------------------------------ fixed recovered photo study

# These picks continue the interrupted Claude photo study.  They are deliberately
# explicit and editable: no claimed sub-pixel metrology is hidden in an image
# processing pipeline.  Coordinates refer to the untouched 800x600 ProtoSupplies
# photographs stored beside this script's input directory.
PCB_X_MM = 34.5
PCB_Y_MM = 26.0

TOP_PICKS_PX = {
    "pcb_corners": [(302.0, 127.0), (752.0, 128.0), (751.0, 480.0), (302.0, 476.0)],
    "mount_holes": [(370.5, 167.0), (716.5, 170.5), (368.0, 428.5), (714.5, 432.0)],
    "joystick_center": [(531.0, 276.0)],
    "gimbal_envelope": [(415.0, 164.0), (646.0, 389.0)],
    "x_pot_envelope": [(638.0, 190.0), (704.0, 365.0)],
    "y_pot_envelope": [(464.0, 127.0), (600.0, 192.0)],
    "push_switch_envelope": [(464.0, 380.0), (600.0, 474.0)],
    "header_pin_envelope": [(227.0, 227.0), (352.0, 384.0)],
}

BOTTOM_PICKS_PX = {
    "pcb_corners": [(207.0, 140.0), (623.0, 140.0), (621.0, 462.0), (207.0, 461.0)],
    "mount_holes": [(269.5, 186.0), (588.5, 186.0), (269.0, 427.0), (588.0, 427.0)],
}


def _pcb_h(corners):
    return homography(
        corners,
        [
            (-PCB_X_MM / 2.0, PCB_Y_MM / 2.0),
            (PCB_X_MM / 2.0, PCB_Y_MM / 2.0),
            (PCB_X_MM / 2.0, -PCB_Y_MM / 2.0),
            (-PCB_X_MM / 2.0, -PCB_Y_MM / 2.0),
        ],
    )


def _rectified(im: Image.Image, H, px_per_mm: int = 24) -> Image.Image:
    """Warp a PCB-plane photograph to a metric, top-datum image."""
    import numpy as np

    width = int(round(PCB_X_MM * px_per_mm))
    height = int(round(PCB_Y_MM * px_per_mm))
    # PIL wants an output-pixel -> input-pixel perspective map.
    mm_from_out = np.asarray(
        [[1.0 / px_per_mm, 0.0, -PCB_X_MM / 2.0],
         [0.0, -1.0 / px_per_mm, PCB_Y_MM / 2.0],
         [0.0, 0.0, 1.0]],
        dtype=float,
    )
    source_from_mm = np.linalg.inv(H)
    source_from_out = source_from_mm @ mm_from_out
    source_from_out /= source_from_out[2, 2]
    a, b, c = source_from_out[0]
    d, e, f = source_from_out[1]
    g, h, _ = source_from_out[2]
    return im.transform(
        (width, height),
        Image.Transform.PERSPECTIVE,
        (a, b, c, d, e, f, g, h),
        Image.Resampling.BICUBIC,
    )


def _annotate(im: Image.Image, picks: dict, H) -> Image.Image:
    out = im.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    colors = {
        "pcb_corners": (255, 210, 60),
        "mount_holes": (70, 230, 255),
        "joystick_center": (255, 80, 80),
        "gimbal_envelope": (95, 240, 135),
        "x_pot_envelope": (215, 105, 255),
        "y_pot_envelope": (255, 150, 70),
        "push_switch_envelope": (255, 90, 170),
        "header_pin_envelope": (255, 245, 120),
    }
    for name, points in picks.items():
        mapped = apply_h(H, points)
        color = colors.get(name, (255, 255, 255))
        for index, ((x, y), (mx, my)) in enumerate(zip(points, mapped)):
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), outline=color, width=2)
            draw.text((x + 7, y - 15), f"{name}[{index}] {mx:.2f},{my:.2f}", fill=color)
    return out


def _mapped_rows(picks: dict, H) -> dict:
    return {
        name: [[round(float(x), 4), round(float(y), 4)] for x, y in apply_h(H, points)]
        for name, points in picks.items()
    }


def cmd_analyze(argv):
    reference_dir = Path(argv[0])
    out_dir = Path(argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    top_path = reference_dir / "ps_Joystick-Module-Connections-1.jpg"
    bottom_path = reference_dir / "ps_Joystick-Module-Back.jpg"
    top_im = Image.open(top_path)
    bottom_im = Image.open(bottom_path)
    top_h = _pcb_h(TOP_PICKS_PX["pcb_corners"])
    bottom_h = _pcb_h(BOTTOM_PICKS_PX["pcb_corners"])
    top_mm = _mapped_rows(TOP_PICKS_PX, top_h)
    bottom_mm = _mapped_rows(BOTTOM_PICKS_PX, bottom_h)

    top_holes = top_mm["mount_holes"]
    bottom_holes = bottom_mm["mount_holes"]

    def pitch(holes):
        x_pitch = ((holes[1][0] - holes[0][0]) + (holes[3][0] - holes[2][0])) / 2.0
        y_pitch = ((holes[0][1] - holes[2][1]) + (holes[1][1] - holes[3][1])) / 2.0
        return [round(x_pitch, 4), round(y_pitch, 4)]

    record = {
        "model": "SZH_EK056_WEB_REFERENCE photo-plane study",
        "classification": "PHOTO-DERIVED; visually matching KY-023, not exact-SKU metrology",
        "datum": "PCB centre; +X right and +Y image-up in rectified top view",
        "calibration": {
            "pcb_mm": [PCB_X_MM, PCB_Y_MM],
            "source": "SZH-EK056 reseller 34.5x26 plan dimension; height excluded from homography",
            "accuracy_note": "manual perspective picks; report dimensions to practical 0.5 mm class only",
        },
        "top_photo": {"file": top_path.name, "picks_px": TOP_PICKS_PX, "mapped_mm": top_mm, "hole_pitch_mm": pitch(top_holes)},
        "bottom_photo": {"file": bottom_path.name, "picks_px": BOTTOM_PICKS_PX, "mapped_mm": bottom_mm, "hole_pitch_mm": pitch(bottom_holes)},
        "adopted": {
            "mount_hole_centres_mm": [[-12.0, 9.95], [14.5, 9.95], [-12.0, -9.5], [14.5, -9.5]],
            "mount_hole_pitch_mm": [26.5, 19.45],
            "joystick_center_mm": [0.4, 2.0],
            "gimbal_envelope_xy_mm": [17.5, 16.6],
            "x_pot_center_xy_mm": [11.1, 2.0],
            "x_pot_envelope_xy_mm": [5.2, 13.2],
            "y_pot_center_xy_mm": [0.5, 10.6],
            "y_pot_envelope_xy_mm": [10.5, 5.0],
            "push_switch_center_xy_mm": [0.5, -9.2],
            "push_switch_envelope_xy_mm": [10.5, 7.0],
            "header_pin_envelope_xy_mm": [8.8, 12.2],
        },
    }
    (out_dir / "szh_photo_measurements.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    _annotate(top_im, TOP_PICKS_PX, top_h).save(out_dir / "top_annotated.png")
    _annotate(bottom_im, BOTTOM_PICKS_PX, bottom_h).save(out_dir / "bottom_annotated.png")
    _rectified(top_im, top_h).save(out_dir / "top_rectified_34p5x26.png")
    _rectified(bottom_im, bottom_h).save(out_dir / "bottom_rectified_34p5x26.png")
    print(json.dumps(record["adopted"], indent=2))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"grid": cmd_grid, "crop": cmd_crop, "analyze": cmd_analyze}[cmd](sys.argv[2:])
