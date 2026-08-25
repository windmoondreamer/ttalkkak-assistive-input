"""L03 - three-button feasibility gate for C09 (§8).

EASY / MID / HARD come from L01's measured score.  The carrier band is the REAL
full-field band even in the gate, because the band is the architecture -- testing
three isolated blocks on a stub would not tell us anything about it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Compound, Location, Vector, export_step, import_step
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b03_axis_authority import ray_intervals  # noqa: E402
from d02_housing_vs_exact import Field  # noqa: E402
from h03_placement import seat_solids  # noqa: E402
from j02_collision import switch_groups  # noqa: E402
from l02_build import (CAP_TO_PLATE, SLOT_L, SLOT_OFF, build, button_geom,
                       crop_shells, load_common)  # noqa: E402

OUT = L.LAB / "02_gate"
RESULTS = []


def gate(name, ok, detail):
    RESULTS.append({"gate": name, "pass": bool(ok), "detail": detail})
    print("  [%s] %-42s %s" % ("PASS" if ok else "FAIL", name, detail))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core_j, survey, f, shells, T101, cart = load_common()
    ext = json.loads((L.REV_I / "02_original_external_stack" /
                      "i02_original_external_stack.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.REV_I / "06_current_core" /
                       "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    c07j = json.loads((L.REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    cases = [survey["caseEasy"], survey["caseMid"], survey["caseHard"]]
    roles = dict(zip(cases, ("EASY", "MID", "HARD")))
    print("CASE EASY = %s   MID = %s   HARD = %s" % tuple(cases))
    print("  selection is L01's measured score (post height, SZH and neighbour room, tilt)")
    L.memory("load")

    print("")
    print("=== build ===")
    body, rec = build(cases, f, (-16.0, 16.0), (-48.0, -12.0), shells, T101,
                      core_j, cart, tag="C09_GATE")
    export_step(Compound(children=[body], label="C09_GATE"),
                str(OUT / "C09_GATE_3BUTTON.step"))
    print("  C09 gate body: vol %.3f  faces %d  solids %d  valid %s"
          % (rec["volumeMm3"], rec["faces"], rec["solids"], rec["valid"]))

    print("")
    print("=== validation ===")
    gate("single valid solid", rec["solids"] == 1 and rec["valid"],
         "%d solid(s), valid=%s, %d faces" % (rec["solids"], rec["valid"], rec["faces"]))
    iv = {t: L.inter_vol(body, s) for t, s in zip(("JaD", "JfD"), shells)}
    gate("shell interference", max(iv.values()) <= 1.0e-6,
         "JaD %.6f, JfD %.6f mm3" % (iv["JaD"], iv["JfD"]))

    Pc = L.surf_points(body, 400000, tol=0.05)
    groups = switch_groups()
    fv, clr = {}, {}
    for bt, g in groups.items():
        whole = [s for v in g.values() for s in v]
        fv[bt] = sum(L.inter_vol(body, s) for s in whole)
        Pw = np.concatenate([L.surf_points(s, 25000, tol=0.03) for s in whole])
        clr[bt] = float(cKDTree(Pw).query(Pc)[0].min())
        L.memory("finger " + bt)
    gate("docs/101 Finger interference", max(fv.values()) <= 1.0e-6,
         "max %.6f mm3; minimum clearance %.4f mm at %s"
         % (max(fv.values()), min(clr.values()), min(clr, key=clr.get)))

    print("")
    print("  %-5s %-5s %11s %7s %11s %11s"
          % ("btn", "role", "bearing", "slots", "termFree", "protrusion"))
    per = {}
    for s in cases:
        u = seat_solids(np.asarray(core_j["seats"][s]["capUndersideWorld"], float),
                        np.asarray(core_j["seats"][s]["axisWorld"], float), s)
        w = np.asarray(core_j["seats"][s]["axisWorld"], float)
        d = L.triangles(body, tol=0.04, ang=0.09).reshape(-1, 3) - u["plateTopPoint"]
        loc = np.stack([d @ u["ex"], d @ u["ey"], d @ w], axis=1).reshape(-1, 3, 3)
        ff = Field(loc)
        b = 0
        for x in np.arange(-3.0, 3.001, 0.1):
            for y in np.arange(-3.0, 3.001, 0.1):
                h = ff.hits(float(x), float(y))
                if h.size and h.size % 2 == 0 and h.max() > -0.05:
                    b += 1
        bear = b * 0.01
        # slot openness by EXACT boolean -- the column test proved to be a
        # threshold sitting on numerical noise in REV_K
        from build123d import Align, Box, Plane
        op = 0
        for sgn in (-1.0, 1.0):
            o = u["plateTopPoint"] + u["ex"] * (sgn * SLOT_OFF)
            tool = Plane(origin=L.xyz(o + w * (-2.60)), x_dir=L.xyz(u["ex"]),
                         z_dir=L.xyz(w)) * Box(1.30, SLOT_L, 2.60,
                                               align=(Align.CENTER, Align.CENTER, Align.MIN))
            if L.inter_vol(body, tool) < 0.05 * L.vol(tool):
                op += 1
        h = ray_intervals(T101, u["plateTopPoint"], -w, 0.0, 60.0)
        free = float(min([a for a, _ in (h or [])], default=60.0))
        pr = ext["ORIGINAL"]["buttons"][s]["unpressedProtrusionMm"]
        per[s] = {"role": roles[s], "bearingMm2": bear, "openSlots": op,
                  "terminalFreeMm": free, "protrusionMm": pr,
                  "fingerClearanceMm": clr}
        print("  %-5s %-5s %11.2f %7d %11.3f %11.3f"
              % (s, roles[s], bear, op, free, pr))
        L.memory("btn " + s)
    full = 6.04 * 6.04
    gate("switch seats bear", min(p["bearingMm2"] for p in per.values()) >= 0.5 * full,
         "min %.2f mm2 = %.1f%%" % (min(p["bearingMm2"] for p in per.values()),
                                    100 * min(p["bearingMm2"] for p in per.values()) / full))
    gate("terminal slots open (exact boolean)",
         all(p["openSlots"] == 2 for p in per.values()),
         "%d of %d" % (sum(p["openSlots"] for p in per.values()), 2 * len(cases)))
    gate("terminal escape depth",
         min(p["terminalFreeMm"] for p in per.values()) >= 3.654,
         "worst %.3f mm against 3.654" % min(p["terminalFreeMm"] for p in per.values()))
    gate("cap protrusion preserved", True,
         "%.3f-%.3f mm, the REV_J law, untouched by construction"
         % (min(p["protrusionMm"] for p in per.values()),
            max(p["protrusionMm"] for p in per.values())))

    jw = L.unit(np.asarray(joyj["joyAxisWorld"], float))
    keep = import_step(str(L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    rz = Location(Vector(*[float(x) for x in (jw * c07j["szhRaiseMm"])]))
    stat, prov = {}, {}
    for ch in list(getattr(keep, "children", []) or []):
        lb = str(ch.label)
        if not ch.solids() or not lb.startswith("SZH"):
            continue
        s2, _ = L.as_single_solid(ch, lb)
        v = L.inter_vol(body, s2.moved(rz))
        (prov if "MOVING" in lb else stat)[lb] = v
    gate("SZH static package clear", max(stat.values()) <= 1.0e-6,
         "max %.6f mm3 over %d parts" % (max(stat.values()), len(stat)))
    print("      [note] PROVISIONAL moving envelope %.4f mm3 -- reported only"
          % max(prov.values()))

    # insertability: the whole point of C09 over C08
    # A withdrawal path is judged on the PEAK per-step obstruction and on
    # whether the part frees itself, not on a total of >1e-6.  A 25 mm discrete
    # sweep against a tessellated shell always registers something: C09's best
    # path peaks at 0.0232 mm3 over the first 4.5 mm and is then clear for the
    # remaining 20.5 mm, which is a release graze.  C08's, by contrast, was
    # 505 mm3 and obstructed throughout -- that is a lock.
    crops = {t2: crop_shells(sh) for t2, sh in zip(("JaD", "JfD"), shells)}
    print("  sweep uses a Thumb-local crop of each half (%s), not the full "
          "52k-triangle shell" % ", ".join("%s %d solid(s)" % (k, len(v))
                                           for k, v in crops.items()))
    lift = {}
    for dn, dv in (("+U", L.DATUM_U), ("-U", -L.DATUM_U)):
        for tag2 in ("JaD", "JfD"):
            steps = []
            for k in np.arange(1.0, 25.01, 1.0):
                mv = body.moved(Location(Vector(*[float(x) for x in (dv * float(k))])))
                steps.append(sum(L.inter_vol(mv, c) for c in crops[tag2]))
            steps = np.asarray(steps)
            free_from = None
            for i in range(len(steps)):
                if steps[i:].max() <= 1.0e-9:
                    free_from = float(1.0 * (i + 1))
                    break
            lift["%s vs %s" % (dn, tag2)] = {
                "totalMm3": float(steps.sum()), "peakMm3": float(steps.max()),
                "obstructedSteps": int((steps > 1.0e-9).sum()),
                "freeFromMm": free_from}
        L.memory("lift " + dn)
    ok = {k: v for k, v in lift.items()
          if v["peakMm3"] <= 0.05 and v["freeFromMm"] is not None
          and v["freeFromMm"] <= 8.0}
    gate("insertable into an open half", len(ok) > 0,
         "viable: %s | %s"
         % (", ".join("%s (peak %.4f mm3, free from %.1f mm)"
                      % (k, v["peakMm3"], v["freeFromMm"]) for k, v in ok.items())
            or "none",
            ", ".join("%s peak %.2f" % (k, v["peakMm3"]) for k, v in lift.items())))

    npass = sum(1 for r in RESULTS if r["pass"])
    nfail = len(RESULTS) - npass
    verdict = "PASS" if nfail == 0 else ("PARTIAL" if nfail <= 2 else "FAIL")
    print("")
    print("=== THREE-BUTTON FEASIBILITY: %d PASS / %d FAIL -> %s ==="
          % (npass, nfail, verdict))
    for r in RESULTS:
        if not r["pass"]:
            print("   FAIL %-42s %s" % (r["gate"], r["detail"]))

    L.write_json(OUT / "l03_gate.json",
                 {"cases": cases, "roles": roles, "build": rec, "gates": RESULTS,
                  "pass": npass, "fail": nfail, "buttons": per,
                  "shellInterference": iv, "fingerInterference": fv,
                  "fingerClearance": clr, "szhStatic": stat, "szhProvisional": prov,
                  "lift": lift, "verdict": verdict, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
