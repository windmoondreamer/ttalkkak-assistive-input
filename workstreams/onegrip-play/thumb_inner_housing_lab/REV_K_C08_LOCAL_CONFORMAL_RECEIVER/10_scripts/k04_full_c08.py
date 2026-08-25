"""K04 - full C08: eight local receivers, then the MINIMUM interconnection (§15, §16).

Section 16 asks for the minimum necessary interconnection rather than an assumed
plate, so the eight receivers are built independently first and the connectivity
is then MEASURED: adjacent Thumb centres are 10.30-10.90 mm apart while each
landing is 13.2 mm across, so some neighbours fuse on their own.  Only the gaps
that remain are bridged, and only where a bridge is needed to make the part
handleable as one piece.
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
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import true_axis  # noqa: E402
from h01_seat_audit import axis_frame  # noqa: E402
from k02_receiver import build_receiver, receiver_voids  # noqa: E402

OUT = L.LAB / "03_full_c08"
LINK_W, LINK_T = 4.0, 2.4


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    shells = []
    for key in ("D101_JAD", "D101_JFD"):
        s, _ = L.as_single_solid(import_step(L.SRC[key]), key)
        shells.append(s)
    SHELL_T = np.concatenate([L.triangles(s, tol=0.05, ang=0.10) for s in shells])
    L.memory("shell")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    units, recs, geom = {}, {}, {}
    print("=== eight independent local receivers ===")
    for name in names:
        lab = next(k for k, v in NAME_MAP.items() if v == name)
        cap, _ = L.as_single_solid(cart[lab], name)
        w, _, _ = true_axis(cap)
        cen = L.surf_points(cap, 40000, tol=0.05).mean(axis=0)
        ex, ey = axis_frame(w)
        seat_top = float((np.asarray(core_j["seats"][name]["plateTopWorld"], float) - cen) @ w)
        # Per-receiver voids are correct again now that FLARE = 0 keeps the
        # receivers from overlapping: nothing can fill a neighbour's pocket.
        body, rec = build_receiver(name, cen, w, ex, ey, seat_top, shells, SHELL_T)
        units[name] = body
        recs[name] = rec
        geom[name] = {"cen": cen, "w": w, "ex": ex, "ey": ey, "seat_top": seat_top}
        print("  %-3s vol %8.3f  faces %3d  solids %d  valid %s  slots %d"
              % (name, rec["volumeMm3"], rec["faces"], rec["solids"], rec["valid"],
                 rec["slotsCut"]))
        del cap
        L.memory("build " + name)

    # ---- measured connectivity, before adding anything -------------------
    print("")
    print("=== natural connectivity between receivers (nothing added yet) ===")
    pair = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            v = L.inter_vol(units[a], units[b])
            if v > 1.0e-6:
                pair["%s-%s" % (a, b)] = v
                print("  %-8s fuse volume %8.3f mm3" % ("%s-%s" % (a, b), v))
    if not pair:
        print("  none -- every receiver is independent")

    fused = units[names[0]]
    for n in names[1:]:
        fused = (fused + units[n]).clean()
    fused, _ = L.as_single_solid(fused, "C08")
    comps = sorted(fused.solids(), key=lambda x: -float(x.volume))
    print("  fused result: %d connected component(s): %s"
          % (len(comps), ", ".join("%.1f" % float(c.volume) for c in comps)))

    # Membership by VOLUME OVERLAP, not by nearest centroid.  The centroid
    # heuristic put T6 and T8 in one group when they were in fact two separate
    # components, so the bridging loop finished with T8 still detached and the
    # "keep the largest component" step silently threw 711.8 mm3 away.
    def members(comps_):
        m = {}
        for n in names:
            v = L.vol(units[n])
            best, bo = None, 0.0
            for k, c in enumerate(comps_):
                o = L.inter_vol(units[n], c)
                if o > bo:
                    best, bo = k, o
            m.setdefault(best if bo > 0.5 * v else -1, []).append(n)
        return m

    member = members(comps)
    for k, v in sorted(member.items()):
        print("     component %d: %s" % (k, ", ".join(v)))

    print("")
    print("=== minimum interconnection ===")
    links = []
    guard = 0
    while len(comps) > 1 and guard < 8:
        guard += 1
        member = members(comps)
        home = member.get(0, [])
        others = [(k, v) for k, v in member.items() if k not in (0, -1)]
        if not home or not others:
            break
        best = None
        for k, g in others:
            for x in home:
                for y in g:
                    d = float(np.linalg.norm(geom[x]["cen"] - geom[y]["cen"]))
                    if best is None or d < best[0]:
                        best = (d, x, y)
        d, x, y = best
        gx, gy = geom[x], geom[y]
        pa = gx["cen"] + gx["w"] * (gx["seat_top"] - 1.2)
        pb = gy["cen"] + gy["w"] * (gy["seat_top"] - 1.2)
        ax = L.unit(pb - pa)
        up = L.unit(gx["w"] + gy["w"])
        up = L.unit(up - ax * float(up @ ax))
        mid = 0.5 * (pa + pb)
        box = Plane(origin=L.xyz(mid - up * LINK_T), x_dir=L.xyz(ax),
                    z_dir=L.xyz(up)) * Box(
            float(np.linalg.norm(pb - pa)) + 4.0, LINK_W, LINK_T,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        box.label = "LINK_%s_%s" % (x, y)
        fused = (fused + box).clean()
        fused, _ = L.as_single_solid(fused, "C08")
        comps = sorted(fused.solids(), key=lambda z: -float(z.volume))
        links.append({"from": x, "to": y, "lengthMm": d,
                      "componentsAfter": len(comps)})
        print("  bridged %s - %s  (%.2f mm, %.1f x %.1f rib) -> %d component(s)"
              % (x, y, d, LINK_W, LINK_T, len(comps)))
        L.memory("link %s-%s" % (x, y))
    if not links:
        print("  none required")

    # ribs are added below the seat planes, so they cannot re-enter a pocket;
    # this is verified in K05 rather than assumed
    # guard against the shell after any link
    for s in shells:
        if L.inter_vol(fused, s) > 1.0e-9:
            fused = (fused - s).clean()
            fused, _ = L.as_single_solid(fused, "C08")
    comps2 = sorted(fused.solids(), key=lambda x: -float(x.volume))
    debris = [float(c.volume) for c in comps2[1:]]
    body = comps2[0]
    body.label = "C08_LOCAL_CONFORMAL_SWITCH_RECEIVER_CORE"
    print("")
    print("C08: vol %.3f  faces %d  solids %d  valid %s"
          % (L.vol(body), len(list(body.faces())), len(list(body.solids())),
             bool(body.is_valid)))
    if debris:
        print("  dropped fragments: %s" % ", ".join("%.3f" % d for d in debris))

    export_step(Compound(children=[body], label=str(body.label)),
                str(OUT / "C08_LOCAL_CONFORMAL_SWITCH_RECEIVER_CORE.step"))
    export_stl(body, str(OUT / "C08_LOCAL_CONFORMAL_SWITCH_RECEIVER_CORE.stl"),
               tolerance=0.03, angular_tolerance=0.10)
    export_step(Compound(children=[units[n] for n in names], label="C08_UNITS"),
                str(OUT / "C08_RECEIVER_UNITS.step"))

    L.write_json(OUT / "k04_full_c08.json",
                 {"receivers": recs, "naturalFusePairs": pair,
                  "componentsBeforeLinks": len(comps),
                  "componentMembership": {str(k): v for k, v in member.items()},
                  "links": links, "linkWidthMm": LINK_W, "linkThicknessMm": LINK_T,
                  "droppedFragmentsMm3": debris,
                  "volumeMm3": L.vol(body), "faces": len(list(body.faces())),
                  "solids": len(list(body.solids())), "valid": bool(body.is_valid),
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
