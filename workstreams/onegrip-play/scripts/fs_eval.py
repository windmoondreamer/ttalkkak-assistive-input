"""Part Studio 에서 FeatureScript 를 평가하고 결과를 파이썬 값으로 돌려준다 (읽기 전용 평가)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from onshape.client import BASE, session          # noqa: E402
from onshape import write_client as wc            # noqa: E402


def _flat(v):
    if not isinstance(v, dict):
        return v
    bt = v.get("btType", "")
    if "ValueMap" in bt:
        return {_flat(e["key"]): _flat(e["value"]) for e in v.get("value", [])}
    if "ValueArray" in bt:
        return [_flat(x) for x in v.get("value", [])]
    if "ValueNumber" in bt or "ValueString" in bt or "ValueBoolean" in bt:
        return v.get("value")
    if "ValueWithUnits" in bt:
        return v.get("value")
    if "value" in v:
        return _flat(v["value"])
    return v


def fs(script, rollback=None, eid=None):
    body = {"script": script}
    if rollback is not None:
        body["rollbackBarIndex"] = rollback
    r = session().post(
        f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{eid or wc.EID_JOYSTICK}/featurescript",
        json=body, timeout=300)
    j = r.json()
    if r.status_code >= 400 or "result" not in j:
        return {"_error": j.get("message") or r.text[:1500], "_status": r.status_code}
    return _flat(j["result"])
