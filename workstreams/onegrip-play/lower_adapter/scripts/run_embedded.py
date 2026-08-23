"""매립 짐벌 FeatureScript 실행기 (신규 Part Studio 전용).

    python lower_adapter/scripts/run_embedded.py vars
    python lower_adapter/scripts/run_embedded.py upload
    python lower_adapter/scripts/run_embedded.py add <STAGE> <name> [housingId]
    python lower_adapter/scripts/run_embedded.py parts

주의: 이 문서의 `GET /features` 는 현재 429 (Retry-After 약 22.5 h) 다.
      따라서 feature 트리를 읽지 않고 POST 응답과 `/parts` 로만 상태를 확인한다.
      POST 는 sourceMicroversion 없이 보낸다 (rejectMicroversionSkew=false).
상체 Joystick Part Studio 는 대상이 아니며 가드로 차단한다.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from onshape.client import BASE, session            # noqa: E402
from onshape import write_client as wc              # noqa: E402

OUT = os.path.join(ROOT, "lower_adapter", "cad_dump")
FS_PATH = os.path.join(ROOT, "lower_adapter", "cad", "OneGrip_EmbeddedGimbal.fs")
TARGET = os.path.join(OUT, "embedded_target.json")

VARS = [("pivot_depth", "15 mm", "LENGTH"),
        ("gimbal_travel", "10 deg", "ANGLE"),
        ("seat_recess", "6 mm", "LENGTH"),
        ("axis1_radius", "29 mm", "LENGTH"),
        ("axis2_radius", "32 mm", "LENGTH"),
        ("yoke_wall", "2.5 mm", "LENGTH")]


def target():
    return json.load(io.open(TARGET, encoding="utf-8"))


def save(t):
    json.dump(t, io.open(TARGET, "w", encoding="utf-8"), indent=1)


def guard(eid):
    if eid == wc.EID_JOYSTICK:
        raise RuntimeError("차단: 상체 Joystick Part Studio 는 대상이 아니다")
    return eid


def post(feature, eid):
    """GET /features 없이 feature 를 append 한다 (429 우회)."""
    guard(eid)
    wc._guard(wc.DID, wc.WID)
    r = session().post(f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{eid}/features",
                       json={"feature": feature, "rejectMicroversionSkew": False}, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"POST 실패 {r.status_code}: {r.text[:400]}")
    j = r.json()
    return (j.get("feature", {}).get("featureId"),
            j.get("featureState", {}).get("featureStatus"))


def local_var_template():
    j = json.load(io.open(os.path.join(ROOT, "cad_dump", "features_Joystick.json"),
                          encoding="utf-8"))
    src = next(f for f in j["features"] if f.get("featureType") == "assignVariable")
    wc._VAR_TEMPLATE = wc._strip_ids(src)


def make_vars(skip=0):
    local_var_template()
    t = target()
    ids = t.get("varIds", {})
    for n, v, ty in VARS[skip:]:
        fid, st = post(wc.assign_variable(n, v, ty), t["ps_eid"])
        ids[n] = fid
        print(f"  #{n:<14s} = {v:<8s} {st}  {fid}")
    t["varIds"] = ids
    save(t)


def upload():
    t = target()
    wc.set_feature_studio_contents(t["fs_eid"], io.open(FS_PATH, encoding="utf-8").read())
    spec = session().get(
        f"{BASE}/featurestudios/d/{wc.DID}/w/{wc.WID}/e/{t['fs_eid']}/featurespecs",
        timeout=180).json()
    if not spec.get("featureSpecs"):
        raise RuntimeError("컴파일 실패:\n" + json.dumps(spec, indent=1)[:1500])
    s = spec["featureSpecs"][0]
    t["namespace"], t["featureType"] = s["namespace"], s["featureType"]
    save(t)
    return t["namespace"], t["featureType"]


def custom(stage, name, ns, ft, housing_id=""):
    return {"btType": "BTMFeature-134", "namespace": ns, "name": name,
            "suppressed": False, "featureType": ft, "subFeatures": [],
            "returnAfterSubfeatures": False, "parameterLibraries": [],
            "parameters": [{"btType": "BTMParameterEnum-145", "namespace": ns,
                            "enumName": "EmbStage", "value": stage, "parameterId": "stage"},
                           {"btType": "BTMParameterString-149", "value": housing_id,
                            "parameterId": "housingId"}]}


def add(stage, name, housing_id=""):
    t = target()
    ns, ft = t.get("namespace"), t.get("featureType")
    if ns is None:
        ns, ft = upload()
    fid, st = post(custom(stage, name, ns, ft, housing_id), t["ps_eid"])
    print(f"  {name:<24s} post={st}  featureId={fid}")
    t.setdefault("stageIds", {})[stage] = fid
    save(t)
    return fid


def parts():
    t = target()
    r = session().get(f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{t['ps_eid']}",
                      params=[("configuration", "default")], timeout=180)
    if r.status_code != 200:
        print("parts GET", r.status_code, r.headers.get("Retry-After"))
        return []
    p = r.json()
    sol = [x for x in p if x.get("bodyType") == "solid"]
    print(f"  records {len(p)}  solid {len(sol)}  wire {len(p) - len(sol)}")
    for x in sol:
        print("   ", x["partId"], x.get("name"))
    return sol


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "vars":
        make_vars(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    elif cmd == "upload":
        print("ns/ft:", upload())
    elif cmd == "add":
        add(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    elif cmd == "parts":
        parts()
