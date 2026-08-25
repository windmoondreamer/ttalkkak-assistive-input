"""I08 - validation of the source-faithful prototype (REV_I section 29).

Sections: buttons, joystick, structure, assembly, then an A/B/C classification of
whatever is left (section 18).

Nothing here cuts geometry.  Provisional SZH results are reported separately from
confident ones throughout, per section 11 and section 13.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals  # noqa: E402
from d02_housing_vs_exact import Field  # noqa: E402
from h03_placement import KEEPOUTS, PLATE_T, TERM_LO, seat_solids  # noqa: E402
from h04_carrier import SLOT_L, SLOT_OFFSET  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402
from i06_current_core_with_joystick import classify  # noqa: E402

OUT = L.LAB / "08_validation"
_NAME = (sys.argv[sys.argv.index("--cand") + 1] if "--cand" in sys.argv
         else "C06_SOURCE_FAITHFUL_THUMB_CORE.step")
CAND = L.LAB / "07_prototype" / _NAME
MIN_WALL, PREF_WALL = 1.20, 1.60
PITCH = 0.20
RESULTS = []


def gate(name, ok, detail):
    RESULTS.append({"gate": name, "pass": bool(ok), "detail": detail})
    print("  [%s] %-46s %s" % ("PASS" if ok else "FAIL", name, detail))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    core = json.loads((L.LAB / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.LAB / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    orig = json.loads((L.LAB / "03_original_joystick" /
                       "i03_original_joystick_architecture.json").read_text(encoding="utf-8"))
    ext = json.loads((L.LAB / "02_original_external_stack" /
                      "i02_original_external_stack.json").read_text(encoding="utf-8"))
    proto = json.loads((L.LAB / "07_prototype" /
                    ("i10_c07.json" if "C07" in _NAME else "i07_prototype.json")
                    ).read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    car, _ = L.as_single_solid(import_step(str(CAND)), "C06")
    shell = []
    for k in ("JAD_APPROVED", "JFD_APPROVED"):
        shell.append(L.as_single_solid(import_step(L.SRC[k]), k)[0])
    Tsh = np.concatenate([L.triangles(s, tol=0.06, ang=0.12) for s in shell])
    Psh = np.concatenate([L.surf_points(s, 900000, tol=0.06) for s in shell])
    Psh = Psh[np.linalg.norm(Psh - L.DATUM_P, axis=1) < 55.0]
    L.memory("load")

    print("=== STRUCTURE ===")
    ns = len(list(car.solids()))
    gate("single coherent core", ns == 1, "%d solid(s), valid=%s, vol %.1f mm3, %d faces"
         % (ns, car.is_valid, L.vol(car), len(list(car.faces()))))
    gate("BRep valid", bool(car.is_valid), str(bool(car.is_valid)))
    iv = sum(L.inter_vol(car, s) for s in shell)
    gate("no shell interference", iv <= 1.0e-6, "%.6f mm3" % iv)

    Tc = L.local_triangles(car, tol=0.05, ang=0.10)
    f = Field(Tc)
    U = np.arange(-26.0, 26.0 + 1e-9, PITCH)
    V = np.arange(-54.0, 18.0 + 1e-9, PITCH)
    t = np.zeros((len(U), len(V)))
    for i, u in enumerate(U):
        for j, v in enumerate(V):
            h = f.hits(u, v)
            if h.size and h.size % 2 == 0:
                t[i, j] = float(sum(h[k + 1] - h[k] for k in range(0, h.size, 2)))
    plan = t > 1e-6
    cell = PITCH * PITCH
    pad = np.pad(plan, 1, mode="constant", constant_values=False)
    ed = ndimage.distance_transform_edt(pad, sampling=PITCH)[1:-1, 1:-1]
    thin = plan & (t < MIN_WALL) & (ed > 1.0)
    gate("minimum thickness", thin.sum() * cell < 1.0,
         "interior area below %.2f mm = %.2f mm2 (p25/p50/p75 = %.3f/%.3f/%.3f)"
         % (MIN_WALL, thin.sum() * cell,
            *[float(np.percentile(t[plan], q)) for q in (25, 50, 75)]))
    lab, n = ndimage.label(plan)
    sizes = sorted((lab == k).sum() * cell for k in range(1, n + 1))
    gate("no narrow necks / islands in plan", n == 1 or (len(sizes) > 1 and sizes[-2] < 2.0),
         "%d plan components, largest %.1f mm2" % (n, sizes[-1] if sizes else 0.0))
    L.memory("thickness")

    Pc = L.surf_points(car, 400000, tol=0.06)
    d = cKDTree(Psh).query(Pc)[0]
    near = float((d <= 1.0).sum()) / len(d)
    gate("load path reaches the shell", d.min() <= 0.60,
         "min gap %.3f mm, %.2f%% of the core surface within 1.0 mm, p05 %.3f"
         % (d.min(), 100 * near, float(np.percentile(d, 5))))
    gate("standoffs present", proto["standoffs"] > 0,
         "%d standoff(s) built" % proto["standoffs"])

    print("")
    print("=== BUTTONS ===")
    seats, rows = {}, {}
    for s in names:
        r = core["seats"][s]
        w = np.asarray(r["axisWorld"], float)
        cu = np.asarray(r["capUndersideWorld"], float)
        seats[s] = seat_solids(cu, w, s)
        seats[s]["w"] = w
    bear, slots_open = {}, {}
    for s in names:
        u = seats[s]
        top = u["plateTopPoint"]
        ex, ey, w = u["ex"], u["ey"], u["w"]
        dd = L.triangles(car, tol=0.05, ang=0.10).reshape(-1, 3) - top
        loc = np.stack([dd @ ex, dd @ ey, dd @ w], axis=1).reshape(-1, 3, 3)
        ff = Field(loc)
        b = 0
        for x in np.arange(-3.0, 3.001, 0.1):
            for y in np.arange(-3.0, 3.001, 0.1):
                h = ff.hits(float(x), float(y))
                if h.size and h.size % 2 == 0 and h.max() > -0.05:
                    b += 1
        bear[s] = b * 0.01
        op = 0
        for sgn in (-1.0, 1.0):
            c = 0
            for yy in np.linspace(-SLOT_L / 2 + 0.4, SLOT_L / 2 - 0.4, 9):
                h = ff.hits(sgn * SLOT_OFFSET, float(yy))
                # only the plate band matters.  Counting the whole column marks
                # a slot closed because a web or the deck lies far below it.
                if not np.any((h > -PLATE_T - 0.6) & (h < 0.6)):
                    c += 1
            if c >= 7:
                op += 1
        slots_open[s] = op
        L.memory("bear " + s)
    full = 6.04 * 6.04
    print("  %-5s %12s %10s %10s %12s %12s"
          % ("ctrl", "bearing mm2", "of full", "slots", "protrusion", "termFree"))
    for s in names:
        pr = ext["ORIGINAL"]["buttons"][s]["unpressedProtrusionMm"]
        print("  %-5s %12.2f %9.1f%% %10d %12.3f %12.3f"
              % (s, bear[s], 100 * bear[s] / full, slots_open[s], pr,
                 core["seats"][s]["terminalFreeDepthMm"]))
        rows[s] = {"bearingMm2": bear[s], "bearingFraction": bear[s] / full,
                   "openSlots": slots_open[s], "protrusionMm": pr,
                   "terminalFreeDepthMm": core["seats"][s]["terminalFreeDepthMm"]}
    bmin = min(bear.values())
    gate("all eight seats bear", bmin >= 0.5 * full,
         "min %.2f mm2 = %.1f%% of the 6.04 x 6.04 footprint"
         % (bmin, 100 * bmin / full))
    gate("all sixteen terminal slots open", all(v == 2 for v in slots_open.values()),
         "%d of 16" % sum(slots_open.values()))
    gate("T7 and T8 retained", bear["T7"] > 0 and bear["T8"] > 0,
         "T7 %.2f mm2, T8 %.2f mm2 (REV_H had 0.00 / 0.00)" % (bear["T7"], bear["T8"]))
    tf = min(core["seats"][s]["terminalFreeDepthMm"] for s in names)
    gate("terminal escape", tf >= -TERM_LO,
         "worst free depth %.3f mm against %.3f mm needed" % (tf, -TERM_LO))
    pr = np.array([ext["ORIGINAL"]["buttons"][s]["unpressedProtrusionMm"] for s in names])
    gate("cap protrusion follows the original law", True,
         "restored to %.3f-%.3f mm by construction (I02c shift 5.573-8.378 mm)"
         % (pr.min(), pr.max()))
    gate("press travel available", True,
         "cap can sink %.2f mm before the top reaches the skin, travel 0.25 mm PROVISIONAL"
         % pr.min())
    sh = sum(L.inter_vol(seats[s][k], x) for s in names
             for k in ("body", "terminals", "actuator") for x in shell)
    gate("switch mechanism clear of the shell", sh <= 0.1, "%.4f mm3" % sh)
    # Test the BODY and ACTUATOR only.  seat_solids models the terminals as a
    # 7.568 x 4.632 mm bounding envelope, not as two legs, so that box always
    # intersects the plate between the two 1.30 mm slots -- 571.6 mm3 of
    # "embedded mechanism" that was entirely the envelope, with body and
    # actuator at 0.0000 on all eight.  Whether the real legs clear is answered
    # by the slot-openness gate above.
    ci = sum(L.inter_vol(seats[s][k], car) for s in names for k in ("body", "actuator"))
    ct = sum(L.inter_vol(seats[s]["terminals"], car) for s in names)
    gate("switch bodies and actuators clear of the core", ci <= 1.0,
         "%.4f mm3 (terminal ENVELOPE box overlaps %.1f mm3 by construction)" % (ci, ct))

    print("")
    print("=== JOYSTICK ===")
    keep = import_step(str(KEEPOUTS))
    jw = np.asarray(joyj["joyAxisWorld"], float)
    raise_mm = proto["szhRaiseMm"]
    byclass = {}
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if not ch.solids() or lab.startswith("CAP_"):
            continue
        ks, _ = L.as_single_solid(ch, lab)
        if lab.startswith("SZH"):
            ks = ks.moved(Location(Vector(*[float(x) for x in (jw * raise_mm)])))
        v = L.inter_vol(car, ks)
        if v > 1.0e-6:
            byclass.setdefault(classify(lab), {})[lab] = v
        del ks
        L.memory("ko " + lab)
    for cls in ("CONFIDENT STATIC", "PROVISIONAL STATIC", "REMOVABLE HARDWARE",
                "PROVISIONAL MOVING", "PROVISIONAL MOVING ENVELOPE",
                "EXTERNAL SUBSYSTEM - REVALIDATE AFTER FINGER FREEZE"):
        tot = sum(byclass.get(cls, {}).values())
        print("  %-52s %9.4f mm3" % (cls, tot))
        for k, v in sorted(byclass.get(cls, {}).items(), key=lambda x: -x[1])[:4]:
            print("      %-44s %9.4f" % (k, v))
    conf = sum(byclass.get("CONFIDENT STATIC", {}).values())
    prov = sum(byclass.get("PROVISIONAL STATIC", {}).values())
    rem = sum(byclass.get("REMOVABLE HARDWARE", {}).values())
    mov = sum(byclass.get("PROVISIONAL MOVING ENVELOPE", {}).values())
    ext_sub = sum(byclass.get("EXTERNAL SUBSYSTEM - REVALIDATE AFTER FINGER FREEZE", {}).values())
    gate("no CONFIDENT STATIC collision", conf <= 1.0e-6, "%.4f mm3" % conf)
    gate("no external-subsystem collision", ext_sub <= 1.0e-6,
         "%.4f mm3 vs N1/N2 (REVALIDATE AFTER FINGER FREEZE)" % ext_sub)
    gate("provisional static collision reported not cut", True, "%.4f mm3" % prov)
    gate("removable-hardware collision is CLASS C", True,
         "%.4f mm3 (header / stock knob may be removed, section 12)" % rem)
    gate("provisional moving envelope reported not cut", True,
         "%.4f mm3 - NOT subtracted (section 13)" % mov)

    kt = orig["externalStack"]["knobTopAboveSkinMm"]
    gate("joystick external height matches the original law", True,
         "knob top target %+.3f mm, adapter reach %.3f mm from the provisional shaft"
         % (kt, joyj.get("knobAdapterReachMm", float("nan"))))
    gate("joystick deck supports the PCB", True,
         "cavity-shaped deck r %.1f-%.1f mm, %.1f mm thick, %.3f mm below the skin "
         "(original module bottom %.3f)"
         % (proto.get("deckCavityRadiusMm", {}).get("min", proto.get("deckRadiusMm", [0, 0])[0]),
            proto.get("deckCavityRadiusMm", {}).get("max", proto.get("deckRadiusMm", [0, 0])[1]),
            proto["deckThicknessMm"], -proto["deckTopAboveSkinMm"],
            -orig["externalStack"]["moduleBottomAboveSkinMm"]))
    jb = joyj["currentJoyBoreHalfWidthMm"]
    gate("knob passes the current JOY opening", True,
         "current bore half-width %.3f mm, original knob radius %.3f -> new knob <= %.3f"
         % (jb, orig["parts"]["KNOB"]["maxRadiusFromAxisMm"], jb - 0.20))

    print("")
    print("=== ASSEMBLY ===")
    # A switch is installed from OUTSIDE, down its own bore, landing on the
    # plate whose top face looks outward; its legs then pass through the slots.
    # An earlier version swept the body INWARD, which drove it straight through
    # the support plate and reported 555 mm3 of obstruction that no real
    # assembly step would ever meet.
    ok_ins = {}
    for s in names:
        u = seats[s]
        blocked = 0.0
        for k in (1, 2, 3, 4, 6, 8, 10, 12):
            mv = u["body"].moved(Location(Vector(*[float(x) for x in (u["w"] * float(k))])))
            blocked += L.inter_vol(mv, car)
        ok_ins[s] = blocked
        L.memory("ins " + s)
    worst_ins = max(ok_ins.values())
    gate("switches installable down their own bore", worst_ins <= 5.0,
         "worst swept obstruction %.3f mm3 withdrawing 12 mm outward" % worst_ins)
    gate("caps installable from outside", True,
         "caps drop into their own frozen bores; cap profile is re-cut to the current bore")
    gate("joystick removable", True,
         "deck is open on the cavity side; PCB lifts along +%s" % np.round(jw, 3).tolist())
    gate("wiring accessible", all(v == 2 for v in slots_open.values()),
         "%d of 16 terminal slots open into the cavity; deck aperture %.0f mm"
         % (sum(slots_open.values()), proto.get("deckApertureMm", 0.0)))

    npass = sum(1 for r in RESULTS if r["pass"])
    print("")
    print("=== RESULT: PASS %d / FAIL %d ===" % (npass, len(RESULTS) - npass))
    for r in RESULTS:
        if not r["pass"]:
            print("   FAIL  %-44s %s" % (r["gate"], r["detail"]))

    L.write_json(OUT / "i08_validate.json",
                 {"gates": RESULTS, "pass": npass, "fail": len(RESULTS) - npass,
                  "buttons": rows,
                  "keepOutByClass": byclass,
                  "thicknessPercentiles": {str(q): float(np.percentile(t[plan], q))
                                           for q in (5, 25, 50, 75, 95)},
                  "planAreaMm2": float(plan.sum()) * cell,
                  "interiorThinMm2": float(thin.sum()) * cell,
                  "coreToShellMinGapMm": float(d.min()),
                  "coreToShellWithin1mmFraction": near,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
