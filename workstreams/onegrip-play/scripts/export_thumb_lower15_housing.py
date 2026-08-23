"""GET-only export of the two final lower-15 external housing shells.

No CAD feature, part, workspace, or assembly data is modified.  The output is
two binary millimetre STL files plus a ZIP and a small verification manifest.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import struct
import urllib.error
import urllib.parse
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "exports" / "thumb_lower15_housing_mockup"
DID = "a21e64f36bc61df760d4587c"
WID = "ef6a7b3ccc45186203e4d2ca"
EID = "425d9199b59cfb1efd9ddc35"
CONFIGURATION = "default"
PARTS = {
    "OneGrip_lower15_housing_Joystick_1_JaD.stl": "JaD",
    "OneGrip_lower15_housing_Joystick_2_JfD.stl": "JfD",
}


def load_env() -> None:
    for raw in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_stl(part_id: str) -> bytes:
    base = os.environ.get("ONSHAPE_BASE_URL", "https://cad.onshape.com/api/v12").rstrip("/")
    params = urllib.parse.urlencode({
        "configuration": CONFIGURATION,
        "mode": "binary",
        "units": "millimeter",
        "angleTolerance": "0.09",
        "chordTolerance": "0.10",
    })
    url = f"{base}/parts/d/{DID}/w/{WID}/e/{EID}/partid/{part_id}/stl?{params}"
    token = base64.b64encode(
        f"{os.environ['ONSHAPE_ACCESS_KEY']}:{os.environ['ONSHAPE_SECRET_KEY']}".encode()
    ).decode()
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/octet-stream",
            "Authorization": f"Basic {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        retry_after = exc.headers.get("Retry-After")
        suffix = f" retry-after={retry_after}s" if retry_after else ""
        raise RuntimeError(f"Onshape STL GET failed: HTTP {exc.code}{suffix}") from exc


def binary_stl_triangle_count(data: bytes) -> int:
    if len(data) < 84:
        raise RuntimeError("STL response is shorter than the binary STL header")
    count = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + count * 50
    if expected != len(data):
        raise RuntimeError(f"binary STL size mismatch: expected {expected}, got {len(data)}")
    return count


def main() -> None:
    load_env()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": {
            "documentId": DID,
            "workspaceId": WID,
            "elementId": EID,
            "configuration": CONFIGURATION,
            "onshapeVersionName": "THUMB_LOWER15_HOUSING_V1",
            "method": "GET only",
        },
        "scope": "external housing shells only; controls and internals excluded",
        "parts": [],
    }
    written = []
    for filename, part_id in PARTS.items():
        data = get_stl(part_id)
        triangles = binary_stl_triangle_count(data)
        path = OUT / filename
        path.write_bytes(data)
        written.append(path)
        manifest["parts"].append({
            "filename": filename,
            "partId": part_id,
            "bytes": len(data),
            "triangles": triangles,
            "binaryStlLengthCheck": "PASS",
        })
        print(f"GET {part_id}: {triangles} triangles -> {path}")

    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    zip_path = OUT / "OneGrip_lower15_external_housing_mockup_STL.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in written:
            archive.write(path, path.name)
        archive.write(manifest_path, manifest_path.name)
    print(f"ZIP -> {zip_path}")


if __name__ == "__main__":
    main()
