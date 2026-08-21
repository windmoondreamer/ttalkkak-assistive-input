"""Feature Studio 업로드 + 커스텀 피처 추가/교체 도구 (승인된 사본 전용)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from onshape.client import BASE, session            # noqa: E402
from onshape import write_client as wc              # noqa: E402

DUMP = os.path.join(os.path.dirname(__file__), "..", "cad_dump")
FS_PATH = os.path.join(os.path.dirname(__file__), "..", "cad", "OneGrip_FingerButtons.fs")


def fs_eid():
    with open(os.path.join(DUMP, "fs_target.json"), encoding="utf-8") as f:
        return json.load(f)["fs_eid"]


def upload():
    eid = fs_eid()
    with open(FS_PATH, encoding="utf-8") as f:
        wc.set_feature_studio_contents(eid, f.read())
    spec = session().get(
        f"{BASE}/featurestudios/d/{wc.DID}/w/{wc.WID}/e/{eid}/featurespecs",
        timeout=180).json()
    if not spec.get("featureSpecs"):
        raise RuntimeError(f"컴파일 실패: {json.dumps(spec)[:800]}")
    s = spec["featureSpecs"][0]
    with open(os.path.join(DUMP, "fs_target.json"), "w", encoding="utf-8") as f:
        json.dump({"fs_eid": eid, "namespace": s["namespace"],
                   "featureType": s["featureType"]}, f, indent=1)
    return s["namespace"], s["featureType"]


def custom_feature(stage, name, ns, ft):
    return {"btType": "BTMFeature-134", "namespace": ns, "name": name,
            "suppressed": False, "featureType": ft, "subFeatures": [],
            "returnAfterSubfeatures": False, "parameterLibraries": [],
            "parameters": [{"btType": "BTMParameterEnum-145", "namespace": ns,
                            "enumName": "OneGripStage", "value": stage,
                            "parameterId": "stage"}]}


def drop_our_features():
    """이 도구가 만든 커스텀 피처만 제거한다 (featureType 일치 + index >= 90)."""
    j = wc.ps_features()
    removed = []
    for f in list(j["features"])[89:]:
        if f.get("featureType", "").startswith("oneGrip"):
            wc.delete_feature(f["featureId"])
            removed.append((f["name"], f["featureId"]))
    return removed


def add(stage, name):
    ns, ft = upload()
    res = wc.post_feature(custom_feature(stage, name, ns, ft))
    f = res.get("feature", {})
    return {"name": f.get("name"), "featureId": f.get("featureId"),
            "state": res.get("featureState", {}).get("featureStatus"),
            "health": wc.feature_health()}


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "drop":
        print("삭제:", drop_our_features())
        print("상태:", wc.feature_health())
    elif cmd == "add":
        print(json.dumps(add(sys.argv[2], sys.argv[3]), ensure_ascii=False, indent=1))
    elif cmd == "upload":
        print("namespace/featureType:", upload())
