"""C09 independent continuous curved under-carrier Thumb core.

All outputs stay in this isolated directory.  Frozen Thumb cap centres, press
axes, seat planes, JOY axis and JOY deck height come from the validated REV_I
source-faithful metadata.  The docs/101 JaD/JfD shells are read-only guards.

Architecture:
    one continuous curved ladder carrier (3 longitudinal curved rails +
    3 broad cross ties) below the Thumb row
      -> one broad upward support per button
      -> one flat seat whose normal is the frozen button press axis

This deliberately has no shell-conformal collars and no opening-by-opening
landings.  The carrier is a smooth, inward-offset frame rather than the C07
remote slab.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Box, Compound, Location, Plane, Polyline, Vector,
                       export_step, export_stl, extrude, import_step, loft,
                       make_face)

ROOT = Path(r"C:\Users\User\Desktop\OneGrip-Play")
WORK = ROOT / "codex_work" / "C09_CONTINUOUS_CURVED_CARRIER"
OUT = WORK / "outputs"
GATE = WORK / "gate"
REV_I = ROOT / "thumb_inner_housing_lab" / "REV_I_SOURCE_FAITHFUL_THUMB_PROTOTYPE"
REV_K_SCRIPTS = ROOT / "thumb_inner_housing_lab" / "REV_K_C08_LOCAL_CONFORMAL_RECEIVER" / "10_scripts"
sys.path.insert(0, str(REV_K_SCRIPTS))

import labutil as L  # noqa: E402
from b01_true_axes import ORDER  # noqa: E402
from b03_axis_authority import ray_intervals  # noqa: E402
from h01_seat_audit import axis_frame  # noqa: E402
from h03_placement import KEEPOUTS, seat_solids  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402


CANDIDATE = "C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE"
CAP_TO_SEAT = 4.759
SEAT_T = 2.60
SEAT_XY = 9.60
RELIEF_XY = 8.60
SUPPORT_XY = 7.00
SLOT_W, SLOT_L, SLOT_OFF = 1.30, 6.40, 2.60

# Carrier dimensions: deliberately structural at 0.4-mm-nozzle scale.
RAIL_W = 4.40
RAIL_T = 2.20
CROSS_W = 4.60
CROSS_T = 2.20
RAIL_Y = (-10.5, 0.0, 10.5)
CURVE_X = np.asarray((-43.0, -40.0, -36.0, -31.0, -26.0, -21.0, -16.0), float)
CURVE_Z = np.asarray((-13.15, -12.82, -12.05, -10.85, -9.95, -9.15, -8.55), float)
CROSS_X = (-40.6, -30.3, -16.3)

DECK_T = 3.0
DECK_APERTURE_R = 6.0
DECK_TO_SKIN = 23.993
SHELL_CLR = 0.45
WALL_T = 3.40


def solid(shape, tag):
    s, _ = L.as_single_solid(shape, tag)
    return s


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    GATE.mkdir(parents=True, exist_ok=True)
    core_j = json.loads((REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joy_j = json.loads((REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    shells = {}
    for tag, key in (("JaD", "D101_JAD"), ("JfD", "D101_JFD")):
        shells[tag] = solid(import_step(L.SRC[key]), tag)
    shell_tris = np.concatenate([L.triangles(s, tol=0.06, ang=0.12) for s in shells.values()])
    L.memory("shell authority")

    jw = L.unit(np.asarray(joy_j["joyAxisWorld"], float))
    jc = np.asarray(joy_j["knobCentreWorld"], float)
    jex, jey = frame(jw)
    skin = float(joy_j["currentSkinOnAxisMm"])

    def local_point(x, y, z):
        return jc + jex * float(x) + jey * float(y) + jw * float(z)

    def coords(p):
        d = np.asarray(p, float) - jc
        return np.asarray((d @ jex, d @ jey, d @ jw), float)

    def curve_z(x):
        return float(np.interp(float(x), CURVE_X, CURVE_Z))

    def pbox(x, y, z0, sx, sy, z1, label="B"):
        b = Plane(origin=L.xyz(local_point(x, y, z0)), x_dir=L.xyz(jex), z_dir=L.xyz(jw)) * Box(
            float(sx), float(sy), float(z1 - z0),
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        b.label = label
        return b

    def sbox(origin, ex, w, sx, sy, n0, n1, label="S"):
        b = Plane(origin=L.xyz(np.asarray(origin, float) + w * float(n0)),
                  x_dir=L.xyz(ex), z_dir=L.xyz(w)) * Box(
            float(sx), float(sy), float(n1 - n0),
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        b.label = label
        return b

    def rail(y, x_values=CURVE_X, label="RAIL"):
        faces = []
        for x in x_values:
            z = curve_z(float(x))
            c = local_point(x, y, z)
            pts = [L.xyz(c + jey * (sy * RAIL_W / 2.0) + jw * (sz * RAIL_T / 2.0))
                   for sy, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            faces.append(make_face(Polyline(*pts, close=True)))
        r = loft(faces, ruled=False)
        r.label = label
        return r

    def full_carrier():
        parts = [rail(y, label=f"CURVED_RAIL_{i+1}") for i, y in enumerate(RAIL_Y)]
        for i, x in enumerate(CROSS_X):
            z = curve_z(x)
            parts.append(pbox(x, 0.0, z - CROSS_T / 2.0, CROSS_W, 26.0,
                              z + CROSS_T / 2.0, f"BROAD_CROSS_TIE_{i+1}"))
        body = parts[0]
        for p in parts[1:]:
            body = (body + p).clean()
        return solid(body, "CONTINUOUS_CURVED_CARRIER")

    seats = {}
    for name in names:
        r = core_j["seats"][name]
        w = L.unit(np.asarray(r["axisWorld"], float))
        u = seat_solids(np.asarray(r["capUndersideWorld"], float), w, name)
        ex, ey = axis_frame(w)
        q = coords(u["plateTopPoint"])
        seats[name] = {"name": name, "w": w, "ex": ex, "ey": ey,
                       "top": np.asarray(u["plateTopPoint"], float),
                       "x": float(q[0]), "y": float(q[1]), "z": float(q[2]),
                       "body": u["body"], "terminals": u["terminals"],
                       "actuator": u["actuator"]}

    def add_seat_support(body, name):
        u = seats[name]
        # Flat seat is defined in the frozen press frame.  Its top plane is
        # exactly the frozen REV_I plane; no opening or axis moves.
        plate = sbox(u["top"], u["ex"], u["w"], SEAT_XY, SEAT_XY,
                     -SEAT_T, 0.0, "FLAT_SEAT_" + name)
        base_centre_z = curve_z(u["x"])
        # Broad printable post rises in JOY-up coordinates.  It overlaps both
        # the carrier and the tilted seat by >=0.40 mm; later cuts provide the
        # two unobstructed terminal paths.
        # The post overlaps the 2.60 mm tilted seat by design.  Feature-normal
        # minimum at the nearby terminal-slot outer ligament is 1.55 mm; a
        # JOY-axis raster can clip that inclined edge diagonally and report a
        # smaller non-structural chord (kept separately in validation).
        top_z = u["z"] - 1.60
        post = pbox(u["x"], u["y"], base_centre_z - 0.65,
                    SUPPORT_XY, SUPPORT_XY, top_z,
                    "UPWARD_SUPPORT_" + name)
        body = solid((body + post + plate).clean(), "C09")
        # Existing source-faithful body/cap clearance above the seat.
        relief = sbox(u["top"], u["ex"], u["w"], RELIEF_XY, RELIEF_XY,
                      0.001, 16.0, "SWITCH_CAP_RELIEF_" + name)
        if L.inter_vol(body, relief) > 1e-9:
            body = solid((body - relief).clean(), "C09")
        for sgn in (-1.0, 1.0):
            o = u["top"] + u["ex"] * (sgn * SLOT_OFF)
            slot = sbox(o, u["ex"], u["w"], SLOT_W, SLOT_L,
                        -18.0, 1.0, "TERMINAL_SLOT_" + name)
            if L.inter_vol(body, slot) > 1e-9:
                body = solid((body - slot).clean(), "C09")
        return body

    # ---- first feasibility geometry: EASY T2 and HARD T8 only -----------
    gate_records = {}
    for name, x0, x1, y0 in (("T2", -36.0, -25.0, 0.0),
                              ("T8", -22.0, -14.0, -8.2)):
        xs = np.linspace(x0, x1, 5)
        unit = rail(y0, xs, "LOCAL_CURVED_CARRIER_" + name)
        # A local transverse foot makes the gate representative of the full
        # ladder junction and prevents a tangent-only post/rail join.
        u = seats[name]
        zc = curve_z(u["x"])
        foot = pbox(u["x"], y0, zc - CROSS_T / 2.0,
                    CROSS_W, 12.0, zc + CROSS_T / 2.0,
                    "LOCAL_CROSS_FOOT_" + name)
        unit = solid((unit + foot).clean(), "C09_GATE_" + name)
        unit = add_seat_support(unit, name)
        unit.label = "C09_GATE_" + name
        export_step(unit, str(GATE / f"C09_GATE_{name}.step"))
        export_stl(unit, str(GATE / f"C09_GATE_{name}.stl"),
                   tolerance=0.03, angular_tolerance=0.10)
        gate_records[name] = {"volumeMm3": L.vol(unit),
                              "faces": len(list(unit.faces())),
                              "valid": bool(unit.is_valid),
                              "solids": len(list(unit.solids())),
                              "role": "EASY" if name == "T2" else "HARD"}
        L.memory("gate build " + name)

    # ---- full eight-button carrier -------------------------------------
    carrier = full_carrier()
    carrier.label = "C09_CONTINUOUS_LOWER_CURVED_CARRIER"
    export_step(carrier, str(OUT / "C09_CONTINUOUS_LOWER_CURVED_CARRIER.step"))
    body = carrier
    for name in names:
        body = add_seat_support(body, name)
        L.memory("full seat " + name)

    # ---- JOY deck at the exact validated source-faithful height ---------
    deck_top = skin - DECK_TO_SKIN
    deck_bot = deck_top - DECK_T
    radii, angles = [], []
    for th in np.arange(0.0, 2 * np.pi - 1e-9, np.pi / 36.0):
        d = jex * np.cos(th) + jey * np.sin(th)
        rr = []
        for zz in (deck_bot, 0.5 * (deck_bot + deck_top), deck_top):
            h = ray_intervals(shell_tris, jc + jw * zz, d, 0.0, 60.0)
            if h:
                rr.append(float(h[0][0]))
        if rr:
            radii.append(max(0.0, min(rr) - SHELL_CLR))
            angles.append(float(th))
    pts = [L.xyz(jc + jw * deck_bot + jex * (r * np.cos(t)) + jey * (r * np.sin(t)))
           for r, t in zip(radii, angles)]
    deck = extrude(make_face(Polyline(*pts, close=True)), amount=DECK_T, dir=L.xyz(jw))
    aperture = pbox(0.0, 0.0, deck_bot - 1.0, 2 * DECK_APERTURE_R,
                    2 * DECK_APERTURE_R, deck_top + 1.0, "JOY_APERTURE")
    deck = solid((deck - aperture).clean(), "SOURCE_FAITHFUL_JOY_DECK")

    # Two broad side walls connect the inner curved rails to the deck while
    # leaving the central SZH PCB/header corridor open.  A single full-width
    # chord wall was geometrically valid but added static package overlap.
    walls = [pbox(-14.5, y, deck_bot, WALL_T, 5.20,
                  curve_z(-16.0) + 0.7, f"SIDE_DECK_CARRIER_WALL_{i+1}")
             for i, y in enumerate((-10.5, 10.5))]
    body = solid((body + deck + walls[0] + walls[1]).clean(), "C09")
    export_step(deck, str(OUT / "C09_SOURCE_FAITHFUL_JOY_DECK.step"))
    export_step(Compound(children=walls, label="C09_SIDE_DECK_WALLS"),
                str(OUT / "C09_SIDE_DECK_WALLS.step"))

    # Static keep-outs and shell are guarded after every additive feature.
    keep = import_step(str(KEEPOUTS))
    keepouts = []
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if ch.solids() and (lab.startswith("ORIGINAL_SCREW") or "N1_N2" in lab.upper()):
            keepouts.append((lab, solid(ch, lab)))
    removed_keepout = {}
    for lab, ko in keepouts:
        v0 = L.vol(body)
        if L.inter_vol(body, ko) > 1e-9:
            body = solid((body - ko).clean(), "C09")
        removed_keepout[lab] = v0 - L.vol(body)

    shell_removed = 0.0
    for sh in shells.values():
        if L.inter_vol(body, sh) > 1e-9:
            v0 = L.vol(body)
            body = solid((body - sh).clean(), "C09")
            shell_removed += v0 - L.vol(body)

    # Re-cut every functional void last so no wall/deck addition can refill it.
    for name in names:
        u = seats[name]
        relief = sbox(u["top"], u["ex"], u["w"], RELIEF_XY, RELIEF_XY,
                      0.001, 16.0, "FINAL_RELIEF_" + name)
        if L.inter_vol(body, relief) > 1e-9:
            body = solid((body - relief).clean(), "C09")
        for sgn in (-1.0, 1.0):
            o = u["top"] + u["ex"] * (sgn * SLOT_OFF)
            slot = sbox(o, u["ex"], u["w"], SLOT_W, SLOT_L,
                        -18.0, 1.0, "FINAL_SLOT_" + name)
            if L.inter_vol(body, slot) > 1e-9:
                body = solid((body - slot).clean(), "C09")

    comps = sorted(body.solids(), key=lambda s: -float(s.volume))
    debris = [float(s.volume) for s in comps[1:]]
    body = comps[0]
    body.label = CANDIDATE
    export_step(Compound(children=[body], label=CANDIDATE),
                str(OUT / f"{CANDIDATE}.step"))
    export_stl(body, str(OUT / f"{CANDIDATE}.stl"),
               tolerance=0.03, angular_tolerance=0.10)

    seat_meta = {n: {"plateTopWorld": seats[n]["top"].tolist(),
                     "axisWorld": seats[n]["w"].tolist(),
                     "joyFrameXYZ": [seats[n]["x"], seats[n]["y"], seats[n]["z"]],
                     "capUndersideToSeatMm": CAP_TO_SEAT,
                     "seatThicknessMm": SEAT_T,
                     "supportXYMm": SUPPORT_XY,
                     "carrierCentreZMm": curve_z(seats[n]["x"])} for n in names}
    result = {
        "candidate": CANDIDATE,
        "architecture": "continuous curved ladder under-carrier + 8 upward supports + frozen flat seats",
        "gateCases": gate_records,
        "carrier": {"longitudinalRails": 3, "broadCrossTies": 3,
                    "railWidthMm": RAIL_W, "railThicknessMm": RAIL_T,
                    "crossTieWidthMm": CROSS_W, "crossTieThicknessMm": CROSS_T,
                    "curveX": CURVE_X.tolist(), "curveZ": CURVE_Z.tolist()},
        "seats": seat_meta,
        "joystick": {"axisWorld": jw.tolist(), "originWorld": jc.tolist(),
                     "deckTopZ": deck_top, "deckBottomZ": deck_bot,
                     "deckThicknessMm": DECK_T, "apertureDiameterMm": 2 * DECK_APERTURE_R,
                     "deckRadiusMm": [float(min(radii)), float(max(radii))],
                     "deckTopBelowSkinMm": DECK_TO_SKIN},
        "keepoutRemovedMm3": removed_keepout,
        "shellRemovedMm3": shell_removed,
        "droppedFragmentsMm3": debris,
        "volumeMm3": L.vol(body), "faces": len(list(body.faces())),
        "solids": len(list(body.solids())), "valid": bool(body.is_valid),
        "memory": L.MEMORY_LOG,
    }
    (OUT / "c09_build.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("candidate", "volumeMm3", "faces", "solids", "valid")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
