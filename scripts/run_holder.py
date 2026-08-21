"""INDEX holder atomic pipeline 실행기 (승인된 사본 전용).

    python scripts/run_holder.py I2
    python scripts/run_holder.py I3 --no-union     # union 전에 멈춤
    python scripts/run_holder.py I3 --clip-union   # split clip 후 union
"""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from onshape.client import BASE, session          # noqa: E402
from onshape import write_client as wc            # noqa: E402

DUMP = os.path.join(os.path.dirname(__file__), "..", "cad_dump")
URL = f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{wc.EID_JOYSTICK}/features"


def cfg():
    with open(os.path.join(DUMP, "dbg_target.json"), encoding="utf-8") as f:
        return json.load(f)


def solids():
    return [(x["partId"], x["name"]) for x in session().get(
        f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{wc.EID_JOYSTICK}", timeout=120).json()
        if x["bodyType"] == "solid"]


def add(button, stage, name, blank_id=""):
    c = cfg()
    f = {"btType": "BTMFeature-134", "namespace": c["namespace"], "name": name,
         "suppressed": False, "featureType": c["featureType"], "subFeatures": [],
         "returnAfterSubfeatures": False, "parameterLibraries": [],
         "parameters": [
             {"btType": "BTMParameterEnum-145", "namespace": c["namespace"],
              "enumName": "IdxButton", "value": button, "parameterId": "button"},
             {"btType": "BTMParameterEnum-145", "namespace": c["namespace"],
              "enumName": "IdxStage", "value": stage, "parameterId": "stage"},
             {"btType": "BTMParameterString-149", "value": blank_id,
              "parameterId": "blankId"}]}
    r = session().post(URL, json={"feature": f, "rejectMicroversionSkew": False}, timeout=300)
    j = r.json() if r.status_code < 400 else {}
    return (j.get("featureState", {}).get("featureStatus"),
            j.get("feature", {}).get("featureId"), r.status_code)


def step(button, stage, name, blank_id="", pause=12):
    before = solids()
    st, fid, code = add(button, stage, name, blank_id)
    time.sleep(pause)
    after = solids()
    ap = {p for p, _ in after}
    j1 = [p for p, n in after if n == "Joystick_1"]
    j2 = [p for p, n in after if n == "Joystick_2"]
    ok = (st == "OK" and "JaD" in ap and "JfD" in ap and len(j1) == 1 and len(j2) == 1)
    print(f"  {name:<28} state={str(st):<6} id={fid}  solid {len(before)}->{len(after)}  "
          f"신규{sorted(ap - {p for p, _ in before})} 소멸{sorted({p for p, _ in before} - ap)}  "
          f"J1={len(j1)} J2={len(j2)}  {'OK' if ok else 'FAIL'}")
    return ok, fid


def pipeline(btn, do_clip=False, do_union=True):
    ok, blank = step(btn, "BLANK", f"DEBUG_{btn}_holder_blank")
    if not ok:
        return False, blank
    for stage, suf in (("SEAT", "switch_seat"), ("REAR", "open_rear"), ("LIP", "front_lip_bore")):
        ok, _ = step(btn, stage, f"DEBUG_{btn}_{suf}", blank)
        if not ok:
            return False, blank
        time.sleep(4)
    if do_clip:
        ok, _ = step(btn, "SPLITCLIP", f"DEBUG_{btn}_split_clip", blank)
        if not ok:
            return False, blank
        time.sleep(4)
    if do_union:
        ok, _ = step(btn, "UNION", f"DEBUG_{btn}_union", blank)
        if not ok:
            return False, blank
    return True, blank


if __name__ == "__main__":
    b = sys.argv[1]
    clip = "--clip" in sys.argv
    nounion = "--no-union" in sys.argv
    ok, blank = pipeline(b, do_clip=clip, do_union=not nounion)
    print(f"\n{b} pipeline: {'PASS' if ok else 'FAIL'}   blank feature id = {blank}")
    with open(os.path.join(DUMP, f"blank_{b}.json"), "w") as f:
        json.dump({"blankId": blank, "ok": ok}, f)
