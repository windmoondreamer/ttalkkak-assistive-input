"""ORIGINAL BUTTON MECHANISM REBASE AUDIT  --  AUDIT / REFERENCE ONLY.

Extracts the original OneGrip button subsystem (PushBtn + 4 cap families +
shell opening + Backplate) from the frozen local dump, overlays the actual
measured ITS-1105 on it, and builds ONE audit-only reference button.

Production geometry is never read for modification and never written:
no cap, carrier, switch pose, shell or SZH fixture is touched.

Mesh geometry is used for measurement and rendering only.  The exported STEP
contains parametric reference envelopes rebuilt from measured numbers, never a
mesh-to-CAD reconstruction of the original shell.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from build123d import (
    Align, Box, Compound, Cylinder, Location, Plane, Vector, export_step,
)

from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles

ROOT = Path(__file__).resolve().parents[1]
DUMP = ROOT / "cad_dump"
OUT = ROOT / "build123d_workbench" / "out" / "original_button_rebase"
REND = ROOT / "renders" / "original_button_rebase"

# ---------------------------------------------------------------- measured
# ORIGINAL PushBtn, measured from cad_dump/mesh_PushBtn.json in its own frame
# (local +Y is the actuation axis, u = 0 at the plastic body bottom).
PB = dict(
    body=6.010, body_top=3.050, shoulder=5.500, shoulder_top=3.550,
    act_dia=3.500, act_top=5.000,
    term_metal=(0.728, 0.700), term_cx=3.419, term_cz=1.955,
    term_u0=-3.519, term_u1=-0.760, skirt=6.310, skirt_top=1.000,
)
PB_ACT_PROJ = PB["act_top"] - PB["shoulder_top"]        # 1.450
PB_TERM_OUTER = 7.566

# ACTUAL measured ITS-1105 (its1105_physical_sample_reaudit.json + user table)
ITS = dict(body_x=6.12, body_y=6.05, housing_h=3.56, total_h=6.00,
           act_dia=3.35, act_proj=2.44,
           term_pitch=4.50, term_outer=7.90, term_metal=(0.30, 0.70),
           term_root=1.80, travel=(0.15, 0.25, 0.35))

# ORIGINAL cap families, measured in each cap's own dominant-plane frame
CAPS = {
    "Button_corner": dict(a=7.597, b=7.597, t=4.866, tris=138),
    "Button_middle": dict(a=7.600, b=7.600, t=4.762, tris=12),
    "Button_side":   dict(a=7.600, b=7.600, t=4.938, tris=38),
    "Button_wide":   dict(a=9.600, b=6.600, t=4.742, tris=26),
}
ORIG_CLEARANCE_TOTAL = 0.400          # measured, both axes
ORIG_OPENING = 8.000                  # cap 7.600 + 0.400

# Current custom mechanism, for comparison only (never modified here).
CUR = dict(cap=7.60, cap_thk=1.20, cap_exposure=1.00, opening=8.00,
           boss=4.50, socket=3.45, front_depth_n1=4.80, body_h=3.56,
           rear_plate=1.60, travel=0.35)


def load(name):
    return np.asarray(json.load(open(DUMP / ("mesh_%s.json" % name)))["tris"], float)


def occurrences():
    asm = json.load(open(DUMP / "asmdef_Joystick.json"))
    r = asm["rootAssembly"]
    inst = {i["id"]: i["name"] for i in r["instances"]}
    out = {}
    for o in r["occurrences"]:
        if len(o["path"]) != 1:
            continue
        M = np.asarray(o["transform"], float).reshape(4, 4).copy()
        M[:3, 3] *= 1000.0            # Onshape assembly transforms are in METRES
        out[inst[o["path"][0]]] = M
    return out


def cap_frame(cm):
    """Right-handed frame from the cap's dominant plane; +w points outward."""
    a, b, c = cm[:, 0], cm[:, 1], cm[:, 2]
    n = np.cross(b - a, c - a)
    ar = np.linalg.norm(n, axis=1) * 0.5
    ok = ar > 1e-12
    nn = n[ok] / np.linalg.norm(n[ok], axis=1)[:, None]
    key = np.round(nn, 2)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    tot = np.array([ar[ok][inv == i].sum() for i in range(len(uniq))])
    w = nn[inv == int(np.argmax(tot))].mean(0)
    w /= np.linalg.norm(w)
    tmp = np.array([1.0, 0.0, 0.0])
    if abs(tmp @ w) > 0.9:
        tmp = np.array([0.0, 1.0, 0.0])
    e1 = np.cross(w, tmp)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(w, e1)
    v = cm.reshape(-1, 3)
    return (v.min(0) + v.max(0)) / 2, np.stack([e1, e2, w])


# ------------------------------------------------- parametric reference parts
def pushbtn_solid(label="ORIGINAL_PUSHBTN_ENVELOPE"):
    """PushBtn rebuilt from measured numbers; +Z is the actuation axis."""
    parts = [
        Box(PB["skirt"], PB["skirt"], PB["skirt_top"],
            align=(Align.CENTER, Align.CENTER, Align.MIN)),
        Box(PB["body"], PB["body"], PB["body_top"],
            align=(Align.CENTER, Align.CENTER, Align.MIN)),
        Box(PB["shoulder"], PB["shoulder"], PB["shoulder_top"] - PB["body_top"],
            align=(Align.CENTER, Align.CENTER, Align.MIN)
            ).moved(Location(Vector(0, 0, PB["body_top"]))),
        Cylinder(PB["act_dia"] / 2, PB["act_top"] - PB["shoulder_top"],
                 align=(Align.CENTER, Align.CENTER, Align.MIN)
                 ).moved(Location(Vector(0, 0, PB["shoulder_top"]))),
    ]
    tm = PB["term_metal"]
    for sx in (-1, 1):
        for sz in (-1, 1):
            parts.append(
                Box(tm[0], tm[1], PB["term_u1"] - PB["term_u0"],
                    align=(Align.CENTER, Align.CENTER, Align.MIN)
                    ).moved(Location(Vector(sx * PB["term_cx"], sz * PB["term_cz"],
                                            PB["term_u0"]))))
    s = parts[0]
    for p in parts[1:]:
        s = s.fuse(p)
    s = s.clean()
    s.label = label
    return s


def its_solid(label="ITS1105_MEASURED_ENVELOPE"):
    """ITS-1105 rebuilt from the measured sample; +Z is the actuation axis."""
    parts = [
        Box(ITS["body_x"], ITS["body_y"], ITS["housing_h"],
            align=(Align.CENTER, Align.CENTER, Align.MIN)),
        Cylinder(ITS["act_dia"] / 2, ITS["act_proj"],
                 align=(Align.CENTER, Align.CENTER, Align.MIN)
                 ).moved(Location(Vector(0, 0, ITS["housing_h"]))),
    ]
    tm = ITS["term_metal"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(
                Box(tm[0], tm[1], ITS["term_root"],
                    align=(Align.CENTER, Align.CENTER, Align.MIN)
                    ).moved(Location(Vector(sx * ITS["term_outer"] / 2,
                                            sy * ITS["term_pitch"] / 2,
                                            -ITS["term_root"]))))
    s = parts[0]
    for p in parts[1:]:
        s = s.fuse(p)
    s = s.clean()
    s.label = label
    return s


def cap_solid(fam, label):
    d = CAPS[fam]
    s = Box(d["a"], d["b"], d["t"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    s.label = label
    return s


def opening_solid(fam, label):
    d = CAPS[fam]
    s = Box(d["a"] + ORIG_CLEARANCE_TOTAL, d["b"] + ORIG_CLEARANCE_TOTAL, 3.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
    s.label = label
    return s


# ------------------------------------------------------------- measurement
def measure_original_subsystem():
    """All ORIGINAL-side measurements, from the frozen dump."""
    occ = occurrences()
    shell = np.vstack([load("Joystick_1"), load("Joystick_2")])
    sv = shell.reshape(-1, 3)
    rep = {"caps": {}, "switches": {}, "pairing": {}}

    for name, M in sorted(occ.items()):
        if not name.startswith("PushBtn"):
            continue
        ax = M[:3, :3] @ np.array([0.0, 1.0, 0.0])
        ax /= np.linalg.norm(ax)
        rep["switches"][name] = dict(
            seat=M[:3, 3].tolist(), axis=ax.tolist(),
            tip=(M[:3, :3] @ np.array([0.0, PB["act_top"], 0.0]) + M[:3, 3]).tolist())
    axes = np.array([v["axis"] for v in rep["switches"].values()])
    rep["switchAxisSpreadDeg"] = float(
        np.degrees(np.arccos(np.clip((axes @ axes[0]).min(), -1, 1))))
    rep["switchAxisFromVerticalDeg"] = float(
        np.degrees(np.arccos(abs(axes[0][2]))))
    seats = np.array([v["seat"] for v in rep["switches"].values()])
    d = [float(np.linalg.norm(seats[i] - seats[j]))
         for i in range(len(seats)) for j in range(i + 1, len(seats))]
    rep["switchGridMinPitchMm"] = min(d)

    for capname in sorted({k.split(" <")[0] for k in occ if k.startswith("Button_")}):
        cm = load(capname)
        o, B = cap_frame(cm)
        lc = (B @ (cm.reshape(-1, 3) - o).T).T
        ls = (B @ (sv - o).T).T
        inb = ls[(ls[:, 2] > lc[:, 2].min()) & (ls[:, 2] < lc[:, 2].max())
                 & (np.abs(ls[:, 0]) < 12) & (np.abs(ls[:, 1]) < 12)]
        clr = {}
        for i, tag in ((0, "a"), (1, "b")):
            j = 1 - i
            p = inb[np.abs(inb[:, j]) < 2.0]
            if (p[:, i] > 0).any() and (p[:, i] < 0).any():
                span = p[p[:, i] > 0][:, i].min() - p[p[:, i] < 0][:, i].max()
                clr[tag] = float(span - (lc[:, i].max() - lc[:, i].min()))
        col = ls[(np.abs(ls[:, 0]) < 6) & (np.abs(ls[:, 1]) < 6)]
        # nearest switch axis
        best, bd = None, 1e9
        c = cm.reshape(-1, 3).mean(0)
        for swn, M in occ.items():
            if not swn.startswith("PushBtn"):
                continue
            loc = M[:3, :3].T @ (c - M[:3, 3])
            perp = float(np.hypot(loc[0], loc[2]))
            if perp < bd:
                bd, best = perp, swn
        rep["caps"][capname] = dict(
            a=float(lc[:, 0].max() - lc[:, 0].min()),
            b=float(lc[:, 1].max() - lc[:, 1].min()),
            thickness=float(lc[:, 2].max() - lc[:, 2].min()),
            clearanceToOpening=clr,
            protrusionMm=float(lc[:, 2].max() - col[:, 2].max()) if len(col) else None,
            nearestSwitch=best, lateralOffsetToSwitchAxisMm=float(bd))
    return rep


def build_reference_button():
    """AUDIT-ONLY reference button: ORIGINAL architecture, resolved.

    The original CAD switch placement is schematic (see report), so the switch
    is placed on the CAP's own axis -- the geometry the original author really
    modelled -- with the actuator tip against the cap underside.
    """
    fam = "Button_middle"
    d = CAPS[fam]
    cap_bottom = 0.0
    cap = cap_solid(fam, "ORIGINAL_CAP_%s" % fam.upper())
    opening = opening_solid(fam, "ORIGINAL_SHELL_OPENING_8x8_REFERENCE")
    opening = opening.moved(Location(Vector(0, 0, cap_bottom + 1.20)))

    pb = pushbtn_solid()
    pb = pb.moved(Location(Vector(0, 0, cap_bottom - PB["act_top"])))
    its = its_solid()
    its = its.moved(Location(Vector(0, 0, cap_bottom - ITS["total_h"])))

    seat_pb = cap_bottom - PB["act_top"]
    seat_its = cap_bottom - ITS["total_h"]
    return dict(cap=cap, opening=opening, pushbtn=pb, its=its,
                seatPushBtnMm=seat_pb, seatItsMm=seat_its,
                seatDeltaMm=seat_pb - seat_its,
                pushbtnRearMm=seat_pb, itsRearMm=seat_its,
                capThicknessMm=d["t"])


# ------------------------------------------------------------------ renders
C_SHELL = (128, 136, 148)
C_CAP = (232, 176, 72)
C_PB = (86, 176, 220)
C_ITS = (226, 96, 96)
C_BP = (150, 200, 150)
FOOT = "AUDIT / REFERENCE ONLY - no production geometry modified"


def xf(t, M):
    p = t.reshape(-1, 3)
    return ((M[:3, :3] @ p.T).T + M[:3, 3]).reshape(t.shape)


def near_tris(t, centre, radius):
    """Keep triangles whose every vertex is within radius of centre."""
    d = np.linalg.norm(t.reshape(-1, 3) - np.asarray(centre), axis=1).reshape(-1, 3)
    return t[(d < radius).all(1)]


def clip_tris(t, axis, val, keep_below=True):
    """Keep triangles fully on one side -- a section view without booleans."""
    m = (t[:, :, axis] <= val).all(1) if keep_below else (t[:, :, axis] >= val).all(1)
    return t[m]


def renders(ref, rep):
    REND.mkdir(parents=True, exist_ok=True)
    occ = occurrences()
    shell = np.vstack([load("Joystick_1"), load("Joystick_2")])
    bp_mesh = load("Backplate")
    capmesh = {n: load(n) for n in
               ("Button_corner_1", "Button_middle_1", "Button_side_1", "Button_wide_1",
                "Button_corner_2", "Button_middle_2", "Button_side_2", "Button_wide_2")}
    pbm = load("PushBtn")
    sw_world = {n: xf(pbm, M) for n, M in occ.items() if n.startswith("PushBtn")}

    thumb = np.vstack(list(capmesh.values())).reshape(-1, 3)
    hub = thumb.mean(0)
    fit = thumb
    shell_local = near_tris(shell, hub, 42.0)
    bp_local = near_tris(bp_mesh, hub, 46.0)

    # 1 - original full button subsystem
    raster_scene(
        REND / "01_original_button_subsystem.png",
        [(shell_local, C_SHELL)] + [(m, C_CAP) for m in capmesh.values()]
        + [(m, C_PB) for m in sw_world.values()] + [(bp_local, C_BP)],
        "ORIGINAL button subsystem",
        "shell + 8 caps + 8 PushBtn + Backplate, assembly coordinates (mm)",
        FOOT, camera_offset=(120.0, -150.0, 110.0), fit_points=None)

    # 2 - exploded
    ex = []
    for m in capmesh.values():
        ex.append((m + np.array([0, -18.0, 20.0]), C_CAP))
    for m in sw_world.values():
        ex.append((m + np.array([0, 14.0, -16.0]), C_PB))
    raster_scene(
        REND / "02_original_subsystem_exploded.png",
        [(shell_local, C_SHELL), (bp_local + np.array([0, 26.0, -30.0]), C_BP)] + ex,
        "ORIGINAL subsystem exploded",
        "caps out along +cap axis, switches and Backplate in",
        FOOT, camera_offset=(120.0, -150.0, 110.0), fit_points=None)

    # 3 - PushBtn isolated
    raster_scene(
        REND / "03_original_pushbtn_isolated.png", [(pbm, C_PB)],
        "ORIGINAL PushBtn isolated",
        "body 6.010 sq, housing top 3.550, actuator dia 3.500 proj 1.450, "
        "4 terminals 0.728 x 0.700",
        FOOT, camera_offset=(16.0, -20.0, 14.0),
        fit_points=pbm.reshape(-1, 3))

    # 4 - ITS isolated
    itst = safe_triangles(ref["its"])
    raster_scene(
        REND / "04_actual_its1105_isolated.png", [(itst, C_ITS)],
        "ACTUAL measured ITS-1105",
        "body 6.12 x 6.05, housing 3.56, total 6.00, actuator dia 3.35 proj 2.44",
        FOOT, camera_offset=(16.0, -20.0, 14.0),
        fit_points=itst.reshape(-1, 3),
        wireframes=[(safe_edge_lines(ref["its"]), (30, 30, 30, 220))])

    # 5 - overlay, both seated on a common actuator-tip datum
    pbt = safe_triangles(pushbtn_solid())
    itso = safe_triangles(its_solid().moved(
        Location(Vector(0, 0, PB["act_top"] - ITS["total_h"]))))
    raster_scene(
        REND / "05_pushbtn_vs_its_overlay.png",
        [(pbt, C_PB)], "PushBtn vs ITS-1105 overlay",
        "common actuator-tip datum; blue = original PushBtn, red = measured ITS",
        FOOT, camera_offset=(18.0, -22.0, 15.0),
        fit_points=np.vstack([pbt.reshape(-1, 3), itso.reshape(-1, 3)]),
        transparent_objects=[(itso, (226, 96, 96, 150))])

    # 6/7 - section: original cap + PushBtn, then cap + ITS
    capt = safe_triangles(ref["cap"])
    opent = safe_triangles(ref["opening"])
    for tag, sw, col, title in (
            ("06_original_cap_pushbtn_section", ref["pushbtn"], C_PB,
             "ORIGINAL cap + ORIGINAL PushBtn (section)"),
            ("07_original_cap_its_section", ref["its"], C_ITS,
             "ORIGINAL cap + ACTUAL ITS-1105 substituted (section)")):
        st = safe_triangles(sw)
        allp = np.vstack([capt.reshape(-1, 3), st.reshape(-1, 3)])
        raster_scene(
            REND / (tag + ".png"),
            [(clip_tris(capt, 1, 0.0), C_CAP), (clip_tris(st, 1, 0.0), col)],
            title,
            "cut at y=0; cap underside on actuator tip; opening 8.00 shown ghosted",
            FOOT, camera_offset=(16.0, -20.0, 13.0), fit_points=allp,
            transparent_objects=[(clip_tris(opent, 1, 0.0), (200, 200, 210, 90))])

    # 8 - guide / retention closeup on the real shell
    M = occ["PushBtn <4>"]
    cm = capmesh["Button_middle_1"]
    o, B = cap_frame(cm)
    sub = near_tris(shell, o, 13.0)
    raster_scene(
        REND / "08_original_guide_retention_closeup.png",
        [(sub, C_SHELL), (cm, C_CAP)],
        "ORIGINAL opening / guide / retention closeup",
        "cap 7.600 in an 8.000 opening: 0.200 mm per side, no shoulder, no lip",
        FOOT, camera_offset=tuple(B[2] * 26.0 + B[0] * 11.0 + B[1] * 9.0),
        fit_points=None)

    # 9 - current custom mechanism vs original architecture
    cur_cap = ROOT / "build123d_workbench" / "out" / "finger_controls_v2" / "N1_cap.step"
    objs = [(capt, C_CAP)]
    trans = []
    if cur_cap.exists():
        from build123d import import_step
        cc = import_step(cur_cap)
        cct = safe_triangles(cc)
        cct = cct - cct.reshape(-1, 3).mean(0) + np.array([14.0, 0, 0])
        objs.append((cct, (120, 200, 160)))
    raster_scene(
        REND / "09_current_vs_original_architecture.png", objs,
        "CURRENT custom cap vs ORIGINAL cap",
        "left: original solid block 7.600 x 7.600 x 4.762   "
        "right: current 7.60 pad 1.20 + boss 4.50 + socket 3.45",
        FOOT, camera_offset=(30.0, -34.0, 24.0),
        fit_points=np.vstack([t for t, _ in objs]).reshape(-1, 3))

    # 10 - the 8 finger positions with original cap family candidates
    man = json.load(open(ROOT / "build123d_workbench" / "out" / "baseline_manifest.json"))
    jad = load("ITS_LIVE_JaD")
    jfd = load("ITS_LIVE_JfD")
    fam_for = {"I2": "Button_side", "I3": "Button_side", "I4": "Button_corner",
               "M3": "Button_side", "M4": "Button_corner", "N1": "Button_middle",
               "N2": "Button_middle", "N3": "Button_corner"}
    fcen = np.mean([d["center_mm"] for d in man["button_datums"].values()], axis=0)
    objs = [(near_tris(jad, fcen, 34.0), C_SHELL),
            (near_tris(jfd, fcen, 34.0), (150, 156, 166))]
    pts = []
    for name, d in man["button_datums"].items():
        fam = fam_for.get(name)
        if fam is None:
            continue
        c = np.asarray(d["center_mm"], float)
        ax = np.asarray(d["axis"], float)
        ax = ax / np.linalg.norm(ax)
        cs = cap_solid(fam, "x")
        pl = Plane(origin=tuple(c - ax * CAPS[fam]["t"] * 0.35), z_dir=tuple(-ax))
        t = safe_triangles(pl.location * cs)
        objs.append((t, C_CAP))
        pts.append(t.reshape(-1, 3))
    raster_scene(
        REND / "10_finger_positions_original_cap_family.png", objs,
        "8 FINGER positions with ORIGINAL cap family candidates",
        "approved exterior centres unchanged; original cap design language only",
        FOOT, camera_offset=tuple(
            np.mean([np.asarray(d["axis"], float) / np.linalg.norm(d["axis"])
                     for d in man["button_datums"].values()], axis=0) * -95.0
            + np.array([0.0, 0.0, 30.0])),
        fit_points=None)
    return sorted(p.name for p in REND.glob("*.png"))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rep = measure_original_subsystem()
    ref = build_reference_button()

    asm = Compound(children=[ref["cap"], ref["opening"], ref["pushbtn"]],
                   label="ORIGINAL_ARCHITECTURE_WITH_ORIGINAL_PUSHBTN")
    asm2 = Compound(children=[cap_solid("Button_middle", "ORIGINAL_CAP_Button_middle"),
                              opening_solid("Button_middle", "ORIGINAL_SHELL_OPENING"),
                              ref["its"]],
                    label="ORIGINAL_ARCHITECTURE_WITH_ACTUAL_ITS1105")
    export_step(asm, OUT / "REFERENCE_BUTTON_ORIGINAL_PUSHBTN.step")
    export_step(asm2, OUT / "REFERENCE_BUTTON_ITS_SUBSTITUTED.step")
    export_step(pushbtn_solid(), OUT / "ORIGINAL_PUSHBTN_ENVELOPE.step")
    export_step(its_solid(), OUT / "ITS1105_MEASURED_ENVELOPE.step")

    # ---- compatibility verdicts
    dbody = max(abs(ITS["body_x"] - PB["body"]), abs(ITS["body_y"] - PB["body"]))
    dact = abs(ITS["act_dia"] - PB["act_dia"])
    dh_house = abs(ITS["housing_h"] - PB["shoulder_top"])
    dh_total = abs(ITS["total_h"] - PB["act_top"])
    dterm = max(abs(ITS["term_pitch"] - 2 * PB["term_cz"]),
                abs(ITS["term_outer"] - PB_TERM_OUTER))
    verdict = dict(
        BODY_COMPATIBILITY="NEAR-EQUIVALENT (max delta %.3f mm, both fit a 6.40 seat)" % dbody,
        ACTUATOR_COMPATIBILITY="NEAR-EQUIVALENT DIAMETER (delta %.3f mm) but "
                               "PROJECTION DIFFERS %.3f mm" % (dact, ITS["act_proj"] - PB_ACT_PROJ),
        HEIGHT_COMPATIBILITY="HOUSING NEAR-IDENTICAL (delta %.3f mm); TOTAL differs %.3f mm, "
                             "entirely from actuator projection" % (dh_house, dh_total),
        TERMINAL_COMPATIBILITY="REQUIRES ADAPTATION (pitch %+.3f, outer span %+.3f mm)"
                               % (ITS["term_pitch"] - 2 * PB["term_cz"],
                                  ITS["term_outer"] - PB_TERM_OUTER),
        OVERALL="REQUIRES SMALL ADAPTATION",
    )

    data = dict(
        schema="onegrip.original_button_mechanism_rebase_audit.v1",
        generatedUtc=datetime.now(timezone.utc).isoformat(),
        classification="AUDIT + REFERENCE RECONSTRUCTION; "
                       "PRODUCTION GEOMETRY MODIFICATION = 0",
        unitsNote="Onshape assembly occurrence transforms are in METRES; "
                  "cached tessellation meshes are in MILLIMETRES",
        originalPushBtn=PB, originalPushBtnActuatorProjection=PB_ACT_PROJ,
        actualIts1105=ITS, originalCapFamilies=CAPS,
        originalOpeningMm=ORIG_OPENING,
        originalClearanceTotalMm=ORIG_CLEARANCE_TOTAL,
        currentMechanism=CUR, compatibility=verdict,
        originalSubsystem=rep, referenceButton={
            k: v for k, v in ref.items() if not hasattr(v, "volume")},
    )
    (OUT / "original_button_rebase_audit.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    pngs = renders(ref, rep)
    print(json.dumps(dict(
        out=str(OUT), renders=pngs,
        switchAxisSpreadDeg=round(rep["switchAxisSpreadDeg"], 6),
        switchAxisFromVerticalDeg=round(rep["switchAxisFromVerticalDeg"], 4),
        switchGridMinPitchMm=round(rep["switchGridMinPitchMm"], 4),
        maxCapLateralOffsetMm=round(max(
            c["lateralOffsetToSwitchAxisMm"] for c in rep["caps"].values()), 4),
        compatibility=verdict,
        productionGeometryModificationCount=0), indent=2))


if __name__ == "__main__":
    main()
