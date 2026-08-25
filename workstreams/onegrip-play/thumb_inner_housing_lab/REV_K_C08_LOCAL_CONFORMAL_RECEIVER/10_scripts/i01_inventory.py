"""I01 - inventory every REV_A..REV_H artifact and hash it (REV_I section 24).

Read-only.  Produces the evidence table behind PREVIOUS_WORK_REUSE_MAP.md so the
classification is anchored to real files, not to memory of what was built.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402

OUT = L.LAB / "01_inventory"
REVS = ["REV_A", "REV_B", "REV_C", "REV_D_EXACT_SOURCE", "REV_E_C02_REFINED",
        "REV_F_RIGID_FIT", "REV_G_BACKPLATE_DRIVEN_FREEZE",
        "REV_H_ORIGINAL_SWITCH_MECHANISM"]
GEOM = {".step", ".stl", ".brep"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest().upper()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    root = L.LAB.parent
    inv = {}
    for r in REVS:
        d = root / r
        files = sorted(p for p in d.rglob("*")
                       if p.is_file() and p.suffix != ".pyc")
        rec = {"fileCount": len(files), "geometry": [], "data": [], "reports": [],
               "scripts": [], "renders": []}
        for p in files:
            rel = p.relative_to(d).as_posix()
            e = {"path": rel, "bytes": p.stat().st_size}
            if p.suffix.lower() in GEOM:
                e["sha256"] = sha(p)
                rec["geometry"].append(e)
            elif p.suffix == ".md":
                rec["reports"].append(e)
            elif p.suffix == ".py":
                rec["scripts"].append(e)
            elif p.suffix == ".png":
                rec["renders"].append(e)
            else:
                rec["data"].append(e)
        inv[r] = rec
        print("%-34s files %4d  geom %3d  data %3d  md %2d  py %3d  png %3d"
              % (r, rec["fileCount"], len(rec["geometry"]), len(rec["data"]),
                 len(rec["reports"]), len(rec["scripts"]), len(rec["renders"])))

    # the frozen external authority must still hash to the REV_D baseline
    gate = {}
    for k in ("JAD_APPROVED", "JFD_APPROVED"):
        p = L.SRC[k]
        gate[k] = {"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size}
    base = {"JAD_APPROVED": "622ADB3B1B1D6095435AAC624BB11042080FC8B7399B0C920BECDE708FA54E86",
            "JFD_APPROVED": "D75F62E04DF15B1150EA10EEB8DA1AAA0AAE7CA7C31862CEA42823A0929EA340"}
    ok = all(gate[k]["sha256"] == base[k] for k in base)
    for k in base:
        print("\nauthority %-14s %s  %s" % (k, gate[k]["sha256"][:16] + "...",
                                            "MATCHES REV_D" if gate[k]["sha256"] == base[k]
                                            else "!! CHANGED !!"))
    print("\nSHELL AUTHORITY GATE = %s" % ("PASS" if ok else "FAIL"))

    # every upstream reference this revision intends to read
    srcs = {}
    for k, p in L.SRC.items():
        srcs[k] = {"path": str(p), "exists": p.exists(),
                   "bytes": p.stat().st_size if p.exists() else 0,
                   "sha256": sha(p) if p.exists() and p.suffix.lower() in GEOM else None}
    miss = [k for k, v in srcs.items() if not v["exists"]]
    print("upstream references: %d present, %d missing %s"
          % (len(srcs) - len(miss), len(miss), miss or ""))

    L.write_json(OUT / "i01_inventory.json",
                 {"revisions": inv, "shellAuthorityGate": {"pass": ok, "hashes": gate,
                                                           "baseline": base},
                  "upstreamSources": srcs})
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
