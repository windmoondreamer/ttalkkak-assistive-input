"""하부 어댑터 FeatureScript 원자 실행기 (승인된 사본의 신규 Part Studio 전용).

    python lower_adapter/scripts/run_adapter.py upload
    python lower_adapter/scripts/run_adapter.py add <STAGE> <name>
    python lower_adapter/scripts/run_adapter.py state
    python lower_adapter/scripts/run_adapter.py drop          # 이 스크립트가 만든 피처만 제거

대상 Part Studio 는 lower_adapter/cad_dump/adapter_target.json 의 ps_eid 하나뿐이다.
Joystick Part Studio(상체)에는 어떤 요청도 보내지 않는다.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from onshape.client import BASE, session            # noqa: E402
from onshape import write_client as wc              # noqa: E402

OUT = os.path.join(ROOT, "lower_adapter", "cad_dump")
FS_PATH = os.path.join(ROOT, "lower_adapter", "cad", "OneGrip_LowerAdapter.fs")
TARGET = os.path.join(OUT, "adapter_target.json")
UPPER_EID = wc.EID_JOYSTICK      # 절대 대상으로 쓰지 않는다


def target():
    with open(TARGET, encoding="utf-8") as f:
        return json.load(f)


def _guard_eid(eid):
    if eid == UPPER_EID:
        raise RuntimeError("차단: 상체 Joystick Part Studio 는 이 스크립트의 대상이 아니다")
    return eid


def upload():
    t = target()
    with open(FS_PATH, encoding="utf-8") as f:
        wc.set_feature_studio_contents(t["fs_eid"], f.read())
    spec = session().get(
        f"{BASE}/featurestudios/d/{wc.DID}/w/{wc.WID}/e/{t['fs_eid']}/featurespecs",
        timeout=180).json()
    if not spec.get("featureSpecs"):
        raise RuntimeError("컴파일 실패:\n" + json.dumps(spec, indent=1)[:2000])
    s = spec["featureSpecs"][0]
    t["namespace"], t["featureType"] = s["namespace"], s["featureType"]
    with open(TARGET, "w", encoding="utf-8") as f:
        json.dump(t, f, indent=1)
    return t["namespace"], t["featureType"]


def custom_feature(stage, name, ns, ft, cradle_id="", wedge_id=""):
    return {"btType": "BTMFeature-134", "namespace": ns, "name": name,
            "suppressed": False, "featureType": ft, "subFeatures": [],
            "returnAfterSubfeatures": False, "parameterLibraries": [],
            "parameters": [{"btType": "BTMParameterEnum-145", "namespace": ns,
                            "enumName": "AdpStage", "value": stage,
                            "parameterId": "stage"},
                           {"btType": "BTMParameterString-149", "value": cradle_id,
                            "parameterId": "cradleId"},
                           {"btType": "BTMParameterString-149", "value": wedge_id,
                            "parameterId": "wedgeId"}]}


def state():
    t = target()
    eid = _guard_eid(t["ps_eid"])
    j = wc.ps_features(eid)
    st = j.get("featureStates", {})
    bad = {k: v.get("featureStatus") for k, v in st.items()
           if v.get("featureStatus") not in ("OK", "INFO")}
    r = session().get(f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{eid}",
                      params=[("configuration", "default")], timeout=180)
    parts = r.json() if r.status_code == 200 else []
    solids = [p for p in parts if p.get("bodyType") == "solid"]
    return {"features": len(j["features"]), "isComplete": j.get("isComplete"),
            "bad": bad, "solids": len(solids),
            "parts": [(p["partId"], p.get("name")) for p in solids]}


def add(stage, name, cradle_id="", wedge_id=""):
    t = target()
    eid = _guard_eid(t["ps_eid"])
    ns, ft = t.get("namespace"), t.get("featureType")
    if ns is None:
        ns, ft = upload()
    res = wc.post_feature(custom_feature(stage, name, ns, ft, cradle_id, wedge_id), eid=eid)
    f = res.get("feature", {})
    return {"name": f.get("name"), "featureId": f.get("featureId"),
            "postState": res.get("featureState", {}).get("featureStatus"),
            "state": state()}


def drop():
    t = target()
    eid = _guard_eid(t["ps_eid"])
    j = wc.ps_features(eid)
    removed = []
    for f in list(j["features"]):
        if f.get("featureType", "").startswith("oneGripLowerAdapter"):
            wc.delete_feature(f["featureId"], eid=eid)
            removed.append(f["name"])
    return removed


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "upload":
        print("namespace/featureType:", upload())
    elif cmd == "add":
        print(json.dumps(add(*sys.argv[2:]), ensure_ascii=False, indent=1))
    elif cmd == "state":
        print(json.dumps(state(), ensure_ascii=False, indent=1))
    elif cmd == "drop":
        print("삭제:", drop())
        print(json.dumps(state(), ensure_ascii=False, indent=1))
