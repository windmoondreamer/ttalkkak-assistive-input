"""Joint search for a printable RP2040 + adjacent power-board layout."""

from __future__ import annotations

import json
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

# User-measured boards.
RP_X, RP_Y, RP_T = 17.92, 23.15, 1.60
PW_X, PW_Y, PW_KEEP_Z = 23.24, 15.35, 3.70  # power board rotated 90 deg

# Minimum printable open cradles.  Side walls 0.8 mm, floor 1.2 mm.
RP_CRADLE = (RP_X + 1.6, RP_Y + 1.6, RP_T + 1.2)
PW_CRADLE = (PW_X + 1.6, PW_Y + 1.6, PW_KEEP_Z + 1.2)
PAIR_GAP = 0.8

USB_W, USB_LEN, USB_H = 8.90, 12.0, 3.0


def box(x, y, z, cx, cy, cz):
    s = Box(x, y, z, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    solids = s.solids()
    s = solids[0] if solids else s
    return s.translate((cx, cy, cz))


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


def load_refs():
    housing = import_step(str(HOUSING_STEP))
    housing = max(housing.solids(), key=lambda s: s.volume)
    assembly = import_step(str(ASSEMBLY_STEP))
    loc = Location(T_ASSEMBLY_TO_GRIP[0], T_ASSEMBLY_TO_GRIP[1])
    for child in assembly.children:
        if child.label.startswith("Base_"):
            solids = [s.moved(loc) for s in child.solids()]
            return housing, solids, Compound(solids)
    raise RuntimeError("Base_<1> not found")


def clearance(shape, housing, gimbal):
    return min(float(shape.distance_to(housing)), float(shape.distance_to(gimbal)))


def main():
    housing, gimbal_solids, gimbal = load_refs()
    results = []

    # Move both modules together along Y.  RP Z also moves to seek a working
    # USB service corridor; the power cradle may sit at a different Z while
    # remaining beside the RP cradle in plan view.
    for rp_y in [float(v) for v in range(-52, -37, 2)]:
        power_y = rp_y + RP_CRADLE[1] / 2 + PAIR_GAP + PW_CRADLE[1] / 2
        for tray_origin_z in [float(v) for v in range(-143, -136, 2)]:
            rp_board_bottom = tray_origin_z + 2.7
            rp_board_center_z = rp_board_bottom + RP_T / 2
            rp_cradle_center_z = rp_board_center_z - 0.6

            # USB opening follows the user's bottom-from-tray datum.
            usb_bottom = tray_origin_z + 2.5
            usb_center_y = rp_y - RP_Y / 2 - USB_LEN / 2
            usb = box(USB_W, USB_LEN, USB_H,
                      0.5, usb_center_y, usb_bottom + USB_H / 2)

            rp_cradle = box(*RP_CRADLE, 0.5, rp_y, rp_cradle_center_z)
            rp_clear = clearance(rp_cradle, housing, gimbal)
            usb_clear = clearance(usb, housing, gimbal)
            if min(rp_clear, usb_clear) <= 1e-5:
                continue

            for power_cz in [round(-132.0 + 0.5 * i, 3) for i in range(11)]:
                power_cradle = box(*PW_CRADLE, 0.5, power_y, power_cz)
                power_clear = clearance(power_cradle, housing, gimbal)
                if power_clear <= 1e-5:
                    continue
                minimum = min(rp_clear, usb_clear, power_clear)
                results.append({
                    "tray_origin_xyz_mm": [0.5, rp_y, tray_origin_z],
                    "power_cradle_center_xyz_mm": [0.5, round(power_y, 3), power_cz],
                    "rp_cradle_clearance_mm": round(rp_clear, 4),
                    "usb_corridor_clearance_mm": round(usb_clear, 4),
                    "power_cradle_clearance_mm": round(power_clear, 4),
                    "minimum_system_clearance_mm": round(minimum, 4),
                })

    results.sort(key=lambda r: -r["minimum_system_clearance_mm"])
    exact = []
    for item in results[:30]:
        _, rp_y, tray_z = item["tray_origin_xyz_mm"]
        _, pw_y, pw_cz = item["power_cradle_center_xyz_mm"]
        rp_bottom = tray_z + 2.7
        rp_cz = rp_bottom + RP_T / 2 - 0.6
        usb_bottom = tray_z + 2.5
        usb_cy = rp_y - RP_Y / 2 - USB_LEN / 2
        shapes = {
            "rp_cradle": box(*RP_CRADLE, 0.5, rp_y, rp_cz),
            "usb_corridor": box(USB_W, USB_LEN, USB_H, 0.5, usb_cy, usb_bottom + USB_H / 2),
            "power_cradle": box(*PW_CRADLE, 0.5, pw_y, pw_cz),
        }
        entry = dict(item)
        valid = True
        for name, shape in shapes.items():
            hv = inter_vol(shape, housing)
            gv = sum(inter_vol(shape, s) for s in gimbal_solids)
            entry[f"{name}_housing_overlap_mm3"] = round(hv, 6)
            entry[f"{name}_gimbal_overlap_mm3"] = round(gv, 6)
            valid = valid and hv <= 1e-5 and gv <= 1e-5
        if valid:
            exact.append(entry)

    report = {
        "rp_cradle_envelope_mm": RP_CRADLE,
        "power_cradle_envelope_mm": PW_CRADLE,
        "pair_gap_mm": PAIR_GAP,
        "candidate_count": len(results),
        "exact_verified_best": exact[:20],
    }
    out = Path(__file__).with_suffix(".json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"REPORT={out}")


if __name__ == "__main__":
    main()
