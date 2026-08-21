"""Cache frozen INDEX_FINAL_VALIDATED meshes (HTTP GET only).

This helper has no POST/PUT/PATCH/DELETE implementation.  It reads the fixed
version and explicit ``configuration=default`` and writes only local JSON
files under ``cad_dump`` for geometric clearance analysis.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parent.parent
DID = "a21e64f36bc61df760d4587c"
VID = "03ede76e83b5c865d9a69c35"
EID = "425d9199b59cfb1efd9ddc35"
CONFIGURATION = "default"
PARTS = {
    "INDEX_FINAL_JaD": "JaD",
    "INDEX_FINAL_JfD": "JfD",
    "INDEX_FINAL_RWID": "RWID",
    "INDEX_FINAL_RZKD": "RZKD",
}


def load_env() -> None:
    for raw in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_tessellation(part_id: str) -> dict:
    base = os.environ.get("ONSHAPE_BASE_URL", "https://cad.onshape.com/api/v6").rstrip("/")
    params = urllib.parse.urlencode(
        {
            "configuration": CONFIGURATION,
            "angleTolerance": "0.09",
            "chordTolerance": "0.10",
            "partId": part_id,
            "outputFaceAppearances": "false",
        }
    )
    url = f"{base}/partstudios/d/{DID}/v/{VID}/e/{EID}/tessellatedfaces?{params}"
    token = base64.b64encode(
        f"{os.environ['ONSHAPE_ACCESS_KEY']}:{os.environ['ONSHAPE_SECRET_KEY']}".encode()
    ).decode()
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"Accept": "application/json", "Authorization": f"Basic {token}"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def flatten(name: str, part_id: str, data: dict) -> dict:
    tris, normals = [], []
    for body in data.get("bodies", []):
        for face in body.get("faces", []):
            for facet in face.get("facets", []):
                vertices = facet.get("vertices", [])
                if len(vertices) != 3:
                    continue
                tris.append(
                    [[float(p[axis]) * 1000.0 for axis in ("x", "y", "z")] for p in vertices]
                )
                normal = facet.get("normal") or {}
                normals.append([float(normal.get(axis, 0.0)) for axis in ("x", "y", "z")])
    return {
        "name": name,
        "partId": part_id,
        "source": {
            "documentId": DID,
            "versionId": VID,
            "elementId": EID,
            "configuration": CONFIGURATION,
            "method": "GET",
        },
        "tris": tris,
        "normals": normals,
    }


def main() -> None:
    load_env()
    out_dir = ROOT / "cad_dump"
    out_dir.mkdir(exist_ok=True)
    for name, part_id in PARTS.items():
        payload = flatten(name, part_id, get_tessellation(part_id))
        path = out_dir / f"mesh_{name}.json"
        path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        print(f"GET {name:<16} partId={part_id:<5} triangles={len(payload['tris']):>6} -> {path}")


if __name__ == "__main__":
    main()
