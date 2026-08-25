"""J02 - C07 against the docs/101 shell and all 8 Finger switch regions.

Sections 8, 9, 10.  Nothing is modified: this measures only.

The docs/101 switch STEP has a labelling quirk that has to be handled or the
audit silently covers one button: every leaf inside all eight groups is stamped
`N3_...`.  The button identity lives on the PARENT group label
(`I2_DETAILED_SWITCH_PLACEMENT`), so a dict keyed by leaf label collapses eight
buttons into one.

Five separate volumes are tested per Finger button, because they fail
differently:

    BODY      the switch body solid
    ACTUATOR  the Ø3.35 plunger
    TERMINALS four solder tabs
    POCKET    body grown by the docs/101 clearance, 0.2 mm per side -- the cut
              that actually exists in the shell
    SERVICE   the whole switch swept 12 mm back along its press axis, i.e. the
              corridor needed to insert or withdraw it and to reach it with
              epoxy or an iron
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Align, Box, Compound, Location, Plane, Vector, export_step, import_step
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402

OUT = L.LAB / "03_collision"
CAND = L.REV_I / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step"
POCKET_CLR = 0.20      # docs/101 architecture.bodyPocketClearancePerSideMm
SERVICE_MM = 12.0
BUTTONS = ("N1", "N2", "I2", "I3", "I4", "M3", "M4", "N3")


def switch_groups():
    """{button: {role: solid}} keyed by the PARENT group label."""
    root = import_step(L.SRC["D101_SWITCHES"])
    out = {}
    for grp in list(getattr(root, "children", []) or []):
        name = str(grp.label).split("_")[0]
        parts = {}
        for ch in list(getattr(grp, "children", []) or []):
            lab = str(ch.label)
            role = ("ACTUATOR" if "ACTUATOR" in lab else
                    "BODY" if "MAIN_BODY" in lab else "TERMINAL")
            s, _ = L.as_single_solid(ch, name + "_" + lab)
            parts.setdefault(role, []).append(s)
        out[name] = parts
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    dat = json.loads((L.ROOT / "build123d_workbench/out/lower15_true_bare_finger_base"
                      / "finger_button_frozen_datums.json").read_text(encoding="utf-8"))
    axes = {k: L.unit(np.asarray(v["pressAxis"], float)) for k, v in dat["controls"].items()}
    cent = {k: np.asarray(v["centerMm"], float) for k, v in dat["controls"].items()}

    core, _ = L.as_single_solid(import_step(str(CAND)), "C07")
    print("C07: vol %.3f mm3, %d faces" % (L.vol(core), len(list(core.faces()))))
    Pc = L.surf_points(core, 500000, tol=0.05)
    tree_core = cKDTree(Pc)
    L.memory("core")

    # ---- section 8: shell -------------------------------------------------
    print("")
    print("=== section 8: C07 vs the docs/101 shell halves ===")
    shells, shell_iv = {}, {}
    for tag, key in (("JaD", "D101_JAD"), ("JfD", "D101_JFD")):
        s, _ = L.as_single_solid(import_step(L.SRC[key]), tag)
        shells[tag] = s
        v = L.inter_vol(core, s)
        shell_iv[tag] = v
        print("  C07 n %-3s = %.6f mm3" % (tag, v))
        L.memory("shell " + tag)
    Ps = np.concatenate([L.surf_points(s, 900000, tol=0.06) for s in shells.values()])
    Ps = Ps[np.linalg.norm(Ps - L.DATUM_P, axis=1) < 55.0]
    d = cKDTree(Ps).query(Pc)[0]
    # C07 was built with a 0.35 mm shell guard and three landing pads, so contact
    # within that band is the designed load path, not a defect
    contact = float((d <= 0.60).sum()) / len(d)
    print("  min gap %.4f mm, p05 %.4f, p50 %.4f" % (d.min(), np.percentile(d, 5),
                                                     np.percentile(d, 50)))
    print("  EXPECTED CONTACT   : %.2f%% of the core surface within 0.60 mm"
          " (designed standoff landings)" % (100 * contact))
    print("  UNINTENDED PENETRATION: %.6f mm3 total"
          % (shell_iv["JaD"] + shell_iv["JfD"]))

    # ---- section 9 / 10: Finger regions -----------------------------------
    print("")
    print("=== section 9: C07 vs all 8 docs/101 Finger switch regions ===")
    groups = switch_groups()
    print("  groups found: %s" % ", ".join(sorted(groups)))
    rows, keep = {}, []
    print("")
    print("%-4s %11s %11s %11s %11s %11s %11s  %s"
          % ("btn", "pocket", "body", "actuator", "terminals", "service", "minClr", "result"))
    for b in BUTTONS:
        g = groups[b]
        w = axes[b]
        ex, ey = frame(w)
        body = g["BODY"][0]
        act = g["ACTUATOR"][0]
        terms = g["TERMINAL"]
        whole = [body, act] + terms

        # pocket: the body's own extent in the press frame, grown per side
        Pb = L.surf_points(body, 60000, tol=0.03)
        c0 = Pb.mean(axis=0)
        lx, ly, lz = (Pb - c0) @ ex, (Pb - c0) @ ey, (Pb - c0) @ w
        pocket = Plane(origin=L.xyz(c0 + w * float(lz.min() - POCKET_CLR)),
                       x_dir=L.xyz(ex), z_dir=L.xyz(w)) * Box(
            float(lx.max() - lx.min()) + 2 * POCKET_CLR,
            float(ly.max() - ly.min()) + 2 * POCKET_CLR,
            float(lz.max() - lz.min()) + 2 * POCKET_CLR,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        pocket.label = b + "_POCKET"

        v_pocket = L.inter_vol(core, pocket)
        v_body = L.inter_vol(core, body)
        v_act = L.inter_vol(core, act)
        v_term = sum(L.inter_vol(core, t) for t in terms)
        v_serv = 0.0
        for k in range(1, int(SERVICE_MM) + 1):
            mv = Location(Vector(*[float(x) for x in (-w * float(k))]))
            for s in whole:
                v_serv += L.inter_vol(core, s.moved(mv))

        Pw = np.concatenate([L.surf_points(s, 40000, tol=0.03) for s in whole])
        clr = float(tree_core.query(Pw)[0].min())

        hard = max(v_body, v_act, v_term) > 1.0e-6 or v_pocket > 1.0
        minor = (not hard) and (v_pocket > 1.0e-6 or v_serv > 1.0e-6 or clr < 0.60)
        res = ("HARD COLLISION" if hard else
               "MINOR LOCAL ADJUSTMENT" if minor else "PASS")
        rows[b] = {"pocketMm3": v_pocket, "bodyMm3": v_body, "actuatorMm3": v_act,
                   "terminalsMm3": v_term, "serviceCorridorMm3": v_serv,
                   "minClearanceMm": clr, "result": res,
                   "centerMm": cent[b].tolist(), "pressAxis": w.tolist()}
        print("%-4s %11.4f %11.4f %11.4f %11.4f %11.4f %11.4f  %s"
              % (b, v_pocket, v_body, v_act, v_term, v_serv, clr, res))
        keep.append(pocket)
        del Pb, Pw
        L.memory("finger " + b)

    mn = min(r["minClearanceMm"] for r in rows.values())
    nhard = sum(1 for r in rows.values() if r["result"] == "HARD COLLISION")
    nminor = sum(1 for r in rows.values() if r["result"] == "MINOR LOCAL ADJUSTMENT")
    print("")
    print("  minimum Finger/Thumb clearance = %.4f mm  (%s)"
          % (mn, min(rows, key=lambda k: rows[k]["minClearanceMm"])))
    print("  HARD %d / MINOR %d / PASS %d" % (nhard, nminor, len(rows) - nhard - nminor))

    export_step(Compound(children=keep, label="D101_FINGER_POCKETS"),
                str(OUT / "J02_FINGER_POCKET_ENVELOPES.step"))
    L.write_json(OUT / "j02_collision.json",
                 {"candidate": str(CAND), "pocketClearancePerSideMm": POCKET_CLR,
                  "serviceCorridorMm": SERVICE_MM,
                  "shellInterferenceMm3": shell_iv,
                  "shellMinGapMm": float(d.min()),
                  "expectedContactFractionWithin0p60mm": contact,
                  "unintendedPenetrationMm3": shell_iv["JaD"] + shell_iv["JfD"],
                  "fingers": rows, "minFingerClearanceMm": mn,
                  "hard": nhard, "minor": nminor, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
