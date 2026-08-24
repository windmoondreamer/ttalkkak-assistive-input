"""A03 - decide the frozen-exterior authority by a low-noise, targeted test.

If a shell carries the LOWERED Thumb openings, a lowered cap/attachment solid
sits in a hole and barely intersects it.  If it does not, the same solid is
buried in shell material.  Run that test for both candidate shell pairs, in
both the ORIGINAL and the LOWERED Thumb position.

Booleans here are cap-vs-shell-crop: small, well separated volumes, which is
the regime where OCC is reliable.  Shell-vs-shell near-coincident booleans are
NOT used (they returned negative/zero common volumes in A02).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402

OUT = L.LAB / "01_source_map"
COPIES = L.LAB / "02_reference_copies"

CROP_LO = (-30.0, -36.0, -34.0)
CROP_HI = (30.0, 30.0, 14.0)


def cartridge_parts(key: str) -> dict:
    root = import_step(L.SRC[key])
    parts = {}
    def walk(shape):
        kids = list(getattr(shape, "children", []) or [])
        if kids:
            for k in kids:
                walk(k)
            return
        if shape.solids():
            parts[str(shape.label)] = shape
    walk(root)
    return root, parts


def main() -> int:
    box = L.local_box(CROP_LO, CROP_HI, "CROP")

    shells = {}
    for tag, key in (("JAD_FROZEN", "JAD_LOWERED_THUMB"), ("JFD_FROZEN", "JFD_LOWERED_THUMB"),
                     ("JAD_FV2", "JAD_FINGER_V2"), ("JFD_FV2", "JFD_FINGER_V2"),
                     ("JAD_CLEAN", "JAD_CLEAN_PRE_FINGER"), ("JFD_CLEAN", "JFD_CLEAN_PRE_FINGER")):
        full = L.load(key)
        sec, _ = L.as_single_solid((full & box).clean(), tag)
        shells[tag] = sec
        del full
        L.memory("crop " + tag)

    results = {}
    for cart_key, tag in (("ORIGINAL_THUMB_CARTRIDGE", "ORIGINAL_POSITION"),
                          ("LOWERED_ORIGINAL_THUMB_CARTRIDGE", "LOWERED_POSITION")):
        root, parts = cartridge_parts(cart_key)
        print("\n=== %s : %d leaf solids ===" % (tag, len(parts)))
        externals = {n: s for n, s in parts.items()
                     if "CAP" in n.upper() or "ATTACHMENT" in n.upper()}
        rows = {}
        for name in sorted(externals):
            part = L.as_single_solid(externals[name], name)[0]
            lb = L.local_bbox(part, 20000)
            row = {"partVolumeMm3": L.vol(part), "localBbox": lb}
            for stag, shell in shells.items():
                row[stag] = L.inter_vol(part, shell)
            rows[name] = row
            print("  %-46s vol=%8.2f  n=[%7.2f,%7.2f]" % (name[:46], row["partVolumeMm3"],
                                                          lb["min"][2], lb["max"][2]))
            print("      buried-in: JAD_FROZEN=%8.3f JFD_FROZEN=%8.3f | JAD_FV2=%8.3f JFD_FV2=%8.3f"
                  " | JAD_CLEAN=%8.3f JFD_CLEAN=%8.3f"
                  % (row["JAD_FROZEN"], row["JFD_FROZEN"], row["JAD_FV2"], row["JFD_FV2"],
                     row["JAD_CLEAN"], row["JFD_CLEAN"]))
        results[tag] = rows
        # totals
        for stag in shells:
            tot = sum(r[stag] for r in rows.values())
            print("  TOTAL buried volume in %-12s = %10.3f mm3" % (stag, tot))
            results.setdefault(tag + "_TOTALS", {})[stag] = tot
        del root, parts
        L.memory("cartridge " + tag)

    L.write_json(OUT / "a03_shell_authority.json", {"results": results, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
