"""Transient FeatureScript B-rep collision probes; no Part Studio mutation."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from collections import Counter


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_i4_retainer as api  # noqa: E402


SCRIPT = r'''
function(context is Context, queries is map)
{
    const jfd = qContainsPoint(qAllSolidBodies(), vector(-4.8872, 0, -35) * millimeter);
    const jad = qContainsPoint(qAllSolidBodies(), vector(4.8859, 0, -35) * millimeter);
    const rwid = qCreatedBy(makeId("Fq5IPkiwWk5pWYv_15"), EntityType.BODY);
    const rzkd = qCreatedBy(makeId("F2N4HZlwCZvkovM_16"), EntityType.BODY);
    return {
        "RWID_JfD" : evCollision(context, { "tools" : rwid, "targets" : jfd }),
        "RWID_JaD" : evCollision(context, { "tools" : rwid, "targets" : jad }),
        "RZKD_JaD" : evCollision(context, { "tools" : rzkd, "targets" : jad }),
        "RWID_RZKD" : evCollision(context, { "tools" : rwid, "targets" : rzkd })
    };
}
'''


def flat(value):
    """Decode Onshape's BT value wrappers into ordinary Python values."""
    if not isinstance(value, dict):
        return value
    bt_type = value.get("btType", "")
    if "ValueMap" in bt_type:
        return {flat(item["key"]): flat(item["value"]) for item in value.get("value", [])}
    if "ValueArray" in bt_type:
        return [flat(item) for item in value.get("value", [])]
    if any(kind in bt_type for kind in ("ValueNumber", "ValueString", "ValueBoolean")):
        return value.get("value")
    if "ValueWithUnits" in bt_type:
        return value.get("value")
    if "value" in value:
        return flat(value["value"])
    return value


def summarize(rows):
    rows = rows if isinstance(rows, list) else []
    types = Counter()
    for row in rows:
        if isinstance(row, dict):
            types[str(row.get("type", "UNKNOWN"))] += 1
        else:
            types["UNKNOWN"] += 1
    return {"count": len(rows), "types": dict(sorted(types.items()))}


def main():
    version_id = sys.argv[1] if len(sys.argv) > 1 else None
    locator = f"v/{version_id}" if version_id else f"w/{api.WID}"
    output = api.request(
        "POST",
        f"partstudios/d/{api.DID}/{locator}/e/{api.EID}/featurescript",
        {"script": SCRIPT},
    )
    decoded = flat(output.get("result", output))
    report = {
        "locator": locator,
        "pairs": {name: summarize(rows) for name, rows in decoded.items()},
    }
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
