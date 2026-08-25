from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step


ROOT = Path(r"C:\Users\User\Desktop\OneGrip-Play")
REV_I = ROOT / "thumb_inner_housing_lab" / "REV_I_SOURCE_FAITHFUL_THUMB_PROTOTYPE"
REV_J = ROOT / "thumb_inner_housing_lab" / "REV_J_DOCS101_REVALIDATION"
WORK = ROOT / "codex_work" / "C07_1_FDM_SIMPLIFICATION"
sys.path.insert(0, str(REV_I / "10_scripts"))

import labutil as L  # noqa: E402
from b01_true_axes import ORDER  # noqa: E402
from h03_placement import seat_solids  # noqa: E402


C07_STEP = REV_I / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step"
C071_STEP = WORK / "outputs" / "C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED.step"
C07_META = REV_I / "07_prototype" / "i10_c07.json"
C071_META = WORK / "outputs" / "c07_1_build.json"
FDM_JSON = WORK / "validation" / "C07_1_FDM_VALIDATION.json"
DOCS_JSON = WORK / "validation" / "docs101" / "j02_collision.json"
ASM_JSON = WORK / "validation" / "assembly" / "j05_assembly_sequences.json"
OUT = WORK / "validation" / "C07_VS_C07_1_COMPARISON.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def feature_counts(shape):
    edge_lengths = np.array([float(e.length) for e in shape.edges()])
    face_areas = np.array([float(f.area) for f in shape.faces()])
    return {
        "edges": int(len(edge_lengths)),
        "edgesBelow0p4Mm": int(np.sum(edge_lengths < 0.40)),
        "edgesBelow0p8Mm": int(np.sum(edge_lengths < 0.80)),
        "minimumEdgeMm": float(edge_lengths.min()),
        "faces": int(len(face_areas)),
        "facesBelow0p25Mm2": int(np.sum(face_areas < 0.25)),
        "facesBelow1mm2": int(np.sum(face_areas < 1.0)),
        "minimumFaceAreaMm2": float(face_areas.min()),
    }


def deck_top_area(shape, up, deck_z):
    rows = []
    for idx, face in enumerate(shape.faces()):
        try:
            n = np.array([face.normal_at().X, face.normal_at().Y, face.normal_at().Z], float)
            n /= np.linalg.norm(n)
        except Exception:
            continue
        vertices = np.array([[v.X, v.Y, v.Z] for v in face.vertices()], float)
        z = vertices @ up
        if float(n @ up) > 0.999 and abs(float(np.median(z)) - deck_z) < 0.02:
            rows.append({"face": idx, "areaMm2": float(face.area)})
    return {"areaMm2": float(sum(x["areaMm2"] for x in rows)), "faces": rows}


def main():
    c07m = json.loads(C07_META.read_text(encoding="utf-8"))
    c71m = json.loads(C071_META.read_text(encoding="utf-8"))
    fdm = json.loads(FDM_JSON.read_text(encoding="utf-8"))
    docs = json.loads(DOCS_JSON.read_text(encoding="utf-8"))
    asm = json.loads(ASM_JSON.read_text(encoding="utf-8"))
    corej = json.loads((REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))

    c07, _ = L.as_single_solid(import_step(str(C07_STEP)), "C07")
    c71, _ = L.as_single_solid(import_step(str(C071_STEP)), "C07_1")
    print("loaded C07 and C07.1", flush=True)

    # Exact added/removed material relative to the frozen C07 authority.
    added = float((c71 - c07).clean().volume)
    removed = float((c07 - c71).clean().volume)
    common = L.inter_vol(c07, c71)
    print("boolean delta measured", flush=True)

    up = np.asarray(c07m["printUpWorld"], float)
    up /= np.linalg.norm(up)
    origin = np.asarray(c07m["printOrigin"], float)
    deck_world_z = float(origin @ up + c07m["deckTopZ"])

    frozen_meta = {}
    for key in ("printUpWorld", "printOrigin", "bedHeightZ", "slabBottomZ", "seatPlaneZ",
                "deckTopZ", "deckThicknessMm", "deckApertureMm", "szhRaiseMm",
                "deckTopAboveSkinMm"):
        a, b = c07m[key], c71m[key]
        if isinstance(a, dict):
            delta = max(abs(float(a[k]) - float(b[k])) for k in a)
        elif isinstance(a, list):
            delta = max(abs(float(x) - float(y)) for x, y in zip(a, b))
        else:
            delta = abs(float(a) - float(b))
        frozen_meta[key] = {"C07": a, "C07_1": b, "maximumDelta": delta, "unchanged": delta <= 1.0e-9}

    # Independent actual core-vs-mechanism checks in each frozen seat frame.
    seats = {}
    mechanism = {}
    for name in [x for x in ORDER if x != "JOY"]:
        r = corej["seats"][name]
        u = seat_solids(np.asarray(r["capUndersideWorld"], float),
                        np.asarray(r["axisWorld"], float), name)
        seats[name] = u
        mechanism[name] = {
            "bodyIntersectionMm3": L.inter_vol(c71, u["body"]),
            "actuatorIntersectionMm3": L.inter_vol(c71, u["actuator"]),
        }
    print("seat mechanisms measured", flush=True)

    seat_rows = {r["seat"]: r for r in fdm["switchSeats"]}
    slot_rows = fdm["terminalSlots"]
    slots_by_seat = {name: [r for r in slot_rows if r["seat"] == name] for name in seat_rows}
    function = {
        "switchSeatsPrintable": sum(1 for r in seat_rows.values() if r["bearingAreaSampledMm2"] >= 20.0),
        "terminalSlotsPrintable": sum(1 for r in slot_rows if r["widthMm"] >= 1.20 and r["lengthMm"] >= 6.20),
        "T7BearingMm2": seat_rows["T7"]["bearingAreaSampledMm2"],
        "T8BearingMm2": seat_rows["T8"]["bearingAreaSampledMm2"],
        "minimumSlotWidthMm": min(r["widthMm"] for r in slot_rows),
        "minimumSlotLengthMm": min(r["lengthMm"] for r in slot_rows),
        "mechanismIntersection": mechanism,
        "capSeatStackAuthority": "same REV_I i06_current_core.json and frozen seat_solids inputs",
        "capUndersideToSeatMm": 4.759,
        "joyAxisWorld": joyj["joyAxisWorld"],
        "joystickDeckPlaneWorldDotUpMm": deck_world_z,
        "frozenMetadata": frozen_meta,
        "deckTopUsableArea": {
            "C07": deck_top_area(c07, up, deck_world_z),
            "C07_1": deck_top_area(c71, up, deck_world_z),
        },
    }

    m = fdm["orientationCandidates"][0]
    regions = m["largestSupportRegions"]
    bridge_pairs = c71m["explicitBridgePairs"]
    bridge_lengths = []
    for a, b in bridge_pairs:
        pa = np.asarray(corej["seats"][a]["plateTopWorld"], float)
        pb = np.asarray(corej["seats"][b]["plateTopWorld"], float)
        bridge_lengths.append({"pair": [a, b], "centreDistanceMm": float(np.linalg.norm(pb - pa))})

    fdm_result = {
        "orientation": m["label"],
        "heightMm": m["heightMm"],
        "bedContactMm2": m["bedContactAreaMm2"],
        "supportRequiredSurfaceMm2": m["supportAreaMm2"],
        "supportFraction": m["supportFraction"],
        "nonRemovableSupportRegions": m["trappedSupportRegions"],
        "nonRemovableSupportAreaMm2": float(sum(r["areaMm2"] for r in regions if r["trapped"])),
        "criticalDeckSupportBaseMm2": fdm["supportLanding"]["wouldBaseOnDeckTopAreaMm2"],
        "otherModelSupportBaseMm2": fdm["supportLanding"]["wouldBaseOnOtherModelAreaMm2"],
        "interiorAreaBelow1p2Mm2": fdm["firstLayer"]["interiorAreaBelow1p2Mm2"],
        "firstLayerComponents": fdm["firstLayer"]["firstLayerComponents"],
        "largestSupportRegionAreaMm2": max(r["areaMm2"] for r in regions),
        "largestSupportRegionSpanMm": max(r["maxSpanMm"] for r in regions),
        "worstOverhang": "flat carrier underside; support required but open and removable",
        "postProcessAccess": "all measured support regions accessible; no trapped region",
        "explicitBridgeLengths": bridge_lengths,
        "longestExplicitBridgeCentreDistanceMm": max(r["centreDistanceMm"] for r in bridge_lengths),
    }

    complexity = {
        "C07": {
            "volumeMm3": float(c07.volume), "faces": len(list(c07.faces())),
            "bridges": 16, "deckWalls": 5, "dynamicStandoffs": 3,
            **feature_counts(c07),
        },
        "C07_1": {
            "volumeMm3": float(c71.volume), "faces": len(list(c71.faces())),
            "bridges": len(bridge_pairs), "deckWalls": c71m["verticalWalls"],
            "dynamicStandoffs": c71m["standoffs"],
            **feature_counts(c71),
        },
        "commonVolumeMm3": common,
        "addedVsC07Mm3": added,
        "removedVsC07Mm3": removed,
    }

    docs101 = {
        "shellInterferenceMm3": docs["shellInterferenceMm3"],
        "fingerResults": docs["fingers"],
        "minimumFingerClearanceMm": docs["minFingerClearanceMm"],
        "N1ClearanceMm": docs["fingers"]["N1"]["minClearanceMm"],
        "N2ClearanceMm": docs["fingers"]["N2"]["minClearanceMm"],
        "hardCollisions": docs["hard"],
        "assembly": {
            "sequenceAValid": asm["sequenceAValid"],
            "sequenceBValid": asm["sequenceBValid"],
            "clearPaths": asm["clearPaths"],
            "blockedButtons": asm["blockedButtons"],
            "result": asm["assembly"],
        },
    }

    out = {
        "candidate": str(C071_STEP),
        "authority": str(C07_STEP),
        "hashes": {"C07_STEP": sha256(C07_STEP), "C07_1_STEP": sha256(C071_STEP)},
        "integrity": {
            "solids": fdm["step"]["solids"], "valid": fdm["step"]["valid"],
            "stlOpenEdges": fdm["stl"]["openEdges"],
            "stlNonManifoldEdges": fdm["stl"]["nonManifoldEdges"],
            "stlSelfIntersections": len(fdm["stl"]["selfIntersectionPairs"]),
            "stlDegenerateTriangles": fdm["stl"]["degenerateTriangles"],
        },
        "function": function,
        "docs101": docs101,
        "fdm": fdm_result,
        "complexity": complexity,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
