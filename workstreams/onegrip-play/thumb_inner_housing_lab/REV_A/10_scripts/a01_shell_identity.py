"""A01 - which shell STEP actually carries the frozen lowered-Thumb exterior?

Two different production scripts use two different "current shell" pairs:
  * original_thumb_module_reuse_audit.py -> JAD/JFD_EXTERIOR_LOWERED_THUMB_V1
  * szh_ek056_provisional_thumb_integration_audit.py -> JAD/JFD_FINGER_V2

They cannot both be the frozen exterior.  Decide by geometry, not by name.
READ-ONLY on all sources; writes only into the Lab.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402

OUT = L.LAB / "01_source_map"


def summarise(key: str) -> dict:
    shape = L.load(key)
    solids = list(shape.solids())
    row = {
        "key": key,
        "path": str(L.SRC[key].relative_to(L.ROOT)).replace("\\", "/"),
        "sha256": L.sha256(L.SRC[key]),
        "bytes": L.SRC[key].stat().st_size,
        "solidCount": len(solids),
        "volumeMm3": float(sum(float(s.volume) for s in solids)),
        "bboxWorld": L.bbox_dict(shape),
    }
    # thumb-local extent of material inside the thumb control region
    pts = L.surf_points(shape, 120000)
    loc = L.to_local(pts)
    # local thumb window: joystick datum +-30 mm in u/v, -40..+15 in n
    m = (np.abs(loc[:, 0]) <= 30.0) & (np.abs(loc[:, 1]) <= 34.0) & (loc[:, 2] > -45.0) & (loc[:, 2] < 15.0)
    row["thumbWindowSamplePoints"] = int(m.sum())
    if m.any():
        w = loc[m]
        row["thumbWindowLocalBbox"] = {
            "min": [float(x) for x in w.min(axis=0)],
            "max": [float(x) for x in w.max(axis=0)],
        }
        # how much material sits ABOVE (outboard of) the datum plane n=0?
        row["thumbWindowMaxOutwardN"] = float(w[:, 2].max())
    del shape, pts, loc
    L.memory("summarised " + key)
    return row


def main() -> int:
    keys = ["JAD_LOWERED_THUMB", "JFD_LOWERED_THUMB",
            "JAD_FINGER_V2", "JFD_FINGER_V2",
            "JAD_CLEAN_PRE_FINGER", "JFD_CLEAN_PRE_FINGER"]
    rows = [summarise(k) for k in keys]
    for r in rows:
        print("\n%-22s solids=%d vol=%14.4f  thumbWin pts=%6d  maxOutwardN=%s"
              % (r["key"], r["solidCount"], r["volumeMm3"], r["thumbWindowSamplePoints"],
                 ("%.4f" % r["thumbWindowMaxOutwardN"]) if "thumbWindowMaxOutwardN" in r else "-"))
        print("   bbox world min=%s" % np.round(r["bboxWorld"]["min"], 4))
        print("   bbox world max=%s" % np.round(r["bboxWorld"]["max"], 4))
        if "thumbWindowLocalBbox" in r:
            print("   thumb-local win min=%s max=%s"
                  % (np.round(r["thumbWindowLocalBbox"]["min"], 3),
                     np.round(r["thumbWindowLocalBbox"]["max"], 3)))
    L.write_json(OUT / "a01_shell_identity.json", {"shells": rows, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
