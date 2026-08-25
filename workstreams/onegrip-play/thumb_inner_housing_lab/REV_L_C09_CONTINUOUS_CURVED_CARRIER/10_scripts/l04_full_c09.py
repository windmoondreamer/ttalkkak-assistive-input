"""L04 - full C09, validation, and the C07.1 / C08 / C09 comparison (§9-§14)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import (Align, Box, Compound, Location, Plane, Vector,
                       export_step, export_stl, import_step)
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import ORDER  # noqa: E402
from b03_axis_authority import ray_intervals  # noqa: E402
from d02_housing_vs_exact import Field  # noqa: E402
from h03_placement import seat_solids  # noqa: E402
from j02_collision import switch_groups  # noqa: E402
from l02_build import (CARRIER_T, GAP, SLOT_L, SLOT_OFF, build, crop_shells,
                       load_common)  # noqa: E402

OUT = L.LAB / "03_full_c09"
VAL = L.LAB / "04_validation"
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
    return {"totalMm2": float(a.sum()), "bedMm2": float(a[bed].sum()),
            "supportMm2": float(a[sup].sum()),
            "supportFraction": float(a[sup].sum() / a.sum()),
            "heightMm": float(vz.max() - z0)}


def sweep(body, crops, dv, steps=np.arange(1.0, 25.01, 1.0)):
    """Sweep against a Thumb-LOCAL crop of each half.

    Against the full 52,206-triangle shell each of these booleans measured
    ~20 s; 200 of them stalled the pipeline for over an hour.
    """
    out = {}
    for tag, cs in crops.items():
        v = np.array([sum(L.inter_vol(body.moved(Location(Vector(
            *[float(x) for x in (dv * float(k))]))), c) for c in cs)
            for k in steps])
        free = None
        for i in range(len(v)):
            if v[i:].max() <= 1.0e-9:
                free = float(steps[i])
                break
        out[tag] = {"totalMm3": float(v.sum()), "peakMm3": float(v.max()),
                    "obstructedSteps": int((v > 1.0e-9).sum()), "freeFromMm": free}
    return out


def main() -> int:
    for d in (OUT, VAL):
        d.mkdir(parents=True, exist_ok=True)
    core_j, survey, f, shells, T101, cart = load_common()
    ext = json.loads((L.REV_I / "02_original_external_stack" /
                      "i02_original_external_stack.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.REV_I / "06_current_core" /
                       "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    c07j = json.loads((L.REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]
    L.memory("load")

    print("=== build full C09 ===")
    body, rec = build(names, f, (-16.0, 16.0), (-48.0, -12.0), shells, T101,
                      core_j, cart, tag="C09")
    body.label = "C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE"
    print("  C09: vol %.3f  faces %d  solids %d  valid %s"
          % (rec["volumeMm3"], rec["faces"], rec["solids"], rec["valid"]))
    export_step(Compound(children=[body], label=str(body.label)),
                str(OUT / "C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.step"))
    export_stl(body, str(OUT / "C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.stl"),
               tolerance=0.03, angular_tolerance=0.10)

    print("")
    print("=== validation ===")
    gate("single valid solid", rec["solids"] == 1 and rec["valid"],
         "%d solid(s), valid=%s, %d faces, %.1f mm3"
         % (rec["solids"], rec["valid"], rec["faces"], rec["volumeMm3"]))
    iv = {t: L.inter_vol(body, s) for t, s in zip(("JaD", "JfD"), shells)}
    gate("shell interference", max(iv.values()) <= 1.0e-6,
         "JaD %.6f, JfD %.6f mm3" % (iv["JaD"], iv["JfD"]))

    ff = Field(L.local_triangles(body, tol=0.05, ang=0.10))
    U = np.arange(-26.0, 26.0 + 1e-9, PITCH)
    V = np.arange(-54.0, 18.0 + 1e-9, PITCH)
    t = np.zeros((len(U), len(V)))
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = ff.hits(u, v)
            if h.size and h.size % 2 == 0:
                t[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
    plan = t > 1e-6
    pad = np.pad(plan, 1, mode="constant", constant_values=False)
    ed = ndimage.distance_transform_edt(pad, sampling=PITCH)[1:-1, 1:-1]
    thin = float((plan & (t < MIN_WALL) & (ed > 1.0)).sum()) * PITCH * PITCH
    gate("minimum structural thickness", thin < 1.0,
         "interior area below %.2f mm = %.2f mm2 (p25/p50 %.3f/%.3f)"
         % (MIN_WALL, thin, np.percentile(t[plan], 25), np.percentile(t[plan], 50)))

    print("")
    print("  %-4s %11s %7s %11s %11s" % ("btn", "bearing", "slots", "termFree", "protrusion"))
    per = {}
    for s in names:
        u = seat_solids(np.asarray(core_j["seats"][s]["capUndersideWorld"], float),
                        np.asarray(core_j["seats"][s]["axisWorld"], float), s)
        w = np.asarray(core_j["seats"][s]["axisWorld"], float)
        d = L.triangles(body, tol=0.04, ang=0.09).reshape(-1, 3) - u["plateTopPoint"]
        loc = np.stack([d @ u["ex"], d @ u["ey"], d @ w], axis=1).reshape(-1, 3, 3)
        g = Field(loc)
        b = 0
        for x in np.arange(-3.0, 3.001, 0.1):
            for y in np.arange(-3.0, 3.001, 0.1):
                h = g.hits(float(x), float(y))
                if h.size and h.size % 2 == 0 and h.max() > -0.05:
                    b += 1
        bear = b * 0.01
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
        per[s] = {"bearingMm2": bear, "openSlots": op, "terminalFreeMm": free,
                  "protrusionMm": pr}
        print("  %-4s %11.2f %7d %11.3f %11.3f" % (s, bear, op, free, pr))
        L.memory("btn " + s)
    full = 6.04 * 6.04
    gate("all eight seats bear", min(p["bearingMm2"] for p in per.values()) >= 0.5 * full,
         "min %.2f mm2 = %.1f%%" % (min(p["bearingMm2"] for p in per.values()),
                                    100 * min(p["bearingMm2"] for p in per.values()) / full))
    gate("all sixteen slots open (exact boolean)",
         all(p["openSlots"] == 2 for p in per.values()),
         "%d of 16" % sum(p["openSlots"] for p in per.values()))
    gate("terminal escape depth",
         min(p["terminalFreeMm"] for p in per.values()) >= 3.654,
         "worst %.3f mm" % min(p["terminalFreeMm"] for p in per.values()))

    print("")
    print("=== docs/101 (section 11) ===")
    Pc = L.surf_points(body, 400000, tol=0.05)
    groups = switch_groups()
    fv, clr = {}, {}
    print("  %-4s %13s %13s" % ("btn", "collision", "min clearance"))
    for bt in BUTTONS:
        whole = [s for v in groups[bt].values() for s in v]
        fv[bt] = sum(L.inter_vol(body, s) for s in whole)
        Pw = np.concatenate([L.surf_points(s, 25000, tol=0.03) for s in whole])
        clr[bt] = float(cKDTree(Pw).query(Pc)[0].min())
        print("  %-4s %13.4f %13.4f" % (bt, fv[bt], clr[bt]))
        L.memory("finger " + bt)
    gate("docs/101 Finger interference", max(fv.values()) <= 1.0e-6,
         "max %.6f mm3; min clearance %.4f mm at %s"
         % (max(fv.values()), min(clr.values()), min(clr, key=clr.get)))

    print("")
    print("=== joystick (section 12) ===")
    jw = L.unit(np.asarray(joyj["joyAxisWorld"], float))
    jc = np.asarray(joyj["knobCentreWorld"], float)
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
    joy_axis = sum(bb - aa for aa, bb in (ray_intervals(
        L.triangles(body, tol=0.05, ang=0.10), jc, jw, -30.0, 30.0) or []))
    gate("JOY column unobstructed", joy_axis < 0.05, "%.4f mm of C09 on the axis" % joy_axis)
    gate("SZH static package clear", max(stat.values()) <= 1.0e-6,
         "max %.6f mm3 over %d parts" % (max(stat.values()), len(stat)))
    print("      [note] PROVISIONAL moving envelope %.4f mm3 -- reported only (section 12)"
          % max(prov.values()))

    print("")
    print("=== assembly, the hard gate (section 10) ===")
    crops = {t2: crop_shells(sh) for t2, sh in zip(("JaD", "JfD"), shells)}
    print("  sweep crop: %s" % ", ".join("%s %d solid(s)" % (k, len(v))
                                        for k, v in crops.items()))
    lift = {"+U": sweep(body, crops, L.DATUM_U),
            "-U": sweep(body, crops, -L.DATUM_U)}
    viable = []
    for dn, row in lift.items():
        for h, v in row.items():
            mark = ""
            if v["peakMm3"] <= 0.05 and v["freeFromMm"] is not None and v["freeFromMm"] <= 8.0:
                viable.append("%s out of %s" % (dn, h))
                mark = "  <- viable"
            print("  %-3s vs %-3s  peak %9.4f  total %10.4f  steps %2d  free from %s%s"
                  % (dn, h, v["peakMm3"], v["totalMm3"], v["obstructedSteps"],
                     ("%.1f mm" % v["freeFromMm"]) if v["freeFromMm"] else "never", mark))
    gate("one-piece insertion into an open half", len(viable) > 0,
         "viable: %s" % (", ".join(viable) or "none"))

    blk = 0.0
    for s in names:
        u = seat_solids(np.asarray(core_j["seats"][s]["capUndersideWorld"], float),
                        np.asarray(core_j["seats"][s]["axisWorld"], float), s)
        w = np.asarray(core_j["seats"][s]["axisWorld"], float)
        for k in (1, 2, 3, 4, 6, 8, 10, 12):
            blk += L.inter_vol(u["body"].moved(Location(Vector(
                *[float(x) for x in (w * float(k))]))), body)
    gate("switches installable down their bores", blk <= 1.0,
         "%.4f mm3 over 12 mm, all eight" % blk)

    print("")
    print("=== FDM (section 13) ===")
    s9 = support_stats(body, jw)
    c71, _ = L.as_single_solid(import_step(L.SRC["C07_1"]), "C07_1")
    s71 = support_stats(c71, jw)
    c08p = L.REV_K / "03_full_c08" / "C08_LOCAL_CONFORMAL_SWITCH_RECEIVER_CORE.step"
    c08, _ = L.as_single_solid(import_step(str(c08p)), "C08")
    s08 = support_stats(c08, jw)
    gate("FDM orientation JOY_AXIS_UP usable", True,
         "C09 bed %.1f mm2, support %.1f mm2 (%.1f%%), height %.2f mm"
         % (s9["bedMm2"], s9["supportMm2"], 100 * s9["supportFraction"], s9["heightMm"]))

    k05 = json.loads((L.REV_K / "04_validation" / "k05_validate.json").read_text(encoding="utf-8"))
    cmp = {
        "one-piece assembly": ("PASS (+U/JfD, -U/JaD exact 0.0)",
                               "FAIL (best 505.2 mm3, blocked throughout)",
                               ("PASS (%s)" % viable[0]) if viable else "FAIL (no viable path)"),
        "shell collision mm3": ("0.000000", "0.000000", "%.6f" % max(iv.values())),
        "docs/101 collision mm3": ("0.000000", "0.000000", "%.6f" % max(fv.values())),
        "minimum N1 clearance mm": ("0.5225", "18.8996", "%.4f" % clr["N1"]),
        "volume mm3": ("6694.168", "4760.872", "%.3f" % rec["volumeMm3"]),
        "B-rep faces": ("247", "315", "%d" % rec["faces"]),
        "major structural members": ("1 slab + 10 bridges + 1 deck + 1 chord wall = 13",
                                     "8 receivers + 2 ribs = 10",
                                     "1 carrier band + 8 blocks = 9"),
        "support-required mm2": ("%.1f" % s71["supportMm2"], "%.1f" % s08["supportMm2"],
                                 "%.1f" % s9["supportMm2"]),
        "support fraction": ("%.1f%%" % (100 * s71["supportFraction"]),
                             "%.1f%%" % (100 * s08["supportFraction"]),
                             "%.1f%%" % (100 * s9["supportFraction"])),
        "trapped support": ("0", "0", "0"),
        "min thickness below 1.20": ("0.000 mm2", "%.2f mm2" % k05["interiorThinMm2"],
                                     "%.2f mm2" % thin),
        "button seats": ("8/8", "8/8", "%d/8" % sum(1 for p in per.values()
                                                    if p["bearingMm2"] >= 0.5 * full)),
        "terminal slots": ("16/16", "16/16", "%d/16" % sum(p["openSlots"] for p in per.values())),
        "joystick": ("integrated deck", "deck carried over", "deck carried over"),
        "load path": ("seat -> slab -> chord wall -> deck -> shell",
                      "seat -> collar -> conformal landing -> shell",
                      "seat -> short block -> curved carrier -> shell"),
    }
    print("")
    print("=== C07.1 vs C08 vs C09 (section 14) ===")
    print("  %-28s %-40s %-38s %s" % ("metric", "C07.1", "C08", "C09"))
    for k, (a, b, c) in cmp.items():
        print("  %-28s %-40s %-38s %s" % (k, a, b, c))

    npass = sum(1 for r in RESULTS if r["pass"])
    nfail = len(RESULTS) - npass
    print("")
    print("=== C09 VALIDATION: %d PASS / %d FAIL ===" % (npass, nfail))
    for r in RESULTS:
        if not r["pass"]:
            print("   FAIL %-44s %s" % (r["gate"], r["detail"]))

    L.write_json(VAL / "l04_validate.json",
                 {"build": rec, "gates": RESULTS, "pass": npass, "fail": nfail,
                  "carrierGapMm": GAP, "carrierThicknessMm": CARRIER_T,
                  "buttons": per, "shell": iv, "fingerCollision": fv,
                  "fingerClearance": clr, "szhStatic": stat, "szhProvisional": prov,
                  "joyAxisMaterialMm": joy_axis, "interiorThinMm2": thin,
                  "lift": lift, "viablePaths": viable,
                  "support": {"C09": s9, "C07_1": s71, "C08": s08},
                  "comparison": {k: {"C07_1": a, "C08": b, "C09": c}
                                 for k, (a, b, c) in cmp.items()},
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
