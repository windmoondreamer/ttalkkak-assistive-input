"""Read-only Onshape source probe for the approved LOWER15 Thumb audit.

This module intentionally exposes GET only.  It stores raw JSON responses only
inside thumb_onshape_source_audit/ and never exports or mutates CAD geometry.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

import requests


ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "raw"
sys.path.insert(0, str(ROOT))

from onshape.client import BASE, session  # noqa: E402


DID = "a21e64f36bc61df760d4587c"
WID = "ef6a7b3ccc45186203e4d2ca"
EID = "425d9199b59cfb1efd9ddc35"
CONFIGURATION = "default"


def get_json(client: requests.Session, label: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Issue one GET and persist a response envelope for reproducibility."""
    url = f"{BASE.rstrip('/')}/{path.lstrip('/')}"
    response = client.request("GET", url, params=params, timeout=120)
    envelope: dict[str, Any] = {
        "method": "GET",
        "url": response.url,
        "status": response.status_code,
        "contentType": response.headers.get("Content-Type"),
        "etag": response.headers.get("ETag"),
    }
    try:
        envelope["body"] = response.json()
    except ValueError:
        envelope["bodyText"] = response.text[:2000]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{label}.json").write_text(
        json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"GET {label}: HTTP {response.status_code} ({len(response.content)} bytes)")
    return envelope


def main() -> None:
    client = session()
    probes = (
        ("document", f"documents/{DID}", None),
        ("versions", f"documents/d/{DID}/versions", None),
        ("workspace_elements", f"documents/d/{DID}/w/{WID}/elements", None),
        ("workspace_parts", f"parts/d/{DID}/w/{WID}/e/{EID}", {"configuration": CONFIGURATION}),
        ("workspace_features", f"partstudios/d/{DID}/w/{WID}/e/{EID}/features", {"configuration": CONFIGURATION}),
        ("workspace_configuration", f"partstudios/d/{DID}/w/{WID}/e/{EID}/configuration", None),
        ("workspace_metadata", f"metadata/d/{DID}/w/{WID}/e/{EID}", {"configuration": CONFIGURATION}),
    )
    results = [get_json(client, label, path, params) for label, path, params in probes]
    if any(row["method"] != "GET" for row in results):
        raise RuntimeError("Non-GET method detected")
    print(f"base={BASE}; auth={'configured' if client.auth else 'anonymous'}")


if __name__ == "__main__":
    main()
