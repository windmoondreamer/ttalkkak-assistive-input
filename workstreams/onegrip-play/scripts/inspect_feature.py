"""피처 트리 상세 조회 유틸 (READ ONLY, 로컬 덤프만 읽음).

사용:
    python scripts/inspect_feature.py <studio> [feature_name_substr ...]
    python scripts/inspect_feature.py Joystick Buttons
    python scripts/inspect_feature.py Joystick --list
    python scripts/inspect_feature.py Joystick --sketch Buttons
    python scripts/inspect_feature.py Joystick --deps

cad_dump/features_<studio>.json 을 읽는다. Onshape에 요청하지 않는다.
"""
import json
import os
import sys

DUMP = os.path.join(os.path.dirname(__file__), "..", "cad_dump")
M2MM = 1000.0


def load(studio):
    with open(os.path.join(DUMP, f"features_{studio}.json"), encoding="utf-8") as f:
        return json.load(f)


def pv(p):
    """파라미터 값을 사람이 읽을 수 있게 편다."""
    bt = p.get("btType", "")
    if bt.startswith("BTMParameterQuantity"):
        return p.get("expression") or f"{p.get('value')} ({p.get('units')})"
    if bt.startswith("BTMParameterQueryList"):
        out = []
        for q in p.get("queries", []):
            ids = q.get("featureId") or q.get("featureIds") or q.get("deterministicIds")
            out.append(f"{q.get('btType','?').split('-')[0]}:{ids}")
        return out or "[]"
    if bt.startswith("BTMParameterBoolean"):
        return p.get("value")
    if bt.startswith("BTMParameterEnum"):
        return f"{p.get('value')} <{p.get('enumName')}>"
    if bt.startswith("BTMParameterString"):
        return p.get("value")
    if bt.startswith("BTMParameterReferenceWithConfiguration") or bt.startswith("BTMParameterDerived"):
        return {k: v for k, v in p.items() if k not in ("btType", "nodeId")}
    return p.get("value", p.get("expression", "?"))


def show_feature(ft, indent=""):
    print(f"{indent}[{ft.get('featureType')}] {ft.get('name')}  id={ft.get('featureId')}")
    if ft.get("suppressed"):
        print(f"{indent}   *** SUPPRESSED ***")
    for p in ft.get("parameters", []):
        print(f"{indent}   - {p.get('parameterId'):<22} = {pv(p)}")
    ents = ft.get("entities", [])
    if ents:
        print(f"{indent}   (sketch entities: {len(ents)})")
    for sub in ft.get("subFeatures", []):
        show_feature(sub, indent + "    ")


def show_sketch(ft):
    """스케치 형상을 mm 단위로 출력."""
    print(f"\n=== SKETCH '{ft.get('name')}'  id={ft.get('featureId')} ===")
    for p in ft.get("parameters", []):
        print(f"  param {p.get('parameterId'):<20} = {pv(p)}")
    circles, lines, arcs, points, other = [], [], [], [], []
    for e in ft.get("entities", []):
        g = e.get("geometry", {}) or {}
        gt = g.get("btType", "")
        eid = e.get("entityId", "")
        con = e.get("isConstruction", False)
        if "Circle" in gt:
            circles.append((eid, con, g.get("xCenter", 0) * M2MM, g.get("yCenter", 0) * M2MM,
                            g.get("radius", 0) * M2MM, g.get("clockwise")))
        elif "Line" in gt:
            sp, ep = e.get("startParam", 0), e.get("endParam", 0)
            x, y = g.get("pntX", 0), g.get("pntY", 0)
            dx, dy = g.get("dirX", 0), g.get("dirY", 0)
            lines.append((eid, con,
                          (x + dx * sp) * M2MM, (y + dy * sp) * M2MM,
                          (x + dx * ep) * M2MM, (y + dy * ep) * M2MM))
        elif "Point" in gt:
            points.append((eid, g.get("x", 0) * M2MM, g.get("y", 0) * M2MM))
        elif gt:
            other.append((eid, gt, {k: v for k, v in g.items() if k != "btType"}))
    if circles:
        print(f"\n  -- circles ({len(circles)}) [mm]")
        for eid, con, cx, cy, r, cw in sorted(circles, key=lambda c: (-c[3], c[2])):
            tag = " (construction)" if con else ""
            print(f"     cx={cx:9.3f}  cy={cy:9.3f}  r={r:7.3f}  d={2*r:7.3f}  {eid}{tag}")
    if lines:
        print(f"\n  -- lines ({len(lines)}) [mm]")
        for eid, con, x1, y1, x2, y2 in lines:
            tag = " (construction)" if con else ""
            ln = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            print(f"     ({x1:8.3f},{y1:8.3f}) -> ({x2:8.3f},{y2:8.3f})  len={ln:7.3f}  {eid}{tag}")
    if points:
        print(f"\n  -- points ({len(points)}) [mm]")
        for eid, x, y in points:
            print(f"     ({x:8.3f},{y:8.3f})  {eid}")
    if other:
        print(f"\n  -- other geometry ({len(other)})")
        for eid, gt, g in other:
            print(f"     {gt} {eid}: {json.dumps(g)[:160]}")


def deps(j):
    """feature 간 참조 관계 (queries 안의 featureId 기준)."""
    byid = {f["featureId"]: f for f in j["features"]}
    print(f"{'feature':<34} {'type':<18} -> refs")
    for ft in j["features"]:
        refs = set()

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("featureId", "featureIds") and v:
                        for x in (v if isinstance(v, list) else [v]):
                            if x in byid and x != ft["featureId"]:
                                refs.add(x)
                    else:
                        walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(ft.get("parameters", []))
        if refs:
            names = ", ".join(sorted(byid[r]["name"] for r in refs))
            print(f"{ft['name'][:33]:<34} {ft['featureType'][:17]:<18} -> {names}")


def main():
    studio = sys.argv[1]
    args = sys.argv[2:]
    j = load(studio)
    feats = j["features"]

    if not args or args[0] == "--list":
        for i, ft in enumerate(feats, 1):
            print(f"{i:3}. {ft['featureType']:<18} {ft['name']:<34} {ft['featureId']}")
        return
    if args[0] == "--deps":
        deps(j)
        return
    if args[0] == "--sketch":
        for ft in feats:
            if any(a.lower() in ft["name"].lower() for a in args[1:]) and ft["featureType"] == "newSketch":
                show_sketch(ft)
        return
    for ft in feats:
        if any(a.lower() in ft["name"].lower() for a in args):
            show_feature(ft)
            print()


if __name__ == "__main__":
    main()
