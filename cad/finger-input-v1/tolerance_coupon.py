"""Create a small PETG tolerance coupon before printing a full cartridge."""

from pathlib import Path
import cadquery as cq

from finger_module_common import ROOT, export_bundle


def build_coupon() -> cq.Workplane:
    coupon = cq.Workplane("XY").box(86, 34, 4, centered=(True, True, False))
    # Four nominal 2 mm shaft holes: 2.20 / 2.25 / 2.30 / 2.35 mm.
    for x, diameter in zip((-30, -20, -10, 0), (2.20, 2.25, 2.30, 2.35)):
        cutter = cq.Workplane("XY").center(x, -7).circle(diameter / 2).extrude(4.4).translate((0, 0, -0.2))
        coupon = coupon.cut(cutter)
    # Moving-fit forks: total gaps 0.30 / 0.40 / 0.50 / 0.60 mm.
    for x, gap in zip((-30, -12, 6, 24), (0.30, 0.40, 0.50, 0.60)):
        slot = cq.Workplane("XY").box(6 + gap, 12, 4.4, centered=(True, True, False)).translate((x, 8, -0.2))
        coupon = coupon.cut(slot)
    return coupon


if __name__ == "__main__":
    export_bundle(build_coupon(), ROOT / "test_fixture" / "petg_tolerance_coupon")
