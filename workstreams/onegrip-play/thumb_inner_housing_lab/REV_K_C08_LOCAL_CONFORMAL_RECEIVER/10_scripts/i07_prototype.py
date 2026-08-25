"""I07 - practical source-faithful Thumb core prototype (REV_I sections 15, 16, 19, 20, 26).

Build order follows section 8: frozen control positions -> original protrusion
law -> original switch seat -> original packaging scale -> real hardware ->
minimum local adaptation -> shell support.  Never a shell offset.

  1  eight ORIGINAL-style seat islands at the RESTORED plate planes (I02c/I06)
  2  structural webs joining them
  3  joystick deck at the depth that reproduces the ORIGINAL knob height
  4  webs from the deck to the button carrier
  5  the original terminal escape slots, 2 per seat
  6  keep-out relief -- CONFIDENT STATIC only.  Provisional SZH geometry and the
     provisional 25 deg moving envelope are measured, never subtracted
     (section 13; using the envelope as a cutter is what destroyed T7/T8)
  7  shell guard
  8  standoffs to the shell for the load path (section 20/21)

Numbers that come from measurement, not from choice:
  CAP_TO_PLATE 4.759   H02
  PLATE_T      2.003   H02
  slots 1.30 x 6.40 at +-2.60   H01
  joystick seat depth           I06b, from the original +7.607 mm knob top
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Box, Compound, Location, Plane, Vector,
                       export_step, export_stl, import_step)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals  # noqa: E402
from h03_placement import KEEPOUTS, PLATE_T, POCKET_XY, seat_solids  # noqa: E402
from h04_carrier import SLOT_L, SLOT_OFFSET, SLOT_W, plane_box  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402

OUT = L.LAB / "07_prototype"
ISLAND = 9.0                 # 11.0 made neighbouring islands overlap: centres are
                             # only 10.3 mm apart and the tiles are tilted up to
                             # 9.4 deg to each other, so the union left 0.40-0.52 mm
                             # feather edges along every joint.  9.0 still covers the
                             # 6.04 mm bearing face and both slots at +-2.60 +- 0.65.
WEB_W = 4.0
WEB_T = 2.6
DECK_T = 2.5
DECK_MARGIN = 3.0
DECK_APERTURE = 6.0          # solder-tail / wiring hole; the SZH gimbal, pots
                             # and push switch all sit ABOVE the PCB, so the
                             # deck under it needs no module aperture at all
KNOB_ENGAGE = 6.0            # shaft into the custom knob
STANDOFF_W = 4.0
SHELL_CLR = 0.35
SCREW_CLR = 1.00


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

    shell = []
    for k in ("JAD_APPROVED", "JFD_APPROVED"):
        shell.append(solid(import_step(L.SRC[k]), k))
    Tsh = np.concatenate([L.triangles(s, tol=0.06, ang=0.12) for s in shell])
    Psh = np.concatenate([L.surf_points(s, 900000, tol=0.06) for s in shell])
    Psh = Psh[np.linalg.norm(Psh - L.DATUM_P, axis=1) < 55.0]
    L.memory("shell")

    seats = {}
    for s in names:
        r = core["seats"][s]
        w = np.asarray(r["axisWorld"], float)
        cu = np.asarray(r["capUndersideWorld"], float)
        u = seat_solids(cu, w, s)
        seats[s] = {"w": w, "top": np.asarray(r["plateTopWorld"], float),
                    "ex": u["ex"], "ey": u["ey"]}

    # ---- 1 seat islands -------------------------------------------------
    isl = [plane_box(seats[s]["top"], seats[s]["ex"], seats[s]["w"],
                     ISLAND, ISLAND, -PLATE_T, 0.0, "ISL_" + s) for s in names]
    car = isl[0]
    for x in isl[1:]:
        car = (car + x).clean()
    car = solid(car, "CARRIER")
    print("1 islands            vol %9.3f  solids %d" % (L.vol(car), len(list(car.solids()))))
    L.memory("islands")
    if stage < 2:
        return 0

    # ---- 2 webs ---------------------------------------------------------
    nweb = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = seats[names[i]], seats[names[j]]
            d = float(np.linalg.norm(a["top"] - b["top"]))
            if d > 26.0 or L.inter_vol(isl[i], isl[j]) > 1.0:
                continue
            mid = 0.5 * (a["top"] + b["top"])
            ax = L.unit(b["top"] - a["top"])
            w = L.unit(a["w"] + b["w"])
            ex = L.unit(ax - w * float(ax @ w))
            pw = Plane(origin=L.xyz(mid - w * WEB_T), x_dir=L.xyz(ex), z_dir=L.xyz(w))
            box = pw * Box(d, WEB_W, WEB_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
            car = (car + box).clean()
            nweb += 1
    car = solid(car, "CARRIER")
    print("2 webs %2d            vol %9.3f  solids %d"
          % (nweb, L.vol(car), len(list(car.solids()))))
    L.memory("webs")
    if stage < 3:
        return 0

    # ---- 3 joystick deck ------------------------------------------------
    jw = np.asarray(joy["joyAxisWorld"], float)
    jc = np.asarray(joy["knobCentreWorld"], float)
    jex, jey = frame(jw)
    skin = joy["currentSkinOnAxisMm"]
    knob_top = orig["externalStack"]["knobTopAboveSkinMm"]
    knob_base = orig["externalStack"]["knobBaseAboveSkinMm"]
    shaft_hi = joy["szhParts"]["SZH_shaft"]["highAboveSkinMm"]
    pcb_lo = joy["szhParts"]["SZH_pcb"]["lowAboveSkinMm"]
    # raise the SZH until its shaft reaches KNOB_ENGAGE into a knob whose top
    # sits at the ORIGINAL height
    raise_mm = (knob_base + KNOB_ENGAGE) - shaft_hi
    deck_top = pcb_lo + raise_mm
    print("3 joystick placement")
    print("    original knob top          %+8.3f  base %+8.3f" % (knob_top, knob_base))
    print("    provisional shaft top      %+8.3f -> raise SZH by %+.3f mm"
          % (shaft_hi, raise_mm))
    print("    SZH PCB bottom / deck top  %+8.3f mm above skin (%.3f below)"
          % (deck_top, -deck_top))
    print("    ORIGINAL module bottom     %+8.3f mm above skin"
          % orig["externalStack"]["moduleBottomAboveSkinMm"])

    keep = import_step(str(KEEPOUTS))
    ko = {}
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if ch.solids() and not lab.startswith("CAP_"):
            ko[lab] = solid(ch, lab)

    # provisional PCB footprint, measured for the record only
    Ppcb = L.surf_points(ko["SZH_pcb"], 60000, tol=0.05) + jw * raise_mm
    dp = Ppcb - jc
    hx = float(np.abs(dp @ jex).max())
    hy = float(np.abs(dp @ jey).max())
    pcb_shell = sum(L.inter_vol(
        ko["SZH_pcb"].moved(Location(Vector(*[float(x) for x in (jw * raise_mm)]))), sh)
        for sh in shell)

    # The deck outline comes from the CAVITY, not from the provisional PCB.
    # Sizing it to the web PCB gave a 41.3 x 36.0 mm plate whose half-diagonal
    # is 27.4 mm, while the cavity at this depth is only 14.03 mm in its
    # narrowest direction -- the shell guard sawed the core into four pieces.
    # The provisional PCB itself already overlaps the shell by 181 mm3 at this
    # depth, so it cannot be a datum (section 11).
    zc = deck_top + skin
    rad, ang = [], []
    for th in np.arange(0.0, 2 * np.pi - 1e-9, np.pi / 36.0):
        d = jex * np.cos(th) + jey * np.sin(th)
        rr = []
        for zz in (zc - DECK_T, zc - 0.5 * DECK_T, zc):
            h = ray_intervals(Tsh, jc + jw * zz, d, 0.0, 60.0)
            if h:
                rr.append(float(h[0][0]))
        if rr:
            rad.append(max(0.0, min(rr) - SHELL_CLR))
            ang.append(float(th))
    rad = np.asarray(rad)
    print("    cavity at the deck plane: min %.2f  median %.2f  max %.2f mm"
          % (rad.min(), np.median(rad), rad.max()))
    print("    provisional PCB half-extent %.2f x %.2f, and it already overlaps the"
          % (hx, hy))
    print("    shell by %.3f mm3 at this depth -> it does NOT drive the deck" % pcb_shell)

    pts = [L.xyz(jc + jw * (zc - DECK_T) + jex * (r * np.cos(t)) + jey * (r * np.sin(t)))
           for r, t in zip(rad, ang)]
    from build123d import Polyline, make_face, extrude
    wire = Polyline(*pts, close=True)
    deck = extrude(make_face(wire), amount=DECK_T, dir=L.xyz(jw))
    ap = Plane(origin=L.xyz(jc + jw * (zc - DECK_T - 1.0)),
               x_dir=L.xyz(jex), z_dir=L.xyz(jw)) * Box(
        2 * DECK_APERTURE, 2 * DECK_APERTURE, DECK_T + 2.0,
        align=(Align.CENTER, Align.CENTER, Align.MIN))
    deck = solid((deck - ap).clean(), "DECK")
    ivd = sum(L.inter_vol(deck, sh) for sh in shell)
    print("    cavity-shaped deck: vol %9.3f  aperture %.1f mm  shell overlap %.4f mm3"
          % (L.vol(deck), 2 * DECK_APERTURE, ivd))
    L.memory("deck")
    if stage < 4:
        export_step(deck, str(OUT / "I07_DECK_ONLY.step"))
        return 0

    # ---- 4 deck-to-carrier webs ----------------------------------------
    nlink = 0
    deck_plane_pt = jc + jw * (zc - 0.5 * DECK_T)
    for s in ("T7", "T8", "T2", "T4", "T6"):
        a = seats[s]["top"]
        rel = a - deck_plane_pt
        rl = rel - jw * float(rel @ jw)
        nrm = float(np.linalg.norm(rl))
        if nrm < 1.0e-6:
            continue
        u = rl / nrm
        th = float(np.arctan2(u @ jey, u @ jex))
        # land on the deck RIM at this bearing, using the cavity radius that
        # actually exists there -- a fixed radius floated off the rim and left
        # the core in three pieces
        rr = float(np.interp(th % (2 * np.pi), np.asarray(ang), rad,
                             period=2 * np.pi))
        r_land = max(DECK_APERTURE + 1.0, min(rr - 1.2, nrm))
        bpt = deck_plane_pt + u * r_land
        d = float(np.linalg.norm(a - bpt))
        if d < 3.0 or d > 45.0:
            continue
        ax = L.unit(bpt - a)
        up = L.unit(seats[s]["w"] + jw)
        up = L.unit(up - ax * float(up @ ax))
        mid = 0.5 * (a + bpt)
        # hang the link BELOW the plane, like the webs.  Centring it on the
        # plane pushed 1.3 mm of link up into every switch body -- 778 mm3 of
        # mechanism ended up embedded in the core.
        pw = Plane(origin=L.xyz(mid - up * WEB_T), x_dir=L.xyz(ax), z_dir=L.xyz(up))
        link = pw * Box(d + 6.0, WEB_W, WEB_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
        keepv = L.vol(car)
        trial = (car + link).clean()
        car = trial
        nlink += 1
    car = (car + deck).clean()
    car = solid(car, "CARRIER")
    print("4 deck links %d       vol %9.3f  solids %d"
          % (nlink, L.vol(car), len(list(car.solids()))))
    L.memory("links")
    if stage < 5:
        return 0

    # ---- 5 terminal slots ----------------------------------------------
    cut = 0
    for s in names:
        for sgn in (-1.0, 1.0):
            o = seats[s]["top"] + seats[s]["ex"] * (sgn * SLOT_OFFSET)
            tool = plane_box(o, seats[s]["ex"], seats[s]["w"], SLOT_W, SLOT_L,
                             -PLATE_T - 1.0, 1.0, "SLOT")
            if L.inter_vol(car, tool) > 1.0e-9:
                car = solid((car - tool).clean(), "CARRIER")
                cut += 1
    print("5 terminal slots cut %d of %d" % (cut, 2 * len(names)))
    L.memory("slots")
    if stage < 6:
        return 0

    # ---- 5b switch pocket relief ---------------------------------------
    # Adjacent seat centres are 10.3-10.9 mm apart but the islands are 11 x 11
    # and each is tilted up to 9.4 deg away from its neighbour, so a neighbour's
    # corner rises about 0.9 mm above the local plate plane -- straight into the
    # switch body, which starts only 0.051 mm up.  734 mm3 of switch ended up
    # inside the core.  Relieve the body volume itself rather than shrinking the
    # islands, so the bearing face and both slots keep their full width.
    pocket = 0.0
    for s in names:
        u = seats[s]
        tool = plane_box(u["top"], u["ex"], u["w"], POCKET_XY, POCKET_XY,
                         0.0, 6.0, "POCKET_" + s)
        if L.inter_vol(car, tool) > 1.0e-9:
            v0 = L.vol(car)
            car = solid((car - tool).clean(), "CARRIER")
            pocket += v0 - L.vol(car)
    print("5b switch pocket relief removed %.3f mm3" % pocket)
    L.memory("pockets")
    if stage < 6:
        return 0

    # ---- 6 CONFIDENT STATIC keep-outs only ------------------------------
    removed = {}
    for lab, ks in ko.items():
        if not lab.startswith("ORIGINAL_SCREW"):
            continue
        tools = [ks] + [ks.moved(Location(Vector(*[float(x) for x in (dd * SCREW_CLR)])))
                        for dd in (L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V,
                                   L.DATUM_N, -L.DATUM_N)]
        v0 = L.vol(car)
        for t in tools:
            if L.inter_vol(car, t) > 1.0e-9:
                car = solid((car - t).clean(), "CARRIER")
        removed[lab] = v0 - L.vol(car)
    print("6 confident-static relief: %s"
          % (", ".join("%s %.3f" % (k.replace("ORIGINAL_", ""), v)
                       for k, v in removed.items()) or "none"))
    L.memory("static ko")
    if stage < 7:
        return 0

    # ---- 7 shell guard --------------------------------------------------
    v0 = L.vol(car)
    for dd in (np.zeros(3), L.DATUM_U, -L.DATUM_U, L.DATUM_V, -L.DATUM_V,
               L.DATUM_N, -L.DATUM_N):
        t = shell if not np.any(dd) else None
        for sh in shell:
            tool = sh if not np.any(dd) else sh.moved(
                Location(Vector(*[float(x) for x in (dd * SHELL_CLR)])))
            if L.inter_vol(car, tool) > 1.0e-9:
                car = solid((car - tool).clean(), "CARRIER")
    print("7 shell guard removed %.3f mm3" % (v0 - L.vol(car)))
    parts = sorted(car.solids(), key=lambda x: -float(x.volume))
    if len(parts) > 1:
        print("   fragments: %s" % ", ".join("%.3f" % float(p.volume) for p in parts[1:]))
    car = parts[0]
    L.memory("guard")
    if stage < 8:
        return 0

    # ---- 8 standoffs to the shell --------------------------------------
    Pc = L.surf_points(car, 400000, tol=0.06)
    from scipy.spatial import cKDTree
    tree = cKDTree(Psh)
    dist, idx = tree.query(Pc)
    print("8 carrier-to-shell gap: min %.3f  p05 %.3f  p50 %.3f  p95 %.3f"
          % (dist.min(), np.percentile(dist, 5), np.percentile(dist, 50),
             np.percentile(dist, 95)))
    order = np.argsort(dist)
    chosen, pads = [], []
    for i in order:
        if dist[i] > 12.0:
            break
        p = Pc[i]
        if any(np.linalg.norm(p - q) < 11.0 for q in chosen):
            continue
        q = Psh[idx[i]]
        ax = q - p
        n = float(np.linalg.norm(ax))
        if n < 0.8:
            continue
        ax = ax / n
        a2 = np.array([1.0, 0.0, 0.0]) if abs(ax[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        e1 = L.unit(np.cross(a2, ax))
        pw = Plane(origin=L.xyz(p), x_dir=L.xyz(e1), z_dir=L.xyz(ax))
        pad = pw * Box(STANDOFF_W, STANDOFF_W, n - SHELL_CLR,
                       align=(Align.CENTER, Align.CENTER, Align.MIN))
        pads.append((pad, p, q, n))
        chosen.append(p)
        if len(chosen) >= 8:
            break
    added = 0
    for pad, p, q, n in pads:
        trial = solid((car + pad).clean(), "CARRIER")
        if len(list(trial.solids())) == 1 and all(L.inter_vol(trial, sh) < 1.0e-6
                                                  for sh in shell):
            car = trial
            added += 1
    print("   standoffs added %d of %d candidates (heights %s)"
          % (added, len(pads), ", ".join("%.2f" % p[3] for p in pads[:8])))
    car = solid(car, "CARRIER")
    car.label = "C06_SOURCE_FAITHFUL_THUMB_CORE"
    print("")
    print("C06: vol %.3f  faces %d  solids %d  valid %s"
          % (L.vol(car), len(list(car.faces())), len(list(car.solids())), bool(car.is_valid)))
    export_step(car, str(OUT / "C06_SOURCE_FAITHFUL_THUMB_CORE.step"))
    export_stl(car, str(OUT / "C06_SOURCE_FAITHFUL_THUMB_CORE.stl"),
               tolerance=0.03, angular_tolerance=0.10)

    L.write_json(OUT / "i07_prototype.json",
                 {"islandMm": ISLAND, "webWidthMm": WEB_W, "webThicknessMm": WEB_T,
                  "plateThicknessMm": PLATE_T, "deckThicknessMm": DECK_T,
                  "deckApertureMm": 2 * DECK_APERTURE, "knobEngagementMm": KNOB_ENGAGE,
                  "deckCavityRadiusMm": {"min": float(rad.min()),
                                         "median": float(np.median(rad)),
                                         "max": float(rad.max())},
                  "szhRaiseMm": raise_mm, "deckTopAboveSkinMm": deck_top,
                  "provisionalPcbFootprintMm": [2 * hx, 2 * hy],
                  "provisionalPcbShellOverlapMm3": pcb_shell,
                  "webs": nweb, "deckLinks": nlink, "slotsCut": cut, "switchPocketReliefMm3": pocket,
                  "confidentStaticRemovedMm3": removed,
                  "standoffs": added,
                  "volumeMm3": L.vol(car), "faces": len(list(car.faces())),
                  "solids": len(list(car.solids())), "valid": bool(car.is_valid),
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
