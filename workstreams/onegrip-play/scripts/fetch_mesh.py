"""Onshape tessellatedfaces 를 받아 로컬 캐시에 저장한다 (READ ONLY, GET 전용).

    python scripts/fetch_mesh.py

cad_dump/mesh_<part>.json 에 {name, partId, tris:[[[x,y,z]*3]...]} (mm) 로 저장.
POST/PUT/DELETE 를 절대 사용하지 않는다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from onshape.client import BASE, ELEMENTS, SOURCE, session  # noqa: E402

DUMP = os.path.join(os.path.dirname(__file__), "..", "cad_dump")
M2MM = 1000.0

# Joystick Part Studio 의 solid part
JOYSTICK_PARTS = {
    "Joystick_1": "JaD",
    "Joystick_2": "JfD",
    "Backplate": "RYDD",
    "Small_joystick_attachment": "RHED",
    "Button_corner_1": "RAEL",
    "Button_side_1": "RAEH",
    "Button_wide_1": "RAED",
    "Button_middle_1": "RDED",
    "Button_corner_2": "RBED",
    "Button_side_2": "RBEH",
    "Button_wide_2": "RBEL",
    "Button_middle_2": "RDEH",
}
BASE_PARTS = {"Pitch": "JmD", "Roll": "JaD", "Base": "RYBD"}


def fetch(eid, pid, name, angle=0.09, chord=0.15):
    path = os.path.join(DUMP, f"mesh_{name}.json")
    if os.path.exists(path):
        return path, True
    s = session()
    r = s.get(f"{BASE}/partstudios/d/{SOURCE['did']}/w/{SOURCE['wid']}/e/{eid}/tessellatedfaces",
              params={"angleTolerance": angle, "chordTolerance": chord,
                      "partId": pid, "outputFaceAppearances": "false"}, timeout=300)
    r.raise_for_status()
    j = r.json()
    tris, norms = [], []
    for body in j.get("bodies", []):
        for face in body.get("faces", []):
            for facet in face.get("facets", []):
                v = facet.get("vertices", [])
                if len(v) != 3:
                    continue
                tris.append([[p["x"] * M2MM, p["y"] * M2MM, p["z"] * M2MM] for p in v])
                nv = facet.get("normal") or {}
                norms.append([nv.get("x", 0.0), nv.get("y", 0.0), nv.get("z", 0.0)])
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"name": name, "partId": pid, "tris": tris, "normals": norms}, f)
    return path, False


def main():
    os.makedirs(DUMP, exist_ok=True)
    jobs = [(ELEMENTS["ps_Joystick"], pid, n) for n, pid in JOYSTICK_PARTS.items()]
    jobs += [(ELEMENTS["ps_Base"], pid, n) for n, pid in BASE_PARTS.items()]
    for eid, pid, name in jobs:
        try:
            path, cached = fetch(eid, pid, name)
            with open(path, encoding="utf-8") as f:
                n = len(json.load(f)["tris"])
            print(f"  {'cached' if cached else 'fetched':<8} {name:<28} tris={n:7}  "
                  f"{os.path.getsize(path)//1024:5} KB")
        except Exception as ex:
            print(f"  FAILED   {name:<28} {ex}")


if __name__ == "__main__":
    main()
