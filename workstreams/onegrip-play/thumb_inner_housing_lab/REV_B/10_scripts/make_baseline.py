"""Record a hash/size/mtime baseline of every production source the Lab reads.

Write scope: thumb_inner_housing_lab/REV_A only.  Read-only elsewhere.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parents[1]

WATCH_GLOBS = [
    "build123d_workbench/*.py",
    "build123d_workbench/out/integrated_exterior_lowered_thumb_v1/*",
    "build123d_workbench/out/finger_controls_v2/*.step",
    "build123d_workbench/out/finger_thumb_joint_feasibility/*.step",
    "build123d_workbench/out/original_thumb_module_reuse_audit/*",
    "build123d_workbench/out/n1_production_intent_mechanism/*.step",
    "build123d_workbench/out/szh_actual_fit_fixture/*",
    "build123d_workbench/out/szh_ek056_knob_interface_confirmation/*",
    "local_cad/reference/*",
    "lower_adapter/local_cad/reference/*.step",
    "docs/*.md",
    "cad/*.fs",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def collect() -> dict:
    records = {}
    for pattern in WATCH_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            st = path.stat()
            records[rel] = {
                "bytes": st.st_size,
                "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                "sha256": sha256(path),
            }
    return records


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "create"
    out = LAB / "00_admin" / "SOURCE_BASELINE.json"
    records = collect()
    if mode == "create":
        out.write_text(json.dumps({"root": str(ROOT), "count": len(records),
                                   "capturedUtc": datetime.now(timezone.utc).isoformat(),
                                   "files": records}, indent=2), encoding="utf-8")
        print(f"baseline written: {len(records)} files -> {out}")
        return 0
    prior = json.loads(out.read_text(encoding="utf-8"))["files"]
    changed = [k for k in prior if k not in records or records[k]["sha256"] != prior[k]["sha256"]]
    added = [k for k in records if k not in prior]
    print(f"checked {len(records)} files")
    print(f"CHANGED/REMOVED outside Lab: {len(changed)}")
    for k in changed:
        print("  !", k)
    print(f"ADDED outside Lab: {len(added)}")
    for k in added:
        print("  +", k)
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
