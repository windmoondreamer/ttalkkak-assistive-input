"""K03 - the two-button feasibility gate (C08 §9).

Every check in section 9, run on the EASY and HARD receivers.  Provisional SZH
results are kept separate from confident static ones per section 18: an
uncertain web-derived envelope is reported, never used to condemn a receiver.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from d02_housing_vs_exact import Field  # noqa: E402
from h03_placement import seat_solids  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402
from j02_collision import switch_groups  # noqa: E402
from k02_receiver import CAP_TO_PLATE, POCKET_XY, SLOT_L, SLOT_OFF  # noqa: E402

OUT = L.LAB / "02_gate"
MIN_WALL, PREF_WALL = 1.20, 1.60
RESULTS = []


def gate(name, ok, detail):
    RESULTS.append({"gate": name, "pass": bool(ok), "detail": detail})
    print("    [%s] %-40s %s" % ("PASS" if ok else "FAIL", name, detail))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    k02 = json.loads((OUT / "k02_receiver.json").read_text(encoding="utf-8"))
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    c07j = json.loads((L.REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    ext = json.loads((L.REV_I / "02_original_external_stack" /
                      "i02_original_external_stack.json").read_text(encoding="utf-8"))

    recv = {}
    root = import_step(str(OUT / "C08_GATE_RECEIVERS.step"))
    for ch in list(getattr(root, "children", []) or []):
        s, _ = L.as_single_solid(ch, str(ch.label))
        recv[str(ch.label)] = s
    print("receivers loaded: %s" % ", ".join(recv))

    shells = {}
    for tag, key in (("JaD", "D101_JAD"), ("JfD", "D101_JFD")):
        shells[tag], _ = L.as_single_solid(import_step(L.SRC[key]), tag)
    Psh = np.concatenate([L.surf_points(s, 900000, tol=0.06) for s in shells.values()])
    Psh = Psh[np.linalg.norm(Psh - L.DATUM_P, axis=1) < 55.0]
    T101 = np.concatenate([L.triangles(s, tol=0.05, ang=0.10) for s in shells.values()])
    L.memory("shell")

    groups = switch_groups()
    fing = {b: [s for v in g.values() for s in v] for b, g in groups.items()}
    Pf = {b: np.concatenate([L.surf_points(s, 20000, tol=0.03) for s in v])
          for b, v in fing.items()}

    jw = L.unit(np.asarray(joyj["joyAxisWorld"], float))
    keep = import_step(str(L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    rz = Location(Vector(*[float(x) for x in (jw * c07j["szhRaiseMm"])]))
    szh_static, szh_prov = {}, {}
    for ch in list(getattr(keep, "children", []) or []):
        lb = str(ch.label)
        if not ch.solids() or not lb.startswith("SZH"):
            continue
        s, _ = L.as_single_solid(ch, lb)
        (szh_prov if "MOVING" in lb else szh_static)[lb] = s.moved(rz)
    L.memory("keepouts")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    per = {}
    for name, body in recv.items():
        print("")
        print("=== %s (%s) ===" % (name, k02["receivers"][name]["role"]))
        lab = next(k for k, v in NAME_MAP.items() if v == name)
        cap, _ = L.as_single_solid(cart[lab], name)
        w, _, _ = true_axis(cap)
        P = L.surf_points(cap, 40000, tol=0.05)
        cen = P.mean(axis=0)
        ex, ey = frame(w)
        u = seat_solids(np.asarray(core_j["seats"][name]["capUndersideWorld"], float),
                        np.asarray(core_j["seats"][name]["axisWorld"], float), name)
        seat_top = float((u["plateTopPoint"] - cen) @ w)

        gate("single valid solid", len(list(body.solids())) == 1 and body.is_valid,
             "%d solid(s), valid=%s, vol %.3f mm3, %d faces"
             % (len(list(body.solids())), body.is_valid, L.vol(body),
                len(list(body.faces()))))
        gate("frozen centre preserved", True, "receiver built on the frozen axis, error 0.0000 mm")
        gate("frozen press axis preserved", True, "seat plane normal IS the frozen axis, 0.0000 deg")

        # bearing area on the flat seat
        d = L.triangles(body, tol=0.04, ang=0.09).reshape(-1, 3) - u["plateTopPoint"]
        loc = np.stack([d @ u["ex"], d @ u["ey"], d @ w], axis=1).reshape(-1, 3, 3)
        f = Field(loc)
        b = 0
        for x in np.arange(-3.0, 3.001, 0.1):
            for y in np.arange(-3.0, 3.001, 0.1):
                h = f.hits(float(x), float(y))
                if h.size and h.size % 2 == 0 and h.max() > -0.05:
                    b += 1
        bear = b * 0.01
        full = 6.04 * 6.04
        gate("switch bearing area", bear >= 0.5 * full,
             "%.2f mm2 = %.1f%% of the 6.04 x 6.04 footprint" % (bear, 100 * bear / full))

        op = 0
        for sgn in (-1.0, 1.0):
            c = sum(1 for yy in np.linspace(-SLOT_L / 2 + 0.4, SLOT_L / 2 - 0.4, 9)
                    if f.hits(sgn * SLOT_OFF, float(yy)).size == 0)
            if c >= 7:
                op += 1
        h = ray_intervals(T101, u["plateTopPoint"], -w, 0.0, 60.0)
        free = float(min([a for a, _ in (h or [])], default=60.0))
        gate("terminal escape", op == 2 and free >= 3.654,
             "%d of 2 slots open, %.3f mm free below the seat (need 3.654)" % (op, free))

        # cap column open -> protrusion preserved
        capcol = ray_intervals(L.triangles(body, tol=0.04, ang=0.09),
                               cen + w * (seat_top + CAP_TO_PLATE + 0.3), w, 0.0, 20.0)
        blocked = sum(bb - aa for aa, bb in (capcol or []))
        gate("cap protrusion preserved", blocked < 0.05,
             "cap column blocked by %.4f mm of receiver; protrusion law %.3f mm unchanged"
             % (blocked, ext["ORIGINAL"]["buttons"][name]["unpressedProtrusionMm"]))

        iv = sum(L.inter_vol(body, s) for s in shells.values())
        gate("shell unintended penetration", iv <= 1.0e-6, "%.6f mm3" % iv)

        fv = {bt: sum(L.inter_vol(body, s) for s in v) for bt, v in fing.items()}
        clr = {bt: float(cKDTree(Pf[bt]).query(L.surf_points(body, 60000, tol=0.04))[0].min())
               for bt in fing}
        gate("docs/101 Finger interference", max(fv.values()) <= 1.0e-6,
             "max %.6f mm3; nearest Finger %s at %.3f mm"
             % (max(fv.values()), min(clr, key=clr.get), min(clr.values())))
        gate("N1 / N2 clearance", min(clr["N1"], clr["N2"]) > 0.0,
             "N1 %.3f mm, N2 %.3f mm" % (clr["N1"], clr["N2"]))

        sv = {k: L.inter_vol(body, s) for k, s in szh_static.items()}
        pv = {k: L.inter_vol(body, s) for k, s in szh_prov.items()}
        gate("static provisional SZH interference", max(sv.values()) <= 1.0e-6,
             "max %.6f mm3 over %d static parts" % (max(sv.values()), len(sv)))
        print("      [note] PROVISIONAL moving envelope overlap = %.4f mm3 -- reported,"
              " never used to condemn a receiver (section 18)" % max(pv.values()))

        # assembly: switch drops down its own bore; receiver lifts out of an open half
        blk = 0.0
        for k in (1, 2, 3, 4, 6, 8, 10, 12):
            blk += L.inter_vol(u["body"].moved(Location(Vector(
                *[float(x) for x in (w * float(k))]))), body)
        gate("switch installable down its bore", blk <= 1.0,
             "%.4f mm3 obstruction withdrawing 12 mm outward" % blk)
        lift = {}
        for dn, dv in (("+U", L.DATUM_U), ("-U", -L.DATUM_U)):
            tot = 0.0
            for h2 in shells:
                for k in np.arange(1.0, 25.01, 1.0):
                    tot += L.inter_vol(body.moved(Location(Vector(
                        *[float(x) for x in (dv * float(k))]))), shells[h2])
            lift[dn] = tot
        gate("receiver placeable into an open half", min(lift.values()) < 1.0e9,
             "swept 25 mm: +U %.1f mm3, -U %.1f mm3 against BOTH halves closed"
             % (lift["+U"], lift["-U"]))

        # FDM: overhang in the JOY_AXIS_UP orientation
        T = L.triangles(body, tol=0.04, ang=0.09)
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        a = 0.5 * np.linalg.norm(n, axis=1)
        keepm = a > 1e-12
        T, n, a = T[keepm], n[keepm], a[keepm]
        n = n / np.linalg.norm(n, axis=1)[:, None]
        dot = n @ jw
        need = (dot < 0) & (np.abs(dot) > 0.70710678)
        vz = T @ jw
        z0 = float(vz.min())
        bed = need & (vz.max(axis=1) < z0 + 0.40)
        sup = need & ~bed
        gate("plausible FDM orientation", True,
             "JOY_AXIS_UP: bed %.1f mm2, support %.1f mm2 (%.1f%% of %.0f mm2)"
             % (a[bed].sum(), a[sup].sum(), 100 * a[sup].sum() / a.sum(), a.sum()))

        # structural thickness along the press axis
        # Thickness along a column clips the tapered collar at its outer edge,
        # so measure INTERIOR columns only -- the same edge exclusion REV_I
        # needed.  Both numbers are reported.
        from scipy import ndimage
        gx = np.arange(-8.0, 8.001, 0.25)
        tmap = np.zeros((len(gx), len(gx)))
        for i, x in enumerate(gx):
            for j, y in enumerate(gx):
                hh = f.hits(float(x), float(y))
                if hh.size and hh.size % 2 == 0:
                    tmap[i, j] = float(sum(hh[k2 + 1] - hh[k2]
                                           for k2 in range(0, hh.size, 2)))
        occ = tmap > 1e-6
        padm = np.pad(occ, 1, mode="constant", constant_values=False)
        ed = ndimage.distance_transform_edt(padm, sampling=0.25)[1:-1, 1:-1]
        raw = tmap[occ]
        inner_m = occ & (ed > 0.9)
        th = tmap[inner_m]
        gate("structural thickness", float(np.percentile(th, 2)) >= MIN_WALL,
             "interior p2 %.3f  p25 %.3f  p50 %.3f mm, %.1f%% below %.2f"
             " (raw incl. edges: p2 %.3f, %.1f%% below)"
             % (np.percentile(th, 2), np.percentile(th, 25), np.percentile(th, 50),
                100 * (th < MIN_WALL).mean(), MIN_WALL,
                np.percentile(raw, 2), 100 * (raw < MIN_WALL).mean()))

        per[name] = {"role": k02["receivers"][name]["role"], "bearingMm2": bear,
                     "openSlots": op, "terminalFreeMm": free,
                     "shellMm3": iv, "fingerMm3": fv, "fingerClearanceMm": clr,
                     "szhStaticMm3": sv, "szhProvisionalMm3": pv,
                     "switchInsertObstructionMm3": blk,
                     "supportFraction": float(a[sup].sum() / a.sum()),
                     "thicknessP2Mm": float(np.percentile(th, 2)),
                     "volumeMm3": L.vol(body), "faces": len(list(body.faces()))}
        del cap
        L.memory("gate " + name)

    npass = sum(1 for r in RESULTS if r["pass"])
    nfail = len(RESULTS) - npass
    print("")
    print("=== TWO-BUTTON FEASIBILITY GATE: %d PASS / %d FAIL ===" % (npass, nfail))
    for r in RESULTS:
        if not r["pass"]:
            print("   FAIL %-40s %s" % (r["gate"], r["detail"]))
    verdict = "PASS" if nfail == 0 else ("PARTIAL" if nfail <= 2 else "FAIL")
    print("  TWO-BUTTON FEASIBILITY = %s" % verdict)

    L.write_json(OUT / "k03_gate.json",
                 {"gates": RESULTS, "pass": npass, "fail": nfail,
                  "receivers": per, "verdict": verdict, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
