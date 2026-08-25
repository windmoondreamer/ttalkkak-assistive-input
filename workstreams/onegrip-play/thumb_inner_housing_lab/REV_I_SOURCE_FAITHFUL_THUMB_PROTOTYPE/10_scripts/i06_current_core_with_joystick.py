"""I06 - CURRENT Thumb core, seats + joystick together (REV_I sections 8, 13, 15).

Section 15 forbids finishing the buttons and inserting the joystick afterwards,
so the seats and the joystick package are placed and evaluated in one pass.

The seat unit is REV_H's, unchanged (h03_placement.seat_solids).  What changes is
WHERE it goes: REV_H hung the seat off the inherited "lowered" cap underside,
which I02 showed is 4.12 - 7.18 mm BELOW the outer skin.  I02c re-derived each
cap position from the ORIGINAL protrusion law, and the seats hang off that
instead, which moves them 5.57 - 8.38 mm outward.

Section 13: keep-outs are reported by CLASS and none of them cuts geometry here.
The provisional SZH 25 deg moving envelope in particular is reported, never
subtracted -- using it as a cutter is what destroyed the T7/T8 seats in REV_H.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Compound, Location, Vector, export_step, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals  # noqa: E402
from h03_placement import KEEPOUTS, TERM_LO, seat_solids  # noqa: E402
from i03_original_joystick_architecture import SZH_CLASS  # noqa: E402

OUT = L.LAB / "06_current_core"
SRC_PLACE = L.LAB / "02_original_external_stack" / "i02c_source_faithful_cap_placement.json"

KO_CLASS = {
    "ORIGINAL_SCREW_1": "CONFIDENT STATIC",
    "ORIGINAL_SCREW_2": "CONFIDENT STATIC",
    "ORIGINAL_SCREW_3": "CONFIDENT STATIC",
    "FROZEN_CONTROL_AXES": "CONFIDENT STATIC",
    "N1_N2_SHARED_CARRIER": "EXTERNAL SUBSYSTEM - REVALIDATE AFTER FINGER FREEZE",
}
for k, v in SZH_CLASS.items():
    KO_CLASS["SZH_" + k] = v
KO_CLASS.update({
    "SZH_pcb": "PROVISIONAL STATIC", "SZH_gimbal": "PROVISIONAL STATIC",
    "SZH_x_pot": "PROVISIONAL STATIC", "SZH_y_pot": "PROVISIONAL STATIC",
    "SZH_push_switch": "PROVISIONAL STATIC", "SZH_shaft": "PROVISIONAL MOVING",
    "SZH_cap": "REMOVABLE HARDWARE", "SZH_header": "REMOVABLE HARDWARE",
    "SZH_MOVING_ENVELOPE": "PROVISIONAL MOVING ENVELOPE",
    "SZH_MOUNT_HOLE_CENTRES_LOCAL": "PROVISIONAL STATIC",
})


def classify(lab):
    for k, v in KO_CLASS.items():
        if lab == k or lab.startswith(k):
            return v
    return "UNCLASSIFIED"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pl = json.loads(SRC_PLACE.read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    shell = []
    for k in ("JAD_APPROVED", "JFD_APPROVED"):
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        shell.append(s)
    Tsh = np.concatenate([L.triangles(s, tol=0.06, ang=0.12) for s in shell])
    print("approved shell: %d solids, %d triangles" % (len(shell), len(Tsh)))
    L.memory("shell")

    seats = {}
    print("")
    print("=== seats placed from the RESTORED cap positions ===")
    print("%-5s %11s %11s %11s %11s %11s"
          % ("ctrl", "body^shell", "term^shell", "act^shell", "termFree", "plate->shell"))
    rows = {}
    for short in names:
        b = pl["buttons"][short]
        w = np.asarray(b["axisWorld"], float)
        cu = np.asarray(b["newCapUndersideWorld"], float)
        s = seat_solids(cu, w, short)
        seats[short] = s
        ib = sum(L.inter_vol(s["body"], x) for x in shell)
        it = sum(L.inter_vol(s["terminals"], x) for x in shell)
        ia = sum(L.inter_vol(s["actuator"], x) for x in shell)
        top = s["plateTopPoint"]
        h = ray_intervals(Tsh, top, -w, 0.0, 60.0)
        free = float(min([a for a, _ in (h or [])], default=60.0))
        # how far outward from the plate plane to shell material (the load path)
        h2 = ray_intervals(Tsh, top, w, 0.0, 60.0)
        up = float(min([a for a, _ in (h2 or [])], default=float("nan")))
        rows[short] = {"axisWorld": w.tolist(),
                       "plateTopWorld": top.tolist(),
                       "capUndersideWorld": cu.tolist(),
                       "axialShiftFromRevHMm": b["axialShiftOutwardMm"],
                       "bodyShellMm3": ib, "terminalShellMm3": it, "actuatorShellMm3": ia,
                       "terminalFreeDepthMm": free, "terminalNeedMm": -TERM_LO,
                       "plateToShellOnAxisMm": up}
        print("%-5s %11.4f %11.4f %11.4f %11.3f %11.3f"
              % (short, ib, it, ia, free, up))
        L.memory("seat " + short)

    print("")
    print("=== neighbouring seat interference ===")
    worst, pair = 0.0, {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            v = 0.0
            for ka in ("body", "terminals"):
                for kb in ("body", "terminals"):
                    v += L.inter_vol(seats[a][ka], seats[b][kb])
            if v > 1.0e-6:
                pair["%s-%s" % (a, b)] = v
                worst = max(worst, v)
                print("  %-8s %9.4f mm3" % ("%s-%s" % (a, b), v))
    if not pair:
        print("  none")
    print("  worst mechanism-to-mechanism overlap = %.4f mm3" % worst)

    print("")
    print("=== seat mechanism vs keep-outs, BY CLASS (section 13, nothing is cut) ===")
    keep = import_step(str(KEEPOUTS))
    hits = {}
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if not ch.solids() or lab.startswith("CAP_"):
            continue
        ks, _ = L.as_single_solid(ch, lab)
        cls = classify(lab)
        for short in names:
            v = sum(L.inter_vol(seats[short][k], ks)
                    for k in ("body", "terminals", "actuator", "plate"))
            if v > 1.0e-6:
                hits.setdefault(cls, {})["%s / %s" % (short, lab)] = v
        del ks
        L.memory("ko " + lab)
    order = ["CONFIDENT STATIC", "PROVISIONAL STATIC", "REMOVABLE HARDWARE",
             "PROVISIONAL MOVING", "PROVISIONAL MOVING ENVELOPE",
             "EXTERNAL SUBSYSTEM - REVALIDATE AFTER FINGER FREEZE", "UNCLASSIFIED"]
    for cls in order:
        if cls not in hits:
            print("  %-52s none" % cls)
            continue
        tot = sum(hits[cls].values())
        print("  %-52s %9.4f mm3 total" % (cls, tot))
        for k, v in sorted(hits[cls].items(), key=lambda t: -t[1])[:8]:
            print("      %-44s %9.4f" % (k, v))

    static_bad = sum(hits.get("CONFIDENT STATIC", {}).values())
    prov_static = sum(hits.get("PROVISIONAL STATIC", {}).values())
    moving = sum(hits.get("PROVISIONAL MOVING ENVELOPE", {}).values())
    print("")
    print("=== section 13 split ===")
    print("  CONFIDENT STATIC collision            %9.4f mm3" % static_bad)
    print("  PROVISIONAL STATIC collision          %9.4f mm3" % prov_static)
    print("  PROVISIONAL MOVING-ENVELOPE collision %9.4f mm3" % moving)
    print("  T7 / T8 seats are RETAINED regardless of the moving envelope.")

    asm = Compound(children=[seats[s][k] for s in names
                             for k in ("body", "terminals", "actuator", "plate")],
                   label="I06_RESTORED_SEAT_UNITS")
    export_step(asm, str(OUT / "I06_RESTORED_SEAT_UNITS.step"))

    up = np.array([rows[k]["plateToShellOnAxisMm"] for k in rows])
    print("")
    print("  plate-plane to shell on axis: %.3f to %.3f mm  (REV_H was 7.63 to 12.70)"
          % (np.nanmin(up), np.nanmax(up)))

    L.write_json(OUT / "i06_current_core.json",
                 {"seats": rows, "neighbourPairs": pair,
                  "worstNeighbourMm3": worst,
                  "keepOutHitsByClass": hits,
                  "confidentStaticMm3": static_bad,
                  "provisionalStaticMm3": prov_static,
                  "provisionalMovingEnvelopeMm3": moving,
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
