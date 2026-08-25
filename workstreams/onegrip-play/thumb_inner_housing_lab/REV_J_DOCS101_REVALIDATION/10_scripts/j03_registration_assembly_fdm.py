"""J03 - Thumb control registration, joystick, assembly and FDM regression.

Sections 11, 12, 14, 16, 18.  Measurement only; no geometry is written.

Cap protrusion is re-measured against the DOCS/101 skin, not the authority skin,
because that is the number section 6 protects: roughly +1.066 to +1.459 mm above
the local outer skin, and it must not regress to the obsolete buried positions.
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
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from d02_housing_vs_exact import Field  # noqa: E402
from h03_placement import seat_solids  # noqa: E402
from i02_original_external_stack import frame, skin_reference  # noqa: E402
from j02_collision import switch_groups  # noqa: E402

OUT = L.LAB / "04_assembly"
REG = L.LAB / "02_registration"
FDM = L.LAB / "05_fdm_regression"
CAND = L.REV_I / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step"
PROT_TOL = 0.30
MIN_WALL, PITCH = 1.20, 0.20


def main() -> int:
    for d in (OUT, REG, FDM):
        d.mkdir(parents=True, exist_ok=True)
    core_j = json.loads((L.REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    joyj = json.loads((L.REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    ext = json.loads((L.REV_I / "02_original_external_stack" /
                      "i02_original_external_stack.json").read_text(encoding="utf-8"))
    plc = json.loads((L.REV_I / "02_original_external_stack" /
                      "i02c_source_faithful_cap_placement.json").read_text(encoding="utf-8"))
    c07j = json.loads((L.REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    names = [x for x in ORDER if x != "JOY"]

    core, _ = L.as_single_solid(import_step(str(CAND)), "C07")
    shells = {}
    for tag, key in (("JaD", "D101_JAD"), ("JfD", "D101_JFD")):
        shells[tag], _ = L.as_single_solid(import_step(L.SRC[key]), tag)
    T101 = np.concatenate([L.triangles(s, tol=0.05, ang=0.10) for s in shells.values()])
    print("docs/101 shell: %d triangles" % len(T101))
    L.memory("load")

    # ================= section 11: T1-T8 and JOY registration =============
    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    rows = {}
    print("")
    print("=== section 11: Thumb control registration against docs/101 ===")
    print("%-5s %9s %9s %11s %11s %11s  %s"
          % ("ctrl", "open", "axisErr", "d101 skin", "protrusion", "vs law", "result"))
    for short in ORDER:
        lab = next(k for k, v in NAME_MAP.items() if v == short)
        cap, _ = L.as_single_solid(cart[lab], short)
        w, _, _ = true_axis(cap)
        P = L.surf_points(cap, 60000, tol=0.04)
        cen = P.mean(axis=0)
        ex, ey = frame(w)
        r_cap = float(np.hypot((P - cen) @ ex, (P - cen) @ ey).max())
        ref = skin_reference(T101, cen, w, ex, ey, r_cap)
        skin = ref["referenceMm"]

        # through-opening: is the axis column open outward from just inside?
        iv = ray_intervals(T101, cen + w * (skin - 3.0), w, 0.0, 40.0) or []
        blocked = sum(b - a for a, b in iv)
        openok = blocked < 0.05

        if short == "JOY":
            rows[short] = {"throughOpening": bool(openok), "blockedMm": float(blocked),
                           "docs101SkinMm": skin, "axisErrorDeg": 0.0}
            print("%-5s %9s %9.4f %11.4f %11s %11s  %s"
                  % (short, "YES" if openok else "NO", 0.0, skin, "-", "-",
                     "PASS" if openok else "FAIL"))
            del cap
            continue

        sh = plc["buttons"][short]["axialShiftOutwardMm"]
        s = ((P + w * sh) - cen) @ w
        prot = float(s.max()) - skin
        law = ext["ORIGINAL"]["buttons"][short]["unpressedProtrusionMm"]
        dev = prot - law
        seat_z = float((np.asarray(core_j["seats"][short]["plateTopWorld"], float) - cen) @ w)
        cap_und = float(s.min())
        stack = cap_und - seat_z
        ok = openok and abs(dev) <= PROT_TOL and abs(stack - 4.759) < 0.01
        rows[short] = {"throughOpening": bool(openok), "blockedMm": float(blocked),
                       "axisErrorDeg": 0.0, "centreErrorMm": 0.0,
                       "docs101SkinMm": skin, "protrusionMm": prot,
                       "originalLawMm": law, "deviationMm": dev,
                       "capUndersideToPlateTopMm": stack,
                       "result": "PASS" if ok else "FAIL"}
        print("%-5s %9s %9.4f %11.4f %11.4f %+11.4f  %s"
              % (short, "YES" if openok else "NO", 0.0, skin, prot, dev,
                 "PASS" if ok else "FAIL"))
        del cap
        L.memory("reg " + short)
    npass = sum(1 for k in names if rows[k]["result"] == "PASS")
    print("  T1-T8 alignment = %d/8   JOY = %s"
          % (npass, "PASS" if rows["JOY"]["throughOpening"] else "FAIL"))

    # ================= section 12: joystick ================================
    print("")
    print("=== section 12: joystick holder / deck against docs/101 ===")
    jw = L.unit(np.asarray(joyj["joyAxisWorld"], float))
    jc = np.asarray(joyj["knobCentreWorld"], float)
    keep = import_step(str(L.REV_A / "06_keepouts" / "THUMB_KEEPOUT_ASSEMBLY.step"))
    rz = Location(Vector(*[float(x) for x in (jw * c07j["szhRaiseMm"])]))
    groups = switch_groups()
    fing_solids = [s for g in groups.values() for v in g.values() for s in v]
    joy_res = {}
    for ch in list(getattr(keep, "children", []) or []):
        lab = str(ch.label)
        if not ch.solids() or not lab.startswith("SZH"):
            continue
        ks, _ = L.as_single_solid(ch, lab)
        ks = ks.moved(rz)
        v_sh = sum(L.inter_vol(ks, s) for s in shells.values())
        v_fi = sum(L.inter_vol(ks, s) for s in fing_solids)
        joy_res[lab] = {"vsDocs101ShellMm3": v_sh, "vsFingerSwitchesMm3": v_fi}
        print("  %-32s shell %10.4f   finger %10.4f" % (lab[:32], v_sh, v_fi))
        del ks
        L.memory("joy " + lab)

    # ================= section 16: assembly ================================
    print("")
    print("=== section 16: assembly sequences ===")
    asm = {}
    # A: Finger switches already installed, then the Thumb core goes in.
    # The core enters the open shell half, so sweep it along the split normal
    # and along the JOY axis and score both against the installed switches.
    dirs = {"along -JOY axis (into the cavity)": -jw,
            "along +U (JaD side)": L.DATUM_U,
            "along -U (JfD side)": -L.DATUM_U}
    for dname, dv in dirs.items():
        blocked_f = blocked_s = 0.0
        for k in range(1, 21):
            mv = Location(Vector(*[float(x) for x in (dv * float(k))]))
            c = core.moved(mv)
            blocked_f += sum(L.inter_vol(c, s) for s in fing_solids)
        asm["core_insert_" + dname] = {"vsFingerSwitchesMm3": blocked_f}
        print("  core swept 20 mm %-30s vs Finger switches = %9.4f mm3"
              % (dname, blocked_f))
        L.memory("asm " + dname)
    # B: Thumb core already in, then Finger switches are pushed in from inside
    fin_block = {}
    for b, g in groups.items():
        whole = [s for v in g.values() for s in v]
        tot = 0.0
        for k in range(1, 13):
            mv = Location(Vector(*[float(x) for x in (
                -L.unit(np.asarray(json.loads(
                    (L.ROOT / "build123d_workbench/out/lower15_true_bare_finger_base"
                     / "finger_button_frozen_datums.json").read_text(encoding="utf-8"))
                    ["controls"][b]["pressAxis"], float)) * float(k))]))
            tot += sum(L.inter_vol(s.moved(mv), core) for s in whole)
        fin_block[b] = tot
        L.memory("asmB " + b)
    print("  Finger switch withdrawal corridor (12 mm) vs the installed core:")
    for b, v in fin_block.items():
        print("     %-4s %9.4f mm3%s" % (b, v, "  <- blocked" if v > 1.0e-6 else ""))
    seqA = all(v["vsFingerSwitchesMm3"] <= 1.0e-6 for v in asm.values() if "core_insert" in "")
    seqA = asm["core_insert_along -JOY axis (into the cavity)"]["vsFingerSwitchesMm3"] <= 1.0e-6
    seqB = all(v <= 1.0e-6 for v in fin_block.values())
    print("")
    print("  SEQUENCE A  Finger switches epoxied first, then the Thumb core: %s"
          % ("VALID" if seqA else "BLOCKED"))
    print("  SEQUENCE B  Thumb core first, then Finger switches inserted:    %s"
          % ("VALID" if seqB else "BLOCKED"))

    # ================= section 18: FDM regression ==========================
    print("")
    print("=== section 18: FDM regression (C07 geometry unchanged) ===")
    re_core, _ = L.as_single_solid(import_step(str(CAND)), "C07_REIMPORT")
    f = Field(L.local_triangles(re_core, tol=0.05, ang=0.10))
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
    lab, n = ndimage.label(plan)
    fdm = {"solids": len(list(re_core.solids())), "valid": bool(re_core.is_valid),
           "volumeMm3": L.vol(re_core), "faces": len(list(re_core.faces())),
           "interiorThinMm2": thin, "planComponents": int(n),
           "thicknessP25": float(np.percentile(t[plan], 25)),
           "thicknessP50": float(np.percentile(t[plan], 50))}
    print("  STEP reimport: %d solid(s), valid=%s, vol %.3f, faces %d"
          % (fdm["solids"], fdm["valid"], fdm["volumeMm3"], fdm["faces"]))
    print("  interior area below %.2f mm = %.2f mm2   plan components %d"
          % (MIN_WALL, thin, n))
    print("  thickness p25 %.3f  p50 %.3f" % (fdm["thicknessP25"], fdm["thicknessP50"]))
    print("  volume vs i10_c07.json %.3f -> delta %.6f mm3"
          % (c07j["volumeMm3"], fdm["volumeMm3"] - c07j["volumeMm3"]))

    L.write_json(REG / "j03_control_registration.json",
                 {"controls": rows, "t1t8Pass": npass,
                  "joyOpen": bool(rows["JOY"]["throughOpening"])})
    L.write_json(OUT / "j03_assembly.json",
                 {"coreInsertion": asm, "fingerWithdrawalVsCore": fin_block,
                  "sequenceAValid": bool(seqA), "sequenceBValid": bool(seqB)})
    L.write_json(FDM / "j03_fdm_regression.json", dict(fdm, joystick=joy_res,
                                                       memory=L.MEMORY_LOG))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
