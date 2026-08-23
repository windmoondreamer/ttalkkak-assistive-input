"""컨포멀 하우징 FS 실행기 (신규 Part Studio 전용)."""
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
FS_PATH = os.path.join(ROOT, "lower_adapter", "cad", "OneGrip_Conformal.fs")
TARGET = os.path.join(OUT, "conformal_target.json")

VARS = [("pocket_clearance2", "0.3 mm", "LENGTH"),
        ("knee_angle", "34 deg", "ANGLE"),
        ("knee_y", "18 mm", "LENGTH"),
        ("trace_steps", "0 mm", "LENGTH")]

FORBIDDEN = {wc.EID_JOYSTICK,
             "df9a32f1f239bc71a732f5d3",     # 스톡 Base PS — IMMUTABLE
             "2e024442c796323fd37e49c3",     # EMBEDDED_GIMBAL (보존)
             "bbfebe9c42748fb6d5b912e8",     # LOWER_ADAPTER V1 (보존)
             "f698b10ce216ca7c95051dd3"}     # OPTION C thin-deck (보존)


def target():
    return json.load(io.open(TARGET, encoding="utf-8"))


def save(t):
    json.dump(t, io.open(TARGET, "w", encoding="utf-8"), indent=1)


def guard(eid):
    if eid in FORBIDDEN:
        raise RuntimeError(f"차단: 보존 대상 element ({eid})")
    return eid


def init():
    ps = wc.create_part_studio("OneGrip_ConformalHousing")
    fs = wc.create_feature_studio("OneGrip_Conformal_FS")
    t = {"ps_eid": ps["id"], "fs_eid": fs["id"]}
    save(t)
    print("Part Studio   ", ps["id"], ps.get("name"))
    print("Feature Studio", fs["id"], fs.get("name"))


def post(feature, eid):
    guard(eid)
    wc._guard(wc.DID, wc.WID)
    r = session().post(f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{eid}/features",
                       json={"feature": feature, "rejectMicroversionSkew": False},
                       timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"POST 실패 {r.status_code}: {r.text[:600]}")
    j = r.json()
    return (j.get("feature", {}).get("featureId"),
            j.get("featureState", {}).get("featureStatus"))


def local_var_template():
    j = json.load(io.open(os.path.join(ROOT, "cad_dump", "features_Joystick.json"),
                          encoding="utf-8"))
    src = next(f for f in j["features"] if f.get("featureType") == "assignVariable")
    wc._VAR_TEMPLATE = wc._strip_ids(src)


def make_vars():
    local_var_template()
    t = target()
    ids = t.get("varIds", {})
    for n, v, ty in VARS:
        fid, st = post(wc.assign_variable(n, v, ty), t["ps_eid"])
        ids[n] = fid
        print(f"  #{n:<20s} = {v:<8s} {st}  {fid}")
    t["varIds"] = ids
    save(t)


def upload():
    t = target()
    wc.set_feature_studio_contents(t["fs_eid"], io.open(FS_PATH, encoding="utf-8").read())
    spec = session().get(
        f"{BASE}/featurestudios/d/{wc.DID}/w/{wc.WID}/e/{t['fs_eid']}/featurespecs",
        timeout=180).json()
    if not spec.get("featureSpecs"):
        raise RuntimeError("컴파일 실패:\n" + json.dumps(spec, indent=1)[:2500])
    s = spec["featureSpecs"][0]
    t["namespace"], t["featureType"] = s["namespace"], s["featureType"]
    save(t)
    return t["namespace"], t["featureType"]


def custom(stage, name, ns, ft):
    return {"btType": "BTMFeature-134", "namespace": ns, "name": name,
            "suppressed": False, "featureType": ft, "subFeatures": [],
            "returnAfterSubfeatures": False, "parameterLibraries": [],
            "parameters": [
                {"btType": "BTMParameterEnum-145", "namespace": ns,
                 "enumName": "ConfStage", "value": stage,
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


def setvar(name, expr, ty="LENGTH"):
    """트리 변수 값을 바꾼다 (무릎면 변형 스윕용)."""
    local_var_template()
    t = target()
    fid = t["varIds"][name]
    f = wc.assign_variable(name, expr, ty)
    f["featureId"] = fid
    r = session().post(
        f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{t['ps_eid']}/features/featureid/{fid}",
        json={"feature": f, "rejectMicroversionSkew": False}, timeout=300)
    print(f"  #{name} = {expr} ->", r.status_code)


def parts():
    t = target()
    r = session().get(f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{t['ps_eid']}",
                      params=[("configuration", "default")], timeout=180)
    if r.status_code != 200:
        print("parts GET", r.status_code, r.headers.get("Retry-After"))
        return
    p = r.json()
    sol = [x for x in p if x.get("bodyType") == "solid"]
    print(f"  records {len(p)}  solid {len(sol)}  wire {len(p) - len(sol)}")
    for x in sol:
        m = session().get(
            f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{t['ps_eid']}/partid/"
            f"{x['partId'].replace('/', '%2F')}/massproperties",
            params=[("configuration", "default")], timeout=180)
        v = ""
        if m.status_code == 200:
            b = m.json()["bodies"]
            v = f"{b[list(b)[0]]['volume'][0] * 1e9:10.1f} mm3"
        print("   ", x["partId"], x.get("name"), v)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "init":
        init()
    elif cmd == "vars":
        make_vars()
    elif cmd == "upload":
        print("ns/ft:", upload())
    elif cmd == "add":
        add(sys.argv[2], sys.argv[3])
    elif cmd == "setvar":
        setvar(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "LENGTH")
    elif cmd == "parts":
        parts()
