"""Guarded atomic runner for THUMB MODULE RESEATING stage B.

The source Part Studio is the user-owned OneGrip_Play_V1 workspace only.
This runner deliberately exposes no shell-interface stage yet.  The old/new
opening relationship must be inspected after the rigid translation succeeds.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_i4_retainer as api  # guarded standard-library request path; noqa: E402


SOURCE = ROOT / "cad" / "OneGrip_Thumb_Module_Reseat.fs"
TARGET = ROOT / "cad_dump" / "thumb_module_reseat_target.json"
ASSEMBLY_EID = "250f706cb675e635b8d344c4"
EXPECTED_SOLIDS = 30
REQUIRED_IDS = {
    "JaD", "JfD", "RWID", "RZKD", "RYDD",
    "RAED", "RAEH", "RAEL", "RBED", "RBEH", "RBEL", "RDED", "RDEH",
}


def request(method: str, path: str, body=None):
    if api.DID != "a21e64f36bc61df760d4587c" or api.WID != "ef6a7b3ccc45186203e4d2ca":
        raise RuntimeError("THUMB RESEAT write guard rejected DID/WID")
    return api.request(method, path, body)


def tree():
    return request(
        "GET",
        f"partstudios/d/{api.DID}/w/{api.WID}/e/{api.EID}/features"
        "?configuration=default&noSketchGeometry=true",
    )


def parts():
    return request(
        "GET",
        f"parts/d/{api.DID}/w/{api.WID}/e/{api.EID}?configuration=default",
    )


def assembly_health():
    data = request(
        "GET",
        f"assemblies/d/{api.DID}/w/{api.WID}/e/{ASSEMBLY_EID}?configuration=default",
    )
    root = data["rootAssembly"]
    active = {row["id"] for row in root.get("instances", []) if not row.get("suppressed")}
    occurrence_roots = {
        row["path"][0] for row in root.get("occurrences", []) if row.get("path")
    }
    referenced = set()

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "matedOccurrence" and isinstance(child, list) and child:
                    referenced.add(child[0])
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(root.get("features", []))
    dangling = sorted((active ^ occurrence_roots) | (referenced - active))
    return {
        "instances": len(root.get("instances", [])),
        "active": len(active),
        "occurrences": len(root.get("occurrences", [])),
        "dangling": dangling,
    }


def health():
    feature_tree = tree()
    state_counts = {}
    bad = {}
    for feature_id, state in feature_tree.get("featureStates", {}).items():
        status = state.get("featureStatus", "UNKNOWN")
        state_counts[status] = state_counts.get(status, 0) + 1
        if status not in ("OK", "INFO"):
            bad[feature_id] = status
    solids = [row for row in parts() if row.get("bodyType") == "solid"]
    return {
        "microversion": feature_tree.get("sourceMicroversion"),
        "serializationVersion": feature_tree.get("serializationVersion"),
        "isComplete": feature_tree.get("isComplete"),
        "featureCount": len(feature_tree.get("features", [])),
        "stateCounts": state_counts,
        "bad": bad,
        "solidCount": len(solids),
        "solidIds": sorted(row.get("partId") for row in solids),
    }


def assert_gate(report):
    assembly = report["assembly"]
    studio = report["partStudio"]
    ids = set(studio["solidIds"])
    ok = bool(
        studio["isComplete"]
        and not studio["bad"]
        and studio["solidCount"] == EXPECTED_SOLIDS
        and REQUIRED_IDS.issubset(ids)
        and assembly["instances"] == 25
        and assembly["active"] == 25
        and assembly["occurrences"] == 25
        and not assembly["dangling"]
    )
    if not ok:
        raise RuntimeError("THUMB RESEAT atomic gate failed: " + json.dumps(report)[:3000])


def full_health():
    report = {"partStudio": health(), "assembly": assembly_health()}
    assert_gate(report)
    return report


def checkpoint(name: str):
    baseline = full_health()
    result = request(
        "POST",
        f"documents/{api.DID}/versions",
        {
            "documentId": api.DID,
            "workspaceId": api.WID,
            "name": name,
            "description": (
                "Pre-write checkpoint for rigid original thumb-module reseating. "
                "Baseline: 30 solids, JaD/JfD/RWID/RZKD identities, assembly 25/25."
            ),
        },
    )
    return {"baseline": baseline, "version": result}


def init_feature_studio():
    if TARGET.exists():
        raise RuntimeError(f"Target already exists: {TARGET}")
    result = request(
        "POST",
        f"featurestudios/d/{api.DID}/w/{api.WID}",
        {"name": "OneGrip THUMB Module Reseat"},
    )
    eid = result.get("id") or result.get("elementId")
    if not eid:
        raise RuntimeError("Feature Studio creation returned no element id")
    TARGET.write_text(json.dumps({"eid": eid}, indent=2), encoding="utf-8")
    return {"eid": eid}


def upload():
    config = json.loads(TARGET.read_text(encoding="utf-8"))
    request(
        "POST",
        f"featurestudios/d/{api.DID}/w/{api.WID}/e/{config['eid']}",
        {"contents": SOURCE.read_text(encoding="utf-8")},
    )
    specs = request(
        "GET",
        f"featurestudios/d/{api.DID}/w/{api.WID}/e/{config['eid']}/featurespecs",
    )
    rows = specs.get("featureSpecs", [])
    if len(rows) != 1:
        raise RuntimeError("FeatureScript compile/spec gate failed: " + json.dumps(specs)[:2000])
    config.update({"namespace": rows[0]["namespace"], "featureType": rows[0]["featureType"]})
    TARGET.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config


def add_transform():
    before = full_health()
    config = upload()
    current = tree()
    feature = {
        "btType": "BTMFeature-134",
        "namespace": config["namespace"],
        "name": "THUMB B rigid module translation (0,+5.5,-6)",
        "suppressed": False,
        "featureType": config["featureType"],
        "subFeatures": [],
        "returnAfterSubfeatures": False,
        "parameterLibraries": [],
        "parameters": [
            {
                "btType": "BTMParameterEnum-145",
                "namespace": config["namespace"],
                "enumName": "ThumbReseatStage",
                "value": "TRANSFORM",
                "parameterId": "stage",
            }
        ],
    }
    payload = {
        "feature": feature,
        "serializationVersion": current.get("serializationVersion"),
        "sourceMicroversion": current.get("sourceMicroversion"),
        "rejectMicroversionSkew": True,
    }
    result = request(
        "POST",
        f"partstudios/d/{api.DID}/w/{api.WID}/e/{api.EID}/features",
        payload,
    )
    after = None
    for _ in range(30):
        time.sleep(2)
        try:
            after = full_health()
        except RuntimeError:
            continue
        if after["partStudio"]["microversion"] != before["partStudio"]["microversion"]:
            break
    if after is None:
        raise RuntimeError("No post-transform health result")
    assert_gate(after)
    return {
        "featureId": result.get("feature", {}).get("featureId"),
        "translationMm": [0.0, 5.5, -6.0],
        "before": before,
        "after": after,
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: run_thumb_module_reseat.py health|checkpoint NAME|init|transform")
    command = sys.argv[1]
    if command == "health":
        result = full_health()
    elif command == "checkpoint":
        result = checkpoint(sys.argv[2])
    elif command == "init":
        result = init_feature_studio()
    elif command == "transform":
        result = add_transform()
    else:
        raise SystemExit("unknown command")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
