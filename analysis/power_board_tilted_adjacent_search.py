"""Targeted search for a printable, tilted, adjacent power-board cradle."""

from __future__ import annotations

import json
import math
from pathlib import Path

from build123d import Align, Box, Compound, Location, Rot, import_step


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

RP_X, RP_Y, RP_T = 17.92, 23.15, 1.60
RP_CENTER = (0.5, -44.0, -133.5)
RP_PLUS_Y = RP_CENTER[1] + RP_Y / 2

# Rotated power-board envelope: long dimension across X.
PW_X, PW_Y, PW_Z = 23.24, 15.35, 3.70

# Minimum printable cradle envelope.  0.8 mm side walls and a 1.2 mm floor;
# top is open.  The conservative Z box includes the floor under the board.
CRADLE_X = PW_X + 1.6
CRADLE_Y = PW_Y + 1.6
CRADLE_Z = PW_Z + 1.2


def centered_box(x, y, z):
    b = Box(x, y, z, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    s = b.solids()
    return s[0] if s else b


def oriented_box(x, y, z, angle_x, center):
    return (Rot(angle_x, 0, 0) * centered_box(x, y, z)).translate(center)


def bbox_overlap(a, b):
    aa, bb = a.bounding_box(), b.bounding_box()
    return not (
        aa.max.X <= bb.min.X or aa.min.X >= bb.max.X
        or aa.max.Y <= bb.min.Y or aa.min.Y >= bb.max.Y
        or aa.max.Z <= bb.min.Z or aa.min.Z >= bb.max.Z
    )


def inter_vol(a, b):
    if not bbox_overlap(a, b):
        return 0.0
    result = a.intersect(b)
    if result is None:
        return 0.0
    solids = result.solids() if hasattr(result, "solids") else [result]
    return float(sum(s.volume for s in solids))


def main():
    housing = import_step(str(HOUSING_STEP))
    housing_shell = max(housing.solids(), key=lambda s: s.volume)
    assembly = import_step(str(ASSEMBLY_STEP))
    loc = Location(T_ASSEMBLY_TO_GRIP[0], T_ASSEMBLY_TO_GRIP[1])
    gimbal_solids = None
    for child in assembly.children:
        if child.label.startswith("Base_"):
            gimbal_solids = [s.moved(loc) for s in child.solids()]
            break
    if gimbal_solids is None:
        raise RuntimeError("Base_<1> not found")
    gimbal = Compound(gimbal_solids)

    rp = centered_box(RP_X, RP_Y, RP_T).translate(RP_CENTER)
    results = []

    # The lower-adapter deck rises toward +Y by approximately 20 degrees.
    # Test both signs to avoid assuming the CAD frame convention.
    for angle in (-30, -20, -10, 0, 10, 20, 30):
        projected_y = CRADLE_Y * abs(math.cos(math.radians(angle))) + CRADLE_Z * abs(math.sin(math.radians(angle)))
        for gap in (0.5, 1.5, 3.0):
            cy = RP_PLUS_Y + gap + projected_y / 2
            for cx in (-0.5, 0.5, 1.5):
                for cz in [round(-133.0 + 0.5 * i, 3) for i in range(15)]:
                    cradle = oriented_box(CRADLE_X, CRADLE_Y, CRADLE_Z, angle, (cx, cy, cz))
                    if cradle.distance_to(rp) < 0.49:
                        continue
                    hd = float(cradle.distance_to(housing_shell))
                    if hd <= 1e-5:
                        continue
                    gd = float(cradle.distance_to(gimbal))
                    if gd <= 1e-5:
                        continue
                    results.append({
                        "angle_x_deg": angle,
                        "rp_to_cradle_gap_mm": gap,
                        "cradle_center_xyz_mm": [round(cx, 3), round(cy, 3), cz],
                        "housing_clearance_mm": round(hd, 4),
                        "gimbal_clearance_mm": round(gd, 4),
                        "minimum_clearance_mm": round(min(hd, gd), 4),
                    })

    # Prefer the largest actual clearance, then the shortest connection gap.
    results.sort(key=lambda r: (-r["minimum_clearance_mm"], r["rp_to_cradle_gap_mm"]))
    exact = []
    for item in results[:30]:
        angle = item["angle_x_deg"]
        center = item["cradle_center_xyz_mm"]
        cradle = oriented_box(CRADLE_X, CRADLE_Y, CRADLE_Z, angle, center)
        hv = inter_vol(cradle, housing_shell)
        gv = sum(inter_vol(cradle, s) for s in gimbal_solids)
        e = dict(item)
        e.update({"housing_overlap_mm3": round(hv, 6), "gimbal_overlap_mm3": round(gv, 6)})
        if hv <= 1e-5 and gv <= 1e-5:
            exact.append(e)

    report = {
        "board_envelope_mm": [PW_X, PW_Y, PW_Z],
        "minimum_fdm_cradle_envelope_mm": [CRADLE_X, CRADLE_Y, CRADLE_Z],
        "candidate_count": len(results),
        "exact_verified_best": exact[:20],
        "note": "Top-side component height of the power board is still unmeasured.",
    }
    out = Path(__file__).with_suffix(".json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"REPORT={out}")


if __name__ == "__main__":
    main()
