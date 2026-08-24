"""D05 - confirm every Thumb authority source is byte-identical to the baseline.

Copied from REV_A/10_scripts/a16_source_check.py so that it writes into REV_B.
Running the REV_A copy regenerates REV_A/00_admin/a16_source_check.json, which
breaks the REV_A-is-immutable rule; that happened once and is recorded in the
REV_B report.  Use this copy from now on.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402


def main() -> int:
    base = json.loads((L.REV_A / "00_admin" / "SOURCE_BASELINE.json").read_text(encoding="utf-8"))["files"]
    bad, rows = 0, {}
    print("%-34s %-16s %s" % ("AUTHORITY SOURCE", "STATE", "SHA-256"))
    for k, p in sorted(L.SRC.items()):
        rel = p.relative_to(L.ROOT).as_posix()
        now = L.sha256(p)
        ref = base.get(rel, {}).get("sha256")
        state = "UNCHANGED" if (ref and ref == now) else ("NOT_IN_BASELINE" if ref is None else "CHANGED")
        if state != "UNCHANGED":
            bad += 1
        rows[k] = {"path": rel, "sha256": now, "state": state}
        print("%-34s %-16s %s" % (k, state, now))
    print("\nTHUMB AUTHORITY SOURCES CHANGED: %d" % bad)

    now_all = {}
    for pattern in ("build123d_workbench/*.py", "docs/*.md", "local_cad/reference/*",
                    "build123d_workbench/out/integrated_exterior_lowered_thumb_v1/*",
                    "build123d_workbench/out/finger_controls_v2/*.step",
                    "build123d_workbench/out/finger_thumb_joint_feasibility/*.step",
                    "build123d_workbench/out/original_thumb_module_reuse_audit/*",
                    "build123d_workbench/out/n1_production_intent_mechanism/*.step",
                    "build123d_workbench/out/szh_actual_fit_fixture/*",
                    "build123d_workbench/out/szh_ek056_knob_interface_confirmation/*",
                    "lower_adapter/local_cad/reference/*.step", "cad/*.fs"):
        for p in sorted(L.ROOT.glob(pattern)):
            if p.is_file():
                now_all[p.relative_to(L.ROOT).as_posix()] = L.sha256(p)
    changed = sorted(k for k in base if k in now_all and now_all[k] != base[k]["sha256"])
    removed = sorted(k for k in base if k not in now_all)
    added = sorted(k for k in now_all if k not in base)
    print("\nWHOLE WATCH SET  changed=%d removed=%d added=%d" % (len(changed), len(removed), len(added)))
    for k in changed:
        print("  CHANGED %s" % k)
    for k in removed:
        print("  REMOVED %s" % k)
    for k in added:
        print("  ADDED   %s" % k)

    L.write_json(L.LAB / "00_admin" / "d05_source_check.json",
                 {"authoritySources": rows, "authorityChangedCount": bad,
                  "watchSetChanged": changed, "watchSetRemoved": removed,
                  "watchSetAdded": added})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
