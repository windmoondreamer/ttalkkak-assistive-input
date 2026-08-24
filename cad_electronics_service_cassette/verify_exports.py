"""Round-trip STEP and binary-STL manifold checks for cassette exports."""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import struct

import cadquery as cq


HERE = Path(__file__).resolve().parent
OUT = HERE / "export"
NAMES = (
    "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_BODY_V4",
    "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_LID_V4",
    "ONEGRIP_ELECTRONICS_CASSETTE_PRINT_LAYOUT_V5",
    "ONEGRIP_STOCK_SPRING_BASE_CASSETTE_BODY_INTEGRATED_V4",
    "ONEGRIP_STOCK_SPRING_BASE_CASSETTE_LID_ASSEMBLY_V4",
    "ONEGRIP_STOCK_SPRING_BASE_CASSETTE_LID_PRINT_LAYOUT_V4",
    "RP2040_LENGTH_CLEARANCE_COUPON_050_060_070",
    "RP2040_USB_PORT_FDM_COUPON",
)


def vertex_key(v):
    return tuple(round(float(x), 5) for x in v)


def read_binary_stl(path):
    triangles = []
    with path.open("rb") as handle:
        handle.seek(80)
        count = struct.unpack("<I", handle.read(4))[0]
        for _ in range(count):
            values = struct.unpack("<12fH", handle.read(50))
            triangles.append((values[3:6], values[6:9], values[9:12]))
    return triangles


def stl_check(path):
    triangles = read_binary_stl(path)
    edges = Counter()
    degenerate = 0
    signed_volume = 0.0
    for tri in triangles:
        a, b, c = tri
        ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        cross = (
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        )
        if math.sqrt(sum(v * v for v in cross)) < 1e-8:
            degenerate += 1
        signed_volume += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0
        keys = [vertex_key(v) for v in tri]
        for i, j in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((keys[i], keys[j])))] += 1
    bad_edges = sum(1 for count in edges.values() if count != 2)
    return {
        "triangle_count": len(triangles),
        "degenerate_triangles": degenerate,
        "nonmanifold_or_open_edges": bad_edges,
        "watertight_by_edge_count": bad_edges == 0,
        "signed_mesh_volume_mm3": round(signed_volume, 3),
    }


def main():
    report = {}
    for name in NAMES:
        step = cq.importers.importStep(str(OUT / f"{name}.step"))
        solids = step.solids().vals()
        compound = cq.Compound.makeCompound(solids)
        bbox = compound.BoundingBox()
        item = {
            "step_valid": bool(all(s.isValid() for s in solids)),
            "step_solid_count": len(solids),
            "step_volume_mm3": round(sum(float(s.Volume()) for s in solids), 3),
            "step_bbox_mm": [
                round(bbox.xlen, 3),
                round(bbox.ylen, 3),
                round(bbox.zlen, 3),
            ],
        }
        item.update(stl_check(OUT / f"{name}.stl"))
        item["mesh_vs_step_volume_error_pct"] = round(
            abs(abs(item["signed_mesh_volume_mm3"]) - item["step_volume_mm3"])
            / item["step_volume_mm3"] * 100,
            5,
        )
        report[name] = item
    path = OUT / "export_verification.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
