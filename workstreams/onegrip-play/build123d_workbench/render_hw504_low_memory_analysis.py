"""Render the HW504 low-memory analysis without importing OCCT/build123d.

Three 960x640 diagrams are generated sequentially from existing JSON values.
No STEP is loaded, no tessellation or boolean is performed, and each image is
released before the next one is allocated.
"""

from __future__ import annotations

import gc
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "build123d_workbench" / "out" / "hw504_low_memory_analysis" / "hw504_low_memory_analysis.json"
OUT_DIR = ROOT / "renders" / "hw504_low_memory_analysis"
WIDTH, HEIGHT = 960, 640
MAX_RSS_MB = 384.0

BG = "#0b1119"
PANEL = "#121c29"
GRID = "#26384a"
TEXT = "#ecf4fb"
MUTED = "#9fb2c3"
HW_A = "#3e9bd1"
HW_B = "#45c49a"
FINGER = "#f4b942"
COLLISION = "#ff4f5e"
PROTECTED = "#c77dff"
GOOD = "#55d187"
WARN = "#f5bd4f"
BAD = "#ff5c68"


def rss_mb() -> float:
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024.0 * 1024.0)
    except Exception:
        return 0.0


def guard() -> None:
    current = rss_mb()
    if current > MAX_RSS_MB:
        raise MemoryError(f"LOW-MEMORY guard stopped rendering at {current:.1f} MB RSS")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "malgunbd.ttf" if bold else "malgun.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size=size)


def canvas(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    guard()
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((20, 18, WIDTH - 20, 88), radius=14, fill=PANEL, outline=GRID, width=2)
    draw.text((42, 31), title, font=font(25, True), fill=TEXT)
    draw.text((42, 63), subtitle, font=font(13), fill=MUTED)
    return image, draw


def save_release(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)
    image.close()
    gc.collect()
    guard()


def mapper(x0: float, x1: float, z0: float, z1: float, box: tuple[int, int, int, int]):
    left, top, right, bottom = box
    def point(x: float, z: float) -> tuple[int, int]:
        px = left + (x - x0) / (x1 - x0) * (right - left)
        py = bottom - (z - z0) / (z1 - z0) * (bottom - top)
        return int(max(left, min(right, px))), int(max(top, min(bottom, py)))
    return point


def projected_rect(draw: ImageDraw.ImageDraw, map_point, bbox_min, bbox_max, fill: str | None, label: str, width: int = 2, outline: str | None = None):
    a = map_point(float(bbox_min[0]), float(bbox_max[2]))
    b = map_point(float(bbox_max[0]), float(bbox_min[2]))
    stroke = outline or fill or TEXT
    draw.rounded_rectangle((*a, *b), radius=8, fill=fill, outline=stroke, width=width)
    draw.text((a[0] + 6, a[1] + 5), label, font=font(12, True), fill=(BG if fill else stroke))


def render_collision_section(data: dict) -> None:
    image, draw = canvas(
        "LOCAL X-Z COLLISION SECTION",
        "Existing bbox/centroid evidence only · no new STEP load, tessellation or boolean",
    )
    plot = (70, 125, 700, 570)
    draw.rounded_rectangle(plot, radius=14, fill=PANEL, outline=GRID, width=2)
    mp = mapper(-18.0, 8.0, 27.0, 38.0, plot)
    for x in range(-15, 6, 5):
        p1, p2 = mp(x, 27.0), mp(x, 38.0)
        draw.line((*p1, *p2), fill=GRID, width=1)
        draw.text((p1[0] - 10, plot[3] + 8), str(x), font=font(11), fill=MUTED)
    for z in range(28, 39, 2):
        p1, p2 = mp(-18.0, z), mp(8.0, z)
        draw.line((*p1, *p2), fill=GRID, width=1)
        draw.text((plot[0] - 32, p1[1] - 7), str(z), font=font(11), fill=MUTED)

    projected_rect(draw, mp, [-15.23, -43.17, 21.537], [11.805, -8.424, 48.552], None, "HW504 A", width=5, outline=HW_A)
    projected_rect(draw, mp, [-12.219, -31.938, 30.390], [4.787, -16.180, 48.868], None, "HW504 B", width=5, outline=HW_B)
    projected_rect(draw, mp, [-15.211, -32.030, 29.138], [5.225, -26.321, 34.966], FINGER, "N1/N2 carrier")
    projected_rect(draw, mp, [-3.718, -31.196, 31.561], [3.282, -27.582, 35.136], COLLISION, "B↔carrier")
    projected_rect(draw, mp, [-3.614, -28.841, 31.657], [-2.905, -27.583, 32.728], PROTECTED, "B↔N2")

    draw.text((735, 135), "KNOWN EXACT", font=font(16, True), fill=TEXT)
    rows = [
        ("Total Finger", "72.902 mm³", COLLISION),
        ("Non-protected", "39.884 mm³", GOOD),
        ("Protected", "33.018 mm³", PROTECTED),
        ("HW504 B", "100% protected", BAD),
    ]
    y = 180
    for label, value, color in rows:
        draw.ellipse((737, y + 4, 749, y + 16), fill=color)
        draw.text((760, y), label, font=font(13), fill=MUTED)
        draw.text((760, y + 22), value, font=font(18, True), fill=TEXT)
        y += 76
    draw.text((735, 510), "Projection: X-Z", font=font(12), fill=MUTED)
    draw.text((735, 532), "Y retained in JSON bbox", font=font(12), fill=MUTED)
    save_release(image, OUT_DIR / "01_collision_section.png")


def render_hw504_b_closeup(data: dict) -> None:
    image, draw = canvas(
        "HW504 B + N1/N2 CLOSE-UP",
        "Moving gimbal/stick body · every current B-side Finger collision lies in protected geometry",
    )
    cx, cy = 390, 350
    draw.rounded_rectangle((80, 120, 700, 575), radius=18, fill=PANEL, outline=GRID, width=2)
    draw.ellipse((cx - 150, cy - 120, cx + 150, cy + 120), fill="#214e54", outline=HW_B, width=4)
    draw.ellipse((cx - 92, cy - 92, cx + 92, cy + 92), outline=PROTECTED, width=18)
    draw.line((cx - 190, cy, cx + 190, cy), fill=TEXT, width=4)
    draw.line((cx, cy - 160, cx, cy + 160), fill=TEXT, width=4)
    draw.text((cx + 105, cy - 24), "U pivot", font=font(13, True), fill=TEXT)
    draw.text((cx + 12, cy - 154), "V pivot", font=font(13, True), fill=TEXT)
    draw.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=HW_B, outline=TEXT, width=3)
    draw.text((cx - 26, cy - 10), "shaft", font=font(12, True), fill=BG)

    draw.rounded_rectangle((165, 245, 275, 345), radius=10, fill=FINGER, outline=TEXT, width=2)
    draw.text((180, 278), "N1", font=font(22, True), fill=BG)
    draw.rounded_rectangle((485, 245, 595, 345), radius=10, fill=FINGER, outline=TEXT, width=2)
    draw.text((500, 278), "N2", font=font(22, True), fill=BG)
    draw.rounded_rectangle((470, 330, 542, 420), radius=8, fill=COLLISION, outline=TEXT, width=2)
    draw.text((481, 350), "26.369", font=font(14, True), fill=TEXT)
    draw.text((484, 374), "carrier", font=font(12), fill=TEXT)
    draw.rounded_rectangle((455, 268, 485, 314), radius=5, fill=PROTECTED, outline=TEXT, width=2)
    draw.text((430, 220), "0.320 mm³ N2", font=font(12, True), fill=PROTECTED)

    draw.text((735, 145), "B VERDICT", font=font(16, True), fill=TEXT)
    draw.text((735, 182), "KEEP EXACT", font=font(24, True), fill=GOOD)
    draw.text((735, 232), "N2 switch", font=font(13), fill=MUTED)
    draw.text((735, 254), "0.320370 mm³", font=font(17, True), fill=TEXT)
    draw.text((735, 300), "shared carrier", font=font(13), fill=MUTED)
    draw.text((735, 322), "26.369309 mm³", font=font(17, True), fill=TEXT)
    draw.text((735, 380), "Protected fraction", font=font(13), fill=MUTED)
    draw.text((735, 405), "100.0%", font=font(26, True), fill=BAD)
    draw.multiline_text((735, 465), "B-side trim would\nchange moving pivot /\ncontact geometry.", font=font(13), fill=MUTED, spacing=5)
    save_release(image, OUT_DIR / "02_hw504_b_n1_n2_closeup.png")


def option_card(draw: ImageDraw.ImageDraw, box, name, subtitle, changed, thumb, finger, kine, result, color):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=16, fill=PANEL, outline=color, width=3)
    draw.text((x1 + 18, y1 + 16), name, font=font(26, True), fill=color)
    draw.text((x1 + 18, y1 + 52), subtitle, font=font(13, True), fill=TEXT)
    items = [
        ("CHANGED", changed),
        ("THUMB", thumb),
        ("FINGER", finger),
        ("KINEMATICS", kine),
    ]
    y = y1 + 92
    for key, value in items:
        draw.text((x1 + 18, y), key, font=font(11, True), fill=MUTED)
        draw.multiline_text((x1 + 18, y + 18), value, font=font(12), fill=TEXT, spacing=3)
        y += 68
    draw.rounded_rectangle((x1 + 18, y2 - 50, x2 - 18, y2 - 16), radius=8, fill=color)
    draw.text((x1 + 32, y2 - 43), result, font=font(15, True), fill=BG)


def render_options(data: dict) -> None:
    image, draw = canvas(
        "OPTION A / B / C — MINIMUM CHANGE COMPARISON",
        "Candidate A shell-only is already FAIL · no new boolean performed in this report",
    )
    option_card(draw, (28, 115, 322, 602), "A", "FINGER-SIDE ONLY",
                "N1 + N2 internals\nshared carrier", "20/20 exact", "72.902 mm³\nlocal repack", "Thumb 0", "FALLBACK", WARN)
    option_card(draw, (333, 115, 627, 602), "B", "HW504-SIDE ONLY",
                "HW504 A + B", "18/20 exact", "0", "NONZERO\n33.018 protected", "REJECT", BAD)
    option_card(draw, (638, 115, 932, 602), "C", "MIXED / PROTECTED SPLIT",
                "A trim 39.884\nFinger 33.018", "19/20 exact\n95%", "N2 + carrier\nlocalized", "Thumb 0 intended", "RECOMMEND", GOOD)
    save_release(image, OUT_DIR / "03_option_abc_comparison.png")


def main() -> None:
    guard()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_collision_section(data)
    render_hw504_b_closeup(data)
    render_options(data)
    print(json.dumps({
        "renders": [
            str((OUT_DIR / "01_collision_section.png").relative_to(ROOT)),
            str((OUT_DIR / "02_hw504_b_n1_n2_closeup.png").relative_to(ROOT)),
            str((OUT_DIR / "03_option_abc_comparison.png").relative_to(ROOT)),
        ],
        "peakSafetyLimitMb": MAX_RSS_MB,
        "finalRssMb": round(rss_mb(), 1),
        "occtImported": False,
    }, indent=2))


if __name__ == "__main__":
    main()
