"""INDEX retainer 원자 실행기 (승인된 사본 전용)."""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from onshape.client import BASE, session            # noqa: E402
from onshape import write_client as wc              # noqa: E402

DUMP = os.path.join(os.path.dirname(__file__), "..", "cad_dump")
URL = f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{wc.EID_JOYSTICK}/features"


def cfg():
    with open(os.path.join(DUMP, "ret_target.json"), encoding="utf-8") as f:
        return json.load(f)


def solids():
    return [(x["partId"], x["name"]) for x in session().get(
        f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{wc.EID_JOYSTICK}", timeout=120).json()]


def add(stage, name, body_id=""):
    c = cfg()
    f = {"btType": "BTMFeature-134", "namespace": c["namespace"], "name": name,
         "suppressed": False, "featureType": c["featureType"], "subFeatures": [],
         "returnAfterSubfeatures": False, "parameterLibraries": [],
         "parameters": [
             {"btType": "BTMParameterEnum-145", "namespace": c["namespace"],
              "enumName": "RetStage", "value": stage, "parameterId": "stage"},
             {"btType": "BTMParameterString-149", "value": body_id,
              "parameterId": "bodyId"}]}
    r = session().post(URL, json={"feature": f, "rejectMicroversionSkew": False}, timeout=300)
    if r.status_code >= 400:
        return None, None, r.status_code, r.text[:400]
    j = r.json()
    return (j.get("featureState", {}).get("featureStatus"),
            j.get("feature", {}).get("featureId"), r.status_code, "")


def step(stage, name, body_id="", pause=14):
    before = solids()
    st, fid, code, err = add(stage, name, body_id)
    time.sleep(pause)
    after = solids()
    ap = {p for p, _ in after}; bp = {p for p, _ in before}
    j1 = [p for p, n in after if n == "Joystick_1"]; j2 = [p for p, n in after if n == "Joystick_2"]
    ok = (st == "OK" and "JaD" in ap and "JfD" in ap and len(j1) == 1 and len(j2) == 1)
    print(f"  {name:<28} state={str(st):<6} id={fid}  solid {len(before)}->{len(after)}  "
          f"신규{sorted(ap-bp)} 소멸{sorted(bp-ap)}  J1={len(j1)} J2={len(j2)}  "
          f"{'OK' if ok else 'FAIL'}  {err}")
    return ok, fid
