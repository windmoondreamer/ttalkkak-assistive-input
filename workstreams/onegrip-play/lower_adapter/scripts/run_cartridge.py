"""OPTION C 카트리지 FeatureScript 실행기 (신규 Part Studio 전용).

    python lower_adapter/scripts/run_cartridge.py init
    python lower_adapter/scripts/run_cartridge.py vars [skip]
    python lower_adapter/scripts/run_cartridge.py upload
    python lower_adapter/scripts/run_cartridge.py add <STAGE> <name>
    python lower_adapter/scripts/run_cartridge.py parts
    python lower_adapter/scripts/run_cartridge.py health
    python lower_adapter/scripts/run_cartridge.py del <featureId>

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
FS_PATH = os.path.join(ROOT, "lower_adapter", "cad", "OneGrip_Cartridge.fs")
TARGET = os.path.join(OUT, "cartridge_target.json")

VARS = [("cartridge_insert_depth", "6 mm", "LENGTH"),
        ("deck_thickness", "6 mm", "LENGTH"),
        ("wall_thickness", "6 mm", "LENGTH"),
        ("carrier_fit", "0.2 mm", "LENGTH"),
        ("pocket_clearance", "0.3 mm", "LENGTH"),
        ("usb_clearance", "6 mm", "LENGTH")]

FORBIDDEN_EIDS = {wc.EID_JOYSTICK,
                  "df9a32f1f239bc71a732f5d3",     # 스톡 Base Part Studio — IMMUTABLE
                  "2e024442c796323fd37e49c3",     # EMBEDDED_GIMBAL (fallback, 보존)
                  "bbfebe9c42748fb6d5b912e8"}     # LOWER_ADAPTER V1 (보존)


def target():
    return json.load(io.open(TARGET, encoding="utf-8"))


def save(t):
    json.dump(t, io.open(TARGET, "w", encoding="utf-8"), indent=1)


def guard(eid):
    if eid in FORBIDDEN_EIDS:
        raise RuntimeError(f"차단: 보존 대상 element 로의 쓰기 시도 ({eid})")
    return eid


def init():
    ps = wc.create_part_studio("OneGrip_StockCartridge")
    fs = wc.create_feature_studio("OneGrip_Cartridge_FS")
    t = {"ps_eid": ps["id"], "fs_eid": fs["id"]}
    save(t)
    print("Part Studio   ", ps["id"], ps.get("name"))
    print("Feature Studio", fs["id"], fs.get("name"))
    return t


def post(feature, eid):
    guard(eid)
    wc._guard(wc.DID, wc.WID)
    r = session().post(f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{eid}/features",
                       json={"feature": feature, "rejectMicroversionSkew": False},
                       timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"POST 실패 {r.status_code}: {r.text[:500]}")
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
        print(f"  #{n:<24s} = {v:<8s} {st}  {fid}")
    t["varIds"] = ids
    save(t)


def upload():
    t = target()
    wc.set_feature_studio_contents(t["fs_eid"], io.open(FS_PATH, encoding="utf-8").read())
    spec = session().get(
        f"{BASE}/featurestudios/d/{wc.DID}/w/{wc.WID}/e/{t['fs_eid']}/featurespecs",
        timeout=180).json()
    if not spec.get("featureSpecs"):
        raise RuntimeError("컴파일 실패:\n" + json.dumps(spec, indent=1)[:2000])
    s = spec["featureSpecs"][0]
    t["namespace"], t["featureType"] = s["namespace"], s["featureType"]
    save(t)
    return t["namespace"], t["featureType"]


def custom(stage, name, ns, ft):
    return {"btType": "BTMFeature-134", "namespace": ns, "name": name,
            "suppressed": False, "featureType": ft, "subFeatures": [],
            "returnAfterSubfeatures": False, "parameterLibraries": [],
            "parameters": [{"btType": "BTMParameterEnum-145", "namespace": ns,
                            "enumName": "CartStage", "value": stage,
                            "parameterId": "stage"}]}


def add(stage, name):
    t = target()
    ns, ft = t.get("namespace"), t.get("featureType")
    if ns is None:
        ns, ft = upload()
    fid, st = post(custom(stage, name, ns, ft), t["ps_eid"])
    print(f"  {name:<28s} post={st}  featureId={fid}")
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


def health():
    t = target()
    r = session().get(f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{t['ps_eid']}/features",
                      timeout=300)
    if r.status_code != 200:
        print("features GET", r.status_code, r.headers.get("Retry-After"))
        return
    j = r.json()
    st = j.get("featureStates", {})
    from collections import Counter
    c = Counter(v.get("featureStatus") for v in st.values())
    print(f"  features {len(j['features'])}  isComplete {j.get('isComplete')}  {dict(c)}")
    for f in j["features"]:
        s = st.get(f["featureId"], {}).get("featureStatus")
        if s not in ("OK",):
            print(f"   {s:<8s} {f.get('name')}  {f['featureId']}")
            for m in st.get(f["featureId"], {}).get("featureMessages", [])[:4]:
                print("      ", m.get("message"))


def delete(fid):
    t = target()
    guard(t["ps_eid"])
    wc.delete_feature(fid, t["ps_eid"])
    print("deleted", fid)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "init":
        init()
    elif cmd == "vars":
        make_vars(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    elif cmd == "upload":
        print("ns/ft:", upload())
    elif cmd == "add":
        add(sys.argv[2], sys.argv[3])
    elif cmd == "parts":
        parts()
    elif cmd == "health":
        health()
    elif cmd == "del":
        delete(sys.argv[2])
