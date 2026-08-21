"""Atomic I4 retainer runner for the approved OneGrip_Play_V1 workspace.

This runner is intentionally isolated from the frozen shared-retainer runner.
It uses only the Python standard library and accepts exactly the six I4 stages.
"""
import base64
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = ROOT / "cad_dump" / "i4_target.json"
SOURCE = ROOT / "cad" / "OneGrip_I4_Retainer.fs"

DID = "a21e64f36bc61df760d4587c"
WID = "ef6a7b3ccc45186203e4d2ca"
EID = "425d9199b59cfb1efd9ddc35"
FORBIDDEN_DID = "143d2aa6a2cf1c2ed82be979"


def load_env():
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


def request(method, path, body=None, timeout=300):
    if DID == FORBIDDEN_DID:
        raise RuntimeError("Original source document write is forbidden")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}/{path.lstrip('/')}", data=data, method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "Authorization": f"Basic {TOKEN}"})
    max_attempts = max(1, int(os.environ.get("ONEGRIP_ONSHAPE_MAX_ATTEMPTS", "6")))
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:1200]
            if exc.code == 429 and attempt < max_attempts - 1:
                retry_header = exc.headers.get("Retry-After")
                try:
                    delay = float(retry_header) if retry_header else 30.0 + 10.0 * attempt
                except ValueError:
                    delay = 30.0 + 10.0 * attempt
                time.sleep(min(max(delay, 5.0), 55.0))
                continue
            rate_headers = {
                key: value for key, value in exc.headers.items()
                if key.lower() in {
                    "retry-after", "x-rate-limit-limit", "x-rate-limit-remaining",
                    "x-rate-limit-reset", "x-ratelimit-limit", "x-ratelimit-remaining",
                    "x-ratelimit-reset",
                }
            }
            raise RuntimeError(
                f"HTTP {exc.code}: {detail}; rateHeaders={rate_headers}"
            ) from exc
    raise RuntimeError("request retry loop exhausted")


def features():
    return request("GET", f"partstudios/d/{DID}/w/{WID}/e/{EID}/features?noSketchGeometry=true")


def parts():
    return request("GET", f"parts/d/{DID}/w/{WID}/e/{EID}")


def health():
    tree = features()
    states = tree.get("featureStates", {})
    bad = {key: value.get("featureStatus") for key, value in states.items()
           if value.get("featureStatus") not in ("OK", "INFO")}
    solids = [(p.get("partId"), p.get("name")) for p in parts()
              if p.get("bodyType") == "solid"]
    return {"features": len(tree.get("features", [])), "bad": bad,
            "complete": tree.get("isComplete"), "solids": solids}


def target():
    return json.loads(TARGET.read_text(encoding="utf-8"))


def upload():
    cfg = target()
    request("POST", f"featurestudios/d/{DID}/w/{WID}/e/{cfg['eid']}",
            {"contents": SOURCE.read_text(encoding="utf-8")})
    spec = request("GET", f"featurestudios/d/{DID}/w/{WID}/e/{cfg['eid']}/featurespecs")
    rows = spec.get("featureSpecs", [])
    if not rows:
        raise RuntimeError(f"FeatureScript compile failed: {json.dumps(spec)[:1200]}")
    return {"namespace": rows[0]["namespace"], "featureType": rows[0]["featureType"]}


def feature(stage, name, body_id="", preload="NOMINAL"):
    cfg = target()
    ns = cfg["namespace"]
    return {
        "btType": "BTMFeature-134", "namespace": ns, "name": name,
        "suppressed": False, "featureType": cfg["featureType"],
        "subFeatures": [], "returnAfterSubfeatures": False, "parameterLibraries": [],
        "parameters": [
            {"btType": "BTMParameterEnum-145", "namespace": ns,
             "enumName": "I4RetStage", "value": stage, "parameterId": "stage"},
            {"btType": "BTMParameterString-149", "value": body_id, "parameterId": "bodyId"},
            {"btType": "BTMParameterEnum-145", "namespace": ns,
             "enumName": "I4Preload", "value": preload, "parameterId": "preload"},
        ],
    }


def add(stage, name, body_id="", preload="NOMINAL"):
    tree = features()
    payload = {
        "feature": feature(stage, name, body_id, preload),
        "serializationVersion": tree.get("serializationVersion"),
        "sourceMicroversion": tree.get("sourceMicroversion"),
        "rejectMicroversionSkew": True,
    }
    result = request("POST", f"partstudios/d/{DID}/w/{WID}/e/{EID}/features", payload)
    return result.get("feature", {}).get("featureId")


def step(stage, name, body_id="", preload="NOMINAL", pause=8):
    before = health()
    feature_id = add(stage, name, body_id, preload)
    time.sleep(pause)
    after = health()
    solid_ids = {pid for pid, _ in after["solids"]}
    ok = not after["bad"] and after["complete"] and "JaD" in solid_ids and "JfD" in solid_ids and "RWID" in solid_ids
    print(json.dumps({"stage": stage, "featureId": feature_id, "ok": ok,
                      "beforeSolidCount": len(before["solids"]),
                      "afterSolidCount": len(after["solids"]),
                      "bad": after["bad"], "solids": after["solids"]}, ensure_ascii=False))
    return ok, feature_id


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "upload":
        print(json.dumps(upload(), ensure_ascii=False))
    elif command == "health":
        print(json.dumps(health(), ensure_ascii=False))
    elif command == "add":
        stage, name = sys.argv[2], sys.argv[3]
        body_id = sys.argv[4] if len(sys.argv) > 4 else ""
        preload = sys.argv[5] if len(sys.argv) > 5 else "NOMINAL"
        ok, feature_id = step(stage, name, body_id, preload)
        if not ok:
            raise SystemExit(1)
        print(feature_id)
    else:
        raise SystemExit("usage: run_i4_retainer.py upload|health|add STAGE NAME [BODY_ID] [PRELOAD]")
