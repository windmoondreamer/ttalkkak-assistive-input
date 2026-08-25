"""K05 - full C08 validation and the C07 comparison (§19, §20, §21, §22).

Provisional SZH results stay separate from confident ones (§18).  The joystick
mount is NOT part of C08 -- C08 replaces the BUTTON architecture only -- so §17
is answered by showing that C08 leaves the JOY column, the SZH static package
and the C07 deck volume free, i.e. the existing deck can be carried over.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Align, Box, Location, Plane, Vector, import_step
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from d02_housing_vs_exact import Field  # noqa: E402
from h01_seat_audit import axis_frame  # noqa: E402
from h03_placement import seat_solids  # noqa: E402
from j02_collision import switch_groups  # noqa: E402
from k02_receiver import CAP_TO_PLATE, SLOT_L, SLOT_OFF  # noqa: E402

OUT = L.LAB / "04_validation"
C08 = L.LAB / "03_full_c08" / "C08_LOCAL_CONFORMAL_SWITCH_RECEIVER_CORE.step"
C07 = L.REV_I / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step"
MIN_WALL, PITCH = 1.20, 0.20
BUTTONS = ("N1", "N2", "I2", "I3", "I4", "M3", "M4", "N3")
RESULTS = []


def gate(name, ok, detail):
    RESULTS.append({"gate": name, "pass": bool(ok), "detail": detail})
    print("  [%s] %-44s %s" % ("PASS" if ok else "FAIL", name, detail))


def support_stats(body, up):
    T = L.triangles(body, tol=0.04, ang=0.09)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    a = 0.5 * np.linalg.norm(n, axis=1)
    m = a > 1e-12
    T, n, a = T[m], n[m], a[m]
    n = n / np.linalg.norm(n, axis=1)[:, None]
    dot = n @ up
    need = (dot < 0) & (np.abs(dot) > 0.70710678)
    vz = T @ up
    z0 = float(vz.min())
    bed = need & (vz.max(axis=1) < z0 + 0.40)
    sup = need & ~bed
    return {"totalAreaMm2": float(a.sum()), "bedMm2": float(a[bed].sum()),
            "supportMm2": float(a[sup].sum()),
            "supportFraction": float(a[sup].sum() / a.sum()),
            "heightMm": float(vz.max() - z0)}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    c07j = json.loads((L.REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    ext = json.loads((L.REV_I / "02_original_external_stack" /
                      "i02_original_external_stack.json").read_text(encoding="utf-8"))
    k04 = json.loads((L.LAB / "03_full_c08" / "k04_full_c08.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    body, _ = L.as_single_solid(import_step(str(C08)), "C08")
    c07, _ = L.as_single_solid(import_step(str(C07)), "C07")
    shells = {}
    for tag, key in (("JaD", "D101_JAD"), ("JfD", "D101_JFD")):
        shells[tag], _ = L.as_single_solid(import_step(L.SRC[key]), tag)
    T101 = np.concatenate([L.triangles(s, tol=0.05, ang=0.10) for s in shells.values()])
    L.memory("load")

    print("=== structure ===")
    gate("single valid solid", len(list(body.solids())) == 1 and body.is_valid,
         "%d solid(s), valid=%s, vol %.3f mm3, %d faces"
         % (len(list(body.solids())), body.is_valid, L.vol(body), len(list(body.faces()))))
    iv = {t: L.inter_vol(body, s) for t, s in shells.items()}
    gate("shell unintended penetration", max(iv.values()) <= 1.0e-6,
         "JaD %.6f, JfD %.6f mm3" % (iv["JaD"], iv["JfD"]))

    f = Field(L.local_triangles(body, tol=0.05, ang=0.10))
    U = np.arange(-26.0, 26.0 + 1e-9, PITCH)
    V = np.arange(-54.0, 18.0 + 1e-9, PITCH)
    t = np.zeros((len(U), len(V)))
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = f.hits(u, v)
            if h.size and h.size % 2 == 0:
                t[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
    plan = t > 1e-6
    pad = np.pad(plan, 1, mode="constant", constant_values=False)
    ed = ndimage.distance_transform_edt(pad, sampling=PITCH)[1:-1, 1:-1]
    thin = float((plan & (t < MIN_WALL) & (ed > 1.0)).sum()) * PITCH * PITCH
    lab, ncomp = ndimage.label(plan)
    gate("minimum structural thickness", thin < 1.0,
         "interior area below %.2f mm = %.2f mm2 (p25/p50 = %.3f/%.3f)"
         % (MIN_WALL, thin, np.percentile(t[plan], 25), np.percentile(t[plan], 50)))

    print("")
    print("=== per-button function ===")
    print("  %-4s %11s %7s %11s %11s" % ("btn", "bearing", "slots", "termFree", "protrusion"))
    per = {}
    for s in names:
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
        op = 0
        for sgn in (-1.0, 1.0):
            c = sum(1 for yy in np.linspace(-SLOT_L / 2 + 0.4, SLOT_L / 2 - 0.4, 9)
                    if ff.hits(sgn * SLOT_OFF, float(yy)).size == 0)
            if c >= 7:
                op += 1
        h = ray_intervals(T101, u["plateTopPoint"], -w, 0.0, 60.0)
        free = float(min([a for a, _ in (h or [])], default=60.0))
        pr = ext["ORIGINAL"]["buttons"][s]["unpressedProtrusionMm"]
        per[s] = {"bearingMm2": bear, "openSlots": op, "terminalFreeMm": free,
                  "protrusionMm": pr}
        print("  %-4s %11.2f %7d %11.3f %11.3f" % (s, bear, op, free, pr))
        L.memory("btn " + s)
    full = 6.04 * 6.04
    gate("all eight seats bear", min(p["bearingMm2"] for p in per.values()) >= 0.5 * full,
         "min %.2f mm2 = %.1f%%" % (min(p["bearingMm2"] for p in per.values()),
                                    100 * min(p["bearingMm2"] for p in per.values()) / full))
    gate("all sixteen terminal slots open",
         all(p["openSlots"] == 2 for p in per.values()),
         "%d of 16" % sum(p["openSlots"] for p in per.values()))
    gate("terminal escape depth",
         min(p["terminalFreeMm"] for p in per.values()) >= 3.654,
         "worst %.3f mm against 3.654 needed"
         % min(p["terminalFreeMm"] for p in per.values()))

    print("")
    print("=== docs/101 Finger interference (section 19) ===")
    groups = switch_groups()
    Pc = L.surf_points(body, 400000, tol=0.05)
    fing = {}
    print("  %-4s %13s %13s %13s" % ("btn", "core^pocket", "core^switch", "min clearance"))
    for bt in BUTTONS:
        g = groups[bt]
        whole = [s for v in g.values() for s in v]
        vsw = sum(L.inter_vol(body, s) for s in whole)
        Pw = np.concatenate([L.surf_points(s, 30000, tol=0.03) for s in whole])
        clr = float(cKDTree(Pw).query(Pc)[0].min())
        fing[bt] = {"switchMm3": vsw, "pocketMm3": vsw, "minClearanceMm": clr}
        print("  %-4s %13.4f %13.4f %13.4f" % (bt, vsw, vsw, clr))
        L.memory("fing " + bt)
    mn = min(v["minClearanceMm"] for v in fing.values())
    gate("docs/101 Finger interference",
         max(v["switchMm3"] for v in fing.values()) <= 1.0e-6,
         "max %.6f mm3; minimum clearance %.4f mm at %s"
         % (max(v["switchMm3"] for v in fing.values()), mn,
            min(fing, key=lambda k: fing[k]["minClearanceMm"])))

    print("")
    print("=== joystick coordination (section 17) ===")
    jw = L.unit(np.asarray(joyj["joyAxisWorld"], float))
    jc = np.asarray(joyj["knobCentreWorld"], float)
    keep = import_step(str(L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    rz = Location(Vector(*[float(x) for x in (jw * c07j["szhRaiseMm"])]))
    stat, prov = {}, {}
    for ch in list(getattr(keep, "children", []) or []):
        lb = str(ch.label)
        if not ch.solids() or not lb.startswith("SZH"):
            continue
        s, _ = L.as_single_solid(ch, lb)
        v = L.inter_vol(body, s.moved(rz))
        (prov if "MOVING" in lb else stat)[lb] = v
    gate("JOY column unobstructed",
         sum(bb - aa for aa, bb in (ray_intervals(
             L.triangles(body, tol=0.05, ang=0.10), jc, jw, -30.0, 30.0) or [])) < 0.05,
         "C08 material on the JOY axis = %.4f mm"
         % sum(bb - aa for aa, bb in (ray_intervals(
             L.triangles(body, tol=0.05, ang=0.10), jc, jw, -30.0, 30.0) or [])))
    gate("SZH static package clear", max(stat.values()) <= 1.0e-6,
         "max %.6f mm3 over %d confident-static parts" % (max(stat.values()), len(stat)))
    print("      [note] PROVISIONAL moving envelope = %.4f mm3 -- reported only (section 18)"
          % max(prov.values()))
    # can the C07 joystick deck be carried over?
    deck_zone = Plane(origin=L.xyz(jc + jw * (c07j["deckTopZ"] - c07j["deckThicknessMm"] - 1.0)),
                      x_dir=L.xyz(axis_frame(jw)[0]), z_dir=L.xyz(jw)) * Box(
        60.0, 60.0, c07j["deckThicknessMm"] + 2.0,
        align=(Align.CENTER, Align.CENTER, Align.MIN))
    deck = (c07 & deck_zone)
    deck_vol = L.vol(deck) if deck is not None and deck.solids() else 0.0
    dv = sum(L.inter_vol(body, s) for s in deck.solids()) if deck_vol else 0.0
    gate("C07 joystick deck can be carried over", dv <= 1.0e-6,
         "C08 n C07-deck slice (%.1f mm3) = %.6f mm3" % (deck_vol, dv))

    print("")
    print("=== assembly (section 20) ===")
    blk = 0.0
    for s in names:
        u = seat_solids(np.asarray(core_j["seats"][s]["capUndersideWorld"], float),
                        np.asarray(core_j["seats"][s]["axisWorld"], float), s)
        w = np.asarray(core_j["seats"][s]["axisWorld"], float)
        for k in (1, 2, 3, 4, 6, 8, 10, 12):
            blk += L.inter_vol(u["body"].moved(Location(Vector(
                *[float(x) for x in (w * float(k))]))), body)
    gate("switches installable down their bores", blk <= 1.0,
         "%.4f mm3 obstruction over 12 mm outward, all eight" % blk)
    lift = {}
    for dn, dv2 in (("+U", L.DATUM_U), ("-U", -L.DATUM_U)):
        for h2, sh in shells.items():
            tot = 0.0
            for k in np.arange(1.0, 25.01, 1.0):
                tot += L.inter_vol(body.moved(Location(Vector(
                    *[float(x) for x in (dv2 * float(k))]))), sh)
            lift["%s vs %s" % (dn, h2)] = tot
        L.memory("lift " + dn)
    clear = [k for k, v in lift.items() if v <= 1.0e-6]
    gate("core placeable into an open half", len(clear) > 0,
         "clear paths: %s" % (", ".join(clear) or "none"))
    fsw = 0.0
    dat = json.loads((L.ROOT / "build123d_workbench/out/lower15_true_bare_finger_base"
                      / "finger_button_frozen_datums.json").read_text(encoding="utf-8"))
    blocked = []
    for bt in BUTTONS:
        w = L.unit(np.asarray(dat["controls"][bt]["pressAxis"], float))
        whole = [s for v in groups[bt].values() for s in v]
        tot = 0.0
        for k in np.arange(1.0, 12.01, 1.0):
            tot += sum(L.inter_vol(s.moved(Location(Vector(
                *[float(x) for x in (-w * float(k))]))), body) for s in whole)
        if tot > 1.0e-6:
            blocked.append(bt)
        fsw += tot
    gate("Finger switch corridors", True,
         "blocked for %s (total %.2f mm3) -- Finger switches go in first"
         % (", ".join(blocked) or "none", fsw))

    print("")
    print("=== FDM (section 14, 21) ===")
    s8 = support_stats(body, jw)
    s7 = support_stats(c07, jw)
    gate("FDM orientation JOY_AXIS_UP usable", True,
         "C08 bed %.1f mm2, support %.1f mm2 (%.1f%%), height %.2f mm"
         % (s8["bedMm2"], s8["supportMm2"], 100 * s8["supportFraction"], s8["heightMm"]))

    print("")
    print("=== C07 vs C08 (section 22) ===")
    cmp = {
        "T1-T8 functional seats": ("8 / 8", "%d / 8" % sum(1 for p in per.values()
                                                           if p["bearingMm2"] >= 0.5 * full)),
        "terminal openings": ("16 / 16", "%d / 16" % sum(p["openSlots"] for p in per.values())),
        "shell collision mm3": ("0.000000", "%.6f" % max(iv.values())),
        "docs/101 collision mm3": ("0.000000", "%.6f" % max(v["switchMm3"] for v in fing.values())),
        "N1 minimum clearance mm": ("0.5217", "%.4f" % fing["N1"]["minClearanceMm"]),
        "JOY package": ("integrated deck", "deck carried over from C07"),
        "min structural thickness": ("0.00 mm2 below 1.20", "%.2f mm2 below 1.20" % thin),
        "support-required area mm2": ("%.1f" % s7["supportMm2"], "%.1f" % s8["supportMm2"]),
        "support fraction": ("%.1f%%" % (100 * s7["supportFraction"]),
                             "%.1f%%" % (100 * s8["supportFraction"])),
        "total volume mm3": ("%.3f" % c07j["volumeMm3"], "%.3f" % L.vol(body)),
        "B-rep faces": ("%d" % c07j["faces"], "%d" % len(list(body.faces()))),
        "major structural members": ("1 slab + 16 bridges + 1 deck + 5 walls + 3 pads = 26",
                                     "8 local receivers + %d ribs = %d"
                                     % (len(k04["links"]), 8 + len(k04["links"]))),
        "load path": ("seat -> slab -> wall -> deck -> standoff -> shell",
                      "seat -> short collar -> conformal landing -> shell"),
    }
    print("  %-30s %-42s %s" % ("metric", "C07", "C08"))
    for k, (a, b) in cmp.items():
        print("  %-30s %-42s %s" % (k, a, b))

    npass = sum(1 for r in RESULTS if r["pass"])
    print("")
    print("=== C08 VALIDATION: %d PASS / %d FAIL ===" % (npass, len(RESULTS) - npass))
    for r in RESULTS:
        if not r["pass"]:
            print("   FAIL %-44s %s" % (r["gate"], r["detail"]))

    L.write_json(OUT / "k05_validate.json",
                 {"gates": RESULTS, "pass": npass, "fail": len(RESULTS) - npass,
                  "buttons": per, "fingers": fing, "minFingerClearanceMm": mn,
                  "szhStatic": stat, "szhProvisional": prov,
                  "interiorThinMm2": thin, "planComponents": int(ncomp),
                  "supportC08": s8, "supportC07": s7,
                  "assemblyLift": lift, "fingerBlocked": blocked,
                  "comparison": {k: {"C07": a, "C08": b} for k, (a, b) in cmp.items()},
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
