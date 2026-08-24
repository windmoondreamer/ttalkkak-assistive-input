"""Search for a single-level power-board placement adjacent to RP2040-Zero.

The search uses the user's measured board envelope and the immutable housing/
stock-gimbal STEP references.  It deliberately excludes any placement that
overlaps the RP2040 board or its provisional straight USB service corridor.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from build123d import Align, Box, Compound, Location, import_step


ROOT = Path(
    r"C:\Users\guest2\Desktop\ttalkkak-assistive-input-add-onegrip-play-cad-workspace"
    r"\workstreams\onegrip-play"
)
HOUSING_STEP = ROOT / "lower_adapter/local_cad/reference/CONFORMAL_CORE_REFERENCE.step"
ASSEMBLY_STEP = ROOT / "lower_adapter/local_cad/reference/ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step"

T_ASSEMBLY_TO_GRIP = (
    (0.5760063798429542, 18.785985876151216, -149.95651399999994),
    (0, 0, 180),
)

# Current verified RP2040 board placement, based on the user's measurements.
RP_CENTER_X = 0.5
RP_CENTER_Y = -44.0
RP_BOTTOM_Z = -134.3
RP_X, RP_Y, RP_T = 17.92, 23.15, 1.60

# Power board: actual plan dimensions.  Envelope height includes the stated
# 2.1 mm lower protrusion plus a provisional 1.6 mm PCB thickness.
PW_A, PW_B, PW_H = 15.35, 23.24, 3.70

# Actual USB connector opening plus a provisional 12 mm straight service path.
USB_W, USB_PATH_Y, USB_H = 8.90, 12.0, 3.0
USB_CENTER_Y = RP_CENTER_Y - RP_Y / 2 - USB_PATH_Y / 2
USB_BOTTOM_Z = -134.5


def solid_box(x, y, z, cx, cy, bottom_z):
    shape = Box(x, y, z, align=(Align.CENTER, Align.CENTER, Align.MIN))
    shape = shape.translate((cx, cy, bottom_z))
    solids = shape.solids()
    return solids[0] if solids else shape


def bbox_overlap(a, b):
    aa, bb = a.bounding_box(), b.bounding_box()
    return not (
        aa.max.X <= bb.min.X or aa.min.X >= bb.max.X
        or aa.max.Y <= bb.min.Y or aa.min.Y >= bb.max.Y
        or aa.max.Z <= bb.min.Z or aa.min.Z >= bb.max.Z
    )


def intersection_volume(a, b):
    if not bbox_overlap(a, b):
        return 0.0
    result = a.intersect(b)
    if result is None:
        return 0.0
    solids = result.solids() if hasattr(result, "solids") else [result]
    return float(sum(s.volume for s in solids))


def envelope_gap_xy(cx, cy, sx, sy):
    """2-D edge-to-edge gap from the RP board; negative means overlap."""
    dx = abs(cx - RP_CENTER_X) - (sx + RP_X) / 2
    dy = abs(cy - RP_CENTER_Y) - (sy + RP_Y) / 2
    if dx > 0 and dy > 0:
        return math.hypot(dx, dy)
    return max(dx, dy)


def load_references():
    housing = import_step(str(HOUSING_STEP))
    housing_shell = max(housing.solids(), key=lambda s: s.volume)
    assembly = import_step(str(ASSEMBLY_STEP))
    loc = Location(T_ASSEMBLY_TO_GRIP[0], T_ASSEMBLY_TO_GRIP[1])
    for child in assembly.children:
        if child.label.startswith("Base_"):
            solids = [s.moved(loc) for s in child.solids()]
            return housing_shell, solids, Compound(solids)
    raise RuntimeError("Base_<1> not found")


def clear_of_references(shape, housing, gimbal_compound):
    # OCCT distance is substantially faster than thousands of Boolean-common
    # operations.  Exact Boolean volumes are recalculated for finalists below.
    hd = float(shape.distance_to(housing))
    if hd <= 1e-5:
        return False, hd, 0.0
    gd = float(shape.distance_to(gimbal_compound))
    if gd <= 1e-5:
        return False, hd, gd
    return True, hd, gd


def search_grid(housing, gimbal_compound, step_xy, step_z, local_center=None):
    rp = solid_box(RP_X, RP_Y, RP_T, RP_CENTER_X, RP_CENTER_Y, RP_BOTTOM_Z)
    usb = solid_box(
        USB_W, USB_PATH_Y, USB_H,
        RP_CENTER_X, USB_CENTER_Y, USB_BOTTOM_Z,
    )
    candidates = []
    orientations = [("long_Y", PW_A, PW_B), ("long_X", PW_B, PW_A)]

    for orientation, sx, sy in orientations:
        if local_center is None:
            # Search narrow bands immediately around the four RP board edges.
            # This is both mechanically meaningful and far faster than testing
            # the entire lower cavity against 69 separate gimbal solids.
            xy_points = set()
            gaps = [0.5, 2.5, 4.5, 6.5, 8.5, 10.5]
            offsets = [round(-10 + i * step_xy, 3)
                       for i in range(int(20 / step_xy) + 1)]
            for gap in gaps:
                x_plus = RP_CENTER_X + (RP_X + sx) / 2 + gap
                x_minus = RP_CENTER_X - (RP_X + sx) / 2 - gap
                y_plus = RP_CENTER_Y + (RP_Y + sy) / 2 + gap
                y_minus = RP_CENTER_Y - (RP_Y + sy) / 2 - gap
                for offset in offsets:
                    xy_points.add((round(x_plus, 3), round(RP_CENTER_Y + offset, 3)))
                    xy_points.add((round(x_minus, 3), round(RP_CENTER_Y + offset, 3)))
                    xy_points.add((round(RP_CENTER_X + offset, 3), round(y_plus, 3)))
                    xy_points.add((round(RP_CENTER_X + offset, 3), round(y_minus, 3)))
            zs = [round(-142 + i * step_z, 3) for i in range(int(13 / step_z) + 1)]
        else:
            bx, by, bz = local_center
            xs = [round(bx - 2 + i * step_xy, 3) for i in range(int(4 / step_xy) + 1)]
            ys = [round(by - 2 + i * step_xy, 3) for i in range(int(4 / step_xy) + 1)]
            xy_points = {(x, y) for x in xs for y in ys}
            zs = [round(bz - 1.5 + i * step_z, 3) for i in range(int(3 / step_z) + 1)]

        for z in zs:
            for x, y in xy_points:
                    gap = envelope_gap_xy(x, y, sx, sy)
                    # Must be a genuinely adjacent, single-level placement:
                    # no XY overlap with RP and no more than 12 mm away.
                    if gap < 0.50 or gap > 12.0:
                        continue
                    board = solid_box(sx, sy, PW_H, x, y, z)
                    if intersection_volume(board, rp) > 1e-5:
                        continue
                    if intersection_volume(board, usb) > 1e-5:
                        continue
                    clear, hd, gd = clear_of_references(board, housing, gimbal_compound)
                    if not clear:
                        continue
                    # Prefer short wiring, close Z alignment, and little lateral
                    # displacement from the existing board cavity.
                    score = gap + 0.35 * abs(z - (RP_BOTTOM_Z - 2.1)) + 0.03 * abs(x - RP_CENTER_X)
                    candidates.append({
                        "orientation": orientation,
                        "size_xyz_mm": [sx, sy, PW_H],
                        "center_xy_bottom_z_mm": [x, y, z],
                        "edge_gap_to_rp_xy_mm": round(gap, 3),
                        "score": round(score, 4),
                        "housing_clearance_mm": round(hd, 4),
                        "gimbal_clearance_mm": round(gd, 4),
                    })
    return sorted(candidates, key=lambda c: c["score"])


def main():
    housing, gimbal_solids, gimbal_compound = load_references()
    coarse = search_grid(housing, gimbal_compound, step_xy=5.0, step_z=2.0)
    refined = []
    for seed in coarse[:8]:
        x, y, z = seed["center_xy_bottom_z_mm"]
        refined.extend(search_grid(housing, gimbal_compound, step_xy=0.5, step_z=0.5,
                                   local_center=(x, y, z)))
    # Deduplicate refinement candidates.
    unique = {}
    for item in refined:
        key = (item["orientation"], *item["center_xy_bottom_z_mm"])
        unique[key] = item
    refined = sorted(unique.values(), key=lambda c: c["score"])

    # Exact Boolean verification for the best distinct candidates.
    exact = []
    for item in refined[:30]:
        sx, sy, sz = item["size_xyz_mm"]
        x, y, z = item["center_xy_bottom_z_mm"]
        board = solid_box(sx, sy, sz, x, y, z)
        hv = intersection_volume(board, housing)
        gv = sum(intersection_volume(board, part) for part in gimbal_solids)
        verified = dict(item)
        verified["housing_overlap_mm3"] = round(hv, 6)
        verified["gimbal_overlap_mm3"] = round(gv, 6)
        if hv <= 1e-5 and gv <= 1e-5:
            exact.append(verified)

    result = {
        "definition": {
            "power_keepout_mm": [PW_A, PW_B, PW_H],
            "rp2040_center_xy_bottom_z_mm": [RP_CENTER_X, RP_CENTER_Y, RP_BOTTOM_Z],
            "usb_service_corridor_mm": [USB_W, USB_PATH_Y, USB_H],
            "single_level_rule": "power board XY envelope must not overlap RP2040; 0.5-12 mm edge gap",
        },
        "coarse_clear_count": len(coarse),
        "coarse_best": coarse[:20],
        "refined_clear_count": len(refined),
        "refined_best": refined[:30],
        "exact_boolean_verified_best": exact[:20],
    }
    out = Path(__file__).with_suffix(".json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"REPORT={out}")


if __name__ == "__main__":
    main()
