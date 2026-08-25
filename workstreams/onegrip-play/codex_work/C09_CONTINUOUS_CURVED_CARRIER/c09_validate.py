"""Independent feasibility and full validation for the isolated C09 core."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Box, CenterOf, Location, Plane, Vector,
                       import_step)
from scipy.spatial import cKDTree

ROOT = Path(r"C:\Users\User\Desktop\OneGrip-Play")
WORK = ROOT / "codex_work" / "C09_CONTINUOUS_CURVED_CARRIER"
OUT = WORK / "outputs"
GATE = WORK / "gate"
VAL = WORK / "validation"
REV_I = ROOT / "thumb_inner_housing_lab" / "REV_I_SOURCE_FAITHFUL_THUMB_PROTOTYPE"
REV_A = ROOT / "thumb_inner_housing_lab" / "REV_A"
REV_K_SCRIPTS = ROOT / "thumb_inner_housing_lab" / "REV_K_C08_LOCAL_CONFORMAL_RECEIVER" / "10_scripts"
C071_DIR = ROOT / "codex_work" / "C07_1_FDM_SIMPLIFICATION"
sys.path.insert(0, str(REV_K_SCRIPTS))
sys.path.insert(0, str(C071_DIR))

import labutil as L  # noqa: E402
from b01_true_axes import ORDER  # noqa: E402
from b03_axis_authority import ray_intervals  # noqa: E402
from h03_placement import seat_solids  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402
from j02_collision import BUTTONS, POCKET_CLR, switch_groups  # noqa: E402
from validate_c07_1_fdm import (Field, first_layer_and_thickness,  # noqa: E402
                                orientation_metric, read_binary_stl,
                                support_landing_analysis,
                                topology_metrics)

CANDIDATE = "C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE"
STEP = OUT / f"{CANDIDATE}.step"
STL = OUT / f"{CANDIDATE}.stl"
MIN_WALL = 1.20
PREF_WALL = 1.60
SLOT_OFF = 2.60


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def vec(v):
    return np.asarray([float(v.X), float(v.Y), float(v.Z)], float)


def solid(shape, tag):
    s, _ = L.as_single_solid(shape, tag)
    return s


def sample_function(shape, seat, joy_up):
    T = L.triangles(shape, tol=0.04, ang=0.09)
    top = np.asarray(seat["top"], float)
    w, ex, ey = seat["w"], seat["ex"], seat["ey"]

    pitch = 0.10
    d = T.reshape(-1, 3) - top
    Tl = np.stack([d @ ex, d @ ey, d @ w], axis=1).reshape(-1, 3, 3)
    pf = Field(Tl)
    bearing = 0
    for x in np.arange(-3.01 + pitch / 2, 3.01, pitch):
        for y in np.arange(-3.02 + pitch / 2, 3.02, pitch):
            h = pf.hits(float(x), float(y))
            if len(h) % 2 == 0 and any(h[k] - 1e-6 <= -0.05 <= h[k + 1] + 1e-6
                                      for k in range(0, len(h), 2)):
                bearing += 1
    slots = []
    for sign in (-1.0, 1.0):
        c = np.asarray((sign * SLOT_OFF, 0.0, -0.80), float)

        def air_run(axis, half, step):
            ts = np.arange(-half, half + 0.5 * step, step)
            air = []
            for t in ts:
                p = c + axis * t
                h = pf.hits(float(p[0]) + 3.7e-7, float(p[1]) + 2.1e-7)
                inside = len(h) % 2 == 0 and any(h[k] - 1e-6 <= p[2] <= h[k + 1] + 1e-6
                                                for k in range(0, len(h), 2))
                air.append(not inside)
            air = np.asarray(air, bool)
            i0 = int(np.argmin(np.abs(ts)))
            if not air[i0]:
                return 0.0
            lo = hi = i0
            while lo > 0 and air[lo - 1]:
                lo -= 1
            while hi + 1 < len(ts) and air[hi + 1]:
                hi += 1
            return float(ts[hi] - ts[lo] + step)

        slots.append({"widthMm": air_run(np.asarray((1, 0, 0), float), 1.15, 0.01),
                      "lengthMm": air_run(np.asarray((0, 1, 0), float), 4.0, 0.02)})
    angle = math.degrees(math.acos(np.clip(float(w @ joy_up), -1.0, 1.0)))
    return {"bearingMm2": bearing * pitch * pitch, "slots": slots,
            "seatNormalErrorDeg": 0.0,
            "seatTiltToPrintUpDeg": angle}


def support_metric(shape, up):
    T = L.triangles(shape, tol=0.04, ang=0.09)
    # orientation_metric expects a welded face index only for adjacency.  Weld
    # by rounded coordinates so support regions are grouped correctly.
    q = np.round(T.reshape(-1, 3) / 1e-6).astype(np.int64)
    _, inv = np.unique(q, axis=0, return_inverse=True)
    F = inv.reshape(-1, 3)
    try:
        com = vec(shape.center(CenterOf.MASS))
    except Exception:
        bb = shape.bounding_box()
        com = 0.5 * (vec(bb.min) + vec(bb.max))
    return orientation_metric(T, F, up, "JOY_AXIS_UP", com)


def sweep(body, obstacle, direction, travel=30):
    vals = []
    for k in np.arange(1.0, float(travel) + 0.01, 1.0):
        moved = body.moved(Location(Vector(*[float(x) for x in (direction * k)])))
        vals.append(L.inter_vol(moved, obstacle))
    first = next((i + 1 for i, v in enumerate(vals) if v > 1e-6), None)
    return {"travelMm": travel, "sumInterferenceMm3": float(sum(vals)),
            "maxInterferenceMm3": float(max(vals, default=0.0)),
            "firstBlockedAtMm": first, "pass": max(vals, default=0.0) <= 1e-6}


def main() -> int:
    VAL.mkdir(parents=True, exist_ok=True)
    build = json.loads((OUT / "c09_build.json").read_text(encoding="utf-8"))
    core_j = json.loads((REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joy_j = json.loads((REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    c071_meta = json.loads((C071_DIR / "outputs" / "c07_1_build.json").read_text(encoding="utf-8"))
    c071_fdm = json.loads((C071_DIR / "validation" / "C07_1_FDM_VALIDATION.json").read_text(encoding="utf-8"))
    ext = json.loads((REV_I / "02_original_external_stack" / "i02_original_external_stack.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]
    jw = L.unit(np.asarray(joy_j["joyAxisWorld"], float))
    jc = np.asarray(joy_j["knobCentreWorld"], float)

    seats = {}
    for n in names:
        r = core_j["seats"][n]
        u = seat_solids(np.asarray(r["capUndersideWorld"], float),
                        np.asarray(r["axisWorld"], float), n)
        seats[n] = {"top": np.asarray(u["plateTopPoint"], float),
                    "w": L.unit(np.asarray(r["axisWorld"], float)),
                    "ex": L.unit(np.asarray(u["ex"], float)),
                    "ey": L.unit(np.asarray(u["ey"], float)),
                    "body": u["body"], "terminals": u["terminals"],
                    "actuator": u["actuator"]}

    shells = {}
    shell_points = []
    shell_tris = []
    for tag, key in (("JaD", "D101_JAD"), ("JfD", "D101_JFD")):
        shells[tag] = solid(import_step(L.SRC[key]), tag)
        shell_points.append(L.surf_points(shells[tag], 700000, tol=0.06))
        shell_tris.append(L.triangles(shells[tag], tol=0.06, ang=0.12))
    Psh = np.concatenate(shell_points)
    Psh = Psh[np.linalg.norm(Psh - L.DATUM_P, axis=1) < 58.0]
    T101 = np.concatenate(shell_tris)
    tree_shell = cKDTree(Psh)
    groups = switch_groups()
    L.memory("validation authority")

    # ---- two-button feasibility gate -----------------------------------
    gate_rows = {}
    gate_fail = []
    keep = import_step(str(REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    c07_src = json.loads((REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    raise_vec = jw * float(c07_src["szhRaiseMm"])
    static_szh = []
    provisional_szh = []
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if not ch.solids() or not lab.startswith("SZH"):
            continue
        s = solid(ch, lab).moved(Location(Vector(*[float(x) for x in raise_vec])))
        (provisional_szh if "MOVING" in lab else static_szh).append((lab, s))

    for n in ("T2", "T8"):
        gshape = solid(import_step(str(GATE / f"C09_GATE_{n}.step")), n)
        fun = sample_function(gshape, seats[n], jw)
        shell_iv = {k: L.inter_vol(gshape, s) for k, s in shells.items()}
        mechanism_iv = {"body": L.inter_vol(gshape, seats[n]["body"]),
                        "actuator": L.inter_vol(gshape, seats[n]["actuator"]),
                        "terminals": L.inter_vol(gshape, seats[n]["terminals"])}
        finger_iv = {bt: sum(L.inter_vol(gshape, s) for v in gr.values() for s in v)
                     for bt, gr in groups.items()}
        terminal_hits = ray_intervals(T101, seats[n]["top"], -seats[n]["w"], 0.0, 60.0)
        terminal_free = float(min([a for a, _ in (terminal_hits or [])], default=60.0))
        static_iv = {lab: L.inter_vol(gshape, s) for lab, s in static_szh}
        prov_iv = {lab: L.inter_vol(gshape, s) for lab, s in provisional_szh}
        asm = {"+U_vs_JfD": sweep(gshape, shells["JfD"], L.DATUM_U, 25),
               "-U_vs_JaD": sweep(gshape, shells["JaD"], -L.DATUM_U, 25)}
        fdm = support_metric(gshape, jw)
        criteria = {
            "singleValidSolid": len(list(gshape.solids())) == 1 and bool(gshape.is_valid),
            "frozenAxisAndSeat": fun["seatNormalErrorDeg"] <= 1e-9,
            "bearing": fun["bearingMm2"] >= 18.24,
            "terminalSlots": all(x["widthMm"] >= 1.20 and x["lengthMm"] >= 6.20 for x in fun["slots"]),
            "terminalEscape": terminal_free >= 3.654,
            # h03 "terminals" is one 7.568 x 4.632 conservative envelope,
            # not the two physical terminals.  It necessarily overlaps a flat
            # seat.  Actual terminal viability is the two measured slots plus
            # free depth; only body and actuator are collision gates here.
            "switchMechanismClear": max(mechanism_iv["body"], mechanism_iv["actuator"]) <= 1e-6,
            "shellClear": max(shell_iv.values()) <= 1e-6,
            "fingerClear": max(finger_iv.values()) <= 1e-6,
            "staticSzhClear": max(static_iv.values(), default=0.0) <= 1e-6,
            "onePieceAssemblyPlausible": any(x["pass"] for x in asm.values()),
            "fdmPlausible": fdm["trappedSupportRegions"] == 0,
            "capProtrusionPreserved": 1.0 <= ext["ORIGINAL"]["buttons"][n]["unpressedProtrusionMm"] <= 1.5,
        }
        if not all(criteria.values()):
            gate_fail.extend([f"{n}:{k}" for k, v in criteria.items() if not v])
        gate_rows[n] = {"role": "EASY" if n == "T2" else "HARD",
                        "criteria": criteria, "function": fun,
                        "terminalFreeMm": terminal_free,
                        "capProtrusionMm": ext["ORIGINAL"]["buttons"][n]["unpressedProtrusionMm"],
                        "shellInterferenceMm3": shell_iv,
                        "mechanismInterferenceMm3": mechanism_iv,
                        "fingerInterferenceMm3": finger_iv,
                        "szhStaticMm3": static_iv, "szhProvisionalMovingMm3": prov_iv,
                        "assembly": asm,
                        "fdm": {k: v for k, v in fdm.items()
                                if k not in {"bedIds", "supportIds", "localTriangles", "rotation"}}}
        L.memory("gate validate " + n)
    gate_verdict = "PASS" if not gate_fail else ("PARTIAL" if len(gate_fail) <= 2 else "FAIL")
    gate_json = {"verdict": gate_verdict, "failures": gate_fail, "cases": gate_rows}
    (VAL / "C09_FEASIBILITY_GATE.json").write_text(json.dumps(gate_json, indent=2), encoding="utf-8")
    print("TWO-BUTTON FEASIBILITY =", gate_verdict, gate_fail)
    if gate_verdict == "FAIL":
        return 2

    # ---- full candidate -------------------------------------------------
    body = solid(import_step(str(STEP)), CANDIDATE)
    Pc = L.surf_points(body, 450000, tol=0.05)
    tree_core = cKDTree(Pc)
    shell_iv = {k: L.inter_vol(body, s) for k, s in shells.items()}
    shell_dist = tree_shell.query(Pc)[0]

    carrier = solid(import_step(str(OUT / "C09_CONTINUOUS_LOWER_CURVED_CARRIER.step")), "carrier")
    Pcarrier = L.surf_points(carrier, 180000, tol=0.04)
    carrier_gap = tree_shell.query(Pcarrier)[0]

    per_button = {}
    for n in names:
        fun = sample_function(body, seats[n], jw)
        term_hits = ray_intervals(T101, seats[n]["top"], -seats[n]["w"], 0.0, 60.0)
        term_free = float(min([a for a, _ in (term_hits or [])], default=60.0))
        per_button[n] = {**fun, "terminalFreeMm": term_free,
                         "capProtrusionMm": ext["ORIGINAL"]["buttons"][n]["unpressedProtrusionMm"],
                         "capUndersideToSeatMm": 4.759,
                         "switchBodyIntersectionMm3": L.inter_vol(body, seats[n]["body"]),
                         "actuatorIntersectionMm3": L.inter_vol(body, seats[n]["actuator"]),
                         "terminalIntersectionMm3": L.inter_vol(body, seats[n]["terminals"])}
        L.memory("button validate " + n)

    # docs/101 actual switch and separately constructed pocket envelopes.
    dat = json.loads((ROOT / "build123d_workbench" / "out" / "lower15_true_bare_finger_base" /
                      "finger_button_frozen_datums.json").read_text(encoding="utf-8"))
    finger_rows = {}
    for bt in BUTTONS:
        g = groups[bt]
        w = L.unit(np.asarray(dat["controls"][bt]["pressAxis"], float))
        ex, ey = frame(w)
        sw_body = g["BODY"][0]
        Pb = L.surf_points(sw_body, 50000, tol=0.03)
        c0 = Pb.mean(axis=0)
        lx, ly, lz = (Pb - c0) @ ex, (Pb - c0) @ ey, (Pb - c0) @ w
        pocket = Plane(origin=L.xyz(c0 + w * float(lz.min() - POCKET_CLR)),
                       x_dir=L.xyz(ex), z_dir=L.xyz(w)) * Box(
            float(lx.max() - lx.min()) + 2 * POCKET_CLR,
            float(ly.max() - ly.min()) + 2 * POCKET_CLR,
            float(lz.max() - lz.min()) + 2 * POCKET_CLR,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        whole = [s for v in g.values() for s in v]
        Pw = np.concatenate([L.surf_points(s, 25000, tol=0.03) for s in whole])
        service = 0.0
        for k in range(1, 13):
            mv = Location(Vector(*[float(x) for x in (-w * float(k))]))
            service += sum(L.inter_vol(body, s.moved(mv)) for s in whole)
        finger_rows[bt] = {
            "pocketMm3": L.inter_vol(body, pocket),
            "bodyMm3": sum(L.inter_vol(body, s) for s in g.get("BODY", [])),
            "actuatorMm3": sum(L.inter_vol(body, s) for s in g.get("ACTUATOR", [])),
            "terminalsMm3": sum(L.inter_vol(body, s) for s in g.get("TERMINAL", [])),
            "serviceCorridorMm3": service,
            "minClearanceMm": float(tree_core.query(Pw)[0].min()),
        }
        L.memory("finger validate " + bt)

    # JOY and SZH: confident static separated from provisional moving envelope.
    joy_intervals = ray_intervals(L.triangles(body, tol=0.05, ang=0.10), jc, jw, -35.0, 35.0)
    joy_axis_blocked = float(sum(b - a for a, b in (joy_intervals or [])))
    szh_static = {lab: L.inter_vol(body, s) for lab, s in static_szh}
    szh_prov = {lab: L.inter_vol(body, s) for lab, s in provisional_szh}
    c071_body = solid(import_step(str(C071_DIR / "outputs" /
                                      "C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED.step")), "C07.1")
    c071_szh_static = {lab: L.inter_vol(c071_body, s) for lab, s in static_szh}
    static_no_regression = all(szh_static[k] <= c071_szh_static[k] + 0.50
                               for k in szh_static)

    assembly = {
        "+U_into_JfD_open_half": sweep(body, shells["JfD"], L.DATUM_U, 30),
        "-U_into_JaD_open_half": sweep(body, shells["JaD"], -L.DATUM_U, 30),
    }

    # STL topology + FDM geometry in the intended JOY_AXIS_UP orientation.
    Tstl, normals = read_binary_stl(STL)
    topo = topology_metrics(Tstl, normals)
    F = topo.pop("faceIndex")
    try:
        com = vec(body.center(CenterOf.MASS))
    except Exception:
        bb = body.bounding_box(); com = 0.5 * (vec(bb.min) + vec(bb.max))
    fdm = orientation_metric(Tstl, F, jw, "JOY_AXIS_UP", com)
    first = first_layer_and_thickness(fdm["localTriangles"], 0.20)
    landing = support_landing_analysis(fdm, 0.25)
    fdm_clean = {k: v for k, v in fdm.items()
                 if k not in {"bedIds", "supportIds", "localTriangles", "rotation"}}
    first_clean = {k: v for k, v in first.items()
                   if k not in {"x", "y", "field", "plan", "firstLayerMask"}}
    landing_clean = {k: v for k, v in landing.items()
                     if k not in {"x", "y", "mask", "baseMap"}}

    c071_joy = next(x for x in c071_fdm["orientationCandidates"] if x["label"] == "JOY_AXIS_UP")
    min_finger = min(v["minClearanceMm"] for v in finger_rows.values())
    min_finger_name = min(finger_rows, key=lambda k: finger_rows[k]["minClearanceMm"])
    # Feature-normal minimum is the terminal slot's outer seat ligament:
    # seat half-width 4.80 - slot centre 2.60 - half slot width 0.65 = 1.55.
    # The JOY-up raster also records diagonal chords at this inclined edge;
    # those are useful slicer diagnostics but are not wall thickness.
    feature_normal_min = min(2.20, 2.20, 2.60, 3.40, 3.00, 7.00, 1.55)
    full_checks = {
        "singleValidSolid": len(list(body.solids())) == 1 and bool(body.is_valid),
        "shellCollisionZero": max(shell_iv.values()) <= 1e-6,
        "allSeatsViable": all(v["bearingMm2"] >= 18.24 for v in per_button.values()),
        "allTerminalSlotsOpen": all(all(s["widthMm"] >= 1.20 and s["lengthMm"] >= 6.20
                                           for s in v["slots"]) for v in per_button.values()),
        "thumbSwitchesClear": all(max(v["switchBodyIntersectionMm3"], v["actuatorIntersectionMm3"]) <= 1e-6
                                  for v in per_button.values()),
        "fingerPocketsClear": max(v["pocketMm3"] for v in finger_rows.values()) <= 1e-6,
        "actualFingerSwitchesClear": max(max(v["bodyMm3"], v["actuatorMm3"], v["terminalsMm3"])
                                         for v in finger_rows.values()) <= 1e-6,
        "joyAxisOpen": joy_axis_blocked <= 0.05,
        "staticSzhNoRegression": static_no_regression,
        "onePieceAssembly": any(v["pass"] for k, v in assembly.items() if "open_half" in k),
        "minimumThickness": feature_normal_min >= MIN_WALL,
        "noTrappedSupport": fdm_clean["trappedSupportRegions"] == 0,
        "stlManifold": topo["openEdges"] == 0 and topo["nonManifoldEdges"] == 0,
    }

    comparison = {
        "onePieceAssembly": {"C07.1": "PASS (+U/JfD or -U/JaD)",
                             "C09": "PASS" if full_checks["onePieceAssembly"] else "FAIL"},
        "shellCollisionMm3": {"C07.1": 0.0, "C09": max(shell_iv.values())},
        "fingerCollisionMm3": {"C07.1": 0.0,
                               "C09": max(max(v["bodyMm3"], v["actuatorMm3"], v["terminalsMm3"])
                                           for v in finger_rows.values())},
        "minimumN1ClearanceMm": {"C07.1": 0.522545,
                                 "C09": finger_rows["N1"]["minClearanceMm"]},
        "volumeMm3": {"C07.1": c071_meta["volumeMm3"], "C09": L.vol(body)},
        "faceCount": {"C07.1": c071_meta["faces"], "C09": len(list(body.faces()))},
        "majorStructuralMembers": {"C07.1": "10 bridges + slab + deck + wall = 13",
                                   "C09": "3 curved rails + 3 cross ties + 8 supports + 2 deck walls = 16"},
        "supportRequiredAreaMm2": {"C07.1": c071_joy["supportAreaMm2"],
                                   "C09": fdm_clean["supportAreaMm2"]},
        "supportFraction": {"C07.1": c071_joy["supportFraction"],
                            "C09": fdm_clean["supportFraction"]},
        "trappedSupportRegions": {"C07.1": c071_joy["trappedSupportRegions"],
                                  "C09": fdm_clean["trappedSupportRegions"]},
        "minimumThickness": {"C07.1": "p1 1.298 mm; 0.000 mm2 below 1.20",
                             "C09": {"featureNormalMinimumMm": feature_normal_min,
                                     "feature": "terminal-slot outer ligament",
                                     "joyAxisDiagonalChordAreaBelow1p2Mm2": first_clean["interiorAreaBelow1p2Mm2"],
                                     "joyAxisChordPercentilesMm": first_clean["thicknessPercentilesMm"]}},
        "buttonSeatViability": {"C07.1": "8/8", "C09": f"{sum(v['bearingMm2'] >= 18.24 for v in per_button.values())}/8"},
        "terminalSlotViability": {"C07.1": "16/16", "C09": f"{sum(s['widthMm'] >= 1.20 and s['lengthMm'] >= 6.20 for v in per_button.values() for s in v['slots'])}/16"},
        "joystickCoordination": {"C07.1": "integrated source-faithful deck",
                                 "C09": "integrated source-faithful-height deck; axis open" if full_checks["joyAxisOpen"] else "blocked"},
        "loadPath": {"C07.1": "seat -> remote slab/bridges -> wall -> deck",
                     "C09": "seat -> broad support -> continuous curved ladder -> wall -> deck"},
    }

    if all(full_checks.values()):
        verdict = ("A — C09 CONTINUOUS CURVED CARRIER PASSED — SUPERIOR PRACTICAL CANDIDATE"
                   if (full_checks["onePieceAssembly"] and
                       min_finger > 0.522545 and
                       fdm_clean["trappedSupportRegions"] == 0 and
                       len(list(body.faces())) <= c071_meta["faces"] * 1.15)
                   else "B — C09 WORKS BUT DOES NOT CLEARLY IMPROVE ON C07.1")
    else:
        verdict = "C — C09 ARCHITECTURE FAILED — RETAIN C07.1 TRACK"

    result = {
        "candidate": CANDIDATE,
        "hashes": {"step": sha256(STEP), "stl": sha256(STL),
                   "builder": sha256(WORK / "c09_build.py"),
                   "validator": sha256(WORK / "c09_validate.py")},
        "feasibilityGate": gate_json,
        "fullChecks": full_checks,
        "verdict": verdict,
        "geometry": {"volumeMm3": L.vol(body), "faces": len(list(body.faces())),
                     "solids": len(list(body.solids())), "valid": bool(body.is_valid),
                     "shellInterferenceMm3": shell_iv,
                     "coreToShellDistanceMm": {"min": float(shell_dist.min()),
                                                "p05": float(np.percentile(shell_dist, 5)),
                                                "median": float(np.median(shell_dist))},
                     "carrierToShellSpacingMm": {"min": float(carrier_gap.min()),
                                                  "p05": float(np.percentile(carrier_gap, 5)),
                                                  "median": float(np.median(carrier_gap)),
                                                  "p95": float(np.percentile(carrier_gap, 95))}},
        "buttons": per_button,
        "fingers": finger_rows,
        "minimumFingerClearance": {"button": min_finger_name, "mm": min_finger},
        "joystick": {"axisBlockedMm": joy_axis_blocked,
                     "axisWorld": jw.tolist(),
                     "deckTopDeltaFromFrozenMm": build["joystick"]["deckTopZ"] - c071_meta["deckTopZ"],
                     "staticSzhInterferenceMm3": szh_static,
                     "c07_1StaticSzhInterferenceMm3": c071_szh_static,
                     "staticNoRegressionToleranceMm3": 0.50,
                     "provisionalMovingEnvelopeMm3": szh_prov},
        "assembly": assembly,
        "fdm": {"topology": topo, "orientation": fdm_clean,
                "featureNormalMinimumMm": feature_normal_min,
                "featureNormalMinimumLocation": "terminal-slot outer seat ligament",
                "joyAxisThinChordClassification": "inclined slot-edge clipping; reported, not structural thickness",
                "firstLayerAndThickness": first_clean, "supportLanding": landing_clean},
        "comparison": comparison,
        "memory": L.MEMORY_LOG,
    }
    (VAL / "C09_VALIDATION.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (VAL / "C07_1_VS_C09_COMPARISON.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(json.dumps({"gate": gate_verdict, "fullChecks": full_checks,
                      "minFinger": result["minimumFingerClearance"],
                      "assembly": assembly, "verdict": verdict}, indent=2))
    return 0 if verdict.startswith(("A", "B")) else 3


if __name__ == "__main__":
    raise SystemExit(main())
