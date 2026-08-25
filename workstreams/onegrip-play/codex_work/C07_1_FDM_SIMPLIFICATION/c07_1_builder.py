"""C07.1 conservative manufacturing simplification, isolated Codex candidate.

This builder is descended from REV_I i10_c07_refine.py.  Frozen seat, slot,
button-stack, JOY and deck datums are retained.  The changes in this isolated
probe are structural only:

* replace the distance-generated 16-bridge graph with ten explicit orthogonal
  load paths matching the three seat rows/columns;
* omit C07's three dynamically placed shell pads, whose re-entrant faces caused
  the independently measured trapped-support and deck-top support-base risks.

The original C07 files are input authority and are never overwritten.

C06 held the right functional architecture in awkward geometry: eight 9 x 9 mm
plate tiles each tilted 0-9.4 deg to its neighbour, twenty tilted webs joining
them, five inclined links to the joystick deck, and 27.36 mm2 of 0.32-0.89 mm
feather edge where all those tilted planes met.  Every one of those slivers is a
union artefact, not a designed feature, and none of them survives a slicer.

C07 keeps every functional number and rebuilds the connective geometry around one
print direction.

PRINT ORIENTATION (chosen first, then designed for):

    PRINT_UP = the JOY axis, outward.  Bed is perpendicular to it, at the lowest
    point of the part, which is the joystick deck underside.

    Why: the eight seat planes lie 1.84-9.38 deg off this axis, so every bearing
    face and every slot wall points up or runs vertical -- no support ever
    touches a switch or joystick interface.  The slab bottom becomes a single
    flat plane perpendicular to the bed instead of eight tilted tiles.

GEOMETRY RULES USED

    * every side wall is parallel to PRINT_UP -> self-supporting
    * every horizontal face is either up-facing or the bed
    * no tilted plate meets another tilted plate; steps between seats are
      vertical faces, not wedges
    * one flat slab bottom, so thickness runs 2.60 mm (lowest seat) to 7.19 mm
      (highest) instead of a nominal 2.003 mm that feathered to 0.32 mm

FUNCTIONAL NUMBERS CARRIED OVER UNCHANGED

    cap underside -> plate top   4.759 mm
    bearing                      6.02 x 6.04 mm flat, no boss or recess
    terminal slots               2 x (1.30 x 6.40) at +-2.60 mm
    joystick deck                23.993 mm below the skin, module bears on it
    all eight frozen axes and centres
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Box, Location, Plane, Vector, export_step,
                       export_stl, extrude, import_step, make_face, Polyline)

REV_I_SCRIPTS = (Path(__file__).resolve().parents[2] / "thumb_inner_housing_lab" /
                 "REV_I_SOURCE_FAITHFUL_THUMB_PROTOTYPE" / "10_scripts")
sys.path.insert(0, str(REV_I_SCRIPTS))
import labutil as L  # noqa: E402
from b01_true_axes import ORDER  # noqa: E402
from b03_axis_authority import ray_intervals  # noqa: E402
from h03_placement import KEEPOUTS, seat_solids  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402

WORK = Path(__file__).resolve().parent
OUT = WORK / "outputs"

COL_XY = 9.6          # per-seat column in the print plan; covers any rotation of
                      # the 6.5 x 6.4 mm slot pattern (half-diagonal 4.55 < 4.8)
BRIDGE_W = 5.6        # slab bridge between adjacent seat columns
SLAB_MIN_T = 2.60     # thickness under the LOWEST seat plane
RELIEF_XY = 8.6       # clearance column above each plate plane: switch + cap
BRIDGE_DROP = 0.60    # bridges stop below the lower of the two seat planes
DECK_T = 3.0
DECK_APERTURE = 6.0
WALL_T = 2.6          # vertical deck-to-slab walls
SLOT_W, SLOT_L, SLOT_OFFSET = 1.30, 6.40, 2.60
SHELL_CLR = 0.35
SCREW_CLR = 1.00
KNOB_ENGAGE = 6.0
PAD_XY, PAD_CHAMFER = 5.0, 1.2


def solid(x, tag):
    s, _ = L.as_single_solid(x, tag)
    return s


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    stage = int(sys.argv[sys.argv.index("--stage") + 1]) if "--stage" in sys.argv else 99
    core = json.loads((L.LAB / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joy = json.loads((L.LAB / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    orig = json.loads((L.LAB / "03_original_joystick" /
                       "i03_original_joystick_architecture.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    shell = [solid(import_step(L.SRC[k]), k) for k in ("JAD_APPROVED", "JFD_APPROVED")]
    Tsh = np.concatenate([L.triangles(s, tol=0.06, ang=0.12) for s in shell])
    L.memory("shell")

    # ---- print frame ----------------------------------------------------
    jw = L.unit(np.asarray(joy["joyAxisWorld"], float))
    jc = np.asarray(joy["knobCentreWorld"], float)
    jex, jey = frame(jw)
    skin = joy["currentSkinOnAxisMm"]

    def zh(p):
        return float((np.asarray(p, float) - jc) @ jw)

    def platform(p, z):
        """A point at lateral position of p, raised to height z."""
        q = np.asarray(p, float) - jc
        return jc + (q - jw * float(q @ jw)) + jw * z

    def pbox(p, sx, sy, z0, z1, ang=0.0, label="B"):
        ex = jex * np.cos(ang) + jey * np.sin(ang)
        b = Plane(origin=L.xyz(platform(p, z0)), x_dir=L.xyz(ex), z_dir=L.xyz(jw)) * Box(
            sx, sy, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        b.label = label
        return b

    def sbox(o, ex, w, sx, sy, n0, n1, label="S"):
        b = Plane(origin=L.xyz(np.asarray(o, float) + w * n0),
                  x_dir=L.xyz(ex), z_dir=L.xyz(w)) * Box(
            sx, sy, n1 - n0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        b.label = label
        return b

    seats = {}
    for s in names:
        r = core["seats"][s]
        w = np.asarray(r["axisWorld"], float)
        u = seat_solids(np.asarray(r["capUndersideWorld"], float), w, s)
        seats[s] = {"w": w, "top": u["plateTopPoint"], "ex": u["ex"], "ey": u["ey"],
                    "z": zh(u["plateTopPoint"]), "body": u["body"],
                    "term": u["terminals"], "act": u["actuator"]}
    z_lo = min(seats[s]["z"] for s in names)
    z_hi = max(seats[s]["z"] for s in names)
    slab_bot = z_lo - SLAB_MIN_T
    deck_top = skin - 23.993
    deck_bot = deck_top - DECK_T
    print("print frame: PRINT_UP = JOY axis outward, bed at z = %.3f" % deck_bot)
    print("  seat planes z %.3f .. %.3f (spread %.3f), tilt to PRINT_UP 1.84-9.38 deg"
          % (z_lo, z_hi, z_hi - z_lo))
    print("  slab: flat bottom z %.3f, thickness %.2f .. %.2f mm"
          % (slab_bot, SLAB_MIN_T, z_hi - slab_bot))
    print("  deck: top z %.3f, bottom z %.3f (bed)" % (deck_top, deck_bot))

    # ---- 1 slab: vertical-walled columns + bridges -----------------------
    body = None
    for s in names:
        c = pbox(seats[s]["top"], COL_XY, COL_XY, slab_bot, z_hi + 3.0, 0.0, "COL_" + s)
        body = c if body is None else (body + c).clean()
    # Explicit, readable load graph: three longitudinal rails and five cross
    # ties.  C07's distance rule also added diagonal/redundant pairs, producing
    # sixteen overlapping bridges and many short Boolean remnants.
    bridge_pairs = [
        ("T1", "T5"), ("T5", "T3"),
        ("T4", "T2"), ("T2", "T6"),
        ("T7", "T8"),
        ("T1", "T4"), ("T5", "T2"), ("T3", "T6"),
        ("T4", "T7"), ("T6", "T8"),
    ]
    pairs = []
    for sa, sb in bridge_pairs:
        a, b = seats[sa], seats[sb]
        d = float(np.linalg.norm(a["top"] - b["top"]))
        pairs.append((sa, sb, d))
        mid = 0.5 * (a["top"] + b["top"])
        ax = b["top"] - a["top"]
        ax = ax - jw * float(ax @ jw)
        th = float(np.arctan2(ax @ jey, ax @ jex))
        top = min(a["z"], b["z"]) - BRIDGE_DROP
        br = pbox(mid, d, BRIDGE_W, slab_bot, top, th, "BR_" + sa + "_" + sb)
        body = (body + br).clean()
    body = solid(body, "SLAB")
    print("1 slab prism  vol %9.3f  solids %d  bridges %d"
          % (L.vol(body), len(list(body.solids())), len(pairs)))
    L.memory("slab")
    if stage < 2:
        return 0

    # ---- 2 face the top to each seat plane ------------------------------
    for s in names:
        u = seats[s]
        above = sbox(u["top"], u["ex"], u["w"], 90.0, 90.0, 0.0, 60.0, "ABOVE")
        col = pbox(u["top"], COL_XY + 0.001, COL_XY + 0.001, slab_bot, z_hi + 4.0, 0.0, "C")
        tool = (col & above).clean()
        if tool.solids() and L.inter_vol(body, tool) > 1.0e-9:
            body = solid((body - tool).clean(), "SLAB")
    print("2 top faced to the eight seat planes   vol %9.3f  solids %d"
          % (L.vol(body), len(list(body.solids()))))
    L.memory("faced")
    if stage < 3:
        return 0

    # ---- 3 joystick deck -------------------------------------------------
    rad, ang = [], []
    for th in np.arange(0.0, 2 * np.pi - 1e-9, np.pi / 36.0):
        d = jex * np.cos(th) + jey * np.sin(th)
        rr = []
        for zz in (deck_bot, 0.5 * (deck_bot + deck_top), deck_top):
            h = ray_intervals(Tsh, jc + jw * zz, d, 0.0, 60.0)
            if h:
                rr.append(float(h[0][0]))
        if rr:
            rad.append(max(0.0, min(rr) - SHELL_CLR))
            ang.append(float(th))
    rad = np.asarray(rad)
    pts = [L.xyz(jc + jw * deck_bot + jex * (r * np.cos(t)) + jey * (r * np.sin(t)))
           for r, t in zip(rad, ang)]
    deck = extrude(make_face(Polyline(*pts, close=True)), amount=DECK_T, dir=L.xyz(jw))
    ap = pbox(jc, 2 * DECK_APERTURE, 2 * DECK_APERTURE, deck_bot - 1.0, deck_top + 1.0, 0.0, "AP")
    deck = solid((deck - ap).clean(), "DECK")
    print("3 deck  r %.2f..%.2f  vol %9.3f  shell overlap %.4f"
          % (rad.min(), rad.max(), L.vol(deck),
             sum(L.inter_vol(deck, s) for s in shell)))
    L.memory("deck")
    if stage < 4:
        return 0

    # ---- 4 one broad deck-to-carrier wall -------------------------------
    body = (body + deck).clean()
    # C07 used five short radial boxes.  Their separate ends left a narrow
    # unsupported carrier-edge stripe whose generated support could base on
    # the joystick deck.  T7/T8 share a straight carrier-facing edge at
    # jex ~= -13.4 mm from the JOY centre.  One continuous chord wall is both
    # simpler and stronger, reaches both columns with a robust overlap, and is
    # vertical in print coordinates from the bed upward.
    chord_mid = jc + jex * -14.0
    wall = pbox(chord_mid, WALL_T, 26.0, deck_top - DECK_T,
                slab_bot + 0.6, 0.0, "MAJOR_CHORD_WALL")
    body = solid((body + wall).clean(), "CORE")
    nwall = 1
    body = solid(body, "CORE")
    print("4 vertical deck-to-slab walls %d   vol %9.3f  solids %d"
          % (nwall, L.vol(body), len(list(body.solids()))))
    L.memory("walls")
    if stage < 5:
        return 0

    # ---- 5 keep-outs and shell guard ------------------------------------
    keep = import_step(str(KEEPOUTS))
    ko = {}
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if ch.solids() and not lab.startswith("CAP_"):
            ko[lab] = solid(ch, lab)
    static = {}
    v0 = L.vol(body)
    for d in (np.zeros(3), L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V,
              L.DATUM_N, -L.DATUM_N):
        for sh in shell:
            t = sh if not np.any(d) else sh.moved(
                Location(Vector(*[float(x) for x in (d * SHELL_CLR)])))
            if L.inter_vol(body, t) > 1.0e-9:
                body = solid((body - t).clean(), "CORE")
    print("5 shell guard removed %.3f mm3" % (v0 - L.vol(body)))
    sl = sorted(body.solids(), key=lambda x: -float(x.volume))
    debris = [float(x.volume) for x in sl[1:]]
    if debris:
        print("   dropped %d fragment(s): %s"
              % (len(debris), ", ".join("%.3f" % d for d in debris)))
    body = sl[0]
    L.memory("guard")
    if stage < 6:
        return 0

    # ---- 6 remove dynamic shell pads ------------------------------------
    # C07's three nearest-point pads are not frozen functional datums.  Their
    # box-union implementation did not form the documented taper and created a
    # 14.607 mm2 re-entrant down-facing region plus projected support bases on
    # the joystick deck.  This conservative probe omits them; the carrier and
    # deck wall system remain the load path.  docs/101 shell/Finger clearances
    # are remeasured after export.
    added, below = 0, 0
    print("6 dynamic shell pads omitted for C07.1 FDM simplification")
    L.memory("pads")
    if stage < 7:
        return 0

    # ---- 7 switch, cap and terminal clearance, applied LAST -------------
    # C06 and the first C07 cut these before the walls and pads existed, so a
    # later addition put 26.1 mm3 back into a switch body and re-covered one of
    # T2's terminal slots.  Anything that adds material must run before the
    # clearances, not after.
    # keep-out relief, AFTER every additive stage.  Running it before the
    # standoff pads let the pads put 26.5 mm3 straight back into the N1/N2
    # keep-out -- the same ordering mistake as the switch clearance.
    for lab, ks in ko.items():
        if not (lab.startswith("ORIGINAL_SCREW") or "N1_N2" in lab.upper()):
            continue
        v0 = L.vol(body)
        for d in (np.zeros(3), L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V,
                  L.DATUM_N, -L.DATUM_N):
            t = ks if not np.any(d) else ks.moved(
                Location(Vector(*[float(x) for x in (d * SCREW_CLR)])))
            if L.inter_vol(body, t) > 1.0e-9:
                body = solid((body - t).clean(), "CORE")
        static[lab] = v0 - L.vol(body)
    print("   keep-out relief %s"
          % ", ".join("%s %.1f" % (k.split("_")[-1], v) for k, v in static.items()))
    rem = 0.0
    for s in names:
        u = seats[s]
        tool = sbox(u["top"], u["ex"], u["w"], RELIEF_XY, RELIEF_XY, 0.0, 26.0, "RELIEF")
        if L.inter_vol(body, tool) > 1.0e-9:
            v0 = L.vol(body)
            body = solid((body - tool).clean(), "CORE")
            rem += v0 - L.vol(body)
    cut = 0
    for s in names:
        u = seats[s]
        for sgn in (-1.0, 1.0):
            o = u["top"] + u["ex"] * (sgn * SLOT_OFFSET)
            tool = sbox(o, u["ex"], u["w"], SLOT_W, SLOT_L,
                        -(z_hi - slab_bot) - 12.0, 1.0, "SLOT")
            if L.inter_vol(body, tool) > 1.0e-9:
                body = solid((body - tool).clean(), "CORE")
                cut += 1
    print("7 switch + cap clearance %.3f mm3 ; terminal slots cut %d of 16" % (rem, cut))
    sl = sorted(body.solids(), key=lambda x: -float(x.volume))
    if len(sl) > 1:
        print("   dropped %d fragment(s) after clearance: %s"
              % (len(sl) - 1, ", ".join("%.3f" % float(x.volume) for x in sl[1:])))
    body = sl[0]
    L.memory("clearance")

    body = solid(body, "CORE")
    body.label = "C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED"
    print("")
    print("C07: vol %.3f  faces %d  solids %d  valid %s"
          % (L.vol(body), len(list(body.faces())), len(list(body.solids())),
             bool(body.is_valid)))
    export_step(body, str(OUT / "C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED.step"))
    export_stl(body, str(OUT / "C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED.stl"),
               tolerance=0.03, angular_tolerance=0.10)

    L.write_json(OUT / "c07_1_build.json",
                 {"printUpWorld": jw.tolist(), "printOrigin": jc.tolist(),
                  "bedHeightZ": deck_bot, "slabBottomZ": slab_bot,
                  "seatPlaneZ": {s: seats[s]["z"] for s in names},
                  "slabThicknessMm": [SLAB_MIN_T, z_hi - slab_bot],
                  "columnXY": COL_XY, "bridgeWidth": BRIDGE_W, "reliefXY": RELIEF_XY,
                  "deckTopZ": deck_top, "deckThicknessMm": DECK_T,
                  "deckApertureMm": 2 * DECK_APERTURE,
                  "deckRadiusMm": [float(rad.min()), float(rad.max())],
                  "verticalWalls": nwall, "wallThicknessMm": WALL_T,
                  "slotsCut": cut, "switchCapReliefMm3": rem,
                  "szhRaiseMm": 5.238983096144226,
                  "deckTopAboveSkinMm": deck_top - skin,
                  "deckCavityRadiusMm": {"min": float(rad.min()),
                                         "max": float(rad.max())},
                  "screwReliefMm3": static, "droppedFragmentsMm3": debris,
                  "candidate": "C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED",
                  "sourceAuthority": str(L.LAB / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step"),
                  "explicitBridgePairs": [[a, b] for a, b, _ in pairs],
                  "standoffs": added, "standoffsSkippedBelowBed": below, "padXY": 0.0, "padChamferMm": 0.0,
                  "volumeMm3": L.vol(body), "faces": len(list(body.faces())),
                  "solids": len(list(body.solids())), "valid": bool(body.is_valid),
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
