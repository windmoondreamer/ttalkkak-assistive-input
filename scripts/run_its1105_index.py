"""Atomic runner for the approved ITS-1105 INDEX downstream Feature Studio."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_i4_retainer as api  # guarded urllib write path; noqa: E402


SOURCE = ROOT / "cad" / "OneGrip_ITS1105_Index.fs"
TARGET = ROOT / "cad_dump" / "its1105_index_target.json"
ASSEMBLY_EID = "250f706cb675e635b8d344c4"


def target():
    return json.loads(TARGET.read_text(encoding="utf-8"))


def features():
    return api.request(
        "GET",
        f"partstudios/d/{api.DID}/w/{api.WID}/e/{api.EID}/features?noSketchGeometry=true",
    )


def parts():
    return api.request("GET", f"parts/d/{api.DID}/w/{api.WID}/e/{api.EID}?configuration=default")


def health():
    tree = features()
    counts = {}
    bad = {}
    for feature_id, state in tree.get("featureStates", {}).items():
        status = state.get("featureStatus", "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
        if status not in ("OK", "INFO"):
            bad[feature_id] = status
    solids = [
        (row.get("partId"), row.get("name"))
        for row in parts() if row.get("bodyType") == "solid"
    ]
    return {
        "microversion": tree.get("sourceMicroversion"),
        "featureCount": len(tree.get("features", [])),
        "stateCounts": counts,
        "complete": tree.get("isComplete"),
        "bad": bad,
        "solids": solids,
    }


def assembly_health():
    data = api.request(
        "GET",
        f"assemblies/d/{api.DID}/w/{api.WID}/e/{ASSEMBLY_EID}?configuration=default",
    )
    root = data["rootAssembly"]
    active = {row["id"] for row in root.get("instances", []) if not row.get("suppressed")}
    occurrences = {row["path"][0] for row in root.get("occurrences", []) if row.get("path")}
    return {
        "instances": len(root.get("instances", [])),
        "active": len(active),
        "occurrences": len(root.get("occurrences", [])),
        "rootMismatch": sorted(active ^ occurrences),
    }


def upload():
    cfg = target()
    api.request(
        "POST",
        f"featurestudios/d/{api.DID}/w/{api.WID}/e/{cfg['eid']}",
        {"contents": SOURCE.read_text(encoding="utf-8")},
    )
    specs = api.request(
        "GET", f"featurestudios/d/{api.DID}/w/{api.WID}/e/{cfg['eid']}/featurespecs"
    )
    rows = specs.get("featureSpecs", [])
    if not rows:
        raise RuntimeError(f"FeatureScript compile failed: {json.dumps(specs)[:1600]}")
    return {"namespace": rows[0]["namespace"], "featureType": rows[0]["featureType"]}


def feature(button: str, stage: str, name: str):
    cfg = target()
    namespace = cfg["namespace"]
    return {
        "btType": "BTMFeature-134",
        "namespace": namespace,
        "name": name,
        "suppressed": False,
        "featureType": cfg["featureType"],
        "subFeatures": [],
        "returnAfterSubfeatures": False,
        "parameterLibraries": [],
        "parameters": [
            {
                "btType": "BTMParameterEnum-145", "namespace": namespace,
                "enumName": "ITSIndexButton", "value": button, "parameterId": "button",
            },
            {
                "btType": "BTMParameterEnum-145", "namespace": namespace,
                "enumName": "ITSIndexStage", "value": stage, "parameterId": "stage",
            },
        ],
    }


def add(button: str, stage: str, name: str):
    tree = features()
    payload = {
        "feature": feature(button, stage, name),
        "serializationVersion": tree.get("serializationVersion"),
        "sourceMicroversion": tree.get("sourceMicroversion"),
        "rejectMicroversionSkew": True,
    }
    result = api.request(
        "POST", f"partstudios/d/{api.DID}/w/{api.WID}/e/{api.EID}/features", payload
    )
    return result.get("feature", {}).get("featureId")


def step(button: str, stage: str, name: str):
    before = health()
    feature_id = add(button, stage, name)
    after = None
    for _ in range(30):
        time.sleep(2)
        after = health()
        if after["complete"] and after["microversion"] != before["microversion"]:
            break
    assert after is not None
    ids = {part_id for part_id, _ in after["solids"]}
    expected_delta = 1 if stage == "SPACER" else 0
    assembly = assembly_health()
    ok = bool(
        not after["bad"]
        and after["complete"]
        and len(after["solids"]) == len(before["solids"]) + expected_delta
        and {"JaD", "JfD", "RWID", "RZKD"}.issubset(ids)
        and assembly["instances"] == 25
        and assembly["active"] == 25
        and assembly["occurrences"] == 25
        and not assembly["rootMismatch"]
    )
    result = {
        "button": button,
        "stage": stage,
        "featureId": feature_id,
        "ok": ok,
        "beforeSolidCount": len(before["solids"]),
        "afterSolidCount": len(after["solids"]),
        "health": after,
        "assembly": assembly,
    }
    print(json.dumps(result, ensure_ascii=True))
    if not ok:
        raise RuntimeError(f"Atomic gate failed: {json.dumps(result, ensure_ascii=True)[:2000]}")
    return result


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: run_its1105_index.py upload|health|add BUTTON STAGE NAME")
    command = sys.argv[1]
    if command == "upload":
        print(json.dumps(upload(), ensure_ascii=True))
    elif command == "health":
        print(json.dumps({"partStudio": health(), "assembly": assembly_health()}, ensure_ascii=True))
    elif command == "add":
        step(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit("unknown command")


if __name__ == "__main__":
    main()
