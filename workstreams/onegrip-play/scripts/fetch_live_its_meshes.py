"""GET-only cache of the live approved workspace for ITS validation."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parent.parent
DID = "a21e64f36bc61df760d4587c"
WID = "ef6a7b3ccc45186203e4d2ca"
EID = "425d9199b59cfb1efd9ddc35"
PARTS = {"ITS_LIVE_JaD": "JaD", "ITS_LIVE_JfD": "JfD",
         "ITS_LIVE_RWID": "RWID", "ITS_LIVE_RZKD": "RZKD"}


def load_env():
    for raw in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#") and "=" in raw:
            key, value = raw.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get(part_id: str):
    base = os.environ.get("ONSHAPE_BASE_URL", "https://cad.onshape.com/api/v6").rstrip("/")
    query = urllib.parse.urlencode({
        "configuration": "default", "angleTolerance": "0.09", "chordTolerance": "0.10",
        "partId": part_id, "outputFaceAppearances": "false",
    })
    token = base64.b64encode(
        f"{os.environ['ONSHAPE_ACCESS_KEY']}:{os.environ['ONSHAPE_SECRET_KEY']}".encode()
    ).decode()
    request = urllib.request.Request(
        f"{base}/partstudios/d/{DID}/w/{WID}/e/{EID}/tessellatedfaces?{query}",
        method="GET", headers={"Accept": "application/json", "Authorization": f"Basic {token}"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def flatten(name: str, part_id: str, data):
    triangles = []
    for body in data.get("bodies", []):
        for face in body.get("faces", []):
            for facet in face.get("facets", []):
                vertices = facet.get("vertices", [])
                if len(vertices) == 3:
                    triangles.append([
                        [float(point[axis]) * 1000.0 for axis in ("x", "y", "z")]
                        for point in vertices
                    ])
    return {"name": name, "partId": part_id,
            "source": {"documentId": DID, "workspaceId": WID, "elementId": EID,
                       "configuration": "default", "method": "GET"},
            "tris": triangles}


def main():
    load_env()
    for name, part_id in PARTS.items():
        payload = flatten(name, part_id, get(part_id))
        path = ROOT / "cad_dump" / f"mesh_{name}.json"
        path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        print(f"GET {name} {part_id} triangles={len(payload['tris'])}")


if __name__ == "__main__":
    main()
