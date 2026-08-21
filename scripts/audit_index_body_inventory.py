"""Read-only INDEX final body inventory audit.

Only HTTP GET is implemented.  The two immutable Onshape versions below are
compared with the same endpoints, filters, tolerances, and hashing rules.
"""
from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
import zlib


ROOT = Path(__file__).resolve().parent.parent
DID = "a21e64f36bc61df760d4587c"
EID = "425d9199b59cfb1efd9ddc35"
ASSEMBLY_EID = "250f706cb675e635b8d344c4"
VERSIONS = {
    "shared": "6703cd9cbd0d5e321ac10b87",
    "final": "03ede76e83b5c865d9a69c35",
}
ANGLE_TOLERANCE = 0.09
CHORD_TOLERANCE = 0.1
BREP_AUDIT_PARTS = ("JfD", "RWID", "RYDD")
CONFIGURATION = "default"


def load_env() -> None:
    for raw in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
BASE = os.environ.get("ONSHAPE_BASE_URL", "https://cad.onshape.com/api/v6").rstrip("/")
TOKEN = base64.b64encode(
    f"{os.environ['ONSHAPE_ACCESS_KEY']}:{os.environ['ONSHAPE_SECRET_KEY']}".encode()
).decode()


def get_json(path: str, params: list[tuple[str, str]] | None = None, timeout: int = 300):
    """Issue an authenticated GET.  No write-capable method exists in this file."""
    query = urllib.parse.urlencode(params or [])
    url = f"{BASE}/{path.lstrip('/')}" + (f"?{query}" if query else "")
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"Accept": "application/json", "Authorization": f"Basic {TOKEN}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def version_path(kind: str, version_id: str, suffix: str = "") -> str:
    tail = f"/{suffix.lstrip('/')}" if suffix else ""
    return f"{kind}/d/{DID}/v/{version_id}/e/{EID}{tail}"


def nominal_volume_mm3(version_id: str, part_id: str) -> float:
    data = get_json(
        version_path("partstudios", version_id, "massproperties"),
        [("configuration", CONFIGURATION), ("partId", part_id)],
    )
    return data["bodies"]["-all-"]["volume"][0] * 1_000_000_000.0


def canonical_tessellation(version_id: str, part_id: str) -> dict:
    data = get_json(
        version_path("partstudios", version_id, "tessellatedfaces"),
        [
            ("configuration", CONFIGURATION),
            ("angleTolerance", str(ANGLE_TOLERANCE)),
            ("chordTolerance", str(CHORD_TOLERANCE)),
            ("partId", part_id),
            ("outputFaceAppearances", "false"),
        ],
    )
    triangles = []
    vertices_flat = []
    for body in data.get("bodies", []):
        for face in body.get("faces", []):
            for facet in face.get("facets", []):
                vertices = facet.get("vertices", [])
                if len(vertices) != 3:
                    continue
                triangle = []
                for vertex in vertices:
                    point = tuple(round(float(vertex[axis]), 12) for axis in ("x", "y", "z"))
                    triangle.append(point)
                    vertices_flat.append(point)
                triangles.append(tuple(sorted(triangle)))
    triangles.sort()
    encoded = json.dumps(triangles, separators=(",", ":")).encode()
    bbox = None
    if vertices_flat:
        bbox = {
            "minMm": [min(point[i] for point in vertices_flat) * 1000.0 for i in range(3)],
            "maxMm": [max(point[i] for point in vertices_flat) * 1000.0 for i in range(3)],
        }
    return {
        "triangles": len(triangles),
        "fingerprint": hashlib.sha256(encoded).hexdigest(),
        "bbox": bbox,
    }


def normalize_brep(value, digits: int):
    if isinstance(value, dict):
        return {
            key: normalize_brep(child, digits)
            for key, child in sorted(value.items())
            if key != "btType"
        }
    if isinstance(value, list):
        normalized = [normalize_brep(child, digits) for child in value]
        if normalized and all(isinstance(child, dict) and "id" in child for child in normalized):
            normalized.sort(key=lambda child: child["id"])
        return normalized
    if isinstance(value, float):
        rounded = round(value, digits)
        return 0.0 if rounded == 0 else rounded
    return value


def bodydetails_fingerprint(version_id: str, part_id: str) -> dict:
    data = get_json(
        f"parts/d/{DID}/v/{version_id}/e/{EID}/partid/{part_id}/bodydetails",
        [("configuration", CONFIGURATION)],
    )
    body = data["bodies"][0]
    fingerprints = {}
    for digits in (12, 9, 8, 7, 6):
        encoded = json.dumps(
            normalize_brep(body, digits), sort_keys=True, separators=(",", ":")
        ).encode()
        fingerprints[str(digits)] = hashlib.sha256(encoded).hexdigest()
    return {
        "bodyId": body.get("id"),
        "vertices": len(body.get("vertices", [])),
        "edges": len(body.get("edges", [])),
        "faces": len(body.get("faces", [])),
        "fingerprintsByMeterDigits": fingerprints,
    }


def decode_query(part_query: str) -> str:
    match = re.search(r'qCompressed\(1\.0,"([^"]+)"', part_query or "")
    if not match:
        return part_query or ""
    token = match.group(1)
    if "$" not in token:
        return part_query or ""
    encoded = token.split("$", 1)[1]
    encoded += "=" * ((4 - len(encoded) % 4) % 4)
    try:
        return zlib.decompress(base64.b64decode(encoded)).decode(errors="replace")
    except (ValueError, zlib.error):
        return part_query or ""


def query_feature_ids(part_query: str, features: list[dict]) -> list[str]:
    decoded = decode_query(part_query)
    return [feature["featureId"] for feature in features if feature.get("featureId") in decoded]


def feature_health(version_id: str) -> tuple[dict, dict]:
    tree = get_json(
        version_path("partstudios", version_id, "features"),
        [("configuration", CONFIGURATION), ("noSketchGeometry", "true")],
    )
    counts: dict[str, int] = {}
    for state in tree.get("featureStates", {}).values():
        status = state.get("featureStatus", "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    suppressed = [
        {"index": index, "name": feature.get("name"), "featureId": feature.get("featureId")}
        for index, feature in enumerate(tree.get("features", []))
        if feature.get("suppressed")
    ]
    return tree, {
        "featureCount": len(tree.get("features", [])),
        "stateCounts": counts,
        "isComplete": tree.get("isComplete"),
        "rollbackIndex": tree.get("rollbackIndex"),
        "sourceMicroversion": tree.get("sourceMicroversion"),
        "suppressed": suppressed,
    }


def assembly_audit(version_id: str) -> dict:
    data = get_json(
        f"assemblies/d/{DID}/v/{version_id}/e/{ASSEMBLY_EID}",
        [("configuration", CONFIGURATION)],
    )
    root = data["rootAssembly"]
    active = {item["id"] for item in root.get("instances", []) if not item.get("suppressed")}
    occurrence_roots = {
        item["path"][0] for item in root.get("occurrences", []) if item.get("path")
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
        "activeInstances": len(active),
        "occurrences": len(root.get("occurrences", [])),
        "suppressedInstances": len(root.get("instances", [])) - len(active),
        "danglingIds": dangling,
        "danglingCount": len(dangling),
    }


def collect_version(label: str, version_id: str) -> dict:
    parts_all = get_json(
        version_path("parts", version_id), [("configuration", CONFIGURATION)]
    )
    solids = [part for part in parts_all if part.get("bodyType") == "solid"]
    wires = [part for part in parts_all if part.get("bodyType") == "wire"]
    tree, health = feature_health(version_id)
    features = tree.get("features", [])
    feature_by_id = {feature.get("featureId"): feature for feature in features}

    jobs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for part in solids:
            part_id = part["partId"]
            jobs.append((part, executor.submit(nominal_volume_mm3, version_id, part_id),
                         executor.submit(canonical_tessellation, version_id, part_id)))
        inventory = []
        for part, volume_future, tess_future in jobs:
            feature_ids = query_feature_ids(part.get("partQuery", ""), features)
            inventory.append({
                "name": part.get("name"),
                "partId": part["partId"],
                "ordinal": part.get("ordinal"),
                "bodyType": part.get("bodyType"),
                "volumeMm3": volume_future.result(),
                "tessellation": tess_future.result(),
                "queryFeatureIds": feature_ids,
                "queryFeatures": [
                    {
                        "featureId": feature_id,
                        "name": feature_by_id[feature_id].get("name"),
                        "featureType": feature_by_id[feature_id].get("featureType"),
                    }
                    for feature_id in feature_ids
                ],
            })
    inventory.sort(key=lambda item: item["ordinal"])
    return {
        "label": label,
        "versionId": version_id,
        "configuration": CONFIGURATION,
        "endpoint": f"GET /parts/d/{DID}/v/{{versionId}}/e/{EID}",
        "countRule": 'bodyType == "solid"',
        "allPartRecords": len(parts_all),
        "solidCount": len(solids),
        "wireCount": len(wires),
        "wireParts": [{"name": part.get("name"), "partId": part.get("partId")} for part in wires],
        "health": health,
        "assembly": assembly_audit(version_id),
        "inventory": inventory,
    }


def main() -> None:
    shared = collect_version("INDEX_SHARED_RET_FINAL", VERSIONS["shared"])
    final = collect_version("INDEX_FINAL_VALIDATED", VERSIONS["final"])
    shared_by_id = {part["partId"]: part for part in shared["inventory"]}
    final_by_id = {part["partId"]: part for part in final["inventory"]}
    shared_ids = set(shared_by_id)
    final_ids = set(final_by_id)
    changed = []
    for part_id in sorted(shared_ids & final_ids):
        before = shared_by_id[part_id]
        after = final_by_id[part_id]
        volume_delta = after["volumeMm3"] - before["volumeMm3"]
        fingerprint_changed = (
            before["tessellation"]["fingerprint"] != after["tessellation"]["fingerprint"]
        )
        if fingerprint_changed or abs(volume_delta) > 1e-6:
            changed.append({
                "partId": part_id,
                "name": after["name"],
                "volumeBeforeMm3": before["volumeMm3"],
                "volumeAfterMm3": after["volumeMm3"],
                "volumeDeltaMm3": volume_delta,
                "fingerprintChanged": fingerprint_changed,
                "trianglesBefore": before["tessellation"]["triangles"],
                "trianglesAfter": after["tessellation"]["triangles"],
            })
    report = {
        "auditMode": "READ_ONLY_GET_ONLY",
        "tessellationRule": {
            "angleTolerance": ANGLE_TOLERANCE,
            "chordTolerance": CHORD_TOLERANCE,
            "canonicalization": "round coordinates to 1e-12 m; sort vertices and triangles; SHA-256",
        },
        "shared": shared,
        "final": final,
        "diff": {
            "added": sorted(final_ids - shared_ids),
            "removed": sorted(shared_ids - final_ids),
            "changed": changed,
        },
    }
    output = ROOT / "cad_dump" / "index_final_body_inventory_audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    print(f"solid {shared['solidCount']} -> {final['solidCount']}")
    print(f"added={report['diff']['added']} removed={report['diff']['removed']}")
    print(f"changed={[item['partId'] for item in report['diff']['changed']]}")


if __name__ == "__main__":
    main()
